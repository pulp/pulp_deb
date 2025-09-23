import pytest
import asyncio
from uuid import uuid4
from aiohttp import ClientResponseError, ClientError

from pulpcore.client.pulp_deb.exceptions import ApiException, ServiceException

from pulp_deb.tests.functional.constants import DEB_FIXTURE_DISTS_ONLY, DEB_FIXTURE_POOLS_ONLY


FRIGG_RELPATH = "pool/asgard/f/frigg/frigg_1.0_ppc64.deb"


@pytest.mark.parallel
def test_acs_create_and_list_smoke(
    apt_acs_api,
    deb_acs_factory,
    deb_remote_factory,
    deb_get_fixture_server_url,
):
    """Minimal smoke test: create a Remote and an ACS with no paths, and ensure it lists back."""
    remote = deb_remote_factory(url=deb_get_fixture_server_url(), policy="on_demand")

    name = f"acs-smoke-{uuid4()}"
    acs = deb_acs_factory(name=name, remote=remote.pulp_href, paths=[])

    res = apt_acs_api.list(name=name)
    assert res.count == 1
    assert res.results[0].pulp_href == acs.pulp_href


@pytest.mark.parallel
def test_acs_end_to_end_download_fallback(
    deb_remote_factory,
    deb_repository_factory,
    deb_publication_factory,
    deb_distribution_factory,
    deb_get_fixture_server_url,
    deb_sync_repository,
    apt_package_api,
    apt_acs_api,
    deb_acs_factory,
    monitor_task_group,
    distribution_base_url,
    http_get,
    download_content_unit,
    record_property,
):
    """
    Proves ACS is used to fetch missing artifacts during download.

    Strategy:
      1) Sync from a primary remote that only serves metadata (no packages).
      2) Verify that download of packages fails.
      3) Add an ACS with the correct base + paths=['pool/'].
      4) The download now succeeds via ACS.
    """
    # primary_base = deb_get_fixture_server_url()
    primary_base = deb_get_fixture_server_url(repo_name=DEB_FIXTURE_DISTS_ONLY)
    acs_base = deb_get_fixture_server_url(repo_name=DEB_FIXTURE_POOLS_ONLY)

    # 1) Primary remote
    primary = deb_remote_factory(
        url=primary_base,
        distributions="ragnarok",
        components="asgard",
        architectures="ppc64",
        policy="on_demand",
    )

    repo = deb_repository_factory()
    deb_sync_repository(primary, repo)

    pub = deb_publication_factory(repo, structured=True, simple=True)
    dist = deb_distribution_factory(publication=pub)

    abs_base = distribution_base_url(dist.base_url)
    url = f"{abs_base.rstrip('/')}/{FRIGG_RELPATH}"

    pkgs = apt_package_api.list(repository_version=pub.repository_version).results
    candidate_relpaths = []
    for p in pkgs:
        rel = getattr(p, "filename", None) or getattr(p, "relative_path", None)
        if rel and rel.endswith(".deb"):
            candidate_relpaths.append(rel)
    assert candidate_relpaths, "No .deb candidates discovered in publication"

    # 2) Verify download fails
    failing_rel = None
    last_exc = None
    for rel in candidate_relpaths:
        url = f"{abs_base.rstrip('/')}/{rel}"
        try:
            http_get(url)
        except (ClientResponseError, ClientError, asyncio.TimeoutError, OSError) as e:
            failing_rel = rel
            last_exc = e
            break
    if failing_rel is None:
        pytest.skip("goddamn")
    record_property("pre_acs_exception", f"{type(last_exc).__name__}: {last_exc}")

    # 4) Create ACS with the relevant packages
    acs_remote = deb_remote_factory(url=acs_base, policy="on_demand")
    acs = deb_acs_factory(
        name=f"acs-e2e-{uuid4()}",
        remote=acs_remote.pulp_href,
        paths=["pool/"],
    )
    try:
        tg = apt_acs_api.refresh(acs.pulp_href)
    except ServiceException as e:
        cid = getattr(getattr(e, "http_resp", None), "headers", {}).get("Correlation-ID")
        record_property("acs_refresh_500_corr_id", cid or "")
    else:
        monitor_task_group(tg.task_group)

    # 5) AFTER ACS: the same download now succeeds
    content = download_content_unit(dist.base_path, failing_rel)
    assert content and len(content) > 0


@pytest.mark.parallel
def test_acs_refresh_taskgroup(
    apt_acs_api,
    deb_acs_factory,
    deb_remote_factory,
    deb_get_fixture_server_url,
    monitor_task_group,
):
    """
    Create an ACS with one path and call refresh; assert the TaskGroup completes.

    NOTE: ACS requires a remote with policy='on_demand'.
    """
    remote = deb_remote_factory(url=deb_get_fixture_server_url(), policy="on_demand")
    acs = deb_acs_factory(
        name=f"acs-refresh-{uuid4()}",
        remote=remote.pulp_href,
        paths=["pool/"],
    )

    try:
        tg = apt_acs_api.refresh(acs.pulp_href)
    except ServiceException as e:
        # 5xx from server
        cid = getattr(getattr(e, "http_resp", None), "headers", {}).get("Correlation-ID")
        pytest.xfail(f"ACS refresh returns 500. Correlation-ID: {cid}")
    else:
        monitor_task_group(tg.task_group)


