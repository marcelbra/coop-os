from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class SplitFooter(Widget):
    """Custom footer split 50/50: contextual hints left, filter shortcuts right."""

    DEFAULT_CSS = """
SplitFooter {
    dock: bottom;
    height: 1;
    layout: horizontal;
    background: $panel;
}
SplitFooter #sf-left {
    width: 1fr;
    height: 1;
    padding: 0 1;
    content-align: left middle;
}
SplitFooter #sf-right {
    width: 1fr;
    height: 1;
    padding: 0 1;
    content-align: right middle;
    text-align: right;
}
"""

    _KEY_STYLE = "bold #f0883e on #21262d"
    _DESC_STYLE = "#6e7681"
    _DESC_ACTIVE_STYLE = "#c9d1d9"
    _LABEL_STYLE = "dim #6e7681"
    _ACTIVE_DOT_STYLE = "#58a6ff"

    def compose(self) -> ComposeResult:
        yield Static(Text(), id="sf-left")
        yield Static(Text(), id="sf-right")

    @staticmethod
    def _hint(key: str, desc: str, active: bool = False) -> Text:
        t = Text()
        t.append(f" {key} ", style=SplitFooter._KEY_STYLE)
        if active:
            t.append(f" {desc}", style=SplitFooter._DESC_ACTIVE_STYLE)
            t.append("·", style=SplitFooter._ACTIVE_DOT_STYLE)
        else:
            t.append(f" {desc}", style=SplitFooter._DESC_STYLE)
        return t

    def update_left(self, pairs: list[tuple[str, str]]) -> None:
        t = Text()
        for i, (key, desc) in enumerate(pairs):
            if i > 0:
                t.append("   ")
            t.append_text(self._hint(key, desc))
        self.query_one("#sf-left", Static).update(t)

    def update_right(
        self,
        label: str,
        pairs: list[tuple[str, str]],
        active_keys: set[str],
    ) -> None:
        t = Text(justify="right")
        t.append(f"{label}  ", style=self._LABEL_STYLE)
        for i, (key, desc) in enumerate(pairs):
            if i > 0:
                t.append("   ")
            t.append_text(self._hint(key, desc, active=key in active_keys))
        self.query_one("#sf-right", Static).update(t)
