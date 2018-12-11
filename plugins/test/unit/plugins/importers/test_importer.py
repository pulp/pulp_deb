"""
Contains tests for pulp_deb.plugins.importers.importer.
"""
from gettext import gettext as _
import json
import os

import mock

from pulp_deb.common import ids
from .... import testbase
from pulp_deb.plugins.db import models
from pulp_deb.plugins.importers import importer


class TestEntryPoint(testbase.TestCase):
    """
    Tests for the entry_point() function.
    """
    def test_return_value(self):
        """
        Assert the correct return value for the entry_point() function.
        """
        return_value = importer.entry_point()

        expected_value = (importer.DebImporter, {})
        self.assertEqual(return_value, expected_value)
        self.assertEquals({
            models.DebPackage.TYPE_ID: models.DebPackage,
        }, importer.DebImporter.Type_Class_Map)
        self.assertEquals(
            ids.TYPE_ID_DEB, models.DebPackage.TYPE_ID)


class ModelMixIn(object):
    def test__compute_checksum(self):
        file_path, checksum = self.new_file()
        self.assertEquals(
            checksum,
            self.__class__.Model._compute_checksum(open(file_path)))

    def test_filename_from_unit_key(self):
        unit_key = dict(name="aaa", version="1", architecture="x86_64",
                        checksumtype="sha256", checksum="decafbad",
                        extra="bbb")
        self.assertEquals(
            "aaa_1_x86_64.%s" % self.__class__.Model.TYPE_ID,
            self.__class__.Model.filename_from_unit_key(unit_key))

    def test_unit_keys(self):
        type_file = os.path.join(os.path.dirname(__file__),
                                 '..', '..', '..', '..',
                                 'types', 'deb.json')
        contents = json.load(open(type_file))
        types = dict((x['id'], x) for x in contents['types'])
        tlist = types[self.__class__.Model.TYPE_ID]['unit_key']
        self.assertEquals(
            sorted(self.__class__.Model.unit_key_fields),
            sorted(tlist))

    def test_ids(self):
        self.assertEquals(self.UNIT_KEY_FIELDS,
                          self.__class__.Model.unit_key_fields)


class TestModel_DebPackage(ModelMixIn, testbase.TestCase):
    Model = models.DebPackage
    Sample_Unit = dict()
    UNIT_KEY_FIELDS = ids.UNIT_KEY_DEB


