# -*- coding: utf-8 -*-

from pulp.common import constants as pulp_constants
from ...testbase import PulpClientTests

from pulp_deb.extensions.admin import repo_list
from pulp_deb.common import constants, ids


class RepoListCommandTests(PulpClientTests):
    def test_get_repositories(self):
        # Setup
        repos = [
            {
                'id': 'matching',
                'notes': {pulp_constants.REPO_NOTE_TYPE_KEY:
                          constants.REPO_NOTE_PKG, },
                'importers': [
                    {'config': {}, 'id': ids.TYPE_ID_IMPORTER}],
                'distributors': [{'id': ids.TYPE_ID_DISTRIBUTOR}],
            },
            {
                'id': 'no-importers',
                'notes': {pulp_constants.REPO_NOTE_TYPE_KEY:
                          constants.REPO_NOTE_PKG, },
                'importers': [],
                'distributors': [{'id': ids.TYPE_ID_DISTRIBUTOR}],
            },
            {'id': 'non-rpm-repo', 'notes': {}}]
        self.server_mock.request.return_value = 200, repos
        distributor_list = [ids.TYPE_ID_DISTRIBUTOR]

        # Test
        command = repo_list.RepoListCommand(self.context)
        repos = command.get_repositories({})

        # Verify
        self.assertEqual(2, len(repos))
        self.assertEqual(repos[0]['id'], 'matching')
        self.assertEqual(repos[1]['id'], 'no-importers')

        # Check that the distributors and importer are present
        self.assertEqual(len(repos[0]['distributors']), 1)
        for distributor in repos[0]['distributors']:
            self.assertTrue(distributor['id'] in distributor_list)
            distributor_list.remove(distributor['id'])

        self.assertEqual(len(repos[0]['importers']), 1)
        self.assertEqual(repos[0]['importers'][0]['id'],
                         ids.TYPE_ID_IMPORTER)

        # Check the importer is not present
        self.assertEqual(len(repos[1]['importers']), 0)
        self.assertRaises(IndexError, lambda: repos[1]['importers'][0])

    def test_get_repositories_no_details(self):
        # Setup
        repos = [
            {'id': 'foo',
             'display_name': 'bar',
             'notes': {pulp_constants.REPO_NOTE_TYPE_KEY:
                       constants.REPO_NOTE_PKG, }}
        ]
        self.server_mock.request.return_value = 200, repos

        # Test
        command = repo_list.RepoListCommand(self.context)
        repos = command.get_repositories({})

        # Verify
        self.assertEqual(1, len(repos))
        self.assertEqual(repos[0]['id'], 'foo')
        self.assertTrue('importers' not in repos[0])
        self.assertTrue('distributors' not in repos[0])

    def test_get_repositories_strip_ssl_cert(self):
        # Setup
        repos = [
            {'id': 'matching',
             'notes': {pulp_constants.REPO_NOTE_TYPE_KEY:
                       constants.REPO_NOTE_PKG, },
             'importers': [{'config': {'ssl_client_cert': 'foo'}}],
             'distributors': []},
            {'id': 'non-rpm-repo', 'notes': {}}]
        self.server_mock.request.return_value = 200, repos

        # Test
        command = repo_list.RepoListCommand(self.context)
        repos = command.get_repositories({})

        # Verify
        imp_config = repos[0]['importers'][0]['config']
        self.assertTrue('ssl_client_cert' not in imp_config)
        self.assertTrue('feed_ssl_configured' in imp_config)
        self.assertEqual(imp_config['feed_ssl_configured'], 'True')

    def test_get_repositories_strip_ssl_key(self):
        # Setup
        repos = [
            {'id': 'matching',
             'notes': {pulp_constants.REPO_NOTE_TYPE_KEY:
                       constants.REPO_NOTE_PKG, },
             'importers': [{'config': {'ssl_client_key': 'foo'}}],
             'distributors': []},
            {'id': 'non-rpm-repo', 'notes': {}}]
        self.server_mock.request.return_value = 200, repos

        # Test
        command = repo_list.RepoListCommand(self.context)
        repos = command.get_repositories({})

        # Verify
        imp_config = repos[0]['importers'][0]['config']
        self.assertTrue('ssl_client_key' not in imp_config)
        self.assertTrue('feed_ssl_configured' in imp_config)
        self.assertEqual(imp_config['feed_ssl_configured'], 'True')

    def test_get_other_repositories(self):
        # Setup
        repos = [
            {'repo_id': 'matching',
             'notes': {pulp_constants.REPO_NOTE_TYPE_KEY:
                       constants.REPO_NOTE_PKG},
             'distributors': [{'id': ids.TYPE_ID_DISTRIBUTOR}]},
            {'repo_id': 'non-rpm-repo-1', 'notes': {}}]
        self.server_mock.request.return_value = 200, repos

        # Test
        command = repo_list.RepoListCommand(self.context)
        repos = command.get_other_repositories({})

        # Verify
        self.assertEqual(1, len(repos))
        self.assertEqual(repos[0]['repo_id'], 'non-rpm-repo-1')
