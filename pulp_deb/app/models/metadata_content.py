from django.db import models

from pulpcore.plugin.models import Content


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
