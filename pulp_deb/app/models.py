import os

from logging import getLogger

from debian import deb822

from django.db import models

from pulpcore.plugin.models import (
    Artifact,
    Content,
    Publication,
    PublicationDistribution,
    Remote,
    RemoteArtifact,
    Repository,
)

logger = getLogger(__name__)

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

    This model holds an artifact to the upstream Release file at the same time.
    """

    TYPE = "release_file"

    codename = models.CharField(max_length=255)
    suite = models.CharField(max_length=255)
    distribution = models.CharField(max_length=255)
    components = models.CharField(max_length=255, blank=True)
    architectures = models.CharField(max_length=255, blank=True)
    relative_path = models.TextField()
    sha256 = models.CharField(max_length=255)

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
            ),
        )


class PackageIndex(Content):
    """
    The "PackageIndex" content type.

    This model represents the Packages file for a specific
    component - architecture combination.
    It's artifacts should include all (non-)compressed versions
    of the upstream Packages file.
    """

    TYPE = "package_index"

    release = models.ForeignKey(ReleaseFile, on_delete=models.CASCADE)
    component = models.CharField(max_length=255)
    architecture = models.CharField(max_length=255)
    relative_path = models.TextField()
    sha256 = models.CharField(max_length=255)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        verbose_name_plural = "PackageIndices"
        unique_together = (("relative_path", "sha256"),)

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
    with the sha256-field pointing to the one with the strongest algorithm.
    """

    TYPE = "installer_file_index"

    FILE_ALGORITHM = {"SHA256SUMS": "sha256", "MD5SUMS": "md5"}  # Are there more?

    release = models.ForeignKey(ReleaseFile, on_delete=models.CASCADE)
    component = models.CharField(max_length=255)
    architecture = models.CharField(max_length=255)
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

    TRANSLATION_DICT = {
        "package": "Package",
        "source": "Source",
        "version": "Version",
        "architecture": "Architecture",
        "section": "Section",
        "priority": "Priority",
        "origin": "Origin",
        "tag": "Tag",
        "bugs": "Bugs",
        "essential": "Essential",
        "build_essential": "Build_essential",
        "installed_size": "Installed_size",
        "maintainer": "Maintainer",
        "original_maintainer": "Original_Maintainer",
        "description": "Description",
        "description_md5": "Description_MD5",
        "homepage": "Homepage",
        "built_using": "Built_Using",
        "auto_built_package": "Auto_Built_Package",
        "multi_arch": "Multi_Arch",
        "breaks": "Breaks",
        "conflicts": "Conflicts",
        "depends": "Depends",
        "recommends": "Recommends",
        "suggests": "Suggests",
        "enhances": "Enhances",
        "pre_depends": "Pre_Depends",
        "provides": "Provides",
        "replaces": "Replaces",
    }

    MULTIARCH_CHOICES = [
        ("no", "no"),
        ("same", "same"),
        ("foreign", "foreign"),
        ("allowed", "allowed"),
    ]

    package = models.CharField(max_length=255)  # package name
    source = models.CharField(max_length=255, null=True)  # source package name
    version = models.CharField(max_length=255)
    architecture = models.CharField(max_length=255)  # all, i386, ...
    section = models.CharField(max_length=255, null=True)  # admin, comm, database, ...
    priority = models.CharField(max_length=255, null=True)  # required, standard, optional, extra
    origin = models.CharField(max_length=255, null=True)
    tag = models.TextField(null=True)
    bugs = models.TextField(null=True)
    essential = models.BooleanField(null=True, choices=BOOL_CHOICES)
    build_essential = models.BooleanField(null=True, choices=BOOL_CHOICES)
    installed_size = models.IntegerField(null=True)
    maintainer = models.CharField(max_length=255)
    original_maintainer = models.CharField(max_length=255, null=True)
    description = models.TextField()
    description_md5 = models.CharField(max_length=255, null=True)
    homepage = models.CharField(max_length=255, null=True)
    built_using = models.CharField(max_length=255, null=True)
    auto_built_package = models.CharField(max_length=255, null=True)
    multi_arch = models.CharField(max_length=255, null=True, choices=MULTIARCH_CHOICES)

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
    sha256 = models.CharField(max_length=255, null=False)

    @property
    def name(self):
        """Print a nice name for Packages."""
        return "{}_{}_{}".format(self.package, self.version, self.architecture)

    def filename(self, component=""):
        """Assemble filename in pool directory."""
        sourcename = self.source or self.package
        if sourcename.startswith("lib"):
            prefix = sourcename[0:4]
        else:
            prefix = sourcename[0]
        return os.path.join(
            "pool", component, prefix, sourcename, "{}.{}".format(self.name, self.SUFFIX)
        )

    def to822(self, component=""):
        """Create deb822.Package object from model."""
        ret = deb822.Packages()

        for k, v in self.TRANSLATION_DICT.items():
            value = getattr(self, k, None)
            if value is not None:
                ret[v] = value

        try:
            artifact = self._artifacts.get()
            ret["MD5sum"] = artifact.md5
            ret["SHA1"] = artifact.sha1
            ret["SHA256"] = artifact.sha256
        except Artifact.DoesNotExist:
            remote_artifact = RemoteArtifact.objects.filter(sha256=self.sha256).first()
            ret["MD5sum"] = remote_artifact.md5
            ret["SHA1"] = remote_artifact.sha1
            ret["SHA256"] = remote_artifact.sha256

        ret["Filename"] = self.filename(component)

        return ret

    @classmethod
    def from822(cls, package_dict):
        """
        Translate deb822.Package to a dictionary for class instatiation.
        """
        return {k: package_dict[v] for k, v in cls.TRANSLATION_DICT.items() if v in package_dict}

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


class VerbatimPublication(Publication):
    """
    A verbatim Publication for Content.

    This publication publishes the obtained metadata unchanged.
    """

    TYPE = "verbatim-publication"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class DebPublication(Publication):
    """
    A Publication for DebContent.

    This publication recreates all metadata.
    """

    TYPE = "apt-publication"

    simple = models.BooleanField(default=False)
    structured = models.BooleanField(default=False)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class DebDistribution(PublicationDistribution):
    """
    A Distribution for DebContent.
    """

    TYPE = "apt-distribution"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class DebRemote(Remote):
    """
    A Remote for DebContent.
    """

    TYPE = "apt-remote"

    distributions = models.CharField(max_length=255, null=True)
    components = models.CharField(max_length=255, null=True)
    architectures = models.CharField(max_length=255, null=True)
    sync_sources = models.BooleanField(default=False)
    sync_udebs = models.BooleanField(default=False)
    sync_installer = models.BooleanField(default=False)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class DebRepository(Repository):
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
    ]

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
