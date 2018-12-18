# coding=utf-8
"""Utilities for tests for the deb plugin."""
from functools import partial
from unittest import SkipTest

from pulp_smash import api, selectors
from pulp_smash.pulp3.constants import (
    REPO_PATH
)
from pulp_smash.pulp3.utils import (
    gen_remote,
    gen_repo,
    gen_publisher,
    get_content,
    require_pulp_3,
    require_pulp_plugins,
    sync
)

from pulp_deb.tests.functional.constants import (
    DEB_GENERIC_CONTENT_NAME,
    DEB_GENERIC_CONTENT_PATH,
    DEB_FIXTURE_URL,
    DEB_FIXTURE_RELEASE,
    DEB_REMOTE_PATH,
)


def set_up_module():
    """Skip tests Pulp 3 isn't under test or if pulp_deb isn't installed."""
    require_pulp_3(SkipTest)
    require_pulp_plugins({'pulp_deb'}, SkipTest)


def gen_deb_remote(**kwargs):
    """Return a semi-random dict for use in creating a deb Remote.

    :param url: The URL of an external content source.
    """
    remote = gen_remote(DEB_FIXTURE_URL)
    deb_extra_fields = {
        'distributions': DEB_FIXTURE_RELEASE,
        **kwargs,
    }
    remote.update(**deb_extra_fields)
    return remote


def gen_deb_verbatim_publisher(**kwargs):
    """Return a semi-random dict for use in creating a verbatim Publisher.
    """
    publisher = gen_publisher()
    deb_extra_fields = {
        **kwargs,
    }
    publisher.update(**deb_extra_fields)
    return publisher


def gen_deb_publisher(**kwargs):
    """Return a semi-random dict for use in creating a Publisher.

    :param url: The URL of an external content source.
    """
    publisher = gen_publisher()
    deb_extra_fields = {
        'simple': True,
        **kwargs,
    }
    publisher.update(**deb_extra_fields)
    return publisher


def get_deb_content_unit_paths(repo):
    """Return the relative path of content units present in a deb repository.

    :param repo: A dict of information about the repository.
    :returns: A list with the paths of units present in a given repository.
    """
    # FIXME: The "relative_path" is actually a file path and name
    # It's just an example -- this needs to be replaced with an implementation that works
    # for repositories of this content type.
    return [
        content_unit['relative_path']
        for content_unit in get_content(repo)[DEB_GENERIC_CONTENT_NAME]
    ]


def gen_deb_content_attrs(artifact):
    """Generate a dict with content unit attributes.

    :param: artifact: A dict of info about the artifact.
    :returns: A semi-random dict for use in creating a content unit.
    """
    # FIXME: Add content specific metadata here.
    return {'artifact': artifact['_href']}


def populate_pulp(cfg, url=DEB_FIXTURE_URL):
    """Add deb contents to Pulp.

    :param pulp_smash.config.PulpSmashConfig: Information about a Pulp application.
    :param url: The deb repository URL. Defaults to
        :data:`pulp_smash.constants.DEB_FIXTURE_URL`
    :returns: A list of dicts, where each dict describes one file content in Pulp.
    """
    client = api.Client(cfg, api.json_handler)
    remote = {}
    repo = {}
    try:
        remote.update(client.post(DEB_REMOTE_PATH, gen_deb_remote(url)))
        repo.update(client.post(REPO_PATH, gen_repo()))
        sync(cfg, remote, repo)
    finally:
        if remote:
            client.delete(remote['_href'])
        if repo:
            client.delete(repo['_href'])
    return client.get(DEB_GENERIC_CONTENT_PATH)['results']


skip_if = partial(selectors.skip_if, exc=SkipTest)
"""The ``@skip_if`` decorator, customized for unittest.

:func:`pulp_smash.selectors.skip_if` is test runner agnostic. This function is
identical, except that ``exc`` has been set to ``unittest.SkipTest``.
"""
