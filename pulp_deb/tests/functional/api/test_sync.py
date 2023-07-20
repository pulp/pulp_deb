"""Tests that sync deb repositories in optimized mode."""
import pytest

from pulpcore.tests.functional.utils import PulpTaskError
from pulp_deb.tests.functional.constants import (
    DEB_FIXTURE_ARCH,
    DEB_FIXTURE_ARCH_UPDATE,
    DEB_FIXTURE_COMPONENT,
    DEB_FIXTURE_COMPONENT_UPDATE,
    DEB_FIXTURE_INVALID_REPOSITORY_NAME,
    DEB_FIXTURE_SINGLE_DIST,
    DEB_FIXTURE_STANDARD_REPOSITORY_NAME,
    DEB_FIXTURE_SUMMARY,
    DEB_FIXTURE_UPDATE_REPOSITORY_NAME,
    DEB_FULL_FIXTURE_SUMMARY,
    DEB_REPORT_CODE_SKIP_PACKAGE,
    DEB_REPORT_CODE_SKIP_RELEASE,
    DEB_SIGNING_KEY,
)


@pytest.mark.parallel
@pytest.mark.parametrize(
    "remote_params, fixture_summary",
    [
        ({"gpgkey": DEB_SIGNING_KEY}, DEB_FIXTURE_SUMMARY),
        ({"gpgkey": DEB_SIGNING_KEY, "sync_udebs": True}, DEB_FULL_FIXTURE_SUMMARY),
    ],
)
def test_sync(
    deb_get_added_content_summary,
    deb_get_present_content_summary,
    deb_get_fixture_server_url,
    deb_remote_factory,
    deb_repository_factory,
    deb_get_repository_by_href,
    deb_sync_repository,
    fixture_summary,
    remote_params,
):
    """Test whether synchronizations with and without udebs works as expected."""
    # Create a repository and a remote and verify latest `repository_version` is 0
    repo = deb_repository_factory()
    url = deb_get_fixture_server_url()
    remote = deb_remote_factory(url=url, **remote_params)
    assert repo.latest_version_href.endswith("/0/")

    # Sync the repository
    task = deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    # Verify latest `repository_version` is 1 and sync was not skipped
    assert repo.latest_version_href.endswith("/1/")
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_RELEASE)

    # Verify that the repo content and added content matches the summary
    assert deb_get_present_content_summary(repo.to_dict()) == fixture_summary
    assert deb_get_added_content_summary(repo.to_dict()) == fixture_summary

    # Sync the repository again
    task_skip = deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    # Verify that the latest `repository_version` is still 1 and sync was skipped
    assert repo.latest_version_href.endswith("/1/")
    assert is_sync_skipped(task_skip, DEB_REPORT_CODE_SKIP_RELEASE)

    # Verify that the repo content still matches the summary
    assert deb_get_present_content_summary(repo.to_dict()) == fixture_summary


@pytest.mark.skip("Skip - ignore_missing_package_indices sync parameter does currently not work")
@pytest.mark.parallel
@pytest.mark.parametrize(
    "remote_params, expected",
    [
        (
            {
                "architectures": "ppc64",
                "ignore_missing_package_indices": False,
            },
            ["No suitable package index files", "ppc64"],
        ),
        (
            {
                "architectures": "armeb",
                "ignore_missing_package_indices": False,
            },
            ["No suitable package index files", "armeb"],
        ),
    ],
)
def test_sync_missing_package_indices(
    expected,
    deb_get_fixture_server_url,
    deb_remote_factory,
    deb_repository_factory,
    deb_sync_repository,
    remote_params,
):
    """Test whether tests fail as expected when package indices are missing.

    The following cases are tested:

    * `Sync a repository with missing files associated with the content unit.`_
    * `Sync a repository with missing package indices and missing Release file.`_
    """
    # Create repository and remote
    repo = deb_repository_factory()
    url = deb_get_fixture_server_url(DEB_FIXTURE_INVALID_REPOSITORY_NAME)
    remote = deb_remote_factory(url=url, **remote_params)

    # Verify a PulpTaskError is raised and the error message is as expected
    with pytest.raises(PulpTaskError) as exc:
        deb_sync_repository(remote, repo)
    for exp in expected:
        assert exp in str(exc.value)


