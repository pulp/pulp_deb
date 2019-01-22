# coding=utf-8
from urllib.parse import urljoin

from pulp_smash.constants import PULP_FIXTURES_BASE_URL
from pulp_smash.pulp3.constants import (
    BASE_PUBLISHER_PATH,
    BASE_REMOTE_PATH,
    CONTENT_PATH
)

DOWNLOAD_POLICIES = ['immediate', 'streamed', 'on_demand']

DEB_RELEASE_NAME = 'deb.release'
DEB_PACKAGE_INDEX_NAME = 'deb.package_index'
DEB_PACKAGE_NAME = 'deb.package'
DEB_GENERIC_CONTENT_NAME = 'deb.generic'

DEB_PACKAGE_PATH = urljoin(CONTENT_PATH, 'deb/packages/')
DEB_GENERIC_CONTENT_PATH = urljoin(CONTENT_PATH, 'deb/generic_contents/')

DEB_REMOTE_PATH = urljoin(BASE_REMOTE_PATH, 'deb/apt/')

DEB_PUBLISHER_PATH = urljoin(BASE_PUBLISHER_PATH, 'deb/default/')
DEB_VERBATIM_PUBLISHER_PATH = urljoin(BASE_PUBLISHER_PATH, 'deb/verbatim/')


DEB_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, 'debian/')
DEB_FIXTURE_RELEASE = 'ragnarok'

DEB_FIXTURE_RELEASE_COUNT = 1
DEB_FIXTURE_PACKAGE_INDEX_COUNT = 4
DEB_FIXTURE_PACKAGE_COUNT = 4
DEB_FIXTURE_GENERIC_CONTENT_COUNT = 0

DEB_FIXTURE_SUMMARY = {
    DEB_RELEASE_NAME: DEB_FIXTURE_RELEASE_COUNT,
    DEB_PACKAGE_INDEX_NAME: DEB_FIXTURE_PACKAGE_INDEX_COUNT,
    DEB_PACKAGE_NAME: DEB_FIXTURE_PACKAGE_COUNT,
#     DEB_GENERIC_CONTENT_NAME: DEB_FIXTURE_GENERIC_CONTENT_COUNT,
}

DEB_PACKAGE_RELPATH = 'pool/asgard/o/odin/odin_1.0_ppc64.deb'
DEB_PACKAGE_URL = urljoin(DEB_FIXTURE_URL, DEB_PACKAGE_RELPATH)
DEB_GENERIC_CONTENT_RELPATH = 'dists/ragnarok/asgard/binary-armeb/Release'
DEB_GENERIC_CONTENT_URL = urljoin(DEB_FIXTURE_URL, DEB_GENERIC_CONTENT_RELPATH)

# FIXME: replace this with your own fixture repository URL and metadata
DEB_LARGE_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, 'deb_large/')

# FIXME: replace this with the actual number of content units in your test fixture
DEB_LARGE_FIXTURE_COUNT = 25
