from gettext import gettext as _

from pulp.client.commands.unit import UnitCopyCommand
from pulp.client.extensions.extensions import PulpCliFlag

from pulp_deb.extensions.admin import units_display
from pulp_deb.common.constants import (DISPLAY_UNITS_THRESHOLD,
                                       CONFIG_RECURSIVE)
from pulp_deb.common.ids import TYPE_ID_DEB


# -- constants ----------------------------------------------------------------

DESC_DEB = _('copy deb units from one repository to another')
DESC_ALL = _('copy all content units from one repository to another')

DESC_RECURSIVE = _(
    'if specified, any dependencies of units being copied that are in the source repo '  # noqa
    'will be copied as well')
FLAG_RECURSIVE = PulpCliFlag('--recursive', DESC_RECURSIVE)

# -- commands -----------------------------------------------------------------


class NonRecursiveCopyCommand(UnitCopyCommand):
    """
    Base class for all copy commands in this module that need not support
    specifying a recursive option to the plugin.
    """
    TYPE_ID = None
    DESCRIPTION = None
    NAME = None

    def __init__(self, context, unit_threshold=None):
        name = self.NAME or self.TYPE_ID
        if unit_threshold is None:
            unit_threshold = DISPLAY_UNITS_THRESHOLD
        super(NonRecursiveCopyCommand, self).__init__(
            context, name=name, description=self.DESCRIPTION,
            type_id=self.TYPE_ID)

        self.unit_threshold = unit_threshold

    def get_formatter_for_type(self, type_id):
        """
        Hook to get a the formatter for a given type

        :param type_id: the type id for which we need to get the formatter
        :type type_id: str
        """
        return units_display.get_formatter_for_type(type_id)


class RecursiveCopyCommand(NonRecursiveCopyCommand):
    """
    Base class for all copy commands in this module that should support
    specifying a recursive option to the plugin.
    """

    def __init__(self, context, unit_threshold=None):
        super(RecursiveCopyCommand, self).__init__(
            context,
            unit_threshold=unit_threshold)

        self.add_flag(FLAG_RECURSIVE)

    def generate_override_config(self, **kwargs):
        override_config = {}

        if kwargs[FLAG_RECURSIVE.keyword]:
            override_config[CONFIG_RECURSIVE] = True

        return override_config


class DebCopyCommand(RecursiveCopyCommand):
    TYPE_ID = TYPE_ID_DEB
    DESCRIPTION = DESC_DEB


class AllCopyCommand(NonRecursiveCopyCommand):
    TYPE_ID = None
    DESCRIPTION = DESC_ALL
    NAME = 'all'
