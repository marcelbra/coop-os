from __future__ import annotations

from pathlib import Path

from coop_os.iterm_launch import _read_agent_command


def test_read_agent_command_defaults_to_claude_when_no_config(tmp_path: Path) -> None:
    assert _read_agent_command(tmp_path) == "claude"


def test_read_agent_command_returns_configured_value(tmp_path: Path) -> None:
    (tmp_path / "config.yml").write_text("agent_harness_command: aider\n")
    assert _read_agent_command(tmp_path) == "aider"


def test_read_agent_command_strips_quotes(tmp_path: Path) -> None:
    (tmp_path / "config.yml").write_text('agent_harness_command: "gpte"\n')
    assert _read_agent_command(tmp_path) == "gpte"


def test_read_agent_command_defaults_to_claude_when_value_blank(tmp_path: Path) -> None:
    (tmp_path / "config.yml").write_text("agent_harness_command: \n")
    assert _read_agent_command(tmp_path) == "claude"
