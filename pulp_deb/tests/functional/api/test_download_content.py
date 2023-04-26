"""Tests that verify download of content served by Pulp."""
import pytest
import hashlib
from random import choice
from urllib.parse import urljoin

from pulp_smash import config, utils
from pulp_smash.pulp3.utils import download_content_unit
from pulp_deb.tests.functional.constants import DEB_FIXTURE_STANDARD_REPOSITORY_NAME

from pulp_deb.tests.functional.utils import (
    get_deb_content_unit_paths,
    get_deb_verbatim_content_unit_paths,
)


@pytest.mark.parallel
@pytest.mark.parametrize("is_verbatim", [False, True])
def test_download_content(
    deb_distribution_factory,
    deb_publication_factory,
    deb_remote_factory,
    deb_repository_factory,
    deb_verbatim_publication_factory,
    deb_get_repository_by_href,
    deb_sync_repository,
    deb_fixture_server,
    is_verbatim,
):
    """Verify whether content served by pulp can be downloaded.

    Both versions of a repository (normal and verbatim) will be tested in
    this case.
    """
    # Create repository, remote and sync them
    repo = deb_repository_factory()
    remote = deb_remote_factory(DEB_FIXTURE_STANDARD_REPOSITORY_NAME)
    deb_sync_repository(remote, repo)
    repo = deb_get_repository_by_href(repo.pulp_href)

    # Create a publication and a distribution
    publication = (
        deb_verbatim_publication_factory(repo)
        if is_verbatim
        else deb_publication_factory(repo, structured=True, simple=True)
    )
    distribution = deb_distribution_factory(publication)

    # Select a random content unit from the distribution and store its checksums
    unit_paths = get_random_content_unit_path(repo, is_verbatim)
    url = deb_fixture_server.make_url(DEB_FIXTURE_STANDARD_REPOSITORY_NAME)
    fixtures_hashes = [
        hashlib.sha256(utils.http_get(urljoin(url, unit_path[0]))).hexdigest()
        for unit_path in unit_paths
    ]

    # Verify that the content unit has the same checksums when fetched directly from Pulp-Fixtures
    pulp_hashes = []
    cfg = config.get_config()
    for unit_path in unit_paths:
        content = download_content_unit(cfg, distribution.to_dict(), unit_path[1])
        pulp_hashes.append(hashlib.sha256(content).hexdigest())
    assert fixtures_hashes == pulp_hashes


def get_random_content_unit_path(repo, is_verbatim):
    """Returns the path from a random content unit of a given (verbatim) repo."""
    if is_verbatim:
        return [
            choice(paths) for paths in get_deb_verbatim_content_unit_paths(repo).values() if paths
        ]
    else:
        return [choice(paths) for paths in get_deb_content_unit_paths(repo).values() if paths]
