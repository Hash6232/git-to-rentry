# rentry-publish

Automated publishing pipeline for Rentry pages.
Push markdown to `main` — your Rentry page updates automatically.

---

## For CI Users

### 1. Add a page

Create a directory under `pages/` with two files:

```
pages/my-page/
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
secret_ref: RENTRY_EDIT_CODE

PAGE_TITLE: "My Page"
ACCESS_RECOMMENDED_THEME:
  - dark
```

| Field | Required | What it is |
|---|---|---|
| `slug` | Yes | The Rentry URL (`https://rentry.co/my-page`) |
| `secret_ref` | Yes | Name of the GitHub secret holding your edit code |
| `theme` | No | Name of a theme in `themes/` (e.g. `example`) — merges defaults overridable by page fields |
| `PAGE_TITLE` | No | Rentry metadata field (see `schemas/metadata_fields.yaml` for all options) |

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

1. Go to your repository on GitHub
2. **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. **Name**: `RENTRY_EDIT_CODE`
5. **Secret**: your Rentry edit code

### 3. Enable GitHub Actions

1. Go to your repository on GitHub
2. **Actions** tab
3. If prompted, click **I understand my workflows, go ahead and enable them**

### 4. Push

```bash
git add pages/
git commit -m "add my page"
git push origin main
```

GitHub Actions will run `src/publish_rentry.py` and update your Rentry page.

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
python src/scrape_metadata_schema.py > schemas/metadata_fields.yaml
```

### Validating the schema

```bash
python src/validate_schema.py
```

---

## Project structure

```
.
├── pages/                    # Your content — add pages here
│   └── example/              # Reference page to copy from
├── themes/                   # Reusable metadata presets
│   └── example.yaml          # Starting point for custom themes
├── src/                      # Publisher and tooling (run by CI)
├── schemas/                  # Auto-generated metadata field definitions
├── .github/workflows/        # CI pipeline config
└── requirements.txt
```
