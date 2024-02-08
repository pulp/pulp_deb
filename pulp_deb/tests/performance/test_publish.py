"""Tests that publish deb plugin repositories."""
import pytest

from pulp_deb.tests.performance.utils import write_csv_to_tmp
from pulp_deb.tests.functional.constants import (
    DEB_PACKAGE_NAME,
    DEB_PERF_BOOKWORN,
    DEB_PERF_DEBIAN_URL,
    DEB_PERF_JAMMY,
    DEB_PERF_UBUNTU_URL,
)

perf_publish_test_params = [
    pytest.param(
        DEB_PERF_UBUNTU_URL,
        DEB_PERF_JAMMY,
        "pulp-deb-performance-publish-tests-ubuntu-jammy",
        id="performance-publish-ubuntu-jammy",
    ),
    pytest.param(
        DEB_PERF_DEBIAN_URL,
        DEB_PERF_BOOKWORN,
        "pulp-deb-performance-publish-tests-debian-bookworm",
        id="performance-publish-debian-bookworm",
    ),
]


@pytest.mark.parametrize("url,remote_args,csv_filename", perf_publish_test_params)
def test_deb_publish(
    apt_publication_api,
    apt_repository_versions_api,
    deb_init_and_sync,
    monitor_task,
    url,
    remote_args,
    csv_filename,
    delete_orphans_pre,
):
    """Publish repositories with the deb plugin."""
    repo, _, task = deb_init_and_sync(url=url, remote_args=remote_args, return_task=True)
    task_time = (task.finished_at - task.started_at).total_seconds()
    wait_time = (task.started_at - task.pulp_created).total_seconds()
    print(f"\n->     Sync => Waiting time (s): {wait_time} | Service time (s): {task_time}")

    # Check that we have the correct content counts
    repo_ver = apt_repository_versions_api.read(repo.latest_version_href)
    assert DEB_PACKAGE_NAME in repo_ver.content_summary.present.keys()
    assert DEB_PACKAGE_NAME in repo_ver.content_summary.added.keys()

    # Publishing
    response = apt_publication_api.create({"repository": repo.pulp_href})
    task = monitor_task(response.task)
    task_time_publish = (task.finished_at - task.started_at).total_seconds()
    wait_time_publish = (task.started_at - task.pulp_created).total_seconds()
    print(
        f"\n->  Publish => Wait time (s): {wait_time_publish} | Task time (s): {task_time_publish}"
    )

    write_csv_to_tmp(
        csv_filename,
        [
            "task_duration_sync",
            "waiting_time_sync",
            "task_duration_publish",
            "waiting_time_publish",
        ],
        [task_time, wait_time, task_time_publish, wait_time_publish],
    )
