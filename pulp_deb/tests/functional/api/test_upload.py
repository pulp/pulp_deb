# coding=utf-8
"""Tests that verify upload of content to Pulp."""
import hashlib
import unittest

from pulp_smash import api, config, utils
from pulp_smash.pulp3.constants import ARTIFACTS_PATH, REPO_PATH
from pulp_smash.pulp3.utils import delete_orphans, gen_repo, sync

from pulp_deb.tests.functional.constants import (
    DEB_PACKAGE_PATH,
    DEB_PACKAGE_URL,
    DEB_REMOTE_PATH,
    DEB_SINGLE_REQUEST_UPLOAD_PATH,
)
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
        delete_orphans(cls.cfg)
        cls.client = api.Client(cls.cfg, api.page_handler)
        cls.file = {"file": utils.http_get(DEB_PACKAGE_URL)}

    def single_request_upload(self, repo):
        """Create single request upload."""
        return self.client.post(
            DEB_SINGLE_REQUEST_UPLOAD_PATH,
            files=self.file,
            data={"repository": repo["_href"]} if repo else {},
        )

    def test_single_request_upload(self):
        """Test single request upload."""
        repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["_href"])
        self.single_request_upload(repo)
        repo = self.client.get(repo["_href"])

        # Assertion about repo version.
        self.assertIsNotNone(repo["_latest_version_href"], repo)

        # Assertions about artifcats.
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
        self.addCleanup(self.client.delete, repo["_href"])
        result = self.single_request_upload(None)
        # Check for a content_unit in created_resources
        task = self.client.get(result["task"])
        self.assertEqual(len(task["created_resources"]), 1)
        self.assertRegex(task["created_resources"][0], r"^/pulp/api/v3/content/deb/packages/")
        result = self.single_request_upload(repo)
        # check for a repository_version in created_resources
        task = self.client.get(result["task"])
        self.assertEqual(len(task["created_resources"]), 1)
        self.assertRegex(task["created_resources"][0], r"^/pulp/api/v3/repositories/.*/versions/")

    def test_sync_interference(self):
        """Test that uploading a file does not break a consecutive sync contining that file."""
        upload_repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, upload_repo["_href"])
        sync_repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, sync_repo["_href"])
        remote = self.client.post(DEB_REMOTE_PATH, gen_deb_remote())
        self.addCleanup(self.client.delete, remote["_href"])

        # upload a file into one repository
        self.single_request_upload(upload_repo)
        # sync the other repository
        sync(self.cfg, remote, sync_repo)
