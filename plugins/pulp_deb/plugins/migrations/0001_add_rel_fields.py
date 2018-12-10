import logging
import os

from debian.debfile import DebFile, ArError

from pulp.server.db import connection
from pulp_deb.plugins.db.models import DependencyParser


_logger = logging.getLogger(__name__)

REL_FIELDS_MAP = dict(
    breaks="Breaks",
    conflicts="Conflicts",
    depends="Depends",
    enhances="Enhances",
    pre_depends="Pre-Depends",
    provides="Provides",
    recommends="Recommends",
    replaces="Replaces",
    suggests="Suggests",
)


def migrate(*args, **kwargs):
    """
    Add relationship fields (breaks/depends/etc)
    """
    warnings_encountered = False
    collection = connection.get_collection('units_deb')
    for unit in collection.find({}):
        unit_id = unit['_id']
        path = unit['_storage_path']
        if not os.path.exists(path):
            warnings_encountered = True
            msg = 'deb package file corresponding to db_unit with _id = {}\n'\
                  'was not found at _storage_path = {}.\n'\
                  'The unit was not migrated!'.format(unit_id, path)
            _logger.warn(msg)
            continue

        try:
            control_fields = DebFile(path).debcontrol()
        except ArError as error:
            warnings_encountered = True
            msg = 'deb package file corresponding to db_unit with _id = {}\n'\
                  'with _storage_path = {}\n'\
                  'was not recognized as a valid deb file:\n'\
                  '{}\n'\
                  'The unit was not migrated!'.format(unit_id,
                                                      path,
                                                      str(error),)
            _logger.warn(msg)
            continue

        update_dict = dict()
        for field, deb_key in REL_FIELDS_MAP.iteritems():
            if deb_key in control_fields:
                update_dict[field] = DependencyParser.from_string(control_fields[deb_key])
            else:
                update_dict[field] = []

        collection.update_one(dict(_id=unit_id),
                              {'$set': update_dict})

    if warnings_encountered:
        msg = 'Warnings were encountered during the db migration!\n'\
              'Check the logs for more information, and consider deleting broken units.'
        _logger.warn(msg)
