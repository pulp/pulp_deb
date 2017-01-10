import os
import shutil
import tempfile

import mock
from pulp.common.plugins import importer_constants
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository as RepositoryModel, Unit
from pulp.server import exceptions
from pulp.server.managers import factory

from .... import testbase

from pulp_deb.common import constants
from pulp_deb.plugins import error_codes
from pulp_deb.plugins.importers import sync


class TestSync(testbase.TestCase):
    def setUp(self):
        super(TestSync, self).setUp()

        self.repo = RepositoryModel('repo1')
        self.conduit = mock.MagicMock()
        plugin_config = {
            importer_constants.KEY_FEED: 'http://pulpproject.org/',
        }
        self.config = PluginCallConfiguration({}, plugin_config)
        self._task_current = mock.patch("pulp.server.managers.repo._common.task.current")
        obj = self._task_current.__enter__()
        obj.request.id = 'aabb'
        worker_name = "worker01"
        obj.request.configure_mock(hostname=worker_name)
        os.makedirs(os.path.join(self.pulp_working_dir, worker_name))
        self.step = sync.RepoSync(repo=self.repo,
                                  conduit=self.conduit,
                                  config=self.config)

    def tearDown(self):
        self._task_current.__exit__()

    def test_init(self):
        self.assertEqual(self.step.step_id, constants.SYNC_STEP)

        # make sure the children are present
        step_ids = set([child.step_id for child in self.step.children])
        self.assertTrue(constants.SYNC_STEP_METADATA in step_ids)

    @mock.patch('pulp_deb.plugins.importers.sync.misc.mkdir')
    def test_generate_download_requests_root_contextpath(self, mock_mkdir):
        """
        Test with a repository at the root context path.
        """
        sample_unit = {
            'name': 'foo',
            'version': '1.5',
            'architecture': 'x86_64',
            'filename': 'foo.deb'}
        self.step.step_get_local_units.units_to_download = [sample_unit]
        self.step.deb_data = {
            sync.get_key_hash(sample_unit): {
                'file_path': '/pool/p/foo.deb',
                'file_name': 'foo.deb'
            }
        }

        requests = list(self.step.generate_download_requests())

        self.assertEquals(1, len(requests))
        download_request = requests[0]
        download_dir = os.path.join(self.pulp_working_dir,
                                    sync.generate_internal_storage_path('foo.deb'))
        download_url = 'http://pulpproject.org/pool/p/foo.deb'
        mock_mkdir.assert_called_once_with(os.path.dirname(download_dir))
        self.assertEquals(download_request.destination, download_dir)
        self.assertEquals(download_request.url, download_url)

    @mock.patch('pulp_deb.plugins.importers.sync.misc.mkdir')
    def test_generate_download_requests_subdirectory_contextpath(self, mock_mkdir):
        """
        Test with a repository at a subdirectory of the context root.
        """
        plugin_config = {
            importer_constants.KEY_FEED: 'http://pulpproject.org/foo/baz/',
        }
        self.step.config = PluginCallConfiguration({}, plugin_config)
        sample_unit = {
            'name': 'foo',
            'version': '1.5',
            'architecture': 'x86_64',
            'filename': 'foo.deb'}
        self.step.step_get_local_units.units_to_download = [sample_unit]
        self.step.deb_data = {
            sync.get_key_hash(sample_unit): {
                'file_path': 'pool/p/foo.deb',
                'file_name': 'foo.deb'
            }
        }
        requests = list(self.step.generate_download_requests())
        self.assertEquals(1, len(requests))
        download_request = requests[0]
        download_dir = os.path.join(self.pulp_working_dir,
                                    sync.generate_internal_storage_path('foo.deb'))
        download_url = 'http://pulpproject.org/foo/baz/pool/p/foo.deb'
        mock_mkdir.assert_called_once_with(os.path.dirname(download_dir))
        self.assertEquals(download_request.destination, download_dir)
        self.assertEquals(download_request.url, download_url)


