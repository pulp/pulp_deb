import os
import shutil
import sys
import time
import uuid
import hashlib

import mock
from .... import testbase

from pulp.plugins.config import PluginCallConfiguration
from pulp_deb.common import ids, constants
from pulp_deb.plugins.db import models


class BaseTest(testbase.TestCase):
    def setUp(self):
        super(BaseTest, self).setUp()
        self._meta_path = sys.meta_path
        from pulp_deb.plugins.distributors import distributor
        self.Module = distributor
        self.Configuration = distributor.configuration
        root = os.path.join(self.work_dir, "root")
        self._confmock = mock.patch.dict(
            distributor.configuration.__dict__,
            ROOT_PUBLISH_DIR=root,
            MASTER_PUBLISH_DIR=os.path.join(root, "master"),
            HTTP_PUBLISH_DIR=os.path.join(root, "http", "repos"),
            HTTPS_PUBLISH_DIR=os.path.join(root, "https", "repos"),
        )
        self._confmock.start()

    def tearDown(self):
        self._confmock.stop()
        sys.meta_path = self._meta_path
        shutil.rmtree(self.work_dir)
        super(BaseTest, self).tearDown()

    def _config_conduit(self):
        ret = mock.MagicMock()
        ret.get_repo_distributors_by_relative_url.return_value = []
        return ret


class TestEntryPoint(BaseTest):
    """
    Tests for the entry_point() function.
    """
    def test_entry_point(self):
        """
        Assert the correct return value for the entry_point() function.
        """
        return_value = self.Module.entry_point()

        expected_value = (self.Module.DebDistributor, {})
        self.assertEqual(return_value, expected_value)


class TestConfiguration(BaseTest):
    def test_validate_config_empty(self):
        repo = mock.MagicMock(id="repo-1")
        conduit = self._config_conduit()
        config = PluginCallConfiguration({}, {})
        distributor = self.Module.DebDistributor()
        self.assertEquals(
            (False, '\n'.join([
                'Configuration key [http] is required, but was not provided',
                'Configuration key [https] is required, but was not provided',
                'Configuration key [relative_url] is required, but was not provided',  # noqa
                'Settings serve via http and https are both set to false. At least one option should be set to true.',  # noqa
            ])),
            distributor.validate_config(repo, config, conduit))

    def test_validate_config(self):
        signer = self.new_file(name="signer", contents="#!/bin/bash").path
        os.chmod(signer, 0o755)

        repo = mock.MagicMock(id="repo-1")
        conduit = self._config_conduit()
        config = PluginCallConfiguration(
            dict(gpg_cmd=signer),
            dict(http=True, https=False, relative_url=None))
        distributor = self.Module.DebDistributor()
        self.assertEquals(
            distributor.validate_config(repo, config, conduit),
            (True, None))

    def test_validate_config_bad_signer(self):
        # Signer is not an executable
        signer = self.new_file(name="signer", contents="#!/bin/bash").path

        repo = mock.MagicMock(id="repo-1")
        conduit = self._config_conduit()
        config = PluginCallConfiguration(
            dict(gpg_cmd=signer),
            dict(http=True, https=False, relative_url=None))
        distributor = self.Module.DebDistributor()
        self.assertEquals(
            (False, '\n'.join([
                "Command %s is not executable" % signer,
            ])),
            distributor.validate_config(repo, config, conduit))


