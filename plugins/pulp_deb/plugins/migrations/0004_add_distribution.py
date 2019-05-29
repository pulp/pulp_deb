import logging
from pulp.server.db import connection
from pulp_deb.common import ids
from pymongo.errors import OperationFailure

_logger = logging.getLogger(__name__)


def prepare_reindex_migration(*args, **kwargs):
    """
    Add a naive distribution field to both deb releases and components, to
    ensure we will survive uniqueness constraints post index creation.
    """
    release_collection = connection.get_collection('units_deb_release')
    component_collection = connection.get_collection('units_deb_component')

    unit_filter = {'distribution': {'$exists': False}}

    # Migrate the units_deb_release collection:
    for release in release_collection.find(unit_filter, ['codename']).batch_size(100):
        new_release_fields = {
            'distribution': release['codename'],
        }

        release_collection.update_one(
            {'_id': release['_id']},
            {'$set': new_release_fields},
        )

    # Migrate the units_deb_component collection:
    for component in component_collection.find(unit_filter, ['release']).batch_size(100):
        new_component_fields = {
            'distribution': component['release'],
        }

        component_collection.update_one(
            {'_id': component['_id']},
            {'$set': new_component_fields},
        )


def migrate(*args, **kwargs):
    """
    Provide a best effort migration for the previously added naive distribution
    fields for both deb releases and components.
    """
    warnings_encountered = False
    release_collection = connection.get_collection('units_deb_release')
    component_collection = connection.get_collection('units_deb_component')
    importer_collection = connection.get_collection('repo_importers')

    # If they exist, drop the old uniqueness constraints:
    try:
        release_collection.drop_index("codename_1_repoid_1")
    except OperationFailure as exception:
        _logger.info("Ignoring expected OperationFailure exception:")
        _logger.info(str(exception))

    try:
        component_collection.drop_index("name_1_release_1_repoid_1")
    except OperationFailure as exception:
        _logger.info("Ignoring expected OperationFailure exception:")
        _logger.info(str(exception))

    deb_importer_filter = {'importer_type_id': ids.TYPE_ID_IMPORTER}

    # Perform a best effort to recreate the upstream distribution:
    for repo_importer in importer_collection.find(deb_importer_filter).batch_size(100):
        distributions = repo_importer['config']['releases'].split(',')

        release_filter = {'repoid': repo_importer['repo_id']}

        for release in release_collection.find(release_filter).batch_size(100):
            original_distribution = None
            if release['codename'] in distributions:
                continue
            elif release['suite'] in distributions:
                original_distribution = release['suite']

            component_filter = {
                'repoid': repo_importer['repo_id'],
                'release': release['codename'],
            }

            prefix = None
            for component in component_collection.find(component_filter).batch_size(100):
                plain_component = None
                if prefix:
                    # never the case in the first iteration
                    plain_component = component['name'].strip('/').split('/')[-1]
                    if prefix != '/'.join(component['name'].strip('/').split('/')[:-1]):
                        warnings_encountered = True
                        msg = 'Encountered component unit with inconsistent prefix!\n'\
                              '_id = {}\n'\
                              'The unit was not migrated!'.format(component['_id'])
                        _logger.warn(msg)
                        continue
                    new_component_fields = {
                        'name': plain_component,
                        'distribution': original_distribution,
                    }
                    component_collection.update_one(
                        {'_id': component['_id']},
                        {'$set': new_component_fields},
                    )
                elif original_distribution:
                    new_component_fields = {'distribution': original_distribution}
                    component_collection.update_one(
                        {'_id': component['_id']},
                        {'$set': new_component_fields},
                    )
                elif '/' in component['name']:
                    # only possible in the first iteration
                    plain_component = component['name'].strip('/').split('/')[-1]
                    prefix = '/'.join(component['name'].strip('/').split('/')[:-1])

                    if release['codename'] + '/' + prefix in distributions:
                        original_distribution = release['codename'] + '/' + prefix
                    elif release['suite'] + '/' + prefix in distributions:
                        original_distribution = release['suite'] + '/' + prefix
                    else:
                        # The approach did not work, out of ideas!
                        break

                    new_component_fields = {
                        'name': plain_component,
                        'distribution': original_distribution,
                    }
                    component_collection.update_one(
                        {'_id': component['_id']},
                        {'$set': new_component_fields},
                    )

            new_release_fields = {'distribution': original_distribution}
            release_collection.update_one(
                {'_id': release['_id']},
                {'$set': new_release_fields},
            )

    if warnings_encountered:
        msg = 'Warnings were encountered during the db migration!\n'\
              'Check the logs for more information, and consider deleting broken units.'
        _logger.warn(msg)
