import os

from django.db import models

from django.db.models import JSONField

from pulpcore.plugin.models import Content


BOOL_CHOICES = [(True, "yes"), (False, "no")]


class GenericContent(Content):
    """
    The "generic" content.

    This model is meant to map to all files in the upstream repository, that
    are not handled by a more specific model.
    Those units are used for the verbatim publish method.
    """

    TYPE = "generic"

    relative_path = models.TextField(null=False)
    sha256 = models.CharField(max_length=255, null=False)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("relative_path", "sha256"),)


class ReleaseFile(Content):
    """
    The "ReleaseFile" content.

    This model holds an artifact to the upstream Release file.
    """

    TYPE = "release_file"
    SUPPORTED_ARTIFACTS = ["Release", "InRelease", "Release.gpg"]

    codename = models.TextField()
    suite = models.TextField()
    distribution = models.TextField()
    components = models.TextField(blank=True)
    architectures = models.TextField(blank=True)
    relative_path = models.TextField()
    sha256 = models.CharField(max_length=255)
    artifact_set_sha256 = models.CharField(max_length=255)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (
            (
                "codename",
                "suite",
                "distribution",
                "components",
                "architectures",
                "relative_path",
                "sha256",
                "artifact_set_sha256",
            ),
        )

    @property
    def main_artifact(self):
        """
        Retrieve the plain ReleaseFile artifact.
        """
        return self._artifacts.get(sha256=self.sha256)


class PackageIndex(Content):
    """
    The "PackageIndex" content type.

    This model represents the Packages file(s) for a specific component - architecture combination
    (or an entire flat repo). The artifacts will always include the uncompressed Packages file, as
    well as any compressed package indices using an archive format supported by pulp_deb.
    """

    TYPE = "package_index"
    SUPPORTED_ARTIFACTS = ["Packages", "Packages.gz", "Packages.xz", "Release"]

    release = models.ForeignKey(ReleaseFile, on_delete=models.CASCADE)
    component = models.TextField()
    architecture = models.TextField()
    relative_path = models.TextField()
    sha256 = models.CharField(max_length=255)
    artifact_set_sha256 = models.CharField(max_length=255)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        verbose_name_plural = "PackageIndices"
        unique_together = (("relative_path", "sha256", "artifact_set_sha256"),)

    @property
    def main_artifact(self):
        """
        Retrieve the uncompressed PackageIndex artifact.
        """
        return self._artifacts.get(sha256=self.sha256)


class InstallerFileIndex(Content):
    """
    The "InstallerFileIndex" content type.

    This model represents the MD5SUMS and SHA256SUMS files for a specific
    component - architecture combination.
    It's artifacts should include all available versions of those SUM-files
    with the sha256-field pointing to the one with the sha256 algorithm.
    """

    TYPE = "installer_file_index"

    FILE_ALGORITHM = {"SHA256SUMS": "sha256", "MD5SUMS": "md5"}  # Are there more?

    release = models.ForeignKey(ReleaseFile, on_delete=models.CASCADE)
    component = models.TextField()
    architecture = models.TextField()
    relative_path = models.TextField()
    sha256 = models.CharField(max_length=255)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        verbose_name_plural = "InstallerFileIndices"
        unique_together = (("relative_path", "sha256"),)

    @property
    def main_artifact(self):
        """
        Retrieve the uncompressed SHA256SUMS artifact.
        """
        return self._artifacts.get(sha256=self.sha256)