class PublishRepoMixIn(object):
    @classmethod
    def _units(cls, storage_dir):
        units = []
        for Model in cls.Sample_Units:
            units.extend([Model(
                _storage_path=None,
                **x)
                for x in cls.Sample_Units[Model]])
        for unit in units:
            try:
                unit.filename = unit.filename_from_unit_key(unit.unit_key)
                _p = unit._storage_path = os.path.join(
                    storage_dir, unit.filename)
                file(_p, "wb").write(str(uuid.uuid4()))
                unit.checksumtype = 'sha256'
                unit.checksum = hashlib.sha256(
                    open(_p, "rb").read()).hexdigest()
            except:
                pass
        return units

    @mock.patch("pulp_deb.plugins.distributors.distributor.aptrepo.AptRepo.sign")
    @mock.patch('pulp.plugins.util.publish_step.selinux.restorecon')
    @mock.patch("pulp_deb.plugins.distributors.distributor.aptrepo.debpkg.debfile.DebFile")
    @mock.patch("pulp.server.managers.repo._common.task.current")
    @mock.patch('pulp.plugins.util.publish_step.repo_controller')
    def test_publish_repo(self, _repo_controller, _task_current, _DebFile,
                          _restorecon, _sign):
        _task_current.request.id = 'aabb'
        worker_name = "worker01"
        _task_current.request.configure_mock(hostname=worker_name)
        os.makedirs(os.path.join(self.pulp_working_dir, worker_name))
        # Set up some files
        storage_dir = os.path.join(self.work_dir, 'storage_dir')
        publish_dir = os.path.join(self.work_dir, 'publish_dir')
        os.makedirs(storage_dir)
        units = self._units(storage_dir)

        unit_dict = dict()
        unit_counts = dict()
        for type_id in sorted(ids.SUPPORTED_TYPES):
            _l = unit_dict[type_id] = [u for u in units
                                       if u.type_id == type_id]
            unit_counts[type_id] = len(_l)

        debcontrol = _DebFile.return_value.control.debcontrol.return_value

        debcontrol.copy.side_effect = [
            self._mkdeb(unit_dict[ids.TYPE_ID_DEB][i]) for i in self.Sample_Units_Order
        ]

        distributor = self.Module.DebDistributor()
        repo = mock.Mock()
        repo_id = "repo-%d-deb-level0" % int(time.time())
        repo.configure_mock(
            working_dir=os.path.join(self.work_dir, 'work_dir'),
            content_unit_counts=unit_counts,
            id=repo_id)

        def mock_get_units(repo_id, model_class, *args, **kwargs):
            units = unit_dict[model_class.TYPE_ID]
            query = mock.MagicMock()
            query.count.return_value = len(units)
            query.__iter__.return_value = iter(units)
            return [query]
        _repo_controller.get_unit_model_querysets.side_effect = mock_get_units
        conduit = self._config_conduit()
        repo_config = dict(
            http=True, https=False,
            relative_url='level1/' + repo.id,
            http_publish_dir=publish_dir + '/http/repos',
            https_publish_dir=publish_dir + '/https/repos')
        if self.default_release:
            repo_config[constants.PUBLISH_DEFAULT_RELEASE_KEYWORD] = True

        signer = self.new_file(name="signer", contents="#!/bin/bash").path
        os.chmod(signer, 0o755)

        repo_config.update(gpg_cmd=signer)

        # This call is to be tested
        distributor.publish_repo(repo, conduit, config=repo_config)

        # Assert, certain things have been called
        self.assertEquals(
            [x[0][0] for x in conduit.build_success_report.call_args_list],
            [{'publish_directory': 'FINISHED', 'publish_modules': 'FINISHED',
              'generate_listing_files': 'FINISHED'}])
        self.assertEquals(
            [x[0][1][0]['num_processed']
             for x in conduit.build_success_report.call_args_list],
            [1])
        self.assertEquals(
            [len(x[0][1][0]['sub_steps'])
             for x in conduit.build_success_report.call_args_list],
            [4])

        # Make sure all three models (packages, components, releases) are retrieved
        self.assertEqual(_repo_controller.get_unit_model_querysets.call_count, 3)

        # Make sure symlinks got created
        for unit in unit_dict[ids.TYPE_ID_DEB]:
            units_components = [comp.name for comp in unit_dict[ids.TYPE_ID_DEB_COMP]
                                if unit.id in comp.packages]
            for component in units_components:
                published_path = os.path.join(
                    repo_config['http_publish_dir'],
                    repo_config['relative_url'],
                    'pool',
                    component,
                    unit.filename)
                self.assertEquals(os.readlink(published_path), unit.storage_path)
            if self.default_release:
                published_path = os.path.join(
                    repo_config['http_publish_dir'],
                    repo_config['relative_url'],
                    'pool',
                    'all',
                    unit.filename)
                self.assertEquals(os.readlink(published_path), unit.storage_path)

        # Make sure the release files exist
        release_units = unit_dict[ids.TYPE_ID_DEB_RELEASE]
        component_units = unit_dict[ids.TYPE_ID_DEB_COMP]
        # Old-style repositories do not have release units and should be published as "stable/main"
        if not release_units:
            release_units.append(models.DebRelease(codename='stable', id='stableid'))
            component_units.append(models.DebComponent(name='main', id='mainid', release='stable'))
        # Test for default/all release
        if self.default_release:
            release_units.append(models.DebRelease(codename='default', id='defaultid'))
            component_units.append(models.DebComponent(name='all', id='allid', release='default'))
        for release in release_units:
            comp_dir = os.path.join(
                repo_config['http_publish_dir'],
                repo_config['relative_url'],
                'dists',
                release.codename)
            release_file = os.path.join(comp_dir, 'Release')
            self.assertTrue(os.path.exists(release_file))
            # Make sure the components Packages files exist
            for comp in [comp.name for comp in component_units
                         if comp.release == release.codename]:
                for arch in self.Architectures:
                    self.assertTrue(os.path.exists(
                        os.path.join(comp_dir, comp, 'binary-' + arch, 'Packages')))

        exp = [
            mock.call(repo.id, models.DebRelease, None),
            mock.call(repo.id, models.DebComponent, None),
            mock.call(repo.id, models.DebPackage, None),
        ]
        self.assertEquals(
            exp,
            _repo_controller.get_unit_model_querysets.call_args_list)

        publish_dir = os.path.join(repo_config['http_publish_dir'],
                                   repo_config['relative_url'])
        # Make sure there is a listing file
        lfpath = os.path.join(os.path.dirname(publish_dir), 'listing')
        self.assertEquals(repo_id, open(lfpath).read())
        # Parent directory too
        lfpath = os.path.join(os.path.dirname(os.path.dirname(lfpath)),
                              'listing')
        self.assertEquals('level1', open(lfpath).read())

        for release in unit_dict[ids.TYPE_ID_DEB_RELEASE]:
            work_release_file = os.path.join(self.pulp_working_dir, worker_name,
                                             "aabb", "dists", release.codename, "Release")
            _sign.assert_any_call(work_release_file)

    @classmethod
    def _mkdeb(cls, unit):
        return dict(Package=unit['name'],
                    Version=unit['version'],
                    Architecture=unit['architecture'])


