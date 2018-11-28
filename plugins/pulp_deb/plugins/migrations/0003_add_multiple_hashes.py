import logging
import os

from pulp.server import util as server_utils
from pulp.server.db import connection
from pulp.server.db.migrations.lib import utils as migration_utils


_logger = logging.getLogger(__name__)

CHECKSUM_TYPES = [server_utils.TYPE_MD5,
                  server_utils.TYPE_SHA1,
                  server_utils.TYPE_SHA256]


def migrate(*args, **kwargs):
    """
    Add seperate fields for md5sum, sha1, sha256
    """
    warnings_encountered = False
    deb_collection = connection.get_collection('units_deb')
    deb_count = deb_collection.count()

    with migration_utils.MigrationProgressLog('Deb Package', deb_count) as progress_log:
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

            with open(storage_path, 'r') as file_handle:
                checksums = server_utils.calculate_checksums(file_handle, CHECKSUM_TYPES)

            new_fields = {
                'md5sum': checksums[server_utils.TYPE_MD5],
                'sha1': checksums[server_utils.TYPE_SHA1],
                'sha256': checksums[server_utils.TYPE_SHA256],
            }

            if checksums[deb_package['checksumtype']] != deb_package['checksum']:
                raise Exception('New checksum does not match existing checksum for\n'
                                '_id = {}\nfile = {}'.format(package_id, storage_path))

            deb_collection.update_one({'_id': package_id},
                                      {'$set': new_fields},)
            progress_log.progress()

    if warnings_encountered:
        msg = 'Warnings were encountered during the db migration!\n'\
              'Check the logs for more information, and consider deleting broken units.'
        _logger.warn(msg)
