import mock

from pulp.bindings.responses import Response
from pulp.client.commands.criteria import DisplayUnitAssociationsCommand
from ...testbase import PulpClientTests

from pulp_deb.common import ids
from pulp_deb.extensions.admin import contents


class PackageSearchCommandTests(PulpClientTests):
    def test_structure(self):
        command = contents.BaseSearchCommand(self.context)
        self.assertTrue(isinstance(command, DisplayUnitAssociationsCommand))
        self.assertEqual(command.context, self.context)

    @mock.patch('pulp.client.commands.criteria.DisplayUnitAssociationsCommand._parse_key_value')
    def test_parse_key_value_override(self, mock_parse):
        command = contents.BaseSearchCommand(self.context)
        command._parse_key_value('test-data')
        mock_parse.assert_called_once_with('test-data')

    @mock.patch('pulp.client.commands.criteria.DisplayUnitAssociationsCommand._parse_sort')
    def test_parse_sort(self, mock_parse):
        command = contents.BaseSearchCommand(self.context)
        command._parse_sort('test-data')
        mock_parse.assert_called_once_with('test-data')

    @mock.patch('pulp.bindings.repository.RepositoryUnitAPI.search')
    def test_run_search(self, mock_search):
        # Setup
        mock_out = mock.MagicMock()
        units = [{'a': 'a', 'metadata': 'm'}]
        mock_search.return_value = Response(200, units)

        user_input = {
            'repo-id': 'repo-1',
            DisplayUnitAssociationsCommand.ASSOCIATION_FLAG.keyword: True,
        }

        # Test
        command = contents.BaseSearchCommand(self.context)
        command.run_search(['fake-type'], out_func=mock_out, **user_input)

        # Verify
        expected = {
            'type_ids': ['fake-type'],
            DisplayUnitAssociationsCommand.ASSOCIATION_FLAG.keyword: True,
        }
        mock_search.assert_called_once_with('repo-1', **expected)
        mock_out.assert_called_once_with(units)

    @mock.patch('pulp.bindings.repository.RepositoryUnitAPI.search')
    def test_run_search_no_details(self, mock_search):
        # Setup
        mock_out = mock.MagicMock()
        units = [{'a': 'a', 'metadata': 'm'}]
        mock_search.return_value = Response(200, units)

        user_input = {
            'repo-id': 'repo-1',
            DisplayUnitAssociationsCommand.ASSOCIATION_FLAG.keyword: False,
        }

        # Test
        command = contents.BaseSearchCommand(self.context)
        command.run_search(['fake-type'], out_func=mock_out, **user_input)

        # Verify
        expected = {
            'type_ids': ['fake-type'],
            DisplayUnitAssociationsCommand.ASSOCIATION_FLAG.keyword: False,
        }
        mock_search.assert_called_once_with('repo-1', **expected)
        # only the metadata due to no details
        mock_out.assert_called_once_with(['m'])

    @mock.patch('pulp.bindings.repository.RepositoryUnitAPI.search')
    def test_run_search_with_field_filters(self, mock_search):
        # Setup
        mock_out = mock.MagicMock()
        units = [{'a': 'a', 'metadata': 'm'}]
        mock_search.return_value = Response(200, units)

        user_input = {
            'repo-id': 'repo-1',
            DisplayUnitAssociationsCommand.ASSOCIATION_FLAG.keyword: False,
        }

        # Test
        command = contents.BaseSearchCommand(self.context)
        command.run_search([ids.TYPE_ID_DEB], out_func=mock_out, **user_input)

        # Verify
        expected = {
            'type_ids': [ids.TYPE_ID_DEB],
            DisplayUnitAssociationsCommand.ASSOCIATION_FLAG.keyword: False,
        }
        mock_search.assert_called_once_with('repo-1', **expected)
        mock_out.assert_called_once_with(
            ['m'],
            contents.FIELDS_BY_TYPE[ids.TYPE_ID_DEB])


class SearchDebCommand(PulpClientTests):
    def test_structure(self):
        command = contents.SearchDebCommand(self.context)
        self.assertTrue(isinstance(command, contents.BaseSearchCommand))
        self.assertEqual(command.context, self.context)
        self.assertEqual(command.name, ids.TYPE_ID_DEB)
        self.assertEqual(command.description, contents.DESC_DEB)
