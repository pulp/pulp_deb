import logging
import os
from debpkgr import aptrepo
from gettext import gettext as _

from pulp_deb.common.constants import PUBLISH_HTTP_KEYWORD, \
    PUBLISH_HTTPS_KEYWORD, PUBLISH_RELATIVE_URL_KEYWORD, \
    HTTP_PUBLISH_DIR_KEYWORD, HTTPS_PUBLISH_DIR_KEYWORD, \
    GPG_CMD, GPG_KEY_ID

_LOG = logging.getLogger(__name__)

REQUIRED_CONFIG_KEYS = (PUBLISH_RELATIVE_URL_KEYWORD, PUBLISH_HTTP_KEYWORD,
                        PUBLISH_HTTPS_KEYWORD)

OPTIONAL_CONFIG_KEYS = (HTTP_PUBLISH_DIR_KEYWORD, HTTPS_PUBLISH_DIR_KEYWORD,
                        GPG_CMD, GPG_KEY_ID)

ROOT_PUBLISH_DIR = '/var/lib/pulp/published/deb'
MASTER_PUBLISH_DIR = os.path.join(ROOT_PUBLISH_DIR, 'master')
HTTP_PUBLISH_DIR = os.path.join(ROOT_PUBLISH_DIR, 'http', 'repos')
HTTPS_PUBLISH_DIR = os.path.join(ROOT_PUBLISH_DIR, 'https', 'repos')


def validate_config(repo, config, config_conduit):
    """
    Validate the prospective configuration instance for the the given
    repository.

    :param repo: repository to validate the config for
    :type  repo: pulp.plugins.model.Repository
    :param config: configuration instance to validate
    :type  config: pulp.plugins.config.PluginCallConfiguration
    :param config_conduit: conduit providing access to relevant Pulp
    functionality
    :type  config_conduit: pulp.plugins.conduits.repo_config.RepoConfigConduit
    :return: tuple of (bool, str) stating that the configuration is valid
    or not and why
    :rtype:  tuple of (bool, str or None)
    """
    # squish it into a dictionary so we can manipulate it
    if not isinstance(config, dict):
        config = config.flatten()
    error_messages = []

    configured_keys = set(config)
    required_keys = set(REQUIRED_CONFIG_KEYS)
    supported_keys = set(REQUIRED_CONFIG_KEYS + OPTIONAL_CONFIG_KEYS)

    # check for any required options that are missing
    missing_keys = required_keys - configured_keys
    msg = _('Configuration key [%(k)s] is required, but was not provided')
    for key in sorted(missing_keys):
        error_messages.append(msg % {'k': key})

    # check for unsupported configuration options
    extraneous_keys = configured_keys - supported_keys
    msg = _('Configuration key [%(k)s] is not supported')
    for key in extraneous_keys:
        error_messages.append(msg % {'k': key})

    # check that http and https are not set to false simultaneously
    if (not config.get(PUBLISH_HTTP_KEYWORD) and not
            config.get(PUBLISH_HTTPS_KEYWORD)):
        msg = _('Settings serve via http and https are both set to false.'
                ' At least one option should be set to true.')
        error_messages.append(msg)
    # when adding validation methods, make sure to register them here
    # yes, the individual sections are in alphabetical oder
    configured_key_validation_methods = {
        # required options
        PUBLISH_HTTP_KEYWORD: _validate_http,
        PUBLISH_HTTPS_KEYWORD: _validate_https,
        PUBLISH_RELATIVE_URL_KEYWORD: _validate_relative_url,
        # optional options
        HTTP_PUBLISH_DIR_KEYWORD: _validate_http_publish_dir,
        HTTPS_PUBLISH_DIR_KEYWORD: _validate_https_publish_dir,
    }

    # iterate through the options that have validation methods, validate them
    for key, validation_method in configured_key_validation_methods.items():

        if key not in configured_keys:
            continue

        validation_method(config[key], error_messages)

    # check that the relative path does not conflict with any existing repos
    _check_for_relative_path_conflicts(repo, config, config_conduit,
                                       error_messages)

    try:
        get_gpg_sign_options(repo, config)
    except aptrepo.SignerError as e:
        error_messages.append(str(e))

    # if we have errors, log them, and return False with a concatenated
    # error message
    if error_messages:

        for msg in error_messages:
            _LOG.error(msg)

        return False, '\n'.join(error_messages)

    return True, None


def get_master_publish_dir(repo, distributor_type):
    """
    Get the master publishing directory for the given repository.

    :param repo: repository to get the master publishing directory for
    :type  repo: pulp.plugins.model.Repository
    :param distributor_type: The type id of distributor that is being published
    :type distributor_type: str
    :return: master publishing directory for the given repository
    :rtype:  str
    """

    return os.path.join(MASTER_PUBLISH_DIR, distributor_type, repo.id)


