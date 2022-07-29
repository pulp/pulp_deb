"""Tests for Pulp download policies."""
import pytest

from pulp_smash.pulp3.bindings import delete_orphans
from pulp_smash.pulp3.utils import (
    get_added_content_summary,
    get_content_summary,
)
from pulp_deb.tests.functional.constants import DEB_FIXTURE_PACKAGE_COUNT, DEB_FIXTURE_SUMMARY


@pytest.mark.parallel
@pytest.mark.parametrize("policy", ["on_demand", "streamed"])
def test_download_policy(
    do_lazy_sync_access_test,
    do_publish,
    do_sync,
    policy,
):
    """Sync, publish a repository and verify lazy synced content can be
    accessed with different download policies.

    Assert that one accessing lazy synced content using the content endpoint,
    e.g. ``http://localhost/pulp/api/v3/content/deb/packages`` will not raise
    an HTTP exception.

    These tests target the following issues:

    * `Pulp #4126 <https://pulp.plan.io/issues/4126>`_
    * `Pulp #4463 <https://pulp.plan.io/issues/4463>`_
    """
    do_sync(policy)
    do_publish(policy)
    do_lazy_sync_access_test(policy)


@pytest.mark.parametrize("policy", ["on_demand", "streamed"])
def test_lazy_sync_immediate_download_test(do_lazy_sync_immediate_download_test, policy):
    """Perform a lazy sync, and change to immediate policy to force download.

    Perform an immediate sync to download artifacts for content units that
    are already created.

    This test targets the following issue:

    * `Pulp #4467 <https://pulp.plan.io/issues/4467>`_
    """
    do_lazy_sync_immediate_download_test(policy)


@pytest.fixture
def do_publish(
    deb_gen_publication,
    deb_gen_repository,
    deb_gen_remote,
    deb_get_repository_by_href,
    deb_sync_repository,
):
    """Fixture that will publish a repository synced with a given download policy."""

    def _do_publish(policy):
        repo = deb_gen_repository()
        remote = deb_gen_remote(policy=policy)
        deb_sync_repository(remote, repo)
        repo = deb_get_repository_by_href(repo.pulp_href)
        publication = deb_gen_publication(repo, simple=True)

        assert publication.repository_version is not None

    return _do_publish


@pytest.fixture
def do_lazy_sync_immediate_download_test(
    artifacts_api_client,
    deb_gen_repository,
    deb_gen_remote,
    deb_get_repository_by_href,
    deb_get_remote_by_href,
    deb_patch_remote,
    deb_sync_repository,
):
    """Fixture that performs a lazy sync and change policy to immediate forcing a download."""

    def _do_lazy_sync_immediate_download_test(policy):
        NON_LAZY_ARTIFACT_COUNT = 17
        delete_orphans()
        repo = deb_gen_repository()
        remote = deb_gen_remote(policy=policy)
        deb_sync_repository(remote, repo)
        repo = deb_get_repository_by_href(repo.pulp_href)
        artifacts = artifacts_api_client.list()

        assert artifacts.count == NON_LAZY_ARTIFACT_COUNT

        deb_patch_remote(remote, {"policy": "immediate"})
        remote = deb_get_remote_by_href(remote.pulp_href)

        assert remote.policy == "immediate"

        deb_sync_repository(remote, repo)
        repo = deb_get_repository_by_href(repo.pulp_href)
        artifacts = artifacts_api_client.list()

        assert artifacts.count == NON_LAZY_ARTIFACT_COUNT + DEB_FIXTURE_PACKAGE_COUNT

    return _do_lazy_sync_immediate_download_test


@pytest.fixture
def do_lazy_sync_access_test(
    apt_package_api,
    deb_gen_remote,
    deb_gen_repository,
    deb_get_repository_by_href,
    deb_sync_repository,
):
    """Fixture that accesses lazy synced content on using content endpoint."""

    def _do_lazy_sync_access_test(policy):
        repo = deb_gen_repository()
        remote = deb_gen_remote(policy=policy)

        assert repo.latest_version_href.endswith("/0/")

        deb_sync_repository(remote, repo)
        repo = deb_get_repository_by_href(repo.pulp_href)

        assert repo.latest_version_href.endswith("/1/")

        content = apt_package_api.list()

        assert content.count == DEB_FIXTURE_PACKAGE_COUNT

    return _do_lazy_sync_access_test


@pytest.fixture
def do_sync(
    deb_gen_remote,
    deb_gen_repository,
    deb_get_repository_by_href,
    deb_sync_repository,
):
    """Fixture that will do the following:

    1. Create a repository, and a remote.
    2. Assert that repository version is None.
    3. Sync the remote.
    4. Assert that repository version is not None.
    5. Assert that the correct number of possible units to be downloaded
       were shown.
    6. Sync the remote one ore time in order to create another repository
       version.
    7. Assert that repository version is the same as the previous one.
    8. Assert that the same number of units are shown, and after the
       second sync no extra units should be shown, since the same remote
       was synced again.
    """

    def _do_sync(policy):
        repo = deb_gen_repository()
        remote = deb_gen_remote(policy=policy)

        assert repo.latest_version_href.endswith("/0/")

        deb_sync_repository(remote, repo)
        repo = deb_get_repository_by_href(repo.pulp_href)

        assert repo.latest_version_href is not None
        assert DEB_FIXTURE_SUMMARY == get_content_summary(repo.to_dict())
        assert DEB_FIXTURE_SUMMARY == get_added_content_summary(repo.to_dict())

        latest_version_href = repo.latest_version_href
        deb_sync_repository(remote, repo)
        repo = deb_get_repository_by_href(repo.pulp_href)

        assert repo.latest_version_href == latest_version_href
        assert DEB_FIXTURE_SUMMARY == get_content_summary(repo.to_dict())

    return _do_sync