class TestGenerateMetadataStep(testbase.TestCase):
    def setUp(self):
        super(TestGenerateMetadataStep, self).setUp()
        self.repo = RepositoryModel('repo1')
        self.repo.working_dir = os.path.join(self.pulp_working_dir, "repo1")
        self.conduit = mock.MagicMock()
        plugin_config = {
            importer_constants.KEY_FEED: 'http://ftp.fau.de/debian/dists/stable/main/binary-amd64/',
        }
        self.config = PluginCallConfiguration({}, plugin_config)

        self.step = sync.GetMetadataStep(repo=self.repo, conduit=self.conduit, config=self.config,
                                         working_dir=self.repo.working_dir)
        self.step.parent = mock.MagicMock()
        self.index = self.step.parent.index_repository

    @mock.patch('pulp_deb.plugins.importers.sync.debian_support.PackageFile')
    @mock.patch('pulp_deb.plugins.importers.sync.debian_support.download_file')
    def test_process_main(self, mock_deb_download, mock_deb_packagefile):
        mock_deb_packagefile.return_value = [
            {
                'Package': 'foo',
                'Version': '1.5',
                'Architecture': 'x86_64',
                'Size': '105',
                'Filename': 'foo.deb'
            }
        ]
        self.step.parent.available_units = []
        self.step.process_main()
        download_feed = self.config.get(importer_constants.KEY_FEED) + 'Packages'
        download_location = os.path.join(self.repo.working_dir, 'Packages')
        mock_deb_download.assert_called_once_with(download_feed, download_location)
        self.assertEquals(len(self.step.parent.available_units), 1)
        self.assertDictEqual(self.step.parent.available_units[0],
                             {'name': 'foo',
                              'version': '1.5',
                              'architecture': 'x86_64'})

    @mock.patch('pulp_deb.plugins.importers.sync.debian_support.PackageFile')
    @mock.patch('pulp_deb.plugins.importers.sync.debian_support.download_file')
    def test_process_main_sub_packagefile(self, mock_deb_download, mock_deb_packagefile):
        """
        Test when the Packages file is not in the feed directory.
        """
        mock_deb_packagefile.return_value = [
            {
                'Package': 'foo',
                'Version': '1.5',
                'Architecture': 'x86_64',
                'Size': '105',
                'Filename': 'foo.deb'
            }
        ]
        plugin_config = {
            importer_constants.KEY_FEED: 'http://ftp.fau.de/debian/',
            'package-file-path': 'dists/stable/main/binary-amd64/'
        }
        self.config = PluginCallConfiguration({}, plugin_config)
        self.step.config = plugin_config
        self.step.parent.available_units = []
        self.step.process_main()
        download_feed = 'http://ftp.fau.de/debian/dists/stable/main/binary-amd64/Packages'
        download_location = os.path.join(self.repo.working_dir, 'Packages')
        mock_deb_download.assert_called_once_with(download_feed, download_location)
        self.assertEquals(len(self.step.parent.available_units), 1)
        self.assertDictEqual(self.step.parent.available_units[0],
                             {'name': 'foo',
                              'version': '1.5',
                              'architecture': 'x86_64'})

    @mock.patch('pulp_deb.plugins.importers.sync.debian_support.PackageFile')
    @mock.patch('pulp_deb.plugins.importers.sync.debian_support.download_file')
    def test_process_main_missing_slashes(self, mock_deb_download, mock_deb_packagefile):
        """
        Test when the the feed is missing a '/' at the end and the package_file_path is
        not relative.
        """
        mock_deb_packagefile.return_value = [
            {
                'Package': 'foo',
                'Version': '1.5',
                'Architecture': 'x86_64',
                'Size': '105',
                'Filename': 'foo.deb'
            }
        ]
        plugin_config = {
            importer_constants.KEY_FEED: 'http://ftp.fau.de/debian',
            'package-file-path': '/dists/stable/main/binary-amd64/'
        }
        self.config = PluginCallConfiguration({}, plugin_config)
        self.step.config = plugin_config
        self.step.parent.available_units = []
        self.step.process_main()
        download_feed = 'http://ftp.fau.de/debian/dists/stable/main/binary-amd64/Packages'
        download_location = os.path.join(self.repo.working_dir, 'Packages')
        mock_deb_download.assert_called_once_with(download_feed, download_location)
        self.assertEquals(len(self.step.parent.available_units), 1)
        self.assertDictEqual(self.step.parent.available_units[0],
                             {'name': 'foo',
                              'version': '1.5',
                              'architecture': 'x86_64'})


