from gettext import gettext as _
import logging
import os
import subprocess
import gzip
from pulp.plugins.util import misc
from pulp.plugins.util.publish_step import PluginStep, AtomicDirectoryPublishStep

from pulp_deb.common import constants
from pulp_deb.plugins.distributors import configuration

from pulp_deb.plugins.importers.sync import generate_internal_storage_path


_logger = logging.getLogger(__name__)


class WebPublisher(PluginStep):
    """
    Web publisher class that is responsible for the actual publishing
    of a repository via a web server
    """

    def __init__(self, repo, publish_conduit, config):
        """
        :param repo: Pulp managed Yum repository
        :type  repo: pulp.plugins.model.Repository
        :param publish_conduit: Conduit providing access to relative Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        super(WebPublisher, self).__init__(constants.PUBLISH_STEP_WEB_PUBLISHER,
                                           repo, publish_conduit, config)

        publish_dir = configuration.get_web_publish_dir(repo, config)
        self.web_working_dir = os.path.join(self.get_working_dir(), repo.id)
        master_publish_dir = configuration.get_master_publish_dir(repo, config)
        atomic_publish_step = AtomicDirectoryPublishStep(self.get_working_dir(),
                                                         [(repo.id, publish_dir)],
                                                         master_publish_dir,
                                                         step_type=constants.PUBLISH_STEP_OVER_HTTP)
        atomic_publish_step.description = _('Making files available via web.')

        self.add_child(PublishContentStep(working_dir=self.web_working_dir))
        self.add_child(PublishMetadataStep(working_dir=self.web_working_dir))
        self.add_child(atomic_publish_step)


class PublishMetadataStep(PluginStep):
    """
    Repository Metadata
    """

    def __init__(self, **kwargs):
        super(PublishMetadataStep, self).__init__(constants.PUBLISH_STEP_METADATA, **kwargs)
        self.context = None
        self.redirect_context = None
        self.description = _('Publishing Metadata.')

    def process_main(self, item=None):
        """
        Publish all the deb metadata or create a blank deb if this has never been synced
        """
        # Write out repo metadata into the working directory
        packfile_name = os.path.join(self.get_working_dir(), "Packages")
        packfile_gz_name = packfile_name + '.gz'

        with open(packfile_name, 'wb') as dpkg_out:
            packfile_gz = gzip.open(packfile_gz_name, 'wb')
            try:
                proc = subprocess.Popen(['dpkg-scanpackages', '-m', '.'],
                                        cwd=self.get_working_dir(),
                                        stdout=subprocess.PIPE)
                (out, err) = proc.communicate()
                dpkg_out.write(out)
                packfile_gz.write(out)
            finally:
                packfile_gz.close()


class PublishContentStep(PluginStep):
    """
    Publish Content
    """
    def __init__(self, **kwargs):
        super(PublishContentStep, self).__init__(constants.PUBLISH_STEP_CONTENT, **kwargs)
        self.description = _('Publishing Deb Content.')

    def initialize(self):
        """
        Perform setup required before we start processing the individual units
        """
        misc.mkdir(self.get_working_dir())

    def _get_total(self):
        return self.get_repo().content_unit_counts[constants.DEB_TYPE_ID]

    def get_iterator(self):
        """
        This method returns a generator to loop over items.
        The items created by this generator will be iterated over by the process_item method.

        :return: generator of items
        :rtype: GeneratorType of items
        """
        units_iterator = self.get_conduit().get_units(as_generator=True)
        return units_iterator

    def process_main(self, item=None):
        """
        Publish an individual deb file
        """
        filename = item.metadata["file_name"]
        tmp = os.path.join(self.get_working_dir(), filename)
        store = "/var/lib/pulp/content/deb/" + generate_internal_storage_path(filename)
        os.symlink(store, tmp)
        if os.path.exists(tmp):
            self.progress_successes += 1
