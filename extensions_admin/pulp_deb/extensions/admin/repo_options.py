"""
Contains option definitions for Deb repository configuration and update, pulled
out of the repo commands module itself to keep it from becoming unwieldy.
"""

from gettext import gettext as _

from okaara import parsers
from pulp.client.extensions.extensions import PulpCliOption, PulpCliOptionGroup

from pulp_deb.common import ids

# -- data ---------------------------------------------------------------------

# Used to validate user entered skip types
VALID_SKIP_TYPES = ids.SUPPORTED_TYPES


def parse_skip_types(t):
    """
    The user-entered value is comma separated and will be the full list of
    types to skip; there is no concept of a diff.

    :param t: user entered value or None
    """
    if t in (None, ''):
        # Returning t itself is important. If it's None, it's an unspecified parameter
        # and should be ignored. If it's an empty string, it's the unset convention,
        # which is translated into a removal later in the parsing.

        return t

    parsed = t.split(',')
    parsed = [p.strip() for p in parsed]

    unmatched = [p for p in parsed if p not in VALID_SKIP_TYPES]
    if len(unmatched) > 0:
        msg = _('Types must be a comma-separated list using only the follodebg values: %(t)s')  # noqa
        msg = msg % {'t': ', '.join(sorted(VALID_SKIP_TYPES))}
        raise ValueError(msg)

    return parsed

# group names
NAME_PUBLISHING = _('Publishing')
NAME_AUTH = _('Consumer Authentication')

ALL_GROUP_NAMES = (NAME_PUBLISHING, NAME_AUTH)

# synchronization options
d = _('comma-separated list of types to omit when synchronizing, if not '
      'specified all types will be synchronized; valid values are: %(t)s')
d = d % {'t': ', '.join(sorted(VALID_SKIP_TYPES))}
OPT_SKIP = PulpCliOption('--skip', d, required=False,
                         parse_func=parse_skip_types)

# publish options
d = _('if "true", on each successful sync the repository will automatically be '
      'published on the configured protocols; if "false" synchronized content '
      'will only be available after manually publishing the repository; '
      'defaults to "true"')
OPT_AUTO_PUBLISH = PulpCliOption('--auto-publish', d, required=False,
                                 parse_func=parsers.parse_boolean)

d = _(
    'relative path the repository will be served from. Only alphanumeric '
    'characters, forward slashes, underscores '
    'and dashes are allowed. It defaults to the relative path of the feed URL')
OPT_RELATIVE_URL = PulpCliOption('--relative-url', d, required=False)

d = _('if "true", the repository will be served over HTTP; defaults to false')
OPT_SERVE_HTTP = PulpCliOption('--serve-http', d, required=False,
                               parse_func=parsers.parse_boolean)

d = _('if "true", the repository will be served over HTTPS; defaults to true')
OPT_SERVE_HTTPS = PulpCliOption('--serve-https', d, required=False,
                                parse_func=parsers.parse_boolean)

d = _('if "true", the "default" release with component "all" will be published.')
OPT_PUBLISH_DEFAULT_RELEASE = PulpCliOption('--publish-default-release', d,
                                            required=False,
                                            parse_func=parsers.parse_boolean)


def add_distributor_config_to_command(command):
    """
    Adds the repository configuration related options to the given command,
    organizing them into the appropriate groups.

    :param command: command to add options to
    :type  command: pulp.clients.extensions.extensions.PulpCliCommand
    """

    publish_group = PulpCliOptionGroup(NAME_PUBLISHING)

    publish_group.add_option(OPT_RELATIVE_URL)
    publish_group.add_option(OPT_SERVE_HTTP)
    publish_group.add_option(OPT_SERVE_HTTPS)
    publish_group.add_option(OPT_PUBLISH_DEFAULT_RELEASE)

    # Order added indicates order in usage, so pay attention to this order
    # when dorking with it to make sure it makes sense
    command.add_option_group(publish_group)
