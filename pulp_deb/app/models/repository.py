from django.conf import settings

from django.db.models import (
    BooleanField,
    TextField,
)

from pulpcore.plugin.models import Repository

from pulpcore.plugin.repo_version_utils import remove_duplicates, validate_repo_version

from pulp_deb.app.models import (
    AptRemote,
    GenericContent,
    InstallerFileIndex,
    InstallerPackage,
    Package,
    PackageIndex,
    PackageReleaseComponent,
    Release,
    ReleaseArchitecture,
    ReleaseComponent,
    ReleaseFile,
)


class AptRepository(Repository):
    """
    A Repository for DebContent.
    """

    TYPE = "deb"
    CONTENT_TYPES = [
        GenericContent,
        InstallerFileIndex,
        InstallerPackage,
        Package,
        PackageIndex,
        PackageReleaseComponent,
        Release,
        ReleaseArchitecture,
        ReleaseComponent,
        ReleaseFile,
    ]
    REMOTE_TYPES = [
        AptRemote,
    ]

    # Space separated list containing a subset of "simple structured verbatim"
    autopublish_modes = models.TextField(null=False, default='')
    autopublish = models.BooleanField(default=False)

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

        if self.autopublish:
            if self.autopublish_modes:
                autopublish_modes = self.autopublish_modes.split()
            else:
                autopublish_modes = settings.DEFAULT_AUTOPUBLISH_MODES.split()

            distributions = self.distributions.all()

            if 'verbatim' in autopublish_modes:
                verbatim_publication = tasks.publish_verbatim(repository_version_pk=version.pk)
                autopublish_modes.remove('verbatim')

            if autopublish_modes:
                simple = 'simple' in autopublish_modes
                structured = 'structured' in autopublish_modes
                # If neither simple nor structured is the case the following will throw an error.
                apt_publication = tasks.publish(
                    repository_version_pk=version.pk,
                    simple=simple,
                    structured=structured,
                    #signing_service_pk=???,
                )


            if distributions:
                for distribution in distributions:
                    if distribution.publication.TYPE == "verbatim-publication":
                        if verbatim_publication:
                            distirbution.publication = verbatim_publication
                            distribution.save()
                    elif distribution.publication.TYPE == "apt-publication":
                        if apt_publication:
                            distirbution.publication = apt_publication
                            distribution.save()
