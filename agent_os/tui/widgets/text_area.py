from __future__ import annotations

from textual.events import Key
from textual.message import Message
from textual.widgets import TextArea


class DetailTextArea(TextArea):
    """TextArea that posts ExitRequested when ← is pressed at column 0."""

    class ExitRequested(Message):
        """User wants to leave edit mode."""

    def on_mount(self) -> None:
        self.styles.scrollbar_size_vertical = 0
        self.styles.scrollbar_size_horizontal = 0

    def on_key(self, event: Key) -> None:
        if event.key == "left" and self.cursor_location[1] == 0:
            event.prevent_default()
            event.stop()
            self.post_message(DetailTextArea.ExitRequested())
