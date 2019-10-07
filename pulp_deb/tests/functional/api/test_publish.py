# coding=utf-8
"""Tests that publish deb plugin repositories."""
import unittest
from random import choice

from requests.exceptions import HTTPError

from pulp_smash import api, config
from pulp_smash.pulp3.constants import REPO_PATH
from pulp_smash.pulp3.utils import gen_repo, get_content, get_versions, sync

from pulp_deb.tests.functional.constants import (
    DEB_GENERIC_CONTENT_NAME,
    DEB_PACKAGE_NAME,
    DEB_PUBLICATION_PATH,
    DEB_REMOTE_PATH,
    VERBATIM_PUBLICATION_PATH,
)
from pulp_deb.tests.functional.utils import (
    create_deb_publication,
    create_verbatim_publication,
    gen_deb_remote,
)
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class PublishAnyRepoVersionTestCase(unittest.TestCase):
    """Test whether a particular repository version can be published.

    This test targets the following issues:

    * `Pulp #3324 <https://pulp.plan.io/issues/3324>`_
    * `Pulp Smash #897 <https://github.com/PulpQE/pulp-smash/issues/897>`_
    """

    class Meta:
        PUBLICATION_PATH = DEB_PUBLICATION_PATH
        create_publication = create_deb_publication

    def test_all(self):
        """Test whether a particular repository version can be published.

        1. Create a repository with at least 2 repository versions.
        2. Create a publication by supplying the latest ``repository_version``.
        3. Assert that the publication ``repository_version`` attribute points
           to the latest repository version.
        4. Create a publication by supplying the non-latest ``repository_version``.
        5. Assert that the publication ``repository_version`` attribute points
           to the supplied repository version.
        6. Assert that an exception is raised when providing two different
           repository versions to be published at same time.
        """
        cfg = config.get_config()
        client = api.Client(cfg, api.json_handler)

        body = gen_deb_remote()
        remote = client.post(DEB_REMOTE_PATH, body)
        self.addCleanup(client.delete, remote["pulp_href"])

        repo = client.post(REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo["pulp_href"])

        sync(cfg, remote, repo)

        # Step 1
        repo = client.get(repo["pulp_href"])
        for deb_generic_content in get_content(repo)[DEB_GENERIC_CONTENT_NAME]:
            client.post(
                repo["versions_href"], {"add_content_units": [deb_generic_content["pulp_href"]]}
            )
        for deb_package in get_content(repo)[DEB_PACKAGE_NAME]:
            client.post(repo["versions_href"], {"add_content_units": [deb_package["pulp_href"]]})
        version_hrefs = tuple(ver["pulp_href"] for ver in get_versions(repo))
        non_latest = choice(version_hrefs[:-1])

        # Step 2
        publication = self.Meta.create_publication(cfg, repo)

        # Step 3
        self.assertEqual(publication["repository_version"], version_hrefs[-1])

        # Step 4
        publication = self.Meta.create_publication(cfg, repo, non_latest)

        # Step 5
        self.assertEqual(publication["repository_version"], non_latest)

        # Step 6
        with self.assertRaises(HTTPError):
            body = {"repository": repo["pulp_href"], "repository_version": non_latest}
            client.post(self.Meta.PUBLICATION_PATH, body)


class VerbatimPublishAnyRepoVersionTestCase(PublishAnyRepoVersionTestCase):
    """Test whether a particular repository version can be published verbatim.

    This test targets the following issues:

    * `Pulp #3324 <https://pulp.plan.io/issues/3324>`_
    * `Pulp Smash #897 <https://github.com/PulpQE/pulp-smash/issues/897>`_
    """

    class Meta:
        PUBLICATION_PATH = VERBATIM_PUBLICATION_PATH
        create_publication = create_verbatim_publication
