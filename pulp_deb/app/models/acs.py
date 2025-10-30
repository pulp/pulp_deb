from logging import getLogger

from pulpcore.plugin.models import AlternateContentSource, AutoAddObjPermsMixin
from pulp_deb.app.models import AptRemote


log = getLogger(__name__)


class AptAlternateContentSource(AlternateContentSource, AutoAddObjPermsMixin):
    """
    Alternate Content Source for 'APT' content.
    """

    TYPE = "deb"
    REMOTE_TYPES = [AptRemote]

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        permissions = [
            ("refresh_aptalternatecontentsource", "Refresh an Alternate Content Source"),
            ("manage_roles_aptalternatecontentsource", "Can manage roles on ACS"),
        ]
