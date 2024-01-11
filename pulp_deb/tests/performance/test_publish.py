"""Tests that publish deb plugin repositories."""
import pytest

from pulp_deb.tests.functional.constants import (
    DEB_PACKAGE_NAME,
    DEB_PERF_BOOKWORN,
    DEB_PERF_DEBIAN_URL,
    DEB_PERF_JAMMY,
    DEB_PERF_UBUNTU_URL,
)


@pytest.mark.parametrize(
    "url,remote_args",
    [
        (DEB_PERF_UBUNTU_URL, DEB_PERF_JAMMY),
        (DEB_PERF_DEBIAN_URL, DEB_PERF_BOOKWORN),
    ],
)
def test_deb_publish(
    apt_publication_api,
    apt_repository_versions_api,
    deb_init_and_sync,
    monitor_task,
    url,
    remote_args,
    delete_orphans_pre,
):
    """Publish repositories with the deb plugin."""
    repo, _, task = deb_init_and_sync(url=url, remote_args=remote_args, return_task=True)
    task_duration = task.finished_at - task.started_at
    waiting_time = task.started_at - task.pulp_created
    print(
        "\n->     Sync => Waiting time (s): {wait} | Service time (s): {service}".format(
            wait=waiting_time.total_seconds(), service=task_duration.total_seconds()
        )
    )

    # Check that we have the correct content counts
    repo_ver = apt_repository_versions_api.read(repo.latest_version_href)
    assert DEB_PACKAGE_NAME in repo_ver.content_summary.present.keys()
    assert DEB_PACKAGE_NAME in repo_ver.content_summary.added.keys()

    # Publishing
    response = apt_publication_api.create({"repository": repo.pulp_href})
    task = monitor_task(response.task)
    task_duration = task.finished_at - task.started_at
    waiting_time = task.started_at - task.pulp_created
    print(
        "\n->     Publish => Waiting time (s): {wait} | Service time (s): {service}".format(
            wait=waiting_time.total_seconds(), service=task_duration.total_seconds()
        )
    )
