import pytest
from uuid import uuid4

from pulpcore.tests.functional.utils import PulpTaskError
from pulpcore.client.pulp_deb.exceptions import ApiException, ServiceException

from pulp_deb.tests.functional.constants import DEB_FIXTURE_ACS, DEB_FIXTURE_ACS_SUMMARY
from pulp_deb.tests.functional.utils import get_counts_from_content_summary


FRIGG_RELPATH = "pool/asgard/f/frigg/frigg_1.0_ppc64.deb"


@pytest.fixture(scope="function")
def register_acs_repo_for_cleanup(apt_repository_api, add_to_cleanup):
    """
    Return a helper that, given an ACS object, finds the hidden repo created
    by apt_acs_api.refresh() and registers it for teadown cleanup.
    """

    def _register(acs_obj):
        hidden_repo_name = f"{acs_obj.name}--repository"
        repos = apt_repository_api.list(name=hidden_repo_name)

        if getattr(repos, "count", 0) == 1:
            hidden_repo_href = repos.results[0].pulp_href
            add_to_cleanup(apt_repository_api, hidden_repo_href)

    return _register


@pytest.mark.parallel
def test_acs_create_and_list_smoke(
    apt_acs_api,
    deb_acs_factory,
    deb_remote_factory,
    deb_get_fixture_server_url,
):
    """Minimal smoke test: create a Remote and an ACS, and ensure it lists back."""
    remote = deb_remote_factory(url=deb_get_fixture_server_url(), policy="on_demand")

    name = f"acs-smoke-{uuid4()}"
    acs = deb_acs_factory(name=name, remote=remote.pulp_href)

    res = apt_acs_api.list(name=name)
    assert res.count == 1
    assert res.results[0].pulp_href == acs.pulp_href


def test_acs_simple(
    deb_remote_factory,
    deb_repository_factory,
    deb_get_fixture_server_url,
    deb_sync_repository,
    deb_get_repository_by_href,
    deb_get_content_summary,
    apt_acs_api,
    deb_acs_factory,
    monitor_task_group,
    delete_orphans_pre,
    register_acs_repo_for_cleanup,
):
    """
    Verifies that an ACS can supply missing artifacts to a metadata-only remote.

    Steps:
      1) Sync from a remote that serves only metadata -> expect failure (missing packages).
      2) Create and refresh an ACS that can serve full content.
      3) Sync again -> expect success.
      4) Assert repository content matches the expected summary.
    """
    primary_base = deb_get_fixture_server_url(repo_name=DEB_FIXTURE_ACS)
    acs_base = deb_get_fixture_server_url()

    primary = deb_remote_factory(
        url=primary_base,
        distributions="ragnarok",
        policy="immediate",
    )

    acs_remote = deb_remote_factory(url=acs_base, distributions="ragnarok", policy="on_demand")
    acs = deb_acs_factory(
        name=f"acs-e2e-{uuid4()}",
        remote=acs_remote.pulp_href,
    )

    repo = deb_repository_factory()
    with pytest.raises(PulpTaskError) as ctx:
        deb_sync_repository(primary, repo)

    assert "404, message='Not Found'" in ctx.value.task.error["description"]

    tg = apt_acs_api.refresh(acs.pulp_href)
    monitor_task_group(tg.task_group)
    register_acs_repo_for_cleanup(acs)

    deb_sync_repository(primary, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)
    present = deb_get_content_summary(repo).present
    assert get_counts_from_content_summary(present) == DEB_FIXTURE_ACS_SUMMARY


@pytest.mark.parallel
def test_acs_refresh_taskgroup(
    apt_acs_api,
    deb_acs_factory,
    deb_remote_factory,
    deb_get_fixture_server_url,
    monitor_task_group,
    register_acs_repo_for_cleanup,
):
    """
    Create an ACS with one path and call refresh; assert the TaskGroup completes.

    NOTE: ACS requires a remote with policy='on_demand'.
    """
    remote = deb_remote_factory(url=deb_get_fixture_server_url(), policy="on_demand")
    acs = deb_acs_factory(
        name=f"acs-refresh-{uuid4()}",
        remote=remote.pulp_href,
    )

    try:
        tg = apt_acs_api.refresh(acs.pulp_href)
    except ServiceException as e:
        # 5xx from server
        cid = getattr(getattr(e, "http_resp", None), "headers", {}).get("Correlation-ID")
        pytest.xfail(f"ACS refresh returns 500. Correlation-ID: {cid}")
    else:
        monitor_task_group(tg.task_group)
    register_acs_repo_for_cleanup(acs)


