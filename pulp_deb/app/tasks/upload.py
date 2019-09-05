import logging
from gettext import gettext as _

from debian import debfile

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from pulpcore.plugin.models import Artifact, ContentArtifact, Repository, RepositoryVersion
from pulpcore.app.models.task import CreatedResource

from pulp_deb.app.models import Package


log = logging.getLogger(__name__)


def one_shot_upload(artifact_pk, repository_pk=None):
    """
    Create a Package from an uploaded file and attach it to a Repository if provided.

    Args:
        artifact_pk (str): Create a Package from this artifact.

    Optional:
        repository_pk (str): Insert the Package into this Repository.

    """
    artifact = Artifact.objects.get(pk=artifact_pk)
    repository = Repository.objects.get(pk=repository_pk) if repository_pk else None
    log.debug(
        _("Uploading deb package: artifact={artifact}, repository={repo}").format(
            artifact=artifact, repo=repository
        )
    )

    package_paragraph = debfile.DebFile(fileobj=artifact.file).debcontrol()
    package_dict = Package.from822(package_paragraph)
    package_dict["sha256"] = artifact.sha256
    package = Package(**package_dict)
    package.relative_path = package.filename()
    try:
        package = Package.objects.get(sha256=artifact.sha256, relative_path=package.relative_path)
    except ObjectDoesNotExist:
        with transaction.atomic():
            package.save()

            ContentArtifact.objects.create(
                artifact=artifact, content=package, relative_path=package.relative_path
            )

            resource = CreatedResource(content_object=package)
            resource.save()

    if repository:
        content_to_add = Package.objects.filter(pk=package.pk)

        # create new repo version with uploaded package
        with RepositoryVersion.create(repository) as new_version:
            new_version.add_content(content_to_add)
