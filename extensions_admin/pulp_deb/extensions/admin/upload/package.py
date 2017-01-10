# -*- coding: utf-8 -*-
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _

from pulp.client.commands.repo.upload import UploadCommand

from pulp_deb.common.ids import TYPE_ID_DEB


NAME_DEB = 'deb'
DESC_DEB = _('uploads one or more deb files into a repository')
SUFFIX_DEB = '.deb'


class _CreatePackageCommand(UploadCommand):
    """
    Base command for uploading. This shouldn't be instantiated directly
    outside of this module in favor of one of the type-specific subclasses.
    """
    TYPE_ID = None
    SUFFIX = None
    NAME = None
    DESCRIPTION = None

    def __init__(self, context, upload_manager):
        super(_CreatePackageCommand, self).__init__(
            context, upload_manager, name=self.NAME,
            description=self.DESCRIPTION)
        self.type_id = self.TYPE_ID
        self.suffix = self.SUFFIX

    def determine_type_id(self, filename, **kwargs):
        return self.TYPE_ID

    def matching_files_in_dir(self, directory):
        all_files_in_dir = super(_CreatePackageCommand, self).matching_files_in_dir(directory)  # noqa
        pkgs = [f for f in all_files_in_dir if f.endswith(self.suffix)]
        return pkgs

    def generate_unit_key_and_metadata(self, filename, **kwargs):
        # These are extracted server-side, so nothing to do here.
        metadata = {}
        return {}, metadata

    def succeeded(self, task):
        """
        Called when a task has completed with a status indicating success.
        Subclasses may override this to display a custom message to the user.

        :param task: full task report for the task being displayed
        :type  task: pulp.bindings.responses.Task
        """
        # Check for any errors in the details block of the task
        if task.result and task.result.get('details') \
                and task.result.get('details').get('errors'):

            self.prompt.render_failure_message(_('Task Failed'))
            for error in task.result.get('details').get('errors'):
                self.prompt.render_failure_message(error)
        else:
            super(_CreatePackageCommand, self).succeeded(task)


class CreateDebCommand(_CreatePackageCommand):
    TYPE_ID = TYPE_ID_DEB
    NAME = NAME_DEB
    DESCRIPTION = DESC_DEB
    SUFFIX = SUFFIX_DEB
