from logging import getLogger

from pulpcore.plugin.models import Repository

from pulpcore.plugin.repo_version_utils import remove_duplicates, validate_repo_version

from pulp_deb.app.models import (
    GenericContent,
    ReleaseFile,
    PackageIndex,
    InstallerFileIndex,
    Package,
    DebugPackage,
    InstallerPackage,
    Release,
    ReleaseArchitecture,
    ReleaseComponent,
    PackageReleaseComponent,
)

logger = getLogger(__name__)


class AptRepository(Repository):
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
        DebugPackage,
        InstallerPackage,
        Release,
        ReleaseArchitecture,
        ReleaseComponent,
        PackageReleaseComponent,
    ]

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"

    def finalize_new_version(self, new_version):
        """
        Finalize and validate the new repository version.

        Ensure there are no duplication of added package in debian repository.

        Args:
            new_version (pulpcore.app.models.RepositoryVersion): The incomplete RepositoryVersion to
                finalize.

        """
        remove_duplicates(new_version)
        validate_repo_version(new_version)
