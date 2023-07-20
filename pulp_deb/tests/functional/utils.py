# coding=utf-8
"""Utilities for tests for the deb plugin."""
from pathlib import Path
from uuid import uuid4

from pulp_deb.tests.functional.constants import DEB_FIXTURE_DISTRIBUTIONS


def gen_local_deb_remote(
    url,
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
        "url": url,
        "distributions": distributions,
        "sync_udebs": sync_udebs,
    }
    data.update(kwargs)
    return data


def get_local_package_absolute_path(package_name):
    """Looks up the local package of the given name under the relative path
    'data/packages/' and returns the absolute path.

    :param package_name: Name of the package to look up.
    :returns: The absolute path to the package.
    """
    p = Path(__file__).parent.absolute()
    return p.joinpath(f"data/packages/{package_name}")


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
