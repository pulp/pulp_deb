from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from pulpcore.plugin.models import Artifact, ContentArtifact
from pulp_deb.app.constants import LAYOUT_TYPES
from pulp_deb.app.models import Package, AptRepository, Release
from pulp_deb.app.models.repository import handle_duplicate_releases
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
        "MD5sum: aabb\n"
        "SHA1: ccdd\n"
        "SHA256: eeff11\n"
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
            md5="aabb",
            sha1="ccdd",
            sha224="ddcc",
            sha256="eeff11",
            sha384="ffee",
            sha512="kkll",
            file=SimpleUploadedFile("test_filename", b"test content"),
        )
        self.artifact1.save()
        ContentArtifact(artifact=self.artifact1, content=self.package1).save()

    def test_package_fields(self):
        """Test package fields that typically identify a package."""
        self.assertEqual(str(self.package1.package), "aegir")
        self.assertEqual(str(self.package1.version), "0.1-edda0")

    def test_filename(self):
        """Test that the pool filename of a package is correct."""
        self.assertEqual(self.package1.filename(), "pool/a/aegir/aegir_0.1-edda0_sea.deb")

    def test_filename_by_digest(self):
        """Test that the pool filename of a package is correct."""
        for layout in [LAYOUT_TYPES.NESTED_BY_DIGEST, LAYOUT_TYPES.NESTED_BY_BOTH]:
            self.assertEqual(
                self.package1.filename(layout=layout), "pool/ee/ff11/aegir_0.1-edda0_sea.deb"
            )

    def test_filename_with_component(self):
        """Test that the pool filename of a package with component is correct."""
        self.assertEqual(
            self.package1.filename("joetunn"), "pool/joetunn/a/aegir/aegir_0.1-edda0_sea.deb"
        )

    def test_filename_with_component_and_by_digest(self):
        """Test that the pool filename of a package with component is correct."""
        for layout in [LAYOUT_TYPES.NESTED_BY_DIGEST, LAYOUT_TYPES.NESTED_BY_BOTH]:
            self.assertEqual(
                self.package1.filename("joetunn", layout=layout),
                "pool/joetunn/ee/ff11/aegir_0.1-edda0_sea.deb",
            )

    def test_to822(self):
        """Test if package transforms correctly into 822dict."""
        artifact_dict = {self.package1.sha256: self.artifact1}
        package_dict = Package822Serializer(self.package1, context={"request": None}).to822(
            "joetunn", artifact_dict=artifact_dict
        )
        self.assertEqual(package_dict["package"], self.package1.package)
        self.assertEqual(package_dict["version"], self.package1.version)
        self.assertEqual(package_dict["architecture"], self.package1.architecture)
        self.assertEqual(package_dict["maintainer"], self.package1.maintainer)
        self.assertEqual(package_dict["description"], self.package1.description)
        self.assertEqual(package_dict["md5sum"], self.artifact1.md5)
        self.assertEqual(package_dict["sha1"], self.artifact1.sha1)
        self.assertEqual(package_dict["sha256"], self.artifact1.sha256)
        self.assertEqual(package_dict["filename"], self.package1.filename("joetunn"))

    def test_to822_dump(self):
        """Test dump to package index."""
        artifact_dict = {self.package1.sha256: self.artifact1}
        self.assertEqual(
            Package822Serializer(self.package1, context={"request": None})
            .to822(artifact_dict=artifact_dict)
            .dump(),
            self.PACKAGE_PARAGRAPH,
        )


class TestRepositoryFunctions(TestCase):
    """Test Repository functions."""

    def test_handle_duplicate_releases(self):
        repo = AptRepository.objects.create(name="dummy")
        self.addCleanup(repo.delete)
        rel1 = Release.objects.create(
            distribution="ginnungagap",
            codename="ginnungagap",
            suite="ginnungagap",
            version="ginnungagap",
            origin="norse",
            label="ginnungagap",
            description="ginnungagap",
        )
        rel2 = Release.objects.create(
            distribution="ginnungagap",
        )

        with repo.new_version() as base_version:
            base_version.add_content(Release.objects.filter(pk=rel1.pk))

        with repo.new_version(base_version=repo.latest_version()) as version:
            version.add_content(Release.objects.filter(pk=rel2.pk))
            self.assertEqual(2, version.content.count())

            handle_duplicate_releases(version)
            self.assertEqual(1, version.content.count())
            self.assertEqual(rel1.pk, version.content[0].pk)
