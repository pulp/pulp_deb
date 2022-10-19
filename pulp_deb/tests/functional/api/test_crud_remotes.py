"""Tests that CRUD deb remotes."""
from random import choice
import pytest

from pulpcore.client.pulp_deb.exceptions import ApiException

from pulp_smash import utils

from pulp_deb.tests.functional.constants import DOWNLOAD_POLICIES, DEB_SIGNING_KEY
from pulp_deb.tests.functional.utils import gen_deb_remote


@pytest.mark.parallel
def test_create_remote_repository(deb_remote_custom_data_factory):
    """Test creation of the remote."""
    data = gen_verbose_remote_data()
    remote = deb_remote_custom_data_factory(data)

    for key, val in data.items():
        if key != "username" and key != "password":
            assert remote.to_dict()[key] == val


@pytest.mark.parallel
def test_create_remote_repository_with_same_name(deb_remote_custom_data_factory):
    """Verify whether it is possible to create a remote with the same name."""
    data = gen_verbose_remote_data()
    deb_remote_custom_data_factory(data)

    with pytest.raises(ApiException) as exc:
        deb_remote_custom_data_factory(data)

    assert exc.value.status == 400


@pytest.mark.parallel
def test_create_remote_repository_without_url(deb_remote_custom_data_factory):
    """Verify whether it is possible to create a remote without an URL."""
    data = gen_verbose_remote_data()
    del data["url"]

    with pytest.raises(ApiException) as exc:
        deb_remote_custom_data_factory(data)

    assert exc.value.status == 400


@pytest.mark.parallel
def test_read_remote_by_href(
    deb_remote_custom_data_factory,
    deb_get_remote_by_href,
):
    """Verify whether it is possible to read a remote repository by its href."""
    data = gen_verbose_remote_data()
    remote = deb_remote_custom_data_factory(data)
    read_remote = deb_get_remote_by_href(remote.pulp_href)

    for key, val in remote.to_dict().items():
        assert read_remote.to_dict()[key] == val


@pytest.mark.parallel
def test_read_remote_by_name(
    deb_remote_custom_data_factory,
    deb_get_remotes_by_name,
):
    """Verify whether it is possible to read a remote repository by its name."""
    data = gen_verbose_remote_data()
    remote = deb_remote_custom_data_factory(data)
    read_remote = deb_get_remotes_by_name(remote.name)

    assert len(read_remote.results) == 1

    for key, val in remote.to_dict().items():
        assert read_remote.results[0].to_dict()[key] == val


@pytest.mark.parallel
def test_patch_remote(
    deb_remote_custom_data_factory,
    deb_get_remote_by_href,
    deb_patch_remote,
):
    """Verify whether it is possible to update a remote with PATCH."""
    data = gen_verbose_remote_data()
    remote = deb_remote_custom_data_factory(data)
    patch_data = gen_verbose_remote_data()
    deb_patch_remote(remote, patch_data)
    patch_remote = deb_get_remote_by_href(remote.pulp_href)

    for key, val in patch_data.items():
        if key != "username" and key != "password":
            assert patch_remote.to_dict()[key] == val
        if key == "distributions" or key == "components" or key == "architectures":
            assert patch_remote.to_dict()[key] != remote.to_dict()[key]


@pytest.mark.parallel
def test_put_remote(
    deb_remote_custom_data_factory,
    deb_get_remote_by_href,
    deb_put_remote,
):
    """Verify whether it is possible to update a remote with PUT."""
    data = gen_verbose_remote_data()
    remote = deb_remote_custom_data_factory(data)
    put_data = gen_verbose_remote_data()
    deb_put_remote(remote, put_data)
    put_remote = deb_get_remote_by_href(remote.pulp_href)

    for key, val in put_data.items():
        if key != "username" and key != "password":
            assert put_remote.to_dict()[key] == val
        if key == "distributions" or key == "components" or key == "architectures":
            assert put_remote.to_dict()[key] != remote.to_dict()[key]


@pytest.mark.parallel
def test_delete_remote(
    deb_delete_remote,
    deb_remote_custom_data_factory,
    deb_get_remote_by_href,
):
    """Verify whether it is possible to delete a remote."""
    data = gen_verbose_remote_data()
    remote = deb_remote_custom_data_factory(data)
    deb_delete_remote(remote)

    with pytest.raises(ApiException) as exc:
        deb_get_remote_by_href(remote.pulp_href)

    assert exc.value.status == 404


@pytest.mark.parallel
def test_remote_download_policies(
    deb_remote_custom_data_factory,
    deb_get_remote_by_href,
    deb_patch_remote,
):
    """Verify download policy behavior for valid and invalid values."""
    # Create a remote without a download policy.
    data = gen_verbose_remote_data()
    del data["policy"]
    remote = deb_remote_custom_data_factory(data)

    # Verify the creation is successful and the "immediate" policy is applied.
    assert remote.policy == "immediate"

    # Pick a random policy that is not the default and apply it to the remote.
    policies = DOWNLOAD_POLICIES
    changed_policy = choice([item for item in policies if item != "immediate"])
    deb_patch_remote(remote, {"policy": changed_policy})
    remote = deb_get_remote_by_href(remote.pulp_href)

    # Verify that the policy change is successful
    assert remote.policy == changed_policy

    # Create a snapshot of the remote for later reference
    remote_snapshot = deb_get_remote_by_href(remote.pulp_href)

    # Attempt to change the remote policy to an invalid string
    with pytest.raises(ApiException) as exc:
        deb_patch_remote(remote, {"policy": utils.uuid4()})
    assert exc.value.status == 400

    # Verify that the remote policy remains unchanged
    remote = deb_get_remote_by_href(remote.pulp_href)
    assert remote.policy == remote_snapshot.policy


def gen_verbose_remote_data():
    """Return a semi-random dict for use in defining a remote.

    For most tests, it's desirable to create remotes with as few attributes
    as possible, so that the tests can specifically target and attempt to break
    specific features. This module specifically targets remotes, so it makes
    sense to provide as many attributes as possible.
    Note that 'username' and 'password' are write-only attributes.
    """
    data = gen_deb_remote()
    data.update(
        {
            "password": utils.uuid4(),
            "username": utils.uuid4(),
            "policy": choice(DOWNLOAD_POLICIES),
            "distributions": f"{utils.uuid4()} {utils.uuid4()}",
            "components": f"{utils.uuid4()} {utils.uuid4()}",
            "architectures": f"{utils.uuid4()} {utils.uuid4()}",
            "gpgkey": DEB_SIGNING_KEY,
        }
    )
    return data
