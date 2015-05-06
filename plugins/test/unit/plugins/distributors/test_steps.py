import os
import shutil
import subprocess
import tempfile
import unittest

from mock import Mock, patch

from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Unit

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
    @patch('pulp_deb.plugins.distributors.steps.PublishMetadataStep')
    @patch('pulp_deb.plugins.distributors.steps.PublishContentStep')
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

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    @patch('pulp_deb.plugins.distributors.steps.misc.mkdir')
    def test_initialize(self, mock_makedirs):
        step = steps.PublishContentStep(working_dir='/foo/bar')
        step.initialize()
        mock_makedirs.assert_called_once_with('/foo/bar')

    def test_get_iterator(self):
        step = steps.PublishContentStep()
        step.conduit = Mock()
        return_value = step.get_iterator()
        self.assertEquals(return_value, step.conduit.get_units.return_value)

    # @patch('pulp_deb.plugins.distributors.steps.get_repo')
    def test_get_total(self):
        step = steps.PublishContentStep()
        step.repo = Mock(content_unit_counts={constants.DEB_TYPE_ID: 10})
        self.assertEquals(10, step._get_total())

    @patch('pulp_deb.plugins.distributors.steps.os.symlink')
    def test_process_item(self, mock_symlink):
        step = steps.PublishContentStep(working_dir='/foo/bar')
        test_unit = Unit(constants.DEB_TYPE_ID, {}, {'file_name': 'apples.deb'},
                         storage_path='/some/random/apples.deb')
        step.process_main(item=test_unit)
        mock_symlink.assert_called_once_with('/some/random/apples.deb', '/foo/bar/apples.deb')


class TestPublishMetadataStep(unittest.TestCase):

    @patch('pulp_deb.plugins.distributors.steps.subprocess.Popen')
    @patch('__builtin__.open')
    @patch('pulp_deb.plugins.distributors.steps.gzip')
    def test_process_main(self, mock_gzip, mock_open, mock_popen):
        mock_stdout = Mock()
        mock_popen.return_value.communicate.return_value = (mock_stdout, Mock())
        step = steps.PublishMetadataStep(working_dir='/foo')
        step.process_main()
        mock_open.assert_called_once_with('/foo/Packages', 'wb')
        mock_gzip.open.assert_called_once_with('/foo/Packages.gz', 'wb')
        mock_popen.assert_called_once_with(['dpkg-scanpackages', '-m', '.'],
                                           cwd='/foo', stdout=subprocess.PIPE)
        mock_gzip.open.return_value.write.assert_called_once_with(mock_stdout)
