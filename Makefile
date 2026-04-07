.PHONY: install lint format fix run test

install:  ## Install project dependencies
	uv sync --group dev
	git config core.hooksPath .githooks

lint:  ## Check for linting and type errors
	uv run ruff check agent_os
	uv run basedpyright agent_os

format:  ## Format the code
	uv run ruff format agent_os

fix:  ## Auto-fix ruff errors
	uv run ruff check --fix agent_os

test:  ## Run the test suite
	uv run pytest tests/

run:  ## Start the TUI
	uv run agent-os start

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
