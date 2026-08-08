from pulp_deb.app.package_metadata import (
    calculate_package_metadata_sha256,
    normalize_package_metadata,
)

BASE_METADATA = {
    "package": "example",
    "version": "1.0",
    "architecture": "amd64",
    "maintainer": "Example <example@example.com>",
    "description": "Example package",
}


def test_custom_field_order_does_not_change_metadata_digest():
    left = {
        **BASE_METADATA,
        "custom_fields": {"X-Foo": "one", "X-Bar": "two"},
    }
    right = {
        **BASE_METADATA,
        "custom_fields": {"X-Bar": "two", "X-Foo": "one"},
    }

    assert calculate_package_metadata_sha256(left) == calculate_package_metadata_sha256(right)


def test_custom_field_value_changes_metadata_digest():
    old = {
        **BASE_METADATA,
        "custom_fields": {"Phased-Update-Percentage": "20"},
    }
    new = {
        **BASE_METADATA,
        "custom_fields": {"Phased-Update-Percentage": "50"},
    }

    assert calculate_package_metadata_sha256(old) != calculate_package_metadata_sha256(new)


def test_custom_field_removal_changes_metadata_digest():
    old = {
        **BASE_METADATA,
        "custom_fields": {"Phased-Update-Percentage": "20"},
    }
    new = {**BASE_METADATA, "custom_fields": {}}

    assert calculate_package_metadata_sha256(old) != calculate_package_metadata_sha256(new)


def test_missing_and_ampty_custom_fields_are_equivalent():
    assert calculate_package_metadata_sha256(BASE_METADATA) == calculate_package_metadata_sha256(
        {**BASE_METADATA, "custom_fields": None}
    )


def test_installed_size_is_normalized_to_integer():
    with_string = {**BASE_METADATA, "installed_size": "123"}
    with_integer = {**BASE_METADATA, "installed_size": 123}

    assert calculate_package_metadata_sha256(with_string) == calculate_package_metadata_sha256(
        with_integer
    )
    assert normalize_package_metadata(with_string)["installed_size"] == 123
