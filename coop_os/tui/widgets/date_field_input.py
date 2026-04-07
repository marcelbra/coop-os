from __future__ import annotations

from datetime import date as _date
from typing import Any

from textual.events import Key
from textual.message import Message

from coop_os.tui.widgets.field_input import FieldInput


class DateFieldInput(FieldInput):
    """FieldInput with ISO date (YYYY-MM-DD) validation. Reverts on bad input."""

    class CalendarRequested(Message):
        def __init__(self, attr_key: str, current_value: str) -> None:
            super().__init__()
            self.attr_key = attr_key
            self.current_value = current_value

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._prev_value: str = ""

    def on_focus(self) -> None:
        super().on_focus()
        self._prev_value = self.value

    def on_blur(self) -> None:
        val = self.value.strip()
        if not val:
            return
        try:
            _date.fromisoformat(val)
        except ValueError:
            self.app.notify(
                f'Invalid date "{val}" — expected YYYY-MM-DD',
                severity="error",
                timeout=4,
            )
            self.value = self._prev_value

    def on_key(self, event: Key) -> None:
        super().on_key(event)
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            attr_key = (self.id or "").removeprefix("se-inp-")
            self.post_message(DateFieldInput.CalendarRequested(attr_key, self.value))
