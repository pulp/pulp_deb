import logging
import os
import urlparse
from gettext import gettext as _

from debpkgr import aptrepo
from nectar.request import DownloadRequest
from pulp.plugins.util import misc, publish_step
from pulp.common.error_codes import Error
from pulp.server.exceptions import PulpCodedTaskFailedException

from pulp_deb.common import constants, ids
from pulp_deb.plugins.db import models

_logger = logging.getLogger(__name__)


DEBSYNC001 = Error(
    "DEBSYNC001",
    "Unable to sync %(repo_id)s from %(feed_url)s:"
    " expected one comp, got %(comp_count)s",
    ["repo_id", "feed_url", "comp_count"])

DEBSYNC002 = Error(
    "DEBSYNC002",
    "Unable to sync %(repo_id)s from %(feed_url)s: mismatching checksums"
    " for %(filename)s: expected %(checksum_expected)s,"
    " actual %(checksum_actual)s",
    ["repo_id", "feed_url", "filename", "checksum_expected", "checksum_actual"])


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
        super(RepoSync, self).__init__(step_type=constants.SYNC_STEP,
                                       repo=repo,
                                       conduit=conduit,
                                       config=config)
        self.description = _('Syncing Repository')

        self.apt_repo_meta = None
        # https://pulp.plan.io/issues/2765 should remove the need to hardcode
        # the dist/component here
        self.feed_url = self.get_config().get('feed').strip('/') + '/dists/stable/'
        self.release_file = os.path.join(self.get_working_dir(),
                                         "Release")
        self.available_units = None
        rel_url = urlparse.urljoin(self.feed_url, 'Release')
        _logger.info("Downloading %s", rel_url)
        self.add_child(publish_step.DownloadStep(
            constants.SYNC_STEP_RELEASE_DOWNLOAD,
            plugin_type=ids.TYPE_ID_IMPORTER,
            description=_('Retrieving metadata: release file'),
            downloads=[
                DownloadRequest(rel_url, self.release_file)]))
        self.add_child(ParseReleaseStep(constants.SYNC_STEP_RELEASE_PARSE))
        self.step_download_Packages = publish_step.DownloadStep(
            constants.SYNC_STEP_PACKAGES_DOWNLOAD,
            plugin_type=ids.TYPE_ID_IMPORTER,
            description=_('Retrieving metadata: Packages files'))
        self.add_child(self.step_download_Packages)

        self.add_child(ParsePackagesStep(constants.SYNC_STEP_PACKAGES_PARSE))

        self.step_local_units = publish_step.GetLocalUnitsStep(
            importer_type=ids.TYPE_ID_IMPORTER)
        self.add_child(self.step_local_units)

        self.add_child(CreateRequestsUnitsToDownload(
            constants.SYNC_STEP_UNITS_DOWNLOAD_REQUESTS))

        self.step_download_units = publish_step.DownloadStep(
            constants.SYNC_STEP_UNITS_DOWNLOAD,
            plugin_type=ids.TYPE_ID_IMPORTER,
            description=_('Retrieving units'))
        self.add_child(self.step_download_units)

        self.add_child(SaveDownloadedUnits(constants.SYNC_STEP_SAVE))


class ParseReleaseStep(publish_step.PluginStep):
    def process_main(self, item=None):
        self.parent.apt_repo_meta = repometa = aptrepo.AptRepoMeta(
            release=open(self.parent.release_file, "rb"),
            upstream_url=self.parent.feed_url)
        components = list(repometa.iter_component_arch_binaries())
        if len(components) != 1:
            raise PulpCodedTaskFailedException(
                DEBSYNC001, repo_id=self.get_repo().repo_obj.repo_id,
                feed_url=self.parent.feed_url,
                comp_count=len(components))
        dl_reqs = repometa.create_Packages_download_requests(
            self.get_working_dir())
        self.parent.step_download_Packages._downloads = [
            DownloadRequest(x.url, x.destination, data=x.data)
            for x in dl_reqs]


class ParsePackagesStep(publish_step.PluginStep):
    def process_main(self, item=None):
        dl_reqs = self.parent.step_download_Packages.downloads
        repometa = self.parent.apt_repo_meta
        repometa.validate_component_arch_packages_downloads(dl_reqs)
        units = []
        for ca in repometa.iter_component_arch_binaries():
            for pkg in ca.iter_packages():
                pkg['checksumtype'] = 'sha256'
                pkg['checksum'] = pkg['SHA256']
                unit = models.DebPackage.from_metadata(pkg)
                units.append(unit)
        self.parent.step_local_units.available_units = units


class CreateRequestsUnitsToDownload(publish_step.PluginStep):
    def process_main(self, item=None):
        wdir = os.path.join(self.get_working_dir())
        csums_to_download = dict(
            (u.checksum, u)
            for u in self.parent.step_local_units.units_to_download)
        repometa = self.parent.apt_repo_meta
        reqs = []

        # upstream_url points to the dist itself, dists/stable
        upstream_url = repometa.upstream_url.rstrip('/')
        upstream_url = os.path.dirname(os.path.dirname(upstream_url))

        step_download_units = self.parent.step_download_units
        step_download_units.path_to_unit = dict()
        for ca in repometa.iter_component_arch_binaries():
            dest_dir = os.path.join(wdir, "packages", ca.component)
            misc.mkdir(dest_dir)

            for pkg in ca.iter_packages():
                unit = csums_to_download.get(pkg['SHA256'])
                if not unit:
                    continue
                url = os.path.join(upstream_url, pkg['Filename'])
                dest = os.path.join(dest_dir, os.path.basename(url))
                reqs.append(DownloadRequest(url, dest))
                step_download_units.path_to_unit[dest] = unit

        step_download_units._downloads = reqs


class SaveDownloadedUnits(publish_step.PluginStep):
    def process_main(self, item=None):
        path_to_unit = self.parent.step_download_units.path_to_unit
        repo = self.get_repo().repo_obj
        for path, unit in sorted(path_to_unit.items()):
            # Verify checksum first
            with open(path, "rb") as fobj:
                csum = unit._compute_checksum(fobj)
            if csum != unit.checksum:
                raise PulpCodedTaskFailedException(
                    DEBSYNC002, repo_id=self.get_repo().repo_obj.repo_id,
                    feed_url=self.parent.feed_url,
                    filename=os.path.basename(path),
                    checksum_expected=unit.checksum,
                    checksum_actual=csum)
            unit.save_and_associate(path, repo)
