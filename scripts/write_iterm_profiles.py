"""Write iTerm2 Dynamic Profiles for coop-os.

Reads the Default profile font from iTerm2 preferences, scales it to 150% for
the TUI pane, then writes both profiles (coop-os-tui and coop-os-agent) to the
iTerm2 DynamicProfiles directory.
"""

import io
import json
import math
import pathlib
import plistlib
import subprocess

result = subprocess.run(["defaults", "export", "com.googlecode.iterm2", "-"], capture_output=True)
plist = plistlib.load(io.BytesIO(result.stdout))

base_font = "Monaco 13"
for bookmark in plist.get("New Bookmarks", []):
    if bookmark.get("Name") == "Default":
        base_font = bookmark.get("Normal Font", "Monaco 13")
        break

parts = base_font.rsplit(" ", 1)
font_name = parts[0]
base_size = float(parts[1]) if len(parts) > 1 else 13
zoomed_font = f"{font_name} {int(math.ceil(base_size * 1.5))}"

dark_bg = {"Red Component": 0.051, "Green Component": 0.067, "Blue Component": 0.090, "Alpha Component": 1.0, "Color Space": "sRGB"}
light_fg = {"Red Component": 0.788, "Green Component": 0.820, "Blue Component": 0.851, "Alpha Component": 1.0, "Color Space": "sRGB"}

profiles = {"Profiles": [
    {
        "Name": "coop-os-tui",
        "Guid": "coop-os-tui-guid",
        "Dynamic Profile Parent Name": "Default",
        "Normal Font": zoomed_font,
        "Background Color": dark_bg,
        "Foreground Color": light_fg,
        "Tab Color": {"Red Component": 0.0, "Green Component": 0.31, "Blue Component": 1.0, "Alpha Component": 1.0, "Color Space": "sRGB"},
        "Use Tab Color": True,
    },
    {
        "Name": "coop-os-agent",
        "Guid": "coop-os-agent-guid",
        "Dynamic Profile Parent Name": "Default",
        "Background Color": dark_bg,
        "Foreground Color": light_fg,
        "Tab Color": {"Red Component": 1.0, "Green Component": 0.50, "Blue Component": 0.0, "Alpha Component": 1.0, "Color Space": "sRGB"},
        "Use Tab Color": True,
    },
]}

profiles_dir = pathlib.Path.home() / "Library/Application Support/iTerm2/DynamicProfiles"
profiles_dir.mkdir(parents=True, exist_ok=True)
(profiles_dir / "coop-os.json").write_text(json.dumps(profiles, indent=2))
