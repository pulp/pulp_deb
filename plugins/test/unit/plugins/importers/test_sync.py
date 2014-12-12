import shutil
import tempfile
import unittest

import mock
from pulp.common.plugins import importer_constants
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository as RepositoryModel
from pulp.server.managers import factory

from pulp_deb.common import constants
from pulp_deb.plugins.importers import sync


factory.initialize()


class TestSyncStep(unittest.TestCase):
    def setUp(self):
        super(TestSyncStep, self).setUp()

        self.repo = RepositoryModel('repo1')
        self.conduit = mock.MagicMock()
        plugin_config = {
            importer_constants.KEY_FEED: 'http://pulpproject.org/',
        }
        self.working_dir = tempfile.mkdtemp()
        self.config = PluginCallConfiguration({}, plugin_config)
        self.step = sync.SyncStep(repo=self.repo,
                                  conduit=self.conduit,
                                  config=self.config,
                                  working_dir=self.working_dir)

    def tearDown(self):
        shutil.rmtree(self.working_dir)

    def test_init(self):
        self.assertEqual(self.step.step_id, constants.IMPORT_STEP_MAIN)

        # make sure the children are present
        step_ids = set([child.step_id for child in self.step.children])
        self.assertTrue(constants.IMPORT_STEP_METADATA in step_ids)


class TestGenerateMetadataStep(unittest.TestCase):
    def setUp(self):
        super(TestGenerateMetadataStep, self).setUp()
        self.working_dir = tempfile.mkdtemp()
        self.repo = RepositoryModel('repo1')
        self.repo.working_dir = self.working_dir
        self.conduit = mock.MagicMock()
        plugin_config = {
            importer_constants.KEY_FEED: 'http://ftp.fau.de/debian/dists/stable/main/binary-amd64/',
        }
        self.config = PluginCallConfiguration({}, plugin_config)

        self.step = sync.GetMetadataStep(repo=self.repo, conduit=self.conduit, config=self.config,
                                         working_dir=self.working_dir)
        self.step.parent = mock.MagicMock()
        self.index = self.step.parent.index_repository

    def tearDown(self):
        super(TestGenerateMetadataStep, self).tearDown()
        shutil.rmtree(self.working_dir)

    def test_process_main(self):
        self.step.process_main()
