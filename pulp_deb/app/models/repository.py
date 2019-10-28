from logging import getLogger

from pulpcore.plugin.models import Repository

from pulp_deb.app.models import (
    GenericContent,
    ReleaseFile,
    PackageIndex,
    InstallerFileIndex,
    Package,
    InstallerPackage,
    Release,
    ReleaseArchitecture,
    ReleaseComponent,
    PackageReleaseComponent,
)

logger = getLogger(__name__)


class DebRepository(Repository):
    """
    A Repository for DebContent.
    """

    TYPE = "deb"
    CONTENT_TYPES = [
        GenericContent,
        ReleaseFile,
        PackageIndex,
        InstallerFileIndex,
        Package,
        InstallerPackage,
        Release,
        ReleaseArchitecture,
        ReleaseComponent,
        PackageReleaseComponent,
    ]

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
