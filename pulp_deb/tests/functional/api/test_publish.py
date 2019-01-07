# coding=utf-8
"""Tests that publish deb plugin repositories."""
import unittest
from random import choice
from urllib.parse import urljoin

from requests.exceptions import HTTPError

from pulp_smash import api, config
from pulp_smash.pulp3.constants import REPO_PATH
from pulp_smash.pulp3.utils import (
    gen_repo,
    get_content,
    get_versions,
    publish,
    sync,
)

from pulp_deb.tests.functional.utils import (
    gen_deb_remote,
    gen_deb_publisher,
    gen_deb_verbatim_publisher,
)
from pulp_deb.tests.functional.constants import (
    DEB_PACKAGE_NAME,
    DEB_GENERIC_CONTENT_NAME,
    DEB_REMOTE_PATH,
    DEB_PUBLISHER_PATH,
    DEB_VERBATIM_PUBLISHER_PATH,
)
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class PublishAnyRepoVersionTestCase(unittest.TestCase):
    """Test whether a particular repository version can be published.

    This test targets the following issues:

    * `Pulp #3324 <https://pulp.plan.io/issues/3324>`_
    * `Pulp Smash #897 <https://github.com/PulpQE/pulp-smash/issues/897>`_
    """

    class Meta:
        publisher_path = DEB_PUBLISHER_PATH
        gen_publisher = gen_deb_publisher

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
        self.addCleanup(client.delete, remote['_href'])

        repo = client.post(REPO_PATH, gen_repo())
        self.addCleanup(client.delete, repo['_href'])

        sync(cfg, remote, repo)

        publisher = client.post(self.Meta.publisher_path, self.Meta.gen_publisher())
        self.addCleanup(client.delete, publisher['_href'])

        # Step 1
        repo = client.get(repo['_href'])
        for deb_generic_content in get_content(repo)[DEB_GENERIC_CONTENT_NAME]:
            client.post(
                repo['_versions_href'],
                {'add_content_units': [deb_generic_content['_href']]}
            )
        for deb_package in get_content(repo)[DEB_PACKAGE_NAME]:
            client.post(
                repo['_versions_href'],
                {'add_content_units': [deb_package['_href']]}
            )
        version_hrefs = tuple(ver['_href'] for ver in get_versions(repo))
        non_latest = choice(version_hrefs[:-1])

        # Step 2
        publication = publish(cfg, publisher, repo)

        # Step 3
        self.assertEqual(publication['repository_version'], version_hrefs[-1])

        # Step 4
        publication = publish(cfg, publisher, repo, non_latest)

        # Step 5
        self.assertEqual(publication['repository_version'], non_latest)

        # Step 6
        with self.assertRaises(HTTPError):
            body = {
                'repository': repo['_href'],
                'repository_version': non_latest
            }
            client.post(urljoin(publisher['_href'], 'publish/'), body)


class VerbatimPublishAnyRepoVersionTestCase(PublishAnyRepoVersionTestCase):
    """Test whether a particular repository version can be published verbatim.

    This test targets the following issues:

    * `Pulp #3324 <https://pulp.plan.io/issues/3324>`_
    * `Pulp Smash #897 <https://github.com/PulpQE/pulp-smash/issues/897>`_
    """

    class Meta:
        publisher_path = DEB_VERBATIM_PUBLISHER_PATH
        gen_publisher = gen_deb_verbatim_publisher
