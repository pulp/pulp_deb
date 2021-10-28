from pulpcore.plugin.importexport import BaseContentResource
from pulp_deb.app.models import (
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


class InstallerFileIndexResource(BaseContentResource):
    """
    Resource for import/export of apt_installerfileindex entities.
    """

    class Meta:
        model = InstallerFileIndex
        import_id_fields = model.natural_key_fields()


class PackageResource(BaseContentResource):
    """
    Resource for import/export of apt_package entities.
    """

    class Meta:
        model = Package
        import_id_fields = model.natural_key_fields()


class InstallerPackageResource(BaseContentResource):
    """
    Resource for import/export of apt_installerpackage entities.
    """

    class Meta:
        model = InstallerPackage
        import_id_fields = model.natural_key_fields()


class GenericContentResource(BaseContentResource):
    """
    Resource for import/export of apt_genericcontent entities.
    """

    class Meta:
        model = GenericContent
        import_id_fields = model.natural_key_fields()


class PackageIndexResource(BaseContentResource):
    """
    Resource for import/export of apt_packageindex entities.
    """

    class Meta:
        model = PackageIndex
        import_id_fields = model.natural_key_fields()


class ReleaseArchitectureResource(BaseContentResource):
    """
    Resource for import/export of apt_releasearchitecture entities.
    """

    class Meta:
        model = ReleaseArchitecture
        import_id_fields = model.natural_key_fields()


class ReleaseComponentResource(BaseContentResource):
    """
    Resource for import/export of apt_releasecomponent entities.
    """

    class Meta:
        model = ReleaseComponent
        import_id_fields = model.natural_key_fields()


class ReleaseFileResource(BaseContentResource):
    """
    Resource for import/export of apt_releasefile entities.
    """

    class Meta:
        model = ReleaseFile
        import_id_fields = model.natural_key_fields()


class PackageReleaseComponentResource(BaseContentResource):
    """
    Resource for import/export of apt_packagereleasecomponent entities.
    """

    class Meta:
        model = PackageReleaseComponent
        import_id_fields = model.natural_key_fields()


class ReleaseResource(BaseContentResource):
    """
    Resource for import/export of apt_release entities.
    """

    class Meta:
        model = Release
        import_id_fields = model.natural_key_fields()


IMPORT_ORDER = [
    InstallerFileIndexResource,
    ReleaseArchitectureResource,
    ReleaseComponentResource,
    ReleaseFileResource,
    PackageReleaseComponentResource,
    ReleaseResource,
    PackageResource,
    InstallerPackageResource,
    PackageIndexResource,
    GenericContentResource,
]
