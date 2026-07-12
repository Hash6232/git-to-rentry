#!/usr/bin/env python3
"""Validate page metadata against the Rentry schema.

Local debugging tool — checks metadata.yaml against the rules in
src/metadata_fields.yaml before you push.

Usage:
    # Single page
    python src/validate_metadata.py pages/my-page

    # All pages under pages/
    python src/validate_metadata.py

Exits non-zero on any validation failure.
"""

import os
import re
import sys

import yaml

SCHEMA_PATH = "src/metadata_fields.yaml"


def load_schema(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def discover_pages(base_dir: str = "pages") -> list[str]:
    if not os.path.isdir(base_dir):
        return []
    pages = []
    for entry in sorted(os.listdir(base_dir)):
        page_dir = os.path.join(base_dir, entry)
        if os.path.isdir(page_dir) and os.path.isfile(os.path.join(page_dir, "content.md")):
            pages.append(page_dir)
    return pages


def validate_css_size(value: str, rules: dict) -> str | None:
    """Validate a CSS size value against unit rules. Returns error string or None."""
    if not rules:
        return None

    # Parse value and unit
    m = re.match(r"([+-]?\d+(?:\.\d+)?)(\D+)?$", value.strip())
    if not m:
        return f'Invalid CSS size: "{value}"'
    num = float(m.group(1))
    unit = (m.group(2) or "no-unit").strip()

    unit_rules = rules.get(unit)
    if not unit_rules:
        allowed = ", ".join(rules.keys())
        return f'Invalid unit "{unit}" for value "{value}". Allowed: {allowed}'

    if num < unit_rules["min"] or num > unit_rules["max"]:
        return (
            f'Value "{value}" out of range ({unit_rules["min"]}-{unit_rules["max"]})'
        )

    # Check decimal places
    if "." in str(m.group(1)):
        decimal_places = len(str(m.group(1)).split(".")[1])
        max_decimals = unit_rules.get("decimals", 0)
        if decimal_places > max_decimals:
            return (
                f'Value "{value}" has {decimal_places} decimal places '
                f"(max {max_decimals})"
            )

    return None


def validate_color(value: str, validate_types: list[str], schema: dict) -> str | None:
    """Validate a color value against the required format."""
    v = value.strip()

    if "color_name" in validate_types:
        return None  # Can't validate arbitrary color names locally

    if "color_hex" in validate_types:
        if re.match(r"^#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3}(?:[0-9a-fA-F]{2})?)?$", v):
            return None

    if "color_rgba" in validate_types:
        m = re.match(
            r"^RGBA\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)$", v
        )
        if m:
            r, g, b, a = int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4))
            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255 and 0 <= a <= 1:
                return None
            return f'RGBA values out of range in "{v}"'

    return f'Invalid color: "{v}"'


def validate_url(value: str) -> str | None:
    if not re.match(r"^https?://", value.strip()):
        return f'Invalid URL: "{value}"'
    return None


def validate_bool(value: str) -> str | None:
    if value.strip().lower() not in ("true", "false"):
        return f'Invalid bool: "{value}" (must be true or false)'
    return None


def validate_field(
    field_name: str, values: list, schema: dict
) -> list[str]:
    """Validate one metadata field against its rules. Returns list of error strings."""
    errors = []
    field_rules = schema.get(field_name)
    if not field_rules:
        return [f"{field_name} : Unknown field"]

    max_values = field_rules.get("max_values", 99)
    if len(values) > max_values:
        errors.append(
            f"{field_name} : Too many values ({len(values)}, max {max_values})"
        )

    max_length = field_rules.get("max_length")
    if max_length:
        for v in values:
            if len(str(v)) > max_length:
                errors.append(
                    f"{field_name} : Value exceeds max length "
                    f"({len(v)} > {max_length}): {v}"
                )

    validate_all = field_rules.get("validate_all", [])
    validate_one = field_rules.get("validate_one", [])
    permitted_values = field_rules.get("permitted_values", [])
    units = field_rules.get("units", {})

    for v in values:
        sv = str(v).strip()

        if permitted_values and "whitelisted_string" in validate_all:
            if sv not in permitted_values:
                allowed = ", ".join(permitted_values)
                errors.append(
                    f"{field_name} : Invalid value \"{sv}\". Allowed: {allowed}"
                )

        if units:
            css_err = validate_css_size(sv, units)
            if css_err:
                errors.append(f"{field_name} : {css_err}")

        if validate_one:
            color_valid = validate_color(sv, validate_one, schema)
            if color_valid:
                if any(vt in validate_one for vt in ["color_name", "color_hex", "color_rgba"]):
                    errors.append(f"{field_name} : {color_valid}")

        if sv.startswith("http") and "url" in validate_one or "url" in validate_all:
            url_err = validate_url(sv)
            if url_err:
                errors.append(f"{field_name} : {url_err}")

        if "bool" in validate_all:
            bool_err = validate_bool(sv)
            if bool_err:
                errors.append(f"{field_name} : {bool_err}")

    return errors


def validate_page(page_dir: str) -> list[str]:
    """Validate a single page directory. Returns list of error strings."""
    errors = []

    meta_path = os.path.join(page_dir, "metadata.yaml")
    if not os.path.isfile(meta_path):
        return [f"Missing metadata.yaml"]
    if os.path.getsize(meta_path) == 0:
        return [f"metadata.yaml is empty"]

    try:
        meta = yaml.safe_load(open(meta_path)) or {}
    except yaml.YAMLError as e:
        return [f"metadata.yaml parse error: {e}"]

    if not isinstance(meta, dict):
        return [f"metadata.yaml must be a mapping, got {type(meta).__name__}"]

    slug = meta.get("slug")
    if not slug:
        errors.append("Missing required field: slug")
    elif not isinstance(slug, str):
        errors.append(f"slug must be a string, got {type(slug).__name__}")

    secret_ref = meta.get("secret_ref")
    if not secret_ref:
        errors.append("Missing required field: secret_ref")
    elif not isinstance(secret_ref, str):
        errors.append(f"secret_ref must be a string, got {type(secret_ref).__name__}")

    # Remove routing fields for metadata validation
    meta_copy = dict(meta)
    for routing_key in ("slug", "secret_ref", "theme"):
        meta_copy.pop(routing_key, None)

    if not meta_copy:
        if not errors:
            errors.append("No metadata fields to publish (only routing fields found)")
        return errors

    schema = load_schema(SCHEMA_PATH)

    for key, value in meta_copy.items():
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        errors.extend(validate_field(key, values, schema))

    return errors


def main():
    if len(sys.argv) > 1:
        page_dirs = [os.path.normpath(sys.argv[1])]
    else:
        page_dirs = discover_pages("pages")
        if not page_dirs:
            sys.stderr.write("No pages found under pages/.\n")
            sys.exit(1)

    total_errors = 0
    for page_dir in page_dirs:
        name = os.path.basename(page_dir)
        errors = validate_page(page_dir)
        if errors:
            total_errors += len(errors)
            for err in errors:
                sys.stderr.write(f"[{name}] {err}\n")

    if total_errors:
        sys.stderr.write(f"\n{total_errors} error(s) found\n")
        sys.exit(1)
    else:
        sys.stderr.write("All pages valid.\n")


if __name__ == "__main__":
    main()
