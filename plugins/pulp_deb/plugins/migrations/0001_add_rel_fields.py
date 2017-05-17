import logging
import os

from pulp.server.db import connection
from pulp_deb.plugins.db import models


_logger = logging.getLogger(__name__)


def migrate(*args, **kwargs):
    """
    Add relationship fields (breaks/depends/etc)
    """
    collection = connection.get_collection('units_deb')
    for unit in collection.find({}):
        unit_id = unit['_id']
        path = unit['_storage_path']
        if not os.path.exists(path):
            continue

        m = models.DebPackage.from_file(path)
        update_dict = dict()
        for fname in m.REL_FIELDS:
            update_dict[fname] = getattr(m, fname)
        collection.update_one(dict(_id=unit_id),
                              {'$set': update_dict})
