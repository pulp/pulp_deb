import os

from logging import getLogger

from debian import deb822

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
    components = models.TextField(blank=True)
    architectures = models.TextField(blank=True)
    relative_path = models.TextField()
    sha256 = models.TextField()

    class Meta:
        unique_together = (
            (
                'codename',
                'suite',
                'distribution',
                'components',
                'architectures',
                'relative_path',
                'sha256',
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

    TRANSLATION_DICT = {
        'package_name': 'package',  # Workaround (this field should be called 'package')
        'source': 'source',
        'version': 'version',
        'architecture': 'architecture',
        'section': 'section',
        'priority': 'priority',
        'origin': 'origin',
        'tag': 'tag',
        'bugs': 'bugs',
        'essential': 'essential',
        'build_essential': 'build_essential',
        'installed_size': 'installed_size',
        'maintainer': 'maintainer',
        'original_maintainer': 'original_maintainer',
        'description': 'description',
        'description_md5': 'description_md5',
        'homepage': 'homepage',
        'built_using': 'built_using',
        'auto_built_package': 'auto_built_package',
        'multi_arch': 'multi_arch',
        'breaks': 'breaks',
        'conflicts': 'conflicts',
        'depends': 'depends',
        'recommends': 'recommends',
        'suggests': 'suggests',
        'enhances': 'enhances',
        'pre_depends': 'pre_depends',
        'provides': 'provides',
        'replaces': 'replaces',
    }

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
    multi_arch = models.TextField(
        null=True,
        choices=[('no', 'no'), ('same', 'same'), ('foreign', 'foreign'), ('allowed', 'allowed')],
    )

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
    def name(self):
        """Print a nice name for Packages."""
        return '{}_{}_{}'.format(self.package_name, self.version, self.architecture)

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
        """Assemble filename in pool directory."""
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

    def to822(self, component=''):
        """Create deb822.Package object from model."""
        ret = deb822.Packages()
        ret['Package'] = self.package_name
        if self.source:
            ret['Source'] = self.source
        ret['Version'] = self.version
        ret['Architecture'] = self.architecture
        if self.section:
            ret['Section'] = self.section
        if self.priority:
            ret['Priority'] = self.priority
        if self.origin:
            ret['Origin'] = self.origin
        if self.tag:
            ret['Tag'] = self.tag
        if self.bugs:
            ret['Bugs'] = self.bugs
        if self.essential:
            ret['Essential'] = self.essential
        if self.build_essential:
            ret['Build-Essential'] = self.build_essential
        if self.installed_size:
            ret['Installed-Size'] = self.installed_size
        ret['Maintainer'] = self.maintainer
        if self.original_maintainer:
            ret['Original-Maintainer'] = self.original_maintainer
        ret['Description'] = self.description
        if self.description_md5:
            ret['Description-MD5'] = self.description_md5
        if self.homepage:
            ret['Homepage'] = self.homepage
        if self.built_using:
            ret['Built-Using'] = self.built_using
        if self.auto_built_package:
            ret['Auto-Built-Package'] = self.auto_built_package
        if self.multi_arch:
            ret['Multi-Arch'] = self.multi_arch

        if self.breaks:
            ret['Breaks'] = self.breaks
        if self.conflicts:
            ret['Conflicts'] = self.conflicts
        if self.depends:
            ret['Depends'] = self.depends
        if self.recommends:
            ret['Recommends'] = self.recommends
        if self.suggests:
            ret['Suggests'] = self.suggests
        if self.enhances:
            ret['Enhances'] = self.enhances
        if self.pre_depends:
            ret['Pre-Depends'] = self.pre_depends
        if self.provides:
            ret['Provides'] = self.provides
        if self.replaces:
            ret['Replaces'] = self.replaces

        artifact = self.artifacts.get()
        ret['MD5sum'] = artifact.md5
        ret['SHA1'] = artifact.sha1
        ret['SHA256'] = artifact.sha256
        ret['Filename'] = self.filename(component)

        return ret

    class Meta:
        unique_together = (
            ('package_name', 'architecture', 'version'),
        )


class DebVerbatimPublisher(Publisher):
    """
    A verbatim Publisher for DebContent.

    This publisher publishes the obtained metadata unchanged.
    """

    TYPE = 'deb'


class DebPublisher(Publisher):
    """
    A Publisher for DebContent.

    This publisher recreates all metadata.
    """

    TYPE = 'deb'

    simple = models.BooleanField(default=False)
    structured = models.BooleanField(default=False)


class DebRemote(Remote):
    """
    A Remote for DebContent.
    """

    TYPE = 'deb'

    distributions = models.TextField(null=True)
    components = models.TextField(null=True)
    architectures = models.TextField(null=True)
