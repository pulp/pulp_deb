import pytest
from pathlib import Path

from pulp_deb.tests.functional.utils import gen_deb_remote, gen_distribution, gen_repo
from pulp_deb.tests.functional.constants import DEB_FIXTURE_STANDARD_REPOSITORY_NAME

from pulpcore.client.pulp_deb import (
    ApiClient,
    AptRepositorySyncURL,
    DebAptPublication,
    DistributionsAptApi,
    PublicationsAptApi,
    RemotesAptApi,
    RepositoriesAptApi,
    RepositoriesAptVersionsApi,
)


@pytest.fixture(scope="session")
def apt_client(_api_client_set, bindings_cfg):
    """Fixture for APT client."""
    api_client = ApiClient(bindings_cfg)
    _api_client_set.add(api_client)
    yield api_client
    _api_client_set.remove(api_client)


@pytest.fixture(scope="session")
def apt_distribution_api(apt_client):
    """Fixture for APT distribution API."""
    return DistributionsAptApi(apt_client)


@pytest.fixture(scope="session")
def apt_publication_api(apt_client):
    """Fixture for APT publication API."""
    return PublicationsAptApi(apt_client)


@pytest.fixture(scope="session")
def apt_remote_api(apt_client):
    """Fixture for APT remote API."""
    return RemotesAptApi(apt_client)


@pytest.fixture(scope="session")
def apt_repository_api(apt_client):
    """Fixture for APT repositories API."""
    return RepositoriesAptApi(apt_client)


@pytest.fixture(scope="session")
def apt_repository_versions_api(apt_client):
    """Fixture for APT repository versions API."""
    return RepositoriesAptVersionsApi(apt_client)


@pytest.fixture(scope="class")
def deb_distribution_factory(apt_distribution_api, gen_object_with_cleanup):
    """Fixture that generates a deb distribution with cleanup from a given publication."""

    def _deb_distribution_factory(publication=None, repository=None, checkpoint=None):
        """Create a deb distribution.

        :param publication: The publication the distribution is based on.
        :returns: The created distribution.
        """
        body = gen_distribution()
        if publication:
            body["publication"] = publication.pulp_href
        if repository:
            body["repository"] = repository.pulp_href
        if checkpoint is not None:
            body["checkpoint"] = checkpoint
        return gen_object_with_cleanup(apt_distribution_api, body)

    return _deb_distribution_factory


@pytest.fixture(scope="class")
def deb_publication_factory(apt_publication_api, gen_object_with_cleanup):
    """Fixture that generates a deb publication with cleanup from a given repository."""

    def _deb_publication_factory(repo, **kwargs):
        """Create a deb publication.

        :param repo: The repository the publication is based on.
        :returns: The created publication.
        """
        publication_data = DebAptPublication(repository=repo.pulp_href, **kwargs)
        return gen_object_with_cleanup(apt_publication_api, publication_data)

    return _deb_publication_factory


@pytest.fixture(scope="class")
def deb_repository_factory(apt_repository_api, gen_object_with_cleanup):
    """Fixture that generates a deb repository with cleanup."""

    def _deb_repository_factory(pulp_domain=None, **kwargs):
        """Create a deb repository.

        :returns: The created repository.
        """
        return gen_object_with_cleanup(
            apt_repository_api, gen_repo(pulp_domain=pulp_domain, **kwargs)
        )

    return _deb_repository_factory


@pytest.fixture(scope="class")
def deb_remote_factory(apt_remote_api, gen_object_with_cleanup):
    """Fixture that generates a deb remote with cleanup."""

    def _deb_remote_factory(url, **kwargs):
        """Creats a remote from the given url.

        :param url: The name of the local data repository.
        :returns: The created remote.
        """
        return gen_object_with_cleanup(apt_remote_api, gen_deb_remote(url=str(url), **kwargs))

    return _deb_remote_factory


@pytest.fixture
def deb_sync_repository(apt_repository_api, monitor_task):
    """Fixture that synchronizes a given repository with a given remote
    and returns the monitored task.
    """

    def _deb_sync_repository(remote, repo, mirror=False, optimize=True):
        """Sync a given remote and repository.

        :param remote: The remote where to sync from.
        :param repo: The repository that needs syncing.
        :param mirror: Whether the sync should use mirror mode. Default False.
        :param optimize: Whether the sync should use optimize mode. Default True.
        :returns: The task of the sync operation.
        """
        repository_sync_data = AptRepositorySyncURL(
            remote=remote.pulp_href, mirror=mirror, optimize=optimize
        )
        sync_response = apt_repository_api.sync(repo.pulp_href, repository_sync_data)
        return monitor_task(sync_response.task)

    return _deb_sync_repository


@pytest.fixture
def deb_fixture_server(gen_fixture_server):
    """A fixture that spins up a local web server to serve test data."""
    p = Path(__file__).parent.absolute()
    fixture_path = p.joinpath("functional/data/")
    yield gen_fixture_server(fixture_path, None)


@pytest.fixture
def deb_get_fixture_server_url(deb_fixture_server):
    """A fixture that provides the url of the local web server."""

    def _deb_get_fixture_server_url(repo_name=DEB_FIXTURE_STANDARD_REPOSITORY_NAME):
        """Generate the URL to the local data repository.

        :param repo_name: Name of the local data repository. Default /debian/.
        :returns: The URL of the local data repository.
        """
        return deb_fixture_server.make_url(repo_name)

    return _deb_get_fixture_server_url


@pytest.fixture
def deb_init_and_sync(
    apt_repository_api,
    deb_get_fixture_server_url,
    deb_repository_factory,
    deb_remote_factory,
    deb_sync_repository,
):
    """Initialize a new repository and remote and sync the content from the passed URL."""

    def _deb_init_and_sync(
        repository=None,
        remote=None,
        url=None,
        pulp_domain=None,
        remote_args={},
        repo_args={},
        sync_args={},
        return_task=False,
    ):
        """Initializes and syncs a repository and remote.

        :param repository: An existing repository. Default: None.
        :param remote: An existing remote. Default: None.
        :param url: The name of the data repository. Default: None -> /debian/.
        :param remote_args: Parameters for the remote creation. Default {}.
        :param repo_args: Parameters for the repository creation. Default {}.
        :param sync_args: Parameters for the sync API call. Default {}.
        :param return_task: Whether to include the sync task to the return value. Default: False.
        :returns: A tuple containing the repository and remote and optionally the sync task.
        """
        if url is None:
            url = deb_get_fixture_server_url()
        elif url.startswith("http"):
            url = url
        else:
            url = deb_get_fixture_server_url(url)
        if repository is None:
            repository = deb_repository_factory(pulp_domain=pulp_domain, **repo_args)
        if remote is None:
            remote = deb_remote_factory(url=url, pulp_domain=pulp_domain, **remote_args)

        task = deb_sync_repository(remote, repository, **sync_args)

        repository = apt_repository_api.read(repository.pulp_href)
        return (repository, remote) if not return_task else (repository, remote, task)

    return _deb_init_and_sync


@pytest.fixture
def deb_get_content_summary(apt_repository_versions_api):
    """A fixture that fetches the content summary from a repository."""

    def _deb_get_content_summary(repo, version_href=None):
        """Fetches the content summary from a given repository.

        :param repo: The repository where the content is fetched from.
        :param version_href: The repository version from where the content should be fetched from.
            Default: latest repository version.
        :returns: The content summary of the repository.
        """
        version_href = version_href or repo.latest_version_href
        if version_href is None:
            return {}
        return apt_repository_versions_api.read(version_href).content_summary

    return _deb_get_content_summary
