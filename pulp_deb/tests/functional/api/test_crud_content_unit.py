# coding=utf-8
"""Tests that perform actions over content unit."""
import unittest

from requests.exceptions import HTTPError

from pulp_smash import api, config, utils
from pulp_smash.pulp3.constants import ARTIFACTS_PATH
from pulp_smash.pulp3.utils import delete_orphans

from pulp_deb.tests.functional.constants import DEB_GENERIC_CONTENT_PATH, DEB_GENERIC_CONTENT_URL
from pulp_deb.tests.functional.utils import gen_deb_generic_content_attrs, skip_if
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class ContentUnitTestCase(unittest.TestCase):
    """CRUD content unit.

    This test targets the following issues:

    * `Pulp #2872 <https://pulp.plan.io/issues/2872>`_
    * `Pulp #3445 <https://pulp.plan.io/issues/3445>`_
    * `Pulp Smash #870 <https://github.com/PulpQE/pulp-smash/issues/870>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variable."""
        cls.cfg = config.get_config()
        delete_orphans(cls.cfg)
        cls.content_unit = {}
        cls.client = api.Client(cls.cfg, api.json_handler)
        files = {"file": utils.http_get(DEB_GENERIC_CONTENT_URL)}
        cls.artifact = cls.client.post(ARTIFACTS_PATH, files=files)

    @classmethod
    def tearDownClass(cls):
        """Clean class-wide variable."""
        delete_orphans(cls.cfg)

    def test_01_create_content_unit(self):
        """Create content unit."""
        attrs = gen_deb_generic_content_attrs(self.artifact)
        self.content_unit.update(self.client.post(DEB_GENERIC_CONTENT_PATH, attrs))
        for key, val in attrs.items():
            with self.subTest(key=key):
                self.assertEqual(self.content_unit[key], val)

    @skip_if(bool, "content_unit", False)
    def test_02_read_content_unit(self):
        """Read a content unit by its href."""
        content_unit = self.client.get(self.content_unit["_href"])
        for key, val in self.content_unit.items():
            with self.subTest(key=key):
                self.assertEqual(content_unit[key], val)

    @skip_if(bool, "content_unit", False)
    def test_02_read_content_units(self):
        """Read a content unit by its relative_path."""
        page = self.client.get(
            DEB_GENERIC_CONTENT_PATH, params={"relative_path": self.content_unit["relative_path"]}
        )
        self.assertEqual(len(page["results"]), 1)
        for key, val in self.content_unit.items():
            with self.subTest(key=key):
                self.assertEqual(page["results"][0][key], val)

    @skip_if(bool, "content_unit", False)
    def test_03_partially_update(self):
        """Attempt to update a content unit using HTTP PATCH.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        attrs = gen_deb_generic_content_attrs(self.artifact)
        with self.assertRaises(HTTPError) as exc:
            self.client.patch(self.content_unit["_href"], attrs)
        self.assertEqual(exc.exception.response.status_code, 405)

    @skip_if(bool, "content_unit", False)
    def test_03_fully_update(self):
        """Attempt to update a content unit using HTTP PUT.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        attrs = gen_deb_generic_content_attrs(self.artifact)
        with self.assertRaises(HTTPError) as exc:
            self.client.put(self.content_unit["_href"], attrs)
        self.assertEqual(exc.exception.response.status_code, 405)

    @skip_if(bool, "content_unit", False)
    def test_04_delete(self):
        """Attempt to delete a content unit using HTTP DELETE.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        with self.assertRaises(HTTPError) as exc:
            self.client.delete(self.content_unit["_href"])
        self.assertEqual(exc.exception.response.status_code, 405)


class DuplicateContentUnit(unittest.TestCase):
    """Attempt to create a duplicate content unit.

    This test targets the following issues:

    *  `Pulp #4125 <https://pulp.plan.io/issue/4125>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)

    @classmethod
    def tearDownClass(cls):
        """Clean created resources."""
        delete_orphans(cls.cfg)

    def test_raise_error(self):
        """Create a duplicate content unit using same relative_path.

        Artifacts are unique by ``relative_path`` and ``file``.

        In order to raise an HTTP error, the same ``artifact`` and the same
        ``relative_path`` should be used.
        """
        delete_orphans(self.cfg)
        files = {"file": utils.http_get(DEB_GENERIC_CONTENT_URL)}
        artifact = self.client.post(ARTIFACTS_PATH, files=files)
        attrs = gen_deb_generic_content_attrs(artifact)

        # create first content unit.
        self.client.post(DEB_GENERIC_CONTENT_PATH, attrs)

        # using the same attrs used to create the first content unit.
        response = api.Client(self.cfg, api.echo_handler).post(DEB_GENERIC_CONTENT_PATH, attrs)
        with self.assertRaises(HTTPError):
            response.raise_for_status()
        for key in ("already", "content", "relative", "path", "sha256"):
            self.assertIn(key, response.json()["non_field_errors"][0].lower(), response.json())

    def test_non_error(self):
        """Create a duplicate content unit with different relative_path.

        Artifacts are unique by ``relative_path`` and ``file``.

        In order to avoid an HTTP error, use the same ``artifact`` and
        different ``relative_path``.
        """
        delete_orphans(self.cfg)
        files = {"file": utils.http_get(DEB_GENERIC_CONTENT_URL)}
        artifact = self.client.post(ARTIFACTS_PATH, files=files)
        attrs = gen_deb_generic_content_attrs(artifact)

        # create first content unit.
        self.client.post(DEB_GENERIC_CONTENT_PATH, attrs)

        attrs["relative_path"] = utils.uuid4()
        # create second content unit.
        self.client.post(DEB_GENERIC_CONTENT_PATH, attrs)
