#!/usr/bin/env python3
"""Validate the generated metadata schema against the live HTML source.

Cross-references every field in src/metadata_fields.yaml against
https://rentry.co/metadata-how and reports discrepancies.

Usage:
    python src/validate_schema.py
"""

import re
import sys
import urllib.request

import yaml

from scrape_metadata_schema import (
    fetch_html,
    parse_groups,
    build_schema,
    strip_tags,
)

SCHEMA_PATH = "src/metadata_fields.yaml"
URL = "https://rentry.co/metadata-how"


def load_schema(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def compare_values(key: str, field_name: str, schema_val, html_val) -> list[str]:
    """Compare two values and return a list of discrepancy messages."""
    issues = []
    if schema_val != html_val:
        # Special case: empty list vs None
        if not schema_val and not html_val:
            return issues
        # Order-independent comparison for lists
        if isinstance(schema_val, list) and isinstance(html_val, list):
            if sorted(schema_val) != sorted(html_val):
                issues.append(
                    f"  {field_name}.{key}: schema={schema_val!r}  html={html_val!r}"
                )
        elif isinstance(schema_val, dict) and isinstance(html_val, dict):
            # Recursive comparison for nested dicts (e.g. units)
            sub_issues = compare_dicts(
                f"{field_name}.{key}", schema_val, html_val
            )
            issues.extend(sub_issues)
        else:
            issues.append(
                f"  {field_name}.{key}: schema={schema_val!r}  html={html_val!r}"
            )
    return issues


def compare_dicts(prefix: str, schema: dict, html: dict) -> list[str]:
    """Recursively compare two dicts and return discrepancy messages."""
    issues = []
    all_keys = set(schema) | set(html)
    for k in sorted(all_keys):
        if k not in schema:
            issues.append(f"  {prefix}.{k}: missing in schema, html={html[k]!r}")
        elif k not in html:
            issues.append(f"  {prefix}.{k}: missing in html, schema={schema[k]!r}")
        else:
            sv, hv = schema[k], html[k]
            if sv != hv:
                if isinstance(sv, dict) and isinstance(hv, dict):
                    issues.extend(compare_dicts(f"{prefix}.{k}", sv, hv))
                else:
                    issues.append(f"  {prefix}.{k}: schema={sv!r}  html={hv!r}")
    return issues


def validate():
    sys.stderr.write(f"Fetching {URL} ...\n")
    html_content = fetch_html(URL)
    sys.stderr.write("Parsing HTML options ...\n")
    groups = parse_groups(html_content)
    html_schema = build_schema(groups)

    schema = load_schema(SCHEMA_PATH)

    issues = []
    all_fields = set(schema) | set(html_schema)

    for field_name in sorted(all_fields):
        if field_name not in schema:
            issues.append(f"MISSING IN SCHEMA: {field_name}")
            continue
        if field_name not in html_schema:
            issues.append(f"EXTRA IN SCHEMA: {field_name}")
            continue

        field_schema = schema[field_name]
        field_html = html_schema[field_name]

        KEYS = {
            "group", "description", "default", "max_length", "max_values",
            "validate_all", "validate_one", "requires", "requires_one",
            "units", "permitted_values", "value_mapping", "value_list",
            "reference",
        }

        for key in KEYS:
            sv = field_schema.get(key)
            hv = field_html.get(key)
            sub = compare_values(key, field_name, sv, hv)
            issues.extend(sub)

    if issues:
        sys.stderr.write(f"\nFound {len(issues)} issue(s):\n\n")
        for issue in issues:
            print(issue)
        sys.exit(1)
    else:
        sys.stderr.write(
            f"All {len(schema)} fields match the HTML source.\n"
        )


if __name__ == "__main__":
    validate()
