# coding=utf-8
"""Tests that CRUD content_unit publishers."""
import unittest

from requests.exceptions import HTTPError

from pulp_smash import api, config
from pulp_smash.pulp3.constants import REPO_PATH
from pulp_smash.pulp3.utils import gen_repo

from pulp_deb.tests.functional.constants import DEB_PUBLISHER_PATH
from pulp_deb.tests.functional.utils import gen_deb_publisher, skip_if
from pulp_deb.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class CRUDPublishersTestCase(unittest.TestCase):
    """CRUD publishers."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables.

        In order to create a publisher a repository has to be created first.
        """
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)
        cls.publisher = {}
        cls.repo = cls.client.post(REPO_PATH, gen_repo())

    @classmethod
    def tearDownClass(cls):
        """Clean class-wide variable."""
        cls.client.delete(cls.repo['_href'])

    def test_01_create_publisher(self):
        """Create a publisher."""
        body = gen_deb_publisher()
        type(self).publisher = self.client.post(DEB_PUBLISHER_PATH, body)
        for key, val in body.items():
            with self.subTest(key=key):
                self.assertEqual(self.publisher[key], val)

    @skip_if(bool, 'publisher', False)
    def test_02_create_same_name(self):
        """Try to create a second publisher with an identical name.

        See: `Pulp Smash #1055
        <https://github.com/PulpQE/pulp-smash/issues/1055>`_.
        """
        body = gen_deb_publisher()
        body['name'] = self.publisher['name']
        with self.assertRaises(HTTPError):
            self.client.post(DEB_PUBLISHER_PATH, body)

    @skip_if(bool, 'publisher', False)
    def test_02_read_publisher(self):
        """Read a publisher by its href."""
        publisher = self.client.get(self.publisher['_href'])
        for key, val in self.publisher.items():
            with self.subTest(key=key):
                self.assertEqual(publisher[key], val)

    @skip_if(bool, 'publisher', False)
    def test_02_read_publishers(self):
        """Read a publisher by its name."""
        page = self.client.get(DEB_PUBLISHER_PATH, params={
            'name': self.publisher['name']
        })
        self.assertEqual(len(page['results']), 1)
        for key, val in self.publisher.items():
            with self.subTest(key=key):
                self.assertEqual(page['results'][0][key], val)

    @skip_if(bool, 'publisher', False)
    def test_03_partially_update(self):
        """Update a publisher using HTTP PATCH."""
        body = gen_deb_publisher()
        self.client.patch(self.publisher['_href'], body)
        type(self).publisher = self.client.get(self.publisher['_href'])
        for key, val in body.items():
            with self.subTest(key=key):
                self.assertEqual(self.publisher[key], val)

    @skip_if(bool, 'publisher', False)
    def test_04_fully_update(self):
        """Update a publisher using HTTP PUT."""
        body = gen_deb_publisher()
        self.client.put(self.publisher['_href'], body)
        type(self).publisher = self.client.get(self.publisher['_href'])
        for key, val in body.items():
            with self.subTest(key=key):
                self.assertEqual(self.publisher[key], val)

    @skip_if(bool, 'publisher', False)
    def test_05_delete(self):
        """Delete a publisher."""
        self.client.delete(self.publisher['_href'])
        with self.assertRaises(HTTPError):
            self.client.get(self.publisher['_href'])
