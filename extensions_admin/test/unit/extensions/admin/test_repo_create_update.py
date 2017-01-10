from pulp.client.commands import options
from pulp.client.commands.repo import cudl, importer_config
from pulp.client.commands.repo.importer_config import ImporterConfigMixin
from pulp.client.extensions.core import TAG_SUCCESS
from pulp.common.compat import json
from pulp.common.plugins import importer_constants as constants

from pulp_deb.common import ids
from pulp_deb.extensions.admin import repo_options
from pulp_deb.extensions.admin import repo_create_update

from ...testbase import PulpClientTests


class RepoCreateCommandTests(PulpClientTests):
    def setUp(self):
        super(RepoCreateCommandTests, self).setUp()

        self.options_bundle = importer_config.OptionsBundle()

    def test_create_structure(self):
        command = repo_create_update.PkgRepoCreateCommand(self.context)

        self.assertTrue(isinstance(command, ImporterConfigMixin))

        # Ensure the required option groups
        found_group_names = set([o.name for o in command.option_groups])
        self.assertTrue(repo_options.NAME_PUBLISHING in found_group_names)

        # Ensure the correct method is wired up
        self.assertEqual(command.method, command.run)

        # Ensure the correct metadata
        self.assertEqual(command.name, 'create')
        self.assertEqual(command.description, cudl.DESC_CREATE)

    def test_run(self):
        # Setup

        data = {
            options.OPTION_REPO_ID.keyword: 'test-repo',
            options.OPTION_NAME.keyword: 'Test Name',
            options.OPTION_DESCRIPTION.keyword: 'Test Description',
            options.OPTION_NOTES.keyword: {'a': 'a'},
            self.options_bundle.opt_feed.keyword: 'http://localhost',
            self.options_bundle.opt_validate.keyword: True,
            self.options_bundle.opt_remove_missing.keyword: True,
            repo_options.OPT_SKIP.keyword: [ids.TYPE_ID_DEB],
            repo_options.OPT_RELATIVE_URL.keyword: '/repo',
            repo_options.OPT_SERVE_HTTP.keyword: True,
            repo_options.OPT_SERVE_HTTPS.keyword: True,
        }

        self.server_mock.request.return_value = 201, {}

        # Test
        command = repo_create_update.PkgRepoCreateCommand(self.context)
        command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)

        self.assertEqual(body['display_name'], 'Test Name')
        self.assertEqual(body['description'], 'Test Description')
        self.assertEqual(body['notes'], {'_repo-type': 'deb-repo', 'a': 'a'})

        self.assertEqual(ids.TYPE_ID_IMPORTER, body['importer_type_id'])
        importer_config = body['importer_config']
        self.assertEqual(importer_config[constants.KEY_FEED], 'http://localhost')
        self.assertEqual(importer_config[repo_create_update.CONFIG_KEY_SKIP], [ids.TYPE_ID_DEB])
        self.assertEqual(importer_config[constants.KEY_UNITS_REMOVE_MISSING], True)

        # The API will be changing to be a dict for each distributor, not a
        # list. This code will have to change to look up the parts by key
        # instead of index.

        yum_distributor = body['distributors'][0]
        self.assertEqual(ids.TYPE_ID_DISTRIBUTOR, yum_distributor['distributor_type_id'])
        self.assertEqual(True, yum_distributor['auto_publish'])
        self.assertEqual(ids.TYPE_ID_DISTRIBUTOR, yum_distributor['distributor_id'])

        yum_config = yum_distributor['distributor_config']
        self.assertEqual(yum_config['relative_url'], '/repo')
        self.assertEqual(yum_config['http'], True)
        self.assertEqual(yum_config['https'], True)
        self.assertEqual(yum_config['skip'], [ids.TYPE_ID_DEB])

        self.assertEqual([TAG_SUCCESS], self.prompt.get_write_tags())

    def test_run_through_cli(self):
        # Setup
        self.server_mock.request.return_value = 201, {}

        # Test
        command = repo_create_update.PkgRepoCreateCommand(self.context)
        self.cli.add_command(command)
        cmd = ["create", "--repo-id", "r", "--validate", "true"]
        self.cli.run(cmd)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)

        self.assertEqual(body['id'], 'r')
        self.assertEqual(body['importer_config'][constants.KEY_VALIDATE],
                         True)  # not the string "true"
        dconfig = body['distributors'][0]['distributor_config']
        self.assertEquals(
            dict(http=False, https=True, relative_url='r'),
            dconfig)

    def test_process_relative_url_with_feed(self):
        # Setup
        repo_id = 'feed-repo'
        importer_config = {constants.KEY_FEED: 'http://localhost/foo/bar/baz'}
        distributor_config = {}  # will be populated in this call
        command = repo_create_update.PkgRepoCreateCommand(self.context)

        # Test
        command.process_relative_url(repo_id, importer_config, distributor_config)

        # Verify
        self.assertTrue('relative_url' in distributor_config)
        self.assertEqual(distributor_config['relative_url'], '/foo/bar/baz')

    def test_process_relative_url_no_feed(self):
        # Setup
        repo_id = 'no-feed-repo'
        importer_config = {}
        distributor_config = {}  # will be populated in this call
        command = repo_create_update.PkgRepoCreateCommand(self.context)

        # Test
        command.process_relative_url(repo_id, importer_config, distributor_config)

        # Verify
        self.assertTrue('relative_url' in distributor_config)
        self.assertEqual(distributor_config['relative_url'], repo_id)

    def test_process_relative_url_specified(self):
        # Setup
        repo_id = 'specified'
        importer_config = {}
        distributor_config = {'relative_url': 'wombat'}
        command = repo_create_update.PkgRepoCreateCommand(self.context)

        # Test
        command.process_relative_url(repo_id, importer_config, distributor_config)

        # Verify
        self.assertTrue('relative_url' in distributor_config)
        self.assertEqual(distributor_config['relative_url'], 'wombat')

    def test_process_yum_distributor_serve_protocol_defaults(self):
        # Setup
        distributor_config = {}  # will be populated in this call
        command = repo_create_update.PkgRepoCreateCommand(self.context)

        # Test
        command.process_distributor_serve_protocol(distributor_config)

        # Verify
        self.assertEqual(distributor_config['http'], False)
        self.assertEqual(distributor_config['https'], True)

    def test_process_distributor_serve_protocol_new_values(self):
        # Setup
        distributor_config = {'http': True, 'https': False}
        command = repo_create_update.PkgRepoCreateCommand(self.context)

        # Test
        command.process_distributor_serve_protocol(distributor_config)

        # Verify
        self.assertEqual(distributor_config['http'], True)
        self.assertEqual(distributor_config['https'], False)


