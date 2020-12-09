# coding=utf-8
"""Tests that CRUD deb remotes."""
from random import choice
import unittest

from pulp_smash import utils
from pulp_smash.pulp3.bindings import monitor_task

from pulp_deb.tests.functional.constants import DOWNLOAD_POLICIES, DEB_SIGNING_KEY
from pulp_deb.tests.functional.utils import (
    deb_remote_api,
    gen_deb_remote,
    skip_if,
)
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401

from pulpcore.client.pulp_deb.exceptions import ApiException


class CRUDRemotesTestCase(unittest.TestCase):
    """CRUD remotes."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.remote_api = deb_remote_api

    def test_01_create_remote(self):
        """Create a remote."""
        body = _gen_verbose_remote()
        type(self).remote = self.remote_api.create(body)
        for key in ("username", "password"):
            del body[key]
        for key, val in body.items():
            with self.subTest(key=key):
                self.assertEqual(self.remote.to_dict()[key], val, key)

    @skip_if(bool, "remote", False)
    def test_02_create_same_name(self):
        """Try to create a second remote with an identical name.

        See: `Pulp Smash #1055
        <https://github.com/pulp/pulp-smash/issues/1055>`_.
        """
        body = gen_deb_remote()
        body["name"] = self.remote.name
        with self.assertRaises(ApiException):
            self.remote_api.create(body)

    @skip_if(bool, "remote", False)
    def test_02_read_remote(self):
        """Read a remote by its href."""
        remote = self.remote_api.read(self.remote.pulp_href)
        for key, val in self.remote.to_dict().items():
            with self.subTest(key=key):
                self.assertEqual(remote.to_dict()[key], val, key)

    @skip_if(bool, "remote", False)
    def test_02_read_remotes(self):
        """Read a remote by its name."""
        page = self.remote_api.list(name=self.remote.name)
        self.assertEqual(len(page.results), 1)
        for key, val in self.remote.to_dict().items():
            with self.subTest(key=key):
                self.assertEqual(page.results[0].to_dict()[key], val, key)

    @skip_if(bool, "remote", False)
    def test_03_partially_update(self):
        """Update a remote using HTTP PATCH."""
        body = _gen_verbose_remote()
        response = self.remote_api.partial_update(self.remote.pulp_href, body)
        monitor_task(response.task)
        for key in ("username", "password"):
            del body[key]
        type(self).remote = self.remote_api.read(self.remote.pulp_href)
        for key, val in body.items():
            with self.subTest(key=key):
                self.assertEqual(self.remote.to_dict()[key], val, key)

    @skip_if(bool, "remote", False)
    def test_04_fully_update(self):
        """Update a remote using HTTP PUT."""
        body = _gen_verbose_remote()
        response = self.remote_api.update(self.remote.pulp_href, body)
        monitor_task(response.task)
        for key in ("username", "password"):
            del body[key]
        type(self).remote = self.remote_api.read(self.remote.pulp_href)
        for key, val in body.items():
            with self.subTest(key=key):
                self.assertEqual(self.remote.to_dict()[key], val, key)

    @skip_if(bool, "remote", False)
    def test_05_delete(self):
        """Delete a remote."""
        response = self.remote_api.delete(self.remote.pulp_href)
        monitor_task(response.task)
        with self.assertRaises(ApiException):
            self.remote_api.read(self.remote.pulp_href)


class CreateRemoteNoURLTestCase(unittest.TestCase):
    """Verify whether is possible to create a remote without a URL."""

    def test_all(self):
        """Verify whether is possible to create a remote without a URL.

        This test targets the following issues:

        * `Pulp #3395 <https://pulp.plan.io/issues/3395>`_
        * `Pulp Smash #984 <https://github.com/pulp/pulp-smash/issues/984>`_
        """
        body = gen_deb_remote()
        del body["url"]
        with self.assertRaises(ApiException):
            deb_remote_api.create(body)


class RemoteDownloadPolicyTestCase(unittest.TestCase):
    """Verify download policy behavior for valid and invalid values.

    In Pulp 3, there are are different download policies.

    This test targets the following testing scenarios:

    1. Creating a remote without a download policy.
       Verify the creation is successful and immediate it is policy applied.
    2. Change the remote policy from default.
       Verify the change is successful.
    3. Attempt to change the remote policy to an invalid string.
       Verify an ApiException is given for the invalid policy as well
       as the policy remaining unchanged.

    For more information on the remote policies, see the Pulp3
    API on an installed server:

    * /pulp/api/v3/docs/#operation`

    This test targets the following issues:

    * `Pulp #4420 <https://pulp.plan.io/issues/4420>`_
    * `Pulp #3763 <https://pulp.plan.io/issues/3763>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.remote_api = deb_remote_api
        cls.remote = {}
        cls.policies = DOWNLOAD_POLICIES
        cls.body = _gen_verbose_remote()

    @classmethod
    def tearDownClass(cls):
        """Clean class-wide variable."""
        results = cls.remote_api.list().to_dict()["results"]
        for result in results:
            cls.remote_api.delete(result["pulp_href"])

    def test_01_no_defined_policy(self):
        """Verify the default policy `immediate`.

        When no policy is defined, the default policy of `immediate`
        is applied.
        """
        del self.body["policy"]
        self.remote.update(self.remote_api.create(self.body).to_dict())
        self.assertEqual(self.remote["policy"], "immediate", self.remote)

    @skip_if(len, "policies", 1)
    def test_02_change_policy(self):
        """Verify ability to change policy to value other than the default.

        Update the remote policy to a valid value other than `immedaite`
        and verify the new set value.
        """
        changed_policy = choice([item for item in self.policies if item != "immediate"])
        response = self.remote_api.partial_update(
            self.remote["pulp_href"], {"policy": changed_policy}
        )
        monitor_task(response.task)
        self.remote.update(self.remote_api.read(self.remote["pulp_href"]).to_dict())
        self.assertEqual(self.remote["policy"], changed_policy, self.remote)

    @skip_if(bool, "remote", False)
    def test_03_invalid_policy(self):
        """Verify an invalid policy does not update the remote policy.

        Get the current remote policy.
        Attempt to update the remote policy to an invalid value.
        Verify the policy remains the same.
        """
        remote = self.remote_api.read(self.remote["pulp_href"]).to_dict()
        with self.assertRaises(ApiException):
            self.remote_api.partial_update(self.remote["pulp_href"], {"policy": utils.uuid4()})
        self.remote.update(self.remote_api.read(self.remote["pulp_href"]).to_dict())
        self.assertEqual(remote["policy"], self.remote["policy"], self.remote)


def _gen_verbose_remote():
    """Return a semi-random dict for use in defining a remote.

    For most tests, it's desirable to create remotes with as few attributes
    as possible, so that the tests can specifically target and attempt to break
    specific features. This module specifically targets remotes, so it makes
    sense to provide as many attributes as possible.

    Note that 'username' and 'password' are write-only attributes.
    """
    attrs = gen_deb_remote()
    attrs.update(
        {
            "password": utils.uuid4(),
            "username": utils.uuid4(),
            "policy": choice(DOWNLOAD_POLICIES),
            "distributions": "{} {}".format(utils.uuid4(), utils.uuid4()),
            "components": "{} {}".format(utils.uuid4(), utils.uuid4()),
            "architectures": "{} {}".format(utils.uuid4(), utils.uuid4()),
            "gpgkey": DEB_SIGNING_KEY,
        }
    )
    return attrs
