import unittest
import types

from mock import Mock, MagicMock
from pulp.common.constants import REPO_NOTE_TYPE_KEY
from pulp.common.plugins.importer_constants import KEY_FEED
from pulp.devel.unit.util import compare_dict

from pulp_deb.common import constants
from pulp_deb.extensions.admin import cudl


class TestCreateDebrRepositoryCommand(unittest.TestCase):
    def test_default_notes(self):
        # make sure this value is set and is correct
        self.assertEqual(cudl.CreateDebRepositoryCommand.default_notes.get(REPO_NOTE_TYPE_KEY),
                         constants.REPO_NOTE_DEB)

    def test_importer_id(self):
        # this value is required to be set, so just make sure it's correct
        self.assertEqual(cudl.CreateDebRepositoryCommand.IMPORTER_TYPE_ID,
                         constants.WEB_IMPORTER_TYPE_ID)

    def test_describe_distributors(self):
        command = cudl.CreateDebRepositoryCommand(Mock())
        user_input = {cudl.OPT_AUTO_PUBLISH.keyword: True}
        result = command._describe_distributors(user_input)
        target_result = {'distributor_id': constants.CLI_WEB_DISTRIBUTOR_ID,
                         'distributor_type_id': constants.WEB_DISTRIBUTOR_TYPE_ID,
                         'distributor_config': {},
                         'auto_publish': True}
        compare_dict(result[0], target_result)

    def test_describe_distributors_override_auto_publish(self):
        command = cudl.CreateDebRepositoryCommand(Mock())
        user_input = {
            cudl.OPT_AUTO_PUBLISH.keyword: False
        }
        result = command._describe_distributors(user_input)
        self.assertEquals(result[0]["auto_publish"], False)

    def test_describe_importers(self):
        command = cudl.CreateDebRepositoryCommand(Mock())
        user_input = {}
        result = command._parse_importer_config(user_input)
        target_result = {}
        compare_dict(result, target_result)

    def test_describe_set_packages_file_path(self):
        command = cudl.CreateDebRepositoryCommand(Mock())
        user_input = {'package-file-path': 'foo/bar'}
        result = command._parse_importer_config(user_input)
        target_result = {'package-file-path': 'foo/bar'}
        compare_dict(result, target_result)


class TestUpdateDebRepositoryCommand(unittest.TestCase):
    def setUp(self):
        self.context = Mock()
        self.context.config = {'output': {'poll_frequency_in_seconds': 3}}
        self.command = cudl.UpdateDebRepositoryCommand(self.context)
        self.command.poll = Mock()
        self.mock_repo_response = Mock(response_body={})
        self.context.server.repo.repository.return_value = self.mock_repo_response

    def test_run_with_importer_config(self):
        user_input = {
            'repo-id': 'foo-repo',
            'package-file-path': 'foo/bar',
            KEY_FEED: 'blah'
        }
        self.command.run(**user_input)

        expected_importer_config = {KEY_FEED: 'blah',
                                    'package-file-path': 'foo/bar'}

        self.context.server.repo.update.assert_called_once_with('foo-repo', {},
                                                                expected_importer_config, None)

    def test_repo_update_distributors(self):
        user_input = {
            'auto-publish': False,
            'repo-id': 'foo-repo'
        }
        self.command.run(**user_input)

        repo_config = {}
        dist_config = {constants.CLI_WEB_DISTRIBUTOR_ID: {'auto_publish': False}}
        self.context.server.repo.update.assert_called_once_with('foo-repo', repo_config,
                                                                None, dist_config)


class TestListDebRepositoriesCommand(unittest.TestCase):
    def setUp(self):
        self.context = Mock()
        self.context.config = {'output': {'poll_frequency_in_seconds': 3}}

    def test_get_all_repos(self):
        self.context.server.repo.repositories.return_value.response_body = 'foo'
        command = cudl.ListDebRepositoriesCommand(self.context)
        result = command._all_repos({'bar': 'baz'})
        self.context.server.repo.repositories.assert_called_once_with({'bar': 'baz'})
        self.assertEquals('foo', result)

    def test_get_all_repos_caches_results(self):
        command = cudl.ListDebRepositoriesCommand(self.context)
        command.all_repos_cache = 'foo'
        result = command._all_repos({'bar': 'baz'})
        self.assertFalse(self.context.server.repo.repositories.called)
        self.assertEquals('foo', result)

    def test_get_repositories(self):
        # Setup
        repos = [
            {
                'id': 'matching',
                'notes': {REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_DEB, },
                'importers': [
                    {'config': {}}
                ],
                'distributors': [
                    {'id': constants.CLI_WEB_DISTRIBUTOR_ID}
                ]
            },
            {'id': 'non-rpm-repo',
             'notes': {}}
        ]
        self.context.server.repo.repositories.return_value.response_body = repos

        # Test
        command = cudl.ListDebRepositoriesCommand(self.context)
        repos = command.get_repositories({})

        # Verify
        self.assertEqual(1, len(repos))
        self.assertEqual(repos[0]['id'], 'matching')

    def test_get_repositories_no_details(self):
        # Setup
        repos = [
            {
                'id': 'foo',
                'display_name': 'bar',
                'notes': {REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_DEB, }
            }
        ]
        self.context.server.repo.repositories.return_value.response_body = repos

        # Test
        command = cudl.ListDebRepositoriesCommand(self.context)
        repos = command.get_repositories({})

        # Verify
        self.assertEqual(1, len(repos))
        self.assertEqual(repos[0]['id'], 'foo')
        self.assertTrue('importers' not in repos[0])
        self.assertTrue('distributors' not in repos[0])

    def test_get_other_repositories(self):
        # Setup
        repos = [
            {
                'repo_id': 'matching',
                'notes': {REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_DEB, },
                'distributors': [
                    {'id': constants.CLI_WEB_DISTRIBUTOR_ID}
                ]
            },
            {
                'repo_id': 'non-deb-repo-1',
                'notes': {}
            }
        ]
        self.context.server.repo.repositories.return_value.response_body = repos

        # Test
        command = cudl.ListDebRepositoriesCommand(self.context)
        repos = command.get_other_repositories({})

        # Verify
        self.assertEqual(1, len(repos))
        self.assertEqual(repos[0]['repo_id'], 'non-deb-repo-1')


class TestDebCopyCommand(unittest.TestCase):
    def test_setup(self):
        mock_context = MagicMock()
        command = cudl.CopyDebUnitCommand(mock_context)
        self.assertEquals(constants.DEB_TYPE_ID, command.type_id)

    def test_get_formatter(self):
        mock_context = MagicMock()
        command = cudl.CopyDebUnitCommand(mock_context)
        self.assertIsInstance(command.get_formatter_for_type(constants.DEB_TYPE_ID),
                              types.FunctionType)
        self.assertRaises(ValueError, command.get_formatter_for_type, 'fooType')
