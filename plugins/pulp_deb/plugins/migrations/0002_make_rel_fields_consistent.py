import logging
import os

from debian.debfile import DebFile, ArError

from pulp.server.db import connection
from pulp.server.db.migrations.lib import utils
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

IGNORED_FIELDS_MAP = dict(
    source='Source',
    maintainer='Maintainer',
    section='Section',
    priority='Priority',
    homepage='Homepage',
    description='Description',
)


def migrate(*args, **kwargs):
    """
    This migration should achieve the following:

    * All existing entries in the units_deb collection should store parsed
      relationship information in any relevant REL_FIELDS. (These fields should
      never be used for plain Debian relationship strings).
    * The control_file field is added to all entries in the units_deb collection.
      This field should contain a dict, containing all control file fields
      associated with the relevant .deb package. This way we can ensure the db
      contains all control file information needed to publish a repo containing
      the unit (including any plain Debian relationship strings).
    """
    warnings_encountered = False
    deb_collection = connection.get_collection('units_deb')
    deb_count = deb_collection.count()

    with utils.MigrationProgressLog('Deb Package', deb_count) as progress_log:
        for deb_package in deb_collection.find({}).batch_size(100):
            storage_path = deb_package['_storage_path']
            package_id = deb_package['_id']
            if not os.path.exists(storage_path):
                warnings_encountered = True
                msg = 'deb package file corresponding to db_unit with _id = {}\n'\
                      'was not found at _storage_path = {}.\n'\
                      'The unit was not migrated!'.format(package_id, storage_path)
                _logger.warn(msg)
                continue

            try:
                control_fields = DebFile(storage_path).debcontrol()
            except ArError as error:
                warnings_encountered = True
                msg = 'deb package file corresponding to db_unit with _id = {}\n'\
                      'with _storage_path = {}\n'\
                      'was not recognized as a valid deb file:\n'\
                      '{}\n'\
                      'The unit was not migrated!'.format(package_id,
                                                          storage_path,
                                                          str(error),)
                _logger.warn(msg)
                continue

            new_fields = dict()
            remove_fields = dict()

            new_fields.update(control_fields=control_fields)

            # Add parsed relational fields and remove empty relational fields:
            for field, deb_key in REL_FIELDS_MAP.iteritems():
                if deb_key in control_fields:
                    new_fields[field] = DependencyParser.from_string(control_fields[deb_key])
                else:
                    remove_fields[field] = ''

            # Also (re)add any fields that may have been previously ignored:
            for field, deb_key in IGNORED_FIELDS_MAP.iteritems():
                if deb_key in control_fields:
                    new_fields[field] = control_fields[deb_key]

            deb_collection.update_one({'_id': package_id},
                                      {'$set': new_fields},)

            deb_collection.update_one({'_id': package_id},
                                      {'$unset': remove_fields},)

            progress_log.progress()

    if warnings_encountered:
        msg = 'Warnings were encountered during the db migration!\n'\
              'Check the logs for more information, and consider deleting broken units.'
        _logger.warn(msg)
