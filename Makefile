.PHONY: install lint format fix run test

install:  ## Install project dependencies
	uv sync --group dev
	git config core.hooksPath .githooks

lint:  ## Check for linting and type errors
	uv run ruff check coop_os
	uv run basedpyright coop_os

format:  ## Format the code
	uv run ruff format coop_os

fix:  ## Auto-fix ruff errors
	uv run ruff check --fix coop_os

test:  ## Run the test suite
	uv run pytest tests/

run:  ## Start the TUI
	uv run coop-os start

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
