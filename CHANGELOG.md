# Changelog

All notable changes to this project will be documented in this file.

## [0.4.0] - 2026-04-10

### Added
- `coop-os validate` command and PostToolUse hook integration
- Filter roles and milestones by name in addition to status
- Skills converted to universal SKILL.md format

### Fixed
- Status section header and toggle-dismiss keybindings on filter screen

### Refactored
- TUI nav/filter overhaul — cursor preservation, fallback logic, and nav kind guards
- Decoupled SkillStore from FlatFileStore; aligned Skill model with skills spec

## [0.3.0] - 2026-04-08

### Added
- Per-type file icons and smart delete navigation
- Task folder files shown as navigable tree nodes
- Syntax highlighting for task files in BodyTextArea
- Tab inserts two spaces in DetailTextArea

### Fixed
- Show raw text for agent.md; focus body on right-arrow edit
- README formatting and contributing link updates

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