class TestPublishOldRepoDeb(PublishRepoMixIn, BaseTest):
    Sample_Units = {
        models.DebPackage: [
            dict(name='burgundy', version='0.1938.0', architecture='amd64',
                 checksum='abcde', checksumtype='sha3.14', id='bbbb'),
            dict(name='chablis', version='0.2013.0', architecture='amd64',
                 checksum='yz', checksumtype='sha3.14', id='cccc'),
        ],
        models.DebComponent: [
        ],
        models.DebRelease: [
        ],
    }
    Sample_Units_Order = [0, 1]
    Architectures = ['all', 'amd64']
    default_release = False


class TestPublishRepoDeb(PublishRepoMixIn, BaseTest):
    Sample_Units = {
        models.DebPackage: [
            dict(name='burgundy', version='0.1938.0', architecture='amd64',
                 checksum='abcde', checksumtype='sha3.14', id='bbbb'),
            dict(name='chablis', version='0.2013.0', architecture='amd64',
                 checksum='yz', checksumtype='sha3.14', id='cccc'),
        ],
        models.DebComponent: [
            dict(name='main', release='stable', id='mainid', packages=['bbbb', 'cccc']),
        ],
        models.DebRelease: [
            dict(codename='stable', id='stableid'),
        ],
    }
    Sample_Units_Order = [0, 1]
    Architectures = ['all', 'amd64']
    default_release = False


