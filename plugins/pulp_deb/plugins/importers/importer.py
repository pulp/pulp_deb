import logging
from pulp.common import config as config_utils
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.importer import Importer
from pulp.plugins.util import importer_config
from pulp.server.db import model as platform_models
from gettext import gettext as _
from pulp_deb.common.ids import SUPPORTED_TYPES, TYPE_ID_IMPORTER
from pulp_deb.plugins.db import models
from pulp_deb.plugins.importers import sync

_LOG = logging.getLogger(__name__)
# The leading '/etc/pulp/' will be added by the read_json_config method.
CONF_FILENAME = 'server/plugins.conf.d/%s.json' % TYPE_ID_IMPORTER


def entry_point():
    return DebImporter, config_utils.read_json_config(CONF_FILENAME)


class DebImporter(Importer):
    Type_Class_Map = sync.RepoSync.Type_Class_Map

    def __init__(self):
        super(DebImporter, self).__init__()
        self.sync_cancelled = False

    @classmethod
    def metadata(cls):
        return {
            'id': TYPE_ID_IMPORTER,
            'display_name': _('Debian importer'),
            'types': sorted(SUPPORTED_TYPES),
        }

    def validate_config(self, repo, config):
        try:
            importer_config.validate_config(config)
            return True, None
        except importer_config.InvalidConfig as e:
            # Concatenate all of the failure messages into a single message
            msg = _('Configuration errors:\n')
            for failure_message in e.failure_messages:
                msg += failure_message + '\n'
            msg = msg.rstrip()  # remove the trailing \n
            return False, msg

    def upload_unit(self, transfer_repo, type_id, unit_key, metadata,
                    file_path, conduit, config):
        if type_id not in SUPPORTED_TYPES:
            return self.fail_report(
                "Unsupported unit type {0}".format(type_id))
        model_class = plugin_api.get_unit_model_by_id(type_id)
        repo = transfer_repo.repo_obj
        conduit.repo = repo
        metadata = metadata or {}

        unit_data = {}
        unit_data.update(metadata or {})
        unit_data.update(unit_key or {})

        try:
            unit = model_class.from_file(file_path, unit_data)
        except models.Error as e:
            return self.fail_report(str(e))

        unit = unit.save_and_associate(file_path, repo)
        return dict(success_flag=True, summary="",
                    details=dict(
                        unit=dict(unit_key=unit.unit_key,
                                  metadata=unit.all_properties)))

    def import_units(self, source_transfer_repo, dest_transfer_repo,
                     import_conduit, config, units=None):
        source_repo = platform_models.Repository.objects.get(
            repo_id=source_transfer_repo.id)
        dest_repo = platform_models.Repository.objects.get(
            repo_id=dest_transfer_repo.id)

        if not units:
            # If no units are passed in, assume we will use all units from
            # source repo
            units = models.repo_controller.find_repo_content_units(
                source_repo, yield_content_unit=True)

        units = sorted(set(units))
        _LOG.info("Importing %s units from %s to %s" %
                  (len(units), source_repo.id, dest_repo.id))
        for u in units:
            u.associate(dest_repo)
        _LOG.debug("%s units from %s have been associated to %s" %
                   (len(units), source_repo.id, dest_repo.id))
        return units

    @classmethod
    def fail_report(cls, message):
        # this is the format returned by the original importer. I'm not sure if
        # anything is actually parsing it
        details = {'errors': [message]}
        return {'success_flag': False, 'summary': '', 'details': details}

    def sync_repo(self, transfer_repo, sync_conduit, call_config):
        """
        Synchronizes content into the given repository. This call is
        responsible for adding new content units to Pulp as well as
        associating them to the given repository.

        While this call may be implemented using multiple threads, its
        execution from the Pulp server's standpoint should be synchronous.
        This call should not return until the sync is complete.

        It is not expected that this call be atomic. Should an error occur, it
        is not the responsibility of the importer to rollback any unit
        additions or associations that have been made.

        The returned report object is used to communicate the results of the
        sync back to the user. Care should be taken to i18n the free text "log"
        attribute in the report if applicable.

        :param transfer_repo: metadata describing the repository
        :type  transfer_repo: pulp.plugins.model.Repository

        :param sync_conduit: provides access to relevant Pulp functionality
        :type  sync_conduit: pulp.plugins.conduits.repo_sync.RepoSyncConduit

        :param call_config: plugin configuration
        :type  call_config: pulp.plugins.config.PluginCallConfiguration

        :return: report of the details of the sync
        :rtype:  pulp.plugins.model.SyncReport
        """
        _LOG.info("Repo sync started.")
        sync_conduit.repo = transfer_repo.repo_obj
        self._current_sync = sync.RepoSync(transfer_repo, sync_conduit, call_config)
        report = self._current_sync.process_lifecycle()
        _LOG.info("Repo sync finished.")
        return report
