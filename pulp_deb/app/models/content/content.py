"""Models to represent APT repository content (not metadata).

This module contains what might be termed "normal" Pulp content models. That is content models used
to represent files provided by APT repositories, but not APT repository metadata files. The most
obvious example would be a model to represent .deb packages, but other examples might include things
like language and Debian installer files. Not included are models for metadata files like Release
files or APT repository package indices.
"""

import os

from django.db import models

from django.db.models import JSONField

from pulpcore.plugin.models import Content
from pulpcore.plugin.util import get_domain_pk

from pulp_deb.fields import DebVersionField

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
    version = DebVersionField()
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
    _pulp_domain = models.ForeignKey("core.Domain", default=get_domain_pk, on_delete=models.PROTECT)

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

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("relative_path", "sha256", "_pulp_domain"),)
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
    _pulp_domain = models.ForeignKey("core.Domain", default=get_domain_pk, on_delete=models.PROTECT)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("relative_path", "sha256", "_pulp_domain"),)


class SourcePackage(Content):
    """
    The Debian Source Package (dsc, orig.tar.gz, debian.tar.gz... files) content type.

    This model must contain all information that is needed to
    generate the corresponding paragraph in "Souces" indices files.
    """

    TYPE = "source_package"

    SUFFIX = "dsc"

    relative_path = models.TextField()
    format = models.TextField()  # the format of the source package
    source = models.TextField()  # source package nameformat
    binary = models.TextField(null=True)  # lists binary packages which a source package can produce
    architecture = models.TextField(null=True)  # all, i386, ...
    version = models.TextField()  # The format is: [epoch:]upstream_version[-debian_revision]
    maintainer = models.TextField()
    uploaders = models.TextField(null=True)  # Names and emails of co-maintainers
    homepage = models.TextField(null=True)
    vcs_browser = models.TextField(null=True)
    vcs_arch = models.TextField(null=True)
    vcs_bzr = models.TextField(null=True)
    vcs_cvs = models.TextField(null=True)
    vcs_darcs = models.TextField(null=True)
    vcs_git = models.TextField(null=True)
    vcs_hg = models.TextField(null=True)
    vcs_mtn = models.TextField(null=True)
    vcs_snv = models.TextField(null=True)
    testsuite = models.TextField(null=True)
    dgit = models.TextField(null=True)
    standards_version = models.TextField()  # most recent version of the standards the pkg complies
    build_depends = models.TextField(null=True)
    build_depends_indep = models.TextField(null=True)
    build_depends_arch = models.TextField(null=True)
    build_conflicts = models.TextField(null=True)
    build_conflicts_indep = models.TextField(null=True)
    build_conflicts_arch = models.TextField(null=True)
    package_list = models.TextField(
        null=True
    )  # all the packages that can be built from the source package

    def __init__(self, *args, **kwargs):
        """Sanatize kwargs by removing multi-lists before contructing DscFile"""
        for kw in ["files", "checksums_sha1", "checksums_sha256", "checksums_sha512"]:
            if kw in kwargs:
                kwargs.pop(kw)
        super().__init__(*args, **kwargs)

    @property
    def sha256(self):
        """Return the sha256 of the dsc file."""
        return self.contentartifact_set.get(relative_path=self.relative_path).artifact.sha256

    def derived_dsc_filename(self):
        """Print a nice name for the Dsc file."""
        return "{}_{}.{}".format(self.source, self.version, self.SUFFIX)

    def derived_dir(self, component=""):
        """Assemble full dir in pool directory."""
        sourcename = self.source
        prefix = sourcename[0]
        return os.path.join(
            "pool",
            component,
            prefix,
            sourcename,
        )

    def derived_path(self, name, component=""):
        """Assemble filename in pool directory."""
        return os.path.join(self.derived_dir(component), name)

    @property
    def checksums_sha1(self):
        """Generate 'Checksums-Sha1' list from content artifacts."""
        contents = []
        for content_artifact in self.contentartifact_set.all():
            if content_artifact:
                if content_artifact.artifact:
                    sha1 = content_artifact.artifact.sha1
                    size = content_artifact.artifact.size
                else:
                    remote_artifact = content_artifact.remoteartifact_set.first()
                    sha1 = remote_artifact.sha1
                    size = remote_artifact.size
                # Sha1 is optional so filter out incomplete data
                if sha1 is not None:
                    contents.append(
                        {
                            "name": os.path.basename(content_artifact.relative_path),
                            "sha1": sha1,
                            "size": size,
                        }
                    )
        return contents

    @property
    def checksums_sha256(self):
        """Generate 'Checksums-Sha256' list from content artifacts."""
        contents = []
        for content_artifact in self.contentartifact_set.all():
            if content_artifact:
                if content_artifact.artifact:
                    sha256 = content_artifact.artifact.sha256
                    size = content_artifact.artifact.size
                else:
                    remote_artifact = content_artifact.remoteartifact_set.first()
                    sha256 = remote_artifact.sha256
                    size = remote_artifact.size
                # Sha256 is required so better to not filter out incomplete data
                contents.append(
                    {
                        "name": os.path.basename(content_artifact.relative_path),
                        "sha256": sha256,
                        "size": size,
                    }
                )
        return contents

    @property
    def checksums_sha512(self):
        """Generate 'Checksums-Sha512' list from content artifacts."""
        contents = []
        for content_artifact in self.contentartifact_set.all():
            if content_artifact:
                if content_artifact.artifact:
                    sha512 = content_artifact.artifact.sha512
                    size = content_artifact.artifact.size
                else:
                    remote_artifact = content_artifact.remoteartifact_set.first()
                    sha512 = remote_artifact.sha512
                    size = remote_artifact.size
                # Sha512 is optional so filter out incomplete data
                if sha512 is not None:
                    contents.append(
                        {
                            "name": os.path.basename(content_artifact.relative_path),
                            "sha512": sha512,
                            "size": size,
                        }
                    )
        return contents

    @property
    def files(self):
        """Generate 'Files' list from content artifacts."""
        contents = []
        for content_artifact in self.contentartifact_set.all():
            if content_artifact:
                if content_artifact.artifact:
                    md5 = content_artifact.artifact.md5
                    size = content_artifact.artifact.size
                else:
                    remote_artifact = content_artifact.remoteartifact_set.first()
                    md5 = remote_artifact.md5
                    size = remote_artifact.size
                # md5 is required so better to not filter out incomplete data
                contents.append(
                    {
                        "name": os.path.basename(content_artifact.relative_path),
                        "md5sum": md5,
                        "size": size,
                    }
                )
        return contents

    repo_key_fields = ("source", "version")

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
