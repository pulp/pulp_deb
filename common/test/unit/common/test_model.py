from hashlib import sha256
from unittest import TestCase

from pulp_deb.common.model import generate_remote_id


class TestUtils(TestCase):

    def test_generate_remote_id(self):
        url = 'url-test'
        remote_id = generate_remote_id(url)
        h = sha256()
        h.update(url)
        self.assertEqual(remote_id, h.hexdigest())