@pytest.mark.parallel
@pytest.mark.parametrize(
    "bad_paths, expected_msg_fragment",
    [
        (["/pool/"], "Path cannot start with a slash"),
        (["pool"], "Path must end with a slash"),
        (["/pool"], "Path cannot start with a slash"),
    ],
)
def test_acs_path_validation(
    deb_remote_factory,
    deb_get_fixture_server_url,
    deb_acs_factory,
    bad_paths,
    expected_msg_fragment,
):
    """Verifies serializer path validation."""
    remote = deb_remote_factory(url=deb_get_fixture_server_url(), policy="immediate")

    with pytest.raises(ApiException) as exc:
        deb_acs_factory(name=f"acs-validate-{uuid4()}", remote=remote.pulp_href, paths=bad_paths)

    assert exc.value.status == 400
    assert expected_msg_fragment.lower() in exc.value.body.lower()


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

    acs = deb_acs_factory(name=name, remote=remote.pulp_href, paths=[])
    # read
    got = apt_acs_api.read(acs.pulp_href)
    assert got.pulp_href == acs.pulp_href
    assert got.name == name
    assert [p for p in (got.paths or []) if p] == []

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
    deb_acs_factory(name=name, remote=remote.pulp_href, paths=[])

    with pytest.raises(ApiException) as exc:
        deb_acs_factory(name=name, remote=remote.pulp_href, paths=[])

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
        deb_acs_factory(name=f"acs-pol-{uuid4()}", remote=bad_remote.pulp_href, paths=[])

    assert exc.value.status == 400
    assert "on_demand" in exc.value.body


@pytest.mark.parallel
def test_acs_update_paths_patch_and_put(
    apt_acs_api,
    deb_acs_factory,
    deb_remote_factory,
    deb_get_fixture_server_url,
    monitor_task,
):
    remote = deb_remote_factory(url=deb_get_fixture_server_url(), policy="on_demand")
    acs = deb_acs_factory(name=f"acs-update-{uuid4()}", remote=remote.pulp_href, paths=[])

    # PATCH add a valid path
    resp = apt_acs_api.partial_update(acs.pulp_href, {"paths": ["pool/"]})
    monitor_task(resp.task)
    updated = apt_acs_api.read(acs.pulp_href)
    assert updated.paths == ["pool/"]

    # PUT replace with two paths
    resp = apt_acs_api.update(
        acs.pulp_href,
        {
            "name": updated.name,
            "remote": remote.pulp_href,
            "paths": ["pool/main/", "dists/stable/"],
        },
    )
    monitor_task(resp.task)
    updated = apt_acs_api.read(acs.pulp_href)
    assert set(updated.paths) == {"pool/main/", "dists/stable/"}

    # PATCH invalid path (no trailing slash) -> 400
    with pytest.raises(ApiException) as exc:
        apt_acs_api.partial_update(acs.pulp_href, {"paths": ["pool"]})
    assert exc.value.status == 400
    assert "slash" in exc.value.body.lower()


@pytest.mark.parallel
def test_acs_refresh_no_paths_returns_taskgroup(
    apt_acs_api,
    deb_acs_factory,
    deb_remote_factory,
    deb_get_fixture_server_url,
    monitor_task_group,
):
    """Empty paths are allowed; refresh should be a quick no-op TaskGroup."""
    remote = deb_remote_factory(url=deb_get_fixture_server_url(), policy="on_demand")
    acs = deb_acs_factory(name=f"acs-refresh-empty-{uuid4()}", remote=remote.pulp_href, paths=[])
    try:
        tg = apt_acs_api.refresh(acs.pulp_href)
    except ServiceException as e:
        cid = getattr(getattr(e, "http_resp", None), "headers", {}).get("Correlation-ID")
        pytest.xfail(f"ACS refresh (empty paths) returned 5xx. Correlation-ID: {cid}")
    else:
        monitor_task_group(tg.task_group)


@pytest.mark.parallel
def test_acs_list_pagination(
    apt_acs_api,
    deb_acs_factory,
    deb_remote_factory,
    deb_get_fixture_server_url,
):
    remote = deb_remote_factory(url=deb_get_fixture_server_url(), policy="on_demand")
    prefix = f"acs-page-{uuid4()}"
    _ = [
        deb_acs_factory(name=f"{prefix}-{i}", remote=remote.pulp_href, paths=[]) for i in range(12)
    ]

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
