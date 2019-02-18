from gettext import gettext as _
import logging
import asyncio
import aiohttp
import os
import shutil
import gzip
from collections import defaultdict
from tempfile import NamedTemporaryFile

from debian import deb822, debfile

from urllib.parse import urlparse, urlunparse

from pulpcore.plugin.models import Artifact, ProgressBar, Repository
from pulpcore.plugin.stages import (
    DeclarativeArtifact,
    DeclarativeContent,
    DeclarativeVersion,
    Stage,
    QueryExistingArtifacts,
    ArtifactDownloader,
    ArtifactSaver,
    QueryExistingContents,
    ContentSaver,
    RemoteArtifactSaver,
    ResolveContentFutures,
)
from pulpcore.plugin.exceptions import PulpException

from pulp_deb.app.models import GenericContent, Release, PackageIndex, Package, DebRemote


log = logging.getLogger(__name__)


class NoPackageIndexFile(PulpException):
    """
    Exception to signal, that no file representing a package index is present.
    """

    pass


def synchronize(remote_pk, repository_pk, mirror):
    """
    Sync content from the remote repository.

    Create a new version of the repository that is synchronized with the remote.

    Args:
        remote_pk (str): The remote PK.
        repository_pk (str): The repository PK.
        mirror (bool): True for mirror mode, False for additive.

    Raises:
        ValueError: If the remote does not specify a URL to sync

    """
    remote = DebRemote.objects.get(pk=remote_pk)
    repository = Repository.objects.get(pk=repository_pk)

    if not remote.url:
        raise ValueError(_('A remote must have a url specified to synchronize.'))

    first_stage = DebFirstStage(remote)
    DebDeclarativeVersion(first_stage, repository, mirror).create()


class DeclarativeFailsafeArtifact(DeclarativeArtifact):
    """
    A declarative artifact that does not fail on 404.
    """

    async def download(self):
        """
        Download the artifact and set to None on 404.
        """
        try:
            await super().download()
        except aiohttp.client_exceptions.ClientResponseError as e:
            if e.code == 404:
                self.artifact = None
                log.info('Artifact not found. Ignored')
            else:
                raise


class DebDeclarativeVersion(DeclarativeVersion):
    """
    This class creates the Pipeline.
    """

    def pipeline_stages(self, new_version):
        """
        Build the list of pipeline stages feeding into the ContentAssociation stage.

        Args:
            new_version (:class:`~pulpcore.plugin.models.RepositoryVersion`): The
                new repository version that is going to be built.

        Returns:
            list: List of :class:`~pulpcore.plugin.stages.Stage` instances

        """
        pipeline = [
            self.first_stage,
            # ---8<--- This should be specific
            # Depends on https://pulp.plan.io/issues/4209
            QueryExistingArtifacts(),
            ArtifactDownloader(),
            DebDropEmptyContent(),
            ArtifactSaver(),
            # ---8<---
        ]
        if self.download_artifacts:
            pipeline.extend([
                # QueryExistingArtifacts(),
                # ArtifactDownloader(),
                # ArtifactSaver(),
                DebUpdatePackageAttributes(),
            ])
        pipeline.extend([
            DebUpdateReleaseAttributes(self.first_stage.components,
                                       self.first_stage.architectures),
            DebUpdatePackageIndexAttributes(),
            QueryExistingContents(),
            ContentSaver(),
            RemoteArtifactSaver(),
            ResolveContentFutures(),
        ])
        return pipeline


def _filter_ssl(values, filter_list):
    """Filter space separated list and return space separated."""
    value_set = set(values.split())
    if filter_list:
        value_set &= set(filter_list)
    return ' '.join(sorted(value_set))


class DebUpdateReleaseAttributes(Stage):
    """
    This stage handles Release content.

    It also transfers the sha256 from the artifact to the Release content units.

    TODO: Verify signature
    """

    def __init__(self, components, architectures, *args, **kwargs):
        """
        Initialize release parser with filters.

        Args:
            components: list of components
            architectures: list of architectures
        """
        super().__init__(*args, **kwargs)
        self.components = components
        self.architectures = architectures

    async def run(self):
        """
        Parse Release content units.

        Update release content with information obtained from its artifact.
        """
        with ProgressBar(message='Update Release units') as pb:
            async for d_content in self.items():
                if isinstance(d_content.content, Release):
                    release = d_content.content
                    release_artifact = d_content.d_artifacts[0].artifact
                    release.sha256 = release_artifact.sha256
                    with open(release_artifact.storage_path(''), 'rb') as f:
                        release_dict = deb822.Release(f)
                        release.codename = release_dict['Codename']
                        release.suite = release_dict['Suite']
                        # TODO split of extra stuff e.g. : 'updates/main' -> 'main'
                        release.components = _filter_ssl(
                            release_dict['Components'], self.components)
                        release.architectures = _filter_ssl(
                            release_dict['Architectures'], self.architectures)
                        log.debug('Codename: {}'.format(release.codename))
                        log.debug('Components: {}'.format(release.components))
                        log.debug('Architectures: {}'.format(release.architectures))
                    pb.increment()
                await self.put(d_content)


