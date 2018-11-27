import asyncio
import logging
import os
from collections import defaultdict

from debian import deb822, debfile

from gettext import gettext as _
from urllib.parse import urlparse, urlunparse

from django.db.models import Q

from pulpcore.plugin.models import Artifact, ProgressBar, Repository
from pulpcore.plugin.stages import (
    DeclarativeArtifact,
    DeclarativeContent,
    DeclarativeVersion,
    Stage,
    QueryExistingArtifacts,
    ArtifactDownloader,
    ArtifactSaver,
    QueryExistingContentUnits,
    ContentUnitSaver,
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
        raise ValueError(
            _('A remote must have a url specified to synchronize.'))

    first_stage = DebFirstStage(remote)
    DebDeclarativeVersion(first_stage, repository, mirror).create()


class DebDeclarativeArtifact(DeclarativeArtifact):
    """
    This child class adds the digest_present slot to the DeclarativeArtifact.

    This mechanism is meant as a catch all, when there is no way of knowing
    whether an artifact is already present in the latest version.
    Consider using ExistingContentNeedsNoNewArtifacts.
    """

    __slots__ = DeclarativeArtifact.__slots__ + ('digest_present',)

    def __init__(self, artifact=None, url=None, relative_path=None,
                 remote=None, extra_data=None, digest_present=True):
        """
        Initialize the declarative content with presence of digests.
        """
        super(DebDeclarativeArtifact, self).__init__(
            artifact, url, relative_path, remote, extra_data)
        self.digest_present = digest_present


class DebDeclarativeContent(DeclarativeContent):
    """
    This child class adds the future mechanism.
    """

    __slots__ = DeclarativeContent.__slots__ + ('future', )

    def __init__(self, *args, **kwargs):
        """
        Initialize the declarative content with a nonexisting future.
        """
        super(DebDeclarativeContent, self).__init__(*args, **kwargs)
        self.future = None

    def get_future(self):
        """
        Return the existing or a new future.
        """
        if self.future is None:
            # If on 3.7, we could preferrably use get_running_loop()
            self.future = asyncio.get_event_loop().create_future()
        return self.future


class DebDeclarativeVersion(DeclarativeVersion):
    """
    This class creates the Pipeline.
    """

    def pipeline_stages(self, new_version):
        """
        Build the list of pipeline stages feeding into the ContentUnitAssociation stage.

        We override this to replace the ContentUnitSaver.

        Args:
            new_version (:class:`~pulpcore.plugin.models.RepositoryVersion`): The
                new repository version that is going to be built.

        Returns:
            list: List of :class:`~pulpcore.plugin.stages.Stage` instances

        """
        return [
            self.first_stage,
            QueryExistingArtifacts(),
            ArtifactDownloader(),
            DebArtifactWithoutDigest(),
            ArtifactSaver(),
            DebParseRelease(self.first_stage.components,
                            self.first_stage.architectures),
            DebParsePackage(),
            QueryExistingContentUnits(),
            ContentUnitSaver(),
            DebContentFutures(),
        ]


class DebArtifactWithoutDigest(Stage):
    """
    This stage looks for existing artifacts that had no digets.
    """

    async def __call__(self, in_q, out_q):
        """
        Perform the pipeline stage.
        """
        while True:
            declarative_content = await in_q.get()
            if declarative_content is None:
                await out_q.put(None)
                break
            for declarative_artifact in declarative_content.d_artifacts:
                if not declarative_artifact.digest_present:
                    # Artifact may exist in the database,
                    # but we did not know the digest before downloading
                    digest_name = declarative_artifact.artifact.DIGEST_FIELDS[0]
                    digest_value = getattr(
                        declarative_artifact.artifact, digest_name)
                    if digest_value:
                        existing_artifact = Artifact.objects.filter(
                            Q(**{digest_name: digest_value}))
                        if existing_artifact:
                            declarative_artifact.artifact = existing_artifact[0]
            await out_q.put(declarative_content)


def _filter_ssl(values, filter_list):
    """Filter space separated list and return space separated."""
    value_set = set(values.split())
    if filter_list:
        value_set &= set(filter_list)
    return ' '.join(sorted(value_set))


class DebParseRelease(Stage):
    """
    This stage handles Release content.

    It also transfers the sha256 from the artifact to the Release content units.

    TODO: Update Codename, Suite, ...
    TODO: Verify signature
    """

    def __init__(self, components, architectures):
        """
        Initialize release parser with filters.

        Args:
            components: list of components
            architectures: list of architectures
        """
        self.components = components
        self.architectures = architectures
        super(DebParseRelease, self).__init__()

    async def __call__(self, in_q, out_q):
        """
        Update release content with information obtained from its artifact.
        """
        while True:
            declarative_content = await in_q.get()
            if declarative_content is None:
                await out_q.put(None)
                break
            if isinstance(declarative_content.content, Release):
                release_artifact = declarative_content.d_artifacts[0].artifact
                declarative_content.content.sha256 = release_artifact.sha256
                with open(release_artifact.storage_path(''), 'rb') as f:
                    release_dict = deb822.Release(f)
                    declarative_content.content.codename = release_dict['Codename']
                    declarative_content.content.suite = release_dict['Suite']
                    # TODO split of extra stuff e.g. : 'updates/main' -> 'main'
                    declarative_content.content.components = _filter_ssl(
                        release_dict['Components'], self.components)
                    declarative_content.content.architectures = _filter_ssl(
                        release_dict['Architectures'], self.architectures)
                    log.debug('Codename: {}'.format(
                        declarative_content.content.codename))
                    log.debug('Components: {}'.format(
                        declarative_content.content.components))
                    log.debug('Architectures: {}'.format(
                        declarative_content.content.architectures))
            await out_q.put(declarative_content)


class DebParsePackage(Stage):
    """
    This stage handles Package content.

    It reads all Package related database fields from the actual file.
    """

    async def __call__(self, in_q, out_q):
        """
        Update package content with the information obtained from its artifact.
        """
        while True:
            declarative_content = await in_q.get()
            if declarative_content is None:
                await out_q.put(None)
                break
            if isinstance(declarative_content.content, Package):
                package_artifact = declarative_content.d_artifacts[0].artifact
                package_dict = debfile.DebFile(
                    package_artifact.storage_path('')).debcontrol()
                # This line is a workaround until we can call this field `package`
                declarative_content.content.package_name = package_dict.pop(
                    'package')
                for key, value in package_dict.items():
                    setattr(declarative_content.content, key.lower(), value)
            await out_q.put(declarative_content)


class DebContentFutures(Stage):
    """
    This stage sets results for content futures.
    """

    async def __call__(self, in_q, out_q):
        """
        Set the result of available futures to the found/created content.
        """
        while True:
            declarative_content = await in_q.get()
            if declarative_content is None:
                await out_q.put(None)
                break
            if declarative_content.future is not None:
                declarative_content.future.set_result(
                    declarative_content.content)
            await out_q.put(declarative_content)


class DebFirstStage(Stage):
    """
    The first stage of a pulp_deb sync pipeline.
    """

    def __init__(self, remote):
        """
        The first stage of a pulp_deb sync pipeline.

        Args:
            remote (FileRemote): The remote data to be used when syncing

        """
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

    async def __call__(self, in_q, out_q):
        """
        Build and emit `DeclarativeContent` from the Release data.

        Args:
            in_q (asyncio.Queue): Unused because the first stage doesn't read from an input queue.
            out_q (asyncio.Queue): The out_q to send `DeclarativeContent` objects to

        """
        parsed_url = urlparse(self.remote.url)
        future_releases = []
        future_package_indices = []
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
                release_da = DebDeclarativeArtifact(
                    Artifact(),
                    urlunparse(parsed_url._replace(path=release_path)),
                    release_relpath,
                    self.remote,
                    digest_present=False,
                )
                release_dc = DebDeclarativeContent(
                    content=release_unit,
                    d_artifacts=[release_da],
                    priority=True,
                )
                future_releases.append(release_dc.get_future())
                await out_q.put(release_dc)
                pb.increment()

        with ProgressBar(message='Parsing Release files', total=len(future_releases)) as pb:
            for release_future in asyncio.as_completed(future_releases):
                release = await release_future
                log.info('Parsing Release file for release: "{}"'.format(
                    release.codename))
                future_package_indices.extend(
                    await self.read_release_file(release, parsed_url, out_q),
                )

                pb.increment()

        with ProgressBar(message='Parsing Packages files', total=len(future_package_indices)) as pb:
            for package_index_future in asyncio.as_completed(future_package_indices):
                package_index = await package_index_future
                log.info('Parsing Packages file for {}/{}'.format(
                    package_index.component, package_index.architecture))
                await self.read_packages_file(package_index, parsed_url, out_q)
                pb.increment()

        await out_q.put(None)

    async def read_release_file(self, release, parsed_url, out_q):
        """
        Parse a Release file of apt Repositories.

        Put DeclarativeContent in the queue accordingly.
        Return futures to resove in PackageIndex units.

        Args:
            release: Release content unit
            parsed_url: parsed base url
            out_q: :class:`asyncio.Queue`

        Returns:
            list: List of :class:`asyncio.Future` instances

        """
        future_package_indices = []
        with open(release.artifacts.get().storage_path(''), 'rb') as f:
            release_dict = deb822.Release(f)
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
                    d_artifacts.append(DebDeclarativeArtifact(packages_artifact, urlunparse(
                        parsed_url._replace(path=packages_path)), packages_relpath, self.remote))
                packages_dc = DebDeclarativeContent(
                    content=package_index_unit,
                    d_artifacts=d_artifacts,
                    priority=True,
                )
                future_package_indices.append(packages_dc.get_future())
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
            generic_content_da = DebDeclarativeArtifact(
                generic_content_artifact,
                urlunparse(parsed_url._replace(path=generic_content_path)),
                generic_content_relpath,
                self.remote,
            )
            generic_content_dc = DebDeclarativeContent(
                content=generic_content_unit, d_artifacts=[generic_content_da])
            await out_q.put(generic_content_dc)
        return future_package_indices

    async def read_packages_file(self, package_index, parsed_url, out_q):
        """
        Parse a Packages file of apt Repositories.

        Put DeclarativeContent in the queue accordingly.

        Args:
            release: Release content unit
            parsed_url: parsed base url
            out_q: :class:`asyncio.Queue`

        """
        with open(package_index.artifacts.first().storage_path(''), 'rb') as f:
            package_list = deb822.Packages.iter_paragraphs(f)
            for package_dict in package_list:
                log.debug("Downloading package {}".format(
                    package_dict['Package']))
                package_relpath = package_dict['Filename']
                package_path = os.path.join(parsed_url.path, package_relpath)
                package_artifact = Artifact(
                    sha256=package_dict['SHA256'],
                    sha1=package_dict['SHA1'],
                    md5=package_dict['MD5sum'])
                package_da = DebDeclarativeArtifact(package_artifact, urlunparse(
                    parsed_url._replace(path=package_path)), package_relpath, self.remote)
                package_dc = DebDeclarativeContent(
                    content=Package(), d_artifacts=[package_da])
                await out_q.put(package_dc)
