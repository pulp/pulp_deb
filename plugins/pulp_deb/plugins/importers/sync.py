import logging
import os
import shutil
import tempfile
from gettext import gettext as _

from nectar.request import DownloadRequest
from pulp.plugins.util import publish_step, verification
from pulp.server.exceptions import PulpCodedException

from pulp_deb.common import constants, ids
from pulp_deb.plugins.db import models

_logger = logging.getLogger(__name__)


class RepoSync(publish_step.PluginStep):
    Type_Class_Map = {
        models.DebPackage.TYPE_ID: models.DebPackage,
    }

    def __init__(self, repo, conduit, config):
        """
        :param repo:        repository to sync
        :type  repo:        pulp.plugins.model.Repository
        :param conduit:     sync conduit to use
        :type  conduit:     pulp.plugins.conduits.repo_sync.RepoSyncConduit
        :param config:      config object for the sync
        :type  config:      pulp.plugins.config.PluginCallConfiguration
        """
        working_dir = tempfile.mkdtemp(dir=repo.working_dir)
        super(RepoSync, self).__init__(step_type=constants.SYNC_STEP,
                                       repo=repo,
                                       conduit=conduit,
                                       config=config,
                                       working_dir=repo.working_dir)
        self.description = _('Syncing Repository')

        self.step_metadata = GetMetadataStep()
        self.add_child(self.step_metadata)
        self.step_local_units = GetLocalUnitsStepDeb()
        self.add_child(self.step_local_units)
        download_dir = os.path.join(self.get_working_dir(), 'packages')
        self.add_child(
            publish_step.DownloadStep(
                constants.SYNC_STEP_DOWNLOAD,
                downloads=self.generate_download_requests(),
                repo=self.get_repo(),
                working_dir=download_dir,
                description=_('Downloading remote files')))
        self.add_child(SaveUnits(download_dir))

    def generate_download_requests(self):
        return []


class GetMetadataStep(publish_step.PluginStep):
    def __init__(self, **kwargs):
        """
        :param repo:        repository to sync
        :type  repo:        pulp.plugins.model.Repository
        :param conduit:     sync conduit to use
        :type  conduit:     pulp.plugins.conduits.repo_sync.RepoSyncConduit
        :param config:      config object for the sync
        :type  config:      pulp.plugins.config.PluginCallConfiguration
        """
        super(GetMetadataStep, self).__init__(constants.SYNC_STEP_METADATA,
                                              plugin_type=ids.TYPE_ID_IMPORTER,
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
        packages_path = self.get_config().get('package-file-path')
        if not packages_url.endswith('/'):
            packages_url += '/'
        if packages_path:
            if packages_path.startswith('/'):
                packages_path = packages_path[1:]
            packages_url = urlparse.urljoin(packages_url, packages_path)
        packpath = os.path.join(self.get_working_dir(), "Packages")
        debian_support.download_file(packages_url + "Packages", packpath)

        # mirror rather than additive, we want to remove packages if they have been removed
        new_units_names = [os.path.basename(dict(package)["Filename"]) for package in debian_support.PackageFile(packpath)]
        repo_name = self.get_repo().id
        existing_repo = "/var/www/pub/deb/web/{0}".format(repo_name)
        try:
            published_links = os.listdir(existing_repo)
            published_links.remove("Packages")
            published_links.remove("Packages.gz")

            for link in published_links:
                if link not in new_units_names:
                    associated_units = self.get_conduit().get_units()
                    for unit in associated_units:
                        uk = unit.unit_key
                        filename = "{0}_{1}_{2}.deb".format(uk["name"], uk["version"], uk["architecture"])
                        if filename == link:
                            self.get_conduit().remove_unit(unit)
                            link_path = existing_repo + "/" + link
                            if os.path.exists(link_path):
                                os.remove(link_path)
        except (ValueError, OSError) as e:
            _logger.debug(e)

        for package in debian_support.PackageFile(packpath):
            package_data = dict(package)
            metadata = get_metadata(package_data)
            unit_key_hash = get_key_hash(metadata)
            self.parent.deb_data[unit_key_hash] = {
                'file_name': os.path.basename(package_data['Filename']),
                'file_path': package_data['Filename'],
                'file_size': package_data['Size']
            }
            name, version, arch = metadata["name"], metadata["version"], metadata["architecture"]
            unit = DebPackage(name=name, version=version, architecture=arch)
            unit.unit_key_hash = unit_key_hash
            unit.metadata = metadata
            self.parent.available_units.append(unit)


class GetLocalUnitsStepDeb(publish_step.GetLocalUnitsStep):

    def __init__(self):
        super(GetLocalUnitsStepDeb, self).__init__(ids.TYPE_ID_IMPORTER)

    def _dict_to_unit(self, unit_dict):
        unit_key_hash = get_key_hash(unit_dict)
        file_name = self.parent.deb_data[unit_key_hash]['file_name']
        storage_path = generate_internal_storage_path(file_name)
        unit_dict.pop('_id')
        return_unit = self.get_conduit().init_unit(
            constants.TYPE_ID_DEB, unit_dict,
            {'file_name': file_name},
            storage_path)
        return return_unit


class SaveUnits(publish_step.PluginStep):
    def __init__(self, working_dir):
        super(SaveUnits, self).__init__(step_type=constants.SYNC_STEP_SAVE,
                                        plugin_type=ids.TYPE_ID_IMPORTER,
                                        working_dir=working_dir)
        self.description = _('Saving packages')

    def process_main(self):
        _logger.debug(self.description)
        for unit_key in self.parent.step_get_local_units.units_to_download:
            hash_key = unit_key.unit_key_hash
            file_name = self.parent.deb_data[hash_key]['file_name']
            storage_path = generate_internal_storage_path(file_name)
            dest_dir = os.path.join(self.working_dir, storage_path)
            # validate the size of the file downloaded
            file_size = int(self.parent.deb_data[hash_key]['file_size'])
            if file_size != os.stat(dest_dir).st_size:
                raise PulpCodedValidationException(error_code=error_codes.DEB1001,
                                                   file_name=file_name)

            unit = self.get_conduit().init_unit(constants.DEB_TYPE_ID, unit_key.metadata,
                                                {'file_name': file_name},

                                                storage_path)
            shutil.move(dest_dir, unit.storage_path)
            self.get_conduit().save_unit(unit)