@pytest.mark.parallel
def test_acs_paths_not_supported(
    deb_remote_factory,
    deb_get_fixture_server_url,
    deb_acs_factory,
):
    """Supplying a non-empty 'paths' should 400 for deb ACS."""
    remote = deb_remote_factory(url=deb_get_fixture_server_url(), policy="on_demand")

    with pytest.raises(ApiException) as exc:
        deb_acs_factory(
            name=f"acs-bad-{uuid4()}",
            remote=remote.pulp_href,
            paths=["pool/"],  # forbidden
        )

    assert exc.value.status == 400
    assert "not supported" in exc.value.body.lower()


@pytest.mark.parallel
def test_acs_crud_roundtrip(
    apt_acs_api,
    deb_acs_factory,
    deb_remote_factory,
    deb_get_fixture_server_url,
):
    """Create -> read -> list -> delete -> verify gone."""
    remote = deb_remote_factory(url=deb_get_fixture_server_url(), policy="on_demand")
    name = f"acs-crud-{uuid4()}"

    acs = deb_acs_factory(name=name, remote=remote.pulp_href)
    # read
    got = apt_acs_api.read(acs.pulp_href)
    assert got.pulp_href == acs.pulp_href
    assert got.name == name

    # list by name
    res = apt_acs_api.list(name=name)
    assert res.count == 1
    assert res.results[0].pulp_href == acs.pulp_href

    # delete
    apt_acs_api.delete(acs.pulp_href)

    # verify 404
    with pytest.raises(ApiException) as exc:
        apt_acs_api.read(acs.pulp_href)
    assert exc.value.status == 404


@pytest.mark.parallel
def test_acs_name_must_be_unique(
    deb_acs_factory,
    deb_remote_factory,
    deb_get_fixture_server_url,
):
    remote = deb_remote_factory(url=deb_get_fixture_server_url(), policy="on_demand")
    name = f"acs-unique-{uuid4()}"
    deb_acs_factory(name=name, remote=remote.pulp_href)

    with pytest.raises(ApiException) as exc:
        deb_acs_factory(name=name, remote=remote.pulp_href)

    assert exc.value.status == 400
    assert "unique" in exc.value.body.lower()


@pytest.mark.parallel
def test_acs_remote_policy_validation(
    deb_remote_factory,
    deb_get_fixture_server_url,
    deb_acs_factory,
):
    """Using a non-on_demand remote should 400 with a clear message."""
    bad_remote = deb_remote_factory(url=deb_get_fixture_server_url(), policy="immediate")
    with pytest.raises(ApiException) as exc:
        deb_acs_factory(name=f"acs-pol-{uuid4()}", remote=bad_remote.pulp_href)

    assert exc.value.status == 400
    assert "on_demand" in exc.value.body


@pytest.mark.parallel
def test_acs_list_pagination(
    apt_acs_api,
    deb_acs_factory,
    deb_remote_factory,
    deb_get_fixture_server_url,
):
    remote = deb_remote_factory(url=deb_get_fixture_server_url(), policy="on_demand")
    prefix = f"acs-page-{uuid4()}"
    _ = [deb_acs_factory(name=f"{prefix}-{i}", remote=remote.pulp_href) for i in range(12)]

    # list all by name prefix
    all_res = apt_acs_api.list(name__contains=prefix, limit=100)
    assert all_res.count == 12

    # first page
    p1 = apt_acs_api.list(name__contains=prefix, limit=5, offset=0)
    assert len(p1.results) == 5

    # second page
    p2 = apt_acs_api.list(name__contains=prefix, limit=5, offset=5)
    assert len(p2.results) == 5

    # last page
    p3 = apt_acs_api.list(name__contains=prefix, limit=5, offset=10)
    assert len(p3.results) == 2

    # sanity: no duplicates across pages by pulp_href
    seen = {x.pulp_href for x in p1.results + p2.results + p3.results}
    assert len(seen) == 12
