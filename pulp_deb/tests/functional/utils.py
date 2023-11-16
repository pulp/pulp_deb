# coding=utf-8
"""Utilities for tests for the deb plugin."""
from random import choice
from pathlib import Path
from uuid import uuid4

from pulp_deb.tests.functional.constants import (
    DEB_FIXTURE_DISTRIBUTIONS,
    DEB_SIGNING_KEY,
    DOWNLOAD_POLICIES,
)


def gen_deb_remote(
    url=None,
    distributions=DEB_FIXTURE_DISTRIBUTIONS,
    sync_udebs=False,
    gpgkey=None,
    **kwargs,
):
    """Return a semi-random dict for use of creating a local test deb Remote.

    :param url: The url of the fixture repository.
    :param distributions: Names of the distributions space separated.
    """
    if gpgkey:
        kwargs["gpgkey"] = gpgkey
    data = {
        "name": str(uuid4()),
        "url": "" if url is None else url,
        "distributions": distributions,
        "sync_udebs": sync_udebs,
    }
    data.update(kwargs)
    return data


def gen_deb_remote_verbose(url=None, remove_policy=False):
    """Return a semi-random dict for use in defining a remote.

    For most tests, it's desirable to create remotes with as few attributes
    as possible, so that the tests can specifically target and attempt to break
    specific features. This module specifically targets remotes, so it makes
    sense to provide as many attributes as possible.
    Note that 'username' and 'password' are write-only attributes.
    """
    data = gen_deb_remote(url)
    data.update(
        {
            "password": str(uuid4()),
            "username": str(uuid4()),
            "policy": choice(DOWNLOAD_POLICIES),
            "distributions": f"{str(uuid4())} {str(uuid4())}",
            "components": f"{str(uuid4())} {str(uuid4())}",
            "architectures": f"{str(uuid4())} {str(uuid4())}",
            "gpgkey": DEB_SIGNING_KEY,
        }
    )
    if url is None:
        del data["url"]
    if remove_policy:
        del data["policy"]
    return data


def get_local_package_absolute_path(package_name, relative_path="data/packages/"):
    """Looks up the local package of the given name under the relative path
    'data/packages/' and returns the absolute path.

    :param package_name: Name of the package to look up.
    :param relative_path: The relative path of the directory below pulp_deb/tests/functional/.
    :returns: The absolute path to the package.
    """
    p = Path(__file__).parent.absolute()
    return p.joinpath(relative_path).joinpath(package_name)


def gen_distribution(**kwargs):
    """Returns a semi-random dict for use in creating a Distribution."""
    data = {"base_path": str(uuid4()), "name": str(uuid4())}
    data.update(kwargs)
    return data


def gen_remote(url, **kwargs):
    """Return a semi-random dict for use in creating a Remote.

    :param url: The URL of an external content source.
    """
    data = {"name": str(uuid4()), "url": url}
    data.update(kwargs)
    return data


def gen_repo(**kwargs):
    """Return a semi-random dict for use in creating a Repository."""
    data = {"name": str(uuid4())}
    data.update(kwargs)
    return data


def get_counts_from_content_summary(content_summary):
    """Returns only the counts from a given content summary."""
    content = content_summary
    for key in content:
        content[key] = content[key]["count"]
    return content
