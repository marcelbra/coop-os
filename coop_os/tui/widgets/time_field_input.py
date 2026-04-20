from __future__ import annotations

from datetime import time as _time
from typing import Any

from coop_os.tui.widgets.field_input import FieldInput


class TimeFieldInput(FieldInput):
    """FieldInput with HH:MM (24h) validation. Reverts on bad input."""

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
            _time.fromisoformat(val if len(val) > 5 else f"{val}:00")
        except ValueError:
            self.app.notify(
                f'Invalid time "{val}" — expected HH:MM',
                severity="error",
                timeout=4,
            )
            self.value = self._prev_value
