# coding=utf-8
"""Constants for Pulp Deb plugin tests."""


def _clean_dict(d):
    return {k: v for k, v in d.items() if v != 0}


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

DEB_FIXTURE_DISTRIBUTIONS = "ragnarok nosuite"
DEB_FIXTURE_SINGLE_DIST = "ragnarok"
DEB_FIXTURE_ALT_SINGLE_DIST = "ginnungagap"
DEB_FIXTURE_MULTI_DIST = "ragnarok ginnungagap"
DEB_FIXTURE_COMPONENT = "asgard"
DEB_FIXTURE_COMPONENT_UPDATE = "jotunheimr"
DEB_FIXTURE_ARCH = "ppc64"
DEB_FIXTURE_ARCH_UPDATE = "armeb"
DEB_FIXTURE_STANDARD_REPOSITORY_NAME = "/debian/"
DEB_FIXTURE_UPDATE_REPOSITORY_NAME = "/debian-update/"
DEB_FIXTURE_INVALID_REPOSITORY_NAME = "/debian-invalid/"
DEB_FIXTURE_FLAT_REPOSITORY_NAME = "/debian-flat/"
DEB_FIXTURE_COMPLEX_REPOSITORY_NAME = "/debian-complex-dists"
DEB_FIXTURE_MISSING_ARCHITECTURE_REPOSITORY_NAME = "/debian-missing-architecture/"

# Publication Parameters
DEB_PARAMS_PUB_SIMPLE = {"simple": True}
DEB_PARAMS_PUB_STRUCTURED = {"structured": True}
DEB_PARAMS_PUB_SIMPLE_AND_STRUCTURED = {"simple": True, "structured": True}
DEB_PARAMS_PUB_ALL = {"simple": True, "structured": True, "signing_service": ""}

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

DEB_REPORT_CODE_SKIP_RELEASE = "sync.release_file.was_skipped"
DEB_REPORT_CODE_SKIP_PACKAGE = "sync.package_index.was_skipped"

DEB_PACKAGE_RELPATH = "frigg_1.0_ppc64.deb"
DEB_GENERIC_CONTENT_RELPATH = "dists/ragnarok/asgard/binary-armeb/Release"

DEB_PUBLISH_COMPLEX_UBUNTU_BACKPORTS = {
    "distribution": "ragnarok-backports",
    "codename": "ragnarok",
    "suite": "ragnarok-backports",
    "components": ["asgard", "jotunheimr"],
    "release_file_folder": "dists/ragnarok-backports/",
    "package_index_paths": [
        "dists/ragnarok-backports/asgard/binary-ppc64/Packages",
        "dists/ragnarok-backports/asgard/binary-armeb/Packages",
        "dists/ragnarok-backports/jotunheimr/binary-ppc64/Packages",
        "dists/ragnarok-backports/jotunheimr/binary-armeb/Packages",
    ],
}

DEB_PUBLISH_COMPLEX_DEBIAN_SECURITY = {
    "distribution": "ragnarok/updates",
    "codename": "ragnarok",
    "suite": "stable",
    "components": ["updates/asgard", "updates/jotunheimr"],
    "release_file_folder": "dists/ragnarok/updates/",
    "package_index_paths": [
        "dists/ragnarok/updates/asgard/binary-ppc64/Packages",
        "dists/ragnarok/updates/asgard/binary-armeb/Packages",
        "dists/ragnarok/updates/jotunheimr/binary-ppc64/Packages",
        "dists/ragnarok/updates/jotunheimr/binary-armeb/Packages",
    ],
}

DEB_PUBLISH_FLAT_STRUCTURED = {
    "distribution": "/",
    "codename": "ragnarok",
    "suite": "mythology",
    "components": ["flat-repo-component"],
    "release_file_folder_sync": "",
    "release_file_folder_dist": "dists/flat-repo/",
    "package_index_paths_sync": ["Packages"],
    "package_index_paths_dist": ["dists/flat-repo/flat-repo-component/binary-ppc64/Packages"],
}

DEB_PUBLISH_FLAT_SIMPLE = {
    "distribution": "/",
    "codename": "ragnarok",
    "suite": "mythology",
    "components": ["flat-repo-component"],
    "release_file_folder_sync": "",
    "release_file_folder_dist": "dists/default/",
    "package_index_paths_sync": ["Packages"],
    "package_index_paths_dist": ["dists/default/all/binary-ppc64/Packages"],
}

DEB_PUBLISH_FLAT_VERBATIM = {
    "distribution": "/",
    "codename": "ragnarok",
    "suite": "mythology",
    "components": ["flat-repo-component"],
    "release_file_folder_sync": "",
    "release_file_folder_dist": "/",
    "package_index_paths_sync": ["Packages"],
    "package_index_paths_dist": ["Packages"],
}

DEB_PUBLISH_FLAT_NESTED_STRUCTURED = {
    "distribution": "nest/fjalar/",
    "codename": "ragnarok",
    "suite": "mythology",
    "components": ["flat-repo-component"],
    "release_file_folder_sync": "nest/fjalar/",
    "release_file_folder_dist": "dists/nest/fjalar",
    "package_index_paths_sync": ["nest/fjalar/Packages"],
    "package_index_paths_dist": ["dists/nest/fjalar/flat-repo-component/binary-ppc64/Packages"],
}

DEB_PUBLISH_FLAT_NESTED_SIMPLE = {
    "distribution": "nest/fjalar/",
    "codename": "ragnarok",
    "suite": "mythology",
    "components": ["flat-repo-component"],
    "release_file_folder_sync": "nest/fjalar/",
    "release_file_folder_dist": "dists/default/",
    "package_index_paths_sync": ["nest/fjalar/Packages"],
    "package_index_paths_dist": ["dists/default/all/binary-ppc64/Packages"],
}

DEB_PUBLISH_FLAT_NESTED_VERBATIM = {
    "distribution": "nest/fjalar/",
    "codename": "ragnarok",
    "suite": "mythology",
    "components": ["flat-repo-component"],
    "release_file_folder_sync": "nest/fjalar/",
    "release_file_folder_dist": "nest/fjalar/",
    "package_index_paths_sync": ["nest/fjalar/Packages"],
    "package_index_paths_dist": ["nest/fjalar/Packages"],
}

DEB_PUBLISH_MISSING_ARCHITECTURE = {
    "distribution": "ragnarok",
    "codename": "ragnarok",
    "suite": "mythology",
    "components": ["asgard", "jotunheimr"],
    "architecture_in_release": ["armeb", "ppc64"],
    "package_index_paths": [
        "dists/ragnarok/asgard/binary-ppc64",
        "dists/ragnarok/asgard/binary-armeb",
        "dists/ragnarok/jotunheimr/binary-ppc64",
        "dists/ragnarok/jotunheimr/binary-armeb",
    ],
}

DEB_PUBLISH_EMPTY_REPOSITORY = {
    "package_index_paths": [
        "dists/ginnungagap/asgard/binary-ppc64/Packages",
        "dists/ginnungagap/jotunheimr/binary-armeb/Packages",
        "dists/ginnungagap/asgard/binary-armeb/Packages",
        "dists/ginnungagap/jotunheimr/binary-ppc64/Packages",
        "dists/default/all/binary-all/Packages",
    ],
}

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
