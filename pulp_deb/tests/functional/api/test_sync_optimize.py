"""Tests that sync deb repositories in optimized mode."""
import pytest

from pulp_deb.tests.functional.constants import (
    DEB_FIXTURE_ARCH,
    DEB_FIXTURE_ARCH_UPDATE,
    DEB_FIXTURE_COMPONENT,
    DEB_FIXTURE_COMPONENT_UPDATE,
    DEB_FIXTURE_SINGLE_DIST,
    DEB_FIXTURE_URL,
    DEB_FIXTURE_DISTRIBUTIONS,
    DEB_FIXTURE_URL_UPDATE,
    DEB_REPORT_CODE_SKIP_PACKAGE,
    DEB_REPORT_CODE_SKIP_RELEASE,
)


@pytest.mark.parallel
def test_sync_optimize_skip_unchanged_release_file(
    deb_gen_remote,
    deb_gen_repository,
    deb_get_repository_by_href,
    is_sync_skipped,
    deb_sync_repository,
):
    """Test whether synchronization is skipped when the ReleaseFile of a remote
    has not been changed.

    1. Create a repository and a remote.
    2. Assert that the latest RepositoryVersion is 0.
    3. Sync the repository.
    4. Assert that the latest RepositoryVersion is 1.
    5. Assert that the sync was not skipped.
    6. Sync the repository again.
    7. Assert that the latest RepositoryVersion is still 1.
    8. Assert that this time the sync was skipped.
    """
    repo = deb_gen_repository()
    remote = deb_gen_remote(url=DEB_FIXTURE_URL, distributions=DEB_FIXTURE_DISTRIBUTIONS)

    assert repo.latest_version_href.endswith("/0/")

    task = deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    assert repo.latest_version_href.endswith("/1/")
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_RELEASE)

    task_skip = deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    assert repo.latest_version_href.endswith("/1/")
    assert is_sync_skipped(task_skip, DEB_REPORT_CODE_SKIP_RELEASE)


@pytest.mark.parallel
@pytest.mark.parametrize(
    "remote_params, remote_diff_params",
    [
        (
            [DEB_FIXTURE_URL, DEB_FIXTURE_SINGLE_DIST, DEB_FIXTURE_COMPONENT, None],
            [DEB_FIXTURE_URL, DEB_FIXTURE_SINGLE_DIST, DEB_FIXTURE_COMPONENT_UPDATE, None],
        ),
        (
            [DEB_FIXTURE_URL, DEB_FIXTURE_SINGLE_DIST, None, DEB_FIXTURE_ARCH],
            [DEB_FIXTURE_URL, DEB_FIXTURE_SINGLE_DIST, None, DEB_FIXTURE_ARCH_UPDATE],
        ),
        (
            [DEB_FIXTURE_URL, DEB_FIXTURE_SINGLE_DIST, DEB_FIXTURE_COMPONENT, None],
            [DEB_FIXTURE_URL_UPDATE, DEB_FIXTURE_SINGLE_DIST, DEB_FIXTURE_COMPONENT_UPDATE, None],
        ),
    ],
)
def test_sync_optimize_no_skip_release_file(
    deb_gen_remote,
    deb_gen_repository,
    deb_get_repository_by_href,
    is_sync_skipped,
    remote_params,
    remote_diff_params,
    deb_sync_repository,
):
    """Test whether repository synchronizations have not been skipped for certain conditions.
    The following cases are tested:

    * `Sync a repository with same ReleaseFile but updated Components.`_
    * `Sync a repository with same ReleaseFile but updated Architectures.`_
    * `Sync a repository with updated ReleaseFile and updated Components.`_

    1. Create a repository and a remote.
    2. Assert that the latest RepositoryVersion is 0.
    3. Synchronize the repository.
    4. Assert that the latest RepositoryVersion is 1.
    5. Assert that the synchronization was not skipped.
    6. Create a new remote with different conditions.
    7. Synchronize the repository with the new remote.
    8. Asser that the latest RepositoryVersion is 2.
    9. Assert that the synchronization was not skipped.
    """
    repo = deb_gen_repository()
    remote = deb_gen_remote(
        url=remote_params[0],
        distributions=remote_params[1],
        components=remote_params[2],
        architectures=remote_params[3],
    )

    assert repo.latest_version_href.endswith("/0/")

    task = deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    assert repo.latest_version_href.endswith("/1/")
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_RELEASE)
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_PACKAGE)

    remote_diff = deb_gen_remote(
        url=remote_diff_params[0],
        distributions=remote_diff_params[1],
        components=remote_diff_params[2],
        architectures=remote_diff_params[3],
    )
    task_diff = deb_sync_repository(remote_diff, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    assert repo.latest_version_href.endswith("/2/")
    assert not is_sync_skipped(task_diff, DEB_REPORT_CODE_SKIP_RELEASE)
    assert not is_sync_skipped(task_diff, DEB_REPORT_CODE_SKIP_PACKAGE)


@pytest.mark.parallel
def test_sync_optimize_skip_unchanged_package_index(
    deb_gen_remote,
    deb_gen_repository,
    deb_get_repository_by_href,
    is_sync_skipped,
    deb_sync_repository,
):
    """Test whether a repository synchronization of PackageIndex is skipped when
    the package has not been changed.

    1. Create a repository and a remote.
    2. Assert that the latest RepositoryVersion is 0.
    3. Sync the repository.
    4. Assert that the latest RepositoryVersion is 1.
    5. Assert that the sync was not skipped.
    6. Create a new remote with at least one updated package and one that remains the same.
    7. Sync the repository with the new remote.
    8. Assert that the latest RepositoryVersion is 2.
    9. Asssert that at least one PackageIndex was skipped.
    """
    repo = deb_gen_repository()
    remote = deb_gen_remote(url=DEB_FIXTURE_URL, distributions=DEB_FIXTURE_SINGLE_DIST)

    assert repo.latest_version_href.endswith("/0/")

    task = deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    assert repo.latest_version_href.endswith("/1/")
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_RELEASE)
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_PACKAGE)

    remote_diff = deb_gen_remote(url=DEB_FIXTURE_URL_UPDATE, distributions=DEB_FIXTURE_SINGLE_DIST)
    task_diff = deb_sync_repository(remote_diff, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    assert repo.latest_version_href.endswith("/2/")
    assert not is_sync_skipped(task_diff, DEB_REPORT_CODE_SKIP_RELEASE)
    assert is_sync_skipped(task_diff, DEB_REPORT_CODE_SKIP_PACKAGE)


@pytest.fixture
def is_sync_skipped():
    """Checks if a given task has skipped the sync based of a given code."""

    def _is_sync_skipped(task, code):
        for report in task.progress_reports:
            if report.code == code:
                return True
        return False

    return _is_sync_skipped
