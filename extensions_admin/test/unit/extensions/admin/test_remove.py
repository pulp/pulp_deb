import mock
from pulp.client.commands.unit import UnitRemoveCommand

from ...testbase import PulpClientTests
from pulp_deb.extensions.admin import remove as remove_commands
from pulp_deb.common.ids import TYPE_ID_DEB
from pulp_deb.extensions.admin.remove import BaseRemoveCommand


class BaseRemoveCommandTests(PulpClientTests):
    def setUp(self):
        super(BaseRemoveCommandTests, self).setUp()

        self.command = BaseRemoveCommand(self.context, 'remove')

    def test_structure(self):
        self.assertTrue(isinstance(self.command, UnitRemoveCommand))

    @mock.patch('pulp_deb.extensions.admin.units_display.get_formatter_for_type')  # noqa
    def test_get_formatter_for_type(self, mock_display):
        # Setup
        fake_units = 'u'
        fake_task = mock.MagicMock()
        fake_task.result = fake_units

        # Test
        self.command.get_formatter_for_type('foo-type')

        # Verify
        mock_display.assert_called_once_with('foo-type')


class PackageRemoveCommandTests(PulpClientTests):
    """
    Simply verifies the criteria_utils is called from the overridden methods.
    """

    @mock.patch('pulp.client.commands.unit.UnitRemoveCommand._parse_key_value')
    def test_key_value(self, mock_parse):
        command = remove_commands.DebRemoveCommand(self.context, 'copy')
        command._parse_key_value('foo')
        mock_parse.assert_called_once_with('foo')

    @mock.patch('pulp.client.commands.unit.UnitRemoveCommand._parse_sort')
    def test_sort(self, mock_parse):
        command = remove_commands.DebRemoveCommand(self.context, 'copy')
        command._parse_sort('foo')
        mock_parse.assert_called_once_with('foo')

    @mock.patch('pulp.client.commands.unit.UnitRemoveCommand.modify_user_input')  # noqa
    def test_modify_user_input(self, mock_super):
        command = remove_commands.DebRemoveCommand(self.context, 'remove')
        user_input = {'a': 'a'}
        command.modify_user_input(user_input)

        # The super call is required.
        self.assertEqual(1, mock_super.call_count)

        # The user_input variable itself should be modified.
        self.assertEqual(user_input, {'a': 'a'})


class RemoveCommandsTests(PulpClientTests):
    """
    The command implementations are simply configuration to the base commands,
    so rather than re-testing the functionality of the base commands, they
    simply assert that the configuration is correct.
    """

    def test_deb_remove_command(self):
        # Test
        command = remove_commands.DebRemoveCommand(self.context)

        # Verify
        self.assertTrue(isinstance(command, BaseRemoveCommand))
        self.assertEqual(command.name, TYPE_ID_DEB)
        self.assertEqual(command.description, remove_commands.DESC_DEB)
        self.assertEqual(command.type_id, TYPE_ID_DEB)
