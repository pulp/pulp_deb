# coding=utf-8
"""Tests that sync deb plugin repositories."""
import unittest
import os

from debian import deb822

from pulp_smash import config
from pulp_smash.pulp3.bindings import monitor_task
from pulp_smash.pulp3.utils import (
    gen_repo,
    get_content,
    delete_orphans,
    get_versions,
    gen_distribution,
    download_content_unit,
)
from pulp_smash.utils import http_get

from pulp_deb.tests.functional.constants import (
    DEB_COMPLEX_DISTS_FIXTURE_URL,
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
    deb_distribution_api,
)

from pulpcore.client.pulp_deb import (
    RepositorySyncURL,
    DebAptPublication,
)


class ComplexDistSyncTestCase(unittest.TestCase):
    """Sync a repository with the deb plugin."""

    def _publication_extra_args(self):
        return {"structured": True}

    def setUp(self):
        """Cleanup."""
        delete_orphans()

    def test_publish_complex_dist_ubuntu_backports(self):
        """Test publishing repository with distrbution ragnarok-backports."""
        expected_values = {
            "distribution": "ragnarok-backports",
            "codename": "ragnarok",
            "suite": "ragnarok-backports",
            "components": ["asgard", "jotunheimr"],
            "release_file_folder": "dists/ragnarok-backports/",
            "package_index_paths": [
                "dists/ragnarok-backports/asgard/binary-ppc64/Packages",
                "dists/ragnarok-backports/asgard/binary-armeb/Packages",
                "dists/ragnarok-backports/jotunheimr/binary-ppc64/Packages",
                "dists/ragnarok-backports/jotunheimr/binary-armeb/Packages",
            ],
        }
        self.do_publish(expected_values)

    def test_publish_complex_dist_debian_security(self):
        """Test publishing repository with distrbution ragnarok/updates."""
        expected_values = {
            "distribution": "ragnarok/updates",
            "codename": "ragnarok",
            "suite": "stable",
            "components": ["updates/asgard", "updates/jotunheimr"],
            "release_file_folder": "dists/ragnarok/updates/",
            "package_index_paths": [
                "dists/ragnarok/updates/asgard/binary-ppc64/Packages",
                "dists/ragnarok/updates/asgard/binary-armeb/Packages",
                "dists/ragnarok/updates/jotunheimr/binary-ppc64/Packages",
                "dists/ragnarok/updates/jotunheimr/binary-armeb/Packages",
            ],
        }
        self.do_publish(expected_values)

    def do_publish(self, expected_values):
        """Publish particular repository with complex distributions.

        1. Create a repository with complex distribtuions.
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
            url=DEB_COMPLEX_DISTS_FIXTURE_URL, distributions=expected_values["distribution"]
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
        publish_data = DebAptPublication(
            repository=repo.pulp_href, **self._publication_extra_args()
        )
        publish_response = deb_apt_publication_api.create(publish_data)
        publication_href = monitor_task(publish_response.task).created_resources[0]
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

        self.assertEqual(len(expected_values["components"]), len(components))
        for component in components:
            self.assertIn(component["component"], expected_values["components"])

        package_indecies = get_content(
            repo=publication.to_dict(), version_href=publication.repository_version
        )[DEB_PACKAGE_INDEX_NAME]

        self.assertEqual(len(expected_values["package_index_paths"]), len(package_indecies))
        for package_index in package_indecies:
            self.assertIn(package_index["relative_path"], expected_values["package_index_paths"])

        # Create a distribution:
        body = gen_distribution()
        body["publication"] = publication_href
        distribution_response = deb_distribution_api.create(body)
        distribution_href = monitor_task(distribution_response.task).created_resources[0]
        distribution = deb_distribution_api.read(distribution_href)
        self.addCleanup(deb_distribution_api.delete, distribution.pulp_href)

        # Check that the expected Release files and package indecies are there:
        cfg = config.get_config()
        release_file_path = os.path.join(expected_values["release_file_folder"], "Release")
        download_content_unit(cfg, distribution.to_dict(), release_file_path)

        for package_index_path in expected_values["package_index_paths"]:
            published = download_content_unit(cfg, distribution.to_dict(), package_index_path)
            url = "/".join([DEB_COMPLEX_DISTS_FIXTURE_URL, package_index_path])
            remote = http_get(url)
            self.assert_equal_package_index(remote, published, url)

    def assert_equal_package_index(self, orig, new, message):
        """In-detail check of two PackageIndex file-strings"""
        parsed_orig = self.parse_package_index(orig)
        parsed_new = self.parse_package_index(new)

        self.assertEqual(len(parsed_orig), len(parsed_new), message)

        for name, pkg in parsed_new.items():
            orig_pkg = parsed_orig[name]
            for k in orig_pkg.keys():
                self.assertIn(k, pkg, "Field '{}' is missing in package '{}'".format(k, name))
                if k == "Filename":
                    # file-location is allowed to differ :-)
                    continue
                self.assertEqual(
                    pkg[k], orig_pkg[k], "Field '{}' of package '{}' does not match".format(k, name)
                )

    def parse_package_index(self, pkg_idx):
        """Parses PackageIndex file-string.
        Returns a dict of the packages by '<Package>-<Version>-<Architecture>'.
        """
        packages = {}
        for package in deb822.Packages.iter_paragraphs(pkg_idx):
            packages[
                "-".join([package["Package"], package["Version"], package["Architecture"]])
            ] = package
        return packages
