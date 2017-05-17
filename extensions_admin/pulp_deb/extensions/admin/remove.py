from gettext import gettext as _

from pulp.client.commands.unit import UnitRemoveCommand

from pulp_deb.extensions.admin import units_display
from pulp_deb.common.constants import DISPLAY_UNITS_THRESHOLD
from pulp_deb.common.ids import TYPE_ID_DEB

DESC_DEB = _('remove deb units from a repository')

# -- commands -----------------------------------------------------------------


class BaseRemoveCommand(UnitRemoveCommand):
    """
    CLI Command for removing a unit from a repository
    """
    TYPE_ID = None
    DESCRIPTION = None
    NAME = None

    def __init__(self, context, unit_threshold=None):
        name = self.NAME or self.TYPE_ID
        if unit_threshold is None:
            unit_threshold = DISPLAY_UNITS_THRESHOLD
        super(BaseRemoveCommand, self).__init__(
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


class DebRemoveCommand(BaseRemoveCommand):
    TYPE_ID = TYPE_ID_DEB
    DESCRIPTION = DESC_DEB
