import os

from django.db import models

from django.db.models import JSONField

from pulpcore.plugin.models import Content


BOOL_CHOICES = [(True, "yes"), (False, "no")]


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
