from unittest import TestCase

from mock import patch, Mock, MagicMock
from pulp.plugins.model import Repository

from pulp_deb.common import constants
from pulp_deb.plugins.importers.web import WebImporter, entry_point


class TestImporter(TestCase):

    @patch('pulp_deb.plugins.importers.web.read_json_config')
    def test_entry_point(self, read_json_config):
        plugin, cfg = entry_point()
        read_json_config.assert_called_with(constants.IMPORTER_CONFIG_FILE_PATH)
        self.assertEqual(plugin, WebImporter)
        self.assertEqual(cfg, read_json_config.return_value)

    def test_metadata(self):
        md = WebImporter.metadata()
        self.assertEqual(md['id'], constants.WEB_IMPORTER_TYPE_ID)
        self.assertEqual(md['types'], [constants.DEB_TYPE_ID])
        self.assertTrue(len(md['display_name']) > 0)

    def test_validate_config(self):
        importer = WebImporter()
        result = importer.validate_config(Mock(), Mock())
        self.assertEqual(result, (True, ''))

    @patch('sys.exit')
    def test_cancel(self, _exit):
        importer = WebImporter()
        importer.cancel_sync_repo()
        _exit.assert_called_once_with(0)


@patch('pulp_deb.plugins.importers.sync.SyncStep')
@patch('tempfile.mkdtemp', spec_set=True)
@patch('shutil.rmtree')
class TestSyncRepo(TestCase):
    def setUp(self):
        super(TestSyncRepo, self).setUp()
        self.repo = Repository('repo1', working_dir='/a/b/c')
        self.sync_conduit = MagicMock()
        self.config = MagicMock()
        self.importer = WebImporter()

    def test_calls_sync_step(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_sync_step.assert_called_once_with(repo=self.repo, conduit=self.sync_conduit,
                                               config=self.config,
                                               working_dir=mock_mkdtemp.return_value)

    def test_calls_process_lifecycle(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_sync_step.return_value.process_lifecycle.assert_called_once_with()

    def test_makes_temp_dir(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_mkdtemp.assert_called_once_with(dir=self.repo.working_dir)

    def test_removes_temp_dir(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_rmtree.assert_called_once_with(mock_mkdtemp.return_value, ignore_errors=True)

    def test_removes_temp_dir_after_exception(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        class MyError(Exception):
            pass
        mock_sync_step.return_value.process_lifecycle.side_effect = MyError
        self.assertRaises(MyError, self.importer.sync_repo, self.repo,
                          self.sync_conduit, self.config)

        mock_rmtree.assert_called_once_with(mock_mkdtemp.return_value, ignore_errors=True)
