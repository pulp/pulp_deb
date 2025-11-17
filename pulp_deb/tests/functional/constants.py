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
DEB_SOURCE_PACKAGE_RELEASE_COMPONENT_NAME = "deb.source_package_release_component"
# Metadata files
DEB_RELEASE_FILE_NAME = "deb.release_file"
DEB_PACKAGE_INDEX_NAME = "deb.package_index"
DEB_INSTALLER_FILE_INDEX_NAME = "deb.installer_file_index"
DEB_SOURCE_INDEX_NAME = "deb.source_index"
# Content
DEB_PACKAGE_NAME = "deb.package"
DEB_INSTALLER_PACKAGE_NAME = "deb.installer_package"
DEB_GENERIC_CONTENT_NAME = "deb.generic"
DEB_SOURCE_PACKAGE_NAME = "deb.source_package"

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
DEB_FIXTURE_BASE = "/"
DEB_FIXTURE_COMPLEX_REPOSITORY_NAME = "/debian-complex-dists"
DEB_FIXTURE_MISSING_ARCHITECTURE_REPOSITORY_NAME = "/debian-missing-architecture/"
DEB_FIXTURE_ACS = "/debian-metadata-only/"

# Publication Parameters (structured is True by default)
DEB_PUBLICATION_ARGS_ONLY_SIMPLE = {"simple": True, "structured": False}
DEB_PUBLICATION_ARGS_ONLY_STRUCTURED = {"simple": False, "structured": True}
DEB_PUBLICATION_ARGS_SIMPLE_AND_STRUCTURED = {"simple": True, "structured": True}
DEB_PUBLICATION_ARGS_ALL = {"simple": True, "structured": True, "signing_service": ""}
DEB_PUBLICATION_ARGS_NESTED_ALPHABETICALLY = {
    "simple": False,
    "structured": True,
    "layout": "nested_alphabetically",
}
DEB_PUBLICATION_ARGS_NESTED_BY_DIGEST = {
    "simple": False,
    "structured": True,
    "layout": "nested_by_digest",
}
DEB_PUBLICATION_ARGS_NESTED_BY_BOTH = {
    "simple": False,
    "structured": True,
    "layout": "nested_by_both",
}

DEB_P2P_REMOTE_ARGS_SIMPLE = {"distributions": "default", "policy": "immediate"}
DEB_P2P_REMOTE_ARGS_STRUCTURED = {"distributions": "ragnarok nosuite", "policy": "immediate"}
DEB_P2P_REMOTE_ARGS_BOTH = {"distributions": "ragnarok nosuite default", "policy": "immediate"}
DEB_P2P_REMOTE_ARGS_VERBATIM = {"distributions": "ragnarok nosuite", "policy": "immediate"}
DEB_P2P_REMOTE_ARGS_FLAT = {"distributions": "flat-repo", "policy": "immediate"}

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
        DEB_SOURCE_INDEX_NAME: 0,
        DEB_SOURCE_PACKAGE_RELEASE_COMPONENT_NAME: 0,
        DEB_SOURCE_PACKAGE_NAME: 0,
    }
)

DEB_FIXTURE_ACS_SUMMARY = _clean_dict(
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
        DEB_SOURCE_INDEX_NAME: 0,
        DEB_SOURCE_PACKAGE_RELEASE_COMPONENT_NAME: 0,
        DEB_SOURCE_PACKAGE_NAME: 0,
    }
)

DEB_INSTALLER_FIXTURE_SUMMARY = _clean_dict(
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
        DEB_SOURCE_INDEX_NAME: 0,
        DEB_SOURCE_PACKAGE_RELEASE_COMPONENT_NAME: 0,
        DEB_SOURCE_PACKAGE_NAME: 0,
    }
)

DEB_INSTALLER_SOURCE_FIXTURE_SUMMARY = _clean_dict(
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
        DEB_SOURCE_INDEX_NAME: 2,
        DEB_SOURCE_PACKAGE_RELEASE_COMPONENT_NAME: 2,
        DEB_SOURCE_PACKAGE_NAME: 2,
    }
)

DEB_ADVANCED_COPY_FIXTURE_SUMMARY = _clean_dict(
    {
        DEB_RELEASE_NAME: 2,
        DEB_RELEASE_ARCHITECTURE_NAME: 2,
        DEB_RELEASE_COMPONENT_NAME: 2,
        DEB_RELEASE_FILE_NAME: 0,
        DEB_PACKAGE_INDEX_NAME: 0,
        DEB_PACKAGE_RELEASE_COMPONENT_NAME: 2,
        DEB_INSTALLER_FILE_INDEX_NAME: 0,
        DEB_PACKAGE_NAME: 1,
        DEB_INSTALLER_PACKAGE_NAME: 0,
        DEB_GENERIC_CONTENT_NAME: 0,
    }
)

