# coding=utf-8
from urllib.parse import urljoin

from pulp_smash.constants import PULP_FIXTURES_BASE_URL
from pulp_smash.pulp3.constants import (
    BASE_PUBLISHER_PATH,
    BASE_REMOTE_PATH,
    CONTENT_PATH
)

# FIXME: replace 'unit' with your own content type names, and duplicate as necessary for each type
DEB_CONTENT_PATH = urljoin(CONTENT_PATH, 'deb/units/')

DEB_REMOTE_PATH = urljoin(BASE_REMOTE_PATH, 'deb/')

DEB_PUBLISHER_PATH = urljoin(BASE_PUBLISHER_PATH, 'deb/')


# FIXME: replace this with your own fixture repository URL and metadata
DEB_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, 'deb/')

# FIXME: replace this with the actual number of content units in your test fixture
DEB_FIXTURE_COUNT = 3

# FIXME: replace this with the location of one specific content unit of your choosing
DEB_URL = urljoin(DEB_FIXTURE_URL, '')

# FIXME: replace this iwth your own fixture repository URL and metadata
DEB_LARGE_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, 'deb_large/')

# FIXME: replace this with the actual number of content units in your test fixture
DEB_LARGE_FIXTURE_COUNT = 25
