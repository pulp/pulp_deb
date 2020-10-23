# coding=utf-8
"""Tests that sync deb plugin repositories."""
import unittest
import os

from pulp_smash import config

from pulp_smash.pulp3.utils import (
    gen_repo,
    get_content,
    delete_orphans,
    get_versions,
    gen_distribution,
    download_content_unit,
)

from pulp_deb.tests.functional.constants import (
    DEB_MISSING_ARCH_DISTS_FIXTURE_URL,
    DEB_RELEASE_FILE_NAME,
    DEB_RELEASE_NAME,
    DEB_RELEASE_COMPONENT_NAME,
    DEB_PACKAGE_INDEX_NAME,
)
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401
from pulp_deb.tests.functional.utils import (
    gen_deb_remote,
    monitor_task,
    deb_remote_api,
    deb_repository_api,
    deb_apt_publication_api,
    deb_distribution_api,
)

from pulpcore.client.pulp_deb import (
    RepositorySyncURL,
    DebAptPublication,
)


class MissingArchDistSyncTestCase(unittest.TestCase):
    """Sync a repository with the deb plugin."""

    def _publication_extra_args(self):
        return {"structured": True}

    def setUp(self):
        """Cleanup."""
        delete_orphans()

    def test_publish_missing_architecture(self):
        """Test publishing repository without Packages file or only Packages.gz or Packages.xz."""
        expected_values = {
            "distribution": "ragnarok",
            "codename": "ragnarok",
            "suite": "mythology",
            "components": ["asgard", "jotunheimr"],
            "architectures_in_release": ["armeb", "ppc64"],
            "release_file_folder": "dists/ragnarok/",
            "package_index_paths": [
                "dists/ragnarok/asgard/binary-ppc64",
                "dists/ragnarok/asgard/binary-armeb",  # not there
                "dists/ragnarok/jotunheimr/binary-ppc64",
                "dists/ragnarok/jotunheimr/binary-armeb",  # not there
            ],
        }
        self.do_publish(expected_values)

    def do_publish(self, expected_values):
        """Publish particular repository with missing package indices.

        1. Create a repository with missing package indices.
        2. Create a publication.
        3. Assert that the publication ``repository_version`` attribute points
           to the latest repository version.
        4. Assert that InRelease file path is equal to desired file path.
        5. Assert that the codename, suite and component are as expected.
        """
        # Create a repository:
        repo = deb_repository_api.create(gen_repo())
        self.addCleanup(deb_repository_api.delete, repo.pulp_href)

        # Create a remote:
        body = gen_deb_remote(
            url=DEB_MISSING_ARCH_DISTS_FIXTURE_URL,
            distributions=expected_values["distribution"],
            ignore_missing_package_indices=True,
        )
        remote = deb_remote_api.create(body)
        self.addCleanup(deb_remote_api.delete, remote.pulp_href)

        # Sync the repository:
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = deb_repository_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)
        repo = deb_repository_api.read(repo.pulp_href)
        version_hrefs = tuple(ver["pulp_href"] for ver in get_versions(repo.to_dict()))

        # Create a publication:
        publish_data = DebAptPublication(
            repository=repo.pulp_href, **self._publication_extra_args()
        )
        publish_response = deb_apt_publication_api.create(publish_data)
        created_resources = monitor_task(publish_response.task)
        publication_href = created_resources[0]
        self.addCleanup(deb_apt_publication_api.delete, publication_href)
        publication = deb_apt_publication_api.read(publication_href)

        # Test the publication:
        self.assertEqual(publication.repository_version, version_hrefs[-1])

        release_file = get_content(
            repo=publication.to_dict(), version_href=publication.repository_version
        )[DEB_RELEASE_FILE_NAME][0]

        release_file_path = os.path.join(expected_values["release_file_folder"], "InRelease")
        self.assertEqual(release_file_path, release_file["relative_path"])
        self.assertEqual(expected_values["distribution"], release_file["distribution"])
        self.assertEqual(expected_values["codename"], release_file["codename"])
        self.assertEqual(expected_values["suite"], release_file["suite"])

        release = get_content(
            repo=publication.to_dict(), version_href=publication.repository_version
        )[DEB_RELEASE_NAME][0]

        self.assertEqual(expected_values["distribution"], release["distribution"])
        self.assertEqual(expected_values["codename"], release["codename"])
        self.assertEqual(expected_values["suite"], release["suite"])

        components = get_content(
            repo=publication.to_dict(), version_href=publication.repository_version
        )[DEB_RELEASE_COMPONENT_NAME]

        self.assertEqual({c["component"] for c in components}, set(expected_values["components"]))

        package_indices = get_content(
            repo=publication.to_dict(), version_href=publication.repository_version
        )[DEB_PACKAGE_INDEX_NAME]

        # Packages has index in release file but may not be there
        self.assertNotEqual(len(expected_values["package_index_paths"]), len(package_indices))
        for package_index in package_indices:  # all existing Packages files are there
            is_true = False
            for package_index_expected in expected_values["package_index_paths"]:
                if package_index["relative_path"] == os.path.join(
                    package_index_expected, "Packages"
                ):
                    is_true = True
            self.assertTrue(is_true)

        self.assertFalse(
            os.path.isdir(os.path.join(remote.url, "dists/ragnarok/asgard/binary-armeb"))
        )
        self.assertFalse(
            os.path.isdir(os.path.join(remote.url, "dists/ragnarok/jotunheimr/binary-armeb"))
        )

        # Create a distribution:
        body = gen_distribution()
        body["publication"] = publication_href
        distribution_response = deb_distribution_api.create(body)
        distribution_href = monitor_task(distribution_response.task)[0]
        distribution = deb_distribution_api.read(distribution_href)
        self.addCleanup(deb_distribution_api.delete, distribution.pulp_href)

        # Check that the expected Release files and package indices are there:
        cfg = config.get_config()
        release_file_path = os.path.join(expected_values["release_file_folder"], "Release")
        download_content_unit(cfg, distribution.to_dict(), release_file_path)

        for package_index_path in expected_values["package_index_paths"]:
            download_content_unit(cfg, distribution.to_dict(), package_index_path + "/Packages")
