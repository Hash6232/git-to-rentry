#!/usr/bin/env python3
"""Publish a page directory to Rentry.

Usage:
    # Single page
    python src/publish_rentry.py _example --edit-code <code>

    # Auto-scan all pages under pages/
    python src/publish_rentry.py --edit-code <code>

    # Dry-run (print payload, no POST)
    python src/publish_rentry.py _example --dry-run
"""

import argparse
import http.cookiejar
import os
import re
import sys
import urllib.parse
import urllib.request
import yaml

RENTRY_BASE = "https://rentry.co"


def load_yaml(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_text(path: str) -> str:
    with open(path) as f:
        return f.read()


def discover_pages(base_dir: str = "pages") -> list[str]:
    if not os.path.isdir(base_dir):
        return []
    pages = []
    for entry in sorted(os.listdir(base_dir)):
        page_dir = os.path.join(base_dir, entry)
        content_path = os.path.join(page_dir, "content.md")
        if os.path.isdir(page_dir) and os.path.isfile(content_path):
            pages.append(page_dir)
    return pages


def load_theme(name: str) -> dict:
    """Load a theme file from themes/<name>.yaml."""
    path = os.path.join("themes", f"{name}.yaml")
    if os.path.isfile(path):
        with open(path) as f:
            return yaml.safe_load(f) or {}
    sys.stderr.write(f"  WARN: theme '{name}' not found at {path}\n")
    return {}


def build_metadata_string(meta: dict) -> str:
    """Convert metadata dict to Rentry's KEY = value per line format."""
    lines = []
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key} = {' '.join(str(v) for v in value)}")
        else:
            lines.append(f"{key} = {value}")
    return "\n".join(lines)


def check_page_exists(slug: str) -> None:
    """Check if a Rentry page exists. Raises RuntimeError if not."""
    url = f"{RENTRY_BASE}/{slug}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            pass
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(
                f"Page https://rentry.co/{slug} does not exist.\n"
                f"  Create it manually at https://rentry.co/new with edit code,\n"
                f"  then add 'slug: {slug}' to metadata.yaml"
            )
        raise RuntimeError(f"HTTP {e.code} when checking page {url}")


def fetch_csrf(slug: str) -> tuple[str, http.cookiejar.CookieJar]:
    """GET the edit page and extract CSRF token + cookie jar.

    Returns (csrf_token, cookie_jar).
    """
    url = f"{RENTRY_BASE}/{slug}/edit"
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar)
    )
    req = urllib.request.Request(url)
    with opener.open(req) as resp:
        body = resp.read().decode()

    m = re.search(r'csrfmiddlewaretoken"\s*value="([^"]+)"', body)
    if not m:
        raise RuntimeError(f"Could not extract CSRF token from {url}")
    return m.group(1), jar


def publish(
    slug: str,
    edit_code: str,
    text: str,
    metadata: str = "",
    dry_run: bool = False,
) -> str:
    """Publish content to a Rentry page.

    Returns the response body.
    """
    if dry_run:
        sys.stderr.write(f"[DRY RUN] Would POST to {RENTRY_BASE}/{slug}/edit\n")
        sys.stderr.write(f"  edit_code={edit_code[:4]}...\n")
        sys.stderr.write(f"  text ({len(text)} chars)\n")
        if metadata:
            sys.stderr.write(f"  metadata ({len(metadata)} chars)\n")
        return ""

    csrf_token, jar = fetch_csrf(slug)

    url = f"{RENTRY_BASE}/{slug}/edit"
    data = urllib.parse.urlencode({
        "csrfmiddlewaretoken": csrf_token,
        "edit_code": edit_code,
        "text": text,
        "metadata": metadata,
    }).encode()

    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar)
    )
    req = urllib.request.Request(url, data=data, headers={
        "Referer": url,
        "Content-Type": "application/x-www-form-urlencoded",
    })

    try:
        with opener.open(req) as resp:
            body = resp.read().decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(
            f"HTTP {e.code}: {extract_generic_error(body) or e.reason}"
        )

    # Rentry rejects bad metadata by returning 200 with the edit form + errors
    form_errors = extract_form_errors(body)
    if form_errors:
        raise RuntimeError(
            f"Rentry rejected the submission:\n"
            + "\n".join(f"  {e}" for e in form_errors)
        )

    return body


