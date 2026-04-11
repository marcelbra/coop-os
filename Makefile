.PHONY: install lint format fix run test check sync-worktree seed-workspace clear-workspace

MAIN_REPO := $(shell git worktree list | head -1 | awk '{print $$1}')

install:  ## Install project dependencies
	uv sync --group dev
	git config core.hooksPath .githooks
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

seed-workspace:  ## Seed workspace with demo data (5 roles, 16 milestones, 30 tasks)
	uv run scripts/seed_workspace.py

clear-workspace:  ## Delete all workspace context (roles, milestones, tasks, user data, session)
	uv run scripts/clear_workspace.py

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
