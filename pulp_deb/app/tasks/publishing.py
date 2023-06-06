import os
import shutil
from contextlib import suppress

from datetime import datetime, timezone
from debian import deb822
from gzip import GzipFile
import tempfile

from django.conf import settings
from django.core.files import File
from django.db.utils import IntegrityError
from django.forms.models import model_to_dict

from pulpcore.plugin.models import (
    PublishedArtifact,
    PublishedMetadata,
    RepositoryVersion,
)

from pulp_deb.app.models import (
    AptPublication,
    Package,
    PackageReleaseComponent,
    Release,
    ReleaseArchitecture,
    ReleaseComponent,
    VerbatimPublication,
    AptReleaseSigningService,
)

from pulp_deb.app.serializers import Package822Serializer

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


def publish(repository_version_pk, simple=False, structured=False, signing_service_pk=None):
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
    if signing_service_pk:
        signing_service = AptReleaseSigningService.objects.get(pk=signing_service_pk)
    else:
        signing_service = None

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
            repository = repo_version.repository

            if simple:
                codename = "default"
                distribution = "default"
                component = "all"
                architectures = (
                    Package.objects.filter(
                        pk__in=repo_version.content.order_by("-pulp_created"),
                    )
                    .distinct("architecture")
                    .values_list("architecture", flat=True)
                )
                architectures = list(architectures)
                if "all" not in architectures:
                    architectures.append("all")
                release_helper = _ReleaseHelper(
                    publication=publication,
                    codename=codename,
                    distribution=distribution,
                    components=[component],
                    architectures=architectures,
                    description=repository.description,
                    label=repository.name,
                    version=str(repo_version.number),
                )

                for package in Package.objects.filter(
                    pk__in=repo_version.content.order_by("-pulp_created"),
                ):
                    release_helper.components[component].add_package(package)
                release_helper.finish()

            if structured:
                for release in Release.objects.filter(
                    pk__in=repo_version.content.order_by("-pulp_created"),
                ):
                    if simple and release.distribution == "default":
                        message = (
                            'Ignoring structured "default" distribution for publication that also '
                            "uses simple mode."
                        )
                        log.warning(_(message))
                        continue
                    architectures = ReleaseArchitecture.objects.filter(
                        pk__in=repo_version.content.order_by("-pulp_created"),
                        release=release,
                    ).values_list("architecture", flat=True)
                    architectures = list(architectures)
                    if "all" not in architectures:
                        architectures.append("all")
                    components = ReleaseComponent.objects.filter(
                        pk__in=repo_version.content.order_by("-pulp_created"),
                        release=release,
                    )
                    release_helper = _ReleaseHelper(
                        publication=publication,
                        codename=release.codename,
                        distribution=release.distribution,
                        components=components.values_list("component", flat=True),
                        architectures=architectures,
                        description=repository.description,
                        label=repository.name,
                        version=str(repo_version.number),
                        suite=release.suite,
                    )

                    for prc in PackageReleaseComponent.objects.filter(
                        pk__in=repo_version.content.order_by("-pulp_created"),
                        release_component__in=components,
                    ):
                        release_helper.components[prc.release_component.component].add_package(
                            prc.package
                        )
                    release_helper.finish()

    log.info(_("Publication: {publication} created").format(publication=publication.pk))


class _ComponentHelper:
    def __init__(self, parent, component):
        self.parent = parent
        self.component = component
        self.plain_component = os.path.basename(component)
        self.package_index_files = {}

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

    def add_package(self, package):
        with suppress(IntegrityError):
            published_artifact = PublishedArtifact(
                relative_path=package.filename(self.component),
                publication=self.parent.publication,
                content_artifact=package.contentartifact_set.get(),
            )
            published_artifact.save()
        package_serializer = Package822Serializer(package, context={"request": None})

        try:
            package_serializer.to822(self.component).dump(
                self.package_index_files[package.architecture][0]
            )
        except KeyError:
            log.warn(
                f"Published package '{package.relative_path}' with architecture "
                f"'{package.architecture}' was not added to component '{self.component}' in "
                f"distribution '{self.parent.distribution}' because it lacks this architecture!"
            )
        else:
            self.package_index_files[package.architecture][0].write(b"\n")

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
            self.parent.add_metadata(package_index)
            self.parent.add_metadata(gz_package_index)


class _ReleaseHelper:
    def __init__(
        self,
        publication,
        codename,
        distribution,
        components,
        architectures,
        label,
        version,
        description=None,
        suite=None,
    ):
        self.publication = publication
        self.distribution = distribution
        self.dists_subfolder = distribution.strip("/") if distribution != "/" else "flat-repo"
        if distribution[-1] == "/":
            message = "Using dists subfolder '{}' for structured publish of originally flat repo!"
            log.info(_(message).format(self.dists_subfolder))
        # Note: The order in which fields are added to self.release is retained in the
        # published Release file. As a "nice to have" for human readers, we try to use
        # the same order of fields that official Debian repositories use.
        self.release = deb822.Release()
        self.release["Origin"] = "Pulp 3"
        if settings.PUBLISH_RELEASE_FILE_LABEL:
            self.release["Label"] = label
        if suite:
            self.release["Suite"] = suite
        if settings.PUBLISH_RELEASE_FILE_VERSION:
            self.release["Version"] = version
        if not codename:
            codename = distribution.split("/")[0] if distribution != "/" else "flat-repo"
        self.release["Codename"] = codename
        self.release["Date"] = datetime.now(tz=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
        self.release["Architectures"] = " ".join(architectures)
        self.release["Components"] = ""  # Will be set later
        if description:
            self.release["Description"] = description

        for checksum_type, deb_field in CHECKSUM_TYPE_MAP.items():
            if checksum_type in settings.ALLOWED_CONTENT_CHECKSUMS:
                self.release[deb_field] = []

        self.architectures = architectures
        self.components = {component: _ComponentHelper(self, component) for component in components}
        self.signing_service = publication.signing_service

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
        # Publish Packages files
        for component in self.components.values():
            component.finish()
        # Publish Release file
        self.release["Components"] = " ".join(self.components.keys())
        release_dir = os.path.join("dists", self.dists_subfolder)
        os.makedirs(release_dir, exist_ok=True)
        release_path = os.path.join(release_dir, "Release")
        with open(release_path, "wb") as release_file:
            self.release.dump(release_file)
        release_metadata = PublishedMetadata.create_from_file(
            publication=self.publication,
            file=File(open(release_path, "rb")),
        )
        release_metadata.save()
        if self.signing_service:
            signed = self.signing_service.sign(release_path)
            for signature_file in signed["signatures"].values():
                file_name = os.path.basename(signature_file)
                relative_path = os.path.join(release_dir, file_name)
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
