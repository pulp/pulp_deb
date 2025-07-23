"""Models to represent APT repository structure.

This module contains Pulp content models that are used to represent APT repository structure. In
particular this information is used to encode what packages, belong into what package indices within
the repo. This implies encoding the available distributions/releases, the available components and
supported architectures within those releases, as well as the mapping of which packages belongs into
which components.

IMPORTANT: It is essential that these models don't contain anything that isn't structure
information. This ensures, that copying structure content between different Pulp repositories, does
not inadvertantly copy anything that is not structure relevant.
"""

import os

from django.db import models

from pulpcore.plugin.models import Content
from pulpcore.plugin.util import get_domain_pk

from pulp_deb.app.models import Package, SourcePackage


BOOL_CHOICES = [(True, "yes"), (False, "no")]


class ReleaseArchitecture(Content):
    """
    This model represents a machine architecture within an APT repository distribution.

    The architecture field must be given by a string as follows:
    https://www.debian.org/doc/debian-policy/ch-customized-programs.html#s-arch-spec

    The meaning of a content of this model, is that the release found at the given distribution
    supports the given architecture. This in turn implies publishing package indices for those
    architectures irrespective of whether there are actually any architecture specific packages.
    """

    TYPE = "release_architecture"

    distribution = models.TextField()
    architecture = models.TextField()
    _pulp_domain = models.ForeignKey("core.Domain", default=get_domain_pk, on_delete=models.PROTECT)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("distribution", "architecture", "_pulp_domain"),)


class ReleaseComponent(Content):
    """
    This model represents an APT repository component within an APT repository distribution.

    The information stored in this model implies knowledge of where various APT metadata files need
    to be placed relative to the repo root, and thus defines the APT repo's metadata structure.
    """

    TYPE = "release_component"

    distribution = models.TextField()
    component = models.TextField()
    _pulp_domain = models.ForeignKey("core.Domain", default=get_domain_pk, on_delete=models.PROTECT)

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
        unique_together = (("distribution", "component", "_pulp_domain"),)


class PackageReleaseComponent(Content):
    """
    The PackageReleaseComponent.

    This is the join table that decides, which Packages (in which RepositoryVersions) belong to
    which ReleaseComponents.
    """

    TYPE = "package_release_component"

    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    release_component = models.ForeignKey(ReleaseComponent, on_delete=models.CASCADE)
    _pulp_domain = models.ForeignKey("core.Domain", default=get_domain_pk, on_delete=models.PROTECT)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("package", "release_component", "_pulp_domain"),)


class SourcePackageReleaseComponent(Content):
    """
    The SourcePackageReleaseComponent.

    This is the join table that decides, which Source Package (in which RepositoryVersions) belong
    to which ReleaseComponents.
    """

    TYPE = "source_package_release_component"

    source_package = models.ForeignKey(SourcePackage, on_delete=models.CASCADE)
    release_component = models.ForeignKey(ReleaseComponent, on_delete=models.CASCADE)
    _pulp_domain = models.ForeignKey("core.Domain", default=get_domain_pk, on_delete=models.PROTECT)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("source_package", "release_component", "_pulp_domain"),)
