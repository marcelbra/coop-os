from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.color import Color
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmDeleteScreen(ModalScreen[bool]):
    DEFAULT_CSS = (Path(__file__).parent / "styles" / "confirm_delete.tcss").read_text(encoding="utf-8")

    _GREY = "#30363d"
    _BLUE = "#1f6feb"
    _RED = "#da3633"

    def __init__(self, item_name: str) -> None:
        super().__init__()
        self.item_name = item_name

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f'Delete "{self.item_name}"?')
            with Horizontal(id="buttons"):
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Delete", variant="default", id="confirm")

    def on_mount(self) -> None:
        self.styles.background = Color(0, 0, 0, a=0.6)
        self._focus_button("cancel")

    def _focus_button(self, focused_id: str) -> None:
        cancel = self.query_one("#cancel", Button)
        confirm = self.query_one("#confirm", Button)
        cancel.styles.background = self._BLUE if focused_id == "cancel" else self._GREY
        confirm.styles.background = self._RED if focused_id == "confirm" else self._GREY
        (cancel if focused_id == "cancel" else confirm).focus()
        self.call_after_refresh(self._reset_button_borders)

    def _reset_button_borders(self) -> None:
        for btn in self.query(Button):
            btn.styles.border = ("none", "transparent")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

    def on_key(self, event) -> None:
        if event.key in ("escape", "q"):
            event.stop()
            self.dismiss(False)
        elif event.key in ("left", "right"):
            event.stop()
            focused = self.focused
            confirm = self.query_one("#confirm", Button)
            self._focus_button("cancel" if focused is confirm else "confirm")
