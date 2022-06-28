"""Tests that sync deb repositories in optimized mode."""
from pulp_smash.pulp3.bindings import monitor_task
from pulp_smash.pulp3.utils import gen_repo
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
from pulp_deb.tests.functional.utils import gen_deb_remote

from pulpcore.client.pulp_deb import AptRepositorySyncURL


def test_sync_optimize_skip_unchanged_release_file(
    gen_remote,
    gen_repository,
    get_repository_by_href,
    is_latest_repo_version,
    is_sync_skipped,
    synchronize_and_get_task,
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
    repo = gen_repository()
    remote = gen_remote()
    assert is_latest_repo_version(repo, 0)
    task = synchronize_and_get_task(remote, repo)
    repo = get_repository_by_href(repo.pulp_href)
    assert is_latest_repo_version(repo, 1)
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_RELEASE)
    task_skip = synchronize_and_get_task(remote, repo)
    repo = get_repository_by_href(repo.pulp_href)
    assert is_latest_repo_version(repo, 1)
    assert is_sync_skipped(task_skip, DEB_REPORT_CODE_SKIP_RELEASE)


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
    gen_remote,
    gen_repository,
    get_repository_by_href,
    is_latest_repo_version,
    is_sync_skipped,
    remote_params,
    remote_diff_params,
    synchronize_and_get_task,
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
    repo = gen_repository()
    remote = gen_remote(
        url=remote_params[0],
        distributions=remote_params[1],
        components=remote_params[2],
        architectures=remote_params[3],
    )
    assert is_latest_repo_version(repo, 0)
    task = synchronize_and_get_task(remote, repo)
    repo = get_repository_by_href(repo.pulp_href)
    assert is_latest_repo_version(repo, 1)
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_RELEASE)
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_PACKAGE)
    remote_diff = gen_remote(
        url=remote_diff_params[0],
        distributions=remote_diff_params[1],
        components=remote_diff_params[2],
        architectures=remote_diff_params[3],
    )
    task_diff = synchronize_and_get_task(remote_diff, repo)
    repo = get_repository_by_href(repo.pulp_href)
    assert is_latest_repo_version(repo, 2)
    assert not is_sync_skipped(task_diff, DEB_REPORT_CODE_SKIP_RELEASE)
    assert not is_sync_skipped(task_diff, DEB_REPORT_CODE_SKIP_PACKAGE)


def test_sync_optimize_skip_unchanged_package_index(
    gen_remote,
    gen_repository,
    get_repository_by_href,
    is_latest_repo_version,
    is_sync_skipped,
    synchronize_and_get_task,
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
    repo = gen_repository()
    remote = gen_remote(url=DEB_FIXTURE_URL, distributions=DEB_FIXTURE_SINGLE_DIST)
    assert is_latest_repo_version(repo, 0)
    task = synchronize_and_get_task(remote, repo)
    repo = get_repository_by_href(repo.pulp_href)
    assert is_latest_repo_version(repo, 1)
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_RELEASE)
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_PACKAGE)
    remote_diff = gen_remote(url=DEB_FIXTURE_URL_UPDATE, distributions=DEB_FIXTURE_SINGLE_DIST)
    task_diff = synchronize_and_get_task(remote_diff, repo)
    repo = get_repository_by_href(repo.pulp_href)
    assert is_latest_repo_version(repo, 2)
    assert not is_sync_skipped(task_diff, DEB_REPORT_CODE_SKIP_RELEASE)
    assert is_sync_skipped(task_diff, DEB_REPORT_CODE_SKIP_PACKAGE)


@pytest.fixture
def is_latest_repo_version():
    """Checks if a given version number is the latest RepositoryVersion of
    a given repository.
    """

    def _is_latest_repo_version(repo, version):
        return repo.latest_version_href == f"{repo.pulp_href}versions/{version}/"

    return _is_latest_repo_version


@pytest.fixture
def is_sync_skipped():
    """Checks if a given task has skipped the sync based of a given code."""

    def _is_sync_skipped(task, code):
        for report in task.progress_reports:
            if report.code == code:
                return True
        return False

    return _is_sync_skipped


@pytest.fixture
def get_repository_by_href(apt_repository_api):
    """Returns the repository of a given pulp_href."""

    def _get_repository_by_href(href):
        return apt_repository_api.read(href)

    return _get_repository_by_href


@pytest.fixture
def synchronize_and_get_task(apt_repository_api):
    """Synchronizes a given repository with a given remote and
    returns the monitored task.
    """

    def _synchronize_and_get_task(remote, repo):
        repository_sync_data = AptRepositorySyncURL(remote=remote.pulp_href)
        sync_response = apt_repository_api.sync(repo.pulp_href, repository_sync_data)
        return monitor_task(sync_response.task)

    return _synchronize_and_get_task


@pytest.fixture
def gen_repository(apt_repository_api, gen_object_with_cleanup):
    """Generates a semi-random repository with cleanup."""

    def _gen_repository():
        return gen_object_with_cleanup(apt_repository_api, gen_repo())

    return _gen_repository


@pytest.fixture
def gen_remote(apt_remote_api, gen_object_with_cleanup):
    """Generates a remote with cleanup. Also allows for parameters to be set manually."""

    def _gen_remote(url=DEB_FIXTURE_URL, distributions=DEB_FIXTURE_DISTRIBUTIONS, **kwargs):
        return gen_object_with_cleanup(
            apt_remote_api, gen_deb_remote(url=url, distributions=distributions, **kwargs)
        )

    return _gen_remote
