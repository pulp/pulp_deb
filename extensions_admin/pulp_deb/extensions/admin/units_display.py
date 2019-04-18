# -*- coding: utf-8 -*-

from pulp_deb.common.ids import (
    TYPE_ID_DEB,
    TYPE_ID_DEB_RELEASE,
    TYPE_ID_DEB_COMP,
)


def get_formatter_for_type(type_id):
    """
    Return a method that takes one argument (a unit) and formats a short string
    to be used as the output for the unit_remove command

    :param type_id: The type of the unit for which a formatter is needed
    :type type_id: str
    """
    type_formatters = {
        TYPE_ID_DEB: _details_package,
        TYPE_ID_DEB_RELEASE: _details_release,
        TYPE_ID_DEB_COMP: _details_component,
    }
    return type_formatters[type_id]


def _details_package(package):
    """
    A formatter that prints detailed package information.

    This is a detailed package formatter that can be used with different
    unit types.

    :param package: The package to have its formatting returned.
    :type package: dict
    :return: The display string of the package
    :rtype: str
    """
    return '%s-%s' % (package['name'], package['version'])


def _details_release(release):
    """
    A formatter that prints detailed release information.

    :param release: The release to have its formatting returned.
    :type release: dict
    :return: The display string of the release
    :rtype: str
    """
    return '%s' % (release['distribution'])


def _details_component(component):
    """
    A formatter that prints detailed component information.

    :param component: The component to have its formatting returned.
    :type component: dict
    :return: The display string of the component
    :rtype: str
    """
    return '%s' % (component['name'])
