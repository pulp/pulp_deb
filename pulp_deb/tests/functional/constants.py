# coding=utf-8
from urllib.parse import urljoin

from pulp_smash.constants import PULP_FIXTURES_BASE_URL
from pulp_smash.pulp3.constants import (
    BASE_PUBLISHER_PATH,
    BASE_REMOTE_PATH,
    CONTENT_PATH
)

# FIXME: list any download policies supported by your plugin type here.
# If your plugin supports all download policies, you can import this
# from pulp_smash.pulp3.constants instead.
# DOWNLOAD_POLICIES = ['immediate', 'streamed', 'on_demand']
DOWNLOAD_POLICIES = ['immediate']

# FIXME: replace 'unit' with your own content type names, and duplicate as necessary for each type
DEB_CONTENT_NAME = 'unit'

# FIXME: replace 'unit' with your own content type names, and duplicate as necessary for each type
DEB_CONTENT_PATH = urljoin(CONTENT_PATH, 'deb/units/')

DEB_REMOTE_PATH = urljoin(BASE_REMOTE_PATH, 'deb/')

DEB_PUBLISHER_PATH = urljoin(BASE_PUBLISHER_PATH, 'deb/')


# FIXME: replace this with your own fixture repository URL and metadata
DEB_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, 'deb/')

# FIXME: replace this with the actual number of content units in your test fixture
DEB_FIXTURE_COUNT = 3

DEB_FIXTURE_SUMMARY = {
    DEB_CONTENT_NAME: DEB_FIXTURE_COUNT
}

# FIXME: replace this with the location of one specific content unit of your choosing
DEB_URL = urljoin(DEB_FIXTURE_URL, '')

# FIXME: replace this iwth your own fixture repository URL and metadata
DEB_LARGE_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, 'deb_large/')

# FIXME: replace this with the actual number of content units in your test fixture
DEB_LARGE_FIXTURE_COUNT = 25
