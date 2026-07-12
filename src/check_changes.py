#!/usr/bin/env python3
"""Check if local content differs from the published version on Rentry.

Usage:
    # Single page
    python src/check_changes.py pages/my-page

    # All pages under pages/
    python src/check_changes.py

No edit code needed — reads the public edit page.
Exits non-zero if any page has changes pending.
"""

import os
import sys
import urllib.request
import urllib.error
import re

RENTRY_BASE = "https://rentry.co"


def load_text(path: str) -> str:
    with open(path) as f:
        return f.read()


def load_yaml(path: str) -> dict:
    import yaml
    with open(path) as f:
        return yaml.safe_load(f) or {}


def normalize_md(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = text.rstrip("\n") + "\n"
    return text


def discover_pages(base_dir: str = "pages") -> list[str]:
    if not os.path.isdir(base_dir):
        return []
    pages = []
    for entry in sorted(os.listdir(base_dir)):
        page_dir = os.path.join(base_dir, entry)
        if os.path.isdir(page_dir) and os.path.isfile(os.path.join(page_dir, "content.md")):
            pages.append(page_dir)
    return pages


def fetch_live_md(slug: str) -> str:
    """Fetch the current published markdown from the /edit page."""
    url = f"{RENTRY_BASE}/{slug}/edit"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode()
    m = re.search(r'<textarea[^>]*>(.*?)</textarea>', body, re.DOTALL)
    if not m:
        raise RuntimeError(f"Could not extract textarea from {url}")
    return m.group(1)


def main():
    if len(sys.argv) > 1:
        page_dirs = [os.path.normpath(sys.argv[1])]
    else:
        page_dirs = discover_pages("pages")
        if not page_dirs:
            sys.stderr.write("No pages found under pages/.\n")
            sys.exit(1)

    any_changed = False

    for page_dir in page_dirs:
        name = os.path.basename(page_dir)
        content_path = os.path.join(page_dir, "content.md")
        meta_path = os.path.join(page_dir, "metadata.yaml")
        local = load_text(content_path)
        meta = load_yaml(meta_path) if os.path.isfile(meta_path) else {}
        slug = meta.get("slug", name)

        sys.stderr.write(f"\n=== {name} ===\n")
        sys.stderr.write(f"  Slug: {slug}\n")
        sys.stderr.write(f"  Local: {len(local)} chars\n")

        try:
            live = fetch_live_md(slug)
        except Exception as e:
            sys.stderr.write(f"  FAIL: {e}\n")
            any_changed = True
            continue

        sys.stderr.write(f"  Live:  {len(live)} chars\n")

        if normalize_md(local) == normalize_md(live):
            sys.stderr.write("  OK: No changes\n")
        else:
            sys.stderr.write("  CHANGED: Local differs from published version\n")
            any_changed = True

    if any_changed:
        sys.stderr.write("\nSome pages have pending changes\n")
        sys.exit(1)
    else:
        sys.stderr.write("\nAll pages up to date\n")


if __name__ == "__main__":
    main()
