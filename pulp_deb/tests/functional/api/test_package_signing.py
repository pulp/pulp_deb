from dataclasses import dataclass
import hashlib
import shutil
import uuid
from importlib_resources import files

from pulp_deb.app.models import AptPackageSigningService
import requests
from pulp_deb.tests.functional.utils import get_local_package_absolute_path
import pytest

@pytest.mark.parallel
def test_register_rpm_package_signing_service(deb_package_signing_service):
    """
    Register a sample rpmsign-based signing service and validate it works.
    """
    service = deb_package_signing_service
    assert "/api/v3/signing-services/" in service.pulp_href
    
@dataclass
class GPGMetadata:
    pubkey: str
    fingerprint: str
    keyid: str


@pytest.fixture
def signing_gpg_extra(signing_gpg_metadata):
    """GPG instance with an extra gpg keypair registered."""
    PRIVATE_KEY_PULP_QE = (
        "https://raw.githubusercontent.com/pulp/pulp-fixtures/master/common/GPG-PRIVATE-KEY-pulp-qe"
    )
    gpg, fingerprint_a, keyid_a = signing_gpg_metadata

    response_private = requests.get(PRIVATE_KEY_PULP_QE)
    response_private.raise_for_status()
    import_result = gpg.import_keys(response_private.content)
    fingerprint_b = import_result.fingerprints[0]
    gpg.trust_keys(fingerprint_b, "TRUST_ULTIMATE")

    pubkey_a = gpg.export_keys(fingerprint_a)
    pubkey_b = gpg.export_keys(fingerprint_b)
    return (
        gpg,
        GPGMetadata(pubkey_a, fingerprint_a, fingerprint_a[-8:]),
        GPGMetadata(pubkey_b, fingerprint_b, fingerprint_b[-8:]),
    )
    
@pytest.mark.parallel
def test_sign_package_on_upload(
    tmp_path,
    download_content_unit,
    signing_gpg_extra,
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
    # Setup RPM tool and package to upload
    gpg, gpg_metadata_a, gpg_metadata_b = signing_gpg_extra
    fingerprint_set = set([gpg_metadata_a.fingerprint, gpg_metadata_b.fingerprint])
    assert len(fingerprint_set) == 2

    file_to_upload = shutil.copy(
        get_local_package_absolute_path("frigg_1.0_ppc64.deb"),
        tmp_path,
    )
    with pytest.raises(Exception, match="No such file or directory:.*"):
        AptPackageSigningService._validate_deb_package(file_to_upload, gpg_metadata_a.fingerprint, str(tmp_path), gpg)

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
        AptPackageSigningService._validate_deb_package(str(downloaded_package), fingerprint, str(tmp_path), gpg)
    
    # Test release override
    repository = deb_repository_factory(
        package_signing_service=deb_package_signing_service.pulp_href,
        package_signing_fingerprint=gpg_metadata_a.fingerprint,
        package_signing_fingerprint_release_overrides={"test": gpg_metadata_b.fingerprint}
    )
    
    deb_release_factory(
        "test", "test", "test", repository=repository.pulp_href
    )
    deb_release_factory(
        "test2", "test2", "test2", repository=repository.pulp_href
    )
    
    deb_package_factory(
        file=file_to_upload,
        repository=repository.pulp_href,
        distribution="test",
    )
    # uncommenting this line causes a failure since it overrides the existing package with a version signed with fingerprint_a
    # deb_package_factory(
    #     file=file_to_upload,
    #     repository=repository.pulp_href,
    #     distribution="test2",
    # )
    
    # Verify that the final served package is signed
    publication = deb_publication_factory(repository)
    distribution = deb_distribution_factory(publication=publication)
    downloaded_package = tmp_path / "package.deb"
    downloaded_package.write_bytes(
        download_content_unit(distribution.base_path, "pool/upload/f/frigg/frigg_1.0_ppc64.deb")
    )
    AptPackageSigningService._validate_deb_package(str(downloaded_package), gpg_metadata_b.fingerprint, str(tmp_path), gpg)
    
    
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
    signing_gpg_extra,
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
    # Setup RPM tool and package to upload
    gpg, gpg_metadata_a, gpg_metadata_b = signing_gpg_extra
    fingerprint_set = set([gpg_metadata_a.fingerprint, gpg_metadata_b.fingerprint])
    assert len(fingerprint_set) == 2

    file_to_upload = shutil.copy(
        get_local_package_absolute_path("frigg_1.0_ppc64.deb"),
        tmp_path,
    )
    with pytest.raises(Exception, match="No such file or directory:.*"):
        AptPackageSigningService._validate_deb_package(file_to_upload, gpg_metadata_a.fingerprint, str(tmp_path), gpg)

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
        AptPackageSigningService._validate_deb_package(str(downloaded_package), fingerprint, str(tmp_path), gpg)
