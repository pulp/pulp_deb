import hashlib
import shutil
import subprocess
import uuid

import pytest

from pulpcore.client.pulp_deb.exceptions import ApiException

from pulp_deb.app.models import AptPackageSigningService
from pulp_deb.tests.functional.utils import get_local_package_absolute_path


@pytest.mark.parallel
def test_register_deb_package_signing_service(deb_package_signing_service):
    """
    Register a sample deb signing service and validate it works.
    """
    service = deb_package_signing_service
    assert "/api/v3/signing-services/" in service.pulp_href


@pytest.fixture
def add_package_to_repo(
    deb_modify_repository,
    deb_release_component_factory,
    deb_package_release_component_factory,
    monitor_task,
):
    def _add_package_to_repo(
        repository,
        package,
        release_component=None,
        prc=None,
    ):
        if not release_component:
            release_component = deb_release_component_factory(
                distribution=str(uuid.uuid4()), component="main"
            ).pulp_href
        if not prc:
            prc = deb_package_release_component_factory(
                package=package,
                release_component=release_component,
            ).pulp_href
        task = deb_modify_repository(
            repository,
            {
                "add_content_units": [
                    package,
                    release_component,
                    prc,
                ]
            },
        )
        monitor_task(task.pulp_href)
        return release_component, prc

    return _add_package_to_repo


@pytest.mark.parallel
def test_sign_package_on_upload(
    tmp_path,
    download_content_unit,
    deb_signing_key_primary,
    deb_signing_key_secondary,
    deb_package_signing_service,
    deb_package_factory,
    deb_repository_factory,
    deb_release_factory,
    deb_publication_factory,
    deb_distribution_factory,
):
    """
    Sign an Deb Package with the Package Upload endpoint.

    This ensures different
    """
    # Setup gpg and package to upload
    combined_public_key = deb_signing_key_primary.public_key + deb_signing_key_secondary.public_key
    fingerprint_set = {deb_signing_key_primary.fingerprint, deb_signing_key_secondary.fingerprint}
    assert len(fingerprint_set) == 2

    file_to_upload = shutil.copy(
        get_local_package_absolute_path("frigg_1.0_ppc64.deb"),
        tmp_path,
    )
    with pytest.raises(Exception, match=".*Package is unsigned.*"):
        AptPackageSigningService._check_deb_signature(
            file_to_upload,
            deb_signing_key_primary.fingerprint,
            str(tmp_path),
            combined_public_key,
        )

    # Upload Package to Repository
    # The same file is uploaded, but signed with different keys each time
    for fingerprint in fingerprint_set:
        repository = deb_repository_factory(
            package_signing_service=deb_package_signing_service.pulp_href,
            package_signing_fingerprint=fingerprint,
        )
        # create release
        deb_package_factory(
            file=file_to_upload,
            repository=repository.pulp_href,
        )

        # Verify that the final served package is signed
        publication = deb_publication_factory(repository)
        distribution = deb_distribution_factory(publication=publication)
        downloaded_package = tmp_path / "package.deb"
        downloaded_package.write_bytes(
            download_content_unit(distribution.base_path, "pool/upload/f/frigg/frigg_1.0_ppc64.deb")
        )
        AptPackageSigningService._check_deb_signature(
            str(downloaded_package), fingerprint, str(tmp_path), combined_public_key
        )

    # Test release override
    repository = deb_repository_factory(
        package_signing_service=deb_package_signing_service.pulp_href,
        package_signing_fingerprint=deb_signing_key_primary.fingerprint,
        package_signing_fingerprint_release_overrides={
            "test": deb_signing_key_secondary.fingerprint,
        },
    )

    deb_release_factory("test", "test", "test", repository=repository.pulp_href)
    deb_release_factory("test2", "test2", "test2", repository=repository.pulp_href)

    deb_package_factory(
        file=file_to_upload,
        repository=repository.pulp_href,
        distribution="test",
    )

    # Verify that the final served package is signed
    publication = deb_publication_factory(repository)
    distribution = deb_distribution_factory(publication=publication)
    downloaded_package = tmp_path / "package.deb"
    downloaded_package.write_bytes(
        download_content_unit(distribution.base_path, "pool/upload/f/frigg/frigg_1.0_ppc64.deb")
    )
    AptPackageSigningService._check_deb_signature(
        str(downloaded_package),
        deb_signing_key_secondary.fingerprint,
        str(tmp_path),
        combined_public_key,
    )


