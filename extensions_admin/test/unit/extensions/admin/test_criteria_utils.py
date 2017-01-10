# -*- coding: utf-8 -*-

import unittest

from pulp.client.commands.criteria import CriteriaCommand

from pulp_rpm.common import version_utils
from pulp_deb.extensions.admin import criteria_utils


class ParseKeyValueTests(unittest.TestCase):
    def test_parse(self):
        # Setup
        user_input = ['name=foo', 'version=1.0', 'release=2', 'license=GPL']

        # Test
        parsed = criteria_utils.parse_key_value(user_input)

        # Verify
        self.assertEqual(4, len(parsed))
        parsed.sort(key=lambda x: x[0])
        self.assertEqual(parsed[0][0], 'license')
        self.assertEqual(parsed[0][1], 'GPL')
        self.assertEqual(parsed[1][0], 'name')
        self.assertEqual(parsed[1][1], 'foo')
        self.assertEqual(parsed[2][0], version_utils.RELEASE_INDEX)
        self.assertEqual(parsed[2][1], version_utils.encode('2'))
        self.assertEqual(parsed[3][0], version_utils.VERSION_INDEX)
        self.assertEqual(parsed[3][1], version_utils.encode('1.0'))


class ParseSortTests(unittest.TestCase):
    def test_parse(self):
        # Setup
        user_input = ['name,ascending', 'version,descending', 'release,ascending']

        # Test
        parsed = criteria_utils.parse_sort(CriteriaCommand, user_input)

        # Verify
        self.assertEqual(3, len(parsed))
        parsed.sort(key=lambda x: x[0])
        self.assertEqual(parsed[0][0], 'name')
        self.assertEqual(parsed[0][1], 'ascending')
        self.assertEqual(parsed[1][0], version_utils.RELEASE_INDEX)
        self.assertEqual(parsed[1][1], 'ascending')
        self.assertEqual(parsed[2][0], version_utils.VERSION_INDEX)
        self.assertEqual(parsed[2][1], 'descending')
