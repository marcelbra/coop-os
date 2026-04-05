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

### What belongs in separate PRs

Split into distinct PRs when changes touch different concerns (e.g. a feature in one file and a bug fix in another, or code changes vs. docs/skills cleanup). Combine when changes are tightly coupled and make no sense apart.

## Development Mode

This project is in active development with no production users. **Never add backward-compatibility shims, migration layers, or legacy-format handling.** When a format or contract changes, update all affected files and callsites directly. This applies until explicitly stated otherwise.
