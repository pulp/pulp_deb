import os
import shutil
import tempfile
import unittest

from mock import Mock, patch, MagicMock

from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.distributor import Distributor
from pulp.plugins.model import Repository

from pulp_deb.common import constants
from pulp_deb.plugins.distributors import web


class TestEntryPoint(unittest.TestCase):
    def test_returns_importer(self):
        distributor, config = web.entry_point()

        self.assertTrue(issubclass(distributor, Distributor))

    def test_returns_config(self):
        distributor, config = web.entry_point()

        # make sure it's at least the correct type
        self.assertTrue(isinstance(config, dict))


class TestBasics(unittest.TestCase):

    def setUp(self):
        self.distributor = web.WebDistributor()
        self.working_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.working_dir)

    def test_metadata(self):
        metadata = web.WebDistributor.metadata()

        self.assertEqual(metadata['id'], constants.WEB_DISTRIBUTOR_TYPE_ID)
        self.assertTrue(len(metadata['display_name']) > 0)

    @patch('pulp_deb.plugins.distributors.web.configuration.get_master_publish_dir')
    @patch('pulp_deb.plugins.distributors.web.configuration.get_web_publish_dir')
    def test_distributor_removed(self, mock_web, mock_master):

        mock_web.return_value = os.path.join(self.working_dir, 'web')
        mock_master.return_value = os.path.join(self.working_dir, 'master')
        repo_working_dir = os.path.join(self.working_dir, 'working')
        os.makedirs(mock_web.return_value)
        os.makedirs(mock_master.return_value)
        repo = Mock(id='bar', working_dir=repo_working_dir)
        config = {}
        self.distributor.distributor_removed(repo, config)

        self.assertEquals(0, len(os.listdir(self.working_dir)))

    @patch('pulp_deb.plugins.distributors.web.WebPublisher')
    def test_publish_repo(self, mock_publisher):
        repo = Repository('test')
        config = PluginCallConfiguration(None, None)
        conduit = RepoPublishConduit(repo.id, 'foo_repo')
        self.distributor.publish_repo(repo, conduit, config)

        mock_publisher.return_value.assert_called_once()

    def test_cancel_publish_repo(self):
        self.distributor._publisher = MagicMock()
        self.distributor.cancel_publish_repo()
        self.assertTrue(self.distributor.canceled)

        self.distributor._publisher.cancel.assert_called_once()

    @patch('pulp_deb.plugins.distributors.web.configuration.validate_config')
    def test_validate_config(self, mock_validate):
        value = self.distributor.validate_config(Mock(), 'foo', Mock())
        mock_validate.assert_called_once_with('foo')
        self.assertEquals(value, mock_validate.return_value)
