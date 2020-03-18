from logging import getLogger

from django.db import models

from pulpcore.plugin.models import Publication, PublicationDistribution

from pulp_deb.app.models.signing_service import AptReleaseSigningService

logger = getLogger(__name__)

BOOL_CHOICES = [(True, "yes"), (False, "no")]


class VerbatimPublication(Publication):
    """
    A verbatim Publication for Content.

    This publication publishes the obtained metadata unchanged.
    """

    TYPE = "verbatim-publication"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class DebPublication(Publication):
    """
    A Publication for DebContent.

    This publication recreates all metadata.
    """

    TYPE = "apt-publication"

    simple = models.BooleanField(default=False)
    structured = models.BooleanField(default=False)
    signing_service = models.ForeignKey(
        AptReleaseSigningService, on_delete=models.PROTECT, null=True
    )

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class DebDistribution(PublicationDistribution):
    """
    A Distribution for DebContent.
    """

    TYPE = "apt-distribution"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
