import asyncio
import aiohttp
import os
import shutil
import bz2
import gzip
import lzma
import subprocess
import gnupg
import hashlib

from asgiref.sync import sync_to_async
from collections import defaultdict
from functools import wraps
from tempfile import NamedTemporaryFile
from debian import deb822
from urllib.parse import quote, urlparse, urlunparse
from django.conf import settings
from django.db.utils import IntegrityError

from pulpcore.plugin.exceptions import DigestValidationError
from rest_framework.exceptions import ValidationError


from pulpcore.plugin.models import (
    Artifact,
    ProgressReport,
    Remote,
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
from pulpcore.plugin.util import get_domain

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
    AptRepository,
    SourceIndex,
    SourcePackage,
    SourcePackageReleaseComponent,
)

from pulp_deb.app.serializers import (
    InstallerPackage822Serializer,
    Package822Serializer,
    DscFile822Serializer,
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

    def __init__(self, url, *args, **kwargs):
        """
        Exception to signal, that no file representing a release is present.
        """
        super().__init__(
            "Could not find a Release file at '{}', try checking the 'url' and "
            "'distributions' option on your remote".format(url),
            *args,
            **kwargs,
        )


class NoValidSignatureForKey(Exception):
    """
    Exception to signal, that verification of release file with provided GPG key fails.
    """

    def __init__(self, url, *args, **kwargs):
        """
        Exception to signal, that verification of release file with provided GPG key fails.
        """
        super().__init__(
            "Unable to verify any Release files from '{}' using the GPG key provided.".format(url),
            *args,
            **kwargs,
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


def synchronize(remote_pk, repository_pk, mirror, optimize):
    """
    Sync content from the remote repository.

    Create a new version of the repository that is synchronized with the remote.

    Args:
        remote_pk (str): The remote PK.
        repository_pk (str): The repository PK.
        mirror (bool): True for mirror mode, False for additive.
        optimize (bool): Optimize mode.

    Raises:
        ValueError: If the remote does not specify a URL to sync

    """
    remote = AptRemote.objects.get(pk=remote_pk)
    repository = AptRepository.objects.get(pk=repository_pk)
    previous_repo_version = repository.latest_version()

    if not remote.url:
        raise ValueError(_("A remote must have a url specified to synchronize."))

    if optimize and mirror:
        skip_dist = []
        for dist in remote.distributions.split():
            artifact_set_sha256 = get_distribution_release_file_artifact_set_sha256(dist, remote)
            previous_release_file = get_previous_release_file(previous_repo_version, dist)
            if (
                previous_release_file
                and previous_release_file.artifact_set_sha256 == artifact_set_sha256
            ):
                skip_dist.append(True)
            else:
                skip_dist.append(False)

        remote_options = gen_remote_options(remote)
        if not previous_repo_version.info:
            optimize = False
        elif not previous_repo_version.info["remote_options"] == remote_options:
            optimize = False
        elif not previous_repo_version.info["sync_options"]["mirror"] and mirror:
            optimize = False

        if all(skip_dist) and optimize:
            log.info("No change in ReleaseFiles detected. Skipping sync.")
            with ProgressReport(
                message="Skipping sync (no changes for any ReleaseFile)",
                code="sync.complete_skip.was_skipped",
            ) as pb:
                asyncio.run(pb.aincrement())
            return

    first_stage = DebFirstStage(remote, optimize, mirror, previous_repo_version)
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
        self.first_stage.new_version = new_version
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

    @staticmethod
    def _gpg_agent_cleanup(func):
        """Kill gpg-agent for this intances gnupghome after the wrapped call, even on error."""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            finally:
                gpgkey = getattr(self, "gpgkey", None)
                gpg = getattr(self, "gpg", None)
                homedir = getattr(gpg, "gnupghome", None) if gpg is not None else None
                if gpgkey and homedir:
                    try:
                        subprocess.run(
                            ["/usr/bin/gpgconf", "--homedir", homedir, "--kill", "gpg-agent"],
                            check=False,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    except Exception:
                        # cleanup must never mask the original error path
                        pass
        return wrapper

    @_gpg_agent_cleanup
    def __init__(self, remote, *args, **kwargs):
        """Initialize DebUpdateReleaseFileAttributes stage."""
        super().__init__(*args, **kwargs)
        self.remote = remote
        self.gpgkey = remote.gpgkey
        self.gpg = None
        if self.gpgkey:
            gnupghome = os.path.join(os.getcwd(), "gpg-home")
            os.makedirs(gnupghome, exist_ok=True)
            self.gpg = gnupg.GPG(gpgbinary="/usr/bin/gpg", gnupghome=gnupghome)
            import_res = self.gpg.import_keys(self.gpgkey)
            if import_res.count == 0:
                log.warning(_("Key import failed."))

    async def run(self):
        """
        Parse ReleaseFile content units, verify GPG if needed, and update attributes.
        """
        async with ProgressReport(
            message="Update ReleaseFile units", code="update.release_file"
        ) as pb:
            async for d_content in self.items():
                release_file = d_content.content
                if isinstance(release_file, ReleaseFile):
                    await self.process_release_file_d_content(d_content, pb)

                await self.put(d_content)

    async def process_release_file_d_content(self, d_content, pb):
        """
        Orchestrates the steps for a single ReleaseFile item.
        """
        release_da, release_gpg_da, inrelease_da = _collect_release_artifacts(d_content)

        release_artifact = None
        if self.gpg:
            release_artifact = self.verify_gpg_artifacts(
                d_content, release_da, release_gpg_da, inrelease_da
            )
        else:
            # If no gpgkey, pick main artifact in an order: InRelease => Release => None
            if inrelease_da:
                release_artifact = inrelease_da.artifact
                d_content.content.relative_path = inrelease_da.relative_path
            elif release_da:
                release_artifact = release_da.artifact
                d_content.content.relative_path = release_da.relative_path

        # If there isn't a valid release
        if not release_artifact:
            if release_da in d_content.d_artifacts:
                d_content.d_artifacts.remove(release_da)
            if release_gpg_da in d_content.d_artifacts:
                d_content.d_artifacts.remove(release_gpg_da)
            if inrelease_da in d_content.d_artifacts:
                d_content.d_artifacts.remove(inrelease_da)
            raise NoReleaseFile(url=os.path.join(self.remote.url, d_content.content.relative_path))

        d_content.content.sha256 = release_artifact.sha256
        d_content.content.artifact_set_sha256 = _get_artifact_set_sha256(
            d_content, ReleaseFile.SUPPORTED_ARTIFACTS
        )
        _parse_release_file_attributes(d_content, release_artifact)
        await pb.aincrement()

    def verify_gpg_artifacts(self, d_content, release_da, release_gpg_da, inrelease_da):
        """
        Handle GPG verification. Returns the main artifact or raises and exception.
        """
        if inrelease_da:
            if self.verify_single_file(inrelease_da.artifact):
                log.info(_("Verification of InRelease successful."))
                d_content.content.relative_path = inrelease_da.relative_path
                return inrelease_da.artifact
            else:
                log.warning(_("Verification of InRelease failed. Removing it."))
                d_content.d_artifacts.remove(inrelease_da)

        if release_da and release_gpg_da:
            if self.verify_detached_signature(release_da.artifact, release_gpg_da.artifact):
                log.info(_("Verification of Release successful."))
                d_content.content.relative_path = release_da.relative_path
                return release_da.artifact
            else:
                log.warning(_("Verification of Release + Release.gpg failed. Removing it."))
                d_content.d_artifacts.remove(release_da)
                d_content.d_artifacts.remove(release_gpg_da)
        elif release_da:
            log.warning(_("Release found but no signature and gpgkey was provided. Removing it."))
            d_content.d_artifacts.remove(release_da)

        raise NoValidSignatureForKey(url=os.path.join(self.remote.url, "Release"))

    def verify_single_file(self, artifact):
        """
        Attempt to verify an inline-signed file (InRelease).
        Returns True if valid, False otherwise.
        """
        with artifact.file.open("rb") as inrelease_fh:
            verified = self.gpg.verify_file(inrelease_fh)
        return bool(verified.valid)

    def verify_detached_signature(self, release_artifact, release_gpg_artifact):
        """
        Attempt to verify a detached signature with "Release" and "Release.gpg".
        Return True if valid, False otherwise.
        """
        with NamedTemporaryFile() as tmp_file:
            with release_artifact.file.open("rb") as rel_fh:
                tmp_file.write(rel_fh.read())
            tmp_file.flush()

            with release_gpg_artifact.file.open("rb") as detached_fh:
                verified = self.gpg.verify_file(detached_fh, tmp_file.name)
        return bool(verified.valid)


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
                if isinstance(d_content.content, (PackageIndex, SourceIndex)):
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

                        try:
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
                        finally:
                            # Ensure the uncompressed file is deleted after usage
                            if os.path.exists(filename):
                                os.remove(filename)
                    content.artifact_set_sha256 = _get_artifact_set_sha256(
                        d_content, PackageIndex.SUPPORTED_ARTIFACTS
                    )
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

    def __init__(self, remote, optimize, mirror, previous_repo_version, *args, **kwargs):
        """
        The first stage of a pulp_deb sync pipeline.

        Args:
            remote (AptRemote): The remote data to be used when syncing
            optimize (Boolean): If optimize mode is enabled or not
            previous_repo_version repository (RepositoryVersion): The previous RepositoryVersion.
        """
        super().__init__(*args, **kwargs)
        self.remote = remote
        self.optimize = optimize
        self.previous_repo_version = previous_repo_version
        self.sync_info = defaultdict()
        self.sync_info["remote_options"] = gen_remote_options(self.remote)
        self.sync_info["sync_options"] = {
            "optimize": optimize,
            "mirror": mirror,
        }
        self.parsed_url = urlparse(remote.url)
        if self.optimize:
            previous_sync_info = defaultdict(dict, self.previous_repo_version.info)
            if not previous_sync_info:
                log.info(_("Setting optimize=False since there is no previous_sync_info."))
                self.optimize = False
            elif not previous_sync_info["remote_options"] == self.sync_info["remote_options"]:
                log.info(_("Setting optimize=False since the remote options have changed."))
                self.optimize = False
            elif mirror and not previous_sync_info["sync_options"]["mirror"]:
                log.info(_("Setting optimize=False since this sync switches to mirror=True."))
                self.optimize = False
            # TODO: https://github.com/pulp/pulp_deb/issues/631
            if mirror:
                log.info(_("Falling back to optimize=False behaviour since mirror=True is set!"))
                log.info(_("See https://github.com/pulp/pulp_deb/issues/631 for more information."))
                self.optimize = False
                self.sync_info["sync_options"]["optimize"] = False

    async def run(self):
        """
        Build and emit `DeclarativeContent` from the Release data.
        """
        if "md5" not in settings.ALLOWED_CONTENT_CHECKSUMS and settings.FORBIDDEN_CHECKSUM_WARNINGS:
            log.warning(_(NO_MD5_WARNING_MESSAGE))

        await asyncio.gather(
            *[self._handle_distribution(dist) for dist in self.remote.distributions.split()]
        )

        self.new_version.info = self.sync_info

    async def _create_unit(self, d_content):
        await self.put(d_content)
        return await d_content.resolution()

    def _to_d_artifact(self, relative_path, data=None):
        artifact = Artifact(**_get_checksums(data or {}))
        url_path = quote(os.path.join(self.parsed_url.path, relative_path), safe=":/")
        return DeclarativeFailsafeArtifact(
            artifact=artifact,
            url=urlunparse(self.parsed_url._replace(path=url_path)),
            relative_path=relative_path,
            remote=self.remote,
            deferred_download=False,
        )

    async def _handle_distribution(self, distribution):
        is_flat = distribution.endswith("/")
        stored_distribution = "flat-repo" if is_flat else distribution

        log.info(_('Downloading Release file for distribution: "{}"').format(distribution))
        # Create release_file
        if is_flat:
            upstream_file_dir = distribution.strip("/")
        else:
            upstream_file_dir = os.path.join("dists", distribution)
        release_file_dc = DeclarativeContent(
            content=ReleaseFile(distribution=stored_distribution, relative_path=upstream_file_dir),
            d_artifacts=[
                self._to_d_artifact(os.path.join(upstream_file_dir, filename))
                for filename in ReleaseFile.SUPPORTED_ARTIFACTS
            ],
        )
        release_file = await self._create_unit(release_file_dc)
        if release_file is None:
            return
        if self.optimize:
            previous_release_file = await _get_previous_release_file(
                self.previous_repo_version, stored_distribution
            )
            if previous_release_file.artifact_set_sha256 == release_file.artifact_set_sha256:
                await _readd_previous_package_indices(
                    self.previous_repo_version, self.new_version, stored_distribution
                )
                message = 'ReleaseFile has not changed for distribution="{}". Skipping.'
                log.info(_(message).format(distribution))
                async with ProgressReport(
                    message="Skipping ReleaseFile sync (no change from previous sync)",
                    code="sync.release_file.was_skipped",
                ) as pb:
                    await pb.aincrement()
                return

        # Parse release file
        log.info(_('Parsing Release file at distribution="{}"').format(distribution))
        release_artifact = await _get_main_artifact_blocking(release_file)
        release_file_dict = deb822.Release(release_artifact.file)

        release_fields = {
            "codename": release_file.codename,
            "suite": release_file.suite,
            "distribution": stored_distribution,
        }

        if "version" in release_file_dict:
            release_fields["version"] = release_file_dict["Version"]
        if "origin" in release_file_dict:
            release_fields["origin"] = release_file_dict["Origin"]
        if "label" in release_file_dict:
            release_fields["label"] = release_file_dict["Label"]
        if "description" in release_file_dict:
            release_fields["description"] = release_file_dict["Description"]

        await self.put(DeclarativeContent(content=Release(**release_fields)))

        # Create release architectures
        if is_flat:
            message = (
                "The ReleaseFile content unit architectures are unset for the flat repo with "
                "distribution '{}'. ReleaseArchitecture content creation is deferred!"
            )
            log.warning(_(message).format(distribution))
            architectures = []
        elif release_file.architectures:
            architectures = _filter_split_architectures(
                release_file.architectures, self.remote.architectures, distribution
            )

        for architecture in architectures:
            release_architecture_dc = DeclarativeContent(
                content=ReleaseArchitecture(architecture=architecture, distribution=distribution)
            )
            await self.put(release_architecture_dc)

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

        if is_flat:
            # Handle flat repo
            sub_tasks = [
                self._handle_flat_repo(
                    file_references,
                    release_file,
                    distribution=stored_distribution,
                    upstream_dist_path=upstream_file_dir,
                )
            ]
        else:
            # Handle components
            sub_tasks = [
                self._handle_component(
                    component,
                    distribution,
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
        distribution,
        release_file,
        file_references,
        architectures,
        hybrid_format,
    ):
        # Create release_component
        release_component_dc = DeclarativeContent(
            content=ReleaseComponent(component=component, distribution=distribution)
        )
        release_component = await self._create_unit(release_component_dc)

        # If we are dealing with a "hybrid format", try handling any architecture='all' indices
        # first. That way, we can recover the special case, where a partial mirror does not mirror
        # this index inspite of indicating "hybrid format" in the mirrored metadata.
        if hybrid_format and "all" in architectures:
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

        # Putting this here because it fixes an issue where debian packages with the parameter
        # architectures='all' are missing after sync/publish. It is not really clear why and
        # needs investigation once there are tests for this issue. Best guess it hasis something do
        # with the asynchronous handling of the tasks and removing something from a dict without
        # a copy.
        if hybrid_format and "all" in architectures:
            architectures.remove("all")

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
        # Handle source indices
        if self.remote.sync_sources:
            pending_tasks.extend(
                [self._handle_source_index(release_file, release_component, file_references)]
            )
        await asyncio.gather(*pending_tasks)

    async def _handle_flat_repo(
        self, file_references, release_file, distribution, upstream_dist_path
    ):
        # We are creating a component so the flat repo can be published as a structured repo!
        release_component_dc = DeclarativeContent(
            content=ReleaseComponent(component="flat-repo-component", distribution=distribution)
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
                distribution=distribution,
                is_flat=True,
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
        distribution=None,
        hybrid_format=False,
        is_flat=False,
    ):
        if is_flat:
            release_file_package_index_dir = ""
        else:
            release_file_package_index_dir = os.path.join(
                release_component.plain_component,
                infix,
                f"binary-{architecture}",
            )
        # Create package_index
        release_base_path = os.path.dirname(release_file.relative_path)

        # Package index directory relative to the repository root:
        package_index_dir = os.path.join(release_base_path, release_file_package_index_dir)
        d_artifacts = []
        for filename in PackageIndex.SUPPORTED_ARTIFACTS:
            if filename == "Release" and is_flat:
                continue
            path = os.path.join(release_file_package_index_dir, filename)
            if path in file_references:
                relative_path = os.path.join(release_base_path, path)
                d_artifacts.append(self._to_d_artifact(relative_path, file_references[path]))
        if not d_artifacts:
            # This case will happen if it is not the case that 'path in file_references' for any of
            # PackageIndex.SUPPORTED_ARTIFACTS. The only case where this is known to occur is when
            # the remote uses 'sync_udebs = True', but the upstream repo does not contain any
            # debian-installer indices.
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

        if self.optimize:
            previous_package_index = await _get_previous_package_index(
                self.previous_repo_version, relative_path
            )
            if previous_package_index.artifact_set_sha256 == package_index.artifact_set_sha256:
                message = 'PackageIndex has not changed for relative_path="{}". Skipped.'
                log.info(_(message).format(relative_path))
                async with ProgressReport(
                    message="Skipping PackageIndex processing (no change from previous sync)",
                    code="sync.package_index.was_skipped",
                ) as pb:
                    await pb.aincrement()
                return

        # Interpret policy to download Artifacts or not
        deferred_download = self.remote.policy != Remote.IMMEDIATE
        # parse package_index
        package_futures = []
        package_index_artifact = await _get_main_artifact_blocking(package_index)
        for package_paragraph in deb822.Packages.iter_paragraphs(
            package_index_artifact.file, use_apt_pkg=False
        ):
            # Sanity check the architecture from the package paragraph:
            package_paragraph_architecture = package_paragraph["Architecture"]
            if is_flat:
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
                package_path = quote(os.path.join(self.parsed_url.path, package_relpath), safe=":/")
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
            if is_flat:
                package_architectures.add(package.architecture)

        # For flat repos we may still need to create ReleaseArchitecture content:
        if is_flat:
            if release_file.architectures:
                for architecture in package_architectures:
                    log.debug(
                        "Flat Repo Architecture handling: "
                        f"Creating ReleaseArchitecture for architecture {architecture}."
                    )
                    release_architecture_dc = DeclarativeContent(
                        content=ReleaseArchitecture(
                            architecture=architecture, distribution="flat-repo"
                        )
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
                        content=ReleaseArchitecture(
                            architecture=architecture, distribution="flat-repo"
                        )
                    )
                    await self.put(release_architecture_dc)

    async def _handle_source_index(self, release_file, release_component, file_references):
        # Create source_index
        release_base_path = os.path.dirname(release_file.relative_path)
        if release_file.distribution[-1] == "/":
            # Flat repo format
            source_index_dir = ""
        else:
            source_index_dir = os.path.join(release_component.plain_component, "source")
        d_artifacts = []
        for filename in ["Sources", "Sources.gz", "Sources.xz", "Release"]:
            path = os.path.join(source_index_dir, filename)
            if path in file_references:
                relative_path = os.path.join(release_base_path, path)
                d_artifacts.append(self._to_d_artifact(relative_path, file_references[path]))
        if not d_artifacts:
            # No reference here, skip this component
            return
        log.info(_("Downloading: {}/Sources").format(source_index_dir))
        content_unit = SourceIndex(
            release=release_file,
            component=release_component.component,
            sha256=d_artifacts[0].artifact.sha256,
            relative_path=os.path.join(release_base_path, source_index_dir, "Sources"),
        )
        source_index = await self._create_unit(
            DeclarativeContent(content=content_unit, d_artifacts=d_artifacts)
        )
        if not source_index:
            log.info(
                _("No sources index for component {}. Skipping.").format(
                    release_component.component
                )
            )
            return
        # Interpret policy to download Artifacts or not
        deferred_download = self.remote.policy != Remote.IMMEDIATE

        # parse source_index
        source_package_content_futures = []
        source_index_artifact = await _get_main_artifact_blocking(source_index)
        for source_paragraph in deb822.Sources.iter_paragraphs(
            source_index_artifact.file, use_apt_pkg=False
        ):
            try:
                source_dir = source_paragraph["Directory"]
                source_relpath = os.path.join(source_dir, "blah")
                serializer = DscFile822Serializer.from822(data=source_paragraph)
                serializer.is_valid(raise_exception=True)
                source_content_unit = SourcePackage(
                    relative_path=source_relpath,
                    **serializer.validated_data,
                )
                # Handle the dsc file content
                source_das = []
                for source_file in source_paragraph["Checksums-Sha256"]:
                    source_relpath = os.path.join(source_dir, source_file["name"])
                    log.debug(_("Downloading dsc content file {}.").format(source_file["name"]))

                    source_path = os.path.join(self.parsed_url.path, source_relpath)
                    source_da = DeclarativeArtifact(
                        artifact=Artifact(
                            size=int(source_file["size"]),
                            **_get_source_checksums(source_paragraph, source_file["name"]),
                        ),
                        url=urlunparse(self.parsed_url._replace(path=source_path)),
                        relative_path=source_relpath,
                        remote=self.remote,
                        deferred_download=deferred_download,
                    )
                    source_das.append(source_da)
                source_dc = DeclarativeContent(content=source_content_unit, d_artifacts=source_das)
                source_package_content_futures.append(source_dc)
                await self.put(source_dc)
            except (KeyError, ValidationError):
                log.warning(_("Ignoring invalid source paragraph. {}").format(source_paragraph))
        # Assign dsc files to this release_component
        for source_package_content_future in source_package_content_futures:
            source_package = await source_package_content_future.resolution()
            source_package_release_component_dc = DeclarativeContent(
                content=SourcePackageReleaseComponent(
                    source_package=source_package, release_component=release_component
                )
            )
            await self.put(source_package_release_component_dc)

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
        async for content_artifact in installer_file_index.contentartifact_set.all():
            algorithm = InstallerFileIndex.FILE_ALGORITHM.get(
                os.path.basename(content_artifact.relative_path)
            )
            if not algorithm:
                continue
            for line in await _get_content_artifact_file(content_artifact):
                digest, filename = line.decode().strip().split(maxsplit=1)
                filename = os.path.normpath(filename)
                if filename in InstallerFileIndex.FILE_ALGORITHM:  # strangely they may appear here
                    continue
                file_list[filename][algorithm] = digest

        for filename, digests in file_list.items():
            relpath = os.path.join(installer_file_index.relative_path, filename)
            urlpath = quote(os.path.join(self.parsed_url.path, relpath), safe=":/")
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
def _get_content_artifact_file(content_artifact):
    return content_artifact.artifact.file


@sync_to_async
def _readd_previous_package_indices(previous_version, new_version, distribution):
    new_version.add_content(
        previous_version.get_content(
            PackageIndex.objects.filter(relative_path__contains=distribution)
        )
    )
    new_version.add_content(
        previous_version.get_content(
            InstallerFileIndex.objects.filter(relative_path__contains=distribution)
        )
    )


def get_previous_release_file(previous_version, distribution):
    previous_release_file_qs = previous_version.get_content(
        ReleaseFile.objects.filter(distribution=distribution)
    )
    if previous_release_file_qs.count() > 1:
        message = "Previous ReleaseFile count: {}. There should only be one."
        raise Exception(message.format(previous_release_file_qs.count()))
    return previous_release_file_qs.first()


_get_previous_release_file = sync_to_async(get_previous_release_file)


@sync_to_async
def _get_previous_package_index(previous_version, relative_path):
    previous_package_index_qs = previous_version.get_content(
        PackageIndex.objects.filter(relative_path=relative_path)
    )
    if previous_package_index_qs.count() > 1:
        message = "Previous PackageIndex count: {}. There should only be one."
        raise Exception(message.format(previous_package_index_qs.count()))
    return previous_package_index_qs.first()


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
        d_artifact.artifact = Artifact.objects.get(
            sha256=d_artifact.artifact.sha256, pulp_domain=get_domain()
        )
        d_artifact.artifact.touch()


def _collect_release_artifacts(d_content):
    """
    Return (release_da, release_gpg_da, inrelease_da) from d_content.d_artifacts.

    Looks for items whose filename is exactly "Release", "Release.gpg", or "InRelease".
    If not found, return None for that slot.
    """
    da_names = {os.path.basename(da.relative_path): da for da in d_content.d_artifacts}

    return (
        da_names.get("Release", None),
        da_names.get("Release.gpg", None),
        da_names.get("InRelease", None),
    )


def _parse_release_file_attributes(d_content, main_artifact):
    """
    Parse the contents of main_artifact as a 'Release' file and update
    d_content.content.* fields accordingly (e.g. codename, suite, etc.).
    """
    from debian import deb822

    with main_artifact.file.open("rb") as fh:
        release_dict = deb822.Release(fh.read())

    if "codename" in release_dict:
        d_content.content.codename = release_dict["Codename"]
    if "suite" in release_dict:
        d_content.content.suite = release_dict["Suite"]
    if "components" in release_dict:
        d_content.content.components = release_dict["Components"]
    elif "component" in release_dict and settings.PERMISSIVE_SYNC:
        d_content.content.components = release_dict["Component"]
    elif d_content.content.distribution == "flat-repo":
        message = (
            "The Release file for distribution '{}' contains no 'Components' "
            "field, but since we are dealing with a flat repo, we can continue "
            "regardless."
        )
        log.warning(_(message).format(d_content.content.distribution))
        # TODO: Consider not setting the field at all (requires migrations).
        d_content.content.components = ""
    else:
        raise MissingReleaseFileField(d_content.content.distribution, "Components")

    if "architectures" in release_dict:
        d_content.content.architectures = release_dict["Architectures"]
    elif "architecture" in release_dict and settings.PERMISSIVE_SYNC:
        d_content.content.architectures = release_dict["Architecture"]
    elif d_content.content.distribution == "flat-repo":
        message = (
            "The Release file for distribution '{}' contains no 'Architectures' "
            "field, but since we are dealing with a flat repo, we can extract them "
            "from the repos single Package index later."
        )
        log.warning(_(message).format(d_content.content.distribution))
        d_content.content.architectures = ""
    else:
        raise MissingReleaseFileField(d_content.content.distribution, "Architectures")

    log.debug(f"Codename: {d_content.content.codename}")
    log.debug(f"Suite: {d_content.content.suite}")
    log.debug(f"Components: {d_content.content.components}")
    log.debug(f"Architectures: {d_content.content.architectures}")


def _get_artifact_set_sha256(d_content, supported_artifacts):
    """
    Get the checksum of checksums for a set of artifacts associated with a multi artifact
    declarative content.
    """
    sha256_dict = {}
    for da in d_content.d_artifacts:
        filename = os.path.basename(da.relative_path)
        sha256 = da.artifact.sha256
        sha256_dict[filename] = sha256
    hash_string = ""
    for filename in supported_artifacts:
        if filename in sha256_dict:
            hash_string = hash_string + filename + "," + sha256_dict[filename] + "\n"
    return hashlib.sha256(hash_string.encode("utf-8")).hexdigest()


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


def _get_source_checksums(source_paragraph, name):
    """
    Pulls the checksums from the various source file lists in the source index file paragraph
    and filters the result to retain only checksum fields permitted by ALLOWED_CONTENT_CHECKSUMS.

    Required checksums which are missing will cause an exception to be thrown whereas optional
    checksums will be ignored if they are not present.

    The passed in name will be used to match the line item in the list as there are guarantees
    that the order will be preserved from list to list.
    """
    checksums = {}
    # Required
    for source_file in source_paragraph["Files"]:
        if source_file["name"] == name:
            checksums["md5"] = source_file["md5sum"]
    for source_file in source_paragraph["Checksums-Sha256"]:
        if source_file["name"] == name:
            checksums["sha256"] = source_file["sha256"]
    # Optional
    if "Checksums-Sha1" in source_paragraph:
        for source_file in source_paragraph["Checksums-Sha1"]:
            if source_file["name"] == name:
                checksums["sha1"] = source_file["sha1"]
    if "Checksums-Sha512" in source_paragraph:
        for source_file in source_paragraph["Checksums-Sha512"]:
            if source_file["name"] == name:
                checksums["sha512"] = source_file["sha512"]

    return {
        checksum_type: checksums[checksum_type]
        for checksum_type in settings.ALLOWED_CONTENT_CHECKSUMS
        if checksum_type in checksums
    }


def gen_remote_options(remote):
    return {
        "distributions": remote.distributions,
        "components": remote.components,
        "architectures": remote.architectures,
        "policy": remote.policy,
        "sync_sources": remote.sync_sources,
        "sync_udebs": remote.sync_udebs,
        "sync_installer": remote.sync_installer,
        "gpgkey": remote.gpgkey,
        "ignore_missing_package_indices": remote.ignore_missing_package_indices,
    }


def get_distribution_release_file_artifact_set_sha256(distribution, remote):
    log.info(_('Downloading Release file for distribution: "{}"').format(distribution))
    if distribution[-1] == "/":
        release_file_dir = distribution.strip("/")
    else:
        release_file_dir = os.path.join("dists", distribution)

    release_file_info_serialized = {}
    base_url = os.path.join(remote.url, release_file_dir)
    for filename in ReleaseFile.SUPPORTED_ARTIFACTS:
        url = os.path.join(base_url, filename)
        downloader = remote.get_downloader(url=url)
        try:
            result = downloader.fetch()
        except Exception:
            continue
        sha256 = result.artifact_attributes["sha256"]
        release_file_info_serialized[filename] = sha256

    hash_string = ""
    for filename, sha256 in release_file_info_serialized.items():
        hash_string = hash_string + filename + "," + sha256 + "\n"

    return hashlib.sha256(hash_string.encode("utf-8")).hexdigest()
