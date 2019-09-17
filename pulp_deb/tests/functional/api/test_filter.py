# coding=utf-8
"""Tests that verify download of content served by Pulp."""
import hashlib
import unittest
from random import choice
from urllib.parse import urljoin

from pulp_smash import api, config, utils
from pulp_smash.pulp3.utils import download_content_unit, gen_distribution, gen_repo, sync

from pulp_deb.tests.functional.constants import (
    DEB_PACKAGE_PATH,
    DEB_REMOTE_PATH,
    DEB_REPO_PATH,
)
from pulp_deb.tests.functional.utils import (
    create_deb_publication,
    create_verbatim_publication,
    gen_deb_remote,
    get_deb_content_unit_paths,
    get_deb_verbatim_content_unit_paths,
)
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class PackageVersionFilterTestCase(unittest.TestCase):
    """Verify that Packages can be filtered by versions."""

    def test_package_version_filter(self):
        """Verify that Packages can be filtered by versions.
        """

        # Create and polulate a repo.
        cfg = config.get_config()
        client = api.Client(cfg, api.json_handler)

        repo = client.post(DEB_REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo["pulp_href"])

        body = gen_deb_remote()
        remote = client.post(DEB_REMOTE_PATH, body)
        self.addCleanup(client.delete, remote["pulp_href"])

        sync(cfg, remote, repo)
        repo = client.get(repo["pulp_href"])

        # Query content units with filters
        result = client.get(DEB_PACKAGE_PATH, params={'version': '1.0'})
        self.assertEqual(4, result['count'])

        result = client.get(DEB_PACKAGE_PATH, params={'version__gt': '1.0~'})
        self.assertEqual(4, result['count'])
        result = client.get(DEB_PACKAGE_PATH, params={'version__gt': '1.0'})
        self.assertEqual(0, result['count'])
        result = client.get(DEB_PACKAGE_PATH, params={'version__gt': '1.0+'})
        self.assertEqual(0, result['count'])

        result = client.get(DEB_PACKAGE_PATH, params={'version__gte': '1.0~'})
        self.assertEqual(4, result['count'])
        result = client.get(DEB_PACKAGE_PATH, params={'version__gte': '1.0'})
        self.assertEqual(4, result['count'])
        result = client.get(DEB_PACKAGE_PATH, params={'version__gte': '1.0+'})
        self.assertEqual(0, result['count'])

        result = client.get(DEB_PACKAGE_PATH, params={'version__lt': '1.0~'})
        self.assertEqual(0, result['count'])
        result = client.get(DEB_PACKAGE_PATH, params={'version__lt': '1.0'})
        self.assertEqual(0, result['count'])
        result = client.get(DEB_PACKAGE_PATH, params={'version__lt': '1.0+'})
        self.assertEqual(4, result['count'])

        result = client.get(DEB_PACKAGE_PATH, params={'version__lte': '1.0~'})
        self.assertEqual(0, result['count'])
        result = client.get(DEB_PACKAGE_PATH, params={'version__lte': '1.0'})
        self.assertEqual(4, result['count'])
        result = client.get(DEB_PACKAGE_PATH, params={'version__lte': '1.0+'})
        self.assertEqual(4, result['count'])
