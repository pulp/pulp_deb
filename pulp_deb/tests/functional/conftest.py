import json
from urllib.parse import urlsplit
from uuid import uuid4
import pytest
import os
import re
import stat
import subprocess
import uuid

from pulp_deb.tests.functional.constants import (
    DEB_SIGNING_SCRIPT_STRING,
    DEB_PACKAGE_SIGNING_SCRIPT_STRING,
)
from pulpcore.client.pulp_deb import (
    ContentGenericContentsApi,
    ContentPackagesApi,
    ContentPackageIndicesApi,
    ContentPackageReleaseComponentsApi,
    ContentReleasesApi,
    ContentReleaseArchitecturesApi,
    ContentReleaseComponentsApi,
    ContentReleaseFilesApi,
    ContentSourcePackagesApi,
    ContentSourceReleaseComponentsApi,
    Copy,
    AcsDebApi,
    DebAptPublication,
    DebAptAlternateContentSource,
    DebCopyApi,
    DebRelease,
    DebReleaseArchitecture,
    DebReleaseComponent,
    DebSourcePackageReleaseComponent,
    DebVerbatimPublication,
    PublicationsVerbatimApi,
)

from pulp_deb.tests.functional.utils import gen_deb_remote, gen_repo


@pytest.fixture(scope="session")
def apt_release_file_api(apt_client):
    return ContentReleaseFilesApi(apt_client)


@pytest.fixture(scope="session")
def apt_acs_api(apt_client):
    """Fixture for APT alternate content source API."""
    return AcsDebApi(apt_client)


@pytest.fixture(scope="session")
def apt_package_indices_api(apt_client):
    """Fixture for APT package indices API."""
    return ContentPackageIndicesApi(apt_client)


@pytest.fixture(scope="session")
def apt_package_release_components_api(apt_client):
    """Fixture for APT package release components API."""
    return ContentPackageReleaseComponentsApi(apt_client)


@pytest.fixture(scope="session")
def apt_source_release_components_api(apt_client):
    """Fixture for APT source package release components API."""
    return ContentSourceReleaseComponentsApi(apt_client)


@pytest.fixture(scope="session")
def apt_verbatim_publication_api(apt_client):
    """Fixture for Verbatim publication API."""
    return PublicationsVerbatimApi(apt_client)


@pytest.fixture(scope="session")
def apt_copy_api(apt_client):
    """Fixture for APT copy api."""
    return DebCopyApi(apt_client)


@pytest.fixture(scope="session")
def apt_package_api(apt_client):
    """Fixture for APT package API."""
    return ContentPackagesApi(apt_client)


@pytest.fixture(scope="session")
def apt_source_package_api(apt_client):
    """Fixture for APT source package API."""
    return ContentSourcePackagesApi(apt_client)


@pytest.fixture(scope="session")
def apt_release_api(apt_client):
    """Fixture for APT release API."""
    return ContentReleasesApi(apt_client)


@pytest.fixture(scope="session")
def apt_release_architecture_api(apt_client):
    """Fixture for APT release architecture API."""
    return ContentReleaseArchitecturesApi(apt_client)


@pytest.fixture(scope="session")
def apt_release_component_api(apt_client):
    """Fixture for APT release component API."""
    return ContentReleaseComponentsApi(apt_client)


@pytest.fixture(scope="session")
def apt_generic_content_api(apt_client):
    """Fixture for APT generic content API."""
    return ContentGenericContentsApi(apt_client)


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
def deb_source_package_factory(apt_source_package_api, gen_object_with_cleanup):
    """Fixture that generates deb source package with cleanup."""

    def _deb_source_package_factory(**kwargs):
        """Create a deb source package.

        :returns: The created source package.
        """
        return gen_object_with_cleanup(apt_source_package_api, deb_source_package=kwargs)

    return _deb_source_package_factory


