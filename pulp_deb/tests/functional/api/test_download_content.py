# coding=utf-8
"""Tests that verify download of content served by Pulp."""
import hashlib
import unittest
from random import choice
from urllib.parse import urljoin

from pulp_smash import api, config, utils
from pulp_smash.pulp3.utils import download_content_unit, gen_distribution, gen_repo, sync

from pulp_deb.tests.functional.constants import (
    DEB_DISTRIBUTION_PATH,
    DEB_FIXTURE_URL,
    DEB_REMOTE_PATH,
    DEB_REPO_PATH,
    DOWNLOAD_POLICIES,
)
from pulp_deb.tests.functional.utils import (
    create_deb_publication,
    create_verbatim_publication,
    gen_deb_remote,
    get_deb_content_unit_paths,
    get_deb_verbatim_content_unit_paths,
)
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class DownloadContentTestCase(unittest.TestCase):
    """Verify whether content served by pulp can be downloaded."""

    class Meta:
        create_publication = create_deb_publication
        DISTRIBUTION_PATH = DEB_DISTRIBUTION_PATH
        get_content_unit_paths = get_deb_content_unit_paths

    def test_all(self):
        """Download content from Pulp. Content is synced with different policies.

        See :meth:`do_test`.
        """
        for policy in DOWNLOAD_POLICIES:
            with self.subTest(policy):
                self.do_test(policy)

    def do_test(self, policy):
        """Verify whether content served by pulp can be downloaded.

        The process of publishing content is more involved in Pulp 3 than it
        was under Pulp 2. Given a repository, the process is as follows:

        1. Create a publication from the repository. (The latest repository
           version is selected if no version is specified.) A publication is a
           repository version plus metadata.
        2. Create a distribution from the publication. The distribution defines
           at which URLs a publication is available, e.g.
           ``http://example.com/content/foo/`` and
           ``http://example.com/content/bar/``.

        Do the following:

        1. Create, populate, publish, and distribute a repository.
        2. Select a random content unit in the distribution. Download that
           content unit from Pulp, and verify that the content unit has the
           same checksum when fetched directly from Pulp-Fixtures.

        This test targets the following issues:

        * `Pulp #2895 <https://pulp.plan.io/issues/2895>`_
        * `Pulp Smash #872 <https://github.com/PulpQE/pulp-smash/issues/872>`_
        """
        cfg = config.get_config()
        client = api.Client(cfg, api.json_handler)

        repo = client.post(DEB_REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo["pulp_href"])

        body = gen_deb_remote()
        remote = client.post(DEB_REMOTE_PATH, body)
        self.addCleanup(client.delete, remote["pulp_href"])

        sync(cfg, remote, repo)
        repo = client.get(repo["pulp_href"])

        # Create a publication.
        publication = self.Meta.create_publication(cfg, repo)
        self.addCleanup(client.delete, publication["pulp_href"])

        # Create a distribution.
        body = gen_distribution()
        body["publication"] = publication["pulp_href"]
        distribution = client.using_handler(api.task_handler).post(
            self.Meta.DISTRIBUTION_PATH, body
        )
        self.addCleanup(client.delete, distribution["pulp_href"])

        # Pick a content unit (of each type), and download it from both Pulp Fixtures…
        unit_paths = [
            choice(paths) for paths in self.Meta.get_content_unit_paths(repo).values() if paths
        ]
        fixtures_hashes = [
            hashlib.sha256(utils.http_get(urljoin(DEB_FIXTURE_URL, unit_path[0]))).hexdigest()
            for unit_path in unit_paths
        ]

        # …and Pulp.
        contents = [
            download_content_unit(cfg, distribution, unit_path[1]) for unit_path in unit_paths
        ]
        pulp_hashes = [hashlib.sha256(content).hexdigest() for content in contents]
        self.assertEqual(fixtures_hashes, pulp_hashes)


class VerbatimDownloadContentTestCase(DownloadContentTestCase):
    """Verify whether content served by pulp can be downloaded."""

    class Meta:
        create_publication = create_verbatim_publication
        DISTRIBUTION_PATH = DEB_DISTRIBUTION_PATH
        get_content_unit_paths = get_deb_verbatim_content_unit_paths
