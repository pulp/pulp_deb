"""Tests that CRUD deb remotes."""

from random import choice
from uuid import uuid4
import pytest

from pulpcore.client.pulp_deb.exceptions import ApiException

from pulp_deb.tests.functional.utils import gen_deb_remote_verbose
from pulp_deb.tests.functional.constants import DOWNLOAD_POLICIES


@pytest.fixture
def deb_init_verbose_remote(deb_get_fixture_server_url, deb_remote_custom_data_factory):
    """A fixture that initializes are deb remote with verbose data."""

    def _deb_init_verbose_remote(remove_policy=False, extra_data=False):
        """Generates a deb remote with verbose data.

        :param remove_policy: (Optional) If set will remove the policy field from the dict
        :param extra_data: (Optional) If set will return an extra set of data for testing
        :returns: A tuple containing the created remote and the verbose data used to create it.
            Optionally it will also return a second set of verbose data for testing purposes.
        """
        url = deb_get_fixture_server_url()
        data = gen_deb_remote_verbose(url, remove_policy)
        remote = deb_remote_custom_data_factory(data)
        return (
            (remote, data)
            if not extra_data
            else (remote, data, gen_deb_remote_verbose(url, remove_policy))
        )

    return _deb_init_verbose_remote


@pytest.mark.parallel
def test_create_remote_repository(deb_init_verbose_remote):
    """Test creation of the remote."""
    remote, data = deb_init_verbose_remote()

    for key, val in data.items():
        if key != "username" and key != "password":
            assert remote.to_dict()[key] == val


@pytest.mark.parallel
def test_create_remote_repository_with_same_name(
    deb_remote_custom_data_factory, deb_init_verbose_remote
):
    """Verify whether it is possible to create a remote with the same name."""
    _, data = deb_init_verbose_remote()

    with pytest.raises(ApiException) as exc:
        deb_remote_custom_data_factory(data)

    assert exc.value.status == 400


@pytest.mark.parallel
def test_create_remote_repository_without_url(deb_remote_custom_data_factory):
    """Verify whether it is possible to create a remote without an URL."""
    pytest.skip("pydantic catches this before we get to the server")
    data = gen_deb_remote_verbose()
    with pytest.raises(ApiException) as exc:
        deb_remote_custom_data_factory(data)

    assert exc.value.status == 400


@pytest.mark.parallel
def test_read_remote_by_href(deb_init_verbose_remote, deb_get_remote_by_href):
    """Verify whether it is possible to read a remote repository by its href."""
    remote, _ = deb_init_verbose_remote()
    read_remote = deb_get_remote_by_href(remote.pulp_href)

    for key, val in remote.to_dict().items():
        assert read_remote.to_dict()[key] == val


@pytest.mark.parallel
def test_read_remote_by_name(deb_init_verbose_remote, deb_get_remotes_by_name):
    """Verify whether it is possible to read a remote repository by its name."""
    remote, _ = deb_init_verbose_remote()
    read_remote = deb_get_remotes_by_name(remote.name)

    assert len(read_remote.results) == 1

    for key, val in remote.to_dict().items():
        assert read_remote.results[0].to_dict()[key] == val


@pytest.mark.parallel
def test_patch_remote(deb_init_verbose_remote, deb_get_remote_by_href, deb_patch_remote):
    """Verify whether it is possible to update a remote with PATCH."""
    remote, _, patch_data = deb_init_verbose_remote(extra_data=True)
    deb_patch_remote(remote, patch_data)
    patch_remote = deb_get_remote_by_href(remote.pulp_href)

    for key, val in patch_data.items():
        if key != "username" and key != "password":
            assert patch_remote.to_dict()[key] == val
        if key == "distributions" or key == "components" or key == "architectures":
            assert patch_remote.to_dict()[key] != remote.to_dict()[key]


@pytest.mark.parallel
def test_put_remote(deb_init_verbose_remote, deb_get_remote_by_href, deb_put_remote):
    """Verify whether it is possible to update a remote with PUT."""
    remote, _, put_data = deb_init_verbose_remote(extra_data=True)
    deb_put_remote(remote, put_data)
    put_remote = deb_get_remote_by_href(remote.pulp_href)

    for key, val in put_data.items():
        if key != "username" and key != "password":
            assert put_remote.to_dict()[key] == val
        if key == "distributions" or key == "components" or key == "architectures":
            assert put_remote.to_dict()[key] != remote.to_dict()[key]


@pytest.mark.parallel
def test_delete_remote(deb_init_verbose_remote, deb_delete_remote, deb_get_remote_by_href):
    """Verify whether it is possible to delete a remote."""
    remote, _ = deb_init_verbose_remote()
    deb_delete_remote(remote)

    with pytest.raises(ApiException) as exc:
        deb_get_remote_by_href(remote.pulp_href)

    assert exc.value.status == 404


@pytest.mark.parallel
def test_remote_download_policies(
    deb_init_verbose_remote,
    deb_get_remote_by_href,
    deb_patch_remote,
):
    """Verify download policy behavior for valid and invalid values."""
    remote, _ = deb_init_verbose_remote(remove_policy=True)

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

    # Attempt to change the remote policy to an invalid string (now caught by pydantic)
    with pytest.raises(Exception):
        deb_patch_remote(remote, {"policy": str(uuid4())})

    # Verify that the remote policy remains unchanged
    remote = deb_get_remote_by_href(remote.pulp_href)
    assert remote.policy == remote_snapshot.policy