@pytest.fixture
def pulpcore_chunked_file_factory(tmp_path):
    """Returns a function to create chunks from file to be uploaded."""

    def _create_chunks(upload_path, chunk_size=512):
        """Chunks file to be uploaded."""
        chunks = {"chunks": []}
        hasher = hashlib.new("sha256")
        start = 0
        with open(upload_path, "rb") as f:
            data = f.read()
        chunks["size"] = len(data)

        while start < len(data):
            content = data[start : start + chunk_size]
            chunk_file = tmp_path / str(uuid.uuid4())
            hasher.update(content)
            chunk_file.write_bytes(content)
            content_sha = hashlib.sha256(content).hexdigest()
            end = start + len(content) - 1
            chunks["chunks"].append(
                (str(chunk_file), f"bytes {start}-{end}/{chunks['size']}", content_sha)
            )
            start += len(content)
        chunks["digest"] = hasher.hexdigest()
        return chunks

    return _create_chunks


@pytest.fixture
def pulpcore_upload_chunks(
    pulpcore_bindings,
    gen_object_with_cleanup,
    monitor_task,
):
    """Upload file in chunks."""

    def _upload_chunks(size, chunks, sha256, include_chunk_sha256=False):
        """
        Chunks is a list of tuples in the form of (chunk_filename, "bytes-ranges", optional_sha256).
        """
        upload = gen_object_with_cleanup(pulpcore_bindings.UploadsApi, {"size": size})

        for data in chunks:
            kwargs = {"file": data[0], "content_range": data[1], "upload_href": upload.pulp_href}
            if include_chunk_sha256:
                if len(data) != 3:
                    raise Exception(f"Chunk didn't include its sha256: {data}")
                kwargs["sha256"] = data[2]

            pulpcore_bindings.UploadsApi.update(**kwargs)

        return upload

    yield _upload_chunks


def test_sign_chunked_package_on_upload(
    tmp_path,
    download_content_unit,
    deb_signing_key_primary,
    deb_signing_key_secondary,
    deb_package_signing_service,
    deb_package_factory,
    deb_repository_factory,
    deb_publication_factory,
    deb_distribution_factory,
    pulpcore_upload_chunks,
    pulpcore_chunked_file_factory,
):
    """
    Sign an Deb Package with the Package Upload endpoint.

    This ensures different
    """
    combined_public_key = deb_signing_key_primary.public_key + deb_signing_key_secondary.public_key
    fingerprint_set = {deb_signing_key_primary.fingerprint, deb_signing_key_secondary.fingerprint}
    assert len(fingerprint_set) == 2

    file_to_upload = shutil.copy(
        get_local_package_absolute_path("frigg_1.0_ppc64.deb"),
        tmp_path,
    )
    with pytest.raises(Exception, match=".*Package is unsigned.*"):
        AptPackageSigningService._check_deb_signature(
            file_to_upload,
            deb_signing_key_primary.fingerprint,
            str(tmp_path),
            combined_public_key,
        )

    # Upload Package to Repository
    # The same file is uploaded, but signed with different keys each time
    for fingerprint in fingerprint_set:
        repository = deb_repository_factory(
            package_signing_service=deb_package_signing_service.pulp_href,
            package_signing_fingerprint=fingerprint,
        )
        file_chunks_data = pulpcore_chunked_file_factory(file_to_upload)
        size = file_chunks_data["size"]
        chunks = file_chunks_data["chunks"]
        sha256 = file_chunks_data["digest"]
        upload = pulpcore_upload_chunks(size, chunks, sha256, include_chunk_sha256=True)
        # create release
        deb_package_factory(
            upload=upload.pulp_href,
            repository=repository.pulp_href,
        )

        # Verify that the final served package is signed
        publication = deb_publication_factory(repository)
        distribution = deb_distribution_factory(publication=publication)
        downloaded_package = tmp_path / "package.deb"
        downloaded_package.write_bytes(
            download_content_unit(distribution.base_path, "pool/upload/f/frigg/frigg_1.0_ppc64.deb")
        )
        AptPackageSigningService._check_deb_signature(
            str(downloaded_package), fingerprint, str(tmp_path), combined_public_key
        )


