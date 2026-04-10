from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.color import Color
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static

_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Navigation", [
        ("↑ / ↓", "move cursor"),
        ("space / enter", "expand or collapse"),
        ("enter", "edit item"),
    ]),
    ("Actions", [
        ("n", "new item"),
        ("ctrl+n", "new subtask"),
        ("d", "delete"),
        ("drop", "attach file to task"),
        ("ctrl+r", "refresh"),
    ]),
    ("Filters", [
        ("r", "filter roles"),
        ("m", "filter milestones"),
        ("t", "filter tasks"),
    ]),
    ("Other", [
        ("k", "keybindings"),
        ("q", "quit"),
    ]),
]

_KEY_STYLE = "bold #f0883e on #21262d"
_DESC_STYLE = "#6e7681"
_SECTION_STYLE = "#484f58"


class KeybindingsScreen(ModalScreen[None]):
    """Read-only keybindings reference popup.

    Displays all app-level keybindings grouped by category.
    Dismissed by pressing k or escape.
    """

    DEFAULT_CSS = (Path(__file__).parent / "styles" / "keybindings_screen.tcss").read_text(encoding="utf-8")

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Keybindings", id="kb-title")
            for section_name, pairs in _GROUPS:
                yield Static(section_name, classes="kb-section")
                for key, description in pairs:
                    row = Text()
                    row.append(f" {key} ", style=_KEY_STYLE)
                    row.append(f"  {description}", style=_DESC_STYLE)
                    yield Static(row, classes="kb-row")
            yield Static("k · esc  close", id="kb-hint")

    def on_mount(self) -> None:
        self.styles.background = Color(0, 0, 0, a=0.6)

    def on_key(self, event) -> None:
        if event.key in ("escape", "k"):
            event.stop()
            self.dismiss(None)
