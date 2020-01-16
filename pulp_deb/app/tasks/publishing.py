import os
import shutil
import logging
from gettext import gettext as _

from debian import deb822
from gzip import GzipFile

from django.core.files import File

from pulpcore.plugin.models import PublishedArtifact, PublishedMetadata, RepositoryVersion
from pulpcore.plugin.tasking import WorkingDirectory

from pulp_deb.app.models import DebPublication, Package, VerbatimPublication
from pulp_deb.app.serializers import Package822Serializer


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
    with WorkingDirectory():
        with VerbatimPublication.create(repo_version, pass_through=True) as publication:
            pass

    log.info(_("Publication (verbatim): {publication} created").format(publication=publication.pk))


def publish(repository_version_pk, simple=False, structured=False):
    """
    Use provided publisher to create a Publication based on a RepositoryVersion.

    Args:
        repository_version_pk (str): Create a publication from this repository version.
        simple (bool): Create a simple publication with all packages contained in default/all.
        structured (bool): Create a structured publication with releases and components.
            (Not yet implemented)

    """
    repo_version = RepositoryVersion.objects.get(pk=repository_version_pk)

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
    with WorkingDirectory():
        with DebPublication.create(repo_version, pass_through=False) as publication:
            publication.simple = simple
            publication.structured = structured
            repository = repo_version.repository

            if simple:
                codename = "default"
                component_name = "all"
                architectures = (
                    Package.objects.filter(pk__in=repo_version.content.order_by("-pulp_created"),)
                    .distinct("architecture")
                    .values_list("architecture", flat=True)
                )
                release_helper = _ReleaseHelper(
                    publication=publication,
                    codename=codename,
                    components=[component_name],
                    architectures=architectures,
                    description=repository.description,
                )

                for package in Package.objects.filter(
                    pk__in=repo_version.content.order_by("-pulp_created"),
                ):
                    release_helper.components[component_name].add_package(package)
                release_helper.finish()

            if structured:
                raise NotImplementedError("Structured publishing is not yet implemented.")

    log.info(_("Publication: {publication} created").format(publication=publication.pk))


class _ComponentHelper:
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name
        self.package_index_files = {}

        for architecture in self.parent.architectures:
            package_index_path = os.path.join(
                "dists",
                self.parent.release["codename"],
                self.name,
                "binary-{}".format(architecture),
                "Packages",
            )
            os.makedirs(os.path.dirname(package_index_path), exist_ok=True)
            self.package_index_files[architecture] = (
                open(package_index_path, "wb"),
                package_index_path,
            )

    def add_package(self, package):
        published_artifact = PublishedArtifact(
            relative_path=package.filename(self.name),
            publication=self.parent.publication,
            content_artifact=package.contentartifact_set.get(),
        )
        published_artifact.save()
        package_serializer = Package822Serializer(package, context={"request": None})
        package_serializer.to822(self.name).dump(self.package_index_files[package.architecture][0])
        self.package_index_files[package.architecture][0].write(b"\n")

    def finish(self):
        # Publish Packages files
        for (package_index_file, package_index_path) in self.package_index_files.values():
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
        self, publication, codename, components, architectures, label=None, description=None
    ):
        self.publication = publication
        self.release = deb822.Release()
        self.release["Codename"] = codename
        self.release["Architectures"] = " ".join(architectures)
        if label:
            self.release["Label"] = label
        if description:
            self.release["Description"] = description
        self.release["MD5sum"] = []
        self.release["SHA1"] = []
        self.release["SHA256"] = []
        self.release["SHA512"] = []
        self.architectures = architectures
        self.components = {name: _ComponentHelper(self, name) for name in components}

    def add_metadata(self, metadata):
        artifact = metadata._artifacts.get()

        self.release["MD5sum"].append(
            {"md5sum": artifact.md5, "size": artifact.size, "name": metadata.relative_path}
        )
        self.release["SHA1"].append(
            {"sha1": artifact.sha1, "size": artifact.size, "name": metadata.relative_path}
        )
        self.release["SHA256"].append(
            {"sha256": artifact.sha256, "size": artifact.size, "name": metadata.relative_path}
        )
        self.release["SHA512"].append(
            {"sha512": artifact.sha512, "size": artifact.size, "name": metadata.relative_path}
        )

    def finish(self):
        # Publish Packages files
        for component in self.components.values():
            component.finish()
        # Publish Release file
        self.release["components"] = " ".join(self.components.keys())
        release_path = os.path.join("dists", self.release["codename"], "Release")
        os.makedirs(os.path.dirname(release_path), exist_ok=True)
        with open(release_path, "wb") as release_file:
            self.release.dump(release_file)
        release_metadata = PublishedMetadata.create_from_file(
            publication=self.publication, file=File(open(release_path, "rb")),
        )
        release_metadata.save()
        # TODO Sign release


def _zip_file(file_path):
    gz_file_path = file_path + ".gz"
    with open(file_path, "rb") as f_in:
        with GzipFile(gz_file_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    return gz_file_path
