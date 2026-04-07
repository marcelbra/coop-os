from __future__ import annotations

from textual.app import RenderResult
from textual.widget import Widget


class FixedHeader(Widget):
    """A simple non-interactive header that displays the app title."""

    def render(self) -> RenderResult:
        return self.app.title
