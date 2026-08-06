from django.conf import settings


def normalize_metadata_field_names(field_names):
    return {field_name.lower() for field_name in (field_names or []) if field_name}


def excluded_package_metadata_fields(*field_name_lists):
    """
    Return globally and locally configured excluded package metadata fields.

    Field matching is case insensitive. Local lists are additive with the global
    ``EXCLUDED_PACKAGE_METADATA_FIELDS`` setting.
    """
    excluded = normalize_metadata_field_names(
        getattr(settings, "EXCLUDED_PACKAGE_METADATA_FIELDS", [])
    )
    for field_names in field_name_lists:
        excluded.update(normalize_metadata_field_names(field_names))
    return excluded
