from __future__ import annotations

from typing import Any

from textual.events import Key

from coop_os.tui.widgets.field_input import FieldInput
from coop_os.tui.widgets.text_area import DetailTextArea


class BodyTextArea(DetailTextArea):
    """Body textarea: cursor line only highlighted when focused; ↑ at row 0 moves to fields."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.highlight_cursor_line = False

    def on_focus(self) -> None:
        self.highlight_cursor_line = True

    def on_blur(self) -> None:
        self.highlight_cursor_line = False

    def on_key(self, event: Key) -> None:
        super().on_key(event)
        # alt+up is its own key name so it won't match "up" — no extra guard needed.
        if event.key == "up" and self.cursor_location[0] == 0:
            event.prevent_default()
            event.stop()
            self.post_message(FieldInput.Navigate(-1))
