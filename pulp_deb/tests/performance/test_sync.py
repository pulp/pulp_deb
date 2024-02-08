"""Tests that sync deb plugin repositories."""
import pytest

from pulp_deb.tests.performance.utils import write_csv_to_tmp
from pulp_deb.tests.functional.constants import (
    DEB_PERF_BOOKWORN,
    DEB_PERF_DEBIAN_URL,
    DEB_PERF_JAMMY,
    DEB_PERF_UBUNTU_URL,
)

perf_sync_test_params = [
    pytest.param(
        DEB_PERF_UBUNTU_URL,
        DEB_PERF_JAMMY,
        True,
        "pulp-deb-performance-sync-tests-ubuntu-jammy",
        id="performance-sync-ubuntu-jammy-with-resync",
    ),
    pytest.param(
        DEB_PERF_DEBIAN_URL,
        DEB_PERF_BOOKWORN,
        True,
        "pulp-deb-performance-sync-tests-debian-bookworm",
        id="performance-sync-debian-bookworm-with-resync",
    ),
]


@pytest.mark.parallel
@pytest.mark.parametrize("url,remote_args,resync,csv_filename", perf_sync_test_params)
def test_deb_sync(deb_init_and_sync, url, remote_args, resync, csv_filename):
    """Sync repositories with the deb plugin."""
    # Create repository & remote and sync
    repo, remote, task = deb_init_and_sync(url=url, remote_args=remote_args, return_task=True)

    task_time = (task.finished_at - task.started_at).total_seconds()
    wait_time = (task.started_at - task.pulp_created).total_seconds()
    print(f"\n->     Sync => Waiting time (s): {wait_time} | Service time (s): {task_time}")

    if resync:
        # Sync the repository again.
        latest_version_href = repo.latest_version_href
        repo, _, task = deb_init_and_sync(repository=repo, remote=remote, return_task=True)

        task_time_resync = (task.finished_at - task.started_at).total_seconds()
        wait_time_resync = (task.started_at - task.pulp_created).total_seconds()
        print(
            f"\n->  Resync => Wait time (s): {wait_time_resync} | Task time (s): {task_time_resync}"
        )

        # Check that nothing has changed since the last sync.
        assert latest_version_href == repo.latest_version_href

        write_csv_to_tmp(
            csv_filename,
            [
                "task_duration_initial",
                "waiting_time_initial",
                "task_duration_resync",
                "waiting_time_resync",
            ],
            [task_time, wait_time, task_time_resync, wait_time_resync],
        )
    else:
        write_csv_to_tmp(
            csv_filename, ["task_duration_initial", "waiting_time_initial"], [task_time, wait_time]
        )
