"""Helpers for deriving immutable package metadata identity."""

import hashlib
import json
from collections.abc import Mapping
from typing import Any

PACKAGE_METADATA_FIELDS = (
    "package",
    "source",
    "version",
    "architecture",
    "architecture_variant",
    "section",
    "priority",
    "origin",
    "tag",
    "bugs",
    "essential",
    "build_essential",
    "installed_size",
    "maintainer",
    "original_maintainer",
    "description",
    "description_md5",
    "homepage",
    "built_using",
    "auto_built_package",
    "multi_arch",
    "breaks",
    "conflicts",
    "depends",
    "recommends",
    "suggests",
    "enhances",
    "pre_depends",
    "provides",
    "replaces",
    "custom_fields",
)


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _normalize_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    return value


def normalize_package_metadata(data: Mapping[str, Any]) -> dict[str, Any]:
    normalized = {}
    for field_name in PACKAGE_METADATA_FIELDS:
        value = data.get(field_name)
        if field_name == "custom_fields":
            value = value or {}
        elif field_name == "installed_size" and value is not None:
            value = int(value)
        normalized[field_name] = _normalize_value(value)
    return normalized


def calculate_package_metadata_sha256(data: Mapping[str, Any]) -> str:
    payload = json.dumps(
        normalize_package_metadata(data),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
