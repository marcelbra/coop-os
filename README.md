<h3 align="center">coop-os</h3>

<p align="center">Agent-native operating system for your daily life. Simple but powerful.</p>

<p align="center">
  <a href="https://pypi.org/project/coop-os/"><img src="https://img.shields.io/pypi/v/coop-os" alt="PyPI version"></a>
  <a href="https://pypi.org/project/coop-os/"><img src="https://img.shields.io/badge/python-3.13%2B-blue" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/marcelbra/coop-os" alt="License"></a>
  <a href="https://github.com/marcelbra/coop-os/actions"><img src="https://img.shields.io/github/actions/workflow/status/marcelbra/coop-os/lint.yml?label=CI" alt="CI"></a>
</p>

---

**coop-os** is a lightweight context layer for agent-human co-working. Unlike classic note taking apps and todo lists it works around simple markdown files that any agent harness can edit. Humans can navigate and edit in a lightweight terminal-only UI.

**Three core concepts**
- the workspace — a tree with an opinionated structure: `roles` → `milestones` → `tasks`
- an agent space — primary worker definitions, augmented by skills and workflows
- a user space — personal context and notetaking

**Features**
- note taking on steroids
- agent-first design
- seamless and smooth TUI for humans

**Coming soon**
- Skills 2.0 — improved workflow integration incl. MCP server
- Examples and tutorials
- An agent-driven CLI for control and performance

Collaboration welcome — see [Contributing](https://github.com/marcelbra/coop-os?tab=contributing-ov-file).

## Requirements

- Python 3.13+ (subject to downgrade)
- Node.js / `npx` — required to install agent skills (`npx skills add ...`)

## Install

```bash
pip install coop-os
npx skills add marcelbra/coop-os
coop-os start        # launch the TUI
```

For local development:

```bash
make install
make run             # start the TUI
```

To work with an agent alongside the TUI, open a second terminal window (or tmux/wezterm pane) and run your agent harness there (e.g. `claude`).


## Configuration

`config.yml` in the project root controls runtime behaviour:

```yaml
agent_harness_command: claude   # preferred agent harness to run alongside the TUI
```

## Collaboration

See [Contributing](https://github.com/marcelbra/coop-os?tab=contributing-ov-file) for the branching model, PR workflow, and release process.


## Notes

Currently only tested on Mac Silicon. The TUI runs in any terminal emulator (Terminal.app, iTerm2, wezterm, Alacritty, etc.).