class TestGetLocalUnitsStepDeb(testbase.TestCase):
    def setUp(self):
        super(TestGetLocalUnitsStepDeb, self).setUp()
        self.step = sync.GetLocalUnitsStepDeb()
        self.step.conduit = mock.MagicMock()

    def test_dict_to_unit(self):
        """
        Test basic conversion of a unit dictionary to an unit object
        """
        unit_dict = {'name': 'foo', 'version': '1.5', 'architecture': 'x86_64',
                     '_id': 'blah'}
        unit_key_hash = sync.get_key_hash(unit_dict)
        deb_data = {
            unit_key_hash: {
                'file_name': 'foo.deb'
            }
        }
        self.step.parent = mock.MagicMock(deb_data=deb_data)

        unit = self.step._dict_to_unit(unit_dict)

        self.assertTrue(unit is self.step.conduit.init_unit.return_value)
        unit_key = {'name': 'foo', 'version': '1.5',
                    'architecture': 'x86_64'}
        storage_path = sync.generate_internal_storage_path('foo.deb')
        self.step.conduit.init_unit.assert_called_once_with(constants.DEB_TYPE_ID,
                                                            unit_key, {'file_name': 'foo.deb'},
                                                            storage_path)


class TestSaveUnits(testbase.TestCase):
    def setUp(self):
        super(TestSaveUnits, self).setUp()
        self.step = sync.SaveUnits(self.pulp_working_dir)
        self.step.conduit = mock.MagicMock()
        self.step.parent = mock.MagicMock()

    @mock.patch('pulp_deb.plugins.importers.sync.os.stat')
    @mock.patch('pulp_deb.plugins.importers.sync.shutil.move')
    def test_process_main(self, mock_shutil, mock_stat):
        """
        Test that we save properly if everything is ok
        """
        unit_key = {'name': 'foo', 'version': '1.5',
                    'architecture': 'x86_64'}
        unit_key_hash = sync.get_key_hash(unit_key)
        deb_data = {
            unit_key_hash: {
                'file_name': 'foo.deb',
                'file_size': '5'
            }
        }
        self.step.parent = mock.MagicMock(deb_data=deb_data)

        self.step.parent.step_get_local_units.units_to_download = [unit_key]
        mock_stat.return_value.st_size = 5
        initialized_unit = Unit(constants.DEB_TYPE_ID, unit_key, {}, 'some/directory')
        save_location = sync.generate_internal_storage_path('foo.deb')

        self.step.conduit.init_unit.return_value = initialized_unit
        self.step.process_main()
        self.step.conduit.init_unit.assert_called_once_with(constants.DEB_TYPE_ID,
                                                            unit_key, {'file_name': 'foo.deb'},
                                                            save_location)
        source = os.path.join(self.pulp_working_dir, save_location)
        mock_shutil.assert_called_once_with(source, initialized_unit.storage_path)

    @mock.patch('pulp_deb.plugins.importers.sync.os.stat')
    @mock.patch('pulp_deb.plugins.importers.sync.shutil.move')
    def test_process_main_file_size_failure(self, mock_shutil, mock_stat):
        """
        Test that we error if the file size does not match the metadata
        """
        unit_key = {'name': 'foo', 'version': '1.5',
                    'architecture': 'x86_64'}
        unit_key_hash = sync.get_key_hash(unit_key)
        deb_data = {
            unit_key_hash: {
                'file_name': 'foo.deb',
                'file_size': '5'
            }
        }
        self.step.parent = mock.MagicMock(deb_data=deb_data)

        self.step.parent.step_get_local_units.units_to_download = [unit_key]
        mock_stat.return_value.st_size = 7
        initialized_unit = Unit(constants.DEB_TYPE_ID, unit_key, {}, 'some/directory')
        self.step.conduit.init_unit.return_value = initialized_unit
        try:
            self.step.process_main()
            self.fail('This should have raised an exception')
        except exceptions.PulpCodedValidationException as e:
            self.assertEquals(e.error_code, error_codes.DEB1001)
