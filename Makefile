.PHONY: install skills lint format fix run launch test check sync-worktree seed-workspace clear-workspace reset-session

MAIN_REPO := $(shell git worktree list | head -1 | awk '{print $$1}')

install:  ## Install project dependencies
	uv sync --group dev
	git config core.hooksPath .githooks
	$(MAKE) skills
	@[ "$$(uname)" = "Darwin" ] && brew install --cask iterm2 2>/dev/null || true

skills:  ## Install agent skills into .claude/skills/ (requires npx)
	@command -v npx >/dev/null 2>&1 || { \
		echo "error: 'npx' not found. Install Node.js (https://nodejs.org) to set up agent skills." >&2; \
		exit 1; \
	}
	npx --yes skills add ./coop_os/agent/skills --all

lint:  ## Check for linting and type errors
	uv run ruff check coop_os
	uv run basedpyright coop_os

format:  ## Format the code
	uv run ruff format coop_os

fix:  ## Auto-fix ruff errors
	uv run ruff check --fix coop_os

test:  ## Run the test suite
	uv run pytest tests/

check: lint test  ## Run lint and tests (CI)

sync-worktree:  ## Copy gitignored workspace/user state from the main worktree into this one
	cp -r $(MAIN_REPO)/coop_os/workspace coop_os/
	cp -r $(MAIN_REPO)/coop_os/user coop_os/

run:  ## Start the TUI
	uv run coop-os start

launch:  ## Open iTerm2 maximized, vertical split by default. Use SPLIT=h for horizontal (top/bottom).
	@bash "$(CURDIR)/launch.sh" $(if $(filter h,$(SPLIT)),-h,-v)

seed-workspace:  ## Seed workspace with demo data (5 roles, 16 milestones, 30 tasks)
	uv run scripts/seed_workspace.py

clear-workspace:  ## Delete all workspace context (roles, milestones, tasks, user data, session)
	uv run scripts/clear_workspace.py

reset-session:  ## Reset session state (filters, expansions, cursor) without touching workspace content
	uv run scripts/reset_session.py

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