def test_signed_repo_modify(
    tmp_path,
    add_package_to_repo,
    download_content_unit,
    deb_signing_key_primary,
    deb_package_signing_service,
    deb_repository_factory,
    deb_package_factory,
    deb_publication_factory,
    deb_distribution_factory,
    apt_repository_api,
    apt_package_api,
):
    """Ensure packages added via modify are signed before distribution."""
    fingerprint = deb_signing_key_primary.fingerprint
    public_key = deb_signing_key_primary.public_key

    file_to_upload = shutil.copy(
        get_local_package_absolute_path("frigg_1.0_ppc64.deb"),
        tmp_path,
    )
    with pytest.raises(Exception, match=".*Package is unsigned.*"):
        AptPackageSigningService._check_deb_signature(
            file_to_upload, fingerprint, str(tmp_path), public_key
        )

    repository = deb_repository_factory(
        package_signing_service=deb_package_signing_service.pulp_href,
        package_signing_fingerprint=fingerprint,
    )

    created_package = deb_package_factory(file=file_to_upload)
    assert created_package.signing_keys is None
    release_component, prc = add_package_to_repo(repository, created_package.pulp_href)

    # Verify that the final served package is signed
    publication = deb_publication_factory(repository)
    distribution = deb_distribution_factory(publication=publication)
    downloaded_package = tmp_path / "package.deb"
    downloaded_package.write_bytes(
        download_content_unit(distribution.base_path, "pool/main/f/frigg/frigg_1.0_ppc64.deb")
    )
    AptPackageSigningService._check_deb_signature(
        str(downloaded_package), fingerprint, str(tmp_path), public_key
    )

    repository = apt_repository_api.read(repository.pulp_href)
    signed_package = apt_package_api.list(
        repository_version=repository.latest_version_href
    ).results[0]
    signed_package_href = signed_package.pulp_href
    prefixed = fingerprint if ":" in fingerprint else f"v4:{fingerprint}"
    assert signed_package.signing_keys == [prefixed]

    # attempt to add the package to the repo a second time (should produce same package href)
    add_package_to_repo(repository, created_package.pulp_href, release_component, prc)

    repository = apt_repository_api.read(repository.pulp_href)
    results = apt_package_api.list(repository_version=repository.latest_version_href).results

    assert [signed_package_href] == [pkg.pulp_href for pkg in results]


def test_signed_repo_modify_overwrite_false_noop(
    tmp_path,
    monitor_task,
    signing_gpg_metadata,
    deb_package_signing_service,
    deb_repository_factory,
    deb_package_factory,
    deb_release_component_factory,
    deb_package_release_component_factory,
    apt_repository_api,
    apt_package_api,
):
    """
    Re-adding an unsigned package with overwrite=False should NOOP, not raise.

    The first add transparently signs the package and caches the result. A second
    add of the same unsigned package would normally produce the same signed
    package (already in the version) and trigger the pulpcore overwrite check.
    The deb-specific override should exempt this signing-NOOP case.
    """
    _, fingerprint, _ = signing_gpg_metadata

    repository = deb_repository_factory(
        package_signing_service=deb_package_signing_service.pulp_href,
        package_signing_fingerprint=fingerprint,
    )

    file_to_upload = shutil.copy(
        get_local_package_absolute_path("frigg_1.0_ppc64.deb"),
        tmp_path,
    )
    created_package = deb_package_factory(file=file_to_upload)
    package_href = created_package.pulp_href

    release_component = deb_release_component_factory(
        distribution=str(uuid.uuid4()), component="main"
    ).pulp_href
    prc = deb_package_release_component_factory(
        package=package_href,
        release_component=release_component,
    ).pulp_href

    # First add: package gets signed and the result gets stored.
    monitor_task(
        apt_repository_api.modify(
            repository.pulp_href,
            {
                "add_content_units": [package_href, release_component, prc],
                "overwrite": False,
            },
        ).task
    )
    repository = apt_repository_api.read(repository.pulp_href)
    signed_package = apt_package_api.list(
        repository_version=repository.latest_version_href
    ).results[0]
    first_version_href = repository.latest_version_href

    # Second add of the same unsigned package: should NOOP rather than raise
    # ContentOverwriteError, because the already signed package is already present.
    task_result = monitor_task(
        apt_repository_api.modify(
            repository.pulp_href,
            {
                "add_content_units": [package_href, release_component, prc],
                "overwrite": False,
            },
        ).task
    )
    repository = apt_repository_api.read(repository.pulp_href)
    assert repository.latest_version_href == first_version_href
    assert task_result.created_resources == []
    results = apt_package_api.list(repository_version=repository.latest_version_href).results
    assert [signed_package.pulp_href] == [pkg.pulp_href for pkg in results]


