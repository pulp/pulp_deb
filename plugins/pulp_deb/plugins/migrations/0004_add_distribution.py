import logging
import re
from six import string_types
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

    # Copy Katello repo_importer releases fields from the relevant root repositories:
    # The following for loop is exclusive to Katello's pulp usage. Anyone not using
    # pulp_deb as part of Katello should be completely unaffected.
    deb_importer_filter = {
        'importer_type_id': ids.TYPE_ID_IMPORTER,
        'repo_id': {'$exists': True},
        'config.releases': {'$exists': False},
    }

    pattern = re.compile('^.+-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$')

    for repo_importer in importer_collection.find(deb_importer_filter).batch_size(100):
        repo_id = repo_importer['repo_id']

        if not isinstance(repo_id, string_types):
            continue

        match = re.match(pattern, repo_id)
        if match is not None:
            root_repo_id_candidate = match.group(1)
        else:
            continue

        id_filter = {
            'importer_type_id': ids.TYPE_ID_IMPORTER,
            'repo_id': root_repo_id_candidate,
            'config.releases': {'$exists': True},
        }

        projection = {
            'config': True,
        }

        root_repo_importer_candidates = importer_collection.find(id_filter, projection)

        if root_repo_importer_candidates.count() == 1:
            katello_root_repo_importer = list(root_repo_importer_candidates)[0]
        else:
            continue

        root_repo_releases = katello_root_repo_importer['config']['releases']

        msg = 'Adding config.releases from root repo_importer {} to repo_importer {}.'\
              ''.format(katello_root_repo_importer['_id'], repo_importer['_id'])
        _logger.debug(msg)
        importer_collection.update_one(
            {'_id': repo_importer['_id']},
            {'$set': {'config.releases': root_repo_releases}},
        )

    deb_importer_filter = {
        'importer_type_id': ids.TYPE_ID_IMPORTER,
        'config.releases': {'$exists': True},
    }

    changed_repos = set()

    # Perform a best effort to recreate the upstream distribution:
    for repo_importer in importer_collection.find(deb_importer_filter).batch_size(100):
        importer_releases = repo_importer['config']['releases']
        if isinstance(importer_releases, string_types) and importer_releases:
            distributions = importer_releases.split(',')
        else:
            continue

        repo_id = repo_importer['repo_id']

        for release in release_collection.find({'repoid': repo_id}).batch_size(100):
            original_distribution = None
            suite = ''
            codename = release['codename']
            if 'suite' in release:
                suite = release['suite']

            if codename in distributions:
                continue
            elif suite in distributions:
                original_distribution = suite

            component_filter = {
                'repoid': repo_id,
                'release': codename,
            }

            prefix = None
            for component in component_collection.find(component_filter).batch_size(100):
                plain_component = None
                prefix_msg_str = 'Removing the prefix of the name of component {} '\
                                 'and appending it to the distribution instead'
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
                    _logger.debug(prefix_msg_str.format(component['_id']))
                    component_collection.update_one(
                        {'_id': component['_id']},
                        {'$set': new_component_fields},
                    )
                elif original_distribution:
                    msg = 'Updating distribution of component {} from {} to {}.'.format(
                        component['_id'],
                        component['distribution'],
                        original_distribution,
                    )
                    _logger.debug(msg)
                    component_collection.update_one(
                        {'_id': component['_id']},
                        {'$set': {'distribution': original_distribution}},
                    )
                elif '/' in component['name']:
                    # only possible in the first iteration
                    plain_component = component['name'].strip('/').split('/')[-1]
                    prefix = '/'.join(component['name'].strip('/').split('/')[:-1])

                    if codename + '/' + prefix in distributions:
                        original_distribution = codename + '/' + prefix
                    elif suite + '/' + prefix in distributions:
                        original_distribution = suite + '/' + prefix
                    else:
                        # The approach did not work, out of ideas!
                        break

                    new_component_fields = {
                        'name': plain_component,
                        'distribution': original_distribution,
                    }
                    _logger.debug(prefix_msg_str.format(component['_id']))
                    component_collection.update_one(
                        {'_id': component['_id']},
                        {'$set': new_component_fields},
                    )

            msg = 'Updating distribution of release {} from {} to {}.'.format(
                release['_id'],
                release['distribution'],
                original_distribution,
            )
            _logger.debug(msg)
            release_collection.update_one(
                {'_id': release['_id']},
                {'$set': {'distribution': original_distribution}},
            )
            changed_repos.add(repo_id)

    output_file_path = '/var/lib/pulp/0004_deb_repo_republish_candidates.txt'

    if changed_repos:
        _logger.info('List of repos modified by the best effort migration (by repo_id):')

        with open(output_file_path, 'w') as output_file:
            for repo_id in changed_repos:
                output_file.write('{}\n'.format(repo_id))
                _logger.info(repo_id)

        msg = 'You should consider republishing these repositories.\n'\
              'Doing so will likely change their structure.\n'\
              'Depending on your usage scenario, this could affect your consumers!\n'\
              'This repo_id list has also been written to {}.'.format(output_file_path)

        _logger.info(msg)

    if warnings_encountered:
        msg = 'Warnings were encountered during the db migration!\n'\
              'Check the logs for more information, and consider deleting broken units.'
        _logger.warn(msg)
