# coding=utf-8
"""Tests that CRUD deb content units."""
import unittest
from random import choice

from requests.exceptions import HTTPError

from pulp_smash import api, config, utils
from pulp_smash.pulp3.constants import ARTIFACTS_PATH, REPO_PATH
from pulp_smash.pulp3.utils import delete_orphans, gen_repo, get_content, sync

from pulp_deb.tests.functional.constants import DEB_URL, DEB_CONTENT_PATH, DEB_REMOTE_PATH
from pulp_deb.tests.functional.utils import gen_deb_content_attrs, gen_deb_remote, skip_if
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


# Read the instructions provided below for the steps needed to enable this test (see: FIXME's).
@unittest.skip("FIXME: plugin writer action required")
class ContentUnitTestCase(unittest.TestCase):
    """CRUD content unit.

    This test targets the following issues:

    * `Pulp #2872 <https://pulp.plan.io/issues/2872>`_
    * `Pulp Smash #870 <https://github.com/PulpQE/pulp-smash/issues/870>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variable."""
        cls.cfg = config.get_config()
        delete_orphans(cls.cfg)
        cls.content_unit = {}
        cls.client = api.Client(cls.cfg, api.json_handler)
        files = {"file": utils.http_get(DEB_URL)}
        cls.artifact = cls.client.post(ARTIFACTS_PATH, files=files)

    @classmethod
    def tearDownClass(cls):
        """Clean class-wide variable."""
        delete_orphans(cls.cfg)

    def test_01_create_content_unit(self):
        """Create content unit."""
        attrs = gen_deb_content_attrs(self.artifact)
        self.content_unit.update(self.client.post(DEB_CONTENT_PATH, attrs))
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
        # FIXME: 'relative_path' is an attribute specific to the File plugin. It is only an
        # example. You should replace this with some other field specific to your content type.
        page = self.client.get(
            DEB_CONTENT_PATH, params={"relative_path": self.content_unit["relative_path"]}
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
        attrs = gen_deb_content_attrs(self.artifact)
        with self.assertRaises(HTTPError):
            self.client.patch(self.content_unit["_href"], attrs)

    @skip_if(bool, "content_unit", False)
    def test_03_fully_update(self):
        """Attempt to update a content unit using HTTP PUT.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        attrs = gen_deb_content_attrs(self.artifact)
        with self.assertRaises(HTTPError):
            self.client.put(self.content_unit["_href"], attrs)


# Implement sync support before enabling this test.
@unittest.skip("FIXME: plugin writer action required")
class DeleteContentUnitRepoVersionTestCase(unittest.TestCase):
    """Test whether content unit used by a repo version can be deleted.

    This test targets the following issues:

    * `Pulp #3418 <https://pulp.plan.io/issues/3418>`_
    * `Pulp Smash #900 <https://github.com/PulpQE/pulp-smash/issues/900>`_
    """

    def test_all(self):
        """Test whether content unit used by a repo version can be deleted.

        Do the following:

        1. Sync content to a repository.
        2. Attempt to delete a content unit present in a repository version.
           Assert that a HTTP exception was raised.
        3. Assert that number of content units present on the repository
           does not change after the attempt to delete one content unit.
        """
        cfg = config.get_config()
        client = api.Client(cfg, api.json_handler)

        body = gen_deb_remote()
        remote = client.post(DEB_REMOTE_PATH, body)
        self.addCleanup(client.delete, remote["_href"])

        repo = client.post(REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo["_href"])

        sync(cfg, remote, repo)

        repo = client.get(repo["_href"])
        content = get_content(repo)
        with self.assertRaises(HTTPError):
            client.delete(choice(content)["_href"])
        self.assertEqual(len(content), len(get_content(repo)))
