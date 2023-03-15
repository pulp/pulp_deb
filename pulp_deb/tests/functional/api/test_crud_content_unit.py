"""Tests that perform actions over content unit."""
import uuid
import pytest


@pytest.mark.parallel
def test_create_generic_content_unit(
    apt_generic_content_api,
    deb_generic_content_factory,
    random_artifact,
):
    """Verify all allowed CRUD actions are working and the ones that don't exist fail."""
    # Create a random content unit and verify its attributes
    attrs = {"artifact": random_artifact.pulp_href, "relative_path": str(uuid.uuid4())}
    content_unit = deb_generic_content_factory(**attrs)
    assert content_unit.artifact == random_artifact.pulp_href
    assert content_unit.relative_path == attrs["relative_path"]

    # Verify that only one content unit with this relative path exists
    content_list = apt_generic_content_api.list(relative_path=content_unit.relative_path)
    assert content_list.count == 1

    # Verify that reading the content unit works and has the same attributes
    content_unit = apt_generic_content_api.read(content_unit.pulp_href)
    assert content_unit.artifact == random_artifact.pulp_href
    assert content_unit.relative_path == attrs["relative_path"]

    # Verify that partial update does not work for content units
    with pytest.raises(AttributeError) as exc:
        apt_generic_content_api.partial_update(
            content_unit.pulp_href, relative_path=str(uuid.uuid4())
        )
    assert "object has no attribute 'partial_update'" in exc.value.args[0]

    # Verify that update does not work for content units
    with pytest.raises(AttributeError) as exc:
        apt_generic_content_api.update(content_unit.pulp_href, relative_path=str(uuid.uuid4()))
    assert "object has no attribute 'update'" in exc.value.args[0]

    # Verify that delete does not work for content units
    with pytest.raises(AttributeError) as exc:
        apt_generic_content_api.delete(content_unit.pulp_href)
    assert "object has no attribute 'delete'" in exc.value.args[0]


@pytest.mark.parallel
def test_same_sha256_same_relative_path_no_repo(
    apt_generic_content_api, deb_generic_content_factory, random_artifact
):
    """Test whether uploading the same content unit works and that it stays unique."""
    attrs = {"artifact": random_artifact.pulp_href, "relative_path": str(uuid.uuid4())}

    # Create the first content unit and verify its attributes
    content_unit_1 = deb_generic_content_factory(**attrs)
    assert content_unit_1.artifact == random_artifact.pulp_href
    assert content_unit_1.relative_path == attrs["relative_path"]

    # Create the second content unit and verify its the same as the first one
    content_unit_2 = deb_generic_content_factory(**attrs)
    assert content_unit_2.pulp_href == content_unit_1.pulp_href
    assert (
        apt_generic_content_api.read(content_unit_1.pulp_href).pulp_href == content_unit_2.pulp_href
    )


@pytest.mark.parallel
def test_same_sha256_diff_relative_path(
    apt_generic_content_api, deb_generic_content_factory, random_artifact
):
    """Test whether uploading the same content unit with different relative path works."""
    attrs = {"artifact": random_artifact.pulp_href, "relative_path": str(uuid.uuid4())}

    # Create the first content unit
    content_unit_1 = deb_generic_content_factory(**attrs)
    assert content_unit_1.artifact == random_artifact.pulp_href
    assert content_unit_1.relative_path == attrs["relative_path"]

    rel_path = attrs["relative_path"]

    # Change the relative path and upload the content unit again verify it is the same
    attrs["relative_path"] = str(uuid.uuid4())
    content_unit_2 = deb_generic_content_factory(**attrs)
    assert content_unit_2.artifact == random_artifact.pulp_href

    # Verify that the relative paths are different and the content unit is still unique
    assert rel_path != attrs["relative_path"]
    response = apt_generic_content_api.list(relative_path=attrs["relative_path"])
    assert response.count == 1
