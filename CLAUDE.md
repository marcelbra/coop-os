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

Every agent-driven change lands via a PR. The agent **always** works in an isolated worktree — never directly on the main checkout. When the work is done it pushes the branch, opens the PR, drops the worktree, and stops. The user reviews and merges at their own pace.

1. **Create the worktree.** Call `EnterWorktree` with the branch name (following the naming table above). The worktree's `make run` points at the main checkout's workspace via `--root $(MAIN_REPO)`, so live data is available without `make sync-worktree`.
2. **Do the work** in focused, atomic commits. The agent owns correctness — run `make check` before committing and fix anything it flags. No user confirmation is required before `git commit`.
3. **Push the branch** from inside the worktree: `git push -u origin <branch>`.
4. **Open the PR** against `develop`:
   ```
   gh pr create --repo marcelbra/coop-os --base develop --head <branch> --title "..." --body "..."
   ```
   Surface the PR URL in the response to the user.
5. **Drop the worktree** once the PR URL has been captured:
   ```
   ExitWorktree(action=remove, discard_changes=true)
   ```
   `discard_changes=true` is safe here because every commit has been pushed to `origin` — the local branch holds no unique state.
6. **Stop.** Do not merge. The user reviews on GitHub or checks the branch out in the main tree (`git fetch && git checkout <branch>`) whenever convenient.

Group changes by concern — one logical unit per PR. If a session produces unrelated work streams, open two PRs (sequentially, one worktree at a time).

### Reviewing a PR (and iterating on it)

When the user opens a session and says they want to review PR `<n>` (or the PR's branch name), the worktree is gone. Work happens in the **main checkout**, not a new worktree:

1. Confirm the main checkout has no uncommitted work that would block a branch switch (`git status`). If it does, flag it and let the user decide.
2. `git fetch origin`
3. `git checkout <branch>` in the main checkout — the local tracking branch is created from `origin/<branch>` automatically if it doesn't already exist.
4. Walk the diff with the user. If they request changes, make them here in the main checkout, commit, and `git push` (no `-u` — the branch already tracks origin). Confirm the PR shows the new commits.
5. When the user is done reviewing, return to develop: `git checkout develop && git pull origin develop`. No worktree to clean up.

Why main-checkout instead of a worktree: review is a user-initiated, user-present activity that already has a branch on origin. Worktrees exist to isolate *new* work that doesn't yet have a branch — they're overhead for an operation that's one `git checkout` away.

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

**The user merges; the agent does not.** The agent's responsibility ends at "PR pushed and linked in the response." The user reviews at their pace and either merges or requests changes.

When the user explicitly asks to merge a PR:

1. Wait for CI: `gh pr checks <n> --repo marcelbra/coop-os --watch`. Never merge while checks are failing or pending.
2. Squash-merge with admin and branch cleanup: `gh pr merge <n> --repo marcelbra/coop-os --squash --delete-branch --admin`.
3. Pull develop locally: `git checkout develop && git pull origin develop`.

**Testing.** The agent self-tests via `make check` before opening the PR. For UI or runtime behaviour the user will want to exercise manually, include a **Test plan** checklist in the PR body so the user can run it whenever they review — don't block the PR on the user running it first.

### What belongs in separate PRs

Split into distinct PRs when changes touch different concerns (e.g. a feature in one file and a bug fix in another, or code changes vs. docs/skills cleanup). Combine when changes are tightly coupled and make no sense apart.

## GitHub Accounts

Two accounts are configured via SSH host aliases:

| Alias | Account | Email |
|-------|---------|-------|
| `github-personal` | marcelbra | marcelbraasch@gmail.com |
| `github-work` | marcel-braasch_kpn | marcel.braasch@kpn.com |

**Check which account a repo is using:**
```
git remote get-url origin
```
The alias in the URL (`github-personal` or `github-work`) tells you which account will be used.

**Switch a repo to a different account:**
```
git remote set-url origin git@github-personal:marcelbra/repo.git
# or
git remote set-url origin git@github-work:workorg/repo.git
```

**When cloning**, always replace `github.com` with the right alias:
```
git clone git@github-personal:marcelbra/repo.git
git clone git@github-work:workorg/repo.git
```

This repo uses `github-personal`. The `gh` CLI stores its auth separately from SSH (in `~/.config/gh/hosts.yml`), so it's a per-machine setup that can drift from the SSH config. Each account needs its own login run — a fresh machine has no `gh` auth until you do this for each account you need:

```
gh auth login --hostname github.com
```

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

### Skills: personal vs. repo-standard

All skills live in **one** directory: `coop_os/agent/skills/`. By default, anything dropped in there is **personal** — `.gitignore` ignores the directory's contents, so new skills stay local and never ship via PyPI. A small allowlist of repo-standard skills (the ones bundled with the package) is explicitly un-ignored.

```
mkdir -p coop_os/agent/skills/my-skill
$EDITOR coop_os/agent/skills/my-skill/SKILL.md
make skills   # installs everything (allowlisted + personal) into .claude/skills/
```

**Publishing a personal skill** (promoting it to a tracked, shipped skill):

1. Add `!coop_os/agent/skills/<slug>/` to the skills allowlist block in `.gitignore`.
2. `git add coop_os/agent/skills/<slug>/` and commit.

**Rule of thumb**: if a skill's "Required reading" section points at a file under `coop_os/user/` or `coop_os/workspace/`, it should stay personal — don't add it to the allowlist.

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
