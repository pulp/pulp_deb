from gettext import gettext as _  # noqa

from django_filters import Filter
from pulpcore.plugin.models import Repository, RepositoryVersion
from pulpcore.plugin.serializers.content import ValidationError
from pulpcore.plugin.viewsets import (
    ContentFilter,
    ContentViewSet,
    NamedModelViewSet,
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


class ContentRelationshipFilter(Filter):
    """
    Base class for filters that allow you to ask meaningful questions about the relationships of
    deb-specific content types. Subclasses must provide a HELP message and implement _filter.

    The value for all these filters is a string that is a comma-separated 2-tuple, where the second
    value is the HREF of the RepositoryVersion you care about. This is logically necessary if you
    want to ask any question beyond "list Package|ReleaseComponent|whatever that were ever at any
    point in this Repository|Release|whatever". I will try to explain by example.

    Question: "What Packages are in the most recent RepositoryVersion of a Release?"

    Imagine we have a very simple repo with two packages and two releases, and this state is stored
    in RepositoryVersion1:
    Repository -> Release1 -> ReleaseComponent1 -> PackageReleaseComponent1 -> Package1
                                                -> PackageReleaseComponent2 -> Package2
               -> Release2 -> ReleaseComponent2 -> PackageReleaseComponent3 -> Package2

    We then update the repo to remove Package2 from ReleaseComponent1 and this state gets stored
    in RepositoryVersion2:
    Repository -> Release1 -> ReleaseComponent1 -> PackageReleaseComponent1 -> Package1
               -> Release2 -> ReleaseComponent2 -> PackageReleaseComponent3 -> Package2

    We could try answer the question using the existing ContentFilter.repository_version filter in
    conjunction with a new filter that naively follows the foreign key references in the database:
    packages.filter(deb_packagereleasecomponent__release_component__release=release_uuid)

    What Django does if you call two separate filters is use the first to filter the QuerySet,
    then use the second to filter the QuerySet further. This is *different* than calling
    filter once with both conditions.
    https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships

    Example: packages.filter("in RepositoryVersion2").filter("in Release1")
    This will return both Package1 and Package2, which is not what we wanted. In the first filter it
    looks and says "yep, both Package1 and Package2 are in RepositoryVersion2", and then the second
    filter is applied and it says "yep, both Package1 and Package2 were in Release1 at some point".
    This is because the linkage via PackageReleaseComponent2 still *exists*, it's just not in
    RepositoryVersion2.

    What we really _actually_ want is to apply _both_ conditions to the PackageReleaseComponent
    mapping as an intermediate step, so both release_uuid and repository_version_href must be
    passed to our new filter:
    packages.filter(package.PRC in PRC.filter("in RepositoryVersion2", "in Release1"))

    This guarantees that we are only considering Packages with both requirements, and returns only
    Package1.
    """

    HELP = "Override with your value-specific help message"
    ARG = "Override with the type of your arg, for example package_href"
    ARG_CLASS = models.Package  # Override with the correct model in subclass
    GENERIC_HELP = """
    Must be a comma-separated string: "{arg},repository_or_repository_version_href"
    {arg}: {help}
    repository_or_repository_version_href: The RepositoryVersion href to filter by, or Repository
        href (assume latest version)
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "help_text", _(self.GENERIC_HELP).format(arg=_(self.ARG), help=_(self.HELP))
        )
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        """
        Args:
            qs (django.db.models.query.QuerySet): The Content Queryset
            value (string, "value,repository_version_href"): The values to filter by
        """
        if value is None:
            # user didn't supply a value
            return qs

        repo_version: RepositoryVersion = None
        arg_href, r_or_rv_href = value.split(",", 1)
        if not arg_href or not r_or_rv_href or "," in r_or_rv_href:
            raise ValidationError(detail=_("Unparsable argument supplied for content filter"))

        repo_version = NamedModelViewSet.get_resource(r_or_rv_href)
        if isinstance(repo_version, Repository):
            repo_version = repo_version.latest_version()

        if not isinstance(repo_version, RepositoryVersion):
            raise ValidationError(
                detail=_("Could not resolve a RepositoryVersion from content filter argument")
            )

        arg_instance = NamedModelViewSet.get_resource(arg_href, self.ARG_CLASS)
        if not repo_version.content.filter(pk=arg_instance.pk).exists():
            raise ValidationError(
                detail=_("Specified filter argument is not in specified RepositoryVersion")
            )

        return self._filter(qs, arg_instance, repo_version.content)

    def _filter(self, qs, arg, rv_content):
        """
        Args:
            qs (django.db.models.query.QuerySet): The Content Queryset
            arg (ARG_CLASS): The specific self.ARG that we're filtering by
            rv_content (django.db.models.query.QuerySet): QuerySet of Content in
                requested RepositoryVersion
        """
        raise NotImplementedError


class PackageToReleaseComponentFilter(ContentRelationshipFilter):
    HELP = "Filter results where Package in ReleaseComponent"
    ARG = "release_component_href"
    ARG_CLASS = models.ReleaseComponent

    def _filter(self, qs, arg, rv_content):
        prc_qs = models.PackageReleaseComponent.objects.filter(
            pk__in=rv_content, release_component=arg.pk
        )
        return qs.filter(deb_packagereleasecomponent__in=prc_qs)


class PackageToReleaseFilter(ContentRelationshipFilter):
    HELP = "Filter results where Package in Release"
    ARG = "release_href"
    ARG_CLASS = models.Release

    def _filter(self, qs, arg, rv_content):
        prc_qs = models.PackageReleaseComponent.objects.filter(
            pk__in=rv_content, release_component__distribution=arg.distribution
        )
        return qs.filter(deb_packagereleasecomponent__in=prc_qs)


class PackageFilter(ContentFilter):
    """
    FilterSet for Package.
    """

    release_component = PackageToReleaseComponentFilter()
    release = PackageToReleaseFilter()

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


class ReleaseToPackageFilter(ContentRelationshipFilter):
    HELP = "Filter results where Release contains Package"
    ARG = "package_href"
    ARG_CLASS = models.Package

    def _filter(self, qs, arg, rv_content):
        prc_qs = models.PackageReleaseComponent.objects.filter(pk__in=rv_content, package=arg)
        rc_qs = models.ReleaseComponent.objects.filter(
            pk__in=rv_content, deb_packagereleasecomponent__in=prc_qs
        )
        return qs.filter(pk__in=rv_content, distribution__in=rc_qs.values("distribution"))


class ReleaseFilter(ContentFilter):
    """
    FilterSet for Release.
    """

    package = ReleaseToPackageFilter()

    class Meta:
        model = models.Release
        fields = ["codename", "suite", "distribution"]


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


class ReleaseComponentToPackageFilter(ContentRelationshipFilter):
    HELP = "Filter results where ReleaseComponent contains Package"
    ARG = "package_href"
    ARG_CLASS = models.Package

    def _filter(self, qs, arg, rv_content):
        prc_qs = models.PackageReleaseComponent.objects.filter(pk__in=rv_content, package=arg)
        return qs.filter(deb_packagereleasecomponent__in=prc_qs)


class ReleaseComponentFilter(ContentFilter):
    """
    FilterSet for ReleaseComponent.
    """

    package = ReleaseComponentToPackageFilter()

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
