import asyncio
import aiohttp
import os
import shutil
import bz2
import gzip
import lzma
import gnupg

from asgiref.sync import sync_to_async
from collections import defaultdict
from tempfile import NamedTemporaryFile
from debian import deb822
from urllib.parse import urlparse, urlunparse
from django.conf import settings
from django.db.utils import IntegrityError

from pulpcore.plugin.exceptions import DigestValidationError

from pulpcore.plugin.models import (
    Artifact,
    ProgressReport,
    Remote,
    Repository,
)

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

from pulp_deb.app.models import (
    GenericContent,
    Release,
    ReleaseArchitecture,
    ReleaseComponent,
    ReleaseFile,
    PackageIndex,
    InstallerFileIndex,
    Package,
    PackageReleaseComponent,
    InstallerPackage,
    AptRemote,
)

from pulp_deb.app.serializers import (
    InstallerPackage822Serializer,
    Package822Serializer,
)

from pulp_deb.app.constants import (
    NO_MD5_WARNING_MESSAGE,
    CHECKSUM_TYPE_MAP,
)


import logging
from gettext import gettext as _

log = logging.getLogger(__name__)


class NoReleaseFile(Exception):
    """
    Exception to signal, that no file representing a release is present.
    """

    def __init__(self, distribution, *args, **kwargs):
        """
        Exception to signal, that no file representing a release is present.
        """
        super().__init__(
            "No valid Release file found for '{}'.".format(distribution), *args, **kwargs
        )


class NoPackageIndexFile(Exception):
    """
    Exception to signal, that no file representing a package index is present.
    """

    def __init__(self, relative_dir, *args, **kwargs):
        """
        Exception to signal, that no file representing a package index is present.
        """
        self.relative_dir = relative_dir
        message = (
            "No suitable package index files found in '{}'. If you are syncing from a partial "
            "mirror, you can ignore this error for individual remotes "
            "(ignore_missing_package_indices='True') or system wide "
            "(FORCE_IGNORE_MISSING_PACKAGE_INDICES setting)."
        )
        super().__init__(_(message).format(relative_dir), *args, **kwargs)

    pass


class MissingReleaseFileField(Exception):
    """
    Exception signifying that the upstream release file is missing a required field.
    """

    def __init__(self, distribution, field, *args, **kwargs):
        """
        The upstream release file is missing a required field.
        """
        message = "The release file for distribution '{}' is missing the required field '{}'."
        super().__init__(_(message).format(distribution, field), *args, **kwargs)


class UnknownNoSupportForArchitectureAllValue(Exception):
    """
    Exception Signifying that the Release file contains the 'No-Support-for-Architecture-all' field,
    but with a value other than 'Packages'. We interpret this as an error since this would likely
    signify some unknown repo format, that pulp_deb is more likely to get wrong than right!
    """

    def __init__(self, release_file_path, unknown_value, *args, **kwargs):
        message = (
            "The Release file at '{}' contains the 'No-Support-for-Architecture-all' field, with "
            "unknown value '{}'! pulp_deb currently only understands the value 'Packages' for "
            "this field, please open an issue at https://github.com/pulp/pulp_deb/issues "
            "specifying the remote you are attempting to sync, so that we can improve pulp_deb!"
        )
        super().__init__(_(message).format(unknown_value), *args, **kwargs)

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
    remote = AptRemote.objects.get(pk=remote_pk)
    repository = Repository.objects.get(pk=repository_pk)

    if not remote.url:
        raise ValueError(_("A remote must have a url specified to synchronize."))

    first_stage = DebFirstStage(remote)
    DebDeclarativeVersion(first_stage, repository, mirror=mirror).create()


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
                log.info(
                    _("Artifact with relative_path='{}' not found. Ignored").format(
                        self.relative_path
                    )
                )
            else:
                raise
        except DigestValidationError:
            self.artifact = None
            log.info(
                _("Digest for artifact with relative_path='{}' not matched. Ignored").format(
                    self.relative_path
                )
            )


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
            QueryExistingArtifacts(),
            ArtifactDownloader(),
            DebDropFailedArtifacts(),
            ArtifactSaver(),
            DebUpdateReleaseFileAttributes(remote=self.first_stage.remote),
            DebUpdatePackageIndexAttributes(),
            QueryExistingContents(),
            ContentSaver(),
            RemoteArtifactSaver(),
            ResolveContentFutures(),
        ]
        return pipeline


