from pulp_smash.pulp3.bindings import monitor_task
from pulp_smash.pulp3.utils import gen_distribution, gen_repo
import pytest
import os
import stat

from pulp_smash.utils import execute_pulpcore_python, uuid4
from pulp_deb.tests.functional.utils import gen_deb_remote

from pulpcore.client.pulp_deb import (
    ApiClient,
    RepositorySyncURL,
    ContentPackagesApi,
    DebAptPublication,
    DebVerbatimPublication,
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


@pytest.fixture
def apt_package_api(apt_client):
    """Fixture for APT package API."""
    return ContentPackagesApi(apt_client)


@pytest.fixture
def deb_distribution_factory(apt_distribution_api, gen_object_with_cleanup):
    """Fixture that generates a deb distribution with cleanup from a given publication."""

    def _deb_distribution_factory(publication):
        body = gen_distribution()
        body["publication"] = publication.pulp_href
        return gen_object_with_cleanup(apt_distribution_api, body)

    return _deb_distribution_factory


@pytest.fixture
def deb_publication_factory(apt_publication_api, gen_object_with_cleanup):
    """Fixture that generates a deb publication with cleanup from a given repository."""

    def _deb_publication_factory(repo, **kwargs):
        publication_data = DebAptPublication(repository=repo.pulp_href, **kwargs)
        return gen_object_with_cleanup(apt_publication_api, publication_data)

    return _deb_publication_factory


@pytest.fixture
def deb_repository_factory(apt_repository_api, gen_object_with_cleanup):
    """Fixture that generates a deb repository with cleanup."""

    def _deb_repository_factory():
        return gen_object_with_cleanup(apt_repository_api, gen_repo())

    return _deb_repository_factory


@pytest.fixture
def deb_remote_factory(apt_remote_api, gen_object_with_cleanup):
    """Fixture that generates a deb remote with cleanup."""

    def _deb_remote_factory(**kwargs):
        return gen_object_with_cleanup(apt_remote_api, gen_deb_remote(**kwargs))

    return _deb_remote_factory


@pytest.fixture
def deb_remote_custom_data_factory(apt_remote_api, gen_object_with_cleanup):
    """Fixture that generates a deb remote with cleanup using custom data."""

    def _deb_remote_custom_data_factory(data):
        return gen_object_with_cleanup(apt_remote_api, data)

    return _deb_remote_custom_data_factory


@pytest.fixture
def deb_verbatim_publication_factory(apt_verbatim_publication_api, gen_object_with_cleanup):
    """Fixture that generates a deb verbatim publication with cleanup from a given repository."""

    def _deb_verbatim_publication_factory(repo, **kwargs):
        publication_data = DebVerbatimPublication(repository=repo.pulp_href, **kwargs)
        return gen_object_with_cleanup(apt_verbatim_publication_api, publication_data)

    return _deb_verbatim_publication_factory


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
def deb_delete_remote(apt_remote_api):
    """Fixture that will delete a deb remote."""

    def _deb_delete_remote(remote):
        response = apt_remote_api.delete(remote.pulp_href)
        return monitor_task(response.task)

    return _deb_delete_remote


@pytest.fixture
def deb_patch_remote(apt_remote_api):
    """Fixture that will partially update a deb remote."""

    def _deb_patch_remote(remote, content):
        response = apt_remote_api.partial_update(remote.pulp_href, content)
        return monitor_task(response.task)

    return _deb_patch_remote


@pytest.fixture
def deb_put_remote(apt_remote_api):
    """Fixture that will update a deb remote."""

    def _deb_put_remote(remote, content):
        response = apt_remote_api.update(remote.pulp_href, content)
        return monitor_task(response.task)

    return _deb_put_remote


@pytest.fixture
def deb_sync_repository(apt_repository_api):
    """Fixture that synchronizes a given repository with a given remote
    and returns the monitored task.
    """

    def _deb_sync_repository(remote, repo):
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
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


@pytest.fixture
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
