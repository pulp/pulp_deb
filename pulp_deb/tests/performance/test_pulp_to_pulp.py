"""Tests that verify download of deb content served by Pulp."""

import pytest

from pulp_deb.tests.performance.utils import write_csv_to_tmp
from pulp_deb.tests.functional.utils import get_counts_from_content_summary
from pulp_deb.tests.functional.constants import (
    DEB_PACKAGE_NAME,
    DEB_PERF_BOOKWORN,
    DEB_PERF_DEBIAN_URL,
    DEB_PERF_JAMMY,
    DEB_PERF_UBUNTU_URL,
)

perf_p2p_test_params = [
    pytest.param(
        DEB_PERF_UBUNTU_URL,
        DEB_PERF_JAMMY,
        "pulp-deb-p2p-tests-ubuntu-jammy",
        id="performance-p2p-ubuntu-jammy",
    ),
    pytest.param(
        DEB_PERF_DEBIAN_URL,
        DEB_PERF_BOOKWORN,
        "pulp-deb-p2p-tests-debian-bookworm",
        id="performance-p2p-debian-bookworm",
    ),
]


@pytest.mark.parallel
@pytest.mark.parametrize("url,remote_args,csv_filename", perf_p2p_test_params)
def test_pulp_to_pulp(
    deb_distribution_factory,
    deb_get_content_summary,
    deb_init_and_sync,
    deb_publication_factory,
    url,
    remote_args,
    csv_filename,
):
    """Verify whether content served by pulp can be synced."""
    repo, _, task = deb_init_and_sync(url=url, remote_args=remote_args, return_task=True)
    task_time = (task.finished_at - task.started_at).total_seconds()
    wait_time = (task.started_at - task.pulp_created).total_seconds()
    print(f"\n->     Sync => Waiting time (s): {wait_time} | Service time (s): {task_time}")

    # Create a publication and distribution
    publication = deb_publication_factory(repo)
    distribution = deb_distribution_factory(publication)

    # Create another repo pointing to distribution base_url
    repo2, _, task = deb_init_and_sync(
        url=distribution.base_url, remote_args=remote_args, return_task=True
    )
    task_time_p2p = (task.finished_at - task.started_at).total_seconds()
    wait_time_p2p = (task.started_at - task.pulp_created).total_seconds()
    print(f"\n->     Sync => Waiting time (s): {wait_time_p2p} | Service time (s): {task_time_p2p}")

    repo_summary = deb_get_content_summary(repo)
    repo2_summary = deb_get_content_summary(repo2)
    present = get_counts_from_content_summary(repo_summary.present)
    present2 = get_counts_from_content_summary(repo2_summary.present)
    assert present[DEB_PACKAGE_NAME] == present2[DEB_PACKAGE_NAME]

    added = get_counts_from_content_summary(repo_summary.added)
    added2 = get_counts_from_content_summary(repo2_summary.added)
    assert added[DEB_PACKAGE_NAME] == added2[DEB_PACKAGE_NAME]

    write_csv_to_tmp(
        csv_filename,
        ["task_duration_initial", "waiting_time_initial", "task_duration_p2p", "waiting_time_p2p"],
        [task_time, wait_time, task_time_p2p, wait_time_p2p],
    )