class TestDebImporter(testbase.TestCase):
    """
    This class contains tests for the DebImporter class.
    """
    @mock.patch("pulp_deb.plugins.importers.importer.platform_models")
    @mock.patch("pulp_deb.plugins.db.models.repo_controller")
    def test_import_units_units_none(self, _repo_controller, _platform_models):
        """
        Assert correct behavior when units == None.
        """
        src_repo = mock.MagicMock()
        dst_repo = mock.MagicMock()
        _platform_models.Repository.objects.get.side_effect = [src_repo,
                                                               dst_repo]
        Deb = models.DebPackage
        units = [
            Deb(name="unit_a", version="1"),
            Deb(name="unit_b", version="1"),
            Deb(name="unit_3", version="1"),
        ]

        _repo_controller.find_repo_content_units.return_value = units

        pulpimp = importer.DebImporter()
        import_conduit = mock.MagicMock()

        imported_units = pulpimp.import_units(mock.MagicMock(),
                                              mock.MagicMock(),
                                              import_conduit,
                                              mock.MagicMock(),
                                              units=None)

        # Assert that the correct criteria was used
        _repo_controller.find_repo_content_units.assert_called_once_with(
            src_repo, yield_content_unit=True)
        # Assert that the units were associated correctly
        _u = sorted(units)
        self.assertEquals(
            [
                mock.call(repository=dst_repo, unit=_u[0]),
                mock.call(repository=dst_repo, unit=_u[1]),
                mock.call(repository=dst_repo, unit=_u[2]),
            ],
            _repo_controller.associate_single_unit.call_args_list)
        self.assertEqual(imported_units, sorted(units))

    @mock.patch("pulp_deb.plugins.importers.importer.platform_models")
    @mock.patch("pulp_deb.plugins.db.models.repo_controller")
    def test_import_units_units_not_none(self, _repo_controller,
                                         _platform_models):
        """
        Assert correct behavior when units != None.
        """
        src_repo = mock.MagicMock()
        dst_repo = mock.MagicMock()
        _platform_models.Repository.objects.get.side_effect = [src_repo,
                                                               dst_repo]
        pulpimp = importer.DebImporter()
        import_conduit = mock.MagicMock()
        Deb = models.DebPackage
        units = [
            Deb(name="unit_a", version="1"),
            Deb(name="unit_b", version="1"),
            Deb(name="unit_3", version="1"),
        ]

        imported_units = pulpimp.import_units(mock.MagicMock(),
                                              mock.MagicMock(),
                                              import_conduit,
                                              mock.MagicMock(),
                                              units=units)

        # Assert that no criteria was used
        self.assertEqual(
            0, _repo_controller.find_repo_content_units.call_count)
        # Assert that the units were associated correctly
        _u = sorted(units)
        self.assertEquals(
            [
                mock.call(repository=dst_repo, unit=_u[0]),
                mock.call(repository=dst_repo, unit=_u[1]),
                mock.call(repository=dst_repo, unit=_u[2]),
            ],
            _repo_controller.associate_single_unit.call_args_list)
        # Assert that the units were returned
        self.assertEqual(imported_units, sorted(units))

    def test_metadata(self):
        """
        Test the metadata class method's return value.
        """
        metadata = importer.DebImporter.metadata()

        expected_value = {
            'id': ids.TYPE_ID_IMPORTER,
            'display_name': _('Debian importer'),
            'types': [ids.TYPE_ID_DEB, ids.TYPE_ID_DEB_COMP, ids.TYPE_ID_DEB_RELEASE], }
        self.assertEqual(metadata, expected_value)

    @mock.patch("pulp_deb.plugins.db.models.repo_controller")
    @mock.patch('pulp_deb.plugins.db.models.DebPackage._get_db')
    @mock.patch('pulp_deb.plugins.db.models.DebPackage.from_file')
    @mock.patch("pulp_deb.plugins.importers.importer.plugin_api")
    def test_upload_unit_deb(self, _plugin_api, from_file,
                             _get_db, _repo_controller):
        """
        Assert correct operation of upload_unit().
        """
        _plugin_api.get_unit_model_by_id.return_value = models.DebPackage
        file_path, checksum = self.new_file("foo.deb")
        deb_file, checksum = self.new_file('foo.deb')

        unit_key = dict()
        metadata = dict(
            name="foo", version="1.1",
            filename=os.path.basename(file_path),
            architecture="x86_64",
            checksumtype="sha256",
            depends=[{'name': 'glibc'}],
            checksum=checksum)
        package = models.DebPackage(**metadata)
        from_file.return_value = package

        pulpimp = importer.DebImporter()
        repo = mock.MagicMock()
        type_id = ids.TYPE_ID_DEB
        conduit = mock.MagicMock()
        config = {}
        models.DebPackage.attach_signals()

        report = pulpimp.upload_unit(repo, type_id, unit_key, metadata,
                                     deb_file, conduit, config)

        from_file.assert_called_once_with(file_path, metadata)

        obj_id = _get_db.return_value.__getitem__.return_value.save.return_value.decode.return_value  # noqa

        metadata.update(
            id=obj_id,
            downloaded=True,
            pulp_user_metadata=dict(),
            relativepath=None,
            installed_size=None,
            priority=None,
            section=None,
            source=None,
            depends=None,
            maintainer=None,
            multi_arch=None,
            original_maintainer=None,
            homepage=None,
            description=None,
            size=None,
            control_fields=None,
        )
        for fname in models.DebPackage.REL_FIELDS:
            metadata[fname] = None
        metadata['depends'] = [{'name': 'glibc'}]
        unit_key = dict((x, metadata[x])
                        for x in models.DebPackage.unit_key_fields)

        self.assertEqual(report,
                         {'success_flag': True,
                          'details': dict(
                              unit=dict(unit_key=unit_key, metadata=metadata)
                          ),
                          'summary': ''})

    def test_validate_config(self):
        """
        There is no config, so we'll just assert that validation passes.
        """
        pulpimp = importer.DebImporter()
        return_value = pulpimp.validate_config(mock.MagicMock(), {})

        self.assertEqual(return_value, (True, None))

    @mock.patch("pulp_deb.plugins.importers.importer.sync.RepoSync")
    def test_sync(self, _RepoSync):
        # Basic test to make sure we're passing information correctly into
        # RepoSync, which itself is tested in test_sync
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        cfg = mock.MagicMock()

        pulpimp = importer.DebImporter()
        pulpimp.sync_repo(repo, conduit, cfg)

        self.assertEquals(pulpimp._current_sync,
                          _RepoSync.return_value)
        _RepoSync.assert_called_once_with(
            repo, conduit, cfg)
        self.assertEquals(repo.repo_obj, conduit.repo)
