from gettext import gettext as _
import logging
from pulp.plugins.util.publish_step import PluginStep
from pulp_deb.common import constants

_logger = logging.getLogger(__name__)


class SyncStep(PluginStep):
    def __init__(self, **kwargs):
        """
        :param repo:        repository to sync
        :type  repo:        pulp.plugins.model.Repository
        :param conduit:     sync conduit to use
        :type  conduit:     pulp.plugins.conduits.repo_sync.RepoSyncConduit
        :param config:      config object for the sync
        :type  config:      pulp.plugins.config.PluginCallConfiguration
        :param working_dir: full path to the directory in which transient files
                            should be stored before being moved into long-term
                            storage. This should be deleted by the caller after
                            step processing is complete.
        :type  working_dir: basestring
        """
        super(SyncStep, self).__init__(constants.IMPORT_STEP_MAIN,
                                       plugin_type=constants.WEB_IMPORTER_TYPE_ID, **kwargs)
        self.description = _('Syncing Repository')

        # Unit keys, populated by GetMetadataStep
        self.available_units = []
        # populated by GetMetadataStep
        self.tags = {}

        # config = self.get_config()
        # working_dir = self.get_working_dir()
        # repo = self.get_repo()

        # create a Repository object to interact with
        # TODO Create a step to get metadata files & read them
        self.add_child(GetMetadataStep())
        # TODO create a pulp.plugins.publish_step.GetLocalUnitsStep to import the units we
        # already know about
        # TODO create a DownloadStep to get the new units
        # TODO create a SaveUnits step to process the saved files (check pulp_docker for example


class GetMetadataStep(PluginStep):
    def __init__(self, **kwargs):
        """
        :param repo:        repository to sync
        :type  repo:        pulp.plugins.model.Repository
        :param conduit:     sync conduit to use
        :type  conduit:     pulp.plugins.conduits.repo_sync.RepoSyncConduit
        :param config:      config object for the sync
        :type  config:      pulp.plugins.config.PluginCallConfiguration
        :param working_dir: full path to the directory in which transient files
                            should be stored before being moved into long-term
                            storage. This should be deleted by the caller after
                            step processing is complete.
        :type  working_dir: basestring
        """
        super(GetMetadataStep, self).__init__(constants.IMPORT_STEP_METADATA,
                                              plugin_type=constants.WEB_IMPORTER_TYPE_ID,
                                              **kwargs)
        self.description = _('Retrieving metadata')

    def process_main(self):
        """
        determine what images are available upstream, get the upstream tags, and
        save a list of available unit keys on the parent step
        """
        super(GetMetadataStep, self).process_main()
        _logger.debug(self.description)
        # TODO Download metadata here
