import shutil
import tempfile
import mock
from unittest import TestCase

from mock import patch, Mock, MagicMock

from pulp.plugins.conduits.unit_import import ImportUnitConduit
from pulp.plugins.model import Repository, Unit

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


class TestISOImporter(TestCase):
    """
    Test the DEBImporter object.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.deb_importer = WebImporter()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_import_units__units_empty_list(self):
        """
        Make sure that when an empty list is passed, we import zero units.
        """
        import_conduit = MagicMock()
        # source_repo, dest_repo, and config aren't used by import_units, so we'll just set them to
        # None for simplicity. Let's pass an empty list as the units we want to import
        units_to_import = []
        imported_units = self.deb_importer.import_units(None, None, import_conduit, None,
                                                        units=units_to_import)

        # There should have been zero calls to the import_conduit. None to get_source_units(), and
        # none to associate units.
        self.assertEqual(len(import_conduit.get_source_units.call_args_list), 0)
        self.assertEqual(len(import_conduit.associate_unit.call_args_list), 0)

        # Make sure that the returned units are correct
        self.assertEqual(imported_units, units_to_import)

    def test_import_units__units_none(self):
        """
        Make sure that when units=None, we import all units from the import_conduit.
        """
        source_units = [Unit(constants.DEB_TYPE_ID, {'name': 'test.deb'}, {}, '/path/test.deb'),
                        Unit(constants.DEB_TYPE_ID, {'name': 'test2.deb'}, {}, '/path/test2.deb'),
                        Unit(constants.DEB_TYPE_ID, {'name': 'test3.deb'}, {}, '/path/test3.deb')]
        import_conduit = mock.Mock(spec=ImportUnitConduit)
        import_conduit.get_source_units.return_value = source_units

        # source_repo, dest_repo, and config aren't used by import_units, so we'll just set them to
        # None for simplicity.
        imported_units = self.deb_importer.import_units(None, None, import_conduit, None,
                                                        units=None)

        # There should have been four calls to the import_conduit. One to get_source_units(), and
        # three to associate units.
        # get_source_units should have a UnitAssociationCriteria that specified ISOs, so we'll
        # assert that behavior.
        self.assertEqual(len(import_conduit.get_source_units.call_args_list), 1)
        get_source_units_args = tuple(import_conduit.get_source_units.call_args_list[0])[1]
        self.assertEqual(get_source_units_args['criteria']['type_ids'], [constants.DEB_TYPE_ID])

        # There are three Units, so there should be three calls to associate_unit since we didn't
        # pass which units we wanted to import. Let's make sure the three calls were made with the
        # correct Units.
        self.assertEqual(len(import_conduit.associate_unit.call_args_list), 3)
        expected_unit_names = ['test.deb', 'test2.deb', 'test3.deb']
        actual_unit_names = [tuple(call)[0][0].unit_key['name']
                             for call in import_conduit.associate_unit.call_args_list]
        self.assertEqual(actual_unit_names, expected_unit_names)

        # The three Units should have been returned
        self.assertEqual(imported_units, source_units)

    def test_import_units__units_some(self):
        """
        Make sure that when units are passed, we import only those units.
        """
        source_units = [Unit(constants.DEB_TYPE_ID, {'name': 'test.deb'}, {}, '/path/test.deb'),
                        Unit(constants.DEB_TYPE_ID, {'name': 'test2.deb'}, {}, '/path/test2.deb'),
                        Unit(constants.DEB_TYPE_ID, {'name': 'test3.deb'}, {}, '/path/test3.deb')]
        import_conduit = MagicMock()
        # source_repo, dest_repo, and config aren't used by import_units, so we'll just set them to
        # None for simplicity. Let's use test.iso and test3.iso, leaving out test2.iso.
        units_to_import = [source_units[i] for i in range(0, 3, 2)]
        imported_units = self.deb_importer.import_units(None, None, import_conduit, None,
                                                        units=units_to_import)

        # There should have been two calls to the import_conduit. None to get_source_units(), and
        # two to associate units.
        self.assertEqual(len(import_conduit.get_source_units.call_args_list), 0)

        # There are two Units, so there should be two calls to associate_unit since we passed which
        # units we wanted to import. Let's make sure the two calls were made with the
        # correct Units.
        self.assertEqual(len(import_conduit.associate_unit.call_args_list), 2)
        expected_unit_names = ['test.deb', 'test3.deb']
        actual_unit_names = [tuple(call)[0][0].unit_key['name']
                             for call in import_conduit.associate_unit.call_args_list]
        self.assertEqual(actual_unit_names, expected_unit_names)

        # Make sure that the returned units are correct
        self.assertEqual(imported_units, units_to_import)