DEB_FULL_ADVANCED_COPY_FIXTURE_SUMMARY = _clean_dict(
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

DEB_P2P_ONLY_SIMPLE = _clean_dict(
    {
        DEB_RELEASE_NAME: 1,
        DEB_RELEASE_ARCHITECTURE_NAME: 3,
        DEB_RELEASE_COMPONENT_NAME: 1,
        DEB_RELEASE_FILE_NAME: 1,
        DEB_PACKAGE_INDEX_NAME: 3,
        DEB_PACKAGE_RELEASE_COMPONENT_NAME: 4,
        DEB_INSTALLER_FILE_INDEX_NAME: 0,
        DEB_PACKAGE_NAME: 4,
        DEB_INSTALLER_PACKAGE_NAME: 0,
        DEB_GENERIC_CONTENT_NAME: 0,
    }
)

DEB_P2P_ONLY_STRUCTURED = _clean_dict(
    {
        DEB_RELEASE_NAME: 2,
        DEB_RELEASE_ARCHITECTURE_NAME: 5,
        DEB_RELEASE_COMPONENT_NAME: 3,
        DEB_RELEASE_FILE_NAME: 2,
        DEB_PACKAGE_INDEX_NAME: 8,
        DEB_PACKAGE_RELEASE_COMPONENT_NAME: 7,
        DEB_INSTALLER_FILE_INDEX_NAME: 0,
        DEB_PACKAGE_NAME: 4,
        DEB_INSTALLER_PACKAGE_NAME: 0,
        DEB_GENERIC_CONTENT_NAME: 0,
    }
)

DEB_P2P_SIMPLE_AND_STRUCTURED = _clean_dict(
    {
        DEB_RELEASE_NAME: 3,
        DEB_RELEASE_ARCHITECTURE_NAME: 8,
        DEB_RELEASE_COMPONENT_NAME: 4,
        DEB_RELEASE_FILE_NAME: 3,
        DEB_PACKAGE_INDEX_NAME: 11,
        DEB_PACKAGE_RELEASE_COMPONENT_NAME: 11,
        DEB_INSTALLER_FILE_INDEX_NAME: 0,
        DEB_PACKAGE_NAME: 8,
        DEB_INSTALLER_PACKAGE_NAME: 0,
        DEB_GENERIC_CONTENT_NAME: 0,
    }
)

DEB_P2P_SIMPLE_THEN_STRUCTURED = _clean_dict(
    {
        DEB_RELEASE_NAME: 2,
        DEB_RELEASE_ARCHITECTURE_NAME: 5,
        DEB_RELEASE_COMPONENT_NAME: 3,
        DEB_RELEASE_FILE_NAME: 2,
        DEB_PACKAGE_INDEX_NAME: 8,
        DEB_PACKAGE_RELEASE_COMPONENT_NAME: 7,
        DEB_INSTALLER_FILE_INDEX_NAME: 0,
        DEB_PACKAGE_NAME: 4,
        DEB_INSTALLER_PACKAGE_NAME: 0,
        DEB_GENERIC_CONTENT_NAME: 0,
    }
)

DEB_P2P_FLAT_STRUCTURED = _clean_dict(
    {
        DEB_RELEASE_NAME: 1,
        DEB_RELEASE_ARCHITECTURE_NAME: 2,
        DEB_RELEASE_COMPONENT_NAME: 1,
        DEB_RELEASE_FILE_NAME: 1,
        DEB_PACKAGE_INDEX_NAME: 2,
        DEB_PACKAGE_RELEASE_COMPONENT_NAME: 3,
        DEB_INSTALLER_FILE_INDEX_NAME: 0,
        DEB_PACKAGE_NAME: 3,
        DEB_INSTALLER_PACKAGE_NAME: 0,
        DEB_GENERIC_CONTENT_NAME: 0,
    }
)

DEB_PERF_DEBIAN_URL = "https://ftp.debian.org/debian/"
DEB_PERF_BOOKWORN = {
    "distributions": "bookworm",
    "components": "main",
    "architectures": "ppc64",
    "policy": "on_demand",
}

DEB_PERF_UBUNTU_URL = "http://archive.ubuntu.com/ubuntu/"
DEB_PERF_JAMMY = {
    "distributions": "jammy",
    "components": "main",
    "policy": "on_demand",
    "ignore_missing_package_indices": True,
}

DEB_FIXTURE_PACKAGE_COUNT = DEB_FIXTURE_SUMMARY.get(DEB_PACKAGE_NAME, 0)

DEB_REPORT_CODE_SKIP_COMPLETE = "sync.complete_skip.was_skipped"
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
    "distribution": "flat-repo",
    "codename": "ragnarok",
    "suite": "mythology",
    "components": ["flat-repo-component"],
    "release_file_folder_sync": "",
    "release_file_folder_dist": "dists/flat-repo/",
    "package_index_paths_sync": ["Packages"],
    "package_index_paths_dist": ["dists/flat-repo/flat-repo-component/binary-ppc64/Packages"],
}

