import hashlib
import json
import os
import tempfile
import shutil
import uuid
import unittest
from collections import namedtuple

from pulp.server import config
config.check_config_files = lambda *args: None

File = namedtuple("File", "path checksum")


class TestCase(unittest.TestCase):
    def setUp(self):
        super(TestCase, self).setUp()
        self.work_dir = tempfile.mkdtemp()

        self.pulp_dir = os.path.join(self.work_dir, 'pulp_dir')
        config.config.set('server', 'storage_dir', self.pulp_dir)
        self.pulp_working_dir = os.path.join(self.work_dir, 'pulp_working_dir')
        config.config.set('server', 'working_directory', self.pulp_working_dir)

    def tearDown(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)
        del self.work_dir
        super(TestCase, self).tearDown()

    def new_file(self, name=None, contents=None):
        if name is None:
            name = str(uuid.uuid4())
        file_path = os.path.join(self.work_dir, name)
        if contents is None:
            contents = str(uuid.uuid4())
        elif isinstance(contents, (dict, list)):
            contents = json.dumps(contents)
        checksum = hashlib.sha256(contents).hexdigest()
        with open(file_path, "w") as fobj:
            fobj.write(contents)
        return File(file_path, checksum)
