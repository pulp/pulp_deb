import os
import shutil
import tempfile
import unittest

from mock import Mock

from pulp.plugins.config import PluginCallConfiguration

from pulp_deb.common import constants
from pulp_deb.plugins.distributors import configuration


class TestConfigurationGetters(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.publish_dir = os.path.join(self.working_directory, 'publish')
        self.repo_working = os.path.join(self.working_directory, 'work')

        self.repo = Mock(id='foo', working_dir=self.repo_working)
        self.config = PluginCallConfiguration({constants.DISTRIBUTOR_CONFIG_KEY_PUBLISH_DIRECTORY:
                                              self.publish_dir}, {})

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def test_get_root_publish_directory(self):
        directory = configuration.get_root_publish_directory(self.config)
        self.assertEquals(directory, self.publish_dir)

    def test_get_master_publish_dir(self):
        directory = configuration.get_master_publish_dir(self.repo, self.config)
        self.assertEquals(directory, os.path.join(self.publish_dir, 'master', self.repo.id))

    def test_get_web_publish_dir(self):
        directory = configuration.get_web_publish_dir(self.repo, self.config)
        self.assertEquals(directory, os.path.join(self.publish_dir, 'web', self.repo.id))

    def test_get_repo_relative_path(self):
        directory = configuration.get_repo_relative_path(self.repo, self.config)
        self.assertEquals(directory, self.repo.id)


class TestValidateConfig(unittest.TestCase):

    def test_server_url_fully_qualified(self):
        config = PluginCallConfiguration({}, {})
        self.assertEquals((True, None),
                          configuration.validate_config(config))
