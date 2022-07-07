"""Tests that verify download of content served by Pulp."""
import pytest
import hashlib
from random import choice
from urllib.parse import urljoin

from pulp_smash import config, utils
from pulp_smash.pulp3.bindings import monitor_task
from pulp_smash.pulp3.utils import download_content_unit, gen_distribution, gen_repo

from pulp_deb.tests.functional.constants import DEB_FIXTURE_URL
from pulp_deb.tests.functional.utils import (
    gen_deb_remote,
    get_deb_content_unit_paths,
    get_deb_verbatim_content_unit_paths,
)

from pulpcore.client.pulp_deb import RepositorySyncURL, DebAptPublication, DebVerbatimPublication


@pytest.mark.parametrize(
    "publication_api, publication_class, get_content_unit_paths",
    [
        ("apt_publication_api", "deb_publication", get_deb_content_unit_paths),
        (
            "apt_verbatim_publication_api",
            "deb_verbatim_publication",
            get_deb_verbatim_content_unit_paths,
        ),
    ],
)
def test_download_content(
    gen_apt_distribution,
    gen_apt_publication,
    gen_repository_with_synced_remote,
    get_content_unit_paths,
    publication_api,
    publication_class,
    request,
):
    """Verify whether content served by pulp can be downloaded.

    The process of publishing content is more involved in Pulp 3 than it
    was under Pulp 2. Given a repository, the process is as follows:

    1. Create a publication from the repository. (The latest repository
       version is selected if no version is specified.) A publication is a
       repository version plus metadata.
    2. Create a distribution from the publication. The distribution defines
       at which URLs a publication is available, e.g.
       ``http://example.com/content/foo/`` and
       ``http://example.com/content/bar/``.

    Do the following:

    1. Create, populate, publish, and distribute a repository.
    2. Select a random content unit in the distribution. Download that
       content unit from Pulp, and verify that the content unit has the
       same checksum when fetched directly from Pulp=Fixtures.

    Both versions of a repository (normal and verbatim) will be tested in
    in this case.

    This test targets the following issues:

    * `Pulp #2895 <https://pulp.plan.io/issues/2895>`_
    * `Pulp Smash #872 <https://github.com/pulp/pulp-smash/issues/872>`_
    """
    publication_api = request.getfixturevalue(publication_api)
    publication_class = request.getfixturevalue(publication_class)
    repo = gen_repository_with_synced_remote()
    publication = gen_apt_publication(repo.pulp_href, publication_api, publication_class)
    distribution = gen_apt_distribution(publication.pulp_href)

    unit_paths = [choice(paths) for paths in get_content_unit_paths(repo).values() if paths]
    fixtures_hashes = [
        hashlib.sha256(utils.http_get(urljoin(DEB_FIXTURE_URL, unit_path[0]))).hexdigest()
        for unit_path in unit_paths
    ]

    pulp_hashes = []
    cfg = config.get_config()
    for unit_path in unit_paths:
        content = download_content_unit(cfg, distribution.to_dict(), unit_path[1])
        pulp_hashes.append(hashlib.sha256(content).hexdigest())

    assert fixtures_hashes == pulp_hashes


@pytest.fixture
def gen_apt_distribution(
    apt_distribution_api,
    gen_object_with_cleanup,
):
    """Fixture that generates a distribution from a given publication."""

    def _gen_apt_distribution(publication_href):
        body = gen_distribution()
        body["publication"] = publication_href
        distribution_response = gen_object_with_cleanup(apt_distribution_api, body)
        return apt_distribution_api.read(distribution_response.pulp_href)

    return _gen_apt_distribution


@pytest.fixture
def gen_apt_publication(gen_object_with_cleanup):
    """Fixture that generates a publication from a given repository."""

    def _gen_apt_publication(repo_href, publication_api, publication):
        publish_data = publication(repository=repo_href)
        return gen_object_with_cleanup(publication_api, publish_data)

    return _gen_apt_publication


@pytest.fixture
def gen_repository_with_synced_remote(
    apt_remote_api,
    apt_repository_api,
    gen_object_with_cleanup,
):
    """Fixture that generates a repository with a synced remote."""

    def _gen_repository_with_synced_remote():
        repo = gen_object_with_cleanup(apt_repository_api, gen_repo())
        remote = gen_object_with_cleanup(apt_remote_api, gen_deb_remote())
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = apt_repository_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)
        return apt_repository_api.read(repo.pulp_href)

    return _gen_repository_with_synced_remote


@pytest.fixture
def deb_publication():
    """Fixture for getting the `DebAptPublication` class."""

    def _deb_publication(*args, **kwargs):
        return DebAptPublication(structured=True, simple=True, *args, **kwargs)

    return _deb_publication


@pytest.fixture
def deb_verbatim_publication():
    """Fixture for getting the `DebVerbatimPublication` class."""

    def _deb_verbatim_publication(*args, **kwargs):
        return DebVerbatimPublication(*args, **kwargs)

    return _deb_verbatim_publication
