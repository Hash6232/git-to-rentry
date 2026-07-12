# git-to-rentry

Automatically publish Rentry pages directly from GitHub.

Store your pages as Markdown, push to `main`, and GitHub Actions updates every Rentry page automatically.

## Features

* 🚀 Publish multiple Rentry pages from one repository
* 📝 Write pages in plain Markdown
* 🎨 Reusable themes for shared styling
* 🔒 Separate edit codes for every page using GitHub Secrets
* ✅ Metadata validation before publishing
* ⚙️ Fully automated with GitHub Actions
* 🔍 Smart change detection — compares local vs live content and only posts when something actually changed

---

# Quick Start

## 1. Create your pages

Each directory inside `pages/` becomes its own Rentry page.

```text
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

`content.md`

```markdown
# Hello

This page will be published to Rentry.
```

For supported Markdown syntax and formatting, see the [Rentry Markdown guide](https://rentry.org/how).

`metadata.yaml`

```yaml
slug: hello
secret_ref: HELLO_EDIT_CODE

PAGE_TITLE: "Hello"
ACCESS_RECOMMENDED_THEME:
  - dark
```

Required fields:

| Field        | Description                                   |
| ------------ | --------------------------------------------- |
| `slug`       | The Rentry URL (`https://rentry.co/<slug>`)   |
| `secret_ref` | GitHub secret containing the page's edit code |

Everything else is optional Rentry metadata.

For the complete list of metadata fields, see the [Rentry Metadata documentation](https://rentry.co/metadata-how).

---

## 2. (Optional) Use themes

Themes provide reusable metadata defaults.

Create a file like:

```yaml
# themes/blog.yaml

CONTAINER_MAX_WIDTH:
  - 800px

CONTENT_TEXT_ALIGN:
  - left
```

Then reference it from your page:

```yaml
slug: hello
secret_ref: HELLO_EDIT_CODE
theme: blog

PAGE_TITLE: Hello
```

Theme values are merged first.

Values defined in `metadata.yaml` always override the theme.

---

## 3. Add GitHub Secrets

Each page needs its own Rentry edit code stored as a repository secret.

Example:

| Secret            | Used by                     |
| ----------------- | --------------------------- |
| `BLOG_EDIT_CODE`  | `pages/blog/metadata.yaml`  |
| `ABOUT_EDIT_CODE` | `pages/about/metadata.yaml` |
| `HELLO_EDIT_CODE` | `pages/hello/metadata.yaml` |

Repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

> [!WARNING]
> **Save your Rentry edit code before adding it as a GitHub Secret.**
>
> Rentry only shows a page's edit code once when the page is created. GitHub Secrets are also write-only—once a secret is saved, GitHub will never display its value again. Editing a secret shows an empty value field, allowing you to replace the secret but not view its current value.
>
> If you lose the edit code, you won't be able to update that Rentry page through this workflow.

---

## 4. Expose the secrets to the workflow

In `.github/workflows/publish.yml`:

```yaml
env:
  BLOG_EDIT_CODE: ${{ secrets.BLOG_EDIT_CODE }}
  ABOUT_EDIT_CODE: ${{ secrets.ABOUT_EDIT_CODE }}
  HELLO_EDIT_CODE: ${{ secrets.HELLO_EDIT_CODE }}
```

Every secret referenced by `secret_ref` must be available here.

---

## 5. Enable GitHub Actions

Open the repository's **Actions** tab and enable workflows if prompted.

---

## 6. Push

```bash
git add pages/
git commit -m "Update pages"
git push origin main
```

The workflow scans every directory in `pages/` and publishes each page using its own edit code.

---

# Local Development

Install dependencies:

```bash
pip install pyyaml
```

Dry run:

```bash
python src/publish_rentry.py pages/my-page --edit-code <code> --dry-run
```

Publish manually:

```bash
python src/publish_rentry.py pages/my-page --edit-code <code>
```

When content hasn't changed, the publisher prints SHA256 hashes and skips the POST with `"Unchanged, skipping"` — the `"Published to"` message only appears when an actual POST happens.

---

# Validation

Validate a single page:

```bash
python src/validate_metadata.py pages/my-page
```

Validate every page:

```bash
python src/validate_metadata.py
```

Check whether local content differs from the published version:

```bash
python src/check_changes.py pages/my-page
python src/check_changes.py      # all pages
```

The script prints SHA256 hashes of both the local and live content for transparent comparison. Content is compared after normalizing line endings and decoding HTML entities (Rentry's edit page encodes `<`, `>`, `&` inside the textarea).

Validate the metadata schema:

```bash
python src/validate_schema.py
```

If Rentry adds new metadata fields, regenerate the schema:

```bash
python src/scrape_metadata_schema.py > src/metadata_fields.yaml
```

---

# Project Structure

```text
.
├── _example/              # Example page
├── pages/                 # Your Rentry pages
├── themes/                # Reusable metadata presets
├── src/                   # Publisher and tooling
├── .github/workflows/     # GitHub Actions
├── CONTRIBUTING.md
└── requirements.txt
```