def test_signing_does_not_add_package_components_from_other_repositories(
    tmp_path,
    add_package_to_repo,
    deb_signing_key_primary,
    deb_package_signing_service,
    deb_repository_factory,
    deb_package_factory,
    apt_repository_api,
    apt_package_release_components_api,
):
    """Ensure signing only replaces package components belonging to the target repository."""
    package_file = shutil.copy(
        get_local_package_absolute_path("frigg_1.0_ppc64.deb"),
        tmp_path,
    )
    package = deb_package_factory(file=package_file)
    other_repository = deb_repository_factory()
    add_package_to_repo(other_repository, package.pulp_href)

    repository = deb_repository_factory(
        package_signing_service=deb_package_signing_service.pulp_href,
        package_signing_fingerprint=deb_signing_key_primary.fingerprint,
    )
    release_component, _ = add_package_to_repo(repository, package.pulp_href)

    repository = apt_repository_api.read(repository.pulp_href)
    package_components = apt_package_release_components_api.list(
        repository_version=repository.latest_version_href
    ).results
    assert [component.release_component for component in package_components] == [release_component]


def test_already_signed_package(
    tmp_path,
    add_package_to_repo,
    deb_signing_key_primary,
    deb_package_signing_service,
    deb_repository_factory,
    deb_package_factory,
    apt_repository_api,
    apt_package_api,
):
    """Don't sign a package if it's already signed with our key."""

    fingerprint = deb_signing_key_primary.fingerprint

    repo_one = deb_repository_factory(
        package_signing_service=deb_package_signing_service.pulp_href,
        package_signing_fingerprint=fingerprint,
    )
    repo_two = deb_repository_factory(
        package_signing_service=deb_package_signing_service.pulp_href,
        package_signing_fingerprint=fingerprint,
    )

    file_to_upload = shutil.copy(
        get_local_package_absolute_path("frigg_1.0_ppc64.deb"),
        tmp_path,
    )
    created_package = deb_package_factory(file=file_to_upload)

    add_package_to_repo(repo_one, created_package.pulp_href)

    repo_one = apt_repository_api.read(repo_one.pulp_href)
    repo_one_packages = apt_package_api.list(
        repository_version=repo_one.latest_version_href
    ).results
    assert len(repo_one_packages) == 1
    signed_package_href = repo_one_packages[0].pulp_href

    add_package_to_repo(repo_two, signed_package_href)

    repo_two = apt_repository_api.read(repo_two.pulp_href)
    repo_two_packages = apt_package_api.list(
        repository_version=repo_two.latest_version_href
    ).results

    # The same signed package should be reused between repositories
    assert [r.pulp_href for r in repo_two_packages] == [signed_package_href]


def test_signed_repo_rejects_on_demand_content(
    monitor_task,
    pulpcore_bindings,
    add_package_to_repo,
    deb_init_and_sync,
    deb_package_signing_service,
    deb_signing_key_primary,
    deb_repository_factory,
    apt_package_api,
):
    """Ensure modify rejects on-demand content when signing is enabled."""
    monitor_task(pulpcore_bindings.OrphansCleanupApi.cleanup({"orphan_protection_time": 0}).task)

    source_repo, *_ = deb_init_and_sync(remote_args={"policy": "on_demand"})
    fingerprint = deb_signing_key_primary.fingerprint
    destination_repo = deb_repository_factory(
        package_signing_service=deb_package_signing_service.pulp_href,
        package_signing_fingerprint=fingerprint,
    )

    packages = apt_package_api.list(repository_version=source_repo.latest_version_href).results
    package_href = packages[0].pulp_href

    with pytest.raises(ApiException) as exc:
        add_package_to_repo(
            destination_repo,
            package_href,
        )

    assert "Cannot add on-demand content" in exc.value.body