class BasePackage(Content):
    """
    Abstract base class for package like content.
    """

    MULTIARCH_CHOICES = [
        ("no", "no"),
        ("same", "same"),
        ("foreign", "foreign"),
        ("allowed", "allowed"),
    ]

    package = models.TextField()  # package name
    source = models.TextField(null=True)  # source package name
    version = models.TextField()
    architecture = models.TextField()  # all, i386, ...
    section = models.TextField(null=True)  # admin, comm, database, ...
    priority = models.TextField(null=True)  # required, standard, optional, extra
    origin = models.TextField(null=True)
    tag = models.TextField(null=True)
    bugs = models.TextField(null=True)
    essential = models.BooleanField(null=True, choices=BOOL_CHOICES)
    build_essential = models.BooleanField(null=True, choices=BOOL_CHOICES)
    installed_size = models.IntegerField(null=True)
    maintainer = models.TextField()
    original_maintainer = models.TextField(null=True)
    description = models.TextField()
    description_md5 = models.TextField(null=True)
    homepage = models.TextField(null=True)
    built_using = models.TextField(null=True)
    auto_built_package = models.TextField(null=True)
    multi_arch = models.TextField(null=True, choices=MULTIARCH_CHOICES)

    # Depends et al
    breaks = models.TextField(null=True)
    conflicts = models.TextField(null=True)
    depends = models.TextField(null=True)
    recommends = models.TextField(null=True)
    suggests = models.TextField(null=True)
    enhances = models.TextField(null=True)
    pre_depends = models.TextField(null=True)
    provides = models.TextField(null=True)
    replaces = models.TextField(null=True)

    # relative path in the upstream repository
    relative_path = models.TextField(null=False)
    # this digest is transferred to the content as a natural_key
    sha256 = models.TextField(null=False)

    custom_fields = JSONField(null=True)

    @property
    def name(self):
        """Print a nice name for Packages."""
        return "{}_{}_{}".format(self.package, self.version, self.architecture)

    def filename(self, component=""):
        """Assemble filename in pool directory."""
        sourcename = self.source or self.package
        sourcename = sourcename.split("(", 1)[0].rstrip()
        if sourcename.startswith("lib"):
            prefix = sourcename[0:4]
        else:
            prefix = sourcename[0]
        return os.path.join(
            "pool",
            component,
            prefix,
            sourcename,
            "{}.{}".format(self.name, self.SUFFIX),
        )

    repo_key_fields = ("package", "version", "architecture")

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("relative_path", "sha256"),)
        abstract = True


class Package(BasePackage):
    """
    The "package" content type.

    This model must contain all information that is needed to
    generate the corresponding paragraph in "Packages" files.
    """

    TYPE = "package"

    SUFFIX = "deb"

    class Meta(BasePackage.Meta):
        pass


class InstallerPackage(BasePackage):
    """
    The "installer_package" content type.

    This model must contain all information that is needed to
    generate the corresponding paragraph in "Packages" files.
    """

    TYPE = "installer_package"

    SUFFIX = "udeb"

    class Meta(BasePackage.Meta):
        pass


class Release(Content):
    """
    The "Release" content.

    This model represents a debian release.
    """

    TYPE = "release"

    codename = models.TextField()
    suite = models.TextField()
    distribution = models.TextField()

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("codename", "suite", "distribution"),)


class ReleaseArchitecture(Content):
    """
    The ReleaseArchitecture content.

    This model represents an architecture in association to a Release.
    """

    TYPE = "release_architecture"

    architecture = models.TextField()
    release = models.ForeignKey(Release, on_delete=models.CASCADE)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("architecture", "release"),)


class ReleaseComponent(Content):
    """
    The ReleaseComponent content.

    This model represents a repository component in association to a Release.
    """

    TYPE = "release_component"

    component = models.TextField()
    release = models.ForeignKey(Release, on_delete=models.CASCADE)

    @property
    def plain_component(self):
        """
        The "plain_component" returns the component WITHOUT path prefixes.

        When a Release file is not stored in a directory directly beneath "dists/",
        the components, as stored in the Release file, may be prefixed with the
        path following the directory beneath "dists/".

        e.g.: If a Release file is stored at "REPO_BASE/dists/something/extra/Release",
        then a component normally named "main" may be stored as "extra/main".

        See also: https://wiki.debian.org/DebianRepository/Format#Components
        """
        return os.path.basename(self.component)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("component", "release"),)


class PackageReleaseComponent(Content):
    """
    The PackageReleaseComponent.

    This is the join table that decides, which Packages (in which RepositoryVersions) belong to
    which ReleaseComponents.
    """

    TYPE = "package_release_component"

    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    release_component = models.ForeignKey(ReleaseComponent, on_delete=models.CASCADE)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("package", "release_component"),)
