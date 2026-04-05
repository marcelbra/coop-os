from __future__ import annotations

from textual.widgets import Header


class FixedHeader(Header):
    """Header that does not grow when clicked."""

    def _on_click(self) -> None:
        pass
