import os
import shutil
import logging
from gettext import gettext as _

import hashlib
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
            if simple:
                repository = repo_version.repository
                release = deb822.Release()
                # TODO: release['Label']
                release["Codename"] = "default"
                release["Components"] = "all"
                release["Architectures"] = ""
                if repository.description:
                    release["Description"] = repository.description
                release["MD5sum"] = []
                release["SHA1"] = []
                release["SHA256"] = []
                release["SHA512"] = []
                package_index_files = {}
                for package in Package.objects.filter(
                    pk__in=repo_version.content.order_by("-pulp_created")
                ):
                    published_artifact = PublishedArtifact(
                        relative_path=package.filename(),
                        publication=publication,
                        content_artifact=package.contentartifact_set.get(),
                    )
                    published_artifact.save()
                    if package.architecture not in package_index_files:
                        package_index_path = os.path.join(
                            "dists",
                            "default",
                            "all",
                            "binary-{}".format(package.architecture),
                            "Packages",
                        )
                        os.makedirs(os.path.dirname(package_index_path), exist_ok=True)
                        package_index_files[package.architecture] = (
                            open(package_index_path, "wb"),
                            package_index_path,
                        )
                    package_serializer = Package822Serializer(package, context={"request": None})
                    package_serializer.to822("all").dump(
                        package_index_files[package.architecture][0]
                    )
                    package_index_files[package.architecture][0].write(b"\n")
                for (package_index_file, package_index_path) in package_index_files.values():
                    package_index_file.close()
                    gz_package_index_path = _zip_file(package_index_path)
                    _add_to_release(release, package_index_path)
                    _add_to_release(release, gz_package_index_path)

                    package_index = PublishedMetadata.create_from_file(
                        publication=publication, file=File(open(package_index_path, "rb"))
                    )
                    package_index.save()
                    gz_package_index = PublishedMetadata.create_from_file(
                        publication=publication, file=File(open(gz_package_index_path, "rb"))
                    )
                    gz_package_index.save()
                release["Architectures"] = ", ".join(package_index_files.keys())
                release_path = os.path.join("dists", "default", "Release")
                os.makedirs(os.path.dirname(release_path), exist_ok=True)
                with open(release_path, "wb") as release_file:
                    release.dump(release_file)
                release_metadata = PublishedMetadata.create_from_file(
                    publication=publication, file=File(open(release_path, "rb"))
                )
                release_metadata.save()

            if structured:
                raise NotImplementedError("Structured publishing is not yet implemented.")

    log.info(_("Publication: {publication} created").format(publication=publication.pk))


def _add_to_release(release, file_path):
    with open(file_path, "rb") as infile:
        size = 0
        md5sum_hasher = hashlib.md5()
        sha1_hasher = hashlib.sha1()
        sha256_hasher = hashlib.sha256()
        sha512_hasher = hashlib.sha512()
        for chunk in iter(lambda: infile.read(4096), b""):
            size += len(chunk)
            md5sum_hasher.update(chunk)
            sha1_hasher.update(chunk)
            sha256_hasher.update(chunk)
            sha512_hasher.update(chunk)

        release["MD5sum"].append(
            {"md5sum": md5sum_hasher.hexdigest(), "size": size, "name": file_path}
        )
        release["SHA1"].append({"sha1": sha1_hasher.hexdigest(), "size": size, "name": file_path})
        release["SHA256"].append(
            {"sha256": sha256_hasher.hexdigest(), "size": size, "name": file_path}
        )
        release["SHA512"].append(
            {"sha512": sha512_hasher.hexdigest(), "size": size, "name": file_path}
        )


def _zip_file(file_path):
    gz_file_path = file_path + ".gz"
    with open(file_path, "rb") as f_in:
        with GzipFile(gz_file_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    return gz_file_path