@pytest.fixture(scope="class")
def deb_source_release_component_factory(
    apt_source_release_components_api, gen_object_with_cleanup
):
    """Fixture that generates source release comopnent with cleanup."""

    def _deb_source_release_component_factory(source_package, release_component, **kwargs):
        """Create an APT SourceReleaseComponent.

        :returns: The created SourceReleaseComponent.
        """
        source_release_component_object = DebSourcePackageReleaseComponent(
            source_package=source_package, release_component=release_component, **kwargs
        )
        return gen_object_with_cleanup(
            apt_source_release_components_api, source_release_component_object
        )

    return _deb_source_release_component_factory


@pytest.fixture(scope="class")
def deb_release_factory(apt_release_api, gen_object_with_cleanup):
    """Fixture that generates deb release with cleanup."""

    def _deb_release_factory(codename, suite, distribution, **kwargs):
        """Create a deb release.

        :returns: The created release.
        """
        release_object = DebRelease(
            codename=codename, suite=suite, distribution=distribution, **kwargs
        )
        return gen_object_with_cleanup(apt_release_api, release_object)

    return _deb_release_factory


@pytest.fixture(scope="class")
def deb_release_component_factory(apt_release_component_api, gen_object_with_cleanup):
    """Fixture that generates deb package with cleanup."""

    def _deb_release_component_factory(component, distribution, **kwargs):
        """Create an APT ReleaseComponent.

        :returns: The created ReleaseComponent.
        """
        release_component_object = DebReleaseComponent(
            component=component, distribution=distribution, **kwargs
        )
        return gen_object_with_cleanup(apt_release_component_api, release_component_object)

    return _deb_release_component_factory


@pytest.fixture(scope="class")
def deb_release_architecture_factory(apt_release_architecture_api, gen_object_with_cleanup):
    """Fixture that generates deb package with cleanup."""

    def _deb_release_architecture_factory(architecture, distribution, **kwargs):
        """Create an APT ReleaseArchitecture.

        :returns: The created ReleaseArchitecture.
        """
        release_architecture_object = DebReleaseArchitecture(
            architecture=architecture, distribution=distribution, **kwargs
        )
        return gen_object_with_cleanup(apt_release_architecture_api, release_architecture_object)

    return _deb_release_architecture_factory


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


@pytest.fixture(scope="class")
def deb_acs_factory(apt_acs_api, gen_object_with_cleanup):
    def _deb_acs_factory(**kwargs):
        body = DebAptAlternateContentSource(**kwargs)
        return gen_object_with_cleanup(apt_acs_api, body)

    return _deb_acs_factory


@pytest.fixture(scope="class")
def deb_copy_content(apt_copy_api, monitor_task):
    """Fixture that copies deb content from a source repository version to a target repository."""

    def _deb_copy_content(source_repo_version, dest_repo, content=None, structured=True):
        """Copy deb content from a source repository version to a target repository.

        :param source_repo_version: The repository version href from where the content is copied.
        :dest_repo: The repository href where the content should be copied to.
        :content: List of package hrefs that should be copied from the source. Default: None
        :structured: Whether or not the content should be structured copied. Default: True
        :returns: The task of the copy operation.
        """
        config = {"source_repo_version": source_repo_version, "dest_repo": dest_repo}
        if content is not None:
            config["content"] = content
        data = Copy(config=[config], structured=structured)
        response = apt_copy_api.copy_content(data)
        return monitor_task(response.task)

    return _deb_copy_content


@pytest.fixture(scope="class")
def deb_copy_content_domain(apt_copy_api, monitor_task):
    """
    Fixture that copies deb content from a source repository version
    to a target repository using domains.
    """

    def _deb_copy_content_domain(
        source_repo_version, dest_repo, domain_name, content=None, structured=True
    ):
        """Copy deb content from a source repository version to a target repository in a domain.

        :param source_repo_version: The repository version href from where the content is copied.
        :dest_repo: The repository href where the content should be copied to.
        :domain_name: The name of the domain where copy should take place.
        :content: List of packages hrefs that should be copied from the source. Default: None
        :structured: Whether or not the content should be structured copied. Default: True
        :returns: The task of the copy operation.
        """
        config = {"source_repo_version": source_repo_version, "dest_repo": dest_repo}
        if content is not None:
            config["content"] = content
        data = Copy(config=[config], structured=structured)
        response = apt_copy_api.copy_content(data, pulp_domain=domain_name)
        return monitor_task(response.task)

    return _deb_copy_content_domain


