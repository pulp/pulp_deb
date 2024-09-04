import asyncio
import os
import shutil
from contextlib import suppress
from pathlib import Path

from datetime import datetime, timezone
from debian import deb822
from gzip import GzipFile
import tempfile

from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.db.utils import IntegrityError
from django.forms.models import model_to_dict

from pulpcore.plugin.models import (
    Artifact,
    PublishedArtifact,
    PublishedMetadata,
    RemoteArtifact,
    RepositoryVersion,
)

from pulp_deb.app.constants import NULL_VALUE
from pulp_deb.app.models import (
    AptPublication,
    AptRepository,
    Package,
    PackageReleaseComponent,
    Release,
    ReleaseArchitecture,
    ReleaseComponent,
    VerbatimPublication,
    AptReleaseSigningService,
    SourcePackage,
    SourcePackageReleaseComponent,
)

from pulp_deb.app.serializers import (
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


def publish_verbatim(repository_version_pk):
    """
    Create a VerbatimPublication based on a RepositoryVersion.

    Args:
        repository_version_pk (str): Create a publication from this repository version.

    """
    repo_version = RepositoryVersion.objects.get(pk=repository_version_pk)

    log.info(
        _("Publishing (verbatim): repository={repo}, version={ver}").format(
            repo=repo_version.repository.name, ver=repo_version.number
        )
    )
    with tempfile.TemporaryDirectory("."):
        with VerbatimPublication.create(repo_version, pass_through=True) as publication:
            pass

    log.info(_("Publication (verbatim): {publication} created").format(publication=publication.pk))


def publish(
    repository_version_pk,
    simple,
    structured,
    signing_service_pk=None,
    publish_upstream_release_fields=None,
):
    """
    Use provided publisher to create a Publication based on a RepositoryVersion.

    Args:
        repository_version_pk (str): Create a publication from this repository version.
        simple (bool): Create a simple publication with all packages contained in default/all.
        structured (bool): Create a structured publication with releases and components.
        signing_service_pk (str): Use this SigningService to sign the Release files.

    """

    if "md5" not in settings.ALLOWED_CONTENT_CHECKSUMS and settings.FORBIDDEN_CHECKSUM_WARNINGS:
        log.warning(_(NO_MD5_WARNING_MESSAGE))

    repo_version = RepositoryVersion.objects.get(pk=repository_version_pk)
    signing_service = (
        AptReleaseSigningService.objects.get(pk=signing_service_pk) if signing_service_pk else None
    )

    log.info(
        _(
            "Publishing: repository={repo}, version={ver}, simple={simple}, structured={structured}"
        ).format(  # noqa
            repo=repo_version.repository.name,
            ver=repo_version.number,
            simple=simple,
            structured=structured,
        )
    )
    with tempfile.TemporaryDirectory("."):
        with AptPublication.create(repo_version, pass_through=False) as publication:
            publication.simple = simple
            publication.structured = structured
            publication.signing_service = signing_service
            repository = AptRepository.objects.get(pk=repo_version.repository.pk)

            if simple:
                release = Release(
                    distribution="default",
                    codename="default",
                    origin="Pulp 3",
                )
                if repository.description:
                    release.description = repository.description

                component = "all"
                architectures = list(
                    Package.objects.filter(
                        pk__in=repo_version.content.order_by("-pulp_created"),
                    )
                    .distinct("architecture")
                    .values_list("architecture", flat=True)
                )
                if "all" not in architectures:
                    architectures.append("all")

                release_helper = _ReleaseHelper(
                    publication=publication,
                    release=release,
                    components=[component],
                    architectures=architectures,
                    signing_service=repository.signing_service,
                )

                packages = Package.objects.filter(
                    pk__in=repo_version.content.order_by("-pulp_created")
                ).prefetch_related("contentartifact_set", "_artifacts")
                artifact_dict, remote_artifact_dict = _batch_fetch_artifacts(packages)
                release_helper.components[component].add_packages(
                    packages, artifact_dict, remote_artifact_dict
                )

                source_packages = SourcePackage.objects.filter(
                    pk__in=repo_version.content.order_by("-pulp_created"),
                )
                release_helper.components[component].add_source_packages(source_packages)

                release_helper.finish()

            if structured:
                release_components = ReleaseComponent.objects.filter(
                    pk__in=repo_version.content.order_by("-pulp_created")
                )

                distributions = list(
                    release_components.distinct("distribution").values_list(
                        "distribution", flat=True
                    )
                )

                if simple and "default" in distributions:
                    message = (
                        'Ignoring structured "default" distribution for publication that also '
                        "uses simple mode."
                    )
                    log.warning(_(message))
                    distributions.remove("default")

                release_helpers = []
                for distribution in distributions:
                    architectures = list(
                        ReleaseArchitecture.objects.filter(
                            pk__in=repo_version.content.order_by("-pulp_created"),
                            distribution=distribution,
                        )
                        .distinct("architecture")
                        .values_list("architecture", flat=True)
                    )
                    if "all" not in architectures:
                        architectures.append("all")

                    release = Release.objects.filter(
                        pk__in=repo_version.content.order_by("-pulp_created"),
                        distribution=distribution,
                    ).first()
                    publish_upstream = (
                        publish_upstream_release_fields
                        if publish_upstream_release_fields is not None
                        else repository.publish_upstream_release_fields
                    )
                    if not release:
                        codename = distribution.strip("/").split("/")[0]
                        release = Release(
                            distribution=distribution,
                            codename=codename,
                            suite=codename,
                            origin="Pulp 3",
                        )
                        if repository.description:
                            release.description = repository.description
                    elif not publish_upstream:
                        release = Release(
                            distribution=release.distribution,
                            codename=release.codename,
                            suite=release.suite,
                            origin="Pulp 3",
                        )
                        if repository.description:
                            release.description = repository.description

                    release_components_filtered = release_components.filter(
                        distribution=distribution
                    )
                    components = list(
                        release_components_filtered.distinct("component").values_list(
                            "component", flat=True
                        )
                    )

                    signing_service = repository.release_signing_service(release)

                    release_helper = _ReleaseHelper(
                        publication=publication,
                        components=components,
                        architectures=architectures,
                        release=release,
                        signing_service=signing_service,
                    )

                    package_release_components = PackageReleaseComponent.objects.filter(
                        pk__in=repo_version.content.order_by("-pulp_created"),
                        release_component__in=release_components_filtered,
                    ).select_related("release_component", "package")

                    source_package_release_components = (
                        SourcePackageReleaseComponent.objects.filter(
                            pk__in=repo_version.content.order_by("-pulp_created"),
                            release_component__in=release_components_filtered,
                        ).select_related("release_component", "source_package")
                    )

                    for component in components:
                        packages = Package.objects.filter(
                            pk__in=[
                                prc.package.pk
                                for prc in package_release_components
                                if prc.release_component.component == component
                            ]
                        ).prefetch_related("contentartifact_set", "_artifacts")
                        artifact_dict, remote_artifact_dict = _batch_fetch_artifacts(packages)
                        release_helper.components[component].add_packages(
                            packages,
                            artifact_dict,
                            remote_artifact_dict,
                        )

                        source_packages = [
                            drc.source_package
                            for drc in source_package_release_components
                            if drc.release_component.component == component
                        ]
                        release_helper.components[component].add_source_packages(source_packages)

                    release_helper.save_unsigned_metadata()
                    release_helpers.append(release_helper)

                asyncio.run(_concurrently_sign_metadata(release_helpers))
                for release_helper in release_helpers:
                    release_helper.save_signed_metadata()

    log.info(_("Publication: {publication} created").format(publication=publication.pk))


async def _concurrently_sign_metadata(release_helpers):
    await asyncio.gather(*[x.sign_metadata() for x in release_helpers])


class _ComponentHelper:
    def __init__(self, parent, component):
        self.parent = parent
        self.component = component
        self.plain_component = os.path.basename(component)
        self.package_index_files = {}
        self.source_index_file_info = None

        for architecture in self.parent.architectures:
            package_index_path = os.path.join(
                "dists",
                self.parent.dists_subfolder,
                self.plain_component,
                "binary-{}".format(architecture),
                "Packages",
            )
            os.makedirs(os.path.dirname(package_index_path), exist_ok=True)
            self.package_index_files[architecture] = (
                open(package_index_path, "wb"),
                package_index_path,
            )
        # Source indicies file
        source_index_path = os.path.join(
            "dists",
            self.parent.distribution.strip("/"),
            self.plain_component,
            "source",
            "Sources",
        )
        os.makedirs(os.path.dirname(source_index_path), exist_ok=True)
        self.source_index_file_info = (
            open(source_index_path, "wb"),
            source_index_path,
        )

    def add_packages(self, packages, artifact_dict, remote_artifact_dict):
        published_artifacts = []
        package_data = []

        content_artifacts = {
            package.pk: list(package.contentartifact_set.all()) for package in packages
        }

        for package in packages:
            with suppress(IntegrityError):
                content_artifact = content_artifacts.get(package.pk, [None])[0]
                relative_path = package.filename(self.component)

                published_artifact = PublishedArtifact(
                    relative_path=relative_path,
                    publication=self.parent.publication,
                    content_artifact=content_artifact,
                )
                published_artifacts.append(published_artifact)
                package_data.append((package, package.architecture))

        with transaction.atomic():
            if published_artifacts:
                PublishedArtifact.objects.bulk_create(published_artifacts, ignore_conflicts=True)

        for package, architecture in package_data:
            package_serializer = Package822Serializer(package, context={"request": None})
            try:
                package_serializer.to822(self.component, artifact_dict, remote_artifact_dict).dump(
                    self.package_index_files[architecture][0]
                )
            except KeyError:
                log.warn(
                    f"Published package '{package.relative_path}' with architecture "
                    f"'{architecture}' was not added to component '{self.component}' in "
                    f"distribution '{self.parent.distribution}' because it lacks this architecture!"
                )
            else:
                self.package_index_files[architecture][0].write(b"\n")

    # Publish DSC file and setup to create Sources Indices file
    def add_source_packages(self, source_packages):
        published_artifacts = []
        source_package_data = []

        for source_package in source_packages:
            with suppress(IntegrityError):
                artifact_set = source_package.contentartifact_set.all()
                for content_artifact in artifact_set:
                    published_artifact = PublishedArtifact(
                        relative_path=source_package.derived_path(
                            os.path.basename(content_artifact.relative_path), self.component
                        ),
                        publication=self.parent.publication,
                        content_artifact=content_artifact,
                    )
                    published_artifacts.append(published_artifact)
                source_package_data.append(source_package)

        with transaction.atomic():
            if published_artifacts:
                PublishedArtifact.objects.bulk_create(published_artifacts, ignore_conflicts=True)

        for source_package in source_package_data:
            dsc_file_822_serializer = DscFile822Serializer(
                source_package, context={"request": None}
            )
            dsc_file_822_serializer.to822(self.component, paragraph=True).dump(
                self.source_index_file_info[0]
            )
            self.source_index_file_info[0].write(b"\n")

    def finish(self):
        # Publish Packages files
        for package_index_file, package_index_path in self.package_index_files.values():
            package_index_file.close()
            gz_package_index_path = _zip_file(package_index_path)
            package_index = PublishedMetadata.create_from_file(
                publication=self.parent.publication, file=File(open(package_index_path, "rb"))
            )
            package_index.save()
            gz_package_index = PublishedMetadata.create_from_file(
                publication=self.parent.publication, file=File(open(gz_package_index_path, "rb"))
            )
            gz_package_index.save()

            # Generating metadata files using checksum
            if settings.APT_BY_HASH:
                self.generate_by_hash(
                    package_index_path, package_index, gz_package_index_path, gz_package_index
                )

            self.parent.add_metadata(package_index)
            self.parent.add_metadata(gz_package_index)
        # Publish Sources Indices file
        if self.source_index_file_info is not None:
            (source_index_file, source_index_path) = self.source_index_file_info
            source_index_file.close()
            gz_source_index_path = _zip_file(source_index_path)
            source_index = PublishedMetadata.create_from_file(
                publication=self.parent.publication, file=File(open(source_index_path, "rb"))
            )
            source_index.save()
            gz_source_index = PublishedMetadata.create_from_file(
                publication=self.parent.publication, file=File(open(gz_source_index_path, "rb"))
            )
            gz_source_index.save()

            # Generating metadata files using checksum
            if settings.APT_BY_HASH:
                self.generate_by_hash(
                    source_index_path, source_index, gz_source_index_path, gz_source_index
                )

            self.parent.add_metadata(source_index)
            self.parent.add_metadata(gz_source_index)

    def generate_by_hash(self, index_path, index, gz_index_path, gz_index):
        for path, index in (
            (index_path, index),
            (gz_index_path, gz_index),
        ):
            for checksum in settings.ALLOWED_CONTENT_CHECKSUMS:
                if checksum in CHECKSUM_TYPE_MAP:
                    hashed_index_path = _fetch_file_checksum(path, index, checksum)
                    hashed_index = PublishedMetadata.create_from_file(
                        publication=self.parent.publication,
                        file=File(open(path, "rb")),
                        relative_path=hashed_index_path,
                    )
                    hashed_index.save()


class _ReleaseHelper:
    def __init__(
        self,
        publication,
        components,
        architectures,
        release,
        signing_service=None,
    ):
        self.publication = publication
        self.distribution = distribution = release.distribution
        self.dists_subfolder = distribution.strip("/") if distribution != "/" else "flat-repo"
        if distribution[-1] == "/":
            message = "Using dists subfolder '{}' for structured publish of originally flat repo!"
            log.info(_(message).format(self.dists_subfolder))
        # Note: The order in which fields are added to self.release is retained in the
        # published Release file. As a "nice to have" for human readers, we try to use
        # the same order of fields that official Debian repositories use.
        self.release = deb822.Release()
        if release.origin != NULL_VALUE:
            self.release["Origin"] = release.origin
        if release.label != NULL_VALUE:
            self.release["Label"] = release.label
        if release.suite:
            self.release["Suite"] = release.suite
        if release.version != NULL_VALUE:
            self.release["Version"] = release.version
        if not release.codename:
            release.codename = distribution.split("/")[0] if distribution != "/" else "flat-repo"
        self.release["Codename"] = release.codename
        self.release["Date"] = datetime.now(tz=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
        self.release["Architectures"] = " ".join(architectures)
        self.release["Components"] = ""  # Will be set later
        if release.description != NULL_VALUE:
            self.release["Description"] = release.description
        self.release["Acquire-By-Hash"] = "yes" if settings.APT_BY_HASH else "no"

        for checksum_type, deb_field in CHECKSUM_TYPE_MAP.items():
            if checksum_type in settings.ALLOWED_CONTENT_CHECKSUMS:
                self.release[deb_field] = []

        self.architectures = architectures
        self.components = {component: _ComponentHelper(self, component) for component in components}
        self.signing_service = publication.signing_service or signing_service

    def add_metadata(self, metadata):
        artifact = metadata._artifacts.get()
        release_file_folder = os.path.join("dists", self.dists_subfolder)
        release_file_relative_path = os.path.relpath(metadata.relative_path, release_file_folder)

        for checksum_type, deb_field in CHECKSUM_TYPE_MAP.items():
            if checksum_type in settings.ALLOWED_CONTENT_CHECKSUMS:
                self.release[deb_field].append(
                    {
                        deb_field.lower(): model_to_dict(artifact)[checksum_type],
                        "size": artifact.size,
                        "name": release_file_relative_path,
                    }
                )

    def finish(self):
        """
        You must *either* call finish (as the simple publications still do), or you must call
        save_unsigned_metadata, sign_metadata, and save_signed_metadata, in order. The benefit of
        doing it the other way is that you can sign the metadata for all releases concurrently.
        """
        self.save_unsigned_metadata()
        asyncio.run(self.sign_metadata())
        self.save_signed_metadata()

    def save_unsigned_metadata(self):
        # Publish Packages files
        for component in self.components.values():
            component.finish()
        # Publish Release file
        self.release["Components"] = " ".join(self.components.keys())
        self.release_dir = os.path.join("dists", self.dists_subfolder)
        os.makedirs(self.release_dir, exist_ok=True)
        self.release_path = os.path.join(self.release_dir, "Release")
        with open(self.release_path, "wb") as release_file:
            self.release.dump(release_file)
        release_metadata = PublishedMetadata.create_from_file(
            publication=self.publication,
            file=File(open(self.release_path, "rb")),
        )
        release_metadata.save()

    async def sign_metadata(self):
        self.signed = {"signatures": {}}
        if self.signing_service:
            self.signed = await self.signing_service.asign(self.release_path)

    def save_signed_metadata(self):
        for signature_file in self.signed["signatures"].values():
            file_name = os.path.basename(signature_file)
            relative_path = os.path.join(self.release_dir, file_name)
            metadata = PublishedMetadata.create_from_file(
                publication=self.publication,
                file=File(open(signature_file, "rb")),
                relative_path=relative_path,
            )
            metadata.save()


def _zip_file(file_path):
    gz_file_path = file_path + ".gz"
    with open(file_path, "rb") as f_in:
        with GzipFile(gz_file_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    return gz_file_path


def _fetch_file_checksum(file_path, index, checksum):
    digest = getattr(index.contentartifact_set.first().artifact, checksum)
    checksum_type = CHECKSUM_TYPE_MAP[checksum]
    hashed_path = Path(file_path).parents[0] / "by-hash" / checksum_type / digest
    return hashed_path


def _batch_fetch_artifacts(packages):
    sha256_values = [package.sha256 for package in packages if package.sha256]
    artifacts = Artifact.objects.filter(sha256__in=sha256_values)
    artifact_dict = {artifact.sha256: artifact for artifact in artifacts}

    remote_artifacts = RemoteArtifact.objects.filter(sha256__in=sha256_values)
    remote_artifact_dict = {artifact.sha256: artifact for artifact in remote_artifacts}

    return artifact_dict, remote_artifact_dict
