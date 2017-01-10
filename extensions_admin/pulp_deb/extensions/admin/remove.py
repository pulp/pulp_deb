# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _

from pulp.client.commands.unit import UnitRemoveCommand

from pulp_deb.extensions.admin import units_display, criteria_utils
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


class PackageRemoveCommand(BaseRemoveCommand):
    """
    Used to intercept the criteria and use sort indexes when necessary.
    """

    @staticmethod
    def _parse_key_value(args):
        return criteria_utils.parse_key_value(args)

    @classmethod
    def _parse_sort(cls, sort_args):
        return criteria_utils.parse_sort(BaseRemoveCommand, sort_args)


class DebRemoveCommand(PackageRemoveCommand):
    TYPE_ID = TYPE_ID_DEB
    DESCRIPTION = DESC_DEB
