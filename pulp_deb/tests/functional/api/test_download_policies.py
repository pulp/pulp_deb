"""Tests for Pulp download policies."""
import pytest

from pulp_deb.tests.functional.constants import DEB_FIXTURE_PACKAGE_COUNT, DEB_FIXTURE_SUMMARY


@pytest.mark.parametrize("policy", ["on_demand", "streamed"])
def test_download_policy(
    apt_package_api,
    deb_get_present_content_summary,
    deb_get_added_content_summary,
    deb_get_fixture_server_url,
    deb_get_repository_by_href,
    deb_publication_factory,
    deb_remote_factory,
    deb_repository_factory,
    deb_sync_repository,
    orphans_cleanup_api_client,
    policy,
):
    """Test whether lazy synced content can be accessed with different download policies."""
    orphans_cleanup_api_client.cleanup({"orphan_protection_time": 0})
    # Create repository and remote and verify latest `repository_version` is 0
    repo = deb_repository_factory()
    url = deb_get_fixture_server_url()
    remote = deb_remote_factory(url=url, policy=policy)
    assert repo.latest_version_href.endswith("/0/")

    # Sync and verify latest `repository_version` is 1
    deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)
    assert repo.latest_version_href.endswith("/1/")

    # Verify the correct amount of content units are available
    assert DEB_FIXTURE_SUMMARY == deb_get_present_content_summary(repo.to_dict())
    assert DEB_FIXTURE_SUMMARY == deb_get_added_content_summary(repo.to_dict())

    # Sync again and verify the same amount of content units are available
    latest_version_href = repo.latest_version_href
    deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)
    assert repo.latest_version_href == latest_version_href
    assert DEB_FIXTURE_SUMMARY == deb_get_present_content_summary(repo.to_dict())

    # Create a publication and verify the `repository_version` is not empty
    publication = deb_publication_factory(repo, simple=True)
    assert publication.repository_version is not None

    # Verify the correct amount of packages are available
    content = apt_package_api.list()
    assert content.count == DEB_FIXTURE_PACKAGE_COUNT


@pytest.mark.parametrize("policy", ["on_demand", "streamed"])
def test_lazy_sync_immediate_download_test(
    artifacts_api_client,
    deb_get_fixture_server_url,
    deb_get_remote_by_href,
    deb_get_repository_by_href,
    deb_patch_remote,
    deb_remote_factory,
    deb_repository_factory,
    deb_sync_repository,
    delete_orphans_pre,
    policy,
):
    """Test whether a immediate sync after a lazy one has all artifacts available."""
    # Cleanup artifacts
    NON_LAZY_ARTIFACT_COUNT = 14

    # Create repository and remote and sync them
    repo = deb_repository_factory()
    url = deb_get_fixture_server_url()
    remote = deb_remote_factory(url=url, policy=policy)
    deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    # Verify amount of artifacts are equal to NON_LAZY_ARTIFACT_COUNT
    artifacts = artifacts_api_client.list()
    assert artifacts.count == NON_LAZY_ARTIFACT_COUNT

    # Update remote policy to immediate and verify it is set
    deb_patch_remote(remote, {"policy": "immediate"})
    remote = deb_get_remote_by_href(remote.pulp_href)
    assert remote.policy == "immediate"

    # Sync with updated remote and verify the correct amount artifacts
    deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)
    artifacts = artifacts_api_client.list()
    assert artifacts.count == NON_LAZY_ARTIFACT_COUNT + DEB_FIXTURE_PACKAGE_COUNT
