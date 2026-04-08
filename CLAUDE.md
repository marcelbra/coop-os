# Claude Code Instructions

## Git & PR Workflow

Two long-lived branches:

| Branch | Purpose |
|--------|---------|
| `develop` | Integration branch — all PRs target this |
| `main` | Release branch — every merge triggers a PyPI publish |

**Never push directly to `main` or `develop`.** All changes go through PRs.

### Branch naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/<slug>` | `feature/dynamic-footer-hints` |
| Bug fix | `fix/<slug>` | `fix/cursor-nav-after-expand` |
| Chore / cleanup | `chore/<slug>` | `chore/skills-cleanup` |

### Day-to-day: feature → develop

1. Branch off `origin/develop`: `git checkout -b <branch> origin/develop`
2. Make focused, atomic commits
3. Push to `origin`: `git push origin <branch>`
4. Open PR against `develop` on `marcelbra/coop-os`:
   ```
   gh pr create --repo marcelbra/coop-os --base develop --head <branch>
   ```
5. Group changes by concern — one logical unit per PR

Use squash merge: `gh pr merge <n> --repo marcelbra/coop-os --squash --delete-branch`

After merging, switch to develop and pull: `git checkout develop && git pull origin develop`

### Releasing: develop → main

When `develop` is stable and ready to ship:

1. On `develop`, in a single PR:
   - Bump `version` in `pyproject.toml`
   - Run `uv sync` to update `uv.lock`, then commit it alongside `pyproject.toml`
   - Add a `## [X.Y.Z] - YYYY-MM-DD` entry to `CHANGELOG.md`
2. Open a release PR from `develop` to `main`:
   ```
   gh pr create --repo marcelbra/coop-os --base main --head develop --title "Release vX.Y.Z"
   ```
3. Merge with a merge commit (not squash — preserves develop history):
   ```
   gh pr merge <n> --repo marcelbra/coop-os --merge
   ```
4. The release workflow auto-tags `vX.Y.Z` and publishes to PyPI.
5. Pull main locally: `git checkout main && git pull origin main`

**The workflow will fail if the version tag already exists** — this is intentional. You must bump the version in `pyproject.toml` before every release merge.

### Merging rules

**Always wait 5 seconds after creating a PR before merging** — GitHub needs a moment to register the PR or pushes may fail. Use `sleep 5` between the `gh pr create` and `gh pr merge` calls.

**Always ask the user to test the changes before creating a PR.** After implementing, prompt the user to verify it works, then wait for confirmation before proceeding to create and merge the PR.

**Always merge immediately after creating a PR.** Don't wait for user confirmation — create the PR and merge it in the same workflow.

### What belongs in separate PRs

Split into distinct PRs when changes touch different concerns (e.g. a feature in one file and a bug fix in another, or code changes vs. docs/skills cleanup). Combine when changes are tightly coupled and make no sense apart.

## Development Commands

Use the Makefile for common tasks:

| Command | Purpose |
|---------|---------|
| `make check` | Run lint and tests (mirrors CI) |
| `make lint` | Check for linting and type errors (ruff + basedpyright) |
| `make test` | Run the test suite |
| `make fix` | Auto-fix linting errors |
| `make format` | Format code |
| `make run` | Start the TUI |
| `make install` | Install dependencies |

Always run `make check` after making changes — it runs ruff, basedpyright, and pytest. Use `make fix` to auto-resolve import ordering and other fixable issues.

## Development Mode

This project is in active development with no production users. **Never add backward-compatibility shims, migration layers, or legacy-format handling.** When a format or contract changes, update all affected files and callsites directly. This applies until explicitly stated otherwise.
