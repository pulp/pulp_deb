import os

from logging import getLogger

from django.db import models

from pulpcore.plugin.models import Content, ContentArtifact, Remote, Publisher

logger = getLogger(__name__)


class GenericContent(Content):
    """
    The "generic" content.

    This model is meant to map to all files in the upstream repository, that
    are not handled by a more specific model.
    Those units are used for the verbatim publish method.
    """

    TYPE = 'generic'

    relative_path = models.TextField(null=False)
    sha256 = models.TextField(null=False)

    @property
    def artifact(self):
        """
        Return the artifact id (there is only one for this content type).
        """
        return self.artifacts.get().pk

    @artifact.setter
    def artifact(self, artifact):
        """
        Set the artifact for this FileContent.
        """
        if self.pk:
            ca = ContentArtifact(artifact=artifact,
                                 content=self,
                                 relative_path=self.relative_path)
            ca.save()

    class Meta:
        unique_together = (
            ('relative_path', 'sha256'),
        )

class Release(Content):
    """
    The "Release" content.

    This model represents a debian release and holds an artifact to the
    upstream Release file at the same time.

    TODO This Content should include the Artifacts InRelease and Release.gpg
    """

    TYPE = 'release'

    codename = models.TextField()
    suite = models.TextField()
    distribution = models.TextField()
    components = models.TextField()
    architectures = models.TextField()
    relative_path = models.TextField()
    sha256 = models.TextField()

    class Meta:
        unique_together = (
            ('relative_path', 'sha256'),
        )


class PackageIndex(Content):
    """
    The "PackageIndex" content type.

    This model represents the Packages file for a specific
    component - architecture combination.
    It's artifacts should include all (non-)compressed versions
    of the upstream Packages file.
    """

    TYPE = 'package_index'

    release_pk = models.ForeignKey('Release', on_delete=models.CASCADE)
    component = models.TextField()
    architecture = models.TextField()
    relative_path = models.TextField()
    sha256 = models.TextField()

    class Meta:
        verbose_name_plural = "PackageIndices"
        unique_together = (
            ('relative_path', 'sha256'),
        )


class Package(Content):
    """
    The "package" content type.

    This model must contain all information that is needed to
    generate the corresponding paragraph in "Packages" files.
    """

    TYPE = 'package'

    # TODO: Do we have any specification for max_length?
    package_name = models.TextField()  # package name
    source = models.TextField(null=True)  # source package name
    version = models.TextField()
    architecture = models.TextField()  # all, i386, ...
    section = models.TextField(null=True)  # admin, comm, database, ...
    priority = models.TextField(null=True)  # required, standard, optional, extra, ...
    origin = models.TextField(null=True)
    tag = models.TextField(null=True)
    bugs = models.TextField(null=True)
    essential = models.BooleanField(null=True)
    build_essential = models.BooleanField(null=True)
    installed_size = models.IntegerField(null=True)
    maintainer = models.TextField()
    original_maintainer = models.TextField(null=True)
    description = models.TextField()
    description_md5 = models.TextField(null=True)
    homepage = models.TextField(null=True)
    built_using = models.TextField(null=True)
    auto_built_package = models.TextField(null=True)
    multi_arch = models.TextField(null=True, choices=[('no', 'no'), ('same', 'same'), ('foreign', 'foreign'), ('allowed', 'allowed')])

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
    # deprecated
    relative_path = models.TextField(null=False)

    @property
    def artifact(self):
        """
        Return the artifact id (there is only one for this content type).
        """
        return self.artifacts.get().pk

    @artifact.setter
    def artifact(self, artifact):
        """
        Set the artifact for this FileContent.
        """
        if self.pk:
            ca = ContentArtifact(artifact=artifact,
                                 content=self,
                                 relative_path=self.relative_path)
            ca.save()

    def filename(self, component=''):
        sourcename = self.source or self.package_name
        if sourcename.startswith('lib'):
            prefix = sourcename[0:4]
        else:
            prefix = sourcename[0]
        return os.path.join(
            'pool',
            component,
            prefix,
            sourcename,
            '{}_{}_{}.deb'.format(self.package_name, self.version, self.architecture)
        )

    class Meta:
        unique_together=(
            ('package_name', 'architecture', 'version'),
        )


class DebPublisher(Publisher):
    """
    A verbatim Publisher for DebContent.

    This publisher recreates all metadata.
    """

    TYPE = 'deb'

    verbatim = models.BooleanField(default=False)


class DebRemote(Remote):
    """
    A Remote for DebContent.
    """

    TYPE = 'deb'

    distributions = models.TextField(null=True)
    components = models.TextField(null=True)
    architectures = models.TextField(null=True)
