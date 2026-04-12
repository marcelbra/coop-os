from __future__ import annotations

from typing import Any

from textual.binding import Binding
from textual.events import Key
from textual.message import Message
from textual.widgets import Input

from coop_os.tui.widgets.text_area import DetailTextArea


class FieldInput(Input):
    """Input field that navigates between fields (↑/↓) and exits edit mode (←)."""

    BINDINGS = [
        Binding("super+v", "paste", "Paste", show=False),
    ]

    class Navigate(Message):
        def __init__(self, direction: int) -> None:
            super().__init__()
            self.direction = direction  # -1 = up, +1 = down

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.select_on_next_focus: bool = False

    def on_focus(self) -> None:
        if self.select_on_next_focus:
            self.select_on_next_focus = False
            self.call_after_refresh(self.action_select_all)
        else:
            self.call_after_refresh(self.action_home)

    def on_key(self, event: Key) -> None:
        # Textual delivers Option+arrow as alt+arrow (single event).
        if event.key == "alt+left":
            event.prevent_default()
            event.stop()
            self.action_cursor_left_word(False)
            return
        elif event.key == "alt+right":
            event.prevent_default()
            event.stop()
            self.action_cursor_right_word(False)
            return
        elif event.key == "alt+shift+left":
            event.prevent_default()
            event.stop()
            self.action_cursor_left_word(True)
            return
        elif event.key == "alt+shift+right":
            event.prevent_default()
            event.stop()
            self.action_cursor_right_word(True)
            return
        elif event.key == "alt+backspace":
            event.prevent_default()
            event.stop()
            self.action_delete_left_word()
            return

        if event.key == "up":
            event.prevent_default()
            event.stop()
            self.post_message(FieldInput.Navigate(-1))
        elif event.key == "down":
            event.prevent_default()
            event.stop()
            self.post_message(FieldInput.Navigate(+1))
        elif event.key == "left" and self.cursor_position == 0:
            event.prevent_default()
            event.stop()
            self.post_message(DetailTextArea.ExitRequested())
