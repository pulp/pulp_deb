import pytest

from pulpcore.client.pulp_deb import (
    AptRepositorySyncURL,
)


@pytest.fixture
def setup_autopublish(
    deb_get_fixture_server_url, deb_repository_factory, deb_remote_factory, deb_distribution_factory
):
    """Create remote, repo, publish settings, and distribution."""
    url = deb_get_fixture_server_url()
    remote = deb_remote_factory(url=url)
    repo = deb_repository_factory(autopublish=True)
    distribution = deb_distribution_factory(repository=repo)

    return repo, remote, distribution


@pytest.mark.parallel
def test_01_sync(setup_autopublish, apt_repository_api, apt_publication_api, monitor_task):
    """Assert that syncing the repository triggers auto-publish and auto-distribution."""
    repo, remote, distribution = setup_autopublish
    assert apt_publication_api.list(repository=repo.pulp_href).count == 0
    assert distribution.publication is None

    # Sync the repository.
    repository_sync_data = AptRepositorySyncURL(remote=remote.pulp_href)
    sync_response = apt_repository_api.sync(repo.pulp_href, repository_sync_data)
    task = monitor_task(sync_response.task)

    # Check that all the appropriate resources were created
    assert len(task.created_resources) > 1
    publications = apt_publication_api.list(repository=repo.pulp_href)
    assert publications.count == 1

    # Sync the repository again. Since there should be no new repository version, there
    # should be no new publications or distributions either.
    sync_response = apt_repository_api.sync(repo.pulp_href, repository_sync_data)
    task = monitor_task(sync_response.task)

    assert len(task.created_resources) == 0
    assert apt_publication_api.list(repository=repo.pulp_href).count == 1


@pytest.mark.parallel
def test_02_modify(
    setup_autopublish, apt_repository_api, apt_package_api, apt_publication_api, monitor_task
):
    """Assert that modifying the repository triggers auto-publish and auto-distribution."""
    repo, remote, distribution = setup_autopublish
    assert apt_publication_api.list(repository=repo.pulp_href).count == 0
    assert distribution.publication is None

    # Modify the repository by adding a content unit
    content = apt_package_api.list().results[0].pulp_href

    modify_response = apt_repository_api.modify(repo.pulp_href, {"add_content_units": [content]})
    task = monitor_task(modify_response.task)

    # Check that all the appropriate resources were created
    assert len(task.created_resources) > 1
    publications = apt_publication_api.list(repository=repo.pulp_href)
    assert publications.count == 1
