import os

from mock import Mock
from .... import testbase

from pulp.plugins.config import PluginCallConfiguration

from pulp_deb.common import constants
from pulp_deb.plugins.distributors import configuration


class TestConfigurationGetters(testbase.TestCase):

    def setUp(self):
        super(TestConfigurationGetters, self).setUp()
        self.publish_dir = os.path.join(self.work_dir, 'publish')
        self.repo_working_dir = os.path.join(self.work_dir, 'work')

        self.repo = Mock(id='foo', working_dir=self.repo_working_dir)
        self.config = PluginCallConfiguration(
            {constants.PUBLISH_HTTP_KEYWORD: True,
             constants.PUBLISH_HTTPS_KEYWORD: True,
             constants.PUBLISH_RELATIVE_URL_KEYWORD: None,
             constants.HTTP_PUBLISH_DIR_KEYWORD: self.publish_dir + '/http',
             constants.HTTPS_PUBLISH_DIR_KEYWORD: self.publish_dir + '/https',
             }, {})

    def test_get_master_publish_dir(self):
        directory = configuration.get_master_publish_dir(self.repo,
                                                         'deb_distributor')
        self.assertEquals(directory,
                          '/var/lib/pulp/published/deb/master/deb_distributor/foo')

    def test_get_http_publish_dir(self):
        directory = configuration.get_http_publish_dir(self.config)
        self.assertEquals(directory, os.path.join(self.publish_dir, 'http'))

    def test_get_https_publish_dir(self):
        directory = configuration.get_https_publish_dir(self.config)
        self.assertEquals(directory, os.path.join(self.publish_dir, 'https'))

    def test_get_repo_relative_path(self):
        directory = configuration.get_repo_relative_path(self.repo, self.config)
        self.assertEquals(directory, self.repo.id)

    def test_get_repo_relative_path__with_slash(self):
        cfg = self.config.__class__(dict(relative_url='/a/b'), dict())
        directory = configuration.get_repo_relative_path(self.repo, cfg)
        self.assertEquals(directory, 'a/b')


class TestValidateConfig(testbase.TestCase):
    def _config_conduit(self, empty=True):
        ret = Mock()
        if empty:
            ret.get_repo_distributors_by_relative_url.return_value = []
        else:
            ret.get_repo_distributors_by_relative_url.return_value = [
                {
                    'repo_id': 'foo',
                    'config': {
                        'http': True,
                        'https': True,
                        'relative_url': '/bar',
                    },
                },
            ]
        return ret

    def test_server_url_fully_qualified(self):
        config = PluginCallConfiguration(
            dict(http=True, https=False, relative_url=None), {})
        repo = Mock(repo_id='foo', working_dir=self.work_dir)
        conduit = self._config_conduit()

        self.assertEquals((True, None),
                          configuration.validate_config(repo, config, conduit))

    def test_update_distributor_same_url(self):
        config = PluginCallConfiguration(
            dict(http=True, https=False, relative_url='bar'), {})
        repo = Mock(repo_id='foo', working_dir=self.work_dir)
        conduit = self._config_conduit(False)

        self.assertEquals((True, None),
                          configuration.validate_config(repo, config, conduit))

    def test_create_distributor_same_url(self):
        config = PluginCallConfiguration(
            dict(http=True, https=False, relative_url='bar'), {})
        repo = Mock(repo_id='fool', working_dir=self.work_dir)
        conduit = self._config_conduit(False)

        self.assertEquals((False, 'Relative URL [bar] for repository [fool] ' +
                           'conflicts with existing relative URL [/bar] ' +
                           'for repository [foo]'),
                          configuration.validate_config(repo, config, conduit))

    def test__repocfg_gpg_cmd(self):
        config = PluginCallConfiguration(
            dict(http=True, https=False, relative_url='fool'),
            dict(gpg_cmd="/bin/true should fail"))
        repo = Mock(repo_id='fool', working_dir=self.work_dir)
        conduit = self._config_conduit()

        expected_reason = ('Configuration key [gpg_cmd] is not allowed '
                           'in repository plugin configuration')
        self.assertEquals((False, expected_reason),
                          configuration.validate_config(repo, config, conduit))
