import os

from django.db import models

from pulpcore.plugin.models import Content

from pulp_deb.app.models import Package


BOOL_CHOICES = [(True, "yes"), (False, "no")]


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
