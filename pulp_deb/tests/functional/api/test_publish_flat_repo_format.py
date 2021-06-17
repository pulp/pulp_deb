# coding=utf-8
"""Tests that sync deb plugin repositories."""
import unittest
import os

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
    DEB_FLAT_REPO_FIXTURE_URL,
    DEB_RELEASE_FILE_NAME,
    DEB_RELEASE_NAME,
    DEB_RELEASE_COMPONENT_NAME,
    DEB_PACKAGE_INDEX_NAME,
)
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401
from pulp_deb.tests.functional.utils import (
    gen_deb_remote,
    deb_remote_api,
    deb_repository_api,
    deb_apt_publication_api,
    deb_verbatim_publication_api,
    deb_distribution_api,
)

from pulpcore.client.pulp_deb import (
    RepositorySyncURL,
    DebAptPublication,
    DebVerbatimPublication,
)


class FlatRepoSyncTestCase(unittest.TestCase):
    """Sync a repository with the deb plugin."""

    def _publication_extra_args(self, modus):
        if modus == "verbatim":
            return {}
        else:
            return {modus: True}

    def setUp(self):
        """Cleanup."""
        delete_orphans()

    def test_publish_flat_repo_structured(self):
        """Test publishing flat repository with distribution /."""
        expected_values = {
            "distribution": "/",
            "codename": "ragnarok",
            "suite": "mythology",
            "components": ["flat-repo-component"],
            "release_file_folder_sync": "",
            "release_file_folder_dist": "dists/flat-repo",
            "package_index_paths_sync": ["Packages"],
            "package_index_paths_dist": [
                "dists/flat-repo/flat-repo-component/binary-ppc64/Packages"
            ],
        }
        self.do_publish(expected_values, "structured")

    def test_publish_flat_repo_simple(self):
        """Test publishing flat repository with distribution /."""
        expected_values = {
            "distribution": "/",
            "codename": "ragnarok",
            "suite": "mythology",
            "components": ["flat-repo-component"],
            "release_file_folder_sync": "",
            "release_file_folder_dist": "dists/default/",
            "package_index_paths_sync": ["Packages"],
            "package_index_paths_dist": ["dists/default/all/binary-ppc64/Packages"],
        }
        self.do_publish(expected_values, "simple")

    def test_publish_flat_repo_verbatim(self):
        """Test publishing flat repository with distribution /."""
        expected_values = {
            "distribution": "/",
            "codename": "ragnarok",
            "suite": "mythology",
            "components": ["flat-repo-component"],
            "release_file_folder_sync": "",
            "release_file_folder_dist": "/",
            "package_index_paths_sync": ["Packages"],
            "package_index_paths_dist": ["Packages"],
        }
        self.do_publish(expected_values, "verbatim")

    def test_publish_flat_repo_structured_nested(self):
        """Test publishing flat repository with distribution nest/fjalar/."""
        expected_values = {
            "distribution": "nest/fjalar/",
            "codename": "ragnarok",
            "suite": "mythology",
            "components": ["flat-repo-component"],
            "release_file_folder_sync": "nest/fjalar/",
            "release_file_folder_dist": "dists/nest/fjalar",
            "package_index_paths_sync": ["nest/fjalar/Packages"],
            "package_index_paths_dist": [
                "dists/nest/fjalar/flat-repo-component/binary-ppc64/Packages"
            ],
        }
        self.do_publish(expected_values, "structured")

    def test_publish_flat_repo_simple_nested(self):
        """Test publishing flat repository with distribution nest/fjalar/."""
        expected_values = {
            "distribution": "nest/fjalar/",
            "codename": "ragnarok",
            "suite": "mythology",
            "components": ["flat-repo-component"],
            "release_file_folder_sync": "nest/fjalar/",
            "release_file_folder_dist": "dists/default/",
            "package_index_paths_sync": ["nest/fjalar/Packages"],
            "package_index_paths_dist": ["dists/default/all/binary-ppc64/Packages"],
        }
        self.do_publish(expected_values, "simple")

    def test_publish_flat_repo_verbatim_nested(self):
        """Test publishing flat repository with distribution nest/fjalar/."""
        expected_values = {
            "distribution": "nest/fjalar/",
            "codename": "ragnarok",
            "suite": "mythology",
            "components": ["flat-repo-component"],
            "release_file_folder_sync": "nest/fjalar/",
            "release_file_folder_dist": "nest/fjalar/",
            "package_index_paths_sync": ["nest/fjalar/Packages"],
            "package_index_paths_dist": ["nest/fjalar/Packages"],
        }
        self.do_publish(expected_values, "verbatim")

    def do_publish(self, expected_values, modus):
        """Publish particular repository in flat format.

        1. Create a repository in flat repo format.
        2. Create a publication.
        3. Assert that the publication ``repository_version`` attribute points
           to the latest repository version.
        4. Assert that Release file path is equal to desired file path.
        5. Assert that the codename, suite and component are as expected.
        """
        # Create a repository:
        repo = deb_repository_api.create(gen_repo())
        self.addCleanup(deb_repository_api.delete, repo.pulp_href)

        # Create a remote:
        body = gen_deb_remote(  # DEB_FLAT_REPO_FIXTURE_URL
            url=DEB_FLAT_REPO_FIXTURE_URL, distributions=expected_values["distribution"]
        )
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
        if modus == "verbatim":
            publication_api = deb_verbatim_publication_api
            Publication = DebVerbatimPublication
        else:
            publication_api = deb_apt_publication_api
            Publication = DebAptPublication

        publish_data = Publication(repository=repo.pulp_href, **self._publication_extra_args(modus))
        publish_response = publication_api.create(publish_data)
        publication_href = monitor_task(publish_response.task).created_resources[0]
        self.addCleanup(publication_api.delete, publication_href)
        publication = publication_api.read(publication_href)

        # Test the publication:
        self.assertEqual(publication.repository_version, version_hrefs[-1])

        release_file = get_content(
            repo=publication.to_dict(), version_href=publication.repository_version
        )[DEB_RELEASE_FILE_NAME][0]

        release_file_path = os.path.join(expected_values["release_file_folder_sync"], "Release")
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

        self.assertEqual(len(expected_values["components"]), len(components))
        for component in components:
            self.assertIn(component["component"], expected_values["components"])

        package_indecies = get_content(
            repo=publication.to_dict(), version_href=publication.repository_version
        )[DEB_PACKAGE_INDEX_NAME]

        self.assertEqual(len(expected_values["package_index_paths_sync"]), len(package_indecies))
        for package_index in package_indecies:
            self.assertIn(
                package_index["relative_path"], expected_values["package_index_paths_sync"]
            )

        # Create a distribution:
        body = gen_distribution()
        body["publication"] = publication_href
        distribution_response = deb_distribution_api.create(body)
        distribution_href = monitor_task(distribution_response.task).created_resources[0]
        distribution = deb_distribution_api.read(distribution_href)
        self.addCleanup(deb_distribution_api.delete, distribution.pulp_href)

        # Check that the expected Release files and package indecies are there:
        cfg = config.get_config()
        release_file_path = os.path.join(expected_values["release_file_folder_dist"], "Release")
        download_content_unit(cfg, distribution.to_dict(), release_file_path)
        for package_index_path in expected_values["package_index_paths_dist"]:
            download_content_unit(cfg, distribution.to_dict(), package_index_path)
