# coding=utf-8
"""Tests that sync deb plugin repositories."""
import unittest

from pulp_smash import cli, config
from pulp_smash.pulp3.constants import MEDIA_PATH
from pulp_smash.pulp3.utils import gen_repo, get_added_content_summary, get_content_summary

from pulp_deb.tests.functional.constants import (
    DEB_FIXTURE_SUMMARY,
    DEB_FULL_FIXTURE_SUMMARY,
    DEB_INVALID_FIXTURE_URL,
)
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401
from pulp_deb.tests.functional.utils import (
    gen_deb_remote,
    monitor_task,
    PulpTaskError,
    deb_remote_api,
    deb_repository_api,
)

from pulpcore.client.pulp_deb import RepositorySyncURL


class BasicSyncTestCase(unittest.TestCase):
    """Sync a repository with the deb plugin."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()

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
        5. Assert that the correct number of units were added and are present
           in the repo.
        6. Sync the remote one more time.
        7. Assert that repository version is the same as the previous one.
        8. Assert that the same number of content units are present and that no
           units were added.
        """
        repo_api = deb_repository_api
        remote_api = deb_remote_api

        repo = repo_api.create(gen_repo())
        self.addCleanup(repo_api.delete, repo.pulp_href)

        body = gen_deb_remote(sync_udebs=sync_udebs)
        remote = remote_api.create(body)
        self.addCleanup(remote_api.delete, remote.pulp_href)

        # Sync the repository.
        self.assertEqual(repo.latest_version_href, f"{repo.pulp_href}versions/0/")
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = repo_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)
        repo = repo_api.read(repo.pulp_href)

        self.assertIsNotNone(repo.latest_version_href)
        self.assertDictEqual(get_content_summary(repo.to_dict()), fixture_summary)
        self.assertDictEqual(get_added_content_summary(repo.to_dict()), fixture_summary)

        # Sync the repository again.
        latest_version_href = repo.latest_version_href
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = repo_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)
        repo = repo_api.read(repo.pulp_href)

        self.assertEqual(latest_version_href, repo.latest_version_href)
        self.assertDictEqual(get_content_summary(repo.to_dict()), fixture_summary)

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
        repo_api = deb_repository_api
        remote_api = deb_remote_api

        # check if 'lsof' is available
        if cli_client.run(("which", "lsof")).returncode != 0:
            raise unittest.SkipTest("lsof package is not present")

        repo = repo_api.create(gen_repo())
        self.addCleanup(repo_api.delete, repo.pulp_href)

        remote = remote_api.create(gen_deb_remote())
        self.addCleanup(remote_api.delete, remote.pulp_href)

        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = repo_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)

        cmd = "lsof -t +D {}".format(MEDIA_PATH).split()
        response = cli_client.run(cmd).stdout
        self.assertEqual(len(response), 0, response)


class SyncInvalidTestCase(unittest.TestCase):
    """Sync a repository with a given url on the remote."""

    def test_invalid_url(self):
        """Sync a repository using a remote url that does not exist.

        Test that we get a task failure. See :meth:`do_test`.
        """
        with self.assertRaises(PulpTaskError) as exc:
            self.do_test("http://i-am-an-invalid-url.com/invalid/")
        error = exc.exception.task.error
        self.assertIsNotNone(error["description"])

    # Provide an invalid repository and specify keywords in the anticipated error message
    @unittest.skip("FIXME: Plugin writer action required.")
    def test_invalid_deb_content(self):
        """Sync a repository using an invalid plugin_content repository.

        Assert that an exception is raised, and that error message has
        keywords related to the reason of the failure. See :meth:`do_test`.
        """
        with self.assertRaises(PulpTaskError) as exc:
            self.do_test(DEB_INVALID_FIXTURE_URL)
        error = exc.exception.task.error
        for key in ("mismached", "empty"):
            self.assertIn(key, error["description"])

    def do_test(self, url):
        """Sync a repository given ``url`` on the remote."""
        repo_api = deb_repository_api
        remote_api = deb_remote_api

        repo = repo_api.create(gen_repo())
        self.addCleanup(repo_api.delete, repo.pulp_href)

        body = gen_deb_remote(url=url)
        remote = remote_api.create(body)
        self.addCleanup(remote_api.delete, remote.pulp_href)

        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = repo_api.sync(repo.pulp_href, repository_sync_data)
        return monitor_task(sync_response.task)