def _filter_split_architectures(release_file_string, remote_string, distribution):
    """
    Returns the set intersection of the two architectures strings provided as a sorted list. If the
    release file includes the 'all' architecture then this is always part of the result. Any
    architectures present in the remote, but not the release file, will result in a warning.
    """
    remaining_values = set(release_file_string.split())
    if remote_string:
        remote_architectures = set(remote_string.split())
        for arch in remote_architectures - remaining_values:
            message = (
                "Architecture '{0}' is not amongst the release file architectures '{1}' for "
                "distribution '{2}'. This could be valid, but more often indicates an error in "
                "the architectures field of the remote being used."
            )
            log.warning(_(message).format(arch, release_file_string, distribution))

        remote_architectures.add("all")  # Users always want the all type architecture!
        remaining_values &= remote_architectures

    return sorted(remaining_values)


def _filter_split_components(release_file_string, remote_string, distribution):
    """
    Returns the set intersection of the two component strings provided as a sorted list. If a
    component from the release file has a path prefix, it is considered equal to a component from
    the remote, that does not. E.g.: release_file_string="updates/main updates/non-free" and
    remote_string="main" would result in a return value of ["updates/main"]. If a component from
    the remote does not correspond to any component in the release file, a warning is logged.
    """
    release_file_components = release_file_string.split()
    if not remote_string:
        filtered_components = release_file_components
    else:
        remote_components = remote_string.split()
        filtered_components = [
            component
            for component in release_file_components
            if component in remote_components or os.path.basename(component) in remote_components
        ]

        # Log any components from the remote, that do not correspont to any release file components:
        plain_components = [os.path.basename(component) for component in release_file_components]
        for component in remote_components:
            if component not in release_file_components and component not in plain_components:
                message = (
                    "Component '{0}' is not amongst the release file components '{1}' for "
                    "distribution '{2}'. This could be valid, but more often indicates an error in "
                    "the components field of the remote being used."
                )
                log.warning(_(message).format(component, release_file_string, distribution))

    return sorted(set(filtered_components))


