# coding=utf-8
"""Constants for Pulp Deb plugin tests."""
from urllib.parse import urljoin

from pulp_smash import config
from pulp_smash.pulp3.constants import (
    # API_DOCS_PATH,
    BASE_CONTENT_PATH,
    BASE_DISTRIBUTION_PATH,
    BASE_PATH,
    BASE_PUBLICATION_PATH,
    BASE_REMOTE_PATH,
    BASE_REPO_PATH,
)


def _clean_dict(d):
    return {k: v for k, v in d.items() if v != 0}


PULP_FIXTURES_BASE_URL = config.get_config().get_fixtures_url()

DOWNLOAD_POLICIES = ["immediate", "streamed", "on_demand"]

# Metadata
DEB_RELEASE_NAME = "deb.release"
DEB_RELEASE_ARCHITECTURE_NAME = "deb.release_architecture"
DEB_RELEASE_COMPONENT_NAME = "deb.release_component"
DEB_PACKAGE_RELEASE_COMPONENT_NAME = "deb.package_release_component"
# Metadata files
DEB_RELEASE_FILE_NAME = "deb.release_file"
DEB_PACKAGE_INDEX_NAME = "deb.package_index"
DEB_INSTALLER_FILE_INDEX_NAME = "deb.installer_file_index"
# Content
DEB_PACKAGE_NAME = "deb.package"
DEB_INSTALLER_PACKAGE_NAME = "deb.installer_package"
DEB_GENERIC_CONTENT_NAME = "deb.generic"

DEB_PACKAGE_PATH = urljoin(BASE_CONTENT_PATH, "deb/packages/")
DEB_GENERIC_CONTENT_PATH = urljoin(BASE_CONTENT_PATH, "deb/generic_contents/")

DEB_DISTRIBUTION_PATH = urljoin(BASE_DISTRIBUTION_PATH, "deb/apt/")

DEB_REMOTE_PATH = urljoin(BASE_REMOTE_PATH, "deb/apt/")

DEB_REPO_PATH = urljoin(BASE_REPO_PATH, "deb/apt/")

DEB_PUBLICATION_PATH = urljoin(BASE_PUBLICATION_PATH, "deb/apt/")
VERBATIM_PUBLICATION_PATH = urljoin(BASE_PUBLICATION_PATH, "deb/verbatim/")

DEB_SINGLE_REQUEST_UPLOAD_PATH = urljoin(BASE_PATH, "deb/upload/")

DEB_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "debian/")
DEB_FIXTURE_RELEASE = "ragnarok"

DEB_FIXTURE_SUMMARY = _clean_dict(
    {
        DEB_RELEASE_NAME: 1,
        DEB_RELEASE_ARCHITECTURE_NAME: 2,
        DEB_RELEASE_COMPONENT_NAME: 2,
        DEB_RELEASE_FILE_NAME: 1,
        DEB_PACKAGE_INDEX_NAME: 4,
        DEB_PACKAGE_RELEASE_COMPONENT_NAME: 4,
        DEB_INSTALLER_FILE_INDEX_NAME: 0,
        DEB_PACKAGE_NAME: 4,
        DEB_INSTALLER_PACKAGE_NAME: 0,
        DEB_GENERIC_CONTENT_NAME: 0,
    }
)

DEB_FULL_FIXTURE_SUMMARY = _clean_dict(
    {
        DEB_RELEASE_NAME: 1,
        DEB_RELEASE_ARCHITECTURE_NAME: 2,
        DEB_RELEASE_COMPONENT_NAME: 2,
        DEB_RELEASE_FILE_NAME: 1,
        DEB_PACKAGE_INDEX_NAME: 6,
        DEB_PACKAGE_RELEASE_COMPONENT_NAME: 4,
        DEB_INSTALLER_FILE_INDEX_NAME: 0,
        DEB_PACKAGE_NAME: 4,
        DEB_INSTALLER_PACKAGE_NAME: 1,
        DEB_GENERIC_CONTENT_NAME: 0,
    }
)

DEB_FIXTURE_PACKAGE_COUNT = DEB_FIXTURE_SUMMARY.get(DEB_PACKAGE_NAME, 0)

DEB_PACKAGE_RELPATH = "pool/asgard/o/odin/odin_1.0_ppc64.deb"
DEB_PACKAGE_URL = urljoin(DEB_FIXTURE_URL, DEB_PACKAGE_RELPATH)
DEB_GENERIC_CONTENT_RELPATH = "dists/ragnarok/asgard/binary-armeb/Release"
DEB_GENERIC_CONTENT_URL = urljoin(DEB_FIXTURE_URL, DEB_GENERIC_CONTENT_RELPATH)

# FIXME: replace this with your own fixture repository URL and metadata
DEB_INVALID_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "deb_invalid/")

# FIXME: replace this with your own fixture repository URL and metadata
DEB_LARGE_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "deb_large/")

# FIXME: replace this with the actual number of content units in your test fixture
DEB_LARGE_FIXTURE_COUNT = 25
