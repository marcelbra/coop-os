from __future__ import annotations

from textual.binding import Binding
from textual.events import Key
from textual.message import Message
from textual.widgets import TextArea


class DetailTextArea(TextArea):
    """TextArea that posts ExitRequested when ← is pressed at column 0."""

    BINDINGS = [
        Binding("super+z", "undo", "Undo", show=False),
        Binding("super+shift+z", "redo", "Redo", show=False),
        Binding("super+v", "paste", "Paste", show=False),
    ]

    class ExitRequested(Message):
        """User wants to leave edit mode."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._escape_prefix: bool = False

    def on_mount(self) -> None:
        self.styles.scrollbar_size_vertical = 0
        self.styles.scrollbar_size_horizontal = 0

    def on_key(self, event: Key) -> None:
        # macOS terminals send option+shift+arrow as ESC followed by a plain
        # arrow. We track the ESC and convert the next arrow into a selection
        # action so that option+shift+left/right selects word-by-word and
        # option+shift+up/down extends the selection line-by-line.
        if event.key == "escape":
            self._escape_prefix = True
            return

        if self._escape_prefix:
            self._escape_prefix = False
            if event.key == "left":
                event.prevent_default()
                event.stop()
                self.action_cursor_word_left(True)
                return
            elif event.key == "right":
                event.prevent_default()
                event.stop()
                self.action_cursor_word_right(True)
                return
            elif event.key == "up":
                event.prevent_default()
                event.stop()
                self.action_cursor_up(True)
                return
            elif event.key == "down":
                event.prevent_default()
                event.stop()
                self.action_cursor_down(True)
                return

        if event.key == "tab":
            event.prevent_default()
            event.stop()
            self.insert("  ")
            return

        if event.key == "left" and self.cursor_location[1] == 0:
            event.prevent_default()
            event.stop()
            self.post_message(DetailTextArea.ExitRequested())
