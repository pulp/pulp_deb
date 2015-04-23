from gettext import gettext as _
import logging
import os
import shutil

from debian import debian_support

from pulp.plugins.model import Unit
from pulp.plugins.util.publish_step import PluginStep, GetLocalUnitsStep, DownloadStep
from pulp_deb.common import constants
from nectar.request import DownloadRequest


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

        # config = self.get_config()
        working_dir = self.get_working_dir()
        # repo = self.get_repo()

        # create a Repository object to interact with
        self.add_child(GetMetadataStep())
        self.step_get_local_units = GetLocalUnitsStepDeb(constants.UNIT_KEY_FIELDS,
                                                         self.get_working_dir())
        self.add_child(self.step_get_local_units)
        self.add_child(
            DownloadStep(constants.SYNC_STEP_DOWNLOAD, downloads=self.generate_download_requests(),
                         repo=kwargs["repo"], config=kwargs["config"],
                         working_dir=kwargs["working_dir"],
                         description=_('Downloading remote files')))
        self.add_child(SaveUnits(working_dir))

    def generate_download_requests(self):
        """
        generator that yields DownloadRequests for needed units.

        :return:    generator of DownloadRequest instances
        :rtype:     collections.Iterable[DownloadRequest]
        """
        for unit_key in self.step_get_local_units.units_to_download:
            dest_dir = os.path.join(self.working_dir, os.path.basename(unit_key["filename"]))
            packages_url = self.get_config().get('feed')
            packages_url = packages_url.rpartition("/")
            for i in range(1, 5):
                packages_url = packages_url[0].rpartition("/")
            packages_url = packages_url[0] + "/" + unit_key["filename"]
            yield DownloadRequest(packages_url, dest_dir)


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
        packages_url = self.get_config().get('feed')
        packpath = os.path.join(self.get_working_dir() + "Packages")
        debian_support.download_file(packages_url + "Packages", packpath)
        for package in debian_support.PackageFile(packpath):
            self.parent.available_units.append(get_metadata(dict(package)))


class GetLocalUnitsStepDeb(GetLocalUnitsStep):
    def __init__(self, unit_key_fields, working_dir):
        super(GetLocalUnitsStepDeb, self).__init__(constants.WEB_IMPORTER_TYPE_ID,
                                                   constants.DEB_TYPE_ID, unit_key_fields,
                                                   working_dir)

    def process_main(self):
        super(GetLocalUnitsStepDeb, self).process_main()

    def _dict_to_unit(self, unit_dict):
        storage_path = unit_dict["filename"]
        unit_key = {}
        unit_dict.pop('_id')
        for val in self.unit_key_fields:
            unit_key[val] = unit_dict[val].encode("ascii")
        return Unit(constants.DEB_TYPE_ID, unit_key, unit_dict, storage_path)


class SaveUnits(PluginStep):
    def __init__(self, working_dir):
        super(SaveUnits, self).__init__(step_type=constants.SYNC_STEP_SAVE,
                                        plugin_type=constants.WEB_IMPORTER_TYPE_ID,
                                        working_dir=working_dir)
        self.description = _('Saving packages')

    def process_main(self):
        _logger.debug(self.description)
        for unit_key in self.parent.step_get_local_units.units_to_download:
            dest_dir = os.path.join(self.working_dir, os.path.basename(unit_key["filename"]))
            unit = self.get_conduit().init_unit(constants.DEB_TYPE_ID, unit_key, {},
                                                unit_key["filename"])
            shutil.move(dest_dir, unit.storage_path)
            self.get_conduit().save_unit(unit)


def get_metadata(package):
    """
    converts an dictionary representing a package to a unit key dictionary
    :param package: dictionary parsed by debian_support
    :type  package: dict
    :return:        unit key
    :rtype          dict
    """
    unit_key = {"name": package["Package"], "version": package["Version"],
                "architecture": package["Architecture"], "filename": package["Filename"]}
    return unit_key