DEB_PUBLISH_STANDARD = {
    "package_index_paths": [
        "dists/ragnarok/asgard/binary-ppc64/Packages",
        "dists/ragnarok/asgard/binary-armeb/Packages",
        "dists/ragnarok/jotunheimr/binary-ppc64/Packages",
        "dists/ragnarok/jotunheimr/binary-armeb/Packages",
    ]
}

DEB_PUBLISH_FLAT_SIMPLE = {
    "distribution": "flat-repo",
    "codename": "ragnarok",
    "suite": "mythology",
    "components": ["flat-repo-component"],
    "release_file_folder_sync": "",
    "release_file_folder_dist": "dists/default/",
    "package_index_paths_sync": ["Packages"],
    "package_index_paths_dist": ["dists/default/all/binary-ppc64/Packages"],
}

DEB_PUBLISH_FLAT_VERBATIM = {
    "distribution": "flat-repo",
    "codename": "ragnarok",
    "suite": "mythology",
    "components": ["flat-repo-component"],
    "release_file_folder_sync": "",
    "release_file_folder_dist": "/",
    "package_index_paths_sync": ["Packages"],
    "package_index_paths_dist": ["Packages"],
}

DEB_PUBLISH_FLAT_NESTED_STRUCTURED = {
    "distribution": "flat-repo",
    "codename": "ragnarok",
    "suite": "mythology",
    "components": ["flat-repo-component"],
    "release_file_folder_sync": "nest/fjalar/",
    "release_file_folder_dist": "dists/flat-repo",
    "package_index_paths_sync": ["nest/fjalar/Packages"],
    "package_index_paths_dist": ["dists/flat-repo/flat-repo-component/binary-ppc64/Packages"],
}

DEB_PUBLISH_FLAT_NESTED_SIMPLE = {
    "distribution": "flat-repo",
    "codename": "ragnarok",
    "suite": "mythology",
    "components": ["flat-repo-component"],
    "release_file_folder_sync": "nest/fjalar/",
    "release_file_folder_dist": "dists/default/",
    "package_index_paths_sync": ["nest/fjalar/Packages"],
    "package_index_paths_dist": ["dists/default/all/binary-ppc64/Packages"],
}

