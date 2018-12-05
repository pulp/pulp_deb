# coding=utf-8
from urllib.parse import urljoin

from pulp_smash.constants import PULP_FIXTURES_BASE_URL
from pulp_smash.pulp3.constants import (
    BASE_PUBLISHER_PATH,
    BASE_REMOTE_PATH,
    CONTENT_PATH
)

# FIXME: replace 'unit' with your own content type names, and duplicate as necessary for each type
# DEB_CONTENT_PATH = urljoin(CONTENT_PATH, 'deb/content/')
DEB_PACKAGE_PATH = urljoin(CONTENT_PATH, 'deb/packages/')
DEB_GENERIC_CONTENT_PATH = urljoin(CONTENT_PATH, 'deb/generic_contents/')

DEB_REMOTE_PATH = urljoin(BASE_REMOTE_PATH, 'deb/')

DEB_PUBLISHER_PATH = urljoin(BASE_PUBLISHER_PATH, 'deb/')
DEB_VERBATIM_PUBLISHER_PATH = urljoin(BASE_PUBLISHER_PATH, 'deb_verbatim/')


DEB_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, 'debian/')
DEB_FIXTURE_RELEASE = 'ragnarok'

DEB_FIXTURE_COUNT = 13

DEB_PACKAGE_RELPATH = 'pool/asgard/o/odin/odin_1.0_ppc64.deb'
DEB_PACKAGE_URL = urljoin(DEB_FIXTURE_URL, DEB_PACKAGE_RELPATH)
DEB_GENERIC_CONTENT_RELPATH = 'dists/ragnarok/asgard/binary-armeb/Release'
DEB_GENERIC_CONTENT_URL = urljoin(DEB_FIXTURE_URL, DEB_GENERIC_CONTENT_RELPATH)

# FIXME: replace this with your own fixture repository URL and metadata
DEB_LARGE_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, 'deb_large/')

# FIXME: replace this with the actual number of content units in your test fixture
DEB_LARGE_FIXTURE_COUNT = 25
