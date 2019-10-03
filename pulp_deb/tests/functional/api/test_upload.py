# coding=utf-8
"""Tests that verify upload of content to Pulp."""
import hashlib
import unittest

from pulp_smash import api, config, utils
from pulp_smash.pulp3.constants import ARTIFACTS_PATH, REPO_PATH
from pulp_smash.pulp3.utils import delete_orphans, gen_repo, sync

from pulp_deb.tests.functional.constants import DEB_PACKAGE_PATH, DEB_PACKAGE_URL, DEB_REMOTE_PATH
from pulp_deb.tests.functional.utils import gen_deb_remote
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class SingleRequestUploadTestCase(unittest.TestCase):
    """Test whether one can upload a RPM using a single request.

    This test targets the following issues:

    `Pulp #4087 <https://pulp.plan.io/issues/4087>`_
    `Pulp #4285 <https://pulp.plan.io/issues/4285>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.page_handler)
        cls.file = {"file": utils.http_get(DEB_PACKAGE_URL)}

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests ran."""
        delete_orphans(cls.cfg)

    def setUp(self):
        """Perform per test preparation."""
        delete_orphans(self.cfg)

    def single_request_upload(self, relative_path=None, repo=None):
        """Create single request upload."""
        data = {}
        if relative_path:
            data["relative_path"] = relative_path
        if repo:
            data["repository"] = repo["pulp_href"]
        return self.client.post(DEB_PACKAGE_PATH, files=self.file, data=data)

    def test_single_request_upload(self):
        """Test single request upload."""
        repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["pulp_href"])
        self.single_request_upload(repo=repo)
        repo = self.client.get(repo["pulp_href"])

        # Assertion about repo version.
        self.assertIsNotNone(repo["_latest_version_href"], repo)

        # Assertions about artifacts.
        artifact = self.client.get(ARTIFACTS_PATH)
        self.assertEqual(len(artifact), 1, artifact)
        self.assertEqual(
            artifact[0]["sha256"], hashlib.sha256(self.file["file"]).hexdigest(), artifact
        )

        # Assertion about content unit.
        content = self.client.get(DEB_PACKAGE_PATH)
        self.assertEqual(len(content), 1, content)

    def test_duplicate_unit(self):
        """Test single request upload for unit already present in Pulp."""
        repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["pulp_href"])
        result = self.single_request_upload(relative_path="another_name.deb")
        # Check for a content_unit in created_resources
        task = self.client.get(result["task"])
        self.assertEqual(len(task["created_resources"]), 1)
        self.assertRegex(task["created_resources"][0], r"^/pulp/api/v3/content/deb/packages/")
        result = self.single_request_upload(repo=repo)
        # check for a repository_version in created_resources
        task = self.client.get(result["task"])
        self.assertEqual(len(task["created_resources"]), 2)
        self.assertRegex(
            " ".join(task["created_resources"]), r"/pulp/api/v3/repositories/.*/versions/"
        )

    def test_sync_interference(self):
        """Test that uploading a file does not break a consecutive sync containing that file."""
        upload_repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, upload_repo["pulp_href"])
        sync_repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, sync_repo["pulp_href"])
        remote = self.client.post(DEB_REMOTE_PATH, gen_deb_remote())
        self.addCleanup(self.client.delete, remote["pulp_href"])

        # upload a file into one repository
        self.single_request_upload(repo=upload_repo)
        # sync the other repository
        sync(self.cfg, remote, sync_repo)
