"""Tests that verify download of deb content served by Pulp."""

import pytest

from pulp_deb.tests.functional.utils import get_counts_from_content_summary
from pulp_deb.tests.functional.constants import (
    DEB_PACKAGE_NAME,
    DEB_PERF_BOOKWORN,
    DEB_PERF_DEBIAN_URL,
    DEB_PERF_JAMMY,
    DEB_PERF_UBUNTU_URL,
)


@pytest.mark.parallel
@pytest.mark.parametrize(
    "url,remote_args",
    [
        (DEB_PERF_UBUNTU_URL, DEB_PERF_JAMMY),
        (DEB_PERF_DEBIAN_URL, DEB_PERF_BOOKWORN),
    ],
)
def test_pulp_to_pulp(
    deb_distribution_factory,
    deb_get_content_summary,
    deb_init_and_sync,
    deb_publication_factory,
    url,
    remote_args,
):
    """Verify whether content served by pulp can be synced."""
    repo, _, task = deb_init_and_sync(url=url, remote_args=remote_args, return_task=True)
    task_duration = task.finished_at - task.started_at
    waiting_time = task.started_at - task.pulp_created
    print(
        "\n->     Sync => Waiting time (s): {wait} | Service time (s): {service}".format(
            wait=waiting_time.total_seconds(), service=task_duration.total_seconds()
        )
    )

    # Create a publication and distribution
    publication = deb_publication_factory(repo)
    distribution = deb_distribution_factory(publication)

    # Create another repo pointing to distribution base_url
    repo2, _, task = deb_init_and_sync(
        url=distribution.base_url, remote_args=remote_args, return_task=True
    )
    task_duration = task.finished_at - task.started_at
    waiting_time = task.started_at - task.pulp_created
    print(
        "\n->     Sync => Waiting time (s): {wait} | Service time (s): {service}".format(
            wait=waiting_time.total_seconds(), service=task_duration.total_seconds()
        )
    )

    repo_summary = deb_get_content_summary(repo)
    repo2_summary = deb_get_content_summary(repo2)
    present = get_counts_from_content_summary(repo_summary.present)
    present2 = get_counts_from_content_summary(repo2_summary.present)
    assert present[DEB_PACKAGE_NAME] == present2[DEB_PACKAGE_NAME]

    added = get_counts_from_content_summary(repo_summary.added)
    added2 = get_counts_from_content_summary(repo2_summary.added)
    assert added[DEB_PACKAGE_NAME] == added2[DEB_PACKAGE_NAME]
