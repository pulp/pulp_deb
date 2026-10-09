from django.contrib.postgres.fields import ArrayField
from django.db import models

from pulpcore.plugin.models import (
    AutoAddObjPermsMixin,
    BaseModel,
    Distribution,
    Publication,
)

from pulp_deb.app.constants import LAYOUT_CHOICES, LAYOUT_TYPES
from pulp_deb.app.models.signing_service import AptReleaseSigningService

BOOL_CHOICES = [(True, "yes"), (False, "no")]


class VerbatimPublication(Publication, AutoAddObjPermsMixin):
    """
    A verbatim Publication for Content.

    This publication publishes the obtained metadata unchanged.
    """

    TYPE = "verbatim-publication"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        permissions = [
            ("manage_roles_verbatimpublication", "Can manage roles on a verbatim publication"),
        ]


class AptPublication(Publication, AutoAddObjPermsMixin):
    """
    A Publication for DebContent.

    This publication recreates all metadata.
    """

    TYPE = "apt-publication"

    simple = models.BooleanField(default=False)
    structured = models.BooleanField(default=True)
    layout = models.TextField(choices=LAYOUT_CHOICES, default=LAYOUT_TYPES.NESTED_ALPHABETICALLY)
    excluded_package_metadata_fields = ArrayField(models.TextField(), default=list)
    signing_service = models.ForeignKey(
        AptReleaseSigningService, on_delete=models.PROTECT, null=True
    )

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        permissions = [
            ("manage_roles_aptpublication", "Can manage roles on an APT publication"),
        ]


class AptDistribution(Distribution, AutoAddObjPermsMixin):
    """
    A Distribution for DebContent.
    """

    TYPE = "apt-distribution"
    SERVE_FROM_PUBLICATION = True

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        permissions = [
            ("manage_roles_aptdistribution", "Can manage roles on an APT distribution"),
        ]


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