@pytest.mark.parallel
def test_set_and_unset_signing_service_release_overrides(
    deb_signing_key_primary,
    deb_signing_key_secondary,
    deb_package_signing_service,
    deb_signing_service_factory,
    deb_repository_factory,
    apt_repository_api,
):
    """Ensure signing service release overrides can be set and removed via partial_update."""

    def _prefixed(fp):
        return fp if ":" in fp else f"v4:{fp}"

    repository = deb_repository_factory(
        package_signing_service=deb_package_signing_service.pulp_href,
        package_signing_fingerprint=deb_signing_key_primary.fingerprint,
    )
    repo = apt_repository_api.read(repository.pulp_href)
    assert repo.package_signing_fingerprint_release_overrides == {}
    assert repo.signing_service_release_overrides == {}

    # Set a fingerprint override, then remove it with an empty string
    apt_repository_api.partial_update(
        repository.pulp_href,
        {
            "package_signing_fingerprint_release_overrides": {
                "bionic": deb_signing_key_secondary.fingerprint,
            }
        },
    )
    repo = apt_repository_api.read(repository.pulp_href)
    assert repo.package_signing_fingerprint_release_overrides == {
        "bionic": _prefixed(deb_signing_key_secondary.fingerprint),
    }

    apt_repository_api.partial_update(
        repository.pulp_href,
        {"package_signing_fingerprint_release_overrides": {"bionic": ""}},
    )
    repo = apt_repository_api.read(repository.pulp_href)
    assert repo.package_signing_fingerprint_release_overrides == {}

    # Set a signing service override, then remove it with null
    signing_service = deb_signing_service_factory
    apt_repository_api.partial_update(
        repository.pulp_href,
        {"signing_service_release_overrides": {"jammy": signing_service.pulp_href}},
    )
    repo = apt_repository_api.read(repository.pulp_href)
    assert repo.signing_service_release_overrides == {"jammy": signing_service.pulp_href}

    apt_repository_api.partial_update(
        repository.pulp_href,
        {"signing_service_release_overrides": {"jammy": None}},
    )
    repo = apt_repository_api.read(repository.pulp_href)
    assert repo.signing_service_release_overrides == {}


def test_presigned_package_not_resigned(
    tmp_path,
    add_package_to_repo,
    deb_signing_key_secondary,
    package_signing_script_path,
    deb_package_signing_service,
    deb_repository_factory,
    deb_package_factory,
    apt_repository_api,
    apt_package_api,
):
    """
    Ensure a package already signed with the repo's signing fingerprint is not re-signed,
    even when the signing service uses a different key.
    """
    # Sign a package locally with key B (different from signing service's key A)
    file_to_upload = shutil.copy(
        get_local_package_absolute_path("frigg_1.0_ppc64.deb"),
        tmp_path,
    )

    # Sign the package with key B using the signing script
    env = {"PULP_SIGNING_KEY_FINGERPRINT": deb_signing_key_secondary.fingerprint}
    result = subprocess.run(
        [str(package_signing_script_path), str(file_to_upload)],
        env=env,
        capture_output=True,
    )
    assert result.returncode == 0, f"Signing failed: {result.stderr}"

    # Verify the package is signed with key B
    AptPackageSigningService._check_deb_signature(
        str(file_to_upload),
        deb_signing_key_secondary.fingerprint,
        str(tmp_path),
        deb_signing_key_secondary.public_key,
    )

    # Upload the pre-signed package without a signing repository
    created_package = deb_package_factory(file=str(file_to_upload))
    original_href = created_package.pulp_href

    # Create a repo with signing service (key A) but package_signing_fingerprint = key B
    repository = deb_repository_factory(
        package_signing_service=deb_package_signing_service.pulp_href,
        package_signing_fingerprint=deb_signing_key_secondary.fingerprint,
    )

    # Add the pre-signed package to the repo
    add_package_to_repo(repository, original_href)

    # Verify the package was NOT re-signed
    repository = apt_repository_api.read(repository.pulp_href)
    packages = apt_package_api.list(repository_version=repository.latest_version_href).results

    assert len(packages) == 1
    assert packages[0].pulp_href == original_href, (
        "Package was re-signed despite already having the correct signature."
    )