class DebUpdateReleaseFileAttributes(Stage):
    """
    This stage handles ReleaseFile content.

    It also transfers the sha256 from the artifact to the ReleaseFile content units.
    """

    def __init__(self, remote, *args, **kwargs):
        """Initialize DebUpdateReleaseFileAttributes stage."""
        super().__init__(*args, **kwargs)
        self.remote = remote
        self.gpgkey = remote.gpgkey
        if self.gpgkey:
            gnupghome = os.path.join(os.getcwd(), "gpg-home")
            os.makedirs(gnupghome)
            self.gpg = gnupg.GPG(gpgbinary="/usr/bin/gpg", gnupghome=gnupghome)
            import_res = self.gpg.import_keys(self.gpgkey)
            if import_res.count == 0:
                log.warning(_("Key import failed."))
            pass

    async def run(self):
        """
        Parse ReleaseFile content units.

        Update release content with information obtained from its artifact.
        """
        async with ProgressReport(
            message="Update ReleaseFile units", code="update.release_file"
        ) as pb:
            async for d_content in self.items():
                if isinstance(d_content.content, ReleaseFile):
                    release_file = d_content.content
                    da_names = {
                        os.path.basename(da.relative_path): da for da in d_content.d_artifacts
                    }
                    if "Release" in da_names:
                        if "Release.gpg" in da_names:
                            if self.gpgkey:
                                with NamedTemporaryFile() as tmp_file:
                                    tmp_file.write(da_names["Release"].artifact.file.read())
                                    tmp_file.flush()
                                    verified = self.gpg.verify_file(
                                        da_names["Release.gpg"].artifact.file, tmp_file.name
                                    )
                                if verified.valid:
                                    log.info(_("Verification of Release successful."))
                                    release_file_artifact = da_names["Release"].artifact
                                    release_file.relative_path = da_names["Release"].relative_path
                                else:
                                    log.warning(_("Verification of Release failed. Dropping it."))
                                    d_content.d_artifacts.remove(da_names.pop("Release"))
                                    d_content.d_artifacts.remove(da_names.pop("Release.gpg"))
                            else:
                                release_file_artifact = da_names["Release"].artifact
                                release_file.relative_path = da_names["Release"].relative_path
                        else:
                            if self.gpgkey:
                                d_content.d_artifacts.delete(da_names["Release"])
                            else:
                                release_file_artifact = da_names["Release"].artifact
                                release_file.relative_path = da_names["Release"].relative_path
                    else:
                        if "Release.gpg" in da_names:
                            # No need to keep the signature without "Release"
                            d_content.d_artifacts.remove(da_names.pop("Release.gpg"))

                    if "InRelease" in da_names:
                        if self.gpgkey:
                            verified = self.gpg.verify_file(da_names["InRelease"].artifact.file)
                            if verified.valid:
                                log.info(_("Verification of InRelease successful."))
                                release_file_artifact = da_names["InRelease"].artifact
                                release_file.relative_path = da_names["InRelease"].relative_path
                            else:
                                log.warning(_("Verification of InRelease failed. Dropping it."))
                                d_content.d_artifacts.remove(da_names.pop("InRelease"))
                        else:
                            release_file_artifact = da_names["InRelease"].artifact
                            release_file.relative_path = da_names["InRelease"].relative_path

                    if not d_content.d_artifacts:
                        # No (proper) artifacts left -> distribution not found
                        raise NoReleaseFile(distribution=release_file.distribution)

                    release_file.sha256 = release_file_artifact.sha256
                    release_file_dict = deb822.Release(release_file_artifact.file)
                    if "codename" in release_file_dict:
                        release_file.codename = release_file_dict["Codename"]
                    if "suite" in release_file_dict:
                        release_file.suite = release_file_dict["Suite"]

                    if "components" in release_file_dict:
                        release_file.components = release_file_dict["Components"]
                    elif release_file.distribution[-1] == "/":
                        message = (
                            "The Release file for distribution '{}' contains no 'Components' "
                            "field, but since we are dealing with a flat repo, we can continue "
                            "regardless."
                        )
                        log.warning(_(message).format(release_file.distribution))
                        # TODO: Consider not setting the field at all (requires migrations).
                        release_file.components = ""
                    else:
                        raise MissingReleaseFileField(release_file.distribution, "Components")

                    if "architectures" in release_file_dict:
                        release_file.architectures = release_file_dict["Architectures"]
                    elif release_file.distribution[-1] == "/":
                        message = (
                            "The Release file for distribution '{}' contains no 'Architectures' "
                            "field, but since we are dealing with a flat repo, we can extract them "
                            "from the repos single Package index later."
                        )
                        log.warning(_(message).format(release_file.distribution))
                        release_file.architectures = ""
                    else:
                        raise MissingReleaseFileField(release_file.distribution, "Architectures")

                    log.debug(_("Codename: {}").format(release_file.codename))
                    log.debug(_("Components: {}").format(release_file.components))
                    log.debug(_("Architectures: {}").format(release_file.architectures))
                    await pb.aincrement()
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
        async with ProgressReport(
            message="Update PackageIndex units", code="update.packageindex"
        ) as pb:
            async for d_content in self.items():
                if isinstance(d_content.content, PackageIndex):
                    if not d_content.d_artifacts:
                        d_content.content = None
                        d_content.resolve()
                        continue
                    content = d_content.content
                    if not [
                        da for da in d_content.d_artifacts if da.artifact.sha256 == content.sha256
                    ]:
                        # No main_artifact found, uncompress one
                        relative_dir = os.path.dirname(d_content.content.relative_path)
                        filename = _uncompress_artifact(d_content.d_artifacts, relative_dir)
                        da = DeclarativeArtifact(
                            artifact=Artifact.init_and_validate(
                                filename, expected_digests={"sha256": content.sha256}
                            ),
                            url=filename,
                            relative_path=content.relative_path,
                            remote=d_content.d_artifacts[0].remote,
                        )
                        d_content.d_artifacts.append(da)
                        await _save_artifact_blocking(da)
                    await pb.aincrement()
                await self.put(d_content)


