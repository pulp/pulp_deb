# coding=utf-8
"""Tests that publish deb plugin repositories."""
import unittest
from random import choice

from pulp_smash import config
from pulp_smash.pulp3.bindings import monitor_task
from pulp_smash.pulp3.utils import gen_repo, get_content, get_versions, modify_repo

from pulp_deb.tests.functional.constants import (
    DEB_GENERIC_CONTENT_NAME,
    DEB_PACKAGE_NAME,
)
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401
from pulp_deb.tests.functional.utils import (
    gen_deb_remote,
    deb_apt_publication_api,
    deb_remote_api,
    deb_repository_api,
    deb_verbatim_publication_api,
    signing_service_api,
)

from pulpcore.client.pulp_deb import (
    RepositorySyncURL,
    DebAptPublication,
    DebVerbatimPublication,
)
from pulpcore.client.pulp_deb.exceptions import ApiException


class PublishAnyRepoVersionSimpleTestCase(unittest.TestCase):
    """Test whether a particular repository version can be published simple.

    This test targets the following issues:

    * `Pulp #3324 <https://pulp.plan.io/issues/3324>`_
    * `Pulp Smash #897 <https://github.com/pulp/pulp-smash/issues/897>`_
    """

    class Meta:
        publication_api = deb_apt_publication_api
        Publication = DebAptPublication

    def _publication_extra_args(self):
        return {"simple": True}

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
        repo_api = deb_repository_api
        remote_api = deb_remote_api
        publication_api = self.Meta.publication_api

        body = gen_deb_remote()
        remote = remote_api.create(body)
        self.addCleanup(remote_api.delete, remote.pulp_href)

        repo = repo_api.create(gen_repo())
        self.addCleanup(repo_api.delete, repo.pulp_href)

        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = repo_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)

        # Step 1
        repo = repo_api.read(repo.pulp_href)
        for deb_generic_content in get_content(repo.to_dict())[DEB_GENERIC_CONTENT_NAME]:
            modify_repo(cfg, repo.to_dict(), remove_units=[deb_generic_content])
        for deb_package in get_content(repo.to_dict())[DEB_PACKAGE_NAME]:
            modify_repo(cfg, repo.to_dict(), remove_units=[deb_package])
        version_hrefs = tuple(ver["pulp_href"] for ver in get_versions(repo.to_dict()))
        non_latest = choice(version_hrefs[:-1])

        # Step 2
        publish_data = self.Meta.Publication(
            repository=repo.pulp_href, **self._publication_extra_args()
        )
        publish_response = publication_api.create(publish_data)
        publication_href = monitor_task(publish_response.task).created_resources[0]
        self.addCleanup(publication_api.delete, publication_href)
        publication = publication_api.read(publication_href)

        # Step 3
        self.assertEqual(publication.repository_version, version_hrefs[-1])

        # Step 4
        publish_data = self.Meta.Publication(
            repository_version=non_latest, **self._publication_extra_args()
        )
        publish_response = publication_api.create(publish_data)
        publication_href = monitor_task(publish_response.task).created_resources[0]
        publication = publication_api.read(publication_href)

        # Step 5
        self.assertEqual(publication.repository_version, non_latest)

        # Step 6
        with self.assertRaises(ApiException):
            body = {"repository": repo.pulp_href, "repository_version": non_latest}
            publication_api.create(body)


class PublishAnyRepoVersionStructuredTestCase(PublishAnyRepoVersionSimpleTestCase):
    """Test whether a particular repository version can be published structured.

    This test targets the following issues:

    * `Pulp #3324 <https://pulp.plan.io/issues/3324>`_
    * `Pulp Smash #897 <https://github.com/pulp/pulp-smash/issues/897>`_
    """

    class Meta:
        publication_api = deb_apt_publication_api
        Publication = DebAptPublication

    def _publication_extra_args(self):
        return {"structured": True}


class PublishAnyRepoVersionCombinedTestCase(PublishAnyRepoVersionSimpleTestCase):
    """Test whether a particular repository version can be published both simple and structured.

    This test targets the following issues:

    * `Pulp #3324 <https://pulp.plan.io/issues/3324>`_
    * `Pulp Smash #897 <https://github.com/pulp/pulp-smash/issues/897>`_
    """

    class Meta:
        publication_api = deb_apt_publication_api
        Publication = DebAptPublication

    def _publication_extra_args(self):
        return {"simple": True, "structured": True}


@unittest.skip("Disabled - Breaks CI")
class PublishAnyRepoVersionSignedTestCase(PublishAnyRepoVersionSimpleTestCase):
    """Test whether a particular repository version can be published with signed metadata.

    This test targets the following issues:

    * `PulpDeb #6171 <https://pulp.plan.io/issues/6171>`_
    """

    class Meta:
        publication_api = deb_apt_publication_api
        Publication = DebAptPublication

    def _publication_extra_args(self):
        return {
            "simple": True,
            "structured": True,
            "signing_service": self.signing_service.pulp_href,
        }

    def setUp(self):
        """Find SigningService for use in tests."""
        response = signing_service_api.list(name="sign_deb_release")
        if response.count == 0:
            self.fail(
                """No signing service setup.
Please call pulp_deb/pulp_deb/tests/functional/setup_signing_service.py"""
            )
        self.signing_service = response.results[0]


class VerbatimPublishAnyRepoVersionTestCase(PublishAnyRepoVersionSimpleTestCase):
    """Test whether a particular repository version can be published verbatim.

    This test targets the following issues:

    * `Pulp #3324 <https://pulp.plan.io/issues/3324>`_
    * `Pulp Smash #897 <https://github.com/pulp/pulp-smash/issues/897>`_
    """

    class Meta:
        publication_api = deb_verbatim_publication_api
        Publication = DebVerbatimPublication

    def _publication_extra_args(self):
        return {}
