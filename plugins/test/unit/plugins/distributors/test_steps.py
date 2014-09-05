import os
import shutil
import tempfile
import unittest

from mock import Mock, patch

from pulp.plugins.model import Repository
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.conduits.repo_publish import RepoPublishConduit

from pulp_deb.common import constants
from pulp_deb.plugins.distributors import steps


class TestWebPublisher(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.publish_dir = os.path.join(self.working_directory, 'publish')
        self.repo_working = os.path.join(self.working_directory, 'work')

        self.repo = Mock(id='foo', working_dir=self.repo_working)
        self.config = PluginCallConfiguration({constants.DISTRIBUTOR_CONFIG_KEY_PUBLISH_DIRECTORY:
                                              self.publish_dir}, {})

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    @patch('pulp_deb.plugins.distributors.steps.AtomicDirectoryPublishStep')
    @patch('pulp_deb.plugins.distributors.steps.PublishContentStep')
    @patch('pulp_deb.plugins.distributors.steps.PublishMetadataStep')
    def test_init_populated(self, mock_metadata, mock_content, mock_atomic):
        mock_conduit = Mock()
        mock_config = {
            constants.DISTRIBUTOR_CONFIG_KEY_PUBLISH_DIRECTORY: self.publish_dir
        }
        self.repo.content_unit_counts = {'deb': 1}
        publisher = steps.WebPublisher(self.repo, mock_conduit, mock_config)
        self.assertEquals(publisher.children, [mock_metadata.return_value,
                                               mock_content.return_value,
                                               mock_atomic.return_value])


class TestPublishContentStep(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.working_directory, 'src')
        self.target_dir = os.path.join(self.working_directory, 'target')

        os.makedirs(self.source_dir)
        os.makedirs(self.target_dir)
        self.repo = Repository(id='foo', working_dir=self.target_dir)
        config = PluginCallConfiguration(None, None)
        conduit = RepoPublishConduit(self.repo.id, 'foo_repo')
        conduit.get_repo_scratchpad = Mock(return_value={})
        self.parent = steps.PluginStep('test-step', self.repo, conduit, config)

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def test_process_main(self):
        step = steps.PublishContentStep()
        self.parent.add_child(step)
        step.process_main()


class TestPublishMetadataStep(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.working_directory, 'src')
        self.target_dir = os.path.join(self.working_directory, 'target')

        os.makedirs(self.source_dir)
        os.makedirs(self.target_dir)
        self.repo = Repository(id='foo', working_dir=self.target_dir)
        config = PluginCallConfiguration(None, None)
        conduit = RepoPublishConduit(self.repo.id, 'foo_repo')
        conduit.get_repo_scratchpad = Mock(return_value={})
        self.parent = steps.PluginStep('test-step', self.repo, conduit, config)

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def test_process_main(self):
        step = steps.PublishMetadataStep()
        self.parent.add_child(step)
        step.process_main()
