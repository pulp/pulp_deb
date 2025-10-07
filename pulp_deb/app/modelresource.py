from import_export import fields
from import_export.widgets import ForeignKeyWidget

from pulpcore.plugin.importexport import BaseContentResource
from pulpcore.plugin.modelresources import RepositoryResource
from pulpcore.plugin.util import get_domain

from pulp_deb.app.models import (
    AptRepository,
    GenericContent,
    InstallerFileIndex,
    Package,
    PackageIndex,
    InstallerPackage,
    PackageReleaseComponent,
    Release,
    ReleaseArchitecture,
    ReleaseComponent,
    ReleaseFile,
)


class DebContentResource(BaseContentResource):
    """
    Resource for import/export of deb content.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the DebContentResource
        """
        self.content_mapping = {}
        super().__init__(*args, **kwargs)

    def _add_to_mapping(self, repo, uuids):
        if not uuids.exists():
            return

        self.content_mapping[repo.name] = list(map(str, uuids))

    def set_up_queryset(self):
        """
        Return Content for a RepositoryVersion while populating content_mapping.

        Returns:
            django.db.models.QuerySet: The Content to export for a RepositoryVersion.
        """
        content = self.Meta.model.objects.filter(pk__in=self.repo_version.content).order_by(
            "content_ptr_id"
        )

        self._add_to_mapping(
            self.repo_version.repository, content.values_list("pulp_id", flat=True)
        )

        return content

    def dehydrate__pulp_domain(self, content):
        return str(content._pulp_domain_id)


class InstallerFileIndexResource(DebContentResource):
    """
    Resource for import/export of apt_installerfileindex entities.
    """

    class Meta:
        model = InstallerFileIndex
        import_id_fields = model.natural_key_fields()


class PackageResource(DebContentResource):
    """
    Resource for import/export of apt_package entities.
    """

    def before_import_row(self, row, **kwargs):
        super().before_import_row(row, **kwargs)
        to_delete_fields = []
        for k, v in row.items():
            if v == "":
                to_delete_fields.append(k)
        for i in to_delete_fields:
            del row[i]

    class Meta:
        model = Package
        import_id_fields = model.natural_key_fields()


class InstallerPackageResource(DebContentResource):
    """
    Resource for import/export of apt_installerpackage entities.
    """

    class Meta:
        model = InstallerPackage
        import_id_fields = model.natural_key_fields()


class GenericContentResource(DebContentResource):
    """
    Resource for import/export of apt_genericcontent entities.
    """

    class Meta:
        model = GenericContent
        import_id_fields = model.natural_key_fields()


class PackageIndexResource(DebContentResource):
    """
    Resource for import/export of apt_packageindex entities.
    """

    class Meta:
        model = PackageIndex
        import_id_fields = model.natural_key_fields()


class ReleaseArchitectureResource(DebContentResource):
    """
    Resource for import/export of apt_releasearchitecture entities.
    """

    class Meta:
        model = ReleaseArchitecture
        import_id_fields = model.natural_key_fields()


class ReleaseComponentResource(DebContentResource):
    """
    Resource for import/export of apt_releasecomponent entities.
    """

    class Meta:
        model = ReleaseComponent
        import_id_fields = model.natural_key_fields()


class ReleaseFileResource(DebContentResource):
    """
    Resource for import/export of apt_releasefile entities.
    """

    class Meta:
        model = ReleaseFile
        import_id_fields = model.natural_key_fields()


class PackageReleaseComponentResource(DebContentResource):
    """
    Resource for import/export of apt_packagereleasecomponent entities.
    """

    class ReleaseComponentForeignKeyWidget(ForeignKeyWidget):
        """
        Class that lets us specify a multi-key link to ReleaseComponent.

        Format to be used at import-row time is:
        str(<release_component.distribution>|<release_component.component>)
        """

        def render(self, value, obj=None, **kwargs):
            """Render formatted string to use as unique-identifier."""
            rc_dist = value.distribution
            rc_comp = value.component
            return f"{rc_dist}|{rc_comp}"

    class PackageForeignKeyWidget(ForeignKeyWidget):
        """
        Class that lets us specify a multi-key link to Package.

        Format to be used at import-row time is:
        str(<package.relative_path>|<package.sha256>)
        """

        def render(self, value, obj=None, **kwargs):
            """Render formatted string to use as unique-identifier."""
            pkg_relative_path = value.relative_path
            pkg_sha256 = value.sha256
            return f"{pkg_relative_path}|{pkg_sha256}"

    release_component = fields.Field(
        column_name="release_component",
        attribute="release_component",
        widget=ReleaseComponentForeignKeyWidget(ReleaseComponent),
    )

    package = fields.Field(
        column_name="package",
        attribute="package",
        widget=PackageForeignKeyWidget(Package),
    )

    def before_import_row(self, row, **kwargs):
        """
        Finds and sets release_component using upstream_id.

        Args:
            row (tablib.Dataset row): incoming import-row representing a single PRC.
            kwargs: args passed along from the import() call.
        """
        super().before_import_row(row, **kwargs)

        (rc_dist, rc_comp) = row["release_component"].split("|")
        (pkg_relative_path, pkg_sha256) = row["package"].split("|")
        rc = ReleaseComponent.objects.filter(
            distribution=rc_dist, component=rc_comp, pulp_domain=get_domain()
        ).first()
        pkg = Package.objects.filter(
            relative_path=pkg_relative_path, sha256=pkg_sha256, pulp_domain=get_domain()
        ).first()
        row["release_component"] = str(rc.pulp_id)
        row["package"] = str(pkg.pulp_id)

    class Meta:
        model = PackageReleaseComponent
        import_id_fields = model.natural_key_fields()


class ReleaseResource(DebContentResource):
    """
    Resource for import/export of apt_release entities.
    """

    class Meta:
        model = Release
        import_id_fields = model.natural_key_fields()


class AptRepositoryResource(RepositoryResource):
    """
    A resource for import/export Deb repository entities.
    """

    def set_up_queryset(self):
        """
        Set up a queryset for DebRepositories.

        Returns:
            A queryset containing one repository that will be exported.
        """
        return AptRepository.objects.filter(pk=self.repo_version.repository)

    class Meta:
        model = AptRepository
        exclude = RepositoryResource.Meta.exclude + ("most_recent_version",)


IMPORT_ORDER = [
    AptRepositoryResource,
    PackageResource,
    InstallerPackageResource,
    ReleaseResource,
    InstallerFileIndexResource,
    ReleaseArchitectureResource,
    ReleaseComponentResource,
    PackageReleaseComponentResource,
    ReleaseFileResource,
    PackageIndexResource,
    GenericContentResource,
]