class DebUpdatePackageIndexAttributes(Stage):  # TODO: Needs a new name
    """
    This stage handles PackageIndex content.
    """

    async def run(self):
        """
        Parse PackageIndex content units.

        Ensure, that an uncompressed artifact is available.
        """
        with ProgressBar(message='Update PackageIndex units') as pb:
            async for d_content in self.items():
                if isinstance(d_content.content, PackageIndex):
                    if not d_content.d_artifacts:
                        raise NoPackageIndexFile()

                    content = d_content.content
                    if not [da for da in d_content.d_artifacts
                            if da.artifact.sha256 == content.sha256]:
                        # No main_artifact found uncompress one
                        filename = _uncompress_artifact(d_content.d_artifacts[0].artifact)
                        da = DeclarativeArtifact(
                            Artifact(sha256=content.sha256),
                            filename,
                            content.relative_path,
                            d_content.d_artifacts[0].remote,
                        )
                        d_content.d_artifacts.append(da)
                        await da.download()
                        da.artifact.save()
                        log.info("*** Expected: {} *** Uncompressed: {} ***".format(
                            content.sha256, da.artifact.sha256))

                    pb.increment()
                await self.put(d_content)


def _uncompress_artifact(artifact):
    with NamedTemporaryFile(delete=False) as f_out:
        with gzip.open(artifact.storage_path(''), 'rb') as f_in:
            shutil.copyfileobj(f_in, f_out)
    return 'file://{}'.format(f_out.name)


class DebUpdatePackageAttributes(Stage):
    """
    This stage handles Package content.

    It reads all Package related database fields from the actual file.
    """

    async def run(self):
        """
        Update package content with the information obtained from its artifact.
        """
        with ProgressBar(message='Update Package units') as pb:
            async for d_content in self.items():
                if isinstance(d_content.content, Package):
                    package = d_content.content
                    package_artifact = d_content.d_artifacts[0].artifact
                    package_paragraph = debfile.DebFile(
                        package_artifact.storage_path('')).debcontrol()
                    package_dict = _sanitize_package_dict(package_paragraph)
                    for key, value in package_dict.items():
                        setattr(package, key.lower(), value)
                    pb.increment()
                await self.put(d_content)


class DebDropEmptyContent(Stage):
    """
    This stage removes empty DeclarativeContent objects for GenericContent.

    In case we tried to fetch something generic, but the artifact 404ed, we simply drop it.
    """

    async def run(self):
        """
        Drop GenericContent units if they have no artifacts left.
        """
        async for d_content in self.items():
            d_content.d_artifacts = [
                da for da in d_content.d_artifacts
                if da.artifact
            ]
            if not d_content.d_artifacts:
                # No artifacts left -> drop it
                continue
            await self.put(d_content)


class DebFirstStage(Stage):
    """
    The first stage of a pulp_deb sync pipeline.
    """

    def __init__(self, remote, *args, **kwargs):
        """
        The first stage of a pulp_deb sync pipeline.

        Args:
            remote (FileRemote): The remote data to be used when syncing

        """
        super().__init__(*args, **kwargs)
        self.remote = remote
        self.distributions = [
            distribution.strip() for distribution in self.remote.distributions.split()
        ]
        self.num_distributions = len(self.distributions)
        self.components = None if self.remote.components is None else [
            component.strip() for component in self.remote.components.split()
        ]
        self.architectures = None if self.remote.architectures is None else [
            architecture.strip() for architecture in self.remote.architectures.split()
        ]

    async def run(self):
        """
        Build and emit `DeclarativeContent` from the Release data.
        """
        parsed_url = urlparse(self.remote.url)
        future_releases = []
        future_package_indices = []
        with ProgressBar(message='Creating download requests for Release files',
                         total=self.num_distributions) as pb:
            for distribution in self.distributions:
                log.info(
                    'Downloading Release file for distribution: "{}"'.format(distribution))
                release_relpath = os.path.join(
                    'dists', distribution, 'Release')
                release_path = os.path.join(parsed_url.path, release_relpath)
                release_unit = Release(
                    distribution=distribution, relative_path=release_relpath)
                release_da = DeclarativeArtifact(
                    Artifact(),
                    urlunparse(parsed_url._replace(path=release_path)),
                    release_relpath,
                    self.remote,
                )
                release_dc = DeclarativeContent(
                    content=release_unit,
                    d_artifacts=[release_da],
                    does_batch=False,
                )
                future_releases.append(release_dc.get_or_create_future())
                await self.put(release_dc)
                pb.increment()

        with ProgressBar(message='Parsing Release files', total=self.num_distributions) as pb:
            for release_future in asyncio.as_completed(future_releases):
                release = await release_future
                log.info('Parsing Release file for release: "{}"'.format(release.codename))
                release_artifact = release._artifacts.first()
                release_dict = deb822.Release(release_artifact.file)
                async for d_content in _read_release_file(release, release_dict, self.remote):
                    if isinstance(d_content.content, PackageIndex):
                        future_package_indices.append(d_content.get_or_create_future())
                    await self.put(d_content)
                pb.increment()

        with ProgressBar(message='Parsing package index files') as pb:
            for package_index_future in asyncio.as_completed(future_package_indices):
                package_index = await package_index_future
                package_index_artifact = package_index.main_artifact
                async for package_dc in _read_package_index(package_index_artifact.file,
                                                            self.remote):
                    await self.put(package_dc)
                pb.increment()


