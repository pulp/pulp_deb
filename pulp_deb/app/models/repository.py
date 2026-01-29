from django.db import models
from django.utils.functional import cached_property

from pulpcore.plugin.models import (
    AutoAddObjPermsMixin,
    BaseModel,
    Content,
    Repository,
)
from pulpcore.plugin.repo_version_utils import (
    validate_version_paths,
    validate_duplicate_content,
)
from pulpcore.plugin.util import batch_qs, get_domain_pk

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
    AptPackageSigningService,
)

import logging
from gettext import gettext as _

log = logging.getLogger(__name__)


class AptRepository(Repository, AutoAddObjPermsMixin):
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

    package_signing_service = models.ForeignKey(
        AptPackageSigningService, on_delete=models.SET_NULL, null=True
    )

    package_signing_fingerprint = models.TextField(null=True, max_length=40)

    # Implicit signing_service_release_overrides
    # Implicit package_signing_fingerprint_release_overrides

    autopublish = models.BooleanField(default=False)

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
            tasks.publish(
                repository_version_pk=version.pk,
                # We currently support only automatically creating a structured
                # publication
                simple=False,
                structured=True,
                signing_service_pk=getattr(self.signing_service, "pk", None),
            )

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        permissions = [
            ("manage_roles_aptrepository", "Can manage roles on APT repositories"),
            ("modify_content_aptrepository", "Add content to, or remove content from a repository"),
            ("repair_aptrepository", "Copy an APT repository"),
            ("sync_aptrepository", "Sync an APT repository"),
            ("delete_aptrepository_version", "Delete a repository version"),
        ]

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

    def release_package_signing_fingerprint(self, release):
        """
        Return the Package Signing Fingerprint specified in the overrides if there is one for this
        release, else return self.package_signing_fingerprint.
        """
        if isinstance(release, Release):
            release = release.distribution
        if not release:
            return self.package_signing_fingerprint
        return self.package_signing_fingerprint_release_overrides_map.get(
            release, self.package_signing_fingerprint
        )

    @cached_property
    def package_signing_fingerprint_release_overrides_map(self):
        """
        Cached mapping of release distributions to package signing fingerprints.
        """
        return {
            override.release_distribution: override.package_signing_fingerprint
            for override in self.package_signing_fingerprint_release_overrides.all()
        }

    def initialize_new_version(self, new_version):
        """
        Remove old metadata from the repo before performing anything else for the new version. This
        way, we ensure any syncs will re-add all metadata relevant for the latest sync, but old
        metadata (which may no longer be appropriate for the new RepositoryVersion is never
        retained.
        """
        new_version.remove_content(ReleaseFile.objects.filter(pulp_domain=get_domain_pk()))
        new_version.remove_content(PackageIndex.objects.filter(pulp_domain=get_domain_pk()))
        new_version.remove_content(InstallerFileIndex.objects.filter(pulp_domain=get_domain_pk()))

    def finalize_new_version(self, new_version):
        """
        Finalize and validate the new repository version.

        Ensure there are no duplication of added package in debian repository.

        Args:
            new_version (pulpcore.app.models.RepositoryVersion): The incomplete RepositoryVersion to
                finalize.

        """
        handle_duplicate_packages(new_version)
        handle_duplicate_releases(new_version)
        validate_duplicate_content(new_version)
        validate_version_paths(new_version)


class AptRepositoryReleaseServiceOverride(BaseModel):
    """
    Override the SigningService that a single Release will use in this AptRepository.
    """

    repository = models.ForeignKey(
        AptRepository,
        on_delete=models.CASCADE,
        related_name="signing_service_release_overrides",
    )
    signing_service = models.ForeignKey(AptReleaseSigningService, on_delete=models.PROTECT)
    release_distribution = models.TextField()

    class Meta:
        unique_together = (("repository", "release_distribution"),)


class AptRepositoryReleasePackageSigningFingerprintOverride(BaseModel):
    """
    Override the signing fingerprint that a single Release will use in this AptRepository for
    signing packages.
    """

    repository = models.ForeignKey(
        AptRepository,
        on_delete=models.CASCADE,
        related_name="package_signing_fingerprint_release_overrides",
    )
    package_signing_fingerprint = models.TextField(max_length=40)
    release_distribution = models.TextField()

    class Meta:
        unique_together = (("repository", "release_distribution"),)


def find_dist_components(package_ids, content_set):
    """
    Given a list of package_ids and a content_set, this function will find all distribution-
    component combinations that exist for the given package_ids within the given content_set.

    Returns a set of strings, e.g.: "buster main".
    """
    # PackageReleaseComponents:
    package_prc_qs = PackageReleaseComponent.objects.filter(package__in=package_ids).only("pk")
    prc_content_qs = content_set.filter(pk__in=package_prc_qs)
    prc_qs = PackageReleaseComponent.objects.filter(pk__in=prc_content_qs.only("pk"))

    # ReleaseComponents:
    distribution_components = set()
    for prc in prc_qs.select_related("release_component").iterator():
        distribution = prc.release_component.distribution
        component = prc.release_component.component
        distribution_components.add(distribution + " " + component)

    return distribution_components


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
            if log.isEnabledFor(logging.DEBUG):
                message = _(
                    'New repository version is trying to add different versions, of package "{}", '
                    'to each of the following distribution-component combinations "{}"!'
                )
                package_qs_added_dups = added_checksum_unique.difference(added_unique)
                for package_fields in package_qs_added_dups.values(*repo_key_fields, "sha256"):
                    package_fields.pop("sha256")
                    duplicate_package_ids = package_qs_added.filter(**package_fields).only("pk")
                    distribution_components = find_dist_components(
                        duplicate_package_ids, content_qs_added
                    )
                    log.debug(message.format(package_fields, distribution_components))

            message = _(
                "Cannot create repository version since there are newly added packages with the "
                "same name, version, and architecture, but a different checksum. If the log level "
                "is DEBUG, you can find a list of affected packages in the Pulp log. You can often "
                "work around this issue by restricting syncs to only those distirbution component "
                "combinations, that do not contain colliding duplicates!"
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


def handle_duplicate_releases(new_version):
    """
    it may happen that Releases with the same 'distribution' get added.
    E.g. the uniqueness values of the Release (codename, etc) change over time but the
    distribution value stays the same. If content is now copied from newer versions to older
    versions, the new release will be marked for copying but will clash with the value from the
    base-version.
    """
    release_qs_added = new_version.added(base_version=new_version.base_version).filter(
        pulp_type="deb.release"
    )
    if new_version.base_version:
        release_qs_existing = new_version.base_version.content.filter(pulp_type="deb.release")
    else:
        try:
            release_qs_existing = new_version.previous().content.filter(pulp_type="deb.release")
        except new_version.DoesNotExist:
            release_qs_existing = Release.objects.none()

    if not release_qs_added.count():
        # let's assume the previous version is valid
        return

    dup_releases = []
    for new_rel in release_qs_added.iterator():
        if (
            Release.objects.filter(pk__in=release_qs_existing.filter(pk__ne=new_rel.pk))
            .filter(distribution=new_rel.deb_release.distribution)
            .count()
        ):
            # duplicate found: remove it!
            dup_releases.append(new_rel.pk)

    if dup_releases:
        log.warning(_("Removing duplicate deb.releases from new repo version."))
        new_version.remove_content(Release.objects.filter(pk__in=dup_releases))
