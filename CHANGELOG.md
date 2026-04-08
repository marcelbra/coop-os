# Changelog

All notable changes to this project will be documented in this file.

## [0.2.1] - 2026-04-08

### Fixed
- Commit missing `uv.lock` update from 0.2.0 version bump

## [0.2.0] - 2026-04-08

### Added
- **Workspaces**: renamed from "To dos", moved to top of nav tree with triangle expand/collapse icons
- **Filter legend**: split layout with multiselect pop-over in footer
- **Item IDs**: new items numbered by ID and sorted by creation order
- **Branching model**: `develop` integration branch, `main` release-only with auto PyPI publish
- **CONTRIBUTING.md**: contributor guide covering branches, PR workflow, and release process

### Changed
- Redesigned navigation tree with grouped sections and visual separators
- Reorganized disk layout to `user/agent/work` structure
- Unified naming across all layers — `Doc→Context`, `work→workspace`
- Replaced `Header` subclass with plain widget; moved CSS to `.tcss`
- Extracted `StateManager` and injected state into `StructuredEditor`
- Extracted CRUD and filter actions into `ActionsMixin`
- Moved entity schema constants to `backend/schema.py`
- Eliminated per-kind dispatch tables in store and app
- Unified state sync into `_sync_state()`

### Fixed
- Empty section triangles no longer rotate
- Navigation tree down/enter key behaviour
- Cursor now starts on Roles instead of Workspaces header

## [0.1.0] - 2026-04-07

Initial beta release.

### Added
- **Hierarchy**: Roles → Milestones → Tasks → Subtasks
- **Tasks**: directory-based storage with `description.md`, supports nesting
- **Notes**: timestamped markdown notes with `scanned` tracking
- **Docs**: free-form markdown documents (Context section)
- **Skills**: prompt files exposed as slash commands (e.g. `/check-in`, `/check-out`)
- **TUI**: full keyboard-driven interface built on [Textual](https://textual.textualize.io/)
  - Inline calendar popup for date fields
  - Inline dropdown selectors for status, milestone, and other fields
  - Date field validation
  - Text editing keyboard shortcuts
- **CLI**: `coop-os start [--root PATH]`
- **Backend**: markdown + YAML frontmatter storage via `python-frontmatter`; Pydantic models
- **Config**: `config.yml` for UI symbol customization
- **Built-in skills**: `/check-in`, `/check-out`, `/scan-notes`, `/weekly-review`
- **CI**: ruff + basedpyright + pytest on every push/PR
- **Packaging**: installable via `pip install coop-os`, entry point `coop-os`
