# Changelog

All notable changes to this project will be documented in this file.

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
