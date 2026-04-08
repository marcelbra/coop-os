<h3 align="center">coop-os</h3>

<p align="center">Agent-native operating system for your daily life. Simple but powerful.</p>

<p align="center">
  <a href="https://pypi.org/project/coop-os/"><img src="https://img.shields.io/pypi/v/coop-os" alt="PyPI version"></a>
  <a href="https://pypi.org/project/coop-os/"><img src="https://img.shields.io/badge/python-3.13%2B-blue" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/marcelbra/coop-os" alt="License"></a>
  <a href="https://github.com/marcelbra/coop-os/actions"><img src="https://img.shields.io/github/actions/workflow/status/marcelbra/coop-os/lint.yml?label=CI" alt="CI"></a>
</p>

---

**coop-os** is a lightweight context layer for agent-human co-working. Unlike classic note taking apps and todo lists `coop-os` works around simple text files that any agent harness can edit. Humans can navigate and edit in a lightweight terminal-only UI.

The app comes with

... three core concepts
- the workspace - as tree with an opinionated naming as `roles` -> `milestones` -> `tasks`
- an agent space as primary worker definitions - augmented by skills and workflows
- user space for context - user information and personal notetaking

... the following features
- note taking on steroids
- agent-first design
- seamless and smooth TUI for humans

And will soon be extended to
- Skills 2.0 - improved workflow integration incl. mcp server
- Examples and tutorials
- An agent-driven CLI mostly for control and performance - for now agent harnesses file editing should work

Collaboration welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Install

To run do

```bash
pip install coop-os
coop-os start
```

or

for local development do

```bash
make install
make run
```

Requires Python 3.13+. Subject to downgrade.


## Collaboration

See [CONTRIBUTING.md](CONTRIBUTING.md) for the branching model, PR workflow, and release process.


## Notes

Currently only tested on Mac Silicon bash terminal.