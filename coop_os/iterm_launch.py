"""iTerm2 split-pane launch for coop-os.

Writes Dynamic Profiles (TUI + agent) and opens iTerm2 with two panes:
left/top runs the coop-os TUI, right/bottom runs the configured agent harness.
"""

from __future__ import annotations

import io
import json
import math
import os
import pathlib
import plistlib
import subprocess
import time
from pathlib import Path


def write_iterm_profiles() -> None:
    """Write coop-os Dynamic Profiles to the iTerm2 DynamicProfiles directory.

    Reads the Default iTerm2 profile font, scales the TUI pane to 135% and
    the agent pane to 200%, and writes two profiles: coop-os-tui (blue tab)
    and coop-os-agent (orange tab).
    """
    result = subprocess.run(
        ["defaults", "export", "com.googlecode.iterm2", "-"],
        capture_output=True,
    )
    plist = plistlib.load(io.BytesIO(result.stdout))

    base_font = "Monaco 13"
    for bookmark in plist.get("New Bookmarks", []):
        if bookmark.get("Name") == "Default":
            base_font = bookmark.get("Normal Font", "Monaco 13")
            break

    parts = base_font.rsplit(" ", 1)
    font_name = parts[0]
    base_size = float(parts[1]) if len(parts) > 1 else 13
    tui_font = f"{font_name} {int(math.ceil(base_size * 1.5))}"
    agent_font = f"{font_name} {int(math.ceil(base_size * 1.1))}"

    cs = "Color Space"
    dark_bg = {
        "Red Component": 0.051, "Green Component": 0.067,
        "Blue Component": 0.090, "Alpha Component": 1.0, cs: "sRGB",
    }
    light_fg = {
        "Red Component": 0.788, "Green Component": 0.820,
        "Blue Component": 0.851, "Alpha Component": 1.0, cs: "sRGB",
    }
    blue_tab = {
        "Red Component": 0.0, "Green Component": 0.31,
        "Blue Component": 1.0, "Alpha Component": 1.0, cs: "sRGB",
    }
    orange_tab = {
        "Red Component": 1.0, "Green Component": 0.50,
        "Blue Component": 0.0, "Alpha Component": 1.0, cs: "sRGB",
    }

    # Ctrl+Shift+Arrow key bindings for switching focus between panes.
    # Key format: "0x{unicode}-0x{modifier_flags}" where arrow keys carry the
    # NumericPad flag (0x200000) in addition to Ctrl (0x40000) and Shift (0x20000).
    # Action 18 = KEY_ACTION_SELECT_PANE_LEFT, 19 = KEY_ACTION_SELECT_PANE_RIGHT.
    # iTerm2 intercepts these before forwarding to the terminal, so they work
    # inside the Textual TUI without any TUI-side changes. Both actions are
    # directional (no wrap-around): pressing right while already in the
    # rightmost pane does nothing, and vice versa.
    pane_switch_key_map = {
        "0xf703-0x260000": {"Action": 19, "Text": ""},  # Ctrl+Shift+Right → Select Pane Right
        "0xf702-0x260000": {"Action": 18, "Text": ""},  # Ctrl+Shift+Left  → Select Pane Left
    }

    profiles = {"Profiles": [
        {
            "Name": "coop-os-tui",
            "Guid": "coop-os-tui-guid",
            "Dynamic Profile Parent Name": "Default",
            "Normal Font": tui_font,
            "Background Color": dark_bg,
            "Foreground Color": light_fg,
            "Tab Color": blue_tab,
            "Use Tab Color": True,
            "Title Components": 16,
            "Custom Title": "coop-os",
            "Keyboard Map": pane_switch_key_map,
        },
        {
            "Name": "coop-os-agent",
            "Guid": "coop-os-agent-guid",
            "Dynamic Profile Parent Name": "Default",
            "Normal Font": agent_font,
            "Background Color": dark_bg,
            "Foreground Color": light_fg,
            "Tab Color": orange_tab,
            "Use Tab Color": True,
            "Title Components": 16,
            "Custom Title": "coop-os",
            "Keyboard Map": pane_switch_key_map,
        },
    ]}

    profiles_dir = pathlib.Path.home() / "Library/Application Support/iTerm2/DynamicProfiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "coop-os.json").write_text(json.dumps(profiles, indent=2))


def _read_agent_command(root: Path) -> str:
    """Read agent_harness_command from config.yml, defaulting to 'claude'."""
    config_path = root / "config.yml"
    if config_path.exists():
        for line in config_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("agent_harness_command:"):
                value = stripped.split(":", 1)[1].strip().strip('"')
                if value:
                    return value
    return "claude"


def launch(root: Path, horizontal: bool = False) -> None:
    """Open iTerm2 maximized with TUI and agent panes side by side.

    Disables inactive pane dimming, writes Dynamic Profiles, then uses
    AppleScript to create a window with a vertical (default) or horizontal
    split. The TUI pane runs `coop-os start` and the agent pane runs the
    configured agent harness command.

    Args:
        root: Project root directory — used as the working directory for both
              panes and to read config.yml for the agent harness command.
        horizontal: If True, split top/bottom instead of left/right.
    """
    subprocess.run(
        ["defaults", "write", "com.googlecode.iterm2", "DimInactiveSplitPanes", "-bool", "false"],
        check=True,
    )

    write_iterm_profiles()

    agent_cmd = _read_agent_command(root)
    split_direction = "horizontally" if horizontal else "vertically"
    root_str = str(root)

    # If not already inside iTerm, launch it and wait for it to be ready.
    in_iterm = os.environ.get("TERM_PROGRAM") == "iTerm.app"
    if not in_iterm:
        iterm_running = subprocess.run(["pgrep", "-xq", "iTerm2"]).returncode == 0
        if not iterm_running:
            subprocess.run(["open", "-a", "iTerm"], check=True)
            while subprocess.run(["pgrep", "-xq", "iTerm2"]).returncode != 0:
                time.sleep(0.3)
            time.sleep(2)

    script = f"""
tell application "Finder" to set screenBounds to bounds of window of desktop
tell application "iTerm2"
    set w to (create window with profile "coop-os-tui")
    tell w
        set tui_pane to current session of current tab
        tell tui_pane
            set agent_pane to (split {split_direction} with profile "coop-os-agent")
            write text "cd '{root_str}' && coop-os start"
        end tell
        tell agent_pane
            set current_cols to columns
            set columns to (round (current_cols * 0.30))
            write text "cd '{root_str}' && {agent_cmd}"
        end tell
    end tell
    set bounds of w to screenBounds
end tell
"""
    subprocess.run(["osascript", "-e", script], check=True)

    # If launched from outside iTerm, bring it to the front now.
    if not in_iterm:
        subprocess.run(["open", "-a", "iTerm"], check=True)
