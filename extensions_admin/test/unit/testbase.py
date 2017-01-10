import os
from pulp_rpm.devel import client_base

client_base.DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                    "data")


class PulpClientTests(client_base.PulpClientTests):
    pass
