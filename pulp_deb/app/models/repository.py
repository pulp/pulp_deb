from logging import getLogger

from pulpcore.plugin.models import Repository

from pulpcore.plugin.repo_version_utils import remove_duplicates, validate_repo_version

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
    AptPublishSettings,
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

    def on_new_version(self, version):
        """
        Called when new repository versions are created.

        Args:
            version: The new repository version.
        """
        super().on_new_version(version)

        # avoid circular import issues
        from pulp_deb.app import tasks

        if self.publish_settings:
            publish_settings = AptPublishSettings.objects.get(pk=self.publish_settings)
            publication = tasks.publish(
                repository_version_pk=version.pk,
                publish_settings_pk=publish_settings.pk,
            )

            distributions = self.distributions.all()

            if publication and distributions:
                for distribution in distributions:
                    distribution.publication = publication
                    distribution.save()
