"""Tests relating to duplicate package handling.

By "duplicate package" we mean two packages with the same Package, Version, and Architecture fields,
but different checksums. By contrast we refer to two packages with the same checksum (but stored at
a different relative_path within some repo) as two "identical packages". So defined, an APT repo may
contain identical packages, but may not contain any duplicates.

To ensure this is the case we use the handle_duplicate_packages function. As such, these tests are
primarily intended to test this function.
"""
import pytest
from uuid import uuid4

from pulpcore.tests.functional.utils import PulpTaskError

from pulp_deb.tests.functional.constants import DEB_PACKAGE_RELPATH
from pulp_deb.tests.functional.utils import (
    get_counts_from_content_summary,
    get_local_package_absolute_path,
)

DUPLICATE_PACKAGE_DIR = "data/packages/duplicates/"  # below pulp_deb/tests/functional/


def test_upload_package_and_duplicate(
    apt_package_api,
    deb_get_content_summary,
    deb_get_repository_by_href,
    deb_package_factory,
    deb_repository_factory,
):
    """Test uploading a package to a repo, and then uploading it's duplicate.

    The expectation is that uploading the duplicate will kick the older duplicate (along with the
    associated PackageReleaseComponent) out of the repo. Only the newer duplicate and its PRC will
    remain.
    """
    # Generate an empty test repo.
    repository = deb_repository_factory()
    assert repository.latest_version_href.endswith("/0/")
    repository_href = repository.pulp_href

    # Upload a test package to a component in the repo.
    package_upload_params = {
        "file": get_local_package_absolute_path(DEB_PACKAGE_RELPATH),
        "relative_path": DEB_PACKAGE_RELPATH,
        "distribution": str(uuid4()),
        "component": str(uuid4()),
        "repository": repository_href,
    }
    deb_package_factory(**package_upload_params)

    # Assert that the uploaded package has arrived in the repo.
    repository = deb_get_repository_by_href(repository_href)
    assert repository.latest_version_href.endswith("/1/")
    content_counts = get_counts_from_content_summary(deb_get_content_summary(repository).added)
    assert content_counts == {
        "deb.package": 1,
        "deb.package_release_component": 1,
        "deb.release_architecture": 1,
        "deb.release_component": 1,
    }
    package1_sha256 = (
        apt_package_api.list(
            repository_version_added=repository.latest_version_href, fields=["sha256"]
        )
        .results[0]
        .sha256
    )

    # Upload a duplicate of the first package into the repo.
    package_upload_params["file"] = get_local_package_absolute_path(
        package_name=DEB_PACKAGE_RELPATH, relative_path=DUPLICATE_PACKAGE_DIR
    )
    deb_package_factory(**package_upload_params)

    # Assert that only the newer duplicate is now in the repo.
    repository = deb_get_repository_by_href(repository_href)
    assert repository.latest_version_href.endswith("/2/")
    content_summary = deb_get_content_summary(repository)
    content_counts_added = get_counts_from_content_summary(content_summary.added)
    content_counts_removed = get_counts_from_content_summary(content_summary.removed)
    assert content_counts_added == {
        "deb.package": 1,
        "deb.package_release_component": 1,
    }
    assert content_counts_removed == {
        "deb.package": 1,
        "deb.package_release_component": 1,
    }
    package2_sha256 = (
        apt_package_api.list(
            repository_version_added=repository.latest_version_href, fields=["sha256"]
        )
        .results[0]
        .sha256
    )
    assert package1_sha256 != package2_sha256


def test_add_duplicates_to_repo(
    deb_modify_repository,
    deb_package_factory,
    deb_repository_factory,
):
    """Test adding two duplicate packages to a repository in a single modify action.

    The expectation is that this will raise a ValueError.
    """
    # Upload two duplicate packages.
    package_upload_params = {
        "file": get_local_package_absolute_path(
            package_name=DEB_PACKAGE_RELPATH, relative_path=DUPLICATE_PACKAGE_DIR
        ),
        "relative_path": DEB_PACKAGE_RELPATH,
    }
    href1 = deb_package_factory(**package_upload_params).pulp_href
    package_upload_params["file"] = get_local_package_absolute_path(DEB_PACKAGE_RELPATH)
    href2 = deb_package_factory(**package_upload_params).pulp_href

    # Generate an empty test repo.
    repository = deb_repository_factory()
    assert repository.latest_version_href.endswith("/0/")

    # Add the duplicates to the repository.
    with pytest.raises(PulpTaskError) as exception:
        deb_modify_repository(repository, {"add_content_units": [href1, href2]})

    # Assert the error message.
    assert "Cannot create repository version since there are newly added packages with" in str(
        exception.value
    )
