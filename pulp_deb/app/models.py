import os

from logging import getLogger

from debian import deb822

from django.db import models

from pulpcore.plugin.models import Content, Remote, Publisher

logger = getLogger(__name__)


class GenericContent(Content):
    """
    The "generic" content.

    This model is meant to map to all files in the upstream repository, that
    are not handled by a more specific model.
    Those units are used for the verbatim publish method.
    """

    TYPE = 'generic'

    relative_path = models.CharField(max_length=255, null=False)
    sha256 = models.CharField(max_length=255, null=False)

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

    codename = models.CharField(max_length=255)
    suite = models.CharField(max_length=255)
    distribution = models.CharField(max_length=255)
    components = models.CharField(max_length=255, blank=True)
    architectures = models.CharField(max_length=255, blank=True)
    relative_path = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=255)

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
    component = models.CharField(max_length=255)
    architecture = models.CharField(max_length=255)
    relative_path = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "PackageIndices"
        unique_together = (
            ('relative_path', 'sha256'),
        )

    @property
    def main_artifact(self):
        """
        Retrieve the uncompressed PackageIndex artifact.
        """
        return self._artifacts.get(sha256=self.sha256)


class Package(Content):
    """
    The "package" content type.

    This model must contain all information that is needed to
    generate the corresponding paragraph in "Packages" files.
    """

    TYPE = 'package'

    TRANSLATION_DICT = {
        'package_name': 'Package',  # Workaround (this field should be called 'package')
        'source': 'Source',
        'version': 'Version',
        'architecture': 'Architecture',
        'section': 'Section',
        'priority': 'Priority',
        'origin': 'Origin',
        'tag': 'Tag',
        'bugs': 'Bugs',
        'essential': 'Essential',
        'build_essential': 'Build_essential',
        'installed_size': 'Installed_size',
        'maintainer': 'Maintainer',
        'original_maintainer': 'Original_Maintainer',
        'description': 'Description',
        'description_md5': 'Description_MD5',
        'homepage': 'Homepage',
        'built_using': 'Built_Using',
        'auto_built_package': 'Auto_Built_Package',
        'multi_arch': 'Multi_Arch',
        'breaks': 'Breaks',
        'conflicts': 'Conflicts',
        'depends': 'Depends',
        'recommends': 'Recommends',
        'suggests': 'Suggests',
        'enhances': 'Enhances',
        'pre_depends': 'Pre_Depends',
        'provides': 'Provides',
        'replaces': 'Replaces',
    }

    package_name = models.CharField(max_length=255)  # package name
    source = models.CharField(max_length=255, null=True)  # source package name
    version = models.CharField(max_length=255)
    architecture = models.CharField(max_length=255)  # all, i386, ...
    section = models.CharField(max_length=255, null=True)  # admin, comm, database, ...
    priority = models.CharField(max_length=255, null=True)  # required, standard, optional, extra
    origin = models.CharField(max_length=255, null=True)
    tag = models.TextField(null=True)
    bugs = models.TextField(null=True)
    essential = models.BooleanField(null=True)
    build_essential = models.BooleanField(null=True)
    installed_size = models.IntegerField(null=True)
    maintainer = models.CharField(max_length=255)
    original_maintainer = models.CharField(max_length=255, null=True)
    description = models.TextField()
    description_md5 = models.CharField(max_length=255, null=True)
    homepage = models.CharField(max_length=255, null=True)
    built_using = models.CharField(max_length=255, null=True)
    auto_built_package = models.CharField(max_length=255, null=True)
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
    relative_path = models.CharField(max_length=255, null=False)

    @property
    def name(self):
        """Print a nice name for Packages."""
        return '{}_{}_{}'.format(self.package_name, self.version, self.architecture)

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

        for k, v in self.TRANSLATION_DICT.items():
            value = getattr(self, k, None)
            if value is not None:
                ret[v] = value

        artifact = self._artifacts.get()
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

    TYPE = 'verbatim-publisher'


class DebPublisher(Publisher):
    """
    A Publisher for DebContent.

    This publisher recreates all metadata.
    """

    TYPE = 'apt-publisher'

    simple = models.BooleanField(default=False)
    structured = models.BooleanField(default=False)


class DebRemote(Remote):
    """
    A Remote for DebContent.
    """

    TYPE = 'apt-remote'

    distributions = models.CharField(max_length=255, null=True)
    components = models.CharField(max_length=255, null=True)
    architectures = models.CharField(max_length=255, null=True)
