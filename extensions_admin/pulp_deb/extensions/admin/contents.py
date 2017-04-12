from gettext import gettext as _
import logging

from pulp.client.commands.criteria import DisplayUnitAssociationsCommand
from pulp_deb.extensions.admin import criteria_utils
from pulp_deb.common import ids

# -- constants ----------------------------------------------------------------

ALL_TYPES = sorted(ids.SUPPORTED_TYPES)

# List of all fields that the user can elect to display for each supported type
FIELDS_DEB = list(ids.UNIT_KEY_DEB) + sorted(ids.EXTRA_FIELDS_DEB)

# Used when generating the --fields help text so it can be customized by type
FIELDS_BY_TYPE = {
    ids.TYPE_ID_DEB: FIELDS_DEB,
}

# Ordering of metadata fields in each type. Keep in mind these are the display
# ordering within a unit; the order of the units themselves in the returned
# list from the server is dictated by the --ascending/--descending options.
ORDER_DEB = FIELDS_DEB

# Used to lookup the right order list based on type
ORDER_BY_TYPE = {
    ids.TYPE_ID_DEB: ORDER_DEB,
}

LOG = logging.getLogger(__name__)

# -- constants ----------------------------------------------------------------

DESC_DEB = _('search for Deb packages in a repository')

ASSOCIATION_METADATA_KEYWORD = 'metadata'

# -- commands -----------------------------------------------------------------


class BaseSearchCommand(DisplayUnitAssociationsCommand):
    """
    Root of all search commands in this module.
    This currently only does modifications
    """
    TYPE_ID = None
    NAME = None
    DESCRIPTION = None
    FILTER = None

    def __init__(self, context, *args, **kwargs):
        name = self.NAME or self.TYPE_ID
        super(BaseSearchCommand, self).__init__(self.package_search,
                                                name=name,
                                                description=self.DESCRIPTION,
                                                *args, **kwargs)
        self.context = context

    def run_search(self, type_ids, out_func=None, **kwargs):
        """
        This is a generic command that will perform a search for any type or
        types of content.

        :param type_ids:    list of type IDs that the command should operate on
        :type  type_ids:    list, tuple

        :param out_func:    optional callable to be used in place of
                            prompt.render_document. Must accept one dict and an
                            optional list of fields
        :type  out_func:    callable

        :param kwargs:  CLI options as input by the user and passed in by okaara
        :type  kwargs:  dict
        """
        out_func = out_func or self.context.prompt.render_document_list

        repo_id = kwargs.pop('repo-id')
        kwargs['type_ids'] = type_ids
        units = self.context.server.repo_unit.search(repo_id, **kwargs).response_body

        if not kwargs.get(DisplayUnitAssociationsCommand.ASSOCIATION_FLAG.keyword):
            units = [u[ASSOCIATION_METADATA_KEYWORD] for u in units]

        # Some items either override output function and are not included
        # in the FIELDS_BY_TYPE dictionary.  Check so tha they can
        # override the default behavior
        if len(type_ids) == 1 and FIELDS_BY_TYPE.get(type_ids[0]):
            out_func(units, FIELDS_BY_TYPE[type_ids[0]])
        else:
            out_func(units)

    @staticmethod
    def _parse_key_value(args):
        return criteria_utils.parse_key_value(args)

    @classmethod
    def _parse_sort(cls, sort_args):
        return criteria_utils.parse_sort(DisplayUnitAssociationsCommand,
                                         sort_args)

    def package_search(self, **kwargs):
        def out_func(document_list, display_filter=self.__class__.FIELDS):
            """Inner function to filter fields to display to the end user"""

            order = []

            # if the --details option has been specified, we need to manually
            # apply filtering to the unit data itself, since okaara's filtering
            # only operates at the top level of the document.
            if kwargs.get(self.ASSOCIATION_FLAG.keyword):
                # including most fields
                display_filter = ['updated', 'repo_id', 'created', 'unit_id',
                                  'metadata', 'unit_type_id', 'id']
                # display the unit info first
                order = [ASSOCIATION_METADATA_KEYWORD]

                # apply the same filtering that would normally be done by okaara
                for doc in document_list:
                    for key in doc[ASSOCIATION_METADATA_KEYWORD].keys():
                        if key not in self.FIELDS:
                            del doc[ASSOCIATION_METADATA_KEYWORD][key]

            self.context.prompt.render_document_list(
                document_list, filters=display_filter, order=order)

        self.run_search([self.TYPE_ID], out_func=out_func, **kwargs)


class SearchDebCommand(BaseSearchCommand):
    TYPE_ID = ids.TYPE_ID_DEB
    FIELDS = FIELDS_DEB
    DESCRIPTION = DESC_DEB
