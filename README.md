<p align="center">
  <img src="banner.png" alt="coop-os" width="100%">
</p>

<h3 align="center">coop-os</h3>

---

<p align="center">The personal OS where you and your agent work as one</p>

<p align="center">
  <a href="https://pypi.org/project/coop-os/"><img src="https://img.shields.io/pypi/v/coop-os" alt="PyPI version"></a>
  <a href="https://pypi.org/project/coop-os/"><img src="https://img.shields.io/badge/python-3.13%2B-blue" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/marcelbra/coop-os" alt="License"></a>
  <a href="https://github.com/marcelbra/coop-os/actions"><img src="https://img.shields.io/github/actions/workflow/status/marcelbra/coop-os/lint.yml?label=CI" alt="CI"></a>
</p>

---


A lightweight context layer for human-AI co-working. Plain markdown files your agent can read and edit directly — a keyboard-driven TUI so you can navigate and update everything yourself.

## What it is

coop-os is built around one idea: **your agent needs context, and you need visibility into what it's doing.**

Everything lives in `coop_os/context/` as plain markdown files with YAML frontmatter. No database, no sync service, no lock-in. Your agent reads and writes files directly. You use the TUI to review, edit, and stay in sync.

The workflow is simple: you and your agent work through milestones and tasks together. The agent reads your current state, picks up where things left off, and works directly inside task directories. You check in via the TUI or by running a skill like `/check-in` or `/weekly-review`.

## Content layer

```
coop_os/context/
├── AGENT.md              # How your agent should operate — instructions, preferences, context
├── milestones/           # Long-horizon goals, each a markdown file
├── tasks/                # Actionable items — each task is a directory the agent works in
├── notes/                # Logs, reflections, observations, raw capture
└── skills/               # Slash-command prompts your agent can run (e.g. /check-in)
```

**Tasks as working directories.** Each task lives in its own folder (`tasks/task-1-slug/`). The agent writes its work — notes, drafts, outputs — directly into that directory alongside `description.md`. Nothing is hidden in a database.

**Skills.** Skills are markdown files that define reusable agent workflows. `/check-in` surfaces today's priorities, `/scan-notes` processes unread notes, `/weekly-review` does what it says. You can edit, create, and delete skills from the TUI.

**AGENT.md.** The top-level driver file for your agent. Define its persona, working style, and any persistent context that should always be in scope. Editable directly from the TUI.

## Install

```bash
pip install coop-os
coop-os start
```

Requires Python 3.13+.

## TUI

The TUI gives you a keyboard-driven view into your content layer.

```
┌─────────────────┬────────────────────────────────────┐
│  AGENT.md       │                                    │
│  Milestones     │   Content panel                    │
│    milestone-1  │   (view / edit / structured form)  │
│  Tasks          │                                    │
│    task-1       │                                    │
│  Notes          │                                    │
│  Skills         │                                    │
└─────────────────┴────────────────────────────────────┘
```

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate tree |
| `→` | Expand section / enter edit |
| `←` | Collapse / exit editor (auto-saves) |
| `n` | New item in current section |
| `d` | Delete item |
| `r` | Refresh from disk |

Structured items (tasks, milestones, notes) open as forms — status, dates, labels, milestone links. AGENT.md and skills open as a raw markdown editor with syntax highlighting.

## Coming soon

- **MCP integrations** — Google Calendar and Gmail wired in so your agent can cross-reference your schedule and inbox during `/check-in` and `/weekly-review`
- **CLI** — a command-line interface so your agent can create, update, and query content without touching files directly

## Tech

- [Textual](https://github.com/Textualize/textual) — TUI framework
- [python-frontmatter](https://github.com/eyeseast/python-frontmatter) — markdown + YAML parsing
- [Pydantic](https://docs.pydantic.dev/) — data models