def get_http_publish_dir(config=None):
    """
    Get the configured HTTP publication directory.
    Returns the global default if not configured.

    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or None
    :return: the HTTP publication directory
    :rtype:  str
    """

    config = config or {}

    publish_dir = config.get(HTTP_PUBLISH_DIR_KEYWORD, HTTP_PUBLISH_DIR)

    if publish_dir != HTTP_PUBLISH_DIR:
        msg = _('Overridden configuration value for [{kw}] provided: %(v)s'.format(
            kw=HTTP_PUBLISH_DIR_KEYWORD))
        _LOG.debug(msg % {'v': publish_dir})

    return publish_dir


def get_https_publish_dir(config=None):
    """
    Get the configured HTTPS publication directory.
    Returns the global default if not configured.

    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or None
    :return: the HTTPS publication directory
    :rtype:  str
    """

    config = config or {}

    publish_dir = config.get(HTTPS_PUBLISH_DIR_KEYWORD, HTTPS_PUBLISH_DIR)

    if publish_dir != HTTPS_PUBLISH_DIR:
        msg = _('Overridden configuration value for [{kw}] provided: %(v)s'.format(
            kw=HTTPS_PUBLISH_DIR_KEYWORD))
        _LOG.debug(msg % {'v': publish_dir})

    return publish_dir


def get_repo_relative_path(repo, config=None):
    """
    Get the configured relative path for the given repository.
    :param repo: repository to get relative path for
    :type  repo: pulp.plugins.model.Repository
    :param config: configuration instance for the repository
    :type  config: pulp.plugins.config.PluginCallConfiguration or dict or None
    :return: relative path for the repository
    :rtype:  str
    """

    cfg = config or {}
    relative_path = cfg.get(PUBLISH_RELATIVE_URL_KEYWORD, repo.id) or repo.id

    relative_path.lstrip('/')
    return relative_path


def get_gpg_sign_options(repo=None, config=None):
    cfg = config or {}
    cmd = cfg.get(GPG_CMD)
    if not cmd:
        return None
    key_id = cfg.get(GPG_KEY_ID)
    repository_name = None if repo is None else repo.id
    return aptrepo.SignOptions(cmd, repository_name=repository_name,
                               key_id=key_id)


# -- required config validation -----------------------------------------------

def _validate_http(http, error_messages):
    _validate_boolean(HTTP_PUBLISH_DIR_KEYWORD, http, error_messages)


def _validate_https(https, error_messages):
    _validate_boolean(HTTPS_PUBLISH_DIR_KEYWORD, https, error_messages)


def _validate_relative_url(relative_url, error_messages):
    if relative_url is None:
        return

    if not isinstance(relative_url, basestring):
        msg = _('Configuration value for [{kw}] must be a string, but is a %(t)s'.format(
            kw=PUBLISH_RELATIVE_URL_KEYWORD))
        error_messages.append(msg % {'t': str(type(relative_url))})


# -- optional config validation -----------------------------------------------

def _validate_http_publish_dir(http_publish_dir, error_messages):
    _validate_usable_directory(HTTP_PUBLISH_DIR_KEYWORD, http_publish_dir,
                               error_messages)


def _validate_https_publish_dir(https_publish_dir, error_messages):
    _validate_usable_directory(HTTPS_PUBLISH_DIR_KEYWORD, https_publish_dir,
                               error_messages)


# -- generalized validation methods -------------------------------------------


def _validate_boolean(key, value, error_messages, none_ok=True):
    if isinstance(value, bool) or (none_ok and value is None):
        return

    msg = _('Configuration value for [%(k)s] should a boolean, but is a %(t)s')  # noqa
    error_messages.append(msg % {'k': key, 't': str(type(value))})


def _validate_usable_directory(key, path, error_messages):
    if not os.path.exists(path) or not os.path.isdir(path):
        msg = _('Configuration value for [%(k)s] must be an existing directory')  # noqa
        error_messages.append(msg % {'k': key})

    elif not os.access(path, os.R_OK | os.W_OK):
        msg = _('Configuration value for [%(k)s] must be a directory that is readable and writable')  # noqa
        error_messages.append(msg % {'k': key})


# -- check for conflicting relative paths -------------------------------------


def _check_for_relative_path_conflicts(repo, config, config_conduit,
                                       error_messages):
    relative_path = get_repo_relative_path(repo, config)
    conflicting_distributors = config_conduit.get_repo_distributors_by_relative_url(relative_path, repo.id)  # noqa
    # in all honesty, this loop should execute at most once
    # but it may be interesting/useful for erroneous situations
    for distributor in conflicting_distributors:
        conflicting_repo_id = distributor['repo_id']
        conflicting_relative_url = None
        if 'relative_url' in distributor['config']:
            conflicting_relative_url = distributor['config']['relative_url']
            msg = _('Relative URL [{relative_path}] for repository [{repo_id}] conflicts with '  # noqa
                    'existing relative URL [{conflict_url}] for repository [{conflict_repo}]')  # noqa
        else:
            msg = _('Relative URL [{relative_path}] for repository [{repo_id}] conflicts with '  # noqa
                    'repo id for existing repository [{conflict_repo}]')
        error_messages.append(msg.format(
            relative_path=relative_path,
            repo_id=repo.id,
            conflict_url=conflicting_relative_url,
            conflict_repo=conflicting_repo_id))