@pytest.mark.parallel
@pytest.mark.parametrize(
    "repo_name, remote_params, expected",
    [
        ("http://i-am-an-invalid-url.com/invalid/", {}, ["Cannot connect"]),
        (
            DEB_FIXTURE_STANDARD_REPOSITORY_NAME,
            {"distributions": "no_dist"},
            ["Could not find a Release file at"],
        ),
        (
            DEB_FIXTURE_INVALID_REPOSITORY_NAME,
            {
                "distributions": "nosuite",
                "gpgkey": DEB_SIGNING_KEY,
            },
            ["Unable to verify any Release files from", "using the GPG key provided."],
        ),
    ],
)
def test_sync_invalid_cases(
    expected,
    deb_get_fixture_server_url,
    deb_remote_factory,
    deb_repository_factory,
    deb_sync_repository,
    remote_params,
    repo_name,
):
    """Test whether various invalid sync cases fail as expected.

    The following cases are tested:

    * `Sync a repository with an invalid remote URL parameter.`_
    * `Sync a repository with an invalid remote Distribution.`_
    * `Sync a repository with an invalid signature.`_
    """
    # Create repository and remote
    repo = deb_repository_factory()
    url = repo_name if repo_name.startswith("http://") else deb_get_fixture_server_url(repo_name)
    remote = deb_remote_factory(url=url, **remote_params)

    # Verify a PulpTaskError is raised and the error message is as expected
    with pytest.raises(PulpTaskError) as exc:
        deb_sync_repository(remote, repo)
    for exp in expected:
        assert exp in str(exc.value)