def _get_checksums(unit_dict):
    return {
        k: unit_dict[v] for k, v in {
            'sha512': 'SHA512',
            'sha256': 'SHA256',
            'sha1': 'SHA1',
            'md5': 'MD5sum',
        }.items() if v in unit_dict
    }


async def _read_release_file(release, release_dict, remote):
    """
    Parse a Release file of apt Repositories.

    Yield DeclarativeContent in the queue accordingly.

    Args:
        release_dict: parsed release dictionary
        remote: remote to associate content artifacts to

    Returns:
        async iterator: Iterator of :class:`asyncio.Future` instances

    """
    parsed_url = urlparse(remote.url)
    file_references = defaultdict(deb822.Deb822Dict)
    for digest_name in ('SHA512', 'SHA256', 'SHA1', 'MD5sum'):
        if digest_name in release_dict:
            for unit in release_dict[digest_name]:
                file_references[unit['Name']].update(unit)
    # Find Package Index files for Component Architecture combinations
    for component in release.components.split():
        for architecture in release.architectures.split():
            log.info('Component: "{}" Architecture: "{}"'.format(
                component, architecture))
            package_index_path = os.path.join(os.path.basename(
                component), 'binary-{}'.format(architecture), 'Packages')
            log.info('Downloading: {}'.format(package_index_path))
            # Use the plain package_index file as the first entry …
            package_index_files = [file_references.pop(package_index_path)]
            # … followed by the compressed versions
            for suffix in ('.gz', '.xz'):
                path = package_index_path + suffix
                if path in file_references:
                    log.info("Pathmatch: {} ~ {}".format(path, package_index_path))
                    package_index_files.append(file_references.pop(path))
            # Sync these files in PackageIndex
            package_index_relpath = os.path.join(os.path.dirname(
                release.relative_path), package_index_files[0]['Name'])
            package_index_unit = PackageIndex(
                release_pk=release,
                component=component,
                architecture=architecture,
                sha256=package_index_files[0]['SHA256'],
                relative_path=package_index_relpath,
            )
            d_artifacts = []
            for package_index_dict in package_index_files:
                package_index_relpath = os.path.join(os.path.dirname(
                    release.relative_path), package_index_dict['Name'])
                package_index_path = os.path.join(
                    parsed_url.path, package_index_relpath)
                log.info(_get_checksums(package_index_dict))
                package_index_artifact = Artifact(**_get_checksums(package_index_dict))
                d_artifacts.append(DeclarativeFailsafeArtifact(
                    package_index_artifact,
                    urlunparse(parsed_url._replace(path=package_index_path)),
                    package_index_relpath,
                    remote,
                ))
            package_index_dc = DeclarativeContent(
                content=package_index_unit,
                d_artifacts=d_artifacts,
                does_batch=False,
            )
            yield package_index_dc

    # Everything else shall be synced as GenericContent
    for generic_content_dict in file_references.values():
        generic_content_relpath = os.path.join(os.path.dirname(
            release.relative_path), generic_content_dict['Name'])
        generic_content_path = os.path.join(
            parsed_url.path, generic_content_relpath)
        generic_content_unit = GenericContent(
            sha256=generic_content_dict['SHA256'], relative_path=generic_content_relpath)
        generic_content_artifact = Artifact(**_get_checksums(generic_content_dict))
        generic_content_da = DeclarativeFailsafeArtifact(
            generic_content_artifact,
            urlunparse(parsed_url._replace(path=generic_content_path)),
            generic_content_relpath,
            remote,
        )
        generic_content_dc = DeclarativeContent(
            content=generic_content_unit, d_artifacts=[generic_content_da])
        yield generic_content_dc


async def _read_package_index(package_index, remote):
    """
    Parse a package index file of apt Repositories.

    Put DeclarativeContent in the queue accordingly.

    Args:
        package_index: file object containing package paragraphs
        remote: remote to associate content artifacts to
        out_q: :class:`asyncio.Queue`

    """
    parsed_url = urlparse(remote.url)
    for package_paragraph in deb822.Packages.iter_paragraphs(package_index):
        log.debug("Downloading package {}".format(
            package_paragraph['Package']))
        package_relpath = package_paragraph['Filename']
        package_dict = _sanitize_package_dict(package_paragraph)
        package_path = os.path.join(parsed_url.path, package_relpath)
        package_content_unit = Package(relative_path=package_relpath, **package_dict)
        package_artifact = Artifact(**_get_checksums(package_dict))
        package_da = DeclarativeArtifact(package_artifact, urlunparse(
            parsed_url._replace(path=package_path)), package_relpath, remote)
        package_dc = DeclarativeContent(
            content=package_content_unit, d_artifacts=[package_da])
        yield package_dc


def _sanitize_package_dict(package_dict):
    return {k: package_dict[v] for k, v in Package.TRANSLATION_DICT.items() if v in package_dict}
