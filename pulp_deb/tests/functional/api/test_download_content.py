"""Tests that verify download of content served by Pulp."""

import os
import pytest
import hashlib
from random import choice
from urllib.parse import urljoin

from pulp_deb.tests.functional.constants import (
    DEB_FIXTURE_STANDARD_REPOSITORY_NAME,
    DEB_GENERIC_CONTENT_NAME,
    DEB_PACKAGE_NAME,
    DEB_PACKAGE_RELEASE_COMPONENT_NAME,
    DEB_RELEASE_COMPONENT_NAME,
    DEB_RELEASE_FILE_NAME,
)


@pytest.fixture
def deb_get_content_unit_paths(deb_get_content_types):
    def _deb_get_content_unit_paths(repo, version_href=None):
        """Return a relative path of content units present in a deb repository.

        :param repo: A dict of information about the repository.
        :param version_href: The repository version to read.
        :returns: A dict of list with the paths of units present in a given repository
            for different content types. Paths are given as pairs with the remote and the
            local version.
        """

        def _rel_path(package, component=""):
            sourcename = package.source or package.package
            if sourcename.startswith("lib"):
                prefix = sourcename[0:4]
            else:
                prefix = sourcename[0]
            return os.path.join(
                "pool",
                component,
                prefix,
                sourcename,
                f"{package.package}_{package.version}_{package.architecture}.deb",
            )

        package_content = deb_get_content_types(
            "apt_package_api", DEB_PACKAGE_NAME, repo, version_href
        )
        package_release_component_content = deb_get_content_types(
            "apt_package_release_components_api",
            DEB_PACKAGE_RELEASE_COMPONENT_NAME,
            repo,
            version_href,
        )
        release_component_content = deb_get_content_types(
            "apt_release_component_api", DEB_RELEASE_COMPONENT_NAME, repo, version_href
        )
        result = {
            DEB_PACKAGE_NAME: [
                (content.relative_path, _rel_path(content, "all")) for content in package_content
            ]
        }
        for prc in package_release_component_content:
            package = next(
                package for package in package_content if package.pulp_href == prc.package
            )
            release_component = next(
                rc for rc in release_component_content if rc.pulp_href == prc.release_component
            )
            result[DEB_PACKAGE_NAME].append(
                (package.relative_path, _rel_path(package, release_component.component))
            )
        return result

    return _deb_get_content_unit_paths


@pytest.fixture
def deb_get_verbatim_content_unit_paths(deb_get_content_types):
    def _deb_get_verbatim_content_unit_paths(repo, version_href=None):
        """Return the relative path of content units present in a deb repository.

        :param repo: A dict of information about the repository.
        :param verison_href: The repository version to read.
        :returns: A dict of list with the paths of units present in a given repository
            for different content types. Paths are given as pairs with the remote and the
            local version.
        """
        release_file_content = deb_get_content_types(
            "apt_release_file_api", DEB_RELEASE_FILE_NAME, repo, version_href
        )
        package_content = deb_get_content_types(
            "apt_package_api", DEB_PACKAGE_NAME, repo, version_href
        )
        generic_content = deb_get_content_types(
            "apt_generic_content_api", DEB_GENERIC_CONTENT_NAME, repo, version_href
        )
        return {
            DEB_RELEASE_FILE_NAME: [
                (content.relative_path, content.relative_path) for content in release_file_content
            ],
            DEB_PACKAGE_NAME: [
                (content.relative_path, content.relative_path) for content in package_content
            ],
            DEB_GENERIC_CONTENT_NAME: [
                (content.relative_path, content.relative_path) for content in generic_content
            ],
        }

    return _deb_get_verbatim_content_unit_paths


@pytest.fixture
def deb_get_random_content_unit_path(request):
    def _deb_get_random_content_unit_path(repo, is_verbatim=False):
        """Get paths from random content units in a given repository.

        :param repo: A dict of information about the repository.
        :param is_verbatim: (Optional) Whether the content is published verbatim or not.
        :returns: List of paths of content units.
        """
        get_content_unit_paths = (
            request.getfixturevalue("deb_get_verbatim_content_unit_paths")
            if is_verbatim
            else request.getfixturevalue("deb_get_content_unit_paths")
        )
        return [choice(paths) for paths in get_content_unit_paths(repo).values() if paths]

    return _deb_get_random_content_unit_path


@pytest.mark.parallel
@pytest.mark.parametrize("is_verbatim", [False, True])
def test_download_content(
    deb_init_and_sync,
    deb_distribution_factory,
    deb_publication_factory,
    deb_verbatim_publication_factory,
    deb_get_random_content_unit_path,
    deb_fixture_server,
    download_content_unit,
    http_get,
    is_verbatim,
):
    """Verify whether content served by pulp can be downloaded.

    Both versions of a repository (normal and verbatim) will be tested in
    this case.
    """
    # Create repository, remote and sync them
    repo, _ = deb_init_and_sync()

    # Create a publication and a distribution
    publication = (
        deb_verbatim_publication_factory(repo)
        if is_verbatim
        else deb_publication_factory(repo, structured=True, simple=True)
    )
    distribution = deb_distribution_factory(publication)

    # Select a random content unit from the distribution and store its checksums
    unit_paths = deb_get_random_content_unit_path(repo, is_verbatim)
    url = deb_fixture_server.make_url(DEB_FIXTURE_STANDARD_REPOSITORY_NAME)
    fixtures_hashes = [
        hashlib.sha256(http_get(urljoin(url, unit_path[0]))).hexdigest() for unit_path in unit_paths
    ]

    # Verify that the content unit has the same checksums when fetched directly from Pulp-Fixtures
    pulp_hashes = []
    for unit_path in unit_paths:
        content = download_content_unit(distribution.base_path, unit_path[1])
        pulp_hashes.append(hashlib.sha256(content).hexdigest())
    assert fixtures_hashes == pulp_hashes