def _uncompress_artifact(d_artifacts, relative_dir):
    for d_artifact in d_artifacts:
        ext = os.path.splitext(d_artifact.relative_path)[1]
        if ext == ".gz":
            compressor = gzip
        elif ext == ".bz2":
            compressor = bz2
        elif ext == ".xz":
            compressor = lzma
        else:
            log.info(_("Compression algorithm unknown for extension '{}'.").format(ext))
            continue
        # At this point we have found a file that can be decompressed
        with NamedTemporaryFile(delete=False) as f_out:
            with compressor.open(d_artifact.artifact.file) as f_in:
                shutil.copyfileobj(f_in, f_out)
        return f_out.name
    # Not one artifact was suitable
    raise NoPackageIndexFile(relative_dir=relative_dir)


class DebDropFailedArtifacts(Stage):
    """
    This stage removes failed failsafe artifacts.

    In case we tried to fetch something, but the artifact 404ed, we simply drop it.
    """

    async def run(self):
        """
        Remove None from d_artifacts in DeclarativeContent units.
        """
        async for d_content in self.items():
            d_content.d_artifacts = [
                d_artifact for d_artifact in d_content.d_artifacts if d_artifact.artifact
            ]
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
        self.parsed_url = urlparse(remote.url)

    async def run(self):
        """
        Build and emit `DeclarativeContent` from the Release data.
        """
        if "md5" not in settings.ALLOWED_CONTENT_CHECKSUMS and settings.FORBIDDEN_CHECKSUM_WARNINGS:
            log.warning(_(NO_MD5_WARNING_MESSAGE))

        await asyncio.gather(
            *[self._handle_distribution(dist) for dist in self.remote.distributions.split()]
        )

    async def _create_unit(self, d_content):
        await self.put(d_content)
        return await d_content.resolution()

    def _to_d_artifact(self, relative_path, data=None):
        artifact = Artifact(**_get_checksums(data or {}))
        url_path = os.path.join(self.parsed_url.path, relative_path)
        return DeclarativeFailsafeArtifact(
            artifact=artifact,
            url=urlunparse(self.parsed_url._replace(path=url_path)),
            relative_path=relative_path,
            remote=self.remote,
            deferred_download=False,
        )

    async def _handle_distribution(self, distribution):
        log.info(_('Downloading Release file for distribution: "{}"').format(distribution))
        # Create release_file
        if distribution[-1] == "/":
            release_file_dir = distribution.strip("/")
        else:
            release_file_dir = os.path.join("dists", distribution)
        release_file_dc = DeclarativeContent(
            content=ReleaseFile(distribution=distribution),
            d_artifacts=[
                self._to_d_artifact(os.path.join(release_file_dir, filename))
                for filename in ["Release", "InRelease", "Release.gpg"]
            ],
        )
        release_file = await self._create_unit(release_file_dc)
        if release_file is None:
            return
        # Create release object
        release_unit = Release(
            codename=release_file.codename, suite=release_file.suite, distribution=distribution
        )
        release_dc = DeclarativeContent(content=release_unit)
        release = await self._create_unit(release_dc)
        # Create release architectures
        if release_file.architectures:
            architectures = _filter_split_architectures(
                release_file.architectures, self.remote.architectures, distribution
            )
        elif distribution[-1] == "/":
            message = (
                "The ReleaseFile content unit architecrures are unset for the flat repo with "
                "distribution '{}'. ReleaseArchitecture content creation is deferred!"
            )
            log.warning(_(message).format(distribution))
            architectures = []

        for architecture in architectures:
            release_architecture_dc = DeclarativeContent(
                content=ReleaseArchitecture(architecture=architecture, release=release)
            )
            await self.put(release_architecture_dc)
        # Parse release file
        log.info(_('Parsing Release file at distribution="{}"').format(distribution))
        release_artifact = await _get_main_artifact_blocking(release_file)
        release_file_dict = deb822.Release(release_artifact.file)

        # Retrieve and interpret any 'No-Support-for-Architecture-all' value:
        # We will refer to the presence of 'No-Support-for-Architecture-all: Packages' in a Release
        # file as indicating "hybrid format". For more info, see:
        # https://wiki.debian.org/DebianRepository/Format#No-Support-for-Architecture-all
        no_support_for_arch_all = release_file_dict.get("No-Support-for-Architecture-all", "")
        if no_support_for_arch_all.strip() == "Packages":
            hybrid_format = True
        elif not no_support_for_arch_all:
            hybrid_format = False
        else:
            raise UnknownNoSupportForArchitectureAllValue(
                release_file.relative_path, no_support_for_arch_all
            )

        # collect file references in new dict
        file_references = defaultdict(deb822.Deb822Dict)
        for digest_name in ["SHA512", "SHA256", "SHA1", "MD5sum"]:
            if digest_name in release_file_dict:
                for unit in release_file_dict[digest_name]:
                    file_references[unit["Name"]].update(unit)

        if distribution[-1] == "/":
            # Handle flat repo
            sub_tasks = [self._handle_flat_repo(file_references, release_file, release)]
        else:
            # Handle components
            sub_tasks = [
                self._handle_component(
                    component,
                    release,
                    release_file,
                    file_references,
                    architectures,
                    hybrid_format,
                )
                for component in _filter_split_components(
                    release_file.components, self.remote.components, distribution
                )
            ]
        await asyncio.gather(*sub_tasks)

    async def _handle_component(
        self,
        component,
        release,
        release_file,
        file_references,
        architectures,
        hybrid_format,
    ):
        # Create release_component
        release_component_dc = DeclarativeContent(
            content=ReleaseComponent(component=component, release=release)
        )
        release_component = await self._create_unit(release_component_dc)

        # If we are dealing with a "hybrid format", try handling any architecture='all' indices
        # first. That way, we can recover the special case, where a partial mirror does not mirror
        # this index inspite of indicating "hybrid format" in the mirrored metadata.
        if hybrid_format and "all" in architectures:
            architectures.remove("all")
            try:
                await self._handle_package_index(
                    release_file=release_file,
                    release_component=release_component,
                    architecture="all",
                    file_references=file_references,
                    hybrid_format=hybrid_format,
                )
            except NoPackageIndexFile as exception:
                message = (
                    "The Release file at '{}' advertised 'No-Support-for-Architecture-all: "
                    "Packages', however the binary-all index at '{}' appears to be missing! "
                    "Defaulting back to old style repo format handling."
                )
                log.warning(_(message).format(release_file.relative_path, exception.relative_dir))
                # We flip hybrid_format to False, and remove 'all' from the list of architectures to
                # signal "old style repo format" to the rest of the sync:
                hybrid_format = False
                release_file.architectures = " ".join(
                    [x for x in release_file.architectures.split() if x != "all"]
                )

        pending_tasks = []
        # Handle package indices
        pending_tasks.extend(
            [
                self._handle_package_index(
                    release_file=release_file,
                    release_component=release_component,
                    architecture=architecture,
                    file_references=file_references,
                    hybrid_format=hybrid_format,
                )
                for architecture in architectures
            ]
        )
        # Handle installer package indices
        if self.remote.sync_udebs:
            pending_tasks.extend(
                [
                    self._handle_package_index(
                        release_file=release_file,
                        release_component=release_component,
                        architecture=architecture,
                        file_references=file_references,
                        infix="debian-installer",
                    )
                    for architecture in architectures
                ]
            )
        # Handle installer file indices
        if self.remote.sync_installer:
            pending_tasks.extend(
                [
                    self._handle_installer_file_index(
                        release_file, release_component, architecture, file_references
                    )
                    for architecture in architectures
                ]
            )
        if self.remote.sync_sources:
            raise NotImplementedError("Syncing source repositories is not yet implemented.")
        await asyncio.gather(*pending_tasks)

    async def _handle_flat_repo(self, file_references, release_file, release):
        # We are creating a component so the flat repo can be published as a structured repo!
        release_component_dc = DeclarativeContent(
            content=ReleaseComponent(component="flat-repo-component", release=release)
        )
        release_component = await self._create_unit(release_component_dc)
        pending_tasks = []

        # Handle single package index
        pending_tasks.append(
            self._handle_package_index(
                release_file=release_file,
                release_component=release_component,
                architecture="",
                file_references=file_references,
                release=release,
            )
        )

        # Handle source package index
        if self.remote.sync_sources:
            raise NotImplementedError("Syncing source repositories is not yet implemented.")

        # Await all tasks
        await asyncio.gather(*pending_tasks)

    async def _handle_package_index(
        self,
        release_file,
        release_component,
        architecture,
        file_references,
        infix="",
        release=None,
        hybrid_format=False,
    ):
        # Create package_index
        release_base_path = os.path.dirname(release_file.relative_path)
        # Package index directory relative to the release file:
        release_file_package_index_dir = (
            os.path.join(release_component.plain_component, infix, "binary-{}".format(architecture))
            if release_file.distribution[-1] != "/"
            else ""
        )
        # Package index directory relative to the repository root:
        package_index_dir = os.path.join(release_base_path, release_file_package_index_dir)
        d_artifacts = []
        for filename in ["Packages", "Packages.gz", "Packages.xz", "Release"]:
            path = os.path.join(release_file_package_index_dir, filename)
            if path in file_references:
                relative_path = os.path.join(release_base_path, path)
                d_artifacts.append(self._to_d_artifact(relative_path, file_references[path]))
        if not d_artifacts:
            # This case will happen if it is not the case that 'path in file_references' for any of
            # ["Packages", "Packages.gz", "Packages.xz", "Release"]. The only case where this is
            # known to occur is when the remote uses 'sync_udebs = True', but the upstream repo does
            # not contain any debian-installer indices.
            message = (
                "Looking for package indices in '{}', but the Release file does not reference any! "
                "Ignoring."
            )
            log.warning(_(message).format(package_index_dir))
            if "debian-installer" in package_index_dir and self.remote.sync_udebs:
                message = (
                    "It looks like the remote is using 'sync_udebs=True', but there is no "
                    "installer package index."
                )
                log.info(_(message))
            return
        relative_path = os.path.join(package_index_dir, "Packages")
        log.info(_('Creating PackageIndex unit with relative_path="{}".').format(relative_path))
        content_unit = PackageIndex(
            release=release_file,
            component=release_component.component,
            architecture=architecture,
            sha256=d_artifacts[0].artifact.sha256,
            relative_path=relative_path,
        )
        package_index = await self._create_unit(
            DeclarativeContent(content=content_unit, d_artifacts=d_artifacts)
        )
        if not package_index:
            if (
                settings.FORCE_IGNORE_MISSING_PACKAGE_INDICES
                or self.remote.ignore_missing_package_indices
            ) and architecture != "all":
                message = "No suitable package index files found in '{}'. Skipping."
                log.info(_(message).format(package_index_dir))
                return
            else:
                raise NoPackageIndexFile(relative_dir=package_index_dir)

        # Interpret policy to download Artifacts or not
        deferred_download = self.remote.policy != Remote.IMMEDIATE
        # parse package_index
        package_futures = []
        package_index_artifact = await _get_main_artifact_blocking(package_index)
        for package_paragraph in deb822.Packages.iter_paragraphs(package_index_artifact.file):
            # Sanity check the architecture from the package paragraph:
            package_paragraph_architecture = package_paragraph["Architecture"]
            if release_file.distribution[-1] == "/":
                if (
                    self.remote.architectures
                    and package_paragraph_architecture != "all"
                    and package_paragraph_architecture not in self.remote.architectures.split()
                ):
                    message = (
                        "Omitting package '{}' with architecture '{}' from flat repo distribution "
                        "'{}', since we are filtering for architectures '{}'!"
                    )
                    log.debug(
                        _(message).format(
                            package_paragraph["Filename"],
                            package_paragraph_architecture,
                            release_file.distribution,
                            self.remote.architectures,
                        )
                    )
                    continue
            # We drop packages if the package_paragraph_architecture != architecture unless that
            # architecture is "all" in a "mixed" (containing all as well as architecture specific
            # packages) package index:
            elif (
                package_paragraph_architecture != "all"
                or "all" in release_file.architectures.split()
            ) and package_paragraph_architecture != architecture:
                if not hybrid_format:
                    message = (
                        "The upstream package index in '{}' contains package '{}' with wrong "
                        "architecture '{}'. Skipping!"
                    )
                    log.warning(
                        _(message).format(
                            package_index_dir,
                            package_paragraph["Filename"],
                            package_paragraph_architecture,
                        )
                    )
                continue

            try:
                package_relpath = os.path.normpath(package_paragraph["Filename"])
                package_sha256 = package_paragraph["sha256"]
                if package_relpath.endswith(".deb"):
                    package_class = Package
                    serializer_class = Package822Serializer
                elif package_relpath.endswith(".udeb"):
                    package_class = InstallerPackage
                    serializer_class = InstallerPackage822Serializer
                log.debug(_("Downloading package {}").format(package_paragraph["Package"]))
                serializer = serializer_class.from822(data=package_paragraph)
                serializer.is_valid(raise_exception=True)
                package_content_unit = package_class(
                    relative_path=package_relpath,
                    sha256=package_sha256,
                    **serializer.validated_data,
                )
                package_path = os.path.join(self.parsed_url.path, package_relpath)
                package_da = DeclarativeArtifact(
                    artifact=Artifact(
                        size=int(package_paragraph["Size"]), **_get_checksums(package_paragraph)
                    ),
                    url=urlunparse(self.parsed_url._replace(path=package_path)),
                    relative_path=package_relpath,
                    remote=self.remote,
                    deferred_download=deferred_download,
                )
                package_dc = DeclarativeContent(
                    content=package_content_unit, d_artifacts=[package_da]
                )
                package_futures.append(package_dc)
                await self.put(package_dc)
            except KeyError:
                log.warning(_("Ignoring invalid package paragraph. {}").format(package_paragraph))
        # Assign packages to this release_component
        package_architectures = set([])
        for package_future in package_futures:
            package = await package_future.resolution()
            if not isinstance(package, Package):
                # TODO repeat this for installer packages
                continue
            package_release_component_dc = DeclarativeContent(
                content=PackageReleaseComponent(
                    package=package, release_component=release_component
                )
            )
            await self.put(package_release_component_dc)
            if release_file.distribution[-1] == "/":
                package_architectures.add(package.architecture)

        # For flat repos we may still need to create ReleaseArchitecture content:
        if release_file.distribution[-1] == "/":
            if release_file.architectures:
                for architecture in package_architectures:
                    if architecture not in release_file.architectures.split():
                        message = (
                            "The flat repo with distribution '{}' contains packages with "
                            "architecture '{}' but this is not included in the ReleaseFile's "
                            "architectures field '{}'!"
                        )
                        log.warning(
                            _(message).format(
                                release_file.distribution, architecture, release_file.architectures
                            )
                        )
                        message = "Creating additional ReleaseArchitecture for architecture '{}'!"
                        log.warning(_(message).format(architecture))
                        release_architecture_dc = DeclarativeContent(
                            content=ReleaseArchitecture(architecture=architecture, release=release)
                        )
                        await self.put(release_architecture_dc)
            else:
                package_architectures_string = " ".join(package_architectures)
                message = (
                    "The ReleaseFile of the flat repo with distribution '{}' has an empty "
                    "architectures field!"
                )
                log.warning(_(message).format(release_file.distribution))
                message = (
                    "Creating ReleaseArchitecture content for architectures '{}', extracted from "
                    "the synced packages."
                )
                log.warning(_(message).format(package_architectures_string))
                for architecture in package_architectures:
                    release_architecture_dc = DeclarativeContent(
                        content=ReleaseArchitecture(architecture=architecture, release=release)
                    )
                    await self.put(release_architecture_dc)

    async def _handle_installer_file_index(
        self, release_file, release_component, architecture, file_references
    ):
        # Create installer file index
        release_base_path = os.path.dirname(release_file.relative_path)
        installer_file_index_dir = os.path.join(
            release_component.plain_component,
            "installer-{}".format(architecture),
            "current",
            "images",
        )
        d_artifacts = []
        for filename in InstallerFileIndex.FILE_ALGORITHM.keys():
            path = os.path.join(installer_file_index_dir, filename)
            if path in file_references:
                relative_path = os.path.join(release_base_path, path)
                d_artifacts.append(self._to_d_artifact(relative_path, file_references[path]))
        if not d_artifacts:
            return
        log.info(_("Downloading installer files from {}").format(installer_file_index_dir))
        content_unit = InstallerFileIndex(
            release=release_file,
            component=release_component.component,
            architecture=architecture,
            sha256=d_artifacts[0].artifact.sha256,
            relative_path=os.path.join(release_base_path, installer_file_index_dir),
        )
        d_content = DeclarativeContent(content=content_unit, d_artifacts=d_artifacts)
        installer_file_index = await self._create_unit(d_content)
        # Interpret policy to download Artifacts or not
        deferred_download = self.remote.policy != Remote.IMMEDIATE
        # Parse installer file index
        file_list = defaultdict(dict)
        for content_artifact in installer_file_index.contentartifact_set.all():
            algorithm = InstallerFileIndex.FILE_ALGORITHM.get(
                os.path.basename(content_artifact.relative_path)
            )
            if not algorithm:
                continue
            for line in content_artifact.artifact.file:
                digest, filename = line.decode().strip().split(maxsplit=1)
                filename = os.path.normpath(filename)
                if filename in InstallerFileIndex.FILE_ALGORITHM:  # strangely they may appear here
                    continue
                file_list[filename][algorithm] = digest

        for filename, digests in file_list.items():
            relpath = os.path.join(installer_file_index.relative_path, filename)
            urlpath = os.path.join(self.parsed_url.path, relpath)
            content_unit = GenericContent(sha256=digests["sha256"], relative_path=relpath)
            d_artifact = DeclarativeArtifact(
                artifact=Artifact(**digests),
                url=urlunparse(self.parsed_url._replace(path=urlpath)),
                relative_path=relpath,
                remote=self.remote,
                deferred_download=deferred_download,
            )
            d_content = DeclarativeContent(content=content_unit, d_artifacts=[d_artifact])
            await self.put(d_content)

    async def _handle_translation_files(self, release_file, release_component, file_references):
        translation_dir = os.path.join(release_component.plain_component, "i18n")
        paths = [path for path in file_references.keys() if path.startswith(translation_dir)]
        translations = {}
        for path in paths:
            relative_path = os.path.join(os.path.dirname(release_file.relative_path), path)
            d_artifact = self._to_d_artifact(relative_path, file_references[path])
            key, ext = os.path.splitext(relative_path)
            if key not in translations:
                translations[key] = {"sha256": None, "d_artifacts": []}
            if not ext:
                translations[key]["sha256"] = d_artifact.artifact.sha256
            translations[key]["d_artifacts"].append(d_artifact)

        for relative_path, translation in translations.items():
            content_unit = GenericContent(sha256=translation["sha256"], relative_path=relative_path)
            await self.put(
                DeclarativeContent(content=content_unit, d_artifacts=translation["d_artifacts"])
            )


