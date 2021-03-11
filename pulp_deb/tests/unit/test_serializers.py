import unittest
from django.test import TestCase

from pulp_deb.app.serializers import GenericContentSerializer
from pulp_deb.app.models import GenericContent

from pulpcore.plugin.models import Artifact


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
