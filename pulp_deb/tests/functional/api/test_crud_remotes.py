"""Tests that CRUD deb remotes."""
from random import choice
import pytest

from pulpcore.client.pulp_deb.exceptions import ApiException

from pulp_smash import utils
from pulp_smash.pulp3.bindings import monitor_task

from pulp_deb.tests.functional.constants import DOWNLOAD_POLICIES, DEB_SIGNING_KEY
from pulp_deb.tests.functional.utils import gen_deb_remote


def test_create_remote_repository(verbose_remote_data, remote_repository):
    """Test creation of the remote repository.
    NOTE: The repository is actually created in this files fixture and this
          test only confirms its creation.
    """
    for key, val in verbose_remote_data.items():
        if key != "username" and key != "password":
            assert remote_repository.to_dict()[key] == val


def test_create_remote_repository_with_same_name(
    apt_remote_api, gen_object_with_cleanup, remote_repository, gen_verbose_remote_data
):
    """Verify whether it is possible to create a remote repository with the same
    name.
    """
    body = gen_verbose_remote_data()
    body["name"] = remote_repository.name
    with pytest.raises(ApiException) as exc:
        gen_object_with_cleanup(apt_remote_api, body)
    assert exc.value.status == 400


@pytest.mark.parallel
def test_create_remote_repository_without_url(
    apt_remote_api, gen_object_with_cleanup, gen_verbose_remote_data
):
    """Verify whether it is possible to create a remote repository without an URL.
    This test targets the following issues:
    * `Pulp #3395 <https://pulp.plan.io/issues/3395>`_
    * `Pulp Smash #984 <https://github.com/pulp/pulp-smash/issues/984>`_
    """
    body = gen_verbose_remote_data()
    del body["url"]
    with pytest.raises(ApiException) as exc:
        gen_object_with_cleanup(apt_remote_api, body)
    assert exc.value.status == 400


def test_read_remote_by_href(apt_remote_api, remote_repository):
    """Verify whether it is possible to read a remote repository by its href."""
    href = apt_remote_api.read(remote_repository.pulp_href)
    for key, val in remote_repository.to_dict().items():
        assert href.to_dict()[key] == val


def test_read_remote_repository_by_name(apt_remote_api, remote_repository):
    """Verify whether it is possible to read a remote repository by its name."""
    page = apt_remote_api.list(name=remote_repository.name)
    assert len(page.results) == 1
    for key, val in remote_repository.to_dict().items():
        assert page.results[0].to_dict()[key] == val


def test_update_remote_repository_with_patch(
    apt_remote_api, gen_verbose_remote_data, remote_repository
):
    """Test if a remote repository is updated by PATCH."""
    previous_repo = apt_remote_api.read(remote_repository.pulp_href)
    body = gen_verbose_remote_data()
    response = apt_remote_api.partial_update(remote_repository.pulp_href, body)
    monitor_task(response.task)
    repo = apt_remote_api.read(remote_repository.pulp_href)
    for key, val in body.items():
        if key != "username" and key != "password":
            assert repo.to_dict()[key] == val
        if key == "distributions" or key == "components" or key == "architectures":
            assert repo.to_dict()[key] != previous_repo.to_dict()[key]


def test_update_remote_repository_with_put(
    apt_remote_api, gen_verbose_remote_data, remote_repository
):
    """Test if a remote repository is updated by PUT."""
    previous_repo = apt_remote_api.read(remote_repository.pulp_href)
    body = gen_verbose_remote_data()
    response = apt_remote_api.update(remote_repository.pulp_href, body)
    monitor_task(response.task)
    repo = apt_remote_api.read(remote_repository.pulp_href)
    for key, val in body.items():
        if key != "username" and key != "password":
            assert repo.to_dict()[key] == val
        if key == "distributions" or key == "components" or key == "architectures":
            assert repo.to_dict()[key] != previous_repo.to_dict()[key]


def test_delete_remote_repository(apt_remote_api, remote_repository):
    """Test if a remote repository can be deleted."""
    response = apt_remote_api.delete(remote_repository.pulp_href)
    monitor_task(response.task)
    with pytest.raises(ApiException) as exc:
        apt_remote_api.read(remote_repository.pulp_href)
    assert exc.value.status == 404


@pytest.mark.parallel
def test_remote_repository_download_policies(
    apt_remote_api, gen_object_with_cleanup, gen_verbose_remote_data
):
    """Verify download policy behavior for valid and invalid values.
    In Pulp 3, there are different download policies.
    This test targets the following testing scenarios:

    1. Creating a remote without a download policy.
       Verify the creation is successful and the immediate policy is applied.
    2. Change the remote policy from default.
       Verify the change is successful.
    3. Attempt to change the remote policy to an invalid string.
       Verify an `ApiException` is given for the invalid policy as well
       as the policy remaining unchanged.

    For more information on the remote policies, see the Pulp3
    API on an installed server:

    * `/pulp/api/v3/docs/#operation`

    This test targets the following issues:

    * `Pulp #4420 <https://pulp.plan.io/issues/4420>`_
    * `Pulp #3763 <https://pulp.plan.io/issues/3763>`_
    """
    body = gen_verbose_remote_data()
    policies = DOWNLOAD_POLICIES

    del body["policy"]
    repo = gen_object_with_cleanup(apt_remote_api, body)
    assert repo.policy == "immediate"

    changed_policy = choice([item for item in policies if item != "immediate"])
    response = apt_remote_api.partial_update(repo.pulp_href, {"policy": changed_policy})
    monitor_task(response.task)
    repo = apt_remote_api.read(repo.pulp_href)
    assert repo.policy == changed_policy

    repo_snapshot = apt_remote_api.read(repo.pulp_href)
    with pytest.raises(ApiException) as exc:
        apt_remote_api.partial_update(repo.pulp_href, {"policy": utils.uuid4()})
    assert exc.value.status == 400
    repo = apt_remote_api.read(repo.pulp_href)
    assert repo_snapshot.policy == repo.policy


@pytest.fixture
def verbose_remote_data(gen_verbose_remote_data):
    """Generates semi-random dict for use in defining a remote to use for multiple test cases."""
    return gen_verbose_remote_data()


@pytest.fixture
def remote_repository(apt_remote_api, gen_object_with_cleanup, verbose_remote_data):
    """Generates a remote repository to use for testing."""
    return gen_object_with_cleanup(apt_remote_api, verbose_remote_data)


@pytest.fixture
def gen_verbose_remote_data():
    """Return a semi-random dict for use in defining a remote.
    For most tests, it's desirable to create remotes with as few attributes
    as possible, so that the tests can specifically target and attempt to break
    specific features. This module specifically targets remotes, so it makes
    sense to provide as many attributes as possible.
    Note that 'username' and 'password' are write-only attributes.
    """

    def _gen_verbose_remote_data():
        attrs = gen_deb_remote()
        attrs.update(
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
        return attrs

    return _gen_verbose_remote_data
