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
    # The doc string is a top level element of the user facing REST API documentation:
    """
    GenericContent is a catch all category for storing files not covered by any other type.

    Associated artifacts: Exactly one arbitrary file that does not match any other type.

    This is needed to store arbitrary files for use with the verbatim publisher. If you are not
    using the verbatim publisher, you may ignore this type.
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
    # The doc string is a top level element of the user facing REST API documentation:
    """
    A Package represents a '.deb' binary package.

    Associated artifacts: Exactly one '.deb' package file.
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
    # The doc string is a top level element of the user facing REST API documentation:
    """
    An InstallerPackage represents a '.udeb' installer package.

    Associated artifacts: Exactly one '.udeb' installer package file.

    Note that installer packages are currently used exclusively for verbatim publications. The APT
    publisher (both simple and structured mode) will not include these packages.
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
    # The doc string is a top level element of the user facing REST API documentation:
    """
    A ReleaseFile represents the Release file(s) from a single APT distribution.

    Associated artifacts: At least one of 'Release' and 'InRelease' file. If the 'Release' file is
    present, then there may also be a 'Release.gpg' detached signature file for it.

    Note: The verbatim publisher will republish all associated artifacts, while the APT publisher
    (both simple and structured mode) will generate any 'Release' files it needs when creating the
    publication. It does not make use of ReleaseFile content.
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
    # The doc string is a top level element of the user facing REST API documentation:
    """
    A PackageIndex represents the package indices of a single component-architecture combination.

    Associated artifacts: Exactly one 'Packages' file. May optionally include one or more of
    'Packages.gz', 'Packages.xz', 'Release'. If included, the 'Release' file is a legacy
    per-component-and-architecture Release file.

    Note: The verbatim publisher will republish all associated artifacts, while the APT publisher
    (both simple and structured mode) will generate any 'Packages' files it needs when creating the
    publication. It does not make use of PackageIndex content.
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
    # The doc string is a top level element of the user facing REST API documentation:
    """
    An InstallerFileIndex represents the indices for a set of installer files.

    Associated artifacts: Exactly one 'SHA256SUMS' and/or 'MD5SUMS' file.

    Each InstallerFileIndes is associated with a single component-architecture combination within
    a single Release. Note that installer files are currently used exclusively for verbatim
    publications. The APT publisher (both simple and structured mode) does not make use of installer
    content.
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
        fields = ["codename", "suite", "distribution", "version", "label", "origin"]


class ReleaseViewSet(ContentViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    The Release contains release file fields, that are not relevant to the APT repo structure.

    Associated artifacts: None; contains only metadata.

    By non-structure relevant release file fields, we mean anything other than the Components and
    Architectures fields. These are handled by their own models and are not part of this model.

    Note that the distribution field is part of this model, but is not added to any published
    release files. The "distribution" is defined as the path between 'dists/' and some 'Release'
    file. As such, it encodes the path to the relevant release file within the APT repository.
    It is often (but not always) equal to the "codename" or the "suite".
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
        fields = ["architecture", "distribution", "codename", "suite"]


class ReleaseArchitectureViewSet(ContentViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    A ReleaseArchitecture represents a single dpkg architecture string.

    Associated artifacts: None; contains only metadata.

    Every ReleaseArchitecture is always associated with exactly one Release. This indicates that
    the release/distribution in question supports this architecture.
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
        fields = ["component", "distribution", "codename", "suite"]


class ReleaseComponentViewSet(ContentViewSet):
    # The doc string is a top level element of the user facing REST API documentation:
    """
    A ReleaseComponent represents a single APT repository component.

    Associated artifacts: None; contains only metadata.
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
    # The doc string is a top level element of the user facing REST API documentation:
    """
    A PackageReleaseComponent associates a Package with a ReleaseComponent.

    Associated artifacts: None; contains only metadata.

    This simply stores the information which packages are part of which components.
    """

    endpoint_name = "package_release_components"
    queryset = models.PackageReleaseComponent.objects.all()
    serializer_class = serializers.PackageReleaseComponentSerializer
    filterset_class = PackageReleaseComponentFilter
