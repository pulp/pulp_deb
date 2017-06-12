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

        self.apt_repo_meta = {}
        self.unit_relative_urls = {}
        self.unit_suites = {}
        self.feed_url = self.get_config().get('feed').strip('/')
        self.suites = self.get_config().get('suites', 'stable').split(',')
        self.architectures = split_or_none(self.get_config().get('architectures'))
        self.components = split_or_none(self.get_config().get('components'))
        self.release_files = {
            suite: os.path.join(self.get_working_dir(), suite, 'Release')
            for suite in self.suites}
        self.available_units = None
        self.feed_urls = {
            suite: urlparse.urljoin(self.feed_url + '/', '/'.join(['dists', suite]))
            for suite in self.suites}
        self.release_urls = {
            suite: urlparse.urljoin(self.feed_urls[suite] + '/', 'Release')
            for suite in self.suites}
        for suite in self.suites:
            misc.mkdir(os.path.dirname(self.release_files[suite]))
            _logger.info("Downloading %s", self.release_urls[suite])
        self.add_child(publish_step.DownloadStep(
            constants.SYNC_STEP_RELEASE_DOWNLOAD,
            plugin_type=ids.TYPE_ID_IMPORTER,
            description=_('Retrieving metadata: release file(s)'),
            downloads=[
                DownloadRequest(self.release_urls[suite], self.release_files[suite])
                for suite in self.suites]))
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
        suites = self.parent.suites
        components = self.parent.components
        architectures = self.parent.architectures
        sync_conduit = self.parent.get_conduit()
        repo_scratchpad = sync_conduit.get_repo_scratchpad() or {}
        repo_scratchpad['releases'] = {}
        dl_reqs = []
        for suite in suites:
            self.parent.apt_repo_meta[suite] = repometa = aptrepo.AptRepoMeta(
                release=open(self.parent.release_files[suite], "rb"),
                upstream_url=self.parent.feed_urls[suite])
            repo_scratchpad['releases'][repometa.codename] = {
                'suite': repometa.release.get('suite')}
            dl_reqs.extend(repometa.create_Packages_download_requests(
                self.get_working_dir()))
        # Filter the release_dl_reqs by selected component and architecture
        if components:
            dl_reqs = [
                x for x in dl_reqs
                if x.data['component'] in components]
        if architectures:
            dl_reqs = [
                x for x in dl_reqs
                if x.data['architecture'] in architectures]
        self.parent.step_download_Packages._downloads = [
            DownloadRequest(x.url, x.destination, data=x.data)
            for x in dl_reqs]
        sync_conduit.set_repo_scratchpad(repo_scratchpad)


class ParsePackagesStep(publish_step.PluginStep):
    def process_main(self, item=None):
        suites = self.parent.suites
        dl_reqs = self.parent.step_download_Packages.downloads
        units = []
        for suite in suites:
            repometa = self.parent.apt_repo_meta[suite]
            repometa.validate_component_arch_packages_downloads(
                [dlr for dlr in dl_reqs
                    if dlr.url.startswith(self.parent.feed_urls[suite])])
            for ca in repometa.iter_component_arch_binaries():
                for pkg in ca.iter_packages():
                    pkg['checksumtype'] = 'sha256'
                    pkg['checksum'] = pkg['SHA256']
                    # TODO: save suite(s) in unit
                    pkg['component'] = ca.component
                    if pkg['checksum'] in self.parent.unit_relative_urls:
                        self.parent.unit_suites[pkg['checksum']].append(suite)
                        continue
                    self.parent.unit_relative_urls[pkg['checksum']] = pkg['Filename']
                    self.parent.unit_suites[pkg['checksum']] = [suite]
                    unit = models.DebPackage.from_metadata(pkg)
                    units.append(unit)
        self.parent.step_local_units.available_units = units


class CreateRequestsUnitsToDownload(publish_step.PluginStep):
    def process_main(self, item=None):
        wdir = os.path.join(self.get_working_dir())
        reqs = []

        feed_url = self.parent.feed_url

        step_download_units = self.parent.step_download_units
        step_download_units.path_to_unit = dict()
        dirs_to_create = set()

        for unit in self.parent.step_local_units.units_to_download:
            # TODO: devide files into more subdirectories they can become to much to handle
            dest_dir = os.path.join(wdir, "packages", unit.component or 'main')
            dirs_to_create.add(dest_dir)
            url = os.path.join(feed_url, self.parent.unit_relative_urls[unit.checksum])
            dest = os.path.join(dest_dir, os.path.basename(url))
            reqs.append(DownloadRequest(url, dest))
            step_download_units.path_to_unit[dest] = unit

        for dest_dir in dirs_to_create:
            misc.mkdir(dest_dir)
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


def split_or_none(data):
    if data:
        return data.split(',')
    return None
