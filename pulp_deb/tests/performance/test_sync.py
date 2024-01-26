"""Tests that sync deb plugin repositories."""

import pytest

from pulp_deb.tests.functional.constants import (
    DEB_PERF_BOOKWORN,
    DEB_PERF_DEBIAN_URL,
    DEB_PERF_JAMMY,
    DEB_PERF_UBUNTU_URL,
)


@pytest.mark.parallel
@pytest.mark.parametrize(
    "url,remote_args,resync",
    [
        (DEB_PERF_UBUNTU_URL, DEB_PERF_JAMMY, True),
        (DEB_PERF_DEBIAN_URL, DEB_PERF_BOOKWORN, True),
    ],
)
def test_deb_sync(deb_init_and_sync, url, remote_args, resync):
    """Sync repositories with the deb plugin."""
    # Create repository & remote and sync
    repo, remote, task = deb_init_and_sync(url=url, remote_args=remote_args, return_task=True)

    task_duration = task.finished_at - task.started_at
    waiting_time = task.started_at - task.pulp_created
    print(
        "\n->     Sync => Waiting time (s): {wait} | Service time (s): {service}".format(
            wait=waiting_time.total_seconds(), service=task_duration.total_seconds()
        )
    )

    if resync:
        # Sync the repository again.
        latest_version_href = repo.latest_version_href
        repo, _, task = deb_init_and_sync(repository=repo, remote=remote, return_task=True)

        task_duration = task.finished_at - task.started_at
        waiting_time = task.started_at - task.pulp_created
        print(
            "\n->     Re-sync => Waiting time (s): {wait} | Service time (s): {service}".format(
                wait=waiting_time.total_seconds(), service=task_duration.total_seconds()
            )
        )

        # Check that nothing has changed since the last sync.
        assert latest_version_href == repo.latest_version_href