@sync_to_async
def _get_main_artifact_blocking(content):
    return content.main_artifact


@sync_to_async
def _save_artifact_blocking(d_artifact):
    """
    Call with await!
    """
    try:
        d_artifact.artifact.save()
    except IntegrityError:
        d_artifact.artifact = Artifact.objects.get(sha256=d_artifact.artifact.sha256)
        d_artifact.artifact.touch()


def _get_checksums(unit_dict):
    """
    Filters the unit_dict provided to retain only checksum fields present in the
    CHECKSUM_TYPE_MAP and permitted by ALLOWED_CONTENT_CHECKSUMS. Also translates the
    retained keys from Debian checksum field name to Pulp checksum type name.

    For example, if the following is in the unit_dict:
        'SHA256': '0b412f7b1a25087871c3e9f2743f4d90b9b025e415f825483b6f6a197d11d409',

    The return dict would contain:
        'sha256': '0b412f7b1a25087871c3e9f2743f4d90b9b025e415f825483b6f6a197d11d409',

    This key translation is defined by the CHECKSUM_TYPE_MAP.
    """
    return {
        checksum_type: unit_dict[deb_field]
        for checksum_type, deb_field in CHECKSUM_TYPE_MAP.items()
        if checksum_type in settings.ALLOWED_CONTENT_CHECKSUMS and deb_field in unit_dict
    }
