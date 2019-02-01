from django.test import TestCase

from pulpcore.plugin.models import Artifact, ContentArtifact
from pulp_deb.app.models import Package


class TestPackage(TestCase):
    """Test Package content type."""

    PACKAGE_PARAGRAPH = 'Package: aegir\n' \
                        'Version: 0.1-edda0\n' \
                        'Architecture: sea\n' \
                        'Maintainer: Utgardloki\n' \
                        'Description: A sea jötunn associated with the ocean.\n' \
                        'MD5sum: aabb\n' \
                        'SHA1: ccdd\n' \
                        'SHA256: eeff\n' \
                        'Filename: pool/a/aegir/aegir_0.1-edda0_sea.deb\n'

    def setUp(self):
        """Setup database fixtures."""
        self.package1 = Package(
            package_name='aegir',
            version='0.1-edda0',
            architecture='sea',
            maintainer='Utgardloki',
            description='A sea jötunn associated with the ocean.',
        )
        self.package1.save()
        self.artifact1 = Artifact(size=42, md5='aabb', sha1='ccdd', sha256='eeff')
        self.artifact1.save()
        ContentArtifact(artifact=self.artifact1, content=self.package1).save()

    def test_str(self):
        """Test package str."""
        self.assertEqual(str(self.package1), '<Package: aegir_0.1-edda0_sea>')

    def test_filename(self):
        """Test that the pool filename of a package is correct."""
        self.assertEqual(self.package1.filename(),
                         'pool/a/aegir/aegir_0.1-edda0_sea.deb')

    def test_filename_with_component(self):
        """Test that the pool filename of a package with component is correct."""
        self.assertEqual(self.package1.filename('joetunn'),
                         'pool/joetunn/a/aegir/aegir_0.1-edda0_sea.deb')

    def test_to822(self):
        """Test if package transforms correctly into 822dict."""
        package_dict = self.package1.to822('joetunn')
        self.assertEqual(package_dict['package'], self.package1.package_name)
        self.assertEqual(package_dict['version'], self.package1.version)
        self.assertEqual(package_dict['architecture'], self.package1.architecture)
        self.assertEqual(package_dict['maintainer'], self.package1.maintainer)
        self.assertEqual(package_dict['description'], self.package1.description)
        self.assertEqual(package_dict['md5sum'], self.artifact1.md5)
        self.assertEqual(package_dict['sha1'], self.artifact1.sha1)
        self.assertEqual(package_dict['sha256'], self.artifact1.sha256)
        self.assertEqual(package_dict['filename'], self.package1.filename('joetunn'))

    def test_to822_dump(self):
        """Test dump to package index."""
        self.assertEqual(self.package1.to822().dump(), self.PACKAGE_PARAGRAPH)
