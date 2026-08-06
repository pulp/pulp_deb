import unittest

from debian import deb822
from django.test import TestCase

from pulpcore.plugin.models import Artifact

from pulp_deb.app.models import GenericContent, Package
from pulp_deb.app.serializers import GenericContentSerializer
from pulp_deb.app.serializers.content_serializers import Package822Serializer


# Fill data with sufficient information to create DebContent
# Provide sufficient parameters to create the DebContent object
# Depending on the base class of the serializer, provide either "_artifact" or "_artifacts"
@unittest.skip("FIXME: plugin writer action required")
class TestGenericContentSerializer(TestCase):
    """Test GenericContentSerializer."""

    def setUp(self):
        """Set up the GenericContentSerializer tests."""
        self.artifact = Artifact.objects.create(
            md5="ec0df26316b1deb465d2d18af7b600f5",
            sha1="cf6121b0425c2f2e3a2fcfe6f402d59730eb5661",
            sha256="c8ddb3dcf8da48278d57b0b94486832c66a8835316ccf7ca39e143cbfeb9184f",
            sha512="a94a65f19b864d184a2a5e07fa29766f08c6d49b6f624b3dd3a36a98267b9137d9c35040b3e105448a869c23c2aec04c9e064e3555295c1b8de6515eed4da27d",  # noqa
            size=1024,
        )

    def test_valid_data(self):
        """Test that the GenericContentSerializer accepts valid data."""
        data = {"_artifact": "/pulp/api/v3/artifacts/{}/".format(self.artifact.pk)}
        serializer = GenericContentSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_duplicate_data(self):
        """Test that the GenericContentSerializer does not accept data."""
        GenericContent.objects.create(artifact=self.artifact)
        data = {"_artifact": "/pulp/api/v3/artifacts/{}/".format(self.artifact.pk)}
        serializer = GenericContentSerializer(data=data)
        self.assertFalse(serializer.is_valid())


def test_package_822_serializer_handles_architecture_variant():
    """
    Test that Architecture-Variant is stored as a real Package field.
    """
    paragraph = deb822.Packages()
    paragraph["Package"] = "foo"
    paragraph["Version"] = "1.0"
    paragraph["Architecture"] = "amd64"
    paragraph["Architecture-Variant"] = "amd64v3"
    paragraph["Maintainer"] = "Example Maintainer <example@example.com>"
    paragraph["Description"] = "Example package"

    serializer = Package822Serializer.from822(paragraph)

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["architecture"] == "amd64"
    assert serializer.validated_data["architecture_variant"] == "amd64v3"
    assert "Architecture-Variant" not in serializer.validated_data.get("custom_fields", {})


def test_package_822_serializer_metadata_digest_changes_with_custom_metadata():
    old_paragraph = deb822.Packages()
    old_paragraph["Package"] = "foo"
    old_paragraph["Version"] = "1.0"
    old_paragraph["Architecture"] = "amd64"
    old_paragraph["Maintainer"] = "Example Maintainer <example@example.com>"
    old_paragraph["Description"] = "Example Package"
    old_paragraph["Phased-Update-Percentage"] = "20"

    new_paragraph = deb822.Packages(old_paragraph)
    new_paragraph["Phased-Update-Percentage"] = "50"

    old_serializer = Package822Serializer.from822(old_paragraph)
    new_serializer = Package822Serializer.from822(new_paragraph)
    assert old_serializer.is_valid(), old_serializer.errors
    assert new_serializer.is_valid(), new_serializer.errors

    from pulp_deb.app.package_metadata import calculate_package_metadata_sha256

    assert calculate_package_metadata_sha256(
        old_serializer.validated_data
    ) != calculate_package_metadata_sha256(new_serializer.validated_data)


def test_package_822_serializer_excludes_custom_metadata_on_sync():
    """Filtered custom package metadata fields are not stored during sync."""
    paragraph = deb822.Packages()
    paragraph["Package"] = "foo"
    paragraph["Version"] = "1.0"
    paragraph["Architecture"] = "amd64"
    paragraph["Maintainer"] = "Example Maintainer <example@example.com>"
    paragraph["Description"] = "Example pacakge"
    paragraph["Phased-Update-Percentage"] = "10"
    paragraph["X-Keep-Me"] = "kept"

    serializer = Package822Serializer.from822(
        paragraph, excluded_package_metadata_fields=["phased-update-percentage"]
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["custom_fields"] == {"X-Keep-Me": "kept"}


def test_package_822_serializer_excludes_custom_metadata_on_publish():
    """Filtered custom package metadata fields are not emitted during structured publish."""
    package = Package(
        package="foo",
        version="1.0",
        architecture="amd64",
        maintainer="Example Maintainer <example@example.com>",
        description="Example package",
        relative_path="pool/main/f/foo/foo_1.0_amd64.deb",
        sha256="0123456789abcdef",
        custom_fields={
            "Phased-Update-Percentage": "10",
            "X-Keep-Me": "kept",
        },
    )
    serializer = Package822Serializer(package, context={"request": None})

    paragraph = serializer.to822(excluded_package_metadata_fields=["PHASED-UPDATE-PERCENTAGE"])

    assert "Phased-Update-Percentage" not in paragraph
    assert paragraph["X-Keep-Me"] == "kept"
