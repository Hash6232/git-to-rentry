# Contributing

## Branches

- **`dev`** — default branch for all development. Commit freely here.
- **`main`** — template branch. No direct commits. Squash `dev` into a single
  commit with `ghost` as both author and committer:

  ```bash
  GIT_AUTHOR_NAME="ghost" GIT_AUTHOR_EMAIL="" \
  GIT_COMMITTER_NAME="ghost" GIT_COMMITTER_EMAIL="" \
  git commit --amend --no-edit
  git push origin main --force
  ```
