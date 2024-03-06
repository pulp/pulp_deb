import pytest

from pulp_deb.tests.functional.constants import (
    DEB_FIXTURE_SINGLE_DIST,
    DEB_FIXTURE_UPDATE_REPOSITORY_NAME,
)


@pytest.fixture
def deb_content_filters_init(deb_init_and_sync):
    def _deb_content_filters_init():
        remote_args = {"distributions": DEB_FIXTURE_SINGLE_DIST}
        repo, _ = deb_init_and_sync(remote_args=remote_args)
        repo_v1_href = repo.latest_version_href
        assert repo_v1_href.endswith("/1/")

        repo, _ = deb_init_and_sync(
            repository=repo, url=DEB_FIXTURE_UPDATE_REPOSITORY_NAME, remote_args=remote_args
        )
        repo_v2_href = repo.latest_version_href
        assert repo_v2_href.endswith("/2/")
        return (repo, repo_v1_href, repo_v2_href)

    return _deb_content_filters_init


@pytest.fixture
def deb_content_filters_get_hrefs(apt_release_api, apt_release_component_api):
    def _deb_content_filters_get_hrefs(repo_version_href, component):
        releases = apt_release_api.list(repository_version=repo_version_href)
        release_href = releases.results[0].pulp_href
        release_components = apt_release_component_api.list(repository_version=repo_version_href)
        rc = [x for x in release_components.results if x.component == component]
        rc_href = rc[0].pulp_href
        return (release_href, rc_href)

    return _deb_content_filters_get_hrefs


@pytest.mark.parallel
def test_content_relationship_filters(
    deb_content_filters_init,
    deb_content_filters_get_hrefs,
    apt_package_api,
    apt_release_api,
    apt_release_component_api,
):
    """Test whether filtering content for different repository versions are working."""
    # Create a repository with two different repository versions.
    repo, repo_v1_href, repo_v2_href = deb_content_filters_init()
    assert repo_v1_href.endswith("/1/")
    assert repo_v2_href.endswith("/2/")

    # Get the hrefs for the release and release components of the latest repository version
    release_href, rc_href = deb_content_filters_get_hrefs(repo_v2_href, "asgard")

    # Assert that the filters are working
    assert apt_package_api.list(release=f"{release_href},{repo_v1_href}").count == 4
    assert apt_package_api.list(release=f"{release_href},{repo_v2_href}").count == 6
    assert apt_package_api.list(release=f"{release_href},{repo.pulp_href}").count == 6

    assert apt_package_api.list(release_component=f"{rc_href},{repo_v1_href}").count == 3
    assert apt_package_api.list(release_component=f"{rc_href},{repo_v2_href}").count == 5
    packages = apt_package_api.list(release_component=f"{rc_href},{repo.pulp_href}")
    assert packages.count == 5

    # Filter for the specific package that got added in the latest repository version
    package_href = [x for x in packages.results if x.package == "heimdallr"][0].pulp_href

    assert apt_release_api.list(package=f"{package_href},{repo_v1_href}").count == 0
    assert apt_release_api.list(package=f"{package_href},{repo_v2_href}").count == 1
    assert apt_release_api.list(package=f"{package_href},{repo.pulp_href}").count == 1

    assert apt_release_component_api.list(package=f"{package_href},{repo_v1_href}").count == 0
    assert apt_release_component_api.list(package=f"{package_href},{repo_v2_href}").count == 1
    assert apt_release_component_api.list(package=f"{package_href},{repo.pulp_href}").count == 1


@pytest.mark.parametrize(
    "q,count",
    [
        # TODO: this should probably expanded to test multiple cases
        pytest.param(*data, id=data[0])
        for data in [("package__startswith=fri", 1), ("package__contains=hor", 1)]
    ],
)
def test_package_name_filters(
    deb_init_and_sync,
    apt_package_api,
    q,
    count,
    delete_orphans_pre,
):
    """Test whether package name filtering is working."""
    repo, _ = deb_init_and_sync()
    assert repo.latest_version_href.endswith("/1/")
    assert apt_package_api.list(q=q).count == count
