# coding=utf-8
"""Tests that perform actions over content unit."""
import unittest

from tempfile import NamedTemporaryFile

from pulp_smash import utils
from pulp_smash.pulp3.utils import delete_orphans

from pulp_deb.tests.functional.constants import (
    DEB_GENERIC_CONTENT_URL,
    DEB_PACKAGE_URL,
)
from pulp_deb.tests.functional.utils import (
    deb_generic_content_api,
    deb_package_api,
    gen_artifact,
    gen_deb_content_attrs,
    gen_deb_content_upload_attrs,
    gen_deb_package_attrs,
    gen_deb_package_upload_attrs,
    monitor_task,
    PulpTaskError,
    skip_if,
)
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class GenericContentUnitTestCase(unittest.TestCase):
    """CRUD content unit.

    This test targets the following issues:

    * `Pulp #2872 <https://pulp.plan.io/issues/2872>`_
    * `Pulp #3445 <https://pulp.plan.io/issues/3445>`_
    * `Pulp Smash #870 <https://github.com/pulp/pulp-smash/issues/870>`_
    """

    gen_content_attrs = staticmethod(gen_deb_content_attrs)
    gen_content_verify_attrs = staticmethod(gen_deb_content_attrs)
    content_api = deb_generic_content_api
    CONTENT_URL = DEB_GENERIC_CONTENT_URL

    @classmethod
    def setUpClass(cls):
        """Create class-wide variable."""
        delete_orphans()
        cls.content_unit = {}
        cls.artifact = gen_artifact(cls.CONTENT_URL)

    @classmethod
    def tearDownClass(cls):
        """Clean class-wide variable."""
        delete_orphans()

    def test_01_create_content_unit(self):
        """Create content unit."""
        attrs = self.gen_content_attrs(self.artifact)
        response = self.content_api.create(**attrs)
        created_resources = monitor_task(response.task)
        content_unit = self.content_api.read(created_resources[0])
        self.content_unit.update(content_unit.to_dict())
        for key, val in attrs.items():
            with self.subTest(key=key):
                self.assertEqual(self.content_unit[key], val)

    @skip_if(bool, "content_unit", False)
    def test_02_read_content_unit(self):
        """Read a content unit by its href."""
        content_unit = self.content_api.read(self.content_unit["pulp_href"]).to_dict()
        for key, val in self.content_unit.items():
            with self.subTest(key=key):
                self.assertEqual(content_unit[key], val)

    @skip_if(bool, "content_unit", False)
    def test_02_read_content_units(self):
        """Read a content unit by its relative_path."""
        page = self.content_api.list(relative_path=self.content_unit["relative_path"])
        self.assertEqual(len(page.results), 1)
        for key, val in self.content_unit.items():
            with self.subTest(key=key):
                self.assertEqual(page.results[0].to_dict()[key], val)

    @skip_if(bool, "content_unit", False)
    def test_03_partially_update(self):
        """Attempt to update a content unit using HTTP PATCH.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        attrs = self.gen_content_attrs(self.artifact)
        with self.assertRaises(AttributeError) as exc:
            self.content_api.partial_update(self.content_unit["pulp_href"], attrs)
        msg = "object has no attribute 'partial_update'"
        self.assertIn(msg, exc.exception.args[0])

    @skip_if(bool, "content_unit", False)
    def test_03_fully_update(self):
        """Attempt to update a content unit using HTTP PUT.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        attrs = self.gen_content_attrs(self.artifact)
        with self.assertRaises(AttributeError) as exc:
            self.content_api.update(self.content_unit["pulp_href"], attrs)
        msg = "object has no attribute 'update'"
        self.assertIn(msg, exc.exception.args[0])

    @skip_if(bool, "content_unit", False)
    def test_04_delete(self):
        """Attempt to delete a content unit using HTTP DELETE.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        with self.assertRaises(AttributeError) as exc:
            self.content_api.delete(self.content_unit["pulp_href"])
        msg = "object has no attribute 'delete'"
        self.assertIn(msg, exc.exception.args[0])


class PackageTestCase(GenericContentUnitTestCase):
    """CRUD content unit."""

    gen_content_attrs = staticmethod(gen_deb_package_attrs)
    gen_content_verify_attrs = staticmethod(gen_deb_package_attrs)
    content_api = deb_package_api
    CONTENT_URL = DEB_PACKAGE_URL


class GenericContentUnitUploadTestCase(unittest.TestCase):
    """CRUD content unit with upload feature.

    This test targets the following issue:

    `Pulp #5403 <https://pulp.plan.io/issues/5403>`_
    """

    gen_content_upload_attrs = staticmethod(gen_deb_content_upload_attrs)
    gen_content_upload_verify_attrs = staticmethod(gen_deb_content_upload_attrs)
    content_api = deb_generic_content_api
    CONTENT_URL = DEB_GENERIC_CONTENT_URL

    @classmethod
    def setUpClass(cls):
        """Create class-wide variable."""
        delete_orphans()
        cls.content_unit = {}
        cls.file = utils.http_get(cls.CONTENT_URL)
        cls.attrs = cls.gen_content_upload_attrs()

    @classmethod
    def tearDownClass(cls):
        """Clean class-wide variable."""
        delete_orphans()

    def test_01_create_content_unit(self):
        """Create content unit."""
        with NamedTemporaryFile() as temp_file:
            temp_file.write(self.file)
            temp_file.flush()
            response = self.content_api.create(**self.attrs, file=temp_file.name)
        created_resources = monitor_task(response.task)
        content_unit = self.content_api.read(created_resources[0])
        self.content_unit.update(content_unit.to_dict())
        for key, val in self.attrs.items():
            with self.subTest(key=key):
                self.assertEqual(self.content_unit[key], val)

    @skip_if(bool, "content_unit", False)
    def test_02_read_content_unit(self):
        """Read a content unit by its href."""
        content_unit = self.content_api.read(self.content_unit["pulp_href"]).to_dict()
        for key, val in self.content_unit.items():
            with self.subTest(key=key):
                self.assertEqual(content_unit[key], val)

    @skip_if(bool, "content_unit", False)
    def test_02_read_content_units(self):
        """Read a content unit by its relative_path."""
        page = self.content_api.list(relative_path=self.content_unit["relative_path"])
        self.assertEqual(len(page.results), 1)
        for key, val in self.content_unit.items():
            with self.subTest(key=key):
                self.assertEqual(page.results[0].to_dict()[key], val)

    @skip_if(bool, "content_unit", False)
    def test_03_fail_duplicate_content_unit(self):
        """Create content unit."""
        with NamedTemporaryFile() as temp_file:
            temp_file.write(self.file)
            temp_file.flush()
            response = self.content_api.create(**self.attrs, file=temp_file.name)
        with self.assertRaises(PulpTaskError) as exc:
            monitor_task(response.task)
        self.assertEqual(exc.exception.task.state, "failed")
        error = exc.exception.task.error
        for key in ("already", "relative", "path", "sha256"):
            self.assertIn(key, error["description"].lower(), error)

    @skip_if(bool, "content_unit", False)
    def test_03_duplicate_content_unit(self):
        """Create content unit."""
        attrs = self.attrs.copy()
        # Packages types only validate the filename, so we can prepend something to the path.
        attrs["relative_path"] = "moved-" + self.content_unit["relative_path"]
        with NamedTemporaryFile() as temp_file:
            temp_file.write(self.file)
            temp_file.flush()
            self.content_api.create(**attrs, file=temp_file.name)


class PackageUnitUploadTestCase(GenericContentUnitUploadTestCase):
    """CRUD content unit with upload feature."""

    gen_content_upload_attrs = staticmethod(gen_deb_package_upload_attrs)
    gen_content_upload_verify_attrs = staticmethod(gen_deb_package_upload_attrs)
    content_api = deb_package_api
    CONTENT_URL = DEB_PACKAGE_URL


class DuplicateGenericContentUnit(unittest.TestCase):
    """Attempt to create a duplicate content unit.

    This test targets the following issues:

    *  `Pulp #4125 <https://pulp.plan.io/issue/4125>`_
    """

    gen_content_attrs = staticmethod(gen_deb_content_attrs)
    gen_content_verify_attrs = staticmethod(gen_deb_content_attrs)
    content_api = deb_generic_content_api
    CONTENT_URL = DEB_GENERIC_CONTENT_URL

    @classmethod
    def tearDownClass(cls):
        """Clean created resources."""
        delete_orphans()

    def test_raise_error(self):
        """Create a duplicate content unit using same relative_path.

        Artifacts are unique by ``relative_path`` and ``file``.

        In order to raise an HTTP error, the same ``artifact`` and the same
        ``relative_path`` should be used.
        """
        delete_orphans()
        artifact = gen_artifact(self.CONTENT_URL)
        attrs = self.gen_content_attrs(artifact)

        # create first content unit.
        response = self.content_api.create(**attrs)
        created_resources = monitor_task(response.task)
        self.content_api.read(created_resources[0])

        # using the same attrs used to create the first content unit.
        response = self.content_api.create(**attrs)
        with self.assertRaises(PulpTaskError) as exc:
            monitor_task(response.task)
        self.assertEqual(exc.exception.task.state, "failed")
        error = exc.exception.task.error
        for key in ("already", "relative", "path", "sha256"):
            self.assertIn(key, error["description"].lower(), error)

    def test_non_error(self):
        """Create a duplicate content unit with different relative_path.

        Artifacts are unique by ``relative_path`` and ``file``.

        In order to avoid an HTTP error, use the same ``artifact`` and
        different ``relative_path``.
        """
        delete_orphans()
        artifact = gen_artifact(self.CONTENT_URL)
        attrs = self.gen_content_attrs(artifact)

        # create first content unit.
        response = self.content_api.create(**attrs)
        created_resources = monitor_task(response.task)
        content_unit = self.content_api.read(created_resources[0])

        # Packages types only validate the filename, so we can prepend something to the path.
        attrs["relative_path"] = "moved-" + content_unit.relative_path
        # create second content unit.
        response = self.content_api.create(**attrs)
        created_resources = monitor_task(response.task)
        content_unit = self.content_api.read(created_resources[0])


class DuplicatePackageUnit(DuplicateGenericContentUnit):
    """Attempt to create a duplicate content unit."""

    gen_content_attrs = staticmethod(gen_deb_package_attrs)
    gen_content_verify_attrs = staticmethod(gen_deb_package_attrs)
    content_api = deb_package_api
    CONTENT_URL = DEB_PACKAGE_URL