class TestPublishRepoMultiArchDeb(PublishRepoMixIn, BaseTest):
    Sample_Units = {
        models.DebPackage: [
            dict(name='burgundy', version='0.1938.0', architecture='amd64',
                 checksum='abcde', checksumtype='sha3.14', id='bbbb'),
            dict(name='chablis', version='0.2013.0', architecture='amd64',
                 checksum='yz', checksumtype='sha3.14', id='cccc'),
            dict(name='dornfelder', version='0.2017.0', architecture='i386',
                 checksum='wxy', checksumtype='sha3.14', id='dddd'),
            dict(name='elbling', version='0.2017.0', architecture='all',
                 checksum='foo', checksumtype='sha3.14', id='eeee'),
        ],
        models.DebComponent: [
            dict(name='main', release='stable', id='mainid',
                 packages=['bbbb', 'cccc', 'dddd', 'eeee']),
        ],
        models.DebRelease: [
            dict(codename='stable', id='stableid'),
        ],
    }
    Sample_Units_Order = [2, 3, 0, 1, 3, 3]
    Architectures = ['all', 'amd64', 'i386']
    default_release = False


class TestPublishRepoMultiCompArchDeb(PublishRepoMixIn, BaseTest):
    Sample_Units = {
        models.DebPackage: [
            dict(name='burgundy', version='0.1938.0', architecture='amd64',
                 checksum='abcde', checksumtype='sha3.14', id='bbbb'),
            dict(name='chablis', version='0.2013.0', architecture='amd64',
                 checksum='yz', checksumtype='sha3.14', id='cccc'),
            dict(name='dornfelder', version='0.2017.0', architecture='i386',
                 checksum='wxy', checksumtype='sha3.14', id='dddd'),
            dict(name='elbling', version='0.2017.0', architecture='all',
                 checksum='foo', checksumtype='sha3.14', id='eeee'),
            dict(name='federweisser', version='0.2017.0', architecture='ppc',
                 checksum='foo', checksumtype='sha3.14', id='ffff'),
        ],
        models.DebComponent: [
            dict(name='main', release='old-stable', id='mainid',
                 packages=['bbbb', 'cccc', 'dddd', 'eeee']),
            dict(name='premature', release='old-stable', id='preid', packages=['ffff']),
        ],
        models.DebRelease: [
            dict(codename='old-stable', id='oldstableid'),
        ],
    }
    Sample_Units_Order = [2, 3, 0, 1, 3, 3, 4, 4, 3, 2, 3, 1, 0, 3, 3]
    Architectures = ['all', 'amd64', 'i386', 'ppc']
    default_release = True


class TestDistributorRemoved(BaseTest):
    def test_dirstibutor_removed(self):
        repo_id = 'repo-1'
        distributor = self.Module.DebDistributor()
        repo = mock.MagicMock(id=repo_id)
        config = {}

        # Create master directory
        repo_dir = os.path.join(
            self.Configuration.MASTER_PUBLISH_DIR,
            ids.TYPE_ID_DISTRIBUTOR,
            repo_id)
        # Create published directories
        http_dir = os.path.join(self.Configuration.HTTP_PUBLISH_DIR, repo_id)
        https_dir = os.path.join(self.Configuration.HTTPS_PUBLISH_DIR, repo_id)
        os.makedirs(repo_dir)
        for d in [http_dir, https_dir]:
            os.makedirs(os.path.dirname(d))
            os.symlink(repo_dir, d)

        distributor.distributor_removed(repo, config)

        self.assertFalse(os.path.exists(repo_dir))
        self.assertFalse(os.path.islink(http_dir))
        self.assertFalse(os.path.islink(https_dir))
