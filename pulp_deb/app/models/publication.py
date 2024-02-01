from contextlib import suppress
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django_lifecycle import hook, AFTER_CREATE, AFTER_UPDATE

from pulpcore.plugin.models import (
    BaseModel,
    Distribution,
    Publication,
    PublishedArtifact,
    RepositoryVersion,
)

from pulp_deb.app.models.signing_service import AptReleaseSigningService


BOOL_CHOICES = [(True, "yes"), (False, "no")]
PUBLICATION_CACHE_DURATION = timedelta(days=3)


def latest_publication(repo_pk):
    """
    Find the latest publication for a repository.

    This function is based on the logic in pulpcore's content handler.

    https://github.com/pulp/pulpcore/blob/3bfd35c76e29944b622d275be52c0d5ebbdfbf72/pulpcore/content/handler.py#L601-L607
    """
    versions = RepositoryVersion.objects.filter(repository=repo_pk)
    with suppress(Publication.DoesNotExist):
        return (
            Publication.objects.filter(repository_version__in=versions, complete=True)
            .latest("repository_version", "pulp_created")
            .cast()
        )


class VerbatimPublication(Publication):
    """
    A verbatim Publication for Content.

    This publication publishes the obtained metadata unchanged.
    """

    TYPE = "verbatim-publication"

    @hook(AFTER_UPDATE, when="complete", has_changed=True, is_now=True)
    def set_distributed_publication(self):
        for distro in AptDistribution.objects.filter(repository__pk=self.repository.pk):
            if self == latest_publication(self.repository.pk):
                DistributedPublication(distribution=distro, publication=self).save()

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class AptPublication(Publication):
    """
    A Publication for DebContent.

    This publication recreates all metadata.
    """

    TYPE = "apt-publication"

    simple = models.BooleanField(default=False)
    structured = models.BooleanField(default=True)
    signing_service = models.ForeignKey(
        AptReleaseSigningService, on_delete=models.PROTECT, null=True
    )

    @hook(AFTER_UPDATE, when="complete", has_changed=True, is_now=True)
    def set_distributed_publication(self):
        for distro in AptDistribution.objects.filter(repository__pk=self.repository.pk):
            if self == latest_publication(self.repository.pk):
                DistributedPublication(distribution=distro, publication=self).save()

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class AptDistribution(Distribution):
    """
    A Distribution for DebContent.
    """

    TYPE = "apt-distribution"
    SERVE_FROM_PUBLICATION = True

    @hook(AFTER_CREATE)
    @hook(AFTER_UPDATE, when="publication", has_changed=True, is_not=None)
    @hook(AFTER_UPDATE, when="repository", has_changed=True, is_not=None)
    def set_distributed_publication(self):
        if self.publication:
            DistributedPublication(distribution=self, publication=self.publication)
        elif self.repository:
            if publication := latest_publication(self.repository):
                DistributedPublication(distribution=self, publication=publication).save()

    def content_handler(self, path):
        recent_dp = self.distributedpublication_set.filter(
            models.Q(expires_at__gte=timezone.now()) | models.Q(expires_at__isnull=True)
        ).order_by("pulp_created")
        pa = (
            PublishedArtifact.objects.filter(
                relative_path=path, publication__distributedpublication__pk__in=recent_dp
            )
            .order_by("-publication__distributedpublication__pulp_created")
            .select_related(
                "content_artifact",
                "content_artifact__artifact",
            )
        ).first()

        if pa:
            return pa.content_artifact
        return

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class DistributedPublication(BaseModel):
    """
    Represents a history of distributed publications.

    This allows the content handler to serve a previous Publication's content for a set period of
    time.

    When a new Publication is served by a Distribution, it creates a new DistributionPublication and
    sets the expires_at field on any existing DistributionPublications.
    """

    distribution = models.ForeignKey(Distribution, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)
    expires_at = models.DateTimeField(null=True)

    @hook(AFTER_CREATE)
    def cleanup(self):
        """Set expires_at on any older DistributedPublication and cleanup any expired ones."""
        DistributedPublication.objects.filter(expires_at__lt=timezone.now()).delete()
        DistributedPublication.objects.exclude(pk=self.pk).filter(
            distribution=self.distribution, expires_at__isnull=True
        ).update(expires_at=(timezone.now() + PUBLICATION_CACHE_DURATION))