class RepoUpdateCommandTests(PulpClientTests):
    def setUp(self):
        super(RepoUpdateCommandTests, self).setUp()
        self.options_bundle = importer_config.OptionsBundle()

    def test_create_structure(self):
        command = repo_create_update.PkgRepoUpdateCommand(self.context)

        self.assertTrue(isinstance(command, ImporterConfigMixin))

        # Ensure the required option groups
        found_group_names = set([o.name for o in command.option_groups])
        self.assertTrue(repo_options.NAME_PUBLISHING in found_group_names)

        # Ensure the correct method is wired up
        self.assertEqual(command.method, command.run)

        # Ensure the correct metadata
        self.assertEqual(command.name, 'update')
        self.assertEqual(command.description, cudl.DESC_UPDATE)

    def test_run_202(self):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword: 'test-repo',
            options.OPTION_NAME.keyword: 'Test Name',
            options.OPTION_DESCRIPTION.keyword: 'Test Description',
            options.OPTION_NOTES.keyword: {'b': 'b'},
            self.options_bundle.opt_feed.keyword: 'http://localhost',
            repo_options.OPT_SERVE_HTTP.keyword: True,
            repo_options.OPT_SERVE_HTTPS.keyword: True,
            repo_options.OPT_SKIP.keyword: [ids.TYPE_ID_DEB],
        }

        self.server_mock.request.return_value = 202, {}

        # Test
        command = repo_create_update.PkgRepoUpdateCommand(self.context)
        command.run(**data)

        # Verify that things at least didn't blow up, which they were for BZ 1096931
        self.assertEqual(1, self.server_mock.request.call_count)

    def test_run(self):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword: 'test-repo',
            options.OPTION_NAME.keyword: 'Test Name',
            options.OPTION_DESCRIPTION.keyword: 'Test Description',
            options.OPTION_NOTES.keyword: {'b': 'b'},
            self.options_bundle.opt_feed.keyword: 'http://localhost',
            repo_options.OPT_SERVE_HTTP.keyword: True,
            repo_options.OPT_SERVE_HTTPS.keyword: True,
            repo_options.OPT_SKIP.keyword: [ids.TYPE_ID_DEB],
        }

        self.server_mock.request.return_value = 200, {}

        # Test
        command = repo_create_update.PkgRepoUpdateCommand(self.context)
        command.run(**data)

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)

        delta = body['delta']
        self.assertEqual(delta['display_name'], 'Test Name')
        self.assertEqual(delta['description'], 'Test Description')
        self.assertEqual(delta['notes'], {'b': 'b'})

        yum_imp_config = body['importer_config']
        self.assertEqual(yum_imp_config[constants.KEY_FEED], 'http://localhost')
        self.assertEqual(yum_imp_config[repo_create_update.CONFIG_KEY_SKIP], [ids.TYPE_ID_DEB])

        yum_dist_config = body['distributor_configs'][ids.TYPE_ID_DISTRIBUTOR]
        self.assertEqual(yum_dist_config['http'], True)
        self.assertEqual(yum_dist_config['https'], True)
        self.assertEqual(yum_dist_config['skip'], [ids.TYPE_ID_DEB])

    def test_run_through_cli(self):
        """
        See the note in test_run_through_cli under the create tests for
        more info.
        """

        # Setup
        self.server_mock.request.return_value = 201, {}

        # Test
        command = repo_create_update.PkgRepoUpdateCommand(self.context)
        self.cli.add_command(command)
        cmd = ("update --repo-id r --validate true")
        self.cli.run(cmd.split())

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)

        self.assertEqual(body['importer_config'][constants.KEY_VALIDATE],
                         True)  # not the string "true"

    def test_remove_skip_types(self):
        # Setup
        self.server_mock.request.return_value = 201, {}

        # Test
        command = repo_create_update.PkgRepoUpdateCommand(self.context)
        self.cli.add_command(command)
        cmd = ("update --repo-id r --skip")
        self.cli.run(cmd.split() + [''])

        # Verify
        self.assertEqual(1, self.server_mock.request.call_count)

        body = self.server_mock.request.call_args[0][2]
        body = json.loads(body)

        self.assertEqual(body['importer_config']['type_skip_list'], None)
        self.assertEqual(body['distributor_configs'][ids.TYPE_ID_DISTRIBUTOR]['skip'], None)
