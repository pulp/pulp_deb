# coding=utf-8
"""Tests for Pulp`s download policies."""
from random import choice
import unittest

from pulp_smash import api, config
from pulp_smash.pulp3.constants import ARTIFACTS_PATH, ON_DEMAND_DOWNLOAD_POLICIES, REPO_PATH
from pulp_smash.pulp3.utils import (
    delete_orphans,
    gen_repo,
    get_added_content_summary,
    get_content_summary,
    sync,
)

from pulp_deb.tests.functional.constants import (
    DEB_FIXTURE_PACKAGE_COUNT,
    DEB_FIXTURE_SUMMARY,
    DEB_PACKAGE_PATH,
    DEB_REMOTE_PATH,
)
from pulp_deb.tests.functional.utils import create_deb_publication, gen_deb_remote
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class SyncPublishDownloadPolicyTestCase(unittest.TestCase):
    """Sync/Publish a repository with different download policies.

    This test targets the following issues:

    `Pulp #4126 <https://pulp.plan.io/issues/4126>`_
    `Pulp #4418 <https://pulp.plan.io/issues/4418>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.page_handler)

    def test_on_demand(self):
        """Sync and publish with ``on_demand`` download policy.

        See :meth:`do_sync`.
        See :meth:`do_publish`.
        """
        self.do_sync("on_demand")
        self.do_publish("on_demand")

    def test_streamed(self):
        """Sync and publish with ``streamend`` download policy.

        See :meth:`do_sync`.
        See :meth:`do_publish`.
        """
        self.do_sync("streamed")
        self.do_publish("streamed")

    def do_sync(self, download_policy):
        """Sync repositories with the different ``download_policy``.

        Do the following:

        1. Create a repository, and a remote.
        2. Assert that repository version is None.
        3. Sync the remote.
        4. Assert that repository version is not None.
        5. Assert that the correct number of possible units to be downloaded
           were shown.
        6. Sync the remote one more time in order to create another repository
           version.
        7. Assert that repository version is different from the previous one.
        8. Assert that the same number of units are shown, and after the
           second sync no extra units should be shown, since the same remote
           was synced again.
        """
        # delete orphans to assure that no content units are present on the
        # file system
        delete_orphans(self.cfg)
        repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["_href"])

        body = gen_deb_remote(policy=download_policy)
        remote = self.client.post(DEB_REMOTE_PATH, body)
        self.addCleanup(self.client.delete, remote["_href"])

        # Sync the repository.
        self.assertIsNone(repo["_latest_version_href"])
        sync(self.cfg, remote, repo)
        repo = self.client.get(repo["_href"])

        self.assertIsNotNone(repo["_latest_version_href"])
        self.assertDictEqual(get_content_summary(repo), DEB_FIXTURE_SUMMARY)
        self.assertDictEqual(get_added_content_summary(repo), DEB_FIXTURE_SUMMARY)

        # Sync the repository again.
        latest_version_href = repo["_latest_version_href"]
        sync(self.cfg, remote, repo)
        repo = self.client.get(repo["_href"])

        self.assertNotEqual(latest_version_href, repo["_latest_version_href"])
        self.assertDictEqual(get_content_summary(repo), DEB_FIXTURE_SUMMARY)
        self.assertDictEqual(get_added_content_summary(repo), {})

    def do_publish(self, download_policy):
        """Publish repository synced with lazy download policy."""
        repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["_href"])

        body = gen_deb_remote(policy=download_policy)
        remote = self.client.post(DEB_REMOTE_PATH, body)
        self.addCleanup(self.client.delete, remote["_href"])

        sync(self.cfg, remote, repo)
        repo = self.client.get(repo["_href"])

        publication = create_deb_publication(self.cfg, repo)
        self.assertIsNotNone(publication["repository_version"], publication)


class LazySyncedContentAccessTestCase(unittest.TestCase):
    """Verify that lazy synced content can be acessed using content endpoint.

    Assert that one acessing lazy synced content using the content endpoint,
    e.g. ``http://localhost/pulp/api/v3/content/deb/packages`` will not raise
    an HTTP exception.

    This test targets the following issue:

    `Pulp #4463 <https://pulp.plan.io/issues/4463>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.page_handler)

    def test_on_demand(self):
        """Test ``on_demand``. See :meth:`do_test`."""
        self.do_test("on_demand")

    def test_streamed(self):
        """Test ``streamed``. See :meth:`do_test`."""
        self.do_test("streamed")

    def do_test(self, policy):
        """Access lazy synced content on using content endpoint."""
        # delete orphans to assure that no content units are present on the
        # file system
        delete_orphans(self.cfg)
        repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo["_href"])

        body = gen_deb_remote(policy=policy)
        remote = self.client.post(DEB_REMOTE_PATH, body)
        self.addCleanup(self.client.delete, remote["_href"])

        # Sync the repository.
        self.assertIsNone(repo["_latest_version_href"])
        sync(self.cfg, remote, repo)
        repo = self.client.get(repo["_href"])
        self.assertIsNotNone(repo["_latest_version_href"])

        # Assert that no HTTP error was raised.
        # Assert that the number of units present is according to the synced
        # feed.
        content = self.client.get(DEB_PACKAGE_PATH)
        self.assertEqual(len(content), DEB_FIXTURE_PACKAGE_COUNT, content)


class SwitchDownloadPolicyTestCase(unittest.TestCase):
    """Perform a lazy sync, and change to immediate to force download.

    Perform an immediate sync to download artifacts for content units that
    are already created.

    This test case targets the following issue:

    * `Pulp #4467 <https://pulp.plan.io/issues/4467>`_
    """

    def test_all(self):
        """Perform a lazy sync and change to immeditae to force download."""
        NON_LAZY_ARTIFACT_COUNT = 11
        cfg = config.get_config()
        # delete orphans to assure that no content units are present on the
        # file system
        delete_orphans(cfg)
        client = api.Client(cfg, api.page_handler)

        repo = client.post(REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo["_href"])

        body = gen_deb_remote(policy=choice(ON_DEMAND_DOWNLOAD_POLICIES))
        remote = client.post(DEB_REMOTE_PATH, body)
        self.addCleanup(client.delete, remote["_href"])

        # Sync the repository using a lazy download policy
        sync(cfg, remote, repo)
        artifacts = client.get(ARTIFACTS_PATH)
        self.assertEqual(len(artifacts), NON_LAZY_ARTIFACT_COUNT, artifacts)

        # Update the policy to immediate
        client.patch(remote["_href"], {"policy": "immediate"})
        remote = client.get(remote["_href"])
        self.assertEqual(remote["policy"], "immediate")

        # Sync using immediate download policy
        sync(cfg, remote, repo)

        # Assert that missing artifacts are downloaded
        artifacts = client.get(ARTIFACTS_PATH)
        self.assertEqual(
            len(artifacts), NON_LAZY_ARTIFACT_COUNT + DEB_FIXTURE_PACKAGE_COUNT, artifacts
        )
