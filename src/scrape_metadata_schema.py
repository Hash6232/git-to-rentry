#!/usr/bin/env python3
"""Fetch Rentry's metadata documentation and generate a structured YAML schema.

Usage:
    python src/scrape_metadata_schema.py > src/metadata_fields.yaml

The schema is generated from https://rentry.co/metadata-how.
Re-run whenever Rentry's metadata options change.
"""

import html
import re
import sys
import urllib.request
from datetime import date

import yaml

URL = "https://rentry.co/metadata-how"

PREFIXES = frozenset({
    "Default Value:", "Max Length:", "Max Values Accepted:",
    "Validate All:", "Validate One:", "Requires:", "Requires One:",
    "Units and Ranges For",     "Permitted whitelisted_string Values:",
    "Value Mapping:", "Value List:", "Reference:",
})


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


def strip_tags(text: str) -> str:
    result = re.sub(r"<[^>]+>", "", text)
    result = html.unescape(result)
    # Clean up leftover artifacts from escaped HTML in descriptions
    result = re.sub(r"<br\s*/?>", " ", result)
    result = re.sub(r"\s+", " ", result).strip()
    return result


def extract_balanced_div(html: str, start: int, tag_class: str) -> tuple[str, int]:
    """Extract a balanced <div class='...'> block starting at `start`.

    NOTE: This depth-tracker is brittle to void/self-closing tags inside
    divs. Verified zero such tags in the metadata-options section of
    rentry.co/metadata-how as of 2026-07-12. Re-check if the scraper
    ever misparses.

    Returns (content_between_tags, end_position_of_closing_tag).
    """
    depth = 0
    i = start
    in_tag = False
    while i < len(html):
        if html[i] == "<":
            # Check if it's a closing tag
            if html[i:i+2] == "</":
                end = html.find(">", i)
                tag_name = html[i+2:end].split()[0] if end > i+2 else ""
                if tag_name == "div":
                    depth -= 1
                    if depth == 0:
                        return (html[start:end+1], end + 1)
                i = end + 1
            elif html[i:i+6] == "<div " or html[i:i+7] == "<div\r\n" or html[i:i+7] == "<div\n":
                # Check class
                end_tag = html.find(">", i)
                if tag_class in html[i:end_tag+1]:
                    depth += 1
                    if depth == 1:
                        start = i
                i = end_tag + 1
            else:
                i = html.find(">", i) + 1
        else:
            i += 1
    return ("", len(html))


def parse_groups(html_content: str) -> list[dict]:
    groups = []
    meta_start = html_content.find('<h3>Metadata Options</h3>')
    if meta_start == -1:
        return groups
    meta_section = html_content[meta_start:]

    # Find each group container div
    pos = 0
    while True:
        container_start = meta_section.find('<div class="metadata-group-container">', pos)
        if container_start == -1:
            break
        # Find the group name
        h4_m = re.search(r'<h4>(GROUP:\s*(\w+))</h4>', meta_section[container_start:container_start+200])
        if not h4_m:
            break
        group_name = h4_m.group(2)
        # Find the matching closing div using depth tracking
        inner_start = container_start + len('<div class="metadata-group-container">')
        # Find the end by locating the next group-container or end of relevant section
        next_container = meta_section.find('<div class="metadata-group-container">', container_start + 1)
        if next_container == -1:
            # End of metadata options section
            next_section = meta_section.find('<h3>Glossary</h3>', container_start)
            if next_section == -1:
                group_end = len(meta_section)
            else:
                group_end = next_section
        else:
            group_end = next_container
        group_html = meta_section[inner_start:group_end]
        options = list(parse_options(group_html))
        groups.append({"name": group_name, "options": options})
        pos = group_end

    return groups


def parse_options(group_html: str):
    pos = 0
    while True:
        opt_start = group_html.find('<div class="metadata-option">', pos)
        if opt_start == -1:
            break
        inner_start = opt_start + len('<div class="metadata-option">')
        # Track depth to find matching </div>
        depth = 1
        i = inner_start
        opt_end = len(group_html)
        while i < len(group_html):
            if group_html[i:i+2] == "</":
                end = group_html.find(">", i)
                if end > i and "div" in group_html[i+2:end].split()[0:1]:
                    depth -= 1
                    if depth == 0:
                        opt_end = end + 1
                        break
                    i = end + 1
                else:
                    i = end + 1 if end > i else i + 1
            elif group_html[i:i+5] == "<div " or group_html[i:i+6] == "<div\r\n" or group_html[i:i+6] == "<div\n":
                end = group_html.find(">", i)
                if end > i:
                    depth += 1
                    i = end + 1
                else:
                    i += 1
            elif group_html[i] == "<":
                end = group_html.find(">", i)
                i = end + 1 if end > i else i + 1
            else:
                i += 1

        option_html = group_html[inner_start:opt_end - 1]  # exclude the closing </div>
        yield parse_option(option_html)
        pos = opt_end


def extract_text_list(html_fragment: str, list_tag: str) -> list[str]:
    """Extract text items from <ul><li> or <ol><li>."""
    items = []
    # Find all <ul> or <ol> blocks, then extract <li> items within each
    for block in re.finditer(rf'<{list_tag}[^>]*>(.*?)</{list_tag}>', html_fragment, re.DOTALL):
        for m in re.finditer(r'<li>(.*?)</li>', block.group(1), re.DOTALL):
            items.append(strip_tags(m.group(1)))
    return items


