# Contributing

## Branches

- **`dev`** — default branch for all development. Commit freely, push normally.
- **`main`** — stable branch. Only updated via squash merge from `dev`.

## Workflow

1. Work on `dev` with as many commits as needed.
2. Before squashing, bump the version in `VERSION` per semver:
   - `PATCH` (1.0.0 → 1.0.1): bug fixes
   - `MINOR` (1.0.0 → 1.1.0): new features
   - `MAJOR` (1.0.0 → 2.0.0): breaking changes
3. Commit the version bump on `dev`.
4. Squash merge to `main`:

```bash
git checkout main
git merge --squash dev
git commit -m "v<version>: <short description>"
git push origin main
```

### Commit message conventions for `main`

- `v1.0.0: initial release`
- `v1.1.0: add dry-run mode`
- `v1.1.1: fix CSRF timeout`
