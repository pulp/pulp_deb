from django.db import models
from pulpcore.plugin.models import BaseModel, Repository
from pulpcore.plugin.repo_version_utils import (
    remove_duplicates,
    validate_version_paths,
    validate_duplicate_content,
)

from pulpcore.plugin.models import Content

from pulp_deb.app.models import (
    AptReleaseSigningService,
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
    SourceIndex,
    SourcePackage,
    SourcePackageReleaseComponent,
)

import logging
from gettext import gettext as _

log = logging.getLogger(__name__)


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
        SourceIndex,
        SourcePackage,
        SourcePackageReleaseComponent,
    ]
    REMOTE_TYPES = [
        AptRemote,
    ]

    publish_upstream_release_fields = models.BooleanField(default=True)

    signing_service = models.ForeignKey(
        AptReleaseSigningService, on_delete=models.PROTECT, null=True
    )
    # Implicit signing_service_release_overrides

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"

    def release_signing_service(self, release):
        """
        Return the Signing Service specified in the overrides if there is one for this release,
        else return self.signing_service.
        """
        if isinstance(release, Release):
            release = release.distribution
        try:
            override = self.signing_service_release_overrides.get(release_distribution=release)
            return override.signing_service
        except AptRepositoryReleaseServiceOverride.DoesNotExist:
            return self.signing_service

    def initialize_new_version(self, new_version):
        """
        Remove old metadata from the repo before performing anything else for the new version. This
        way, we ensure any syncs will re-add all metadata relevant for the latest sync, but old
        metadata (which may no longer be appropriate for the new RepositoryVersion is never
        retained.
        """
        new_version.remove_content(ReleaseFile.objects.all())
        new_version.remove_content(PackageIndex.objects.all())
        new_version.remove_content(InstallerFileIndex.objects.all())

    def finalize_new_version(self, new_version):
        """
        Finalize and validate the new repository version.

        Ensure there are no duplication of added package in debian repository.

        Args:
            new_version (pulpcore.app.models.RepositoryVersion): The incomplete RepositoryVersion to
                finalize.

        """
        handle_duplicate_packages(new_version)
        validate_duplicate_content(new_version)
        remove_duplicates(new_version)
        validate_version_paths(new_version)


class AptRepositoryReleaseServiceOverride(BaseModel):
    """
    Override the SigningService that a single Release will use in this AptRepository.
    """

    repository = models.ForeignKey(
        AptRepository, on_delete=models.CASCADE, related_name="signing_service_release_overrides"
    )
    signing_service = models.ForeignKey(AptReleaseSigningService, on_delete=models.PROTECT)
    release_distribution = models.TextField()

    class Meta:
        unique_together = (("repository", "release_distribution"),)


def handle_duplicate_packages(new_version):
    """
    pulpcore's remove_duplicates does not work for .deb packages, since identical duplicate
    packages (same sha256) are rare, but allowed, while duplicates with different sha256 are
    forbidden. As such we need our own version of this function for .deb packages. Since we are
    already building our own function, we will also be combining the functionality of pulpcore's
    remove_duplicates and validate_duplicate_content within this function.
    """
    content_qs_added = new_version.added(base_version=new_version.base_version)
    if new_version.base_version:
        content_qs_existing = new_version.base_version.content
    else:
        try:
            content_qs_existing = new_version.previous().content
        except new_version.DoesNotExist:
            content_qs_existing = Content.objects.none()
    package_types = {
        Package.get_pulp_type(): Package,
        InstallerPackage.get_pulp_type(): InstallerPackage,
    }
    repo_key_fields = ("package", "version", "architecture")

    for pulp_type, package_obj in package_types.items():
        # First handle duplicates within the packages added to new_version
        package_qs_added = package_obj.objects.filter(
            pk__in=content_qs_added.filter(pulp_type=pulp_type)
        )
        added_unique = package_qs_added.distinct(*repo_key_fields)
        added_checksum_unique = package_qs_added.distinct(*repo_key_fields, "sha256")

        if added_unique.count() < added_checksum_unique.count():
            package_qs_added_duplicates = added_checksum_unique.difference(added_unique)
            if log.isEnabledFor(logging.DEBUG):
                message = _(
                    "New repository version contains multiple packages with '{}', but differing "
                    "checksum!"
                )
                for package_fields in package_qs_added_duplicates.values(*repo_key_fields):
                    log.debug(message.format(package_fields))

            message = _(
                "Cannot create repository version since there are newly added packages with the "
                "same name, version, and architecture, but a different checksum. If the log level "
                "is DEBUG, you can find a list of affected packages in the Pulp log."
            )
            raise ValueError(message)

        # Now remove existing packages that are duplicates of any packages added to new_version
        if package_qs_added.count() and content_qs_existing.count():
            for batch in batch_qs(package_qs_added.values(*repo_key_fields, "sha256")):
                find_dup_qs = models.Q()

                for content_dict in batch:
                    sha256 = content_dict.pop("sha256")
                    item_query = models.Q(**content_dict) & ~models.Q(sha256=sha256)
                    find_dup_qs |= item_query

                package_qs_duplicates = (
                    package_obj.objects.filter(pk__in=content_qs_existing)
                    .filter(find_dup_qs)
                    .only("pk")
                )
                prc_qs_duplicates = (
                    PackageReleaseComponent.objects.filter(pk__in=content_qs_existing)
                    .filter(package__in=package_qs_duplicates)
                    .only("pk")
                )
                if package_qs_duplicates.count():
                    message = _("Removing duplicates for type {} from new repo version.")
                    log.warning(message.format(pulp_type))
                    new_version.remove_content(package_qs_duplicates)
                    new_version.remove_content(prc_qs_duplicates)


# The following helper function is copy and pasted from pulpcore. As soon as
# https://github.com/pulp/pulpcore/issues/4607 is ready, we should replace it with an import!
def batch_qs(qs, batch_size=1000):
    """
    Returns a queryset batch in the given queryset.

    Usage:
        # Make sure to order your querset
        article_qs = Article.objects.order_by('id')
        for qs in batch_qs(article_qs):
            for article in qs:
                print article.body
    """
    total = qs.count()
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield qs[start:end]
