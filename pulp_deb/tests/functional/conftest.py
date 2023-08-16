from urllib.parse import urlsplit
from pathlib import Path
from uuid import uuid4
import pytest
import os
import stat
import subprocess

from pulp_deb.tests.functional.utils import gen_local_deb_remote, gen_distribution, gen_repo
from pulp_deb.tests.functional.constants import DEB_FIXTURE_STANDARD_REPOSITORY_NAME

from pulpcore.client.pulp_deb import (
    ApiClient,
    AptRepositorySyncURL,
    ContentGenericContentsApi,
    ContentPackagesApi,
    ContentPackageIndicesApi,
    ContentPackageReleaseComponentsApi,
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
    """Fixture for APT package indices API."""
    return ContentPackageIndicesApi(apt_client)


@pytest.fixture(scope="session")
def apt_package_release_components_api(apt_client):
    """Fixture for APT package release components API."""
    return ContentPackageReleaseComponentsApi(apt_client)


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
        """Create a deb distribution.

        :param publication: The publication the distribution is based on.
        :returns: The created distribution.
        """
        body = gen_distribution()
        body["publication"] = publication.pulp_href
        return gen_object_with_cleanup(apt_distribution_api, body)

    return _deb_distribution_factory


@pytest.fixture(scope="class")
def deb_generic_content_factory(apt_generic_content_api, gen_object_with_cleanup):
    """Fixture that generates deb generic content with cleanup."""

    def _deb_generic_content_factory(**kwargs):
        """Create deb generic content.

        :returns: The created generic content.
        """
        return gen_object_with_cleanup(apt_generic_content_api, **kwargs)

    return _deb_generic_content_factory


@pytest.fixture(scope="class")
def deb_package_factory(apt_package_api, gen_object_with_cleanup):
    """Fixture that generates deb package with cleanup."""

    def _deb_package_factory(**kwargs):
        """Create a deb package.

        :returns: The created package.
        """
        return gen_object_with_cleanup(apt_package_api, **kwargs)

    return _deb_package_factory


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


@pytest.fixture
def deb_publication_by_version_factory(apt_publication_api, gen_object_with_cleanup):
    """Fixture that generates a deb publication with cleanup from a given repository version."""

    def _deb_publication_by_version_factory(repo_version, **kwargs):
        """Create a deb publication from a given repository version.

        :param repo_version: The repository version the publication should be based on.
        :returns: The created publication.
        """
        publication_data = DebAptPublication(repository_version=repo_version, **kwargs)
        return gen_object_with_cleanup(apt_publication_api, publication_data)

    return _deb_publication_by_version_factory


@pytest.fixture
def deb_delete_publication(apt_publication_api):
    """Fixture that deletes a deb publication."""

    def _deb_delete_publication(publication):
        """Delete a given publication.

        :param publication: The publication that should be deleted.
        """
        apt_publication_api.delete(publication.pulp_href)

    return _deb_delete_publication


@pytest.fixture(scope="class")
def deb_repository_factory(apt_repository_api, gen_object_with_cleanup):
    """Fixture that generates a deb repository with cleanup."""

    def _deb_repository_factory(**kwargs):
        """Create a deb repository.

        :returns: The created repository.
        """
        return gen_object_with_cleanup(apt_repository_api, gen_repo(**kwargs))

    return _deb_repository_factory


@pytest.fixture
def deb_repository_get_versions(apt_repository_versions_api):
    """Fixture that lists the repository versions of a given repository href."""

    def _deb_repository_get_versions(repo_href):
        """Lists the repository versions of a given repository href.

        :param repo_href: The pulp_href of a repository.
        :returns: The versions that match the given href.
        """
        requests = apt_repository_versions_api.list(repo_href)
        versions = []
        for result in requests.results:
            versions.append(result.pulp_href)
        versions.sort(key=lambda version: int(urlsplit(version).path.split("/")[-2]))
        return versions

    return _deb_repository_get_versions


@pytest.fixture
def deb_modify_repository(apt_repository_api, monitor_task):
    """Fixture that modifies content in a deb repository."""

    def _deb_modify_repository(repo, body):
        """Modifies the content of a given repository.

        :param repo: The repository that should be modified.
        :param body: The content the repository should be updated with.
        :returns: The task of the modify operation.
        """
        task = apt_repository_api.modify(repo.pulp_href, body).task
        return monitor_task(task)

    return _deb_modify_repository


@pytest.fixture(scope="class")
def deb_remote_factory(apt_remote_api, gen_object_with_cleanup):
    """Fixture that generates a deb remote with cleanup."""

    def _deb_remote_factory(url, **kwargs):
        """Creats a remote from the given url.

        :param url: The name of the local data repository.
        :returns: The created remote.
        """
        return gen_object_with_cleanup(apt_remote_api, gen_local_deb_remote(url=str(url), **kwargs))

    return _deb_remote_factory


@pytest.fixture
def deb_delete_repository(apt_repository_api, monitor_task):
    """Fixture that deletes a deb repository."""

    def _deb_delete_repository(repo):
        """Delete a given repository.

        :param repo: The repository that should be deleted.
        :returns: The task of the delete operation.
        """
        response = apt_repository_api.delete(repo.pulp_href)
        return monitor_task(response.task)

    return _deb_delete_repository


@pytest.fixture(scope="class")
def deb_remote_custom_data_factory(apt_remote_api, gen_object_with_cleanup):
    """Fixture that generates a deb remote with cleanup using custom data."""

    def _deb_remote_custom_data_factory(data):
        """Create a remote with custom data.

        :param data: The custom data the remote should be created with.
        :returns: The created remote.
        """
        return gen_object_with_cleanup(apt_remote_api, data)

    return _deb_remote_custom_data_factory


@pytest.fixture(scope="class")
def deb_verbatim_publication_factory(apt_verbatim_publication_api, gen_object_with_cleanup):
    """Fixture that generates a deb verbatim publication with cleanup from a given repository."""

    def _deb_verbatim_publication_factory(repo, **kwargs):
        """Create a verbatim publication.

        :param repo: The repository the verbatim publication should be based on.
        :returns: The created verbatim publication.
        """
        publication_data = DebVerbatimPublication(repository=repo.pulp_href, **kwargs)
        return gen_object_with_cleanup(apt_verbatim_publication_api, publication_data)

    return _deb_verbatim_publication_factory


@pytest.fixture
def deb_verbatim_publication_by_version_factory(
    apt_verbatim_publication_api, gen_object_with_cleanup
):
    """Fixture that generates verbatim publication with cleanup from a given repository version."""

    def _deb_verbatim_publication_by_version_factory(repo_version, **kwargs):
        """Creates a deb verbatim publication from a given repository version.

        :param repo_version: The repository version the verbatim publication should be created on.
        :returns: The created verbatim publication.
        """
        publication_data = DebVerbatimPublication(repository_version=repo_version, **kwargs)
        return gen_object_with_cleanup(apt_verbatim_publication_api, publication_data)

    return _deb_verbatim_publication_by_version_factory


@pytest.fixture
def deb_get_repository_by_href(apt_repository_api):
    """Fixture that returns the deb repository of a given pulp_href."""

    def _deb_get_repository_by_href(href):
        """Read a deb repository by the given pulp_href.

        :param href: The pulp_href of the repository that should be read.
        :returns: The repository that matches the given pulp_href.
        """
        return apt_repository_api.read(href)

    return _deb_get_repository_by_href


@pytest.fixture
def deb_get_remote_by_href(apt_remote_api):
    """Fixture that returns the deb remote of a given pulp_href."""

    def _deb_get_remote_by_href(href):
        """Read a deb remote by the given pulp_href.

        :param href: The pulp_href of the remote that should be read.
        :returns: The remote that matches the given pulp_href.
        """
        return apt_remote_api.read(href)

    return _deb_get_remote_by_href


@pytest.fixture
def deb_get_remotes_by_name(apt_remote_api):
    """Fixture that returns the deb remotes of a given name."""

    def _deb_get_remotes_by_name(name):
        """List deb remotes by a given name.

        :param name: The name of the remote that should be listed.
        :returns: The list of the remote with the given name.
        """
        return apt_remote_api.list(name=name)

    return _deb_get_remotes_by_name


@pytest.fixture
def deb_delete_remote(apt_remote_api, monitor_task):
    """Fixture that will delete a deb remote."""

    def _deb_delete_remote(remote):
        """Delete a given remote.

        :param remote: The remote that should be deleted.
        :returns: The task of the delete operation.
        """
        response = apt_remote_api.delete(remote.pulp_href)
        return monitor_task(response.task)

    return _deb_delete_remote


@pytest.fixture
def deb_patch_remote(apt_remote_api, monitor_task):
    """Fixture that will partially update a deb remote."""

    def _deb_patch_remote(remote, content):
        """Patch a remote with given content.

        :param remote: The remote that needs patching.
        :param content: The content the remote should be patched with.
        :returns: The task of the patch operation.
        """
        response = apt_remote_api.partial_update(remote.pulp_href, content)
        return monitor_task(response.task)

    return _deb_patch_remote


@pytest.fixture
def deb_put_remote(apt_remote_api, monitor_task):
    """Fixture that will update a deb remote."""

    def _deb_put_remote(remote, content):
        """Update a remote with given content.

        :param remote: The remote that needs updating.
        :param content: The content the remote should be updated with.
        :returns: The task of the update operation.
        """
        response = apt_remote_api.update(remote.pulp_href, content)
        return monitor_task(response.task)

    return _deb_put_remote


@pytest.fixture
def deb_sync_repository(apt_repository_api, monitor_task):
    """Fixture that synchronizes a given repository with a given remote
    and returns the monitored task.
    """

    def _deb_sync_repository(remote, repo):
        """Sync a given remote and repository.

        :param remote: The remote where to sync from.
        :param repo: The repository that needs syncing.
        :returns: The task of the sync operation.
        """
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
    deb_signing_script_path,
    signing_gpg_metadata,
    signing_service_api_client,
):
    """A fixture for the debian signing service."""
    st = os.stat(deb_signing_script_path)
    os.chmod(deb_signing_script_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    gpg, fingerprint, keyid = signing_gpg_metadata
    service_name = str(uuid4())
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
    process = subprocess.run(cmd, capture_output=True)

    assert process.returncode == 0

    signing_service = signing_service_api_client.list(name=service_name).results[0]

    assert signing_service.pubkey_fingerprint == fingerprint
    assert signing_service.public_key == gpg.export_keys(keyid)

    yield signing_service

    cmd = (
        "from pulpcore.app.models import SigningService;"
        f"SigningService.objects.filter(name='{service_name}').delete()"
    )
    process = subprocess.run(["pulpcore-manager", "shell", "-c", cmd], capture_output=True)
    assert process.returncode == 0


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
def deb_get_content(apt_repository_versions_api):
    """A fixture that fetches the content from a repository."""

    def _deb_get_content(repo, version_href=None):
        """Fetches the content from a given repository.
        :param repo: The repository where the content is fetched from.
        :param version_href: The repository version from where the content should be fetched.
            Default: latest repository version.
        :returns: The content summary of the repository.
        """
        version_href = version_href or repo.latest_version_href
        if version_href is None:
            return {}
        return apt_repository_versions_api.read(version_href).content_summary

    return _deb_get_content


@pytest.fixture
def deb_get_present_content(deb_get_content):
    """A fixture that fetches the present content from a repository."""

    def _deb_get_present_content(repo, version_href=None):
        """Fetches the present content from a given repository.

        :param repo: The repository where the content is fetched from.
        :param version_href: The repository version from where the content is fetched freom.
        :returns: The present content of the repository.
        """
        return deb_get_content(repo, version_href).present

    return _deb_get_present_content


@pytest.fixture
def deb_get_added_content(deb_get_content):
    """A fixture that fetches the added content from a repository."""

    def _deb_get_added_content(repo, version_href=None):
        """Fetches the added content from a given repository.

        :param repo: The repository where the content is fetched from.
        :param version_href: The repository version from where the content is fetched freom.
        :returns: The added content of the repository.
        """
        return deb_get_content(repo, version_href).added

    return _deb_get_added_content


@pytest.fixture
def deb_get_removed_content(deb_get_content):
    """A fixture that fetches the removed content from a repository."""

    def _deb_get_removed_content(repo, version_href=None):
        """Fetches the removed content from a given repository.

        :param repo: The repository where the content is fetched from.
        :param version_href: The repository version from where the content is fetched freom.
        :returns: The removed content of the repository.
        """
        return deb_get_content(repo, version_href).removed

    return _deb_get_removed_content


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
        version_href = version_href or repo["latest_version_href"]
        if version_href is None:
            return {}
        return apt_repository_versions_api.read(version_href).content_summary

    return _deb_get_content_summary


@pytest.fixture
def deb_get_added_content_summary(deb_get_content_summary):
    """A fixture that fetches the added content summary from a repository version."""

    def _deb_get_added_content_summary(repo, version_href=None):
        """Fetches the added content summary from a given repository.

        :param repo: The repository where content is fetched from.
        :param version_href: The repository version from where content should be fetched from.
        :returns: The added content of the repository version.
        """
        content = deb_get_content_summary(repo, version_href).added
        for key in content:
            content[key] = content[key]["count"]
        return content

    return _deb_get_added_content_summary


@pytest.fixture
def deb_get_present_content_summary(deb_get_content_summary):
    """A fixture that fetches the present content summary from a repository version."""

    def _deb_get_present_content_summary(repo, version_href=None):
        """Fetches the present content summary from a given repository.

        :param repo: The repository where content is fetched from.
        :param version_href: The repository version from where content should be fetched from.
        :returns: The added content of the repository version.
        """
        content = deb_get_content_summary(repo, version_href).present
        for key in content:
            content[key] = content[key]["count"]
        return content

    return _deb_get_present_content_summary


@pytest.fixture
def deb_get_removed_content_summary(deb_get_content_summary):
    """A fixture that fetches the removed content summary from a repository version."""

    def _deb_get_removed_content_summary(repo, version_href=None):
        """Fetches the removed content from a given repository.

        :param repo: The repository where the content is fetched from.
        :param version_href: The repository version from where content should be fetched from.
        :returns: The removed content of the repository version.
        """
        content = deb_get_content_summary(repo, version_href).removed
        for key in content:
            content[key] = content[key]["count"]
        return content

    return _deb_get_removed_content_summary


@pytest.fixture
def deb_get_content_types(deb_get_present_content, request):
    """A fixture that fetches content by type."""

    def _deb_get_content_types(content_api_name, content_type, repo, version_href=None):
        """Lists the content of a given repository and repository version by type.

        :param content_api_name: The name of the api fixture of the desired content type.
        :param content_type: The name of the desired content type.
        :param repo: The repository where the content is fetched from.
        :param version_href: (Optional) The repository version of the content.
        :returns: List of the fetched content type.
        """
        api = request.getfixturevalue(content_api_name)
        content = deb_get_present_content(repo, version_href)
        if content_type not in content.keys():
            return {}
        content_hrefs = content[content_type]["href"]
        _, _, latest_version_href = content_hrefs.partition("?repository_version=")
        return api.list(repository_version=latest_version_href).results

    return _deb_get_content_types