@pytest.fixture(scope="session")
def deb_signing_script_path(
    signing_script_temp_dir, signing_gpg_homedir_path, signing_gpg_metadata
):
    _, _, keyid = signing_gpg_metadata
    """A fixture that provides a signing script path for signing debian packages."""
    signing_script_filename = signing_script_temp_dir / "sign_deb_release.sh"
    rep = {"HOMEDIRHERE": str(signing_gpg_homedir_path), "GPGKEYIDHERE": str(keyid)}
    rep = dict((re.escape(k), v) for k, v in rep.items())
    pattern = re.compile("|".join(rep.keys()))
    with open(signing_script_filename, "w", 0o770) as sign_metadata_file:
        sign_metadata_file.write(
            pattern.sub(lambda m: rep[re.escape(m.group(0))], DEB_SIGNING_SCRIPT_STRING)
        )

    st = os.stat(signing_script_filename)
    os.chmod(signing_script_filename, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return signing_script_filename


@pytest.fixture(scope="session")
def deb_signing_service_factory(
    deb_signing_script_path,
    signing_gpg_metadata,
    signing_gpg_homedir_path,
    pulpcore_bindings,
):
    """A fixture for the debian signing service."""
    gpg, fingerprint, keyid = signing_gpg_metadata
    service_name = str(uuid4())
    cmd = (
        "pulpcore-manager",
        "add-signing-service",
        service_name,
        str(deb_signing_script_path),
        fingerprint,
        "--class",
        "deb:AptReleaseSigningService",
        "--gnupghome",
        str(gpg.gnupghome),
    )
    process = subprocess.run(cmd, capture_output=True)

    assert process.returncode == 0

    signing_service = pulpcore_bindings.SigningServicesApi.list(name=service_name).results[0]

    assert signing_service.pubkey_fingerprint == fingerprint
    assert signing_service.public_key == gpg.export_keys(keyid)

    yield signing_service

    cmd = (
        "pulpcore-manager",
        "remove-signing-service",
        service_name,
        "--class",
        "deb:AptReleaseSigningService",
    )
    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.returncode == 0


@pytest.fixture
def deb_get_content_types(deb_get_content_summary, request):
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
        content = deb_get_content_summary(repo, version_href).present
        if content_type not in content.keys():
            return {}
        content_hrefs = content[content_type]["href"]
        _, _, latest_version_href = content_hrefs.partition("?repository_version=")
        return api.list(repository_version=latest_version_href).results

    return _deb_get_content_types


@pytest.fixture
def deb_setup_domain(
    gen_object_with_cleanup,
    apt_remote_api,
    apt_repository_api,
    deb_get_fixture_server_url,
    deb_sync_repository,
    deb_domain_factory,
):
    def _deb_setup_domain(sync=True, pulp_domain=None, url=None):
        if url is None:
            url = deb_get_fixture_server_url()
        elif url.startswith("http"):
            url = url
        else:
            url = deb_get_fixture_server_url(url)

        if not pulp_domain:
            pulp_domain = deb_domain_factory()

        remote = gen_object_with_cleanup(
            apt_remote_api, gen_deb_remote(url=str(url)), pulp_domain=pulp_domain.name
        )
        src = gen_object_with_cleanup(apt_repository_api, gen_repo(), pulp_domain=pulp_domain.name)

        if sync:
            deb_sync_repository(remote=remote, repo=src)
            src = apt_repository_api.read(src.pulp_href)

        dest = gen_object_with_cleanup(apt_repository_api, gen_repo(), pulp_domain=pulp_domain.name)
        return pulp_domain, remote, src, dest

    return _deb_setup_domain


@pytest.fixture
def deb_cleanup_domains(pulpcore_bindings, monitor_task, apt_repository_api):
    def _deb_cleanup_domains(
        domains,
        content_api_client=None,
        cleanup_repositories=False,
        repository_api_client=apt_repository_api,
    ):
        for domain in domains:
            # clean up each domain specified
            if domain:
                if cleanup_repositories:
                    # delete repos from the domain
                    for repo in repository_api_client.list(pulp_domain=domain.name).results:
                        monitor_task(repository_api_client.delete(repo.pulp_href).task)
                # let orphan cleanup reap the resulting abandoned content
                monitor_task(
                    pulpcore_bindings.OrphansCleanupApi.cleanup(
                        {"orphan_protection_time": 0}, pulp_domain=domain.name
                    ).task
                )

        if content_api_client:
            # if we have a client, check that each domain is empty of that kind-of entity
            for domain in domains:
                if domain:
                    assert content_api_client.list(pulp_domain=domain.name).count == 0

    return _deb_cleanup_domains


@pytest.fixture
def deb_domain_factory(pulpcore_bindings, gen_object_with_cleanup):
    """Fixture to create a domain."""

    def _deb_domain_factory(name=None):
        name = str(uuid.uuid4()) if name is None else name
        body = {
            "name": name,
            "storage_class": "pulpcore.app.models.storage.FileSystem",
            "storage_settings": {"MEDIA_ROOT": "/var/lib/pulp/media/"},
        }
        return gen_object_with_cleanup(pulpcore_bindings.DomainsApi, body)

    return _deb_domain_factory


@pytest.fixture(scope="session")
def package_signing_script_path(signing_script_temp_dir, signing_gpg_homedir_path):
    signing_script_file = signing_script_temp_dir / "sign-deb-package.sh"
    signing_script_file.write_text(
        DEB_PACKAGE_SIGNING_SCRIPT_STRING.replace("HOMEDIRHERE", str(signing_gpg_homedir_path))
    )

    signing_script_file.chmod(0o755)

    return signing_script_file


@pytest.fixture(scope="session")
def signing_script_temp_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("sigining_script_dir")


@pytest.fixture(scope="session")
def signing_gpg_homedir_path(tmp_path_factory):
    return tmp_path_factory.mktemp("gpghome")


@pytest.fixture
def sign_with_deb_package_signing_service(package_signing_script_path, signing_gpg_metadata):
    """
    Runs the test signing script manually, locally, and returns the signature file produced.
    """

    def _sign_with_deb_package_signing_service(filename):
        env = {"PULP_SIGNING_KEY_FINGERPRINT": signing_gpg_metadata[1]}
        cmd = (package_signing_script_path, filename)
        completed_process = subprocess.run(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if completed_process.returncode != 0:
            raise RuntimeError(str(completed_process.stderr))

        try:
            return_value = json.loads(completed_process.stdout)
        except json.JSONDecodeError:
            raise RuntimeError("The signing script did not return valid JSON!")

        return return_value

    return _sign_with_deb_package_signing_service


@pytest.fixture(scope="session")
def _deb_package_signing_service_name(
    bindings_cfg,
    package_signing_script_path,
    signing_gpg_metadata,
    signing_gpg_homedir_path,
    pytestconfig,
):
    service_name = str(uuid.uuid4())
    gpg, fingerprint, keyid = signing_gpg_metadata

    cmd = (
        "pulpcore-manager",
        "add-signing-service",
        service_name,
        str(package_signing_script_path),
        fingerprint,
        "--class",
        "deb:AptPackageSigningService",
        "--gnupghome",
        str(signing_gpg_homedir_path),
    )
    completed_process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert completed_process.returncode == 0

    yield service_name

    cmd = (
        "pulpcore-manager",
        "remove-signing-service",
        service_name,
        "--class",
        "deb:AptPackageSigningService",
    )
    subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


@pytest.fixture
def deb_package_signing_service(_deb_package_signing_service_name, pulpcore_bindings):
    return pulpcore_bindings.SigningServicesApi.list(
        name=_deb_package_signing_service_name
    ).results[0]
