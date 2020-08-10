from gettext import gettext as _
import logging
import asyncio
import aiohttp
import os
import shutil
import bz2
import gzip
import lzma
import gnupg
from collections import defaultdict
from tempfile import NamedTemporaryFile

from debian import deb822

from urllib.parse import urlparse, urlunparse

from pulpcore.plugin.exceptions import DigestValidationError
from pulpcore.plugin.models import Artifact, ProgressReport, Remote, Repository
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

from pulp_deb.app.serializers import InstallerPackage822Serializer, Package822Serializer


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
        super().__init__(
            "No suitable Package index file found in '{}'.".format(relative_dir), *args, **kwargs
        )

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
                log.info("Artifact not found. Ignored")
            else:
                raise
        except DigestValidationError:
            self.artifact = None
            log.info("Artifact digest not matched. Ignored")


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


def _filter_split(values, filter_list):
    """Filter space separated list and return iterable."""
    value_set = set(values.split())
    if filter_list:
        value_set &= set(filter_list)
    return sorted(value_set)


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
                log.warn("Key import failed.")
            pass

    async def run(self):
        """
        Parse ReleaseFile content units.

        Update release content with information obtained from its artifact.
        """
        with ProgressReport(message="Update ReleaseFile units", code="update.release_file") as pb:
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
                                    log.info("Verification of Release successful.")
                                    release_file_artifact = da_names["Release"].artifact
                                    release_file.relative_path = da_names["Release"].relative_path
                                else:
                                    log.warn("Verification of Release failed. Dropping it.")
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
                                log.info("Verification of InRelease successful.")
                                release_file_artifact = da_names["InRelease"].artifact
                                release_file.relative_path = da_names["InRelease"].relative_path
                            else:
                                log.warn("Verification of InRelease failed. Dropping it.")
                                d_content.d_artifacts.remove(da_names.pop("InRelease"))
                        else:
                            release_file_artifact = da_names["InRelease"].artifact
                            release_file.relative_path = da_names["InRelease"].relative_path

                    if not d_content.d_artifacts:
                        # No (proper) artifacts left -> distribution not found
                        raise NoReleaseFile(distribution=release_file.distribution)

                    release_file.sha256 = release_file_artifact.sha256
                    release_file_dict = deb822.Release(release_file_artifact.file)
                    release_file.codename = release_file_dict["Codename"]
                    if "suite" in release_file_dict:
                        release_file.suite = release_file_dict.get("Suite")
                    # TODO split of extra stuff e.g. : 'updates/main' -> 'main'
                    release_file.components = release_file_dict["Components"]
                    release_file.architectures = release_file_dict["Architectures"]
                    log.debug("Codename: {}".format(release_file.codename))
                    log.debug("Components: {}".format(release_file.components))
                    log.debug("Architectures: {}".format(release_file.architectures))
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
        with ProgressReport(message="Update PackageIndex units", code="update.packageindex") as pb:
            async for d_content in self.items():
                if isinstance(d_content.content, PackageIndex):
                    relative_dir = os.path.dirname(d_content.content.relative_path)
                    if not d_content.d_artifacts:
                        raise NoPackageIndexFile(relative_dir=relative_dir)

                    content = d_content.content
                    if not [
                        da for da in d_content.d_artifacts if da.artifact.sha256 == content.sha256
                    ]:
                        # No main_artifact found, uncompress one
                        filename = _uncompress_artifact(d_content.d_artifacts, relative_dir)
                        da = DeclarativeArtifact(
                            Artifact.init_and_validate(
                                filename, expected_digests={"sha256": content.sha256}
                            ),
                            filename,
                            content.relative_path,
                            d_content.d_artifacts[0].remote,
                        )
                        d_content.d_artifacts.append(da)
                        da.artifact.save()
                        log.info(
                            "*** Expected: {} *** Uncompressed: {} ***".format(
                                content.sha256, da.artifact.sha256
                            )
                        )

                    pb.increment()
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
            log.info("Compression algorithm unknown for extension '{}'.".format(ext))
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
        self.distributions = [
            distribution.strip() for distribution in self.remote.distributions.split()
        ]
        self.num_distributions = len(self.distributions)
        self.components = (
            None
            if self.remote.components is None
            else [component.strip() for component in self.remote.components.split()]
        )
        self.architectures = (
            None
            if self.remote.architectures is None
            else [architecture.strip() for architecture in self.remote.architectures.split()]
        )

    async def run(self):
        """
        Build and emit `DeclarativeContent` from the Release data.
        """
        await asyncio.gather(
            *[self._handle_distribution(distribution) for distribution in self.distributions]
        )

    async def _create_unit(self, d_content):
        # Warning! If d_content batches, this will deadlock.
        await self.put(d_content)
        return await d_content.resolution()

    def _to_d_artifact(self, relative_path, data=None):
        artifact = Artifact(**_get_checksums(data or {}))
        url_path = os.path.join(self.parsed_url.path, relative_path)
        return DeclarativeFailsafeArtifact(
            artifact,
            urlunparse(self.parsed_url._replace(path=url_path)),
            relative_path,
            self.remote,
            deferred_download=False,
        )

    async def _handle_distribution(self, distribution):
        log.info('Downloading Release file for distribution: "{}"'.format(distribution))
        # Create release_file
        release_file_dc = DeclarativeContent(
            content=ReleaseFile(distribution=distribution),
            d_artifacts=[
                self._to_d_artifact(os.path.join("dists", distribution, filename))
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
        for architecture in _filter_split(release_file.architectures, self.architectures):
            release_architecture_dc = DeclarativeContent(
                content=ReleaseArchitecture(architecture=architecture, release=release)
            )
            await self.put(release_architecture_dc)
        # Parse release file
        log.info('Parsing Release file for release: "{}"'.format(release_file.codename))
        release_file_dict = deb822.Release(release_file.main_artifact.file)
        # collect file references in new dict
        file_references = defaultdict(deb822.Deb822Dict)
        for digest_name in ["SHA512", "SHA256", "SHA1", "MD5sum"]:
            if digest_name in release_file_dict:
                for unit in release_file_dict[digest_name]:
                    file_references[unit["Name"]].update(unit)
        await asyncio.gather(
            *[
                self._handle_component(component, release, release_file, file_references)
                for component in _filter_split(release_file.components, self.components)
            ]
        )

    async def _handle_component(self, component, release, release_file, file_references):
        # Create release_component
        release_component_dc = DeclarativeContent(
            content=ReleaseComponent(component=component, release=release)
        )
        release_component = await self._create_unit(release_component_dc)
        architectures = _filter_split(release_file.architectures, self.architectures)
        pending_tasks = []
        # Handle package indices
        pending_tasks.extend(
            [
                self._handle_package_index(
                    release_file, release_component, architecture, file_references
                )
                for architecture in architectures
            ]
        )
        # Handle installer package indices
        if self.remote.sync_udebs:
            pending_tasks.extend(
                [
                    self._handle_package_index(
                        release_file,
                        release_component,
                        architecture,
                        file_references,
                        "debian-installer",
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
        # Handle translation files
        pending_tasks.append(
            self._handle_translation_files(release_file, release_component, file_references)
        )
        if self.remote.sync_sources:
            raise NotImplementedError("Syncing source repositories is not yet implemented.")
        await asyncio.gather(*pending_tasks)

    async def _handle_package_index(
        self, release_file, release_component, architecture, file_references, infix=""
    ):
        # Create package_index
        release_base_path = os.path.dirname(release_file.relative_path)
        package_index_dir = os.path.join(
            release_component.plain_component, infix, "binary-{}".format(architecture)
        )
        d_artifacts = []
        for filename in ["Packages", "Packages.gz", "Packages.xz", "Release"]:
            path = os.path.join(package_index_dir, filename)
            if path in file_references:
                relative_path = os.path.join(release_base_path, path)
                d_artifacts.append(self._to_d_artifact(relative_path, file_references[path]))
        if not d_artifacts:
            # No reference here, skip this component architecture combination
            return
        log.info("Downloading: {}/Packages".format(package_index_dir))
        content_unit = PackageIndex(
            release=release_file,
            component=release_component.component,
            architecture=architecture,
            sha256=d_artifacts[0].artifact.sha256,
            relative_path=os.path.join(release_base_path, package_index_dir, "Packages"),
        )
        package_index = await self._create_unit(
            DeclarativeContent(content=content_unit, d_artifacts=d_artifacts)
        )
        # Interpret policy to download Artifacts or not
        deferred_download = self.remote.policy != Remote.IMMEDIATE
        # parse package_index
        package_futures = []
        for package_paragraph in deb822.Packages.iter_paragraphs(package_index.main_artifact.file):
            try:
                package_relpath = package_paragraph["Filename"]
                package_sha256 = package_paragraph["sha256"]
                if package_relpath.endswith(".deb"):
                    package_class = Package
                    serializer_class = Package822Serializer
                elif package_relpath.endswith(".udeb"):
                    package_class = InstallerPackage
                    serializer_class = InstallerPackage822Serializer
                log.debug("Downloading package {}".format(package_paragraph["Package"]))
                serializer = serializer_class.from822(data=package_paragraph)
                serializer.is_valid(raise_exception=True)
                package_content_unit = package_class(
                    relative_path=package_relpath,
                    sha256=package_sha256,
                    **serializer.validated_data,
                )
                package_path = os.path.join(self.parsed_url.path, package_relpath)
                package_da = DeclarativeArtifact(
                    artifact=Artifact(**_get_checksums(package_paragraph)),
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
                log.warning("Ignoring invalid package paragraph. {}".format(package_paragraph))
        # Assign packages to this release_component
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
        log.info("Downloading installer files from {}".format(installer_file_index_dir))
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
            relative_path = os.path.join(os.path.dirname(release_file.relative_path))
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


def _get_checksums(unit_dict):
    return {
        k: unit_dict[v]
        for k, v in {
            "sha512": "SHA512",
            "sha256": "SHA256",
            "sha1": "SHA1",
            "md5": "MD5sum",
        }.items()
        if v in unit_dict
    }
