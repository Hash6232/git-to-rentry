# Contributing

## Branches

- **`dev`** — default branch for all development. Commit freely, push normally.
- **`main`** — template branch. Only updated via squash merge from `dev`.

## Updating the template

```bash
git checkout main
git merge --squash dev
git commit -m "Updated template"
git push origin main
```
