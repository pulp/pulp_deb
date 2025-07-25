"""Models to represent APT repository metadata as used for verbatim publications.

This module contains Pulp content models that are used to represent APT repository metadata, exactly
(down to the checksum) as it was synced from some upstream APT repostiroy. These metadata types are
exclusively used for verbatim publications.
"""

from django.db import models

from pulpcore.plugin.models import Content
from pulpcore.plugin.util import get_domain_pk


BOOL_CHOICES = [(True, "yes"), (False, "no")]


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
    _pulp_domain = models.ForeignKey("core.Domain", default=get_domain_pk, on_delete=models.PROTECT)

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
                "_pulp_domain",
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

    component = models.TextField()
    architecture = models.TextField()
    relative_path = models.TextField()
    sha256 = models.CharField(max_length=255)
    artifact_set_sha256 = models.CharField(max_length=255)
    _pulp_domain = models.ForeignKey("core.Domain", default=get_domain_pk, on_delete=models.PROTECT)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        verbose_name_plural = "PackageIndices"
        unique_together = (("relative_path", "sha256", "artifact_set_sha256", "_pulp_domain"),)

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

    component = models.TextField()
    architecture = models.TextField()
    relative_path = models.TextField()
    sha256 = models.CharField(max_length=255)
    _pulp_domain = models.ForeignKey("core.Domain", default=get_domain_pk, on_delete=models.PROTECT)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        verbose_name_plural = "InstallerFileIndices"
        unique_together = (("relative_path", "sha256", "_pulp_domain"),)

    @property
    def main_artifact(self):
        """
        Retrieve the uncompressed SHA256SUMS artifact.
        """
        return self._artifacts.get(sha256=self.sha256)


class SourceIndex(Content):
    """
    The "SourceIndex" content type.

    This model represents the Sources file for a specific
    component.
    It's artifacts should include all (non-)compressed versions
    of the upstream Sources file.
    """

    TYPE = "source_index"

    release = models.ForeignKey(ReleaseFile, on_delete=models.CASCADE)
    component = models.CharField(max_length=255)
    relative_path = models.TextField()
    sha256 = models.CharField(max_length=255)
    _pulp_domain = models.ForeignKey("core.Domain", default=get_domain_pk, on_delete=models.PROTECT)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        verbose_name_plural = "SourceIndices"
        unique_together = (("relative_path", "sha256", "_pulp_domain"),)

    @property
    def main_artifact(self):
        """
        Retrieve teh uncompressed SourceIndex artifact.
        """
        return self._artifacts.get(sha256=self.sha256)