def extract_generic_error(html: str) -> str | None:
    """Extract error message from Rentry's generic error page (CSRF, 404, etc)."""
    m = re.search(
        r'<span class="h5[^"]*font-weight-normal[^"]*m-0">([^<]+)',
        html
    )
    if m:
        return m.group(1).strip()
    return None


def extract_form_errors(html: str) -> list[str]:
    """Extract validation error messages from the edit form on failure."""
    errors = []
    for m in re.finditer(
        r'<div class="text-danger messages"[^>]*>(.*?)</div>',
        html, re.DOTALL
    ):
        text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if text:
            parts = re.split(r"(?<=[.!])(?=[A-Z])", text)
            for p in parts:
                p = p.strip()
                if p:
                    errors.append(p)
    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Publish a page directory to Rentry"
    )
    parser.add_argument(
        "page_dir", nargs="?", default=None,
        help="Page directory (auto-scans pages/*/ if omitted)"
    )
    parser.add_argument(
        "--slug", default=None,
        help="Rentry slug (overrides metadata.yaml)"
    )
    parser.add_argument(
        "--edit-code", default=None,
        help="Rentry edit code (overrides env var from secret_ref)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Build payload but don't POST"
    )
    args = parser.parse_args()

    # Discover pages
    if args.page_dir:
        page_dirs = [args.page_dir]
    else:
        page_dirs = discover_pages("pages")
        if not page_dirs:
            sys.stderr.write("No pages found. Run with a page directory or create pages/<name>/content.md\n")
            sys.exit(1)

    failures = 0

    for page_dir in page_dirs:
        dir_name = os.path.basename(os.path.normpath(page_dir))
        sys.stderr.write(f"\n=== {dir_name} ===\n")

        content_path = os.path.join(page_dir, "content.md")
        meta_path = os.path.join(page_dir, "metadata.yaml")

        if not os.path.isfile(content_path):
            sys.stderr.write(f"  SKIP: no content.md in {page_dir}\n")
            continue

        # Load content
        text = load_text(content_path)

        # Load metadata
        meta = {}
        if os.path.isfile(meta_path):
            meta = load_yaml(meta_path)

        # Extract routing fields (not sent to Rentry)
        slug = args.slug or meta.pop("slug", dir_name)
        secret_ref = meta.pop("secret_ref", slug.upper() + "_EDIT_CODE")
        theme_name = meta.pop("theme", None)

        # Merge theme defaults (page values take precedence)
        if theme_name:
            theme = load_theme(theme_name)
            merged = dict(theme)
            merged.update(meta)
            meta = merged

        # Resolve edit code
        edit_code = args.edit_code or os.environ.get(secret_ref)
        if not edit_code:
            sys.stderr.write(
                f"  FAIL: no edit code. Provide --edit-code or set env var ${secret_ref}\n"
            )
            failures += 1
            continue

        # Build metadata string
        metadata_str = build_metadata_string(meta)

        sys.stderr.write(f"  Slug: {slug}\n")
        sys.stderr.write(f"  Text: {len(text)} chars\n")
        if metadata_str:
            sys.stderr.write(f"  Metadata: {len(metadata_str)} chars\n")

        try:
            check_page_exists(slug)
            publish(slug, edit_code, text, metadata_str, dry_run=args.dry_run)
            if not args.dry_run:
                sys.stderr.write(f"  OK: Published to https://rentry.co/{slug}\n")
            else:
                sys.stderr.write(f"  OK: Dry-run complete\n")
        except RuntimeError as e:
            msg = str(e)
            if "\n" in msg:
                sys.stderr.write(f"  FAIL:\n")
                for line in msg.split("\n"):
                    sys.stderr.write(f"    {line}\n")
            else:
                sys.stderr.write(f"  FAIL: {msg}\n")
            failures += 1

    if failures:
        sys.stderr.write(f"\n{failures} page(s) failed\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
