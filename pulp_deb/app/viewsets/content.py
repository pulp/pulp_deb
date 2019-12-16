from gettext import gettext as _  # noqa

from pulpcore.plugin.viewsets import (
    ContentViewSet,
    ContentFilter,
    SingleArtifactContentUploadViewSet,
)

from pulp_deb.app import models, serializers


class GenericContentFilter(ContentFilter):
    """
    FilterSet for GenericContent.
    """

    class Meta:
        model = models.GenericContent
        fields = ["relative_path", "sha256"]


class GenericContentViewSet(SingleArtifactContentUploadViewSet):
    """
    A ViewSet for GenericContent.
    """

    endpoint_name = "generic_contents"
    queryset = models.GenericContent.objects.prefetch_related("_artifacts")
    serializer_class = serializers.GenericContentSerializer
    filterset_class = GenericContentFilter


class PackageFilter(ContentFilter):
    """
    FilterSet for Package.
    """

    class Meta:
        model = models.Package
        fields = [
            "package",
            "source",
            "version",
            "architecture",
            "section",
            "priority",
            "origin",
            "tag",
            "essential",
            "build_essential",
            "installed_size",
            "maintainer",
            "original_maintainer",
            "built_using",
            "auto_built_package",
            "multi_arch",
            "sha256",
            "relative_path",
        ]


class PackageViewSet(SingleArtifactContentUploadViewSet):
    """
    A ViewSet for Package.
    """

    endpoint_name = "packages"
    queryset = models.Package.objects.prefetch_related("_artifacts")
    serializer_class = serializers.PackageSerializer
    filterset_class = PackageFilter


class InstallerPackageFilter(ContentFilter):
    """
    FilterSet for InstallerPackage.
    """

    class Meta:
        model = models.InstallerPackage
        fields = [
            "package",
            "source",
            "version",
            "architecture",
            "section",
            "priority",
            "origin",
            "tag",
            "essential",
            "build_essential",
            "installed_size",
            "maintainer",
            "original_maintainer",
            "built_using",
            "auto_built_package",
            "multi_arch",
            "sha256",
        ]


class InstallerPackageViewSet(SingleArtifactContentUploadViewSet):
    """
    A ViewSet for InstallerPackage.
    """

    endpoint_name = "installer_packages"
    queryset = models.InstallerPackage.objects.prefetch_related("_artifacts")
    serializer_class = serializers.InstallerPackageSerializer
    filterset_class = InstallerPackageFilter


# Metadata


class ReleaseFileFilter(ContentFilter):
    """
    FilterSet for ReleaseFile.
    """

    class Meta:
        model = models.ReleaseFile
        fields = ["codename", "suite", "relative_path", "sha256"]


class ReleaseFileViewSet(ContentViewSet):
    """
    A ViewSet for ReleaseFile.
    """

    endpoint_name = "release_files"
    queryset = models.ReleaseFile.objects.all()
    serializer_class = serializers.ReleaseFileSerializer
    filterset_class = ReleaseFileFilter


class PackageIndexFilter(ContentFilter):
    """
    FilterSet for PackageIndex.
    """

    class Meta:
        model = models.PackageIndex
        fields = ["component", "architecture", "relative_path", "sha256"]


class PackageIndexViewSet(ContentViewSet):
    """
    A ViewSet for PackageIndex.
    """

    endpoint_name = "package_indices"
    queryset = models.PackageIndex.objects.all()
    serializer_class = serializers.PackageIndexSerializer
    filterset_class = PackageIndexFilter


class InstallerFileIndexFilter(ContentFilter):
    """
    FilterSet for InstallerFileIndex.
    """

    class Meta:
        model = models.InstallerFileIndex
        fields = ["component", "architecture", "relative_path", "sha256"]


class InstallerFileIndexViewSet(ContentViewSet):
    """
    A ViewSet for InstallerFileIndex.
    """

    endpoint_name = "installer_file_indices"
    queryset = models.InstallerFileIndex.objects.all()
    serializer_class = serializers.InstallerFileIndexSerializer
    filterset_class = InstallerFileIndexFilter


class ReleaseFilter(ContentFilter):
    """
    FilterSet for Release.
    """

    class Meta:
        model = models.Release
        fields = ["codename", "suite", "distribution"]


class ReleaseViewSet(ContentViewSet):
    """
    A ViewSet for Release.
    """

    endpoint_name = "releases"
    queryset = models.Release.objects.all()
    serializer_class = serializers.ReleaseSerializer
    filterset_class = ReleaseFilter


class ReleaseArchitectureFilter(ContentFilter):
    """
    FilterSet for ReleaseArchitecture.
    """

    class Meta:
        model = models.ReleaseArchitecture
        fields = ["architecture", "release"]


class ReleaseArchitectureViewSet(ContentViewSet):
    """
    A ViewSet for ReleaseArchitecture.
    """

    endpoint_name = "release_architectures"
    queryset = models.ReleaseArchitecture.objects.all()
    serializer_class = serializers.ReleaseArchitectureSerializer
    filterset_class = ReleaseArchitectureFilter


class ReleaseComponentFilter(ContentFilter):
    """
    FilterSet for ReleaseComponent.
    """

    class Meta:
        model = models.ReleaseComponent
        fields = ["component", "release"]


class ReleaseComponentViewSet(ContentViewSet):
    """
    A ViewSet for ReleaseComponent.
    """

    endpoint_name = "release_components"
    queryset = models.ReleaseComponent.objects.all()
    serializer_class = serializers.ReleaseComponentSerializer
    filterset_class = ReleaseComponentFilter


class PackageReleaseComponentFilter(ContentFilter):
    """
    FilterSet for PackageReleaseComponent.
    """

    class Meta:
        model = models.PackageReleaseComponent
        fields = ["package", "release_component"]


class PackageReleaseComponentViewSet(ContentViewSet):
    """
    A ViewSet for PackageReleaseComponent.
    """

    endpoint_name = "package_release_components"
    queryset = models.PackageReleaseComponent.objects.all()
    serializer_class = serializers.PackageReleaseComponentSerializer
    filterset_class = PackageReleaseComponentFilter
