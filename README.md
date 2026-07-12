# rentry-publish

Automated publishing pipeline for Rentry pages.
Push markdown to `main` — your Rentry page updates automatically.

---

## For CI Users

### 1. Add pages

Each directory under `pages/` becomes a separate Rentry page:

```
pages/
├── blog/
│   ├── content.md
│   └── metadata.yaml
├── about/
│   ├── content.md
│   └── metadata.yaml
└── links/
    ├── content.md
    └── metadata.yaml
```

`content.md` — your markdown:

```markdown
# My Page

Hello from the automated publishing pipeline!
```

`metadata.yaml` — routing and optional styling:

```yaml
slug: my-page
secret_ref: MY_PAGE_EDIT_CODE

PAGE_TITLE: "My Page"
ACCESS_RECOMMENDED_THEME:
  - dark
```

| Field | Required | What it is |
|---|---|---|
| `slug` | Yes | The Rentry URL (`https://rentry.co/my-page`) |
| `secret_ref` | Yes | Name of the GitHub secret holding your edit code |
| `theme` | No | Name of a theme in `themes/` (e.g. `example`) — merges defaults overridable by page fields |
| `PAGE_TITLE` | No | Rentry metadata field (see `src/metadata_fields.yaml` for all options) |

### Themes

The `theme` field merges defaults from `themes/<name>.yaml` before publishing. Page-level metadata always overrides theme values. Copy `themes/example.yaml` to create your own:

```yaml
# themes/my-theme.yaml
CONTAINER_MAX_WIDTH:
  - 800px
CONTENT_TEXT_ALIGN:
  - left
```

Then reference it in your page's metadata:

```yaml
slug: my-page
theme: my-theme
PAGE_TITLE: "My Page"
```

### 2. Configure secrets

Each page's `secret_ref` must match a GitHub secret you create:

| Secret name | Used by |
|---|---|
| `BLOG_EDIT_CODE` | when `secret_ref: BLOG_EDIT_CODE` in `pages/blog/metadata.yaml` |
| `ABOUT_EDIT_CODE` | when `secret_ref: ABOUT_EDIT_CODE` in `pages/about/metadata.yaml` |
| `MY_PAGE_EDIT_CODE` | ...and so on for any page |

1. Go to your repository on GitHub
2. **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** for each page
4. **Name**: your secret ref (e.g. `MY_PAGE_EDIT_CODE`)
5. **Secret**: the page's Rentry edit code

### 3. Enable GitHub Actions

1. Go to your repository on GitHub
2. **Actions** tab
3. If prompted, click **I understand my workflows, go ahead and enable them**

### 4. Push

All pages under `pages/` are published on every push:

```bash
git add pages/
git commit -m "add my page"
git push origin main
```

The publisher scans `pages/` and updates each page with its own edit code.

---

## For Developers

### Local setup

```bash
pip install pyyaml
```

### Testing a page

```bash
# Dry run (no actual publish)
python src/publish_rentry.py pages/my-page --edit-code <code> --dry-run

# Publish
python src/publish_rentry.py pages/my-page --edit-code <code>
```

### Regenerating the schema

If Rentry's metadata options change:

```bash
python src/scrape_metadata_schema.py > src/metadata_fields.yaml
```

### Validating the schema

```bash
python src/validate_schema.py
```

### Validating metadata locally

Check page metadata against the schema before pushing:

```bash
# Single page
python src/validate_metadata.py pages/my-page

# All pages
python src/validate_metadata.py
```

---

## Project structure

```
.
├── _example/                 # Reference page to copy from
├── pages/                    # Your content — add pages here
├── themes/                   # Reusable metadata presets
│   └── example.yaml          # Starting point for custom themes
├── src/                      # Publisher, tooling, and metadata schema
├── .github/workflows/        # CI pipeline config
└── requirements.txt
```
