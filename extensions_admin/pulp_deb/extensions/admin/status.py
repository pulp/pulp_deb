# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains functionality related to rendering the progress report for the Win
plugins (both the sync and publish operations).
"""

from gettext import gettext as _

from pulp.client.commands.repo.sync_publish import StatusRenderer
from pulp.client.commands.repo.status import PublishStepStatusRenderer

from pulp_deb.common import constants, ids


class CancelException(Exception):
    pass


class PackageStatusRenderer(StatusRenderer):
    def __init__(self, context):
        super(PackageStatusRenderer, self).__init__(context)

        self.publish_steps_renderer = PublishStepStatusRenderer(context)

        # Publish Steps
        self.publish_steps_last_state = dict.fromkeys(
            constants.PUBLISH_STEPS,
            constants.STATE_NOT_STARTED)

        self.publish_http_last_state = constants.STATE_NOT_STARTED
        self.publish_https_last_state = constants.STATE_NOT_STARTED

        # UI Widgets
        self.packages_bar = self.prompt.create_progress_bar()
        self.publish_http_spinner = self.prompt.create_spinner()
        self.publish_https_spinner = self.prompt.create_spinner()

    def display_report(self, progress_report):
        """
        Displays the contents of the progress report to the user. This will
        aggregate the calls to render individual sections of the report.
        """

        # There's a small race condition where the task will indicate it's
        # begun running but the importer has yet to submit a progress report
        # (or it has yet to be saved into the task). This should be alleviated
        # by the if statements below.
        try:
            # Sync Steps
            if ids.TYPE_ID_IMPORTER in progress_report:
                pass

            # Publish Steps
            if ids.TYPE_ID_DISTRIBUTOR in progress_report:
                # Proxy to the standard renderer
                self.publish_steps_renderer.display_report(progress_report)

        except CancelException:
            self.prompt.render_failure_message(_('Operation canceled.'))
