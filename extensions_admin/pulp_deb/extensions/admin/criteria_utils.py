"""
Methods for manipulating user input for criteria-based calls, such as the conversion
between sorting/comparing versions to use version_sort_index.
"""
from pulp.client.commands.criteria import CriteriaCommand

from pulp_rpm.common import version_utils


TRANSLATIONS = {
    'version': version_utils.VERSION_INDEX,
    'release': version_utils.RELEASE_INDEX,
}


def parse_key_value(args):
    """
    Meant to replace the CriteriaCommand _parse_key_value method. The docstring below was
    copied from that implementation.

    parses the raw user input, taken as a list of strings in the format
    'name=value', into a list of tuples in the format (name, value).

    :param args:    list of raw strings passed by the user on the command
                    line.
    :type  args:    list of basestrings

    :return:    new list of tuples in the format (name, value)
    """

    def translate(key_value_tuple):
        """
        :param key_value_tuple: single key/value tuple to translate
        :return: new key-value tuple to use
        """
        for orig_key, translated_key in TRANSLATIONS.items():
            if key_value_tuple[0] == orig_key:
                encoded_value = version_utils.encode(key_value_tuple[1])
                return translated_key, encoded_value

        return key_value_tuple

    base_parsed_list = CriteriaCommand._parse_key_value(args)
    translated_list = map(translate, base_parsed_list)

    return translated_list


def parse_sort(cls, sort_args):
    """
    Meant to replace the CriteriaCommand _parse_sort method. The docstring below was
    copied from that implementation.

    Parse the sort argument to a search command

    @param sort_args:   list of search arguments. Each is in the format
                        'field_name,direction' where direction is
                        'ascending' or 'descending'.
    @type  sort_args:   list

    @return:    list of sort arguments in the format expected by Criteria
    @rtype:     list
    """

    def translate(key_value_tuple):
        """
        :param key_value_tuple: single key/value tuple to translate
        :return: new key-value tuple to use
        """
        for orig_key, translated_key in TRANSLATIONS.items():
            if key_value_tuple[0] == orig_key:
                return translated_key, key_value_tuple[1]

        return key_value_tuple

    base_parsed_list = cls._parse_sort(sort_args)
    translated_list = map(translate, base_parsed_list)

    return translated_list
