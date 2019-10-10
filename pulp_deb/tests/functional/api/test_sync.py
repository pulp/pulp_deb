# coding=utf-8
"""Tests that sync deb plugin repositories."""
import unittest

from pulp_smash import api, cli, config, exceptions
from pulp_smash.pulp3.constants import MEDIA_PATH, REPO_PATH
from pulp_smash.pulp3.utils import gen_repo, get_content_summary, get_added_content_summary, sync

from pulp_deb.tests.functional.constants import (
    DEB_FIXTURE_SUMMARY,
    DEB_FULL_FIXTURE_SUMMARY,
    DEB_REMOTE_PATH,
)
from pulp_deb.tests.functional.utils import gen_deb_remote
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class BasicSyncTestCase(unittest.TestCase):
    """Sync repositories with the deb plugin."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)

    def test_sync_small(self):
        """Test synching with deb content only."""
        self.do_sync(sync_udebs=False, fixture_summary=DEB_FIXTURE_SUMMARY)

    def test_sync_full(self):
        """Test synching with udeb."""
        self.do_sync(sync_udebs=True, fixture_summary=DEB_FULL_FIXTURE_SUMMARY)

    def do_sync(self, sync_udebs, fixture_summary):
        """Sync repositories with the deb plugin.

        In order to sync a repository a remote has to be associated within
        this repository. When a repository is created this version field is set
        as None. After a sync the repository version is updated.

        Do the following:

        1. Create a repository, and a remote.
        2. Assert that repository version is None.
        3. Sync the remote.
        4. Assert that repository version is not None.
        5. Sync the remote one more time.
        6. Assert that repository version is different from the previous one.
        """
        repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["pulp_href"])

        body = gen_deb_remote(sync_udebs=sync_udebs)
        remote = self.client.post(DEB_REMOTE_PATH, body)
        self.addCleanup(self.client.delete, remote["pulp_href"])

        # Sync the repository.
        self.assertIsNone(repo["latest_version_href"])
        sync(self.cfg, remote, repo)
        repo = self.client.get(repo["pulp_href"])

        self.assertIsNotNone(repo["latest_version_href"])
        self.assertDictEqual(get_content_summary(repo), fixture_summary)
        self.assertDictEqual(get_added_content_summary(repo), fixture_summary)

        # Sync the repository again.
        latest_version_href = repo["latest_version_href"]
        sync(self.cfg, remote, repo)
        repo = self.client.get(repo["pulp_href"])

        self.assertNotEqual(latest_version_href, repo["latest_version_href"])
        self.assertDictEqual(get_content_summary(repo), fixture_summary)
        self.assertDictEqual(get_added_content_summary(repo), {})

    def test_file_decriptors(self):
        """Test whether file descriptors are closed properly.

        This test targets the following issue:
        `Pulp #4073 <https://pulp.plan.io/issues/4073>`_

        Do the following:
        1. Check if 'lsof' is installed. If it is not, skip this test.
        2. Create and sync a repo.
        3. Run the 'lsof' command to verify that files in the
           path ``/var/lib/pulp/`` are closed after the sync.
        4. Assert that issued command returns `0` opened files.
        """
        cli_client = cli.Client(self.cfg, cli.echo_handler)

        # check if 'lsof' is available
        if cli_client.run(("which", "lsof")).returncode != 0:
            raise unittest.SkipTest("lsof package is not present")

        repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["pulp_href"])

        remote = self.client.post(DEB_REMOTE_PATH, gen_deb_remote())
        self.addCleanup(self.client.delete, remote["pulp_href"])

        sync(self.cfg, remote, repo)

        cmd = "lsof -t +D {}".format(MEDIA_PATH).split()
        response = cli_client.run(cmd).stdout
        self.assertEqual(len(response), 0, response)


class SyncInvalidURLTestCase(unittest.TestCase):
    """Sync a repository with an invalid url on the Remote."""

    def test_all(self):
        """
        Sync a repository using a Remote url that does not exist.

        Test that we get a task failure.

        """
        cfg = config.get_config()
        client = api.Client(cfg, api.json_handler)

        repo = client.post(REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo["pulp_href"])

        body = gen_deb_remote(url="http://i-am-an-invalid-url.com/invalid/")
        remote = client.post(DEB_REMOTE_PATH, body)
        self.addCleanup(client.delete, remote["pulp_href"])

        with self.assertRaises(exceptions.TaskReportError):
            sync(cfg, remote, repo)
