# coding=utf-8
"""Tests that sync deb plugin repositories."""
import unittest

from pulp_smash import config
from pulp_smash.pulp3.bindings import monitor_task, delete_orphans
from pulp_smash.pulp3.utils import (
    gen_repo,
    get_content,
    get_versions,
    gen_distribution,
    download_content_unit,
)

from pulp_deb.tests.functional.constants import (
    DEB_FIXTURE_URL,
    DEB_PACKAGE_INDEX_NAME,
    DEB_PACKAGE_NAME,
)
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401
from pulp_deb.tests.functional.utils import (
    gen_deb_remote,
    deb_remote_api,
    deb_repository_api,
    deb_apt_publication_api,
    deb_distribution_api,
)

from pulpcore.client.pulp_deb import (
    RepositorySyncURL,
    DebAptPublication,
)


class EmptyRepositoryTestCase(unittest.TestCase):
    """Sync a repository with the deb plugin."""

    def _publication_extra_args(self):
        return {"simple": True, "structured": True}

    def setUp(self):
        """Cleanup."""
        delete_orphans()

    def test_publish(self):
        """Publish particular empty repository with no packages.

        1. Create a repository with given distribtuions.
        2. Create a publication.
        3. Assert that the publication ``repository_version`` attribute points
           to the latest repository version.
        4. Assert that Package Index File is not empty.
        5. Assert that there are no packages.
        """
        # Create a repository:
        repo = deb_repository_api.create(gen_repo())
        self.addCleanup(deb_repository_api.delete, repo.pulp_href)

        # Create a remote:
        body = gen_deb_remote(url=DEB_FIXTURE_URL, distributions="ginnungagap")
        remote = deb_remote_api.create(body)
        self.addCleanup(deb_remote_api.delete, remote.pulp_href)

        # Sync the repository:
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = deb_repository_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)
        repo = deb_repository_api.read(repo.pulp_href)
        version_hrefs = tuple(ver["pulp_href"] for ver in get_versions(repo.to_dict()))

        self.assertIsNotNone(repo.latest_version_href)

        # Create a publication:
        publish_data = DebAptPublication(
            repository=repo.pulp_href, **self._publication_extra_args()
        )
        publish_response = deb_apt_publication_api.create(publish_data)
        publication_href = monitor_task(publish_response.task).created_resources[0]
        self.addCleanup(deb_apt_publication_api.delete, publication_href)
        publication = deb_apt_publication_api.read(publication_href)

        # Test the publication:
        self.assertEqual(publication.repository_version, version_hrefs[-1])

        release = get_content(
            repo=publication.to_dict(), version_href=publication.repository_version
        )

        package_index_paths = [
            "dists/ginnungagap/asgard/binary-ppc64/Packages",
            "dists/ginnungagap/jotunheimr/binary-armeb/Packages",
            "dists/ginnungagap/asgard/binary-armeb/Packages",
            "dists/ginnungagap/jotunheimr/binary-ppc64/Packages",
            "dists/default/all/binary-all/Packages",
        ]

        self.assertFalse(release[DEB_PACKAGE_NAME])
        self.assertTrue(release[DEB_PACKAGE_INDEX_NAME])
        self.assertEqual(len(package_index_paths) - 1, len(release[DEB_PACKAGE_INDEX_NAME]))

        # Create a distribution:
        body = gen_distribution()
        body["publication"] = publication_href
        distribution_response = deb_distribution_api.create(body)
        distribution_href = monitor_task(distribution_response.task).created_resources[0]
        distribution = deb_distribution_api.read(distribution_href)
        self.addCleanup(deb_distribution_api.delete, distribution.pulp_href)

        # Check that the expected package indecies are there:
        cfg = config.get_config()
        for package_index_path in package_index_paths:
            download_content_unit(cfg, distribution.to_dict(), package_index_path)
