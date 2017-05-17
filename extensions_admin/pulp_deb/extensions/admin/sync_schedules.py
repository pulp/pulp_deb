from gettext import gettext as _

from pulp.client.commands.schedule import (
    DeleteScheduleCommand, ListScheduleCommand, CreateScheduleCommand,
    UpdateScheduleCommand, NextRunCommand, RepoScheduleStrategy)
from pulp.client.commands.options import OPTION_REPO_ID

from pulp_deb.common.ids import TYPE_ID_IMPORTER


DESC_LIST = _('list scheduled sync operations')
DESC_CREATE = _('adds a new scheduled sync operation')
DESC_DELETE = _('delete a sync schedule')
DESC_UPDATE = _('updates an existing schedule')
DESC_NEXT_RUN = _('displays the next scheduled sync run for a repository')


class PkgListScheduleCommand(ListScheduleCommand):
    def __init__(self, context):
        strategy = RepoScheduleStrategy(context.server.repo_sync_schedules,
                                        TYPE_ID_IMPORTER)
        super(PkgListScheduleCommand, self).__init__(context, strategy,
                                                     description=DESC_LIST)
        self.add_option(OPTION_REPO_ID)


class PkgCreateScheduleCommand(CreateScheduleCommand):
    def __init__(self, context):
        strategy = RepoScheduleStrategy(context.server.repo_sync_schedules,
                                        TYPE_ID_IMPORTER)
        super(PkgCreateScheduleCommand, self).__init__(context, strategy,
                                                       description=DESC_CREATE)
        self.add_option(OPTION_REPO_ID)


class PkgDeleteScheduleCommand(DeleteScheduleCommand):
    def __init__(self, context):
        strategy = RepoScheduleStrategy(context.server.repo_sync_schedules,
                                        TYPE_ID_IMPORTER)
        super(PkgDeleteScheduleCommand, self).__init__(context, strategy,
                                                       description=DESC_DELETE)
        self.add_option(OPTION_REPO_ID)


class PkgUpdateScheduleCommand(UpdateScheduleCommand):
    def __init__(self, context):
        strategy = RepoScheduleStrategy(context.server.repo_sync_schedules,
                                        TYPE_ID_IMPORTER)
        super(PkgUpdateScheduleCommand, self).__init__(context, strategy,
                                                       description=DESC_UPDATE)
        self.add_option(OPTION_REPO_ID)


class PkgNextRunCommand(NextRunCommand):
    def __init__(self, context):
        strategy = RepoScheduleStrategy(context.server.repo_sync_schedules,
                                        TYPE_ID_IMPORTER)
        super(PkgNextRunCommand, self).__init__(context, strategy,
                                                description=DESC_NEXT_RUN)
        self.add_option(OPTION_REPO_ID)
