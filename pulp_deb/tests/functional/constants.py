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
DEB_FIXTURE_DISTRIBUTIONS = "ragnarok nosuite"

DEB_FIXTURE_SUMMARY = _clean_dict(
    {
        DEB_RELEASE_NAME: 2,
        DEB_RELEASE_ARCHITECTURE_NAME: 3,
        DEB_RELEASE_COMPONENT_NAME: 3,
        DEB_RELEASE_FILE_NAME: 2,
        DEB_PACKAGE_INDEX_NAME: 5,
        DEB_PACKAGE_RELEASE_COMPONENT_NAME: 7,
        DEB_INSTALLER_FILE_INDEX_NAME: 0,
        DEB_PACKAGE_NAME: 4,
        DEB_INSTALLER_PACKAGE_NAME: 0,
        DEB_GENERIC_CONTENT_NAME: 0,
    }
)

DEB_FULL_FIXTURE_SUMMARY = _clean_dict(
    {
        DEB_RELEASE_NAME: 2,
        DEB_RELEASE_ARCHITECTURE_NAME: 3,
        DEB_RELEASE_COMPONENT_NAME: 3,
        DEB_RELEASE_FILE_NAME: 2,
        DEB_PACKAGE_INDEX_NAME: 7,
        DEB_PACKAGE_RELEASE_COMPONENT_NAME: 7,
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

DEB_INVALID_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "debian-invalid/")

DEB_COMPLEX_DISTS_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "debian-complex-dists/")

DEB_MISSING_ARCH_DISTS_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "debian-missing-architecture/")

# FIXME: replace this with your own fixture repository URL and metadata
DEB_LARGE_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "deb_large/")

# FIXME: replace this with the actual number of content units in your test fixture
DEB_LARGE_FIXTURE_COUNT = 25

DEB_SIGNING_KEY = """-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v2

mQENBFek0GkBCACwGSRiUSE3d+0vA7/X7xj+6u4y5Pg43G6AZIeUrNN4+Y7z2s/y
VWBWfjimJevQUBbOn5Otm/9wBNAcTKAMEqlVGmsRPKonPT3SHeX9dVo2LkbOZJDR
kdEu1TX6wiuuhZAsJoPM0cClF2IV9xSQN3o4xW8oo63/ZLRu3lCraia0sfob3jZi
cYUI9cC6OOLmH+1nmcCVo1qg3zSZg/gFyvscVMr1Dm5PfjyH/1SO4MgK6RqHkrxV
dhvwBPs1bO9dzjB7H1Lmyb2l0lFOrArqPW3jgcKV1+AmpJGshLyOQBmZ2rW7oGTG
il33iSSrZ4TKjj6y3392gxX3gs4bYvB8hjotABEBAAG0B1B1bHAgUUWJATcEEwEI
ACEFAlek0GkCGwMFCwkIBwIGFQgJCgsCBBYCAwECHgECF4AACgkQBaXm2iadnZhP
vAf9GG8foj1EaBTENXgH+7Zc1aKur7i738felcqhZhUlZBD8vyPrh0TPJ63uITXS
9RiE70/iwsDqKY8RiB8oMENI2CAEHXEelLC7Qx5f97WVaNmlydOQBxs4V09T8pDg
BK21D3/HLBL0QjW6uE7TAEGuiCd8A1ZKvjNyQhCtElDKjgOT2LtvlH6L3PZ+KWnA
l4n7wSADkgyU+n+jGorKH4yxxVHelnpNNas5AhI/cB73i9lhR8iQL6RDKgQuc0fy
wW4gsAoxjH2SeCJgxRIF2ezrCedS1chgnQAvItKmHsuLJHuWNT0QuG5nLzNVjjh1
L8YUJiVGxxqzEIQ/HrQdZBPlL7kBDQRXpNBpAQgAu9+1oHg1uhCQTwjMRNpPT6qr
z8gvVepfUK7UzHvtBjRMVcUmfHVOwURNpd6qPNu7tsGe/KuvrMFU9pwmq+zIytX4
vmY8BBtIIoHTeC3DtoWrpemXZht5jDL8kgygCNqGg9E6TvdqDZ6ItDOAP3wBkieR
LghwPG3KylQFudRJq5qbWpzrX2RRIVSSiLLl/zttiYKE1eCimUQ12nztey/eN+VV
u5U+y88xJr40vnPEkPKQmE713xuzIUAFXEx6FxDUMWNPUPPJtlfIe9QsjxNZ4R9w
s/arq5TILiiqmOHpnu8gcEjfDu8n10AKMUgdc2NocqmetyPnb8KZon1oX+IN0wAR
AQABiQEfBBgBCAAJBQJXpNBpAhsMAAoJEAWl5tomnZ2YP2MIAJtzsoRbzLtixNWP
PoYXPW5eUZ/R+9pV6agAZYwzTmuCNRzTV2vxgCGvnvzC0SZbvBKeVqONBuTariyo
aC4Y1pUj5xX6AOIt0gbyMsj+XcYz2SuRuB+fAW1avmBaBI7jlsqHkPGBqTdeVbJC
qKhCv0igH3jv/222eWEp5w7V7Xre1IyNCtyn8qeN9igH+5XyPmiV04PndmORusFq
CeEE45C7ahpX9VJ8fwZ+XJBRYxoaRJ1tpAVrNeJsXxiGxJGmuL86hdJN/1W1G8QT
gAMUtmcqiACuLWVpljMJKzuVaIqXq9nNMRTUzGFIG0dSmA6pNeym9RFPW2ro3G11
uUBsbCg=
=8Is3
-----END PGP PUBLIC KEY BLOCK-----"""
