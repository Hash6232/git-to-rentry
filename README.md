# rentry-publish

Automated publishing pipeline for Rentry pages.

## Quick Start

```bash
# Install
pip install pyyaml

# Publish a single page
python src/publish_rentry.py pages/example --edit-code <code>

# Or set as env var
export RENTRY_EDIT_CODE=<code>
python src/publish_rentry.py
```

## Structure

```
pages/<name>/
├── content.md       # Markdown body
└── metadata.yaml    # Routing + styling config
```

See `PLAN.md` for full architecture.
