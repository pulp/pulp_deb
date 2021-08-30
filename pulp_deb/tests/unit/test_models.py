from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from pulpcore.plugin.models import Artifact, ContentArtifact
from pulp_deb.app.models import Package
from pulp_deb.app.serializers import Package822Serializer


class TestPackage(TestCase):
    """Test Package content type."""

    PACKAGE_PARAGRAPH = (
        "Package: aegir\n"
        "Version: 0.1-edda0\n"
        "Architecture: sea\n"
        "Essential: yes\n"
        "Maintainer: Utgardloki\n"
        "Description: A sea jötunn associated with the ocean.\n"
        "SHA256: eeff\n"
        "Size: 42\n"
        "Filename: pool/a/aegir/aegir_0.1-edda0_sea.deb\n"
    )

    def setUp(self):
        """Setup database fixtures."""
        self.package1 = Package(
            package="aegir",
            version="0.1-edda0",
            architecture="sea",
            essential=True,
            maintainer="Utgardloki",
            description="A sea jötunn associated with the ocean.",
        )
        self.package1.save()
        self.artifact1 = Artifact(
            size=42,
            sha256="eeff",
            sha512="kkll",
            file=SimpleUploadedFile("test_filename", b"test content"),
        )
        self.artifact1.save()
        ContentArtifact(artifact=self.artifact1, content=self.package1).save()

    def test_str(self):
        """Test package str."""
        self.assertEqual(str(self.package1), "<Package: aegir_0.1-edda0_sea>")

    def test_filename(self):
        """Test that the pool filename of a package is correct."""
        self.assertEqual(self.package1.filename(), "pool/a/aegir/aegir_0.1-edda0_sea.deb")

    def test_filename_with_component(self):
        """Test that the pool filename of a package with component is correct."""
        self.assertEqual(
            self.package1.filename("joetunn"), "pool/joetunn/a/aegir/aegir_0.1-edda0_sea.deb"
        )

    def test_to822(self):
        """Test if package transforms correctly into 822dict."""
        package_dict = Package822Serializer(self.package1, context={"request": None}).to822(
            "joetunn"
        )
        self.assertEqual(package_dict["package"], self.package1.package)
        self.assertEqual(package_dict["version"], self.package1.version)
        self.assertEqual(package_dict["architecture"], self.package1.architecture)
        self.assertEqual(package_dict["maintainer"], self.package1.maintainer)
        self.assertEqual(package_dict["description"], self.package1.description)
        self.assertEqual(package_dict["sha256"], self.artifact1.sha256)
        self.assertEqual(package_dict["filename"], self.package1.filename("joetunn"))

    def test_to822_dump(self):
        """Test dump to package index."""
        self.assertEqual(
            Package822Serializer(self.package1, context={"request": None}).to822().dump(),
            self.PACKAGE_PARAGRAPH,
        )
