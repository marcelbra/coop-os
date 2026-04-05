# Claude Code Instructions

## Git & PR Workflow

**Never push directly to `main`.** Branch protection is enabled — all changes go through PRs.

### Branch naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/<slug>` | `feature/dynamic-footer-hints` |
| Bug fix | `fix/<slug>` | `fix/cursor-nav-after-expand` |
| Chore / cleanup | `chore/<slug>` | `chore/skills-cleanup` |

### Creating a PR

1. Branch off `origin/main` (not local main): `git checkout -b <branch> origin/main`
2. Make focused, atomic commits
3. Push to `origin`: `git push origin <branch>`
4. Open PR against `main` on `marcelbra/agent-os`:
   ```
   gh pr create --repo marcelbra/agent-os --base main --head <branch>
   ```
5. Group changes by concern — one logical unit per PR

### Merging

Use squash merge: `gh pr merge <n> --repo marcelbra/agent-os --squash --delete-branch`

**Always wait 5 seconds after creating a PR before merging** — GitHub needs a moment to register the PR or pushes may fail. Use `sleep 5` between the `gh pr create` and `gh pr merge` calls.

**Always ask the user to test the changes before creating a PR.** After implementing, prompt the user to verify it works, then wait for confirmation before proceeding to create and merge the PR.

**Always merge immediately after creating a PR.** Don't wait for user confirmation — create the PR and merge it in the same workflow. After merging, switch to main and pull to get a fresh state:
```
git checkout main && git pull origin main
```

### What belongs in separate PRs

Split into distinct PRs when changes touch different concerns (e.g. a feature in one file and a bug fix in another, or code changes vs. docs/skills cleanup). Combine when changes are tightly coupled and make no sense apart.

## Development Commands

Use the Makefile for common tasks:

| Command | Purpose |
|---------|---------|
| `make lint` | Check for linting and type errors (ruff + basedpyright) |
| `make fix` | Auto-fix linting errors |
| `make format` | Format code |
| `make run` | Start the TUI |
| `make install` | Install dependencies |

Always run `make lint` after making changes — it runs both ruff (style) and basedpyright (types). Use `make fix` to auto-resolve import ordering and other fixable issues.

## Development Mode

This project is in active development with no production users. **Never add backward-compatibility shims, migration layers, or legacy-format handling.** When a format or contract changes, update all affected files and callsites directly. This applies until explicitly stated otherwise.
