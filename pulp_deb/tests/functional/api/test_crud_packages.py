"""Tests that perform actions over packages."""
from uuid import uuid4
import pytest

from pulp_deb.tests.functional.constants import DEB_PACKAGE_RELPATH
from pulp_deb.tests.functional.utils import get_local_package_absolute_path


@pytest.mark.parallel
def test_create_package(apt_package_api, deb_package_factory):
    """Verify all allowed CRUD actions are working and the ones that don't exist fail."""
    # Create a package and verify its attributes
    attrs = {
        "relative_path": DEB_PACKAGE_RELPATH,
        "file": get_local_package_absolute_path(DEB_PACKAGE_RELPATH),
    }
    package = deb_package_factory(**attrs)
    assert package.relative_path == DEB_PACKAGE_RELPATH

    # Verify that only one package with this relative path exists
    package_list = apt_package_api.list(relative_path=package.relative_path)
    assert package_list.count == 1

    # Verify that reading the package works and has the same attributes
    package = apt_package_api.read(package.pulp_href)
    assert package.relative_path == DEB_PACKAGE_RELPATH

    # Verify that partial update does not work for packages
    with pytest.raises(AttributeError) as exc:
        apt_package_api.partial_update(package.pulp_href, relative_path=str(uuid4()))
    assert "object has no attribute 'partial_update'" in exc.value.args[0]

    # Verify that update does not work for packages
    with pytest.raises(AttributeError) as exc:
        apt_package_api.update(package.pulp_href, relative_path=str(uuid4()))
    assert "object has no attribute 'update'" in exc.value.args[0]

    # Verify that delete does not work for packages
    with pytest.raises(AttributeError) as exc:
        apt_package_api.delete(package.pulp_href)
    assert "object has no attribute 'delete'" in exc.value.args[0]


def test_same_sha256_same_relative_path_no_repo(
    apt_package_api, deb_package_factory, delete_orphans_pre
):
    """Test whether uploading the same package works and that it stays unique."""
    attrs = {
        "file": get_local_package_absolute_path(DEB_PACKAGE_RELPATH),
        "relative_path": DEB_PACKAGE_RELPATH,
    }

    # Create the first package and verify its attributes
    package_1 = deb_package_factory(**attrs)
    assert package_1.relative_path == attrs["relative_path"]

    # Create the second package and verify it has the same href as the first one
    package_2 = deb_package_factory(**attrs)
    assert package_2.pulp_href == package_1.pulp_href
    assert apt_package_api.read(package_1.pulp_href).pulp_href == package_2.pulp_href

    # Verify the package is one
    package_list = apt_package_api.list(relative_path=DEB_PACKAGE_RELPATH)
    assert package_list.count == 1


def test_structured_package_upload(
    apt_package_api,
    deb_get_repository_by_href,
    deb_package_factory,
    deb_repository_factory,
    delete_orphans_pre,
):
    """Test whether uploading a structured package works and creates the correct paths."""
    attrs = {
        "file": get_local_package_absolute_path(DEB_PACKAGE_RELPATH),
        "relative_path": DEB_PACKAGE_RELPATH,
        "distribution": str(uuid4()),
        "component": str(uuid4()),
    }

    repository = deb_repository_factory()
    assert repository.latest_version_href.endswith("/0/")
    attrs["repository"] = repository.pulp_href

    deb_package_factory(**attrs)
    repository = deb_get_repository_by_href(repository.pulp_href)
    assert repository.latest_version_href.endswith("/1/")

    package_list = apt_package_api.list(relative_path=DEB_PACKAGE_RELPATH)
    assert package_list.count == 1

    results = package_list.results[0]
    assert results.relative_path == attrs["relative_path"]
