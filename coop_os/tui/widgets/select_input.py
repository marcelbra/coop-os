from __future__ import annotations

from typing import Any

from textual.events import Key
from textual.message import Message
from textual.widget import Widget

from coop_os.tui.widgets.field_input import FieldInput
from coop_os.tui.widgets.text_area import DetailTextArea


class SelectInput(Widget):
    """Single-line selectable field; Enter opens an inline option list."""

    can_focus = True

    class ValueSelected(Message):
        """Posted after the user confirms a selection from the dropdown."""

    def __init__(self, options: list[str] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._options: list[str] = options or []
        self._display: list[str] = list(self._options)
        self._value: str = ""
        self._open: bool = False
        self._cursor: int = 0

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, v: str) -> None:
        self._value = v
        self.refresh()

    def set_options(self, options: list[str], display: list[str] | None = None) -> None:
        self._options = options
        self._display = display if display is not None else list(options)

    def render(self) -> str:
        if not self._open:
            try:
                return self._display[self._options.index(self._value)]
            except (ValueError, IndexError):
                return self._value
        lines = []
        for i, disp in enumerate(self._display):
            prefix = "> " if i == self._cursor else "  "
            lines.append(f"{prefix}{disp}")
        return "\n".join(lines)

    def _open_dropdown(self) -> None:
        self._open = True
        try:
            self._cursor = self._options.index(self._value.strip())
        except ValueError:
            self._cursor = 0
        n = max(len(self._options), 1)
        if self.parent:
            self.parent.styles.height = n
        self.styles.height = n
        self.refresh()

    def _close_dropdown(self) -> None:
        self._open = False
        if self.parent:
            self.parent.styles.height = 1
        self.styles.height = 1
        self.refresh()

    def on_key(self, event: Key) -> None:  # noqa: C901
        if self.disabled:
            return
        if not self._open:
            if event.key == "enter":
                event.prevent_default()
                event.stop()
                if self._options:
                    self._open_dropdown()
            elif event.key == "up":
                event.prevent_default()
                event.stop()
                self.post_message(FieldInput.Navigate(-1))
            elif event.key == "down":
                event.prevent_default()
                event.stop()
                self.post_message(FieldInput.Navigate(+1))
            elif event.key == "left":
                event.prevent_default()
                event.stop()
                self.post_message(DetailTextArea.ExitRequested())
        else:
            if event.key == "up":
                event.prevent_default()
                event.stop()
                self._cursor = max(0, self._cursor - 1)
                self.refresh()
            elif event.key == "down":
                event.prevent_default()
                event.stop()
                self._cursor = min(len(self._options) - 1, self._cursor + 1)
                self.refresh()
            elif event.key == "enter":
                event.prevent_default()
                event.stop()
                if self._options:
                    self._value = self._options[self._cursor]
                self._close_dropdown()
                self.post_message(SelectInput.ValueSelected())
            elif event.key in ("escape", "left"):
                event.prevent_default()
                event.stop()
                self._close_dropdown()

    def on_blur(self) -> None:
        if self._open:
            self._close_dropdown()
