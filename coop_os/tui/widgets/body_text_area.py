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
        # Snapshot the flag before super() consumes it. If the up key was the
        # second event of an option+shift+up sequence (ESC then up), we must
        # not treat it as "plain up at row 0 → navigate to fields".
        was_escape_prefix = self._escape_prefix
        super().on_key(event)
        if event.key == "up" and self.cursor_location[0] == 0 and not was_escape_prefix:
            event.prevent_default()
            event.stop()
            self.post_message(FieldInput.Navigate(-1))
