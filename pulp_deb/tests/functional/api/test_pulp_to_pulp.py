"""Tests that verify download of content served by Pulp."""

import pytest

from pulp_deb.tests.functional.constants import (
    DEB_FIXTURE_FLAT_REPOSITORY_NAME,
    DEB_P2P_FLAT_STRUCTURED,
    DEB_P2P_REMOTE_ARGS_FLAT,
    DEB_P2P_SIMPLE_THEN_STRUCTURED,
    DEB_PUBLICATION_ARGS_ONLY_SIMPLE,
    DEB_PUBLICATION_ARGS_ONLY_STRUCTURED,
    DEB_PUBLICATION_ARGS_SIMPLE_AND_STRUCTURED,
    DEB_P2P_ONLY_SIMPLE,
    DEB_P2P_ONLY_STRUCTURED,
    DEB_P2P_SIMPLE_AND_STRUCTURED,
    DEB_P2P_REMOTE_ARGS_SIMPLE,
    DEB_P2P_REMOTE_ARGS_STRUCTURED,
    DEB_P2P_REMOTE_ARGS_BOTH,
    DEB_P2P_REMOTE_ARGS_VERBATIM,
)
from pulp_deb.tests.functional.utils import get_counts_from_content_summary

pulp_to_pulp_test_data = [
    pytest.param(
        "immediate",
        False,
        DEB_PUBLICATION_ARGS_ONLY_SIMPLE,
        DEB_P2P_REMOTE_ARGS_SIMPLE,
        DEB_P2P_ONLY_SIMPLE,
        id="p2p-immediate-simple",
    ),
    pytest.param(
        "immediate",
        False,
        DEB_PUBLICATION_ARGS_ONLY_STRUCTURED,
        DEB_P2P_REMOTE_ARGS_STRUCTURED,
        DEB_P2P_ONLY_STRUCTURED,
        id="p2p-immediate-structured",
    ),
    pytest.param(
        "immediate",
        False,
        DEB_PUBLICATION_ARGS_SIMPLE_AND_STRUCTURED,
        DEB_P2P_REMOTE_ARGS_BOTH,
        DEB_P2P_SIMPLE_AND_STRUCTURED,
        id="p2p-immediate-both",
    ),
    pytest.param(
        "immediate", True, {}, DEB_P2P_REMOTE_ARGS_VERBATIM, {}, id="p2p-immediate-verbatim"
    ),
    pytest.param(
        "streamed",
        False,
        DEB_PUBLICATION_ARGS_ONLY_SIMPLE,
        DEB_P2P_REMOTE_ARGS_SIMPLE,
        DEB_P2P_ONLY_SIMPLE,
        id="p2p-streamed-simple",
    ),
    pytest.param(
        "streamed",
        False,
        DEB_PUBLICATION_ARGS_ONLY_STRUCTURED,
        DEB_P2P_REMOTE_ARGS_STRUCTURED,
        DEB_P2P_ONLY_STRUCTURED,
        id="p2p-streamed-structured",
    ),
    pytest.param(
        "streamed",
        False,
        DEB_PUBLICATION_ARGS_SIMPLE_AND_STRUCTURED,
        DEB_P2P_REMOTE_ARGS_BOTH,
        DEB_P2P_SIMPLE_AND_STRUCTURED,
        id="p2p-streamed-both",
    ),
    pytest.param(
        "streamed", True, {}, DEB_P2P_REMOTE_ARGS_VERBATIM, {}, id="p2p-streamed-verbatim"
    ),
    pytest.param(
        "on_demand",
        False,
        DEB_PUBLICATION_ARGS_ONLY_SIMPLE,
        DEB_P2P_REMOTE_ARGS_SIMPLE,
        DEB_P2P_ONLY_SIMPLE,
        id="p2p-on_demand-simple",
    ),
    pytest.param(
        "on_demand",
        False,
        DEB_PUBLICATION_ARGS_ONLY_STRUCTURED,
        DEB_P2P_REMOTE_ARGS_STRUCTURED,
        DEB_P2P_ONLY_STRUCTURED,
        id="p2p-on_demand-structured",
    ),
    pytest.param(
        "on_demand",
        False,
        DEB_PUBLICATION_ARGS_SIMPLE_AND_STRUCTURED,
        DEB_P2P_REMOTE_ARGS_BOTH,
        DEB_P2P_SIMPLE_AND_STRUCTURED,
        id="p2p-on_demand-both",
    ),
    pytest.param(
        "on_demand", True, {}, DEB_P2P_REMOTE_ARGS_VERBATIM, {}, id="p2p-on_demand-verbatim"
    ),
]


