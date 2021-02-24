# coding=utf-8
"""Tests that sync file plugin repositories."""
import unittest

from pulp_smash import config
from pulp_smash.pulp3.bindings import monitor_task
from pulp_smash.pulp3.utils import gen_repo

from pulp_deb.tests.functional.utils import gen_apt_client, gen_apt_remote
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401

from pulpcore.client.pulp_deb import (
    ContentPackagesApi,
    DistributionsAptApi,
    PublicationsAptApi,
    PublishSettingsAptApi,
    RepositoriesAptApi,
    AptRepositorySyncURL,
    RemotesAptApi,
)


class AutoPublishDistributeTestCase(unittest.TestCase):
    """Test auto-publish and auto-distribution."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = gen_apt_client()

        cls.content_api = ContentPackagesApi(cls.client)
        cls.repo_api = RepositoriesAptApi(cls.client)
        cls.remote_api = RemotesAptApi(cls.client)
        cls.publications_api = PublicationsAptApi(cls.client)
        cls.publish_settings_api = PublishSettingsAptApi(cls.client)
        cls.distributions_api = DistributionsAptApi(cls.client)

    def setUp(self):
        """Create remote, repo, publish settings, and distribution."""
        self.remote = self.remote_api.create(gen_apt_remote())
        self.publish_settings = self.publish_settings_api.create({"sqlite_metadata": True})
        self.repo = self.repo_api.create(gen_repo(publish_settings=self.publish_settings.pulp_href))
        response = self.distributions_api.create(
            {"name": "foo", "base_path": "bar/foo", "repository": self.repo.pulp_href}
        )
        distribution_href = monitor_task(response.task).created_resources[0]
        self.distribution = self.distributions_api.read(distribution_href)

    def tearDown(self):
        """Clean up."""
        self.repo_api.delete(self.repo.pulp_href)
        self.remote_api.delete(self.remote.pulp_href)
        self.distributions_api.delete(self.distribution.pulp_href)
        self.publish_settings_api.delete(self.publish_settings.pulp_href)

    def test_01_sync(self):
        """Assert that syncing the repository triggers auto-publish and auto-distribution."""
        self.assertEqual(self.publications_api.list().count, 0)
        self.assertTrue(self.distribution.publication is None)

        # Sync the repository.
        repository_sync_data = AptRepositorySyncURL(remote=self.remote.pulp_href)
        sync_response = self.repo_api.sync(self.repo.pulp_href, repository_sync_data)
        task = monitor_task(sync_response.task)
        self.distribution = self.distributions_api.read(self.distribution.pulp_href)

        # Check that all the appropriate resources were created
        self.assertGreater(len(task.created_resources), 1)
        self.assertEqual(self.publications_api.list().count, 1)
        self.assertTrue(self.distribution.publication is not None)
        self.assertTrue(self.distribution.publication in task.created_resources)

        # Check that the publish settings were used
        publication = self.publications_api.read(self.distribution.publication)
        self.assertEqual(publication.sqlite_metadata, True)

        # Sync the repository again. Since there should be no new repository version, there
        # should be no new publications or distributions either.
        sync_response = self.repo_api.sync(self.repo.pulp_href, repository_sync_data)
        task = monitor_task(sync_response.task)

        self.assertEqual(len(task.created_resources), 0)
        self.assertEqual(self.publications_api.list().count, 1)

    def test_02_modify(self):
        """Assert that modifying the repository triggers auto-publish and auto-distribution."""
        self.assertEqual(self.publications_api.list().count, 0)
        self.assertTrue(self.distribution.publication is None)

        # Modify the repository by adding a coment unit
        content = self.content_api.list().results[0].pulp_href

        modify_response = self.repo_api.modify(
            self.repo.pulp_href, {"add_content_units": [content]}
        )
        task = monitor_task(modify_response.task)
        self.distribution = self.distributions_api.read(self.distribution.pulp_href)

        # Check that all the appropriate resources were created
        self.assertGreater(len(task.created_resources), 1)
        self.assertEqual(self.publications_api.list().count, 1)
        self.assertTrue(self.distribution.publication is not None)
        self.assertTrue(self.distribution.publication in task.created_resources)

        # Check that the publish settings were used
        publication = self.publications_api.read(self.distribution.publication)
        self.assertEqual(publication.sqlite_metadata, True)
