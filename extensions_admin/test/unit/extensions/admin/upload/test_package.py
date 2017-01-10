import os
import shutil
import tempfile

import mock
from pulp.bindings.responses import Task
from ....testbase import PulpClientTests

from pulp_deb.extensions.admin.upload import package
from pulp_deb.common.ids import TYPE_ID_DEB


class CreatePackageCommandTests(PulpClientTests):
    def setUp(self):
        super(CreatePackageCommandTests, self).setUp()
        self.upload_manager = mock.MagicMock()
        self.command = package._CreatePackageCommand(
            self.context, self.upload_manager)
        self.work_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)
        super(CreatePackageCommandTests, self).tearDown()

    def test_matching_files_in_dir(self):
        self.command.suffix = '.something'
        open(os.path.join(self.work_dir, 'foo.something'), "w")
        open(os.path.join(self.work_dir, 'foo.somethingelse'), "w")
        unit_files = self.command.matching_files_in_dir(self.work_dir)
        self.assertEqual(['foo.something'],
                         [os.path.basename(x) for x in unit_files])

    def test_succeeded(self):
        self.command.prompt = mock.Mock()
        task = Task({})
        self.command.succeeded(task)
        self.assertTrue(self.command.prompt.render_success_message.called)

    def test_succeeded_error_in_result(self):
        self.command.prompt = mock.Mock()
        task = Task({'result': {'details': {'errors': ['foo']}}})
        self.command.succeeded(task)
        self.assertTrue(self.command.prompt.render_failure_message.called)


class CreateDebCommandTests(PulpClientTests):
    def setUp(self):
        super(CreateDebCommandTests, self).setUp()
        self.upload_manager = mock.MagicMock()
        self.command = package.CreateDebCommand(
            self.context, self.upload_manager)
        self.work_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)
        super(CreateDebCommandTests, self).tearDown()

    def test_structure(self):
        self.assertTrue(isinstance(self.command,
                                   package._CreatePackageCommand))
        self.assertEqual(self.command.name, package.NAME_DEB)
        self.assertEqual(self.command.description, package.DESC_DEB)
        self.assertEqual(self.command.suffix, package.SUFFIX_DEB)
        self.assertEqual(self.command.type_id, TYPE_ID_DEB)

    def test_generate_unit_key_and_metadata(self):
        unit_key, metadata = self.command.generate_unit_key_and_metadata(
            __file__)

        self.assertEqual({}, unit_key)
        self.assertEqual({}, metadata)
