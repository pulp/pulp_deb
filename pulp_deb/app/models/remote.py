from logging import getLogger

from django.db import models

from pulpcore.plugin.models import Remote

logger = getLogger(__name__)


class AptRemote(Remote):
    """
    A Remote for DebContent.
    """

    TYPE = "apt-remote"

    distributions = models.CharField(max_length=255, null=True)
    components = models.CharField(max_length=255, null=True)
    architectures = models.CharField(max_length=255, null=True)
    sync_sources = models.BooleanField(default=False)
    sync_udebs = models.BooleanField(default=False)
    sync_installer = models.BooleanField(default=False)
    gpgkey = models.TextField(null=True)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