DEB_PUBLISH_FLAT_NESTED_VERBATIM = {
    "distribution": "flat-repo",
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

mQINBGVVa7sBEADPM841oGmIzx4pLgxURWA3o+45LO7i0jF42IWIPsHgb6wkzxi3
mGTpsQm0faHUtB+hKYb3BmSc+fH1JiO+eZPul7w/Ow1JEcTfIHrfWAhJdJpb8Ylm
y0dcfThOZ2Vq468tSYYvPd7KKXJgYjpDDCAtKdeGYABSn2rAJPFfizJE/a/lx/OZ
gsu7McfmG14w/hs5wDpC5T15O4PG/aDdpQczsl/jDbrzTPgd5AqCh83KjqGiUwYQ
QkeJjxIoMM2qg4gqLoYjZ65Y6/YEOwhbyH/88ZNxDsDfqQxJMCegSQo3wV+ODMmm
9xn/mjMU4brS88oZUzU2qRPf1w8wFXgJIhQqM0VrLfxs3VAmyhRKaX2aAzTvTwPi
ycdifSlrdnimI7UBkb8FNnQIGYsnX8psQDmUSgolAdc21IX7zQeRQYdAm3Rbu+3f
/AY4VoCVTCHmieCt988PxY2afVBScaQqfO8+HleNEq9AAjrmEVmEhVIVExZxYQO6
XulPa8TIJ3pwELwEPyq4SFkGCK6JdYBwxYfvjA6Ca8DM5G97/PE38iibcYQ9s6KT
os8zfL+v5NgCcBc7aIfLK0DDdfCus4DEORSugaoNdGt62NJp1D68Jw9w9hs+mGmw
corn7ELFmY+wvGz7Lru+dXmMxidN7LWbaZVmsy/ehYfIYm6w/NWrp2rizQARAQAB
tEBwdWxwLWZpeHR1cmUtc2lnbmluZy1rZXkgPGdlbmVyYXRlZC1zaWduaW5nLWtl
eUBwdWxwcHJvamVjdC5vcmc+iQJRBBMBCAA7FiEEDBqJTruGr64hhCTK3e8wGcLU
qM8FAmVVa7sCGwMFCwkIBwICIgIGFQoJCAsCBBYCAwECHgcCF4AACgkQ3e8wGcLU
qM8tVQ//SJr12jCyI3rsT8H4xsmuq8GQhjNqA8PG3ZTXeQ+nl+YEUEkVxpA+Q6Xk
zUVpwE3S5qKMFVzFV6Y1lgirhTgR/efrQsAmAhSvw1iwfFiSfCUU6XIA1Yu4A5iN
Q8XYzeJJ4ML3poYLq0BsZQFaGxuj3Cexc37e+fHEYIaGyPA1PpWlycSOSMUAe7Ba
c4oo5EBe5nHIL/SNif5aLWHTs7ejnQPFzxMnPcdz4c1ZpdeqFGCx2tqTnMw47Y5b
B/nFlcqaOX3mfHSHgY7LGIZyCDBpfM7q2vHUIhxsg4DbqlthwlvJrK40gmIFUZeq
3TcoCKV1txSFujmzLt7XKLVhDk6WFvcXUGh9kQ1cX/Hl0gz5FjZFKAMtyb7hqIhA
fBes2sojAm5BKK5No3e7BHE5Yvp4J1MX/xB+A/4yPbY3w6sDy0ggdKQdwoUlt0zc
mEJE4NVB7l+BR9HlJw+mX2eStGR24dR2qP8hD4bQnmsnLetOP6iEzj4EVxnlipyL
d96g3JU/UA7Q5wgGgxBbFjEz1PPW94Lqpb5SfujvEEw6rylufWCqAqe6lI0+W05u
iX/4BzVw9GxC6JTbkXt9r85LDWm7RFCNSXJTw5Bg0XMDAjs1J0M4rYKEKgohnwMC
Vh4v5YQPV1ReqSlb4dkEh9NNLvIz90prYqGD85Zb/ZxVubnL/XA=
=rGwu
-----END PGP PUBLIC KEY BLOCK-----"""

DEB_SIGNING_SCRIPT_STRING = r"""#!/bin/bash

set -e

export GNUPGHOME="HOMEDIRHERE"
RELEASE_FILE="$(/usr/bin/readlink -f $1)"
OUTPUT_DIR="${PULP_TEMP_WORKING_DIR}"
DETACHED_SIGNATURE_PATH="${OUTPUT_DIR}/Release.gpg"
INLINE_SIGNATURE_PATH="${OUTPUT_DIR}/InRelease"
GPG_KEY_ID="GPGKEYIDHERE"
COMMON_GPG_OPTS="--batch --armor --digest-algo SHA256"

# Create a detached signature
/usr/bin/gpg ${COMMON_GPG_OPTS} \
        --detach-sign \
        --output "${DETACHED_SIGNATURE_PATH}" \
        --local-user "${GPG_KEY_ID}" \
        "${RELEASE_FILE}"

# Create an inline signature
/usr/bin/gpg ${COMMON_GPG_OPTS} \
        --clearsign \
        --output "${INLINE_SIGNATURE_PATH}" \
        --local-user "${GPG_KEY_ID}" \
        "${RELEASE_FILE}"

echo { \
       \"signatures\": { \
         \"inline\": \"${INLINE_SIGNATURE_PATH}\", \
         \"detached\": \"${DETACHED_SIGNATURE_PATH}\" \
       } \
     }
"""

DEB_PACKAGE_SIGNING_SCRIPT_STRING = r"""#!/usr/bin/env bash
export GNUPGHOME="HOMEDIRHERE"
GPG_NAME="${PULP_SIGNING_KEY_FINGERPRINT}"

# Sign the package without using debsigs so this can run on rpm-based distros
tmpdir=$(mktemp -d)
ctrl=$(ar t "$1" | grep -m1 '^control\.tar\.')
data=$(ar t "$1" | grep -m1 '^data\.tar\.')
ar p "$1" debian-binary "$ctrl" "$data" | \
    gpg --openpgp --detach-sign --default-key "$GPG_NAME" > "$tmpdir/_gpgorigin"
ar r "$1" "$tmpdir/_gpgorigin" >/dev/null

# Check the exit status
STATUS=$?
if [[ ${STATUS} -eq 0 ]]; then
   echo {\"deb_package\": \"$1\"}
else
   exit ${STATUS}
fi
"""
