import pytest

from pulp_deb.tests.functional.constants import (
    DEB_ADVANCED_COPY_FIXTURE_SUMMARY,
    DEB_FULL_ADVANCED_COPY_FIXTURE_SUMMARY,
)
from pulp_deb.tests.functional.utils import get_counts_from_content_summary


@pytest.mark.parallel
def test_copy(
    deb_init_and_sync,
    deb_repository_factory,
    apt_package_api,
    deb_copy_content,
    deb_get_repository_by_href,
    deb_get_content_summary,
):
    """Test whether the copy operation can successfully copy a single package."""
    source_repo, _ = deb_init_and_sync()
    target_repo = deb_repository_factory()

    source_version_href = source_repo.latest_version_href
    package = apt_package_api.list(
        package="frigg",
        repository_version=source_version_href,
    ).results[0]

    deb_copy_content(
        source_repo_version=source_repo.latest_version_href,
        dest_repo=target_repo.pulp_href,
        content=[package.pulp_href],
    )

    target_repo = deb_get_repository_by_href(target_repo.pulp_href)
    added_summary = deb_get_content_summary(target_repo).added
    assert DEB_ADVANCED_COPY_FIXTURE_SUMMARY == get_counts_from_content_summary(added_summary)


@pytest.mark.parallel
def test_copy_all(
    deb_init_and_sync,
    deb_repository_factory,
    deb_copy_content,
    deb_get_repository_by_href,
    deb_get_content_summary,
):
    """Test whether the copy operation can successfully copy all packages of a repository."""
    source_repo, _ = deb_init_and_sync()
    target_repo = deb_repository_factory()
    deb_copy_content(
        source_repo_version=source_repo.latest_version_href,
        dest_repo=target_repo.pulp_href,
    )

    target_repo = deb_get_repository_by_href(target_repo.pulp_href)
    added_summary = deb_get_content_summary(target_repo).added
    assert DEB_FULL_ADVANCED_COPY_FIXTURE_SUMMARY == get_counts_from_content_summary(added_summary)


@pytest.mark.parallel
def test_copy_empty_content(
    deb_init_and_sync,
    deb_repository_factory,
    deb_copy_content,
    deb_get_repository_by_href,
):
    """Test whether the copy operation does not copy if the content is empty."""
    source_repo, _ = deb_init_and_sync()
    target_repo = deb_repository_factory()
    deb_copy_content(
        source_repo_version=source_repo.latest_version_href,
        dest_repo=target_repo.pulp_href,
        content=[],
    )

    target_repo = deb_get_repository_by_href(target_repo.pulp_href)
    assert target_repo.latest_version_href.endswith("/versions/0/")
