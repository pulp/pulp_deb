from gettext import gettext as _
import logging
import os
import commands
import gzip
from pulp.plugins.util.publish_step import PluginStep, AtomicDirectoryPublishStep

from pulp_deb.common import constants
from pulp_deb.plugins.distributors import configuration


_LOG = logging.getLogger(__name__)


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
        self.working_directory = kwargs["working_dir"]
        self.description = _('Publishing Metadata.')

    def process_main(self):
        """
        Publish all the deb metadata or create a blank deb if this has never been synced
        """
        # Write out repo metadata into the working directory
        packfile = os.path.join(self.working_directory, "Packages")
        status, out = commands.getstatusoutput("cd " + self.working_directory + "; dpkg-scanpackages -m . > " + packfile)
        f_in = open(packfile, 'rb')
        f_out = gzip.open(packfile + '.gz', 'wb')
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()


class PublishContentStep(PluginStep):
    """
    Publish Content
    """

    def __init__(self, **kwargs):
        super(PublishContentStep, self).__init__(constants.PUBLISH_STEP_CONTENT, **kwargs)
        self.context = None
        self.redirect_context = None
        self.description = _('Publishing Deb Content.')
        self.unit = None
        self.working_directory = kwargs["working_dir"]
        os.makedirs(self.working_directory)

    def process_main(self):
        """
        Publish all the deb files themselves
        """
        units = self.get_conduit().get_units()
        for unit in units:
            path = os.path.join(self.working_directory, os.path.basename(unit.storage_path))
            unit_path = os.path.join(constants.CONTENT_DIR, unit.storage_path)
            os.symlink(unit_path, path)
