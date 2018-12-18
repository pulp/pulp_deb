import logging
from gettext import gettext as _

from pulpcore.plugin.models import (
    RepositoryVersion,
    Publication,
    PublishedArtifact,
    PublishedMetadata,
    RemoteArtifact
)
from pulpcore.plugin.tasking import WorkingDirectory

from pulp_deb.app.models import DebPublisher


log = logging.getLogger(__name__)


def publish(publisher_pk, repository_version_pk):
    """
    Use provided publisher to create a Publication based on a RepositoryVersion.

    Args:
        publisher_pk (str): Use the publish settings provided by this publisher.
        repository_version_pk (str): Create a publication from this repository version.
    """
    publisher = DebPublisher.objects.get(pk=publisher_pk)
    repository_version = RepositoryVersion.objects.get(pk=repository_version_pk)

    log.info(_('Publishing: repository={repo}, version={ver}, publisher={pub}').format(
        repo=repository_version.repository.name,
        ver=repository_version.number,
        pub=publisher.name
    ))
    with WorkingDirectory():
        with Publication.create(repository_version, publisher) as publication:
            # Write any Artifacts (files) to the file system, and the database.
            #
            # artifact = YourArtifactWriter.write(relative_path)
            # published_artifact = PublishedArtifact(
            #     relative_path=artifact.relative_path,
            #     publication=publication,
            #     content_artifact=artifact)
            # published_artifact.save()

            # Write any metadata files to the file system, and the database.
            #
            # metadata = YourMetadataWriter.write(relative_path)
            # metadata = PublishedMetadata(
            #     relative_path=os.path.basename(manifest.relative_path),
            #     publication=publication,
            #     file=File(open(manifest.relative_path, 'rb')))
            # metadata.save()
            pass

    log.info(_('Publication: {publication} created').format(publication=publication.pk))
