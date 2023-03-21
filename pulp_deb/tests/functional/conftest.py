from urllib.parse import urlsplit
from pulp_smash.pulp3.utils import gen_distribution, gen_repo
from pathlib import Path
import pytest
import os
import stat

from pulp_deb.tests.functional.utils import gen_local_deb_remote
from pulp_smash.utils import execute_pulpcore_python, uuid4
from pulp_deb.tests.functional.constants import DEB_FIXTURE_STANDARD_REPOSITORY_NAME

from pulpcore.client.pulp_deb import (
    ApiClient,
    AptRepositorySyncURL,
    ContentGenericContentsApi,
    ContentPackagesApi,
    ContentPackageIndicesApi,
    ContentReleasesApi,
    ContentReleaseComponentsApi,
    ContentReleaseFilesApi,
    DebAptPublication,
    DebVerbatimPublication,
    DistributionsAptApi,
    PublicationsAptApi,
    PublicationsVerbatimApi,
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
def apt_repository_api(apt_client):
    """Fixture for APT repositories API."""
    return RepositoriesAptApi(apt_client)


@pytest.fixture(scope="session")
def apt_repository_versions_api(apt_client):
    """Fixture for APT repository versions API."""
    return RepositoriesAptVersionsApi(apt_client)


@pytest.fixture(scope="session")
def apt_release_file_api(apt_client):
    return ContentReleaseFilesApi(apt_client)


@pytest.fixture(scope="session")
def apt_remote_api(apt_client):
    """Fixture for APT remote API."""
    return RemotesAptApi(apt_client)


@pytest.fixture(scope="session")
def apt_package_indices_api(apt_client):
    return ContentPackageIndicesApi(apt_client)


@pytest.fixture(scope="session")
def apt_publication_api(apt_client):
    """Fixture for APT publication API."""
    return PublicationsAptApi(apt_client)


@pytest.fixture(scope="session")
def apt_verbatim_publication_api(apt_client):
    """Fixture for Verbatim publication API."""
    return PublicationsVerbatimApi(apt_client)


@pytest.fixture(scope="session")
def apt_distribution_api(apt_client):
    """Fixture for APT distribution API."""
    return DistributionsAptApi(apt_client)


@pytest.fixture(scope="session")
def apt_package_api(apt_client):
    """Fixture for APT package API."""
    return ContentPackagesApi(apt_client)


@pytest.fixture(scope="session")
def apt_release_api(apt_client):
    """Fixture for APT release API."""
    return ContentReleasesApi(apt_client)


@pytest.fixture(scope="session")
def apt_release_component_api(apt_client):
    """Fixture for APT release API."""
    return ContentReleaseComponentsApi(apt_client)


@pytest.fixture(scope="session")
def apt_generic_content_api(apt_client):
    """Fixture for APT generic content API."""
    return ContentGenericContentsApi(apt_client)


@pytest.fixture(scope="class")
def deb_distribution_factory(apt_distribution_api, gen_object_with_cleanup):
    """Fixture that generates a deb distribution with cleanup from a given publication."""

    def _deb_distribution_factory(publication):
        body = gen_distribution()
        body["publication"] = publication.pulp_href
        return gen_object_with_cleanup(apt_distribution_api, body)

    return _deb_distribution_factory


@pytest.fixture(scope="class")
def deb_generic_content_factory(apt_generic_content_api, gen_object_with_cleanup):
    """Fixture that generates deb generic content with cleanup."""

    def _deb_generic_content_factory(**kwargs):
        return gen_object_with_cleanup(apt_generic_content_api, **kwargs)

    return _deb_generic_content_factory


@pytest.fixture(scope="class")
def deb_package_factory(apt_package_api, gen_object_with_cleanup):
    """Fixture that generates deb package with cleanup."""

    def _deb_package_factory(**kwargs):
        return gen_object_with_cleanup(apt_package_api, **kwargs)

    return _deb_package_factory


@pytest.fixture(scope="class")
def deb_publication_factory(apt_publication_api, gen_object_with_cleanup):
    """Fixture that generates a deb publication with cleanup from a given repository."""

    def _deb_publication_factory(repo, **kwargs):
        publication_data = DebAptPublication(repository=repo.pulp_href, **kwargs)
        return gen_object_with_cleanup(apt_publication_api, publication_data)

    return _deb_publication_factory


@pytest.fixture
def deb_publication_by_version_factory(apt_publication_api, gen_object_with_cleanup):
    """Fixture that generates a deb publication with cleanup from a given repository version."""

    def _deb_publication_by_version_factory(repo_version, **kwargs):
        publication_data = DebAptPublication(repository_version=repo_version, **kwargs)
        return gen_object_with_cleanup(apt_publication_api, publication_data)

    return _deb_publication_by_version_factory


@pytest.fixture
def deb_delete_publication(apt_publication_api):
    """Fixture that deletes a deb publication."""

    def _deb_delete_publication(publication):
        apt_publication_api.delete(publication.pulp_href)

    return _deb_delete_publication


@pytest.fixture(scope="class")
def deb_repository_factory(apt_repository_api, gen_object_with_cleanup):
    """Fixture that generates a deb repository with cleanup."""

    def _deb_repository_factory(**kwargs):
        return gen_object_with_cleanup(apt_repository_api, gen_repo(**kwargs))

    return _deb_repository_factory


@pytest.fixture
def deb_repository_get_versions(apt_repository_versions_api):
    def _deb_repository_get_versions(repo_href):
        requests = apt_repository_versions_api.list(repo_href)
        versions = []
        for result in requests.results:
            versions.append(result.pulp_href)
        versions.sort(key=lambda version: int(urlsplit(version).path.split("/")[-2]))
        return versions

    return _deb_repository_get_versions


@pytest.fixture
def deb_modify_repository(apt_repository_api, monitor_task):
    def _deb_modify_repository(repo, body):
        task = apt_repository_api.modify(repo.pulp_href, body).task
        return monitor_task(task)

    return _deb_modify_repository


@pytest.fixture(scope="class")
def deb_remote_factory(apt_remote_api, gen_object_with_cleanup):
    """Fixture that generates a deb remote with cleanup."""

    def _deb_remote_factory(url, **kwargs):
        return gen_object_with_cleanup(apt_remote_api, gen_local_deb_remote(url=str(url), **kwargs))

    return _deb_remote_factory


@pytest.fixture
def deb_delete_repository(apt_repository_api):
    """Fixture that deletes a deb repository."""

    def _deb_delete_repository(repo):
        apt_repository_api.delete(repo.pulp_href)

    return _deb_delete_repository


@pytest.fixture(scope="class")
def deb_remote_custom_data_factory(apt_remote_api, gen_object_with_cleanup):
    """Fixture that generates a deb remote with cleanup using custom data."""

    def _deb_remote_custom_data_factory(data):
        return gen_object_with_cleanup(apt_remote_api, data)

    return _deb_remote_custom_data_factory


@pytest.fixture(scope="class")
def deb_verbatim_publication_factory(apt_verbatim_publication_api, gen_object_with_cleanup):
    """Fixture that generates a deb verbatim publication with cleanup from a given repository."""

    def _deb_verbatim_publication_factory(repo, **kwargs):
        publication_data = DebVerbatimPublication(repository=repo.pulp_href, **kwargs)
        return gen_object_with_cleanup(apt_verbatim_publication_api, publication_data)

    return _deb_verbatim_publication_factory


@pytest.fixture
def deb_verbatim_publication_by_version_factory(
    apt_verbatim_publication_api, gen_object_with_cleanup
):
    """Fixture that generates verbatim publication with cleanup from a given repository version."""

    def _deb_verbatim_publication_by_version_factory(repo_version, **kwargs):
        publication_data = DebVerbatimPublication(repository_version=repo_version, **kwargs)
        return gen_object_with_cleanup(apt_verbatim_publication_api, publication_data)

    return _deb_verbatim_publication_by_version_factory


@pytest.fixture
def deb_get_repository_by_href(apt_repository_api):
    """Fixture that returns the deb repository of a given pulp_href."""

    def _deb_get_repository_by_href(href):
        return apt_repository_api.read(href)

    return _deb_get_repository_by_href


@pytest.fixture
def deb_get_remote_by_href(apt_remote_api):
    """Fixture that returns the deb remote of a given pulp_href."""

    def _deb_get_remote_by_href(href):
        return apt_remote_api.read(href)

    return _deb_get_remote_by_href


@pytest.fixture
def deb_get_remotes_by_name(apt_remote_api):
    """Fixture that returns the deb remotes of a given name."""

    def _deb_get_remotes_by_name(name):
        return apt_remote_api.list(name=name)

    return _deb_get_remotes_by_name


@pytest.fixture
def deb_delete_remote(apt_remote_api, monitor_task):
    """Fixture that will delete a deb remote."""

    def _deb_delete_remote(remote):
        response = apt_remote_api.delete(remote.pulp_href)
        return monitor_task(response.task)

    return _deb_delete_remote


@pytest.fixture
def deb_patch_remote(apt_remote_api, monitor_task):
    """Fixture that will partially update a deb remote."""

    def _deb_patch_remote(remote, content):
        response = apt_remote_api.partial_update(remote.pulp_href, content)
        return monitor_task(response.task)

    return _deb_patch_remote


@pytest.fixture
def deb_put_remote(apt_remote_api, monitor_task):
    """Fixture that will update a deb remote."""

    def _deb_put_remote(remote, content):
        response = apt_remote_api.update(remote.pulp_href, content)
        return monitor_task(response.task)

    return _deb_put_remote


@pytest.fixture
def deb_sync_repository(apt_repository_api, monitor_task):
    """Fixture that synchronizes a given repository with a given remote
    and returns the monitored task.
    """

    def _deb_sync_repository(remote, repo):
        repository_sync_data = AptRepositorySyncURL(remote=remote.pulp_href)
        sync_response = apt_repository_api.sync(repo.pulp_href, repository_sync_data)
        return monitor_task(sync_response.task)

    return _deb_sync_repository


@pytest.fixture(scope="session")
def deb_signing_script_path(signing_gpg_homedir_path):
    """A fixture for a script that is suited for signing packages."""
    dir_path = os.path.dirname(__file__)
    file_path = os.path.join(dir_path, "sign_deb_release.sh")

    with open(file_path) as fp:
        lines = [line.rstrip() for line in fp]
        # For the test environment the GNUPGHOME environment variable
        # needs to be part of the script. Otherwise the test containers
        # will not find the right gpg key.
        lines = lines[0:3] + [f'export GNUPGHOME="{signing_gpg_homedir_path}"'] + lines[3:]

    raw_script = tuple(line for line in lines)

    with open(os.path.join(signing_gpg_homedir_path, "bash-script.sh"), "w") as f:
        f.write("\n".join(raw_script))

    return f.name


@pytest.fixture(scope="class")
def deb_signing_service_factory(
    cli_client,
    deb_signing_script_path,
    signing_gpg_metadata,
    signing_service_api_client,
):
    """A fixture for the debian signing service."""
    st = os.stat(deb_signing_script_path)
    os.chmod(deb_signing_script_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    gpg, fingerprint, keyid = signing_gpg_metadata
    service_name = uuid4()
    cmd = (
        "pulpcore-manager",
        "add-signing-service",
        service_name,
        deb_signing_script_path,
        keyid,
        "--class",
        "deb:AptReleaseSigningService",
        "--gnupghome",
        gpg.gnupghome,
    )
    response = cli_client.run(cmd)

    assert response.returncode == 0

    signing_service = signing_service_api_client.list(name=service_name).results[0]

    assert signing_service.pubkey_fingerprint == fingerprint
    assert signing_service.public_key == gpg.export_keys(keyid)

    yield signing_service

    cmd = (
        "from pulpcore.app.models import SigningService;"
        f"SigningService.objects.filter(name='{service_name}').delete()"
    )
    execute_pulpcore_python(cli_client, cmd)


@pytest.fixture
def deb_fixture_server(gen_fixture_server):
    """A fixture that spins up a local web server to serve test data."""
    p = Path(__file__).parent.absolute()
    fixture_path = p.joinpath("data/")
    yield gen_fixture_server(fixture_path, None)


@pytest.fixture
def deb_get_fixture_server_url(deb_fixture_server):
    """A fixture that provides the url of the local web server."""

    def _deb_get_fixture_server_url(repo_name=DEB_FIXTURE_STANDARD_REPOSITORY_NAME):
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
        repository=None, remote=None, url=None, remote_args={}, repo_args={}, return_task=False
    ):
        """Initializes and syncs a repository and remote.

        :param repository: An existing repository. Default: None.
        :param remote: An existing remote. Default: None.
        :param url: The name of the data repository. Default: None -> /debian/.
        :param remote_args: Parameters for the remote creation. Default {}.
        :param repo_args: Parameters for the repository creation. Default {}.
        :param return_task: Whether to include the sync task to the return value. Default: False.
        :returns: A tuple containing the repository and remote and optionally the sync task.
        """
        url = deb_get_fixture_server_url() if url is None else deb_get_fixture_server_url(url)
        if repository is None:
            repository = deb_repository_factory(**repo_args)
        if remote is None:
            remote = deb_remote_factory(url=url, **remote_args)

        task = deb_sync_repository(remote, repository)

        repository = apt_repository_api.read(repository.pulp_href)
        return (repository, remote) if not return_task else (repository, remote, task)

    return _deb_init_and_sync


@pytest.fixture
def deb_get_present_content(apt_repository_versions_api):
    """A fixture that fetches the present content from a repository."""

    def _deb_get_present_content(repo, version_href=None):
        """Fetches the present content from a given repository.

        :param repo: The repository where the content is fetched from.
        :param version_href: The repository version from where the content should be fetched.
            Default: latest repository version.
        :returns: The present content summary of the repository.
        """
        version_href = version_href or repo.latest_version_href
        if version_href is None:
            return {}
        return apt_repository_versions_api.read(version_href).content_summary.present

    return _deb_get_present_content


@pytest.fixture
def deb_list_content_types_by_href(request):
    """A fixture that lists content of a given type by given href."""

    def _deb_list_content_types_by_href(content_type, content_href):
        """Lists the content of a given type.

        :param content_type: The fixture name of the content type api.
        :param content_href: The type href string from the content summary.
        :returns: The results of the content list.
        """
        api = request.getfixturevalue(content_type)
        _, _, latest_version_href = content_href.partition("?repository_version=")
        return api.list(repository_version=latest_version_href).results

    return _deb_list_content_types_by_href
