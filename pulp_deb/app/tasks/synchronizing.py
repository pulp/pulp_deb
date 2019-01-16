from gettext import gettext as _
import logging
import os
from collections import defaultdict

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
)

from pulp_deb.app.models import GenericContent, Release, PackageIndex, Package, DebRemote


log = logging.getLogger(__name__)


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
            ArtifactDownloader(),  # Releases
            ArtifactSaver(),  # Releases
            DebUpdateReleaseAttributes(self.first_stage.components,
                                       self.first_stage.architectures),
            QueryExistingContents(),  # Releases
            ContentSaver(),  # Releases
            DebParseRelease(self.first_stage.remote),
            QueryExistingArtifacts(),
            ArtifactDownloader(),
            ArtifactSaver(),
            DebParsePackageIndex(self.first_stage.remote),
        ]
        if self.download_artifacts:
            pipeline.extend([
                QueryExistingArtifacts(),
                ArtifactDownloader(),
                ArtifactSaver(),
                DebUpdatePackageAttributes(),
            ])
        pipeline.extend([
            QueryExistingContents(),
            ContentSaver(),
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
        Create declarative content units for dependent data.
        """
        with ProgressBar(message='Parsing Release files') as pb:
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


class DebParseRelease(Stage):
    """
    This stage creates download requests for PackageIndices and other generic content.
    """

    def __init__(self, remote, *args, **kwargs):
        """
        Initialize release parser 2 with remote.

        Args:
            remote: remote to associate content artifacts to
        """
        super().__init__(*args, **kwargs)
        self.remote = remote

    async def run(self):
        """
        Create declarative content units for dependent data.
        """
        with ProgressBar(message='Parsing Release files (second run)') as pb:
            async for d_content in self.items():
                if isinstance(d_content.content, Release):
                    release = d_content.content
                    release_artifact = d_content.d_artifacts[0].artifact
                    with open(release_artifact.storage_path(''), 'rb') as f:
                        release_dict = deb822.Release(f)
                        await _read_release_file(release, release_dict, self.remote, self)
                    pb.increment()
                await self.put(d_content)


class DebParsePackageIndex(Stage):
    """
    This stage handles PackageIndex content.
    """

    def __init__(self, remote, *args, **kwargs):
        """
        Initialize package index parser.

        Args:
            remote: remote to associate content artifacts to
        """
        super().__init__(*args, **kwargs)
        self.remote = remote

    async def run(self):
        """
        Parse PackageIndex content units.

        Create declarative content units for found packages.
        """
        with ProgressBar(message='Parsing package index files') as pb:
            async for d_content in self.items():
                if isinstance(d_content.content, PackageIndex):
                    package_index_artifact = d_content.d_artifacts[0].artifact
                    with open(package_index_artifact.storage_path(''), 'rb') as f:
                        await _read_package_index(f, self.remote, self)
                    pb.increment()
                await self.put(d_content)


class DebUpdatePackageAttributes(Stage):
    """
    This stage handles Package content.

    It reads all Package related database fields from the actual file.
    """

    async def run(self):
        """
        Update package content with the information obtained from its artifact.
        """
        async for d_content in self.items():
            if isinstance(d_content.content, Package):
                package = d_content.content
                package_artifact = d_content.d_artifacts[0].artifact
                package_paragraph = debfile.DebFile(
                    package_artifact.storage_path('')).debcontrol()
                package_dict = _sanitize_package_dict(package_paragraph)
                for key, value in package_dict.items():
                    setattr(package, key.lower(), value)
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
        with ProgressBar(message='Creating download requests for Release files',
                         total=len(self.distributions)) as pb:
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
                )
                await self.put(release_dc)
                pb.increment()


async def _read_release_file(release, release_dict, remote, out_q):
    """
    Parse a Release file of apt Repositories.

    Put DeclarativeContent in the queue accordingly.
    Return futures to resove in PackageIndex units.

    Args:
        release_dict: parsed release dictionary
        remote: remote to associate content artifacts to
        out_q: :class:`asyncio.Queue`

    Returns:
        list: List of :class:`asyncio.Future` instances

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
            packages_path = os.path.join(os.path.basename(
                component), 'binary-{}'.format(architecture), 'Packages')
            log.info('Downloading: {}'.format(packages_path))
            # Use the plain Packages file as the first entry
            packages_files = [file_references.pop(packages_path)]
            for path in list(file_references.keys()):
                if path.startswith(packages_path):
                    packages_files.append(file_references.pop(path))
            # Sync these files in PackageIndex
            packages_relpath = os.path.join(os.path.dirname(
                release.relative_path), packages_files[0]['Name'])
            package_index_unit = PackageIndex(
                release_pk=release,
                component=component,
                architecture=architecture,
                sha256=packages_files[0]['SHA256'],
                relative_path=packages_relpath,
            )
            d_artifacts = []
            for packages_dict in packages_files:
                packages_relpath = os.path.join(os.path.dirname(
                    release.relative_path), packages_dict['Name'])
                packages_path = os.path.join(
                    parsed_url.path, packages_relpath)
                packages_artifact = Artifact(
                    sha256=packages_dict['SHA256'],
                    sha1=packages_dict['SHA1'],
                    md5=packages_dict['MD5sum'])
                d_artifacts.append(DeclarativeArtifact(packages_artifact, urlunparse(
                    parsed_url._replace(path=packages_path)), packages_relpath, remote))
            packages_dc = DeclarativeContent(
                content=package_index_unit,
                d_artifacts=d_artifacts,
            )
            await out_q.put(packages_dc)

    # Everything else shall be synced as GenericContent
    for generic_content_dict in file_references.values():
        generic_content_relpath = os.path.join(os.path.dirname(
            release.relative_path), generic_content_dict['Name'])
        generic_content_path = os.path.join(
            parsed_url.path, generic_content_relpath)
        generic_content_unit = GenericContent(
            sha256=generic_content_dict['SHA256'], relative_path=generic_content_relpath)
        generic_content_artifact = Artifact(
            sha256=generic_content_dict['SHA256'],
            sha1=generic_content_dict['SHA1'],
            md5=generic_content_dict['MD5sum'])
        generic_content_da = DeclarativeArtifact(
            generic_content_artifact,
            urlunparse(parsed_url._replace(path=generic_content_path)),
            generic_content_relpath,
            remote,
        )
        generic_content_dc = DeclarativeContent(
            content=generic_content_unit, d_artifacts=[generic_content_da])
        await out_q.put(generic_content_dc)


async def _read_package_index(package_index, remote, out_q):
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
        package_artifact = Artifact(
            sha512=package_dict.get('SHA512'),
            sha256=package_dict.get('SHA256'),
            sha1=package_dict.get('SHA1'),
            md5=package_dict.get('MD5sum'),
        )
        package_da = DeclarativeArtifact(package_artifact, urlunparse(
            parsed_url._replace(path=package_path)), package_relpath, remote)
        package_dc = DeclarativeContent(
            content=package_content_unit, d_artifacts=[package_da])
        await out_q.put(package_dc)


def _sanitize_package_dict(package_dict):
    return {k: package_dict[v] for k, v in Package.TRANSLATION_DICT.items() if v in package_dict}
