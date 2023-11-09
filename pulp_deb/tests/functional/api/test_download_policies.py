"""Tests for Pulp download policies."""
import pytest

from pulp_deb.tests.functional.constants import DEB_FIXTURE_PACKAGE_COUNT, DEB_FIXTURE_SUMMARY
from pulp_deb.tests.functional.utils import get_counts_from_content_summary


@pytest.mark.parametrize("remote_args", [{"policy": "on_demand"}, {"policy": "streamed"}])
def test_download_policy(
    apt_package_api,
    deb_init_and_sync,
    deb_get_content_summary,
    deb_publication_factory,
    remote_args,
    delete_orphans_pre,
):
    """Test whether lazy synced content can be accessed with different download policies."""
    repo, remote = deb_init_and_sync(remote_args=remote_args)
    assert repo.latest_version_href.endswith("/1/")

    # Verify the correct amount of content units are available
    content_summary = deb_get_content_summary(repo)
    assert DEB_FIXTURE_SUMMARY == get_counts_from_content_summary(content_summary.present)
    assert DEB_FIXTURE_SUMMARY == get_counts_from_content_summary(content_summary.added)

    # Sync again and verify the same amount of content units are available
    latest_version_href = repo.latest_version_href
    repo, _ = deb_init_and_sync(repository=repo, remote=remote)
    content_summary = deb_get_content_summary(repo)
    assert repo.latest_version_href == latest_version_href
    assert DEB_FIXTURE_SUMMARY == get_counts_from_content_summary(content_summary.present)

    # Create a publication and verify the `repository_version` is not empty
    publication = deb_publication_factory(repo, simple=True)
    assert publication.repository_version is not None

    # Verify the correct amount of packages are available
    content = apt_package_api.list()
    assert content.count == DEB_FIXTURE_PACKAGE_COUNT


@pytest.mark.parametrize("remote_args", [{"policy": "on_demand"}, {"policy": "streamed"}])
def test_lazy_sync_immediate_download_test(
    artifacts_api_client,
    deb_init_and_sync,
    deb_get_remote_by_href,
    deb_patch_remote,
    remote_args,
    delete_orphans_pre,
):
    """Test whether a immediate sync after a lazy one has all artifacts available."""
    # Cleanup artifacts
    NON_LAZY_ARTIFACT_COUNT = 17

    # Create repository and remote and sync them
    repo, remote = deb_init_and_sync(remote_args=remote_args)

    # Verify amount of artifacts are equal to NON_LAZY_ARTIFACT_COUNT
    artifacts = artifacts_api_client.list()
    assert artifacts.count == NON_LAZY_ARTIFACT_COUNT

    # Update remote policy to immediate and verify it is set
    deb_patch_remote(remote, {"policy": "immediate"})
    remote = deb_get_remote_by_href(remote.pulp_href)
    assert remote.policy == "immediate"

    # Sync with updated remote and verify the correct amount artifacts
    repo, _ = deb_init_and_sync(repository=repo, remote=remote)
    artifacts = artifacts_api_client.list()
    assert artifacts.count == NON_LAZY_ARTIFACT_COUNT + DEB_FIXTURE_PACKAGE_COUNT
