from pulp_smash.pulp3.bindings import monitor_task
from pulp_smash.pulp3.utils import gen_repo
import pytest
import os
import stat

from pulp_smash.utils import execute_pulpcore_python, uuid4
from pulp_deb.tests.functional.constants import DEB_FIXTURE_URL, DEB_FIXTURE_DISTRIBUTIONS
from pulp_deb.tests.functional.utils import gen_deb_remote

from pulpcore.client.pulp_deb import (
    ApiClient,
    AptRepositorySyncURL,
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
def deb_gen_repository(apt_repository_api, gen_object_with_cleanup):
    """Generates a semi-random repository with cleanup."""

    def _deb_gen_repository():
        return gen_object_with_cleanup(apt_repository_api, gen_repo())

    return _deb_gen_repository


@pytest.fixture
def deb_gen_remote(apt_remote_api, gen_object_with_cleanup):
    """Fixture that generates a remote with cleanup.

    Also allows for parameters to be set manually.
    """

    def _deb_gen_remote(url=DEB_FIXTURE_URL, distributions=DEB_FIXTURE_DISTRIBUTIONS, **kwargs):
        return gen_object_with_cleanup(
            apt_remote_api, gen_deb_remote(url=url, distributions=distributions, **kwargs)
        )

    return _deb_gen_remote


@pytest.fixture
def deb_sync_repository(apt_repository_api):
    """Fixture that synchronizes a given repository with a given remote
    and returns the monitored task.
    """

    def _deb_sync_repository(remote, repo):
        repository_sync_data = AptRepositorySyncURL(remote=remote.pulp_href)
        sync_response = apt_repository_api.sync(repo.pulp_href, repository_sync_data)
        return monitor_task(sync_response.task)

    return _deb_sync_repository


@pytest.fixture(scope="session")
def signing_script_filename(signing_gpg_homedir_path):
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
def apt_signing_service(
    cli_client,
    signing_gpg_metadata,
    signing_script_filename,
    signing_service_api_client,
):
    """A fixture for the debian signing service."""
    st = os.stat(signing_script_filename)
    os.chmod(signing_script_filename, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    gpg, fingerprint, keyid = signing_gpg_metadata

    service_name = uuid4()
    cmd = (
        "pulpcore-manager",
        "add-signing-service",
        service_name,
        signing_script_filename,
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
