from __future__ import annotations

from collections.abc import Callable

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

    def on_mount(self) -> None:
        self.styles.scrollbar_size_vertical = 0
        self.styles.scrollbar_size_horizontal = 0

    def on_key(self, event: Key) -> None:
        # Textual delivers Option+arrow as alt+arrow (single event).
        alt_actions: dict[str, tuple[Callable[[bool], None], bool]] = {
            "alt+left": (self.action_cursor_word_left, False),
            "alt+right": (self.action_cursor_word_right, False),
            "alt+shift+left": (self.action_cursor_word_left, True),
            "alt+shift+right": (self.action_cursor_word_right, True),
            "alt+up": (self.action_cursor_up, False),
            "alt+down": (self.action_cursor_down, False),
            "alt+shift+up": (self.action_cursor_up, True),
            "alt+shift+down": (self.action_cursor_down, True),
        }
        if event.key in alt_actions:
            action, select = alt_actions[event.key]
            event.prevent_default()
            event.stop()
            action(select)
            return

        if event.key == "alt+backspace":
            event.prevent_default()
            event.stop()
            self.action_delete_word_left()
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
