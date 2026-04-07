from __future__ import annotations

from textual.app import ComposeResult
from textual.color import Color
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static


class FilterScreen(ModalScreen[set[str] | None]):
    """Multiselect filter pop-over.

    Returns the selected status set on confirm, or None on cancel.
    """

    DEFAULT_CSS = """
FilterScreen {
    align: center middle;
}
FilterScreen > #dialog {
    width: 38;
    height: auto;
    background: #161b22;
    border: heavy #30363d;
    padding: 1 2;
}
FilterScreen #fs-title {
    width: 1fr;
    color: #58a6ff;
    margin-bottom: 1;
}
FilterScreen .fs-option {
    height: 1;
    color: #c9d1d9;
    padding: 0 1;
}
FilterScreen .fs-option.-cursor {
    background: #1c2d45;
    color: #e6edf3;
}
FilterScreen #fs-hint {
    color: #6e7681;
    margin-top: 1;
}
"""

    def __init__(
        self,
        title: str,
        options: list[tuple[str, str]],
        selected: set[str],
    ) -> None:
        super().__init__()
        self._title = title
        self._options = options       # [(value, display_label), ...]
        self._selected = set(selected)
        self._cursor = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._title, id="fs-title")
            for i, (value, label) in enumerate(self._options):
                mark = "◉" if value in self._selected else "○"
                cls = "fs-option -cursor" if i == 0 else "fs-option"
                yield Static(f" {mark}  {label}", id=f"fs-opt-{i}", classes=cls)
            yield Static("space toggle · enter confirm · esc cancel", id="fs-hint")

    def on_mount(self) -> None:
        self.styles.background = Color(0, 0, 0, a=0.6)

    def _refresh_options(self) -> None:
        for i, (value, label) in enumerate(self._options):
            w = self.query_one(f"#fs-opt-{i}", Static)
            mark = "◉" if value in self._selected else "○"
            w.update(f" {mark}  {label}")
            if i == self._cursor:
                w.add_class("-cursor")
            else:
                w.remove_class("-cursor")

    def on_key(self, event) -> None:
        key = event.key
        if key == "escape":
            event.stop()
            self.dismiss(None)
        elif key == "enter":
            event.stop()
            self.dismiss(self._selected)
        elif key == "up":
            event.stop()
            self._cursor = max(0, self._cursor - 1)
            self._refresh_options()
        elif key == "down":
            event.stop()
            self._cursor = min(len(self._options) - 1, self._cursor + 1)
            self._refresh_options()
        elif key == "space":
            event.stop()
            value = self._options[self._cursor][0]
            if value in self._selected:
                self._selected.discard(value)
            else:
                self._selected.add(value)
            self._refresh_options()
