from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.commands.schedule import (
    DeleteScheduleCommand, ListScheduleCommand, CreateScheduleCommand,
    UpdateScheduleCommand, NextRunCommand)

from pulp_deb.extensions.admin import sync_schedules
from ...testbase import PulpClientTests


class StructureTests(PulpClientTests):
    def test_pkg_list_schedule_command(self):
        command = sync_schedules.PkgListScheduleCommand(self.context)

        self.assertTrue(isinstance(command, ListScheduleCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'list')
        self.assertEqual(command.description, sync_schedules.DESC_LIST)

    def test_pkg_create_schedule_command(self):
        command = sync_schedules.PkgCreateScheduleCommand(self.context)

        self.assertTrue(isinstance(command, CreateScheduleCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'create')
        self.assertEqual(command.description, sync_schedules.DESC_CREATE)

    def test_pkg_delete_schedule_command(self):
        command = sync_schedules.PkgDeleteScheduleCommand(self.context)

        self.assertTrue(isinstance(command, DeleteScheduleCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'delete')
        self.assertEqual(command.description, sync_schedules.DESC_DELETE)

    def test_pkg_update_schedule_command(self):
        command = sync_schedules.PkgUpdateScheduleCommand(self.context)

        self.assertTrue(isinstance(command, UpdateScheduleCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'update')
        self.assertEqual(command.description, sync_schedules.DESC_UPDATE)

    def test_pkg_next_run_command(self):
        command = sync_schedules.PkgNextRunCommand(self.context)

        self.assertTrue(isinstance(command, NextRunCommand))
        self.assertTrue(OPTION_REPO_ID in command.options)
        self.assertEqual(command.name, 'next')
        self.assertEqual(command.description, sync_schedules.DESC_NEXT_RUN)