@pytest.mark.parametrize(
    "policy, is_verbatim, publication_args, remote_args_new, expected_value", pulp_to_pulp_test_data
)
def test_pulp_to_pulp_sync(
    deb_get_content_summary,
    deb_init_and_sync,
    deb_distribution_factory,
    is_verbatim,
    policy,
    publication_args,
    request,
    remote_args_new,
    expected_value,
    delete_orphans_pre,
):
    """Verify whether content served by Pulp can be synced.

    The initial sync to Pulp is one of many different download policies, the second sync is
    immediate in order to exercise downloading all of the files.

    Multiple test cases are covered here which are a combination of different policies and
    different publish methods:

    * `Test policy=immediate and publish=simple`
    * `Test policy=immediate and publish=structured`
    * `Test policy=immediate and publish=simple+structured`
    * `Test policy=immediate and publish=verbatim`
    * `Test policy=streamed and publish=simple`
    * `Test policy=streamed and publish=structured`
    * `Test policy=streamed and publish=simple+structured`
    * `Test policy=streamed and publish=verbatim`
    * `Test policy=on_demand and publish=simple`
    * `Test policy=on_demand and publish=structured`
    * `Test policy=on_demand and publish=simple+structured`
    * `Test policy=on_demand and publish=verbatim`
    """
    remote_args = {"policy": policy}
    publication_factory = (
        request.getfixturevalue("deb_verbatim_publication_factory")
        if is_verbatim
        else request.getfixturevalue("deb_publication_factory")
    )

    # Create and sync a repository. Then publish and distribute it.
    repo, _ = deb_init_and_sync(remote_args=remote_args)
    publication = publication_factory(repo, **publication_args)
    distribution = deb_distribution_factory(publication)

    # Create and sync a new repository with the published repo as the remote
    repo_new, _ = deb_init_and_sync(url=distribution.base_url, remote_args=remote_args_new)

    # Assert whether the present content matches the expected data
    summary_new = deb_get_content_summary(repo_new)
    summary_orig = deb_get_content_summary(repo)
    present_new = get_counts_from_content_summary(summary_new.present)
    if is_verbatim:
        present_orig = get_counts_from_content_summary(summary_orig.present)
        assert present_orig == present_new
    else:
        assert present_new == expected_value

    # Assert whether the added content matches the expected data
    added_new = get_counts_from_content_summary(summary_new.added)
    if is_verbatim:
        added_orig = get_counts_from_content_summary(summary_orig.added)
        assert added_orig == added_new
    else:
        assert added_new == expected_value


def test_pulp_to_pulp_sync_simple_to_structured(
    deb_init_and_sync,
    deb_publication_factory,
    deb_distribution_factory,
    deb_get_content_summary,
    delete_orphans_pre,
):
    """Verify whether a repository served by Pulp can sync its simple content first
    and in a concurrent sync simple and structured content without loss of data.
    """
    # Create and sync a repository. Then publish and distribute it.
    repo, _ = deb_init_and_sync(remote_args={"policy": "immediate"})
    publication = deb_publication_factory(repo, **DEB_PUBLICATION_ARGS_SIMPLE_AND_STRUCTURED)
    distribution = deb_distribution_factory(publication)

    # Create and sync a new repository with published repo as the remote and simple distribution
    repo_simple, _ = deb_init_and_sync(
        url=distribution.base_url, remote_args=DEB_P2P_REMOTE_ARGS_SIMPLE
    )
    summary_simple = deb_get_content_summary(repo_simple)
    present_simple = get_counts_from_content_summary(summary_simple.present)
    added_simple = get_counts_from_content_summary(summary_simple.added)
    assert present_simple == DEB_P2P_ONLY_SIMPLE
    assert added_simple == DEB_P2P_ONLY_SIMPLE

    # Use the same respository and sync again with published repo as remote but both distributions
    repo_both, _ = deb_init_and_sync(
        repository=repo_simple, url=distribution.base_url, remote_args=DEB_P2P_REMOTE_ARGS_BOTH
    )
    summary_both = deb_get_content_summary(repo_both)
    present_both = get_counts_from_content_summary(summary_both.present)
    added_both = get_counts_from_content_summary(summary_both.added)
    assert added_both == DEB_P2P_SIMPLE_THEN_STRUCTURED
    assert present_both == DEB_P2P_SIMPLE_AND_STRUCTURED


def test_pulp_to_pulp_sync_flat(
    deb_init_and_sync,
    deb_publication_factory,
    deb_distribution_factory,
    deb_get_content_summary,
    delete_orphans_pre,
):
    """Verify whether a repository served by Pulp can sync its content originally
    stemming from a flat repository.
    """
    repo_flat, _ = deb_init_and_sync(
        remote_args={"distributions": "/", "policy": "immediate"},
        url=DEB_FIXTURE_FLAT_REPOSITORY_NAME,
    )
    publication = deb_publication_factory(repo_flat, **DEB_PUBLICATION_ARGS_ONLY_STRUCTURED)
    distribution = deb_distribution_factory(publication)

    repo_new, _ = deb_init_and_sync(url=distribution.base_url, remote_args=DEB_P2P_REMOTE_ARGS_FLAT)
    summary_new = deb_get_content_summary(repo_new)
    present_new = get_counts_from_content_summary(summary_new.present)
    added_new = get_counts_from_content_summary(summary_new.added)
    assert present_new == DEB_P2P_FLAT_STRUCTURED
    assert added_new == DEB_P2P_FLAT_STRUCTURED
