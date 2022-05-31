import pytest

from pulpcore.client.pulp_deb import (
    ApiClient,
    DistributionsAptApi,
    PublicationsAptApi,
    PublicationsVerbatimApi,
    RemotesAptApi,
    RepositoriesAptApi,
)


@pytest.fixture
def apt_client(cid, bindings_cfg):
    """Fixture for APT client."""
    api_client = ApiClient(bindings_cfg)
    api_client.default_headers["Correlation-ID"] = cid
    return api_client


@pytest.fixture
def apt_repository_api(apt_client):
    """Fixture for APT repositories API."""
    return RepositoriesAptApi(apt_client)


@pytest.fixture
def apt_remote_api(apt_client):
    """Fixture for APT remote API."""
    return RemotesAptApi(apt_client)


@pytest.fixture
def apt_publication_api(apt_client):
    """Fixture for APT publication API."""
    return PublicationsAptApi(apt_client)


@pytest.fixture
def apt_verbatim_publication_api(apt_client):
    """Fixture for Verbatim publication API."""
    return PublicationsVerbatimApi(apt_client)


@pytest.fixture
def apt_distribution_api(apt_client):
    """Fixture for APT distribution API."""
    return DistributionsAptApi(apt_client)
