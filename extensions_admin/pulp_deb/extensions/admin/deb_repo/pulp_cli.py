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

import os

from pulp.client.commands.repo import cudl, sync_publish, upload
from pulp.client.commands.repo.query import RepoSearchCommand
from pulp.client.commands.repo.status import PublishStepStatusRenderer
from pulp.client.upload import manager as upload_lib

from pulp_deb.extensions.admin import (contents, copy_commands, remove,
                                       repo_create_update, repo_list, status,
                                       structure, sync_schedules)
from pulp_deb.common import constants, ids
from pulp_deb.extensions.admin.upload import package

UPLOAD_SUBDIR = 'deb'


def initialize(context):
    structure.ensure_repo_structure(context.cli)
    upload_manager = _upload_manager(context)

    repo_section = structure.repo_section(context.cli)
    repo_section.add_command(repo_create_update.PkgRepoCreateCommand(context))
    repo_section.add_command(repo_create_update.PkgRepoUpdateCommand(context))
    repo_section.add_command(cudl.DeleteRepositoryCommand(context))
    repo_section.add_command(repo_list.RepoListCommand(context))
    repo_section.add_command(RepoSearchCommand(context,
                                               constants.REPO_NOTE_PKG))

    copy_section = structure.repo_copy_section(context.cli)
    copy_section.add_command(copy_commands.DebCopyCommand(context))
    copy_section.add_command(copy_commands.AllCopyCommand(context))

    remove_section = structure.repo_remove_section(context.cli)
    remove_section.add_command(remove.DebRemoveCommand(context))

    contents_section = structure.repo_contents_section(context.cli)
    contents_section.add_command(contents.SearchDebCommand(context))

    uploads_section = structure.repo_uploads_section(context.cli)
    for cls_ in [package.CreateDebCommand,
                 upload.ResumeCommand, upload.CancelCommand,
                 upload.ListCommand]:
        uploads_section.add_command(cls_(context, upload_manager))

    sync_section = structure.repo_sync_section(context.cli)
    renderer = status.PackageStatusRenderer(context)
    sync_section.add_command(sync_publish.RunSyncRepositoryCommand(context,
                                                                   renderer))
    sync_section.add_command(sync_publish.SyncStatusCommand(context,
                                                            renderer))

    publish_section = structure.repo_publish_section(context.cli)
    renderer = PublishStepStatusRenderer(context)
    distributor_id = ids.TYPE_ID_DISTRIBUTOR
    publish_section.add_command(sync_publish.RunPublishRepositoryCommand(
        context, renderer, distributor_id))
    publish_section.add_command(sync_publish.PublishStatusCommand(
        context, renderer))

    sync_schedules_section = structure.repo_sync_schedules_section(
        context.cli)
    sync_schedules_section.add_command(
        sync_schedules.PkgCreateScheduleCommand(context))
    sync_schedules_section.add_command(
        sync_schedules.PkgUpdateScheduleCommand(context))
    sync_schedules_section.add_command(
        sync_schedules.PkgDeleteScheduleCommand(context))
    sync_schedules_section.add_command(
        sync_schedules.PkgListScheduleCommand(context))

    sync_schedules_section.add_command(
        sync_schedules.PkgNextRunCommand(context))


def _upload_manager(context):
    """
    Instantiates and configures the upload manager. The context is used to
    access any necessary configuration.

    :return: initialized and ready to run upload manager instance
    :rtype: UploadManager
    """
    upload_working_dir = os.path.join(
        context.config['filesystem']['upload_working_dir'],
        UPLOAD_SUBDIR)
    upload_working_dir = os.path.expanduser(upload_working_dir)
    chunk_size = int(context.config['server']['upload_chunk_size'])
    upload_manager = upload_lib.UploadManager(upload_working_dir,
                                              context.server, chunk_size)
    upload_manager.initialize()
    return upload_manager