@pytest.mark.parallel
@pytest.mark.parametrize(
    "repo_name, remote_params, repo_diff_name, remote_diff_params",
    [
        (
            DEB_FIXTURE_STANDARD_REPOSITORY_NAME,
            {
                "distributions": DEB_FIXTURE_SINGLE_DIST,
                "components": DEB_FIXTURE_COMPONENT,
                "architectures": None,
            },
            DEB_FIXTURE_STANDARD_REPOSITORY_NAME,
            {
                "distributions": DEB_FIXTURE_SINGLE_DIST,
                "components": DEB_FIXTURE_COMPONENT_UPDATE,
                "architectures": None,
            },
        ),
        (
            DEB_FIXTURE_STANDARD_REPOSITORY_NAME,
            {
                "distributions": DEB_FIXTURE_SINGLE_DIST,
                "components": None,
                "architectures": DEB_FIXTURE_ARCH,
            },
            DEB_FIXTURE_STANDARD_REPOSITORY_NAME,
            {
                "distributions": DEB_FIXTURE_SINGLE_DIST,
                "components": None,
                "architectures": DEB_FIXTURE_ARCH_UPDATE,
            },
        ),
        (
            DEB_FIXTURE_STANDARD_REPOSITORY_NAME,
            {
                "distributions": DEB_FIXTURE_SINGLE_DIST,
                "components": DEB_FIXTURE_COMPONENT,
                "architectures": None,
            },
            DEB_FIXTURE_UPDATE_REPOSITORY_NAME,
            {
                "distributions": DEB_FIXTURE_SINGLE_DIST,
                "components": DEB_FIXTURE_COMPONENT_UPDATE,
                "architectures": None,
            },
        ),
    ],
)
def test_sync_optimize_no_skip_release_file(
    deb_get_fixture_server_url,
    deb_remote_factory,
    deb_repository_factory,
    deb_get_repository_by_href,
    remote_params,
    remote_diff_params,
    repo_name,
    repo_diff_name,
    deb_sync_repository,
):
    """Test whether synchronizations have not been skipped for certain conditions.

    The following cases are tested:

    * `Sync a repository with same Release file but updated Components.`_
    * `Sync a repository with same Release file but updated Architectures.`_
    * `Sync a repository with updated Release file and updated Components.`_
    """
    # Create a repository and a remote and verify latest `repository_version` is 0
    repo = deb_repository_factory()
    url = deb_get_fixture_server_url(repo_name)
    remote = deb_remote_factory(url=url, **remote_params)
    assert repo.latest_version_href.endswith("/0/")

    # Sync the repository
    task = deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    # Verify latest `repository_version` is 1 and sync was not skipped
    assert repo.latest_version_href.endswith("/1/")
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_RELEASE)
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_PACKAGE)

    # Create a new remote with different parameters and sync with repository
    url = deb_get_fixture_server_url(repo_diff_name)
    remote_diff = deb_remote_factory(url=url, **remote_diff_params)
    task_diff = deb_sync_repository(remote_diff, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    # Verify that latest `repository_version` is 2 and sync was not skipped
    assert repo.latest_version_href.endswith("/2/")
    assert not is_sync_skipped(task_diff, DEB_REPORT_CODE_SKIP_RELEASE)
    assert not is_sync_skipped(task_diff, DEB_REPORT_CODE_SKIP_PACKAGE)


@pytest.mark.parallel
def test_sync_optimize_skip_unchanged_package_index(
    deb_get_fixture_server_url,
    deb_remote_factory,
    deb_repository_factory,
    deb_get_repository_by_href,
    deb_sync_repository,
    apt_package_api,
    apt_release_api,
    apt_release_component_api,
):
    """Test whether package synchronization is skipped when a package has not been changed."""
    # Create a repository and a remote and verify latest `repository_version` is 0
    repo = deb_repository_factory()
    url = deb_get_fixture_server_url()
    remote = deb_remote_factory(url=url, distributions=DEB_FIXTURE_SINGLE_DIST)
    assert repo.latest_version_href.endswith("/0/")

    # Sync the repository
    task = deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    # Verify latest `repository_version` is 1 and sync was not skipped
    repo_v1_href = repo.latest_version_href
    assert repo_v1_href.endswith("/1/")
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_RELEASE)
    assert not is_sync_skipped(task, DEB_REPORT_CODE_SKIP_PACKAGE)

    # Create new remote with both updated and unchanged packages and sync with repository
    url = deb_get_fixture_server_url(DEB_FIXTURE_UPDATE_REPOSITORY_NAME)
    remote_diff = deb_remote_factory(url=url, distributions=DEB_FIXTURE_SINGLE_DIST)
    task_diff = deb_sync_repository(remote_diff, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    # Verify latest `repository_version` is 2, release was not skipped and package was skipped
    repo_v2_href = repo.latest_version_href
    assert repo_v2_href.endswith("/2/")
    assert not is_sync_skipped(task_diff, DEB_REPORT_CODE_SKIP_RELEASE)
    assert is_sync_skipped(task_diff, DEB_REPORT_CODE_SKIP_PACKAGE)

    # === Test whether the content filters are working. ===
    # This doesn't _technically_ have anything to do with testing syncing, but it's a
    # convenient place to do it since we've already created a repo with content and
    # multiple versions. Repo version 1 synced from debian/ragnarok and version 2 synced
    # from debian-update/ragnarok.
    releases = apt_release_api.list(repository_version=repo_v2_href)
    assert releases.count == 1
    release_href = releases.results[0].pulp_href
    release_components = apt_release_component_api.list(repository_version=repo_v2_href)
    assert release_components.count == 2
    rc = [x for x in release_components.results if x.component == "asgard"]
    rc_href = rc[0].pulp_href

    # some simple "happy path" tests to ensure the filters are working properly
    assert apt_package_api.list(release=f"{release_href},{repo_v1_href}").count == 4
    assert apt_package_api.list(release=f"{release_href},{repo_v2_href}").count == 6
    assert apt_package_api.list(release=f"{release_href},{repo.pulp_href}").count == 6

    assert apt_package_api.list(release_component=f"{rc_href},{repo_v1_href}").count == 3
    assert apt_package_api.list(release_component=f"{rc_href},{repo_v2_href}").count == 5
    assert apt_package_api.list(release_component=f"{rc_href},{repo.pulp_href}").count == 5

    packages = apt_package_api.list(release_component=f"{rc_href},{repo.pulp_href}")
    # The package that was added to asgard in debian-update.
    package_href = [x for x in packages.results if x.package == "heimdallr"][0].pulp_href

    assert apt_release_api.list(package=f"{package_href},{repo_v1_href}").count == 0
    assert apt_release_api.list(package=f"{package_href},{repo_v2_href}").count == 1
    assert apt_release_api.list(package=f"{package_href},{repo.pulp_href}").count == 1

    assert apt_release_component_api.list(package=f"{package_href},{repo_v1_href}").count == 0
    assert apt_release_component_api.list(package=f"{package_href},{repo_v2_href}").count == 1
    assert apt_release_component_api.list(package=f"{package_href},{repo.pulp_href}").count == 1


def test_sync_orphan_cleanup_fail(
    deb_get_fixture_server_url,
    deb_remote_factory,
    deb_repository_factory,
    deb_get_repository_by_href,
    deb_sync_repository,
    orphans_cleanup_api_client,
    monitor_task,
    delete_orphans_pre,
):
    """Test whether an orphan cleanup is possible after syncing where only some PackageIndices got
    changed and older repository versions are not kept.

    See: https://github.com/pulp/pulp_deb/issues/690
    """
    # Create a repository and only retain the latest repository version.
    repo = deb_repository_factory(retain_repo_versions=1)

    # Create a remote and sync with repo. Verify the latest `repository_version` is 1.
    url = deb_get_fixture_server_url()
    remote = deb_remote_factory(url=url, distributions=DEB_FIXTURE_SINGLE_DIST)
    deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)
    assert repo.latest_version_href.endswith("/1/")

    # Create a new remote with updated packages and sync again. Verify `repository_version` is 2.
    url = deb_get_fixture_server_url(DEB_FIXTURE_UPDATE_REPOSITORY_NAME)
    remote_diff = deb_remote_factory(url=url, distributions=DEB_FIXTURE_SINGLE_DIST)
    deb_sync_repository(remote_diff, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)
    assert repo.latest_version_href.endswith("/2/")

    # Trigger orphan cleanup without protection time and verify the task completed
    # and Content and Artifacts have been removed.
    task = monitor_task(orphans_cleanup_api_client.cleanup({"orphan_protection_time": 0}).task)
    assert task.state == "completed"
    for report in task.progress_reports:
        if "Content" in report.message:
            assert report.done == 2


def is_sync_skipped(task, code):
    """Checks if a given task has skipped the sync based of a given code."""
    for report in task.progress_reports:
        if report.code == code:
            return True
    return False
