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

1. **Before starting any work**, ask the user: "Do you want to work in a worktree (isolated) or directly on the project?" Wait for their answer before proceeding.
2. If worktree: call `EnterWorktree` with the branch name (following naming conventions above) — this creates an isolated worktree. If direct: create and check out the branch manually with `git checkout -b <branch> origin/develop`.
3. Make focused, atomic commits
4. If in a worktree: call `ExitWorktree` after committing — it cleans up automatically. Then push to `origin`. If direct: push to `origin`: `git push origin <branch>`.
5. Open PR against `develop` on `marcelbra/coop-os`:
   ```
   gh pr create --repo marcelbra/coop-os --base develop --head <branch>
   ```
6. Group changes by concern — one logical unit per PR

Use squash merge — wait for CI first, then: `gh pr merge <n> --repo marcelbra/coop-os --squash --delete-branch --admin`

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
3. Wait for CI, then merge with a merge commit (not squash — preserves develop history):
   ```
   gh pr checks <n> --repo marcelbra/coop-os --watch
   gh pr merge <n> --repo marcelbra/coop-os --merge --admin
   ```
4. The release workflow auto-tags `vX.Y.Z` and publishes to PyPI.
5. Pull main locally: `git checkout main && git pull origin main`

**The workflow will fail if the version tag already exists** — this is intentional. You must bump the version in `pyproject.toml` before every release merge.

### Merging rules

**Always wait for CI before merging.** After creating a PR, run `gh pr checks <n> --repo marcelbra/coop-os --watch` and wait for all checks to pass. Only then merge with `--admin`. Never merge while checks are failing or pending.

**Always ask the user to review and test before committing.** After implementing:
1. Explain what changed, , concisely
2. Run `make check` — if it passes, prompt the user to test
3. Give them the exact commands to run in a new terminal window, as two lines:
   ```
   cd <worktree-path>
   make run
   ```
4. Describe exactly what to verify — e.g. "You should see a bold orange `·` next to any task that has child tasks."
5. Wait for explicit confirmation before running `git commit`

Only after confirmation: commit, push, open the PR, and merge — all in one uninterrupted workflow.

**Always merge immediately after creating a PR.** Don't wait for further confirmation after the user has already approved — create the PR and merge it in the same workflow.

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

## Code Standards

### Naming
Always use explicit, descriptive names. No single-letter variables, no abbreviations — even when context makes the meaning obvious. Prefer clarity over brevity at every scope level.

```python
# bad
for i in ids: ...
m = re.search(...)
d = _find_task_dir(...)

# good
for id_str in ids: ...
match = re.search(...)
task_dir = _find_task_dir(...)
```

### Docstrings
Add docstrings to any function whose behavior or intent is not immediately obvious from its signature. Document:
- What it does and why (not just how)
- Non-obvious contracts, invariants, or edge cases
- Filtering logic, cascade rules, preservation guarantees

### Type safety
Every function must be fully typed — parameters, return values, and local variables where the type is not inferred. No `Any` unless genuinely unavoidable. Run `make lint` (basedpyright) to verify.

### Tests
Write tests for any non-trivial behavior. Before writing tests for a new feature or edge case, confirm the intended behavior with the user first. Tests must cover the real contract, not just the happy path.

## Development Mode

This project is in active development with no production users. **Never add backward-compatibility shims, migration layers, or legacy-format handling.** When a format or contract changes, update all affected files and callsites directly. This applies until explicitly stated otherwise.
