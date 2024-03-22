from django.db import models

from pulpcore.plugin.models import Remote, AutoAddObjPermsMixin


class AptRemote(Remote, AutoAddObjPermsMixin):
    """
    A Remote for DebContent.
    """

    TYPE = "apt-remote"

    distributions = models.TextField(null=True)
    components = models.TextField(null=True)
    architectures = models.TextField(null=True)
    sync_sources = models.BooleanField(default=False)
    sync_udebs = models.BooleanField(default=False)
    sync_installer = models.BooleanField(default=False)
    gpgkey = models.TextField(null=True)
    ignore_missing_package_indices = models.BooleanField(default=False)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        permissions = [
            ("manage_roles_aptremote", "Can manage roles on an APT remote"),
        ]
