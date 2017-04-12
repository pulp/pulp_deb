# -*- coding: utf-8 -*-

import mock
from ...testbase import PulpClientTests

from pulp_deb.extensions.admin import copy_commands
from pulp_deb.common.constants import CONFIG_RECURSIVE
from pulp_deb.common.ids import TYPE_ID_DEB


class RecursiveCopyCommandTests(PulpClientTests):
    """
    This test case isn't interested in testing the functionality of the base
    UnitCopyCommand class. It exists to test the customizations made on top of
    it, so don't expect there to be a ton going on in here.
    """

    def setUp(self):
        super(RecursiveCopyCommandTests, self).setUp()

        self.name = 'copy'
        self.description = 'fake-description'
        self.type_id = 'fake-type'
        self.command = copy_commands.RecursiveCopyCommand(
            self.context, self.name)

    def test_generate_override_config(self):
        # Test
        user_input = {copy_commands.FLAG_RECURSIVE.keyword: True}
        override_config = self.command.generate_override_config(**user_input)

        # Verify
        self.assertEqual(override_config, {CONFIG_RECURSIVE: True})

    def test_generate_override_config_no_recursive(self):
        # Test
        user_input = {copy_commands.FLAG_RECURSIVE.keyword: None}
        override_config = self.command.generate_override_config(**user_input)

        # Verify
        self.assertEqual(override_config, {})


class PackageCopyCommandTests(PulpClientTests):
    """
    Simply verifies the criteria_utils is called from the overridden methods.
    """

    @mock.patch('pulp.client.commands.unit.UnitCopyCommand._parse_key_value')
    def test_key_value(self, mock_parse):
        command = copy_commands.DebCopyCommand(self.context, 'copy')
        command._parse_key_value('foo')
        mock_parse.assert_called_once_with('foo')

    @mock.patch('pulp.client.commands.unit.UnitCopyCommand._parse_sort')
    def test_sort(self, mock_parse):
        command = copy_commands.DebCopyCommand(self.context, 'copy')
        command._parse_sort('foo')
        mock_parse.assert_called_once_with('foo')

    @mock.patch('pulp.client.commands.unit.UnitCopyCommand.modify_user_input')
    def test_modify_user_input(self, mock_super):
        command = copy_commands.DebCopyCommand(self.context, 'copy')
        user_input = {'a': 'a'}
        command.modify_user_input(user_input)

        # The super call is required.
        self.assertEqual(1, mock_super.call_count)

        # The user_input variable itself should be modified.
        self.assertEqual(user_input, {'a': 'a'})

    def test_get_formatter_for_type(self):
        command = copy_commands.DebCopyCommand(self.context)

        # get a formatter and make sure it can be used
        formatter = command.get_formatter_for_type(TYPE_ID_DEB)
        unit_string = formatter(
            {'name': 'package1', 'version': '1.2.3'})

        # make sure the name appears in the formatted string somewhere, which
        # seems like a reasonable assumption for any implementation of such
        # a formatter
        self.assertTrue(unit_string.find('package1') >= 0)


class OtherCopyCommandsTests(PulpClientTests):
    """
    Again, this test isn't concerned with testing the base command's
    functionality, but rather the correct usage of it. Given the size of the
    command code, rather than make a class per command, I
    lumping them all in here and doing one method per command.
    """

    def test_deb_copy_command(self):
        # Test
        command = copy_commands.DebCopyCommand(self.context)

        # Verify
        self.assertTrue(isinstance(command, copy_commands.RecursiveCopyCommand))
        self.assertEqual(command.name, TYPE_ID_DEB)
        self.assertEqual(command.description, copy_commands.DESC_DEB)
        self.assertEqual(command.type_id, TYPE_ID_DEB)

    def test_all_copy_command(self):
        # Test
        command = copy_commands.AllCopyCommand(self.context)

        # Verify
        self.assertTrue(isinstance(command,
                                   copy_commands.NonRecursiveCopyCommand))
        self.assertEqual(command.name, 'all')
        self.assertEqual(command.description, copy_commands.DESC_ALL)
        self.assertEqual(command.type_id, None)
