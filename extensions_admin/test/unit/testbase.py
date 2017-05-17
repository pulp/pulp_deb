from ConfigParser import SafeConfigParser
import logging
import os
import unittest

import mock
import okaara
from pulp.bindings.bindings import Bindings
from pulp.bindings.server import PulpConnection
from pulp.client.extensions.core import PulpPrompt, ClientContext, PulpCli
from pulp.client.extensions.exceptions import ExceptionHandler
from pulp.common.config import Config


DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                        'data')


class PulpClientTests(unittest.TestCase):
    """
    Base unit test class for all extension unit tests.
    """

    def setUp(self):
        super(PulpClientTests, self).setUp()

        self.config = SafeConfigParser()
        config_filename = os.path.join(DATA_DIR, 'test-override-client.conf')
        self.config = Config(config_filename)

        self.server_mock = mock.Mock()
        self.pulp_connection = PulpConnection('', server_wrapper=self.server_mock)
        self.bindings = Bindings(self.pulp_connection)

        # Disabling color makes it easier to grep results since the character codes aren't there
        self.recorder = okaara.prompt.Recorder()
        self.prompt = PulpPrompt(enable_color=False, output=self.recorder, record_tags=True)

        self.logger = logging.getLogger('pulp')
        self.exception_handler = ExceptionHandler(self.prompt, self.config)

        self.context = ClientContext(self.bindings, self.config, self.logger, self.prompt,
                                     self.exception_handler)

        self.cli = PulpCli(self.context)
        self.context.cli = self.cli
