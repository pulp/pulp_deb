from types import SimpleNamespace

NO_MD5_WARNING_MESSAGE = (
    "Your pulp instance is configured to prohibit use of the MD5 checksum algorithm!\n"
    'Processing MD5 IN ADDITION to a secure hash like SHA-256 is "highly recommended".\n'
    "See https://docs.pulpproject.org/pulp_deb/workflows/checksums.html for more info.\n"
)

# Maps pulpcore names onto Debian metadata field names for all supported checksums:
CHECKSUM_TYPE_MAP = {
    "md5": "MD5sum",
    "sha1": "SHA1",
    "sha256": "SHA256",
    "sha512": "SHA512",
}

PACKAGE_UPLOAD_DEFAULT_DISTRIBUTION = "pulp"
PACKAGE_UPLOAD_DEFAULT_COMPONENT = "upload"

# Represents null values since nulls can't be used in unique indexes in postgres < 15
NULL_VALUE = "__!!!NULL VALUE!!!__"

LAYOUT_TYPES = SimpleNamespace(
    NESTED_ALPHABETICALLY="nested_alphabetically",  # default
    NESTED_BY_DIGEST="nested_by_digest",
    NESTED_BY_BOTH="nested_by_both",
)

LAYOUT_CHOICES = (
    (LAYOUT_TYPES.NESTED_ALPHABETICALLY, LAYOUT_TYPES.NESTED_ALPHABETICALLY),
    (LAYOUT_TYPES.NESTED_BY_DIGEST, LAYOUT_TYPES.NESTED_BY_DIGEST),
    (LAYOUT_TYPES.NESTED_BY_BOTH, LAYOUT_TYPES.NESTED_BY_BOTH),
)
