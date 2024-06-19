"""Tests related to source packages."""

import json
import pytest
import re
from uuid import uuid4

from pulp_deb.tests.functional.utils import (
    get_counts_from_content_summary,
    get_local_package_absolute_path,
)
from pulpcore.client.pulpcore.exceptions import ApiException

SOURCE_PACKAGE_RELPATH = "mimir_1.0.dsc"
SOURCE_PACKAGE_SOURCE = "mimir_1.0.tar.xz"
SOURCE_PACKAGE_PATH = "data/debian/pool/asgard/m/mimir"


def _extract_sha256(body):
    """Parse the sha256 from the body of an artifact create exception."""
    error = json.loads(body)["non_field_errors"][0]
    return re.search("checksum of '([0-9a-fA-F]+)'", error)[1]


def _find_existing_artifact(artifacts_api, exc):
    """Given an exception when creating an artifact, find if there's an existing one."""
    try:
        sha256 = _extract_sha256(exc.body)
        artifact = artifacts_api.list(sha256=sha256).results[0]
        return artifact
    except Exception:
        return None


@pytest.fixture
def artifact_factory(
    pulpcore_bindings,
    gen_object_with_cleanup,
):
    """Factory to create an artifact."""

    def _artifact_factory(relative_name, relative_path=SOURCE_PACKAGE_PATH):
        try:
            file = get_local_package_absolute_path(relative_name, relative_path=relative_path)
            artifact = gen_object_with_cleanup(pulpcore_bindings.ArtifactsApi, file)
        except ApiException as exc:
            if artifact := _find_existing_artifact(pulpcore_bindings.ArtifactsApi, exc):
                return artifact
            else:
                raise
        return artifact

    return _artifact_factory


@pytest.mark.parallel
def test_upload_source_package_and_publish(
    artifact_factory,
    deb_publication_factory,
    deb_get_repository_by_href,
    deb_get_content_summary,
    deb_modify_repository,
    deb_repository_factory,
    deb_release_component_factory,
    deb_source_package_factory,
    apt_source_package_api,
    apt_source_release_components_api,
    deb_source_release_component_factory,
):
    """
    Test uploading a source package and publishing it in two repository releases.

    This tests the fix for https://github.com/pulp/pulp_deb/issues/1053
    """
    # Generate a test repo
    repository = deb_repository_factory()
    assert repository.latest_version_href.endswith("/0/")
    repository_href = repository.pulp_href

    # create our source package
    source_packages = apt_source_package_api.list(relative_path=SOURCE_PACKAGE_RELPATH)
    if source_packages.count > 0:
        # source package exists, use it
        source_package = source_packages.results[0]
    else:
        # source package doesn't exist
        artifact_factory(SOURCE_PACKAGE_SOURCE)
        artifact = artifact_factory(SOURCE_PACKAGE_RELPATH)

        # Upload a test  source package
        package_upload_params = {
            "artifact": artifact.pulp_href,
            "relative_path": SOURCE_PACKAGE_RELPATH,
        }
        source_package = deb_source_package_factory(**package_upload_params)
    deb_modify_repository(repository, {"add_content_units": [source_package.pulp_href]})

    # create two release components and source release components
    for _ in range(2):
        release_component = deb_release_component_factory(
            repository=repository.pulp_href,
            distribution=str(uuid4()),
            component="main",
        )
        deb_source_release_component_factory(
            repository=repository.pulp_href,
            source_package=source_package.pulp_href,
            release_component=release_component.pulp_href,
        )

    # confirm our repository has two source package release components
    repository = deb_get_repository_by_href(repository_href)
    assert repository.latest_version_href.endswith("/5/")
    content_counts = get_counts_from_content_summary(deb_get_content_summary(repository).present)
    assert content_counts == {
        "deb.source_package": 1,
        "deb.source_package_release_component": 2,
        "deb.release_component": 2,
    }

    # attempt to publish the repo
    publication = deb_publication_factory(repository, structured=True)
    assert publication.repository_version == repository.latest_version_href


def test_upload_same_source_package(
    artifact_factory,
    apt_source_package_api,
    deb_source_package_factory,
    delete_orphans_pre,
):
    """Test whether uploading the same source package works and that it stays unique."""
    artifact_factory(SOURCE_PACKAGE_SOURCE)
    artifact = artifact_factory(SOURCE_PACKAGE_RELPATH)
    attrs = {
        "artifact": artifact.pulp_href,
        "relative_path": SOURCE_PACKAGE_RELPATH,
    }

    # Create the first source package and verify its attributes
    package_1 = deb_source_package_factory(**attrs)
    assert package_1.relative_path == attrs["relative_path"]

    # Create the second package and verify it has the same href as the first one
    package_2 = deb_source_package_factory(**attrs)
    assert package_2.pulp_href == package_1.pulp_href
    assert apt_source_package_api.read(package_1.pulp_href).pulp_href == package_2.pulp_href

    # Verify the package count is one
    package_list = apt_source_package_api.list(relative_path=SOURCE_PACKAGE_RELPATH)
    assert package_list.count == 1