def parse_option(html_fragment: str) -> dict:
    h5_m = re.search(r'<h5>(.*?)</h5>', html_fragment)
    if not h5_m:
        raise RuntimeError("Missing <h5> field name in option block")
    field_name = strip_tags(h5_m.group(1))

    description = ""
    default = None
    max_length = None
    max_values = None
    validate_all = []
    validate_one = []
    requires = []
    requires_one = []
    units = {}
    permitted_values = []
    value_mapping = []
    value_list = []
    reference = None

    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html_fragment, re.DOTALL)
    i = 0
    while i < len(paragraphs):
        p = paragraphs[i]
        p_text = strip_tags(p)

        if not p_text:
            i += 1
            continue

        if p_text.startswith("Default Value:"):
            default = p_text.split("Default Value:", 1)[1].strip()
        elif p_text.startswith("Max Length:"):
            v = p_text.split("Max Length:", 1)[1].strip()
            max_length = int(v)
        elif p_text.startswith("Max Values Accepted:"):
            v = p_text.split("Max Values Accepted:", 1)[1].strip()
            max_values = int(v)
        elif p_text.startswith("Validate All:"):
            validate_all = [strip_tags(s) for s in re.findall(r'<span class="validation-item">(.*?)</span>', p)]
        elif p_text.startswith("Validate One:"):
            validate_one = [strip_tags(s) for s in re.findall(r'<span class="validation-item">(.*?)</span>', p)]
        elif p_text.startswith("Requires:"):
            requires = [strip_tags(s) for s in re.findall(r'<span class="require-item">(.*?)</span>', p)]
        elif p_text.startswith("Requires One:"):
            requires_one = [strip_tags(s) for s in re.findall(r'<span class="require-item">(.*?)</span>', p)]
        elif p_text.startswith("Units and Ranges For"):
            units = parse_units(html_fragment, p_text)
        elif "Permitted" in p_text and "Values" in p_text:
            permitted_values = extract_text_list(html_fragment, "ul")
        elif p_text.startswith("Value Mapping:"):
            value_mapping = extract_text_list(html_fragment, "ol")
        elif p_text.startswith("Value List:"):
            value_list = extract_text_list(html_fragment, "ol")
        elif p_text.startswith("Reference:"):
            href_m = re.search(r'<a href="(.*?)"', p)
            if href_m:
                reference = href_m.group(1)
        elif not any(p_text.startswith(prefix) for prefix in PREFIXES):
            if not description:
                description = p_text
            else:
                sys.stderr.write(f"  WARN: unmatched paragraph in {field_name}: {p_text[:80]}\n")
        i += 1

    result = {
        "group": None,
        "description": description,
        "default": default,
        "max_length": max_length,
        "max_values": max_values,
        "validate_all": validate_all,
        "validate_one": validate_one,
        "requires": requires,
        "requires_one": requires_one,
        "units": units,
        "permitted_values": permitted_values,
        "value_mapping": value_mapping,
        "value_list": value_list,
        "reference": reference,
    }

    # Remove None/empty defaults for cleaner output
    result = {k: v for k, v in result.items() if v is not None and v != [] and v != {}}

    return (field_name, result)


def parse_units(html_fragment: str, header_text: str) -> dict:
    """Parse units and ranges from the <ul> following a 'Units and Ranges For' header."""
    units = {}
    # Match the ul after the units header
    ul_match = re.search(
        r'<p>Units and Ranges For[^<]*</p>\s*<ul>(.*?)</ul>',
        html_fragment, re.DOTALL
    )
    if not ul_match:
        return units

    li_items = re.findall(r'<li>(.*?)</li>', ul_match.group(1), re.DOTALL)
    for li in li_items:
        li_text = strip_tags(li)
        m = re.match(r'(\S+)\s*:\s*([\d.]+)\s*-\s*([\d.]+)\s*\|\|\s*Decimals:\s*(\d+)', li_text)
        if m:
            unit_name = m.group(1)
            units[unit_name] = {
                "min": float(m.group(2)) if "." in m.group(2) else int(m.group(2)),
                "max": float(m.group(3)) if "." in m.group(3) else int(m.group(3)),
                "decimals": int(m.group(4)),
            }
    return units


def build_schema(groups: list[dict]) -> dict:
    schema = {}
    for group in groups:
        for field_name, option_data in group["options"]:
            option_data["group"] = group["name"]
            schema[field_name] = option_data
    return schema


def main():
    sys.stderr.write(f"Fetching {URL} ...\n")
    html_content = fetch_html(URL)
    sys.stderr.write("Parsing metadata options ...\n")
    groups = parse_groups(html_content)
    schema = build_schema(groups)

    sys.stderr.write(f"Found {len(schema)} fields across {len(groups)} groups\n")

    out = yaml.dump(schema, default_flow_style=False, sort_keys=False, allow_unicode=True, width=1000)
    sys.stdout.write(f"# Rentry Metadata Schema\n")
    sys.stdout.write(f"# Auto-generated by scrape_metadata_schema.py\n")
    sys.stdout.write(f"# Source: {URL}\n")
    sys.stdout.write(f"# Generated: {date.today()}\n")
    sys.stdout.write("#\n")
    sys.stdout.write("# 'default' values shown are Rentry's server-side defaults.\n")
    sys.stdout.write("# They are NOT injected by this system. Omitting a field from\n")
    sys.stdout.write("# metadata.yaml lets Rentry apply its own default automatically.\n")
    sys.stdout.write("---\n")
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
