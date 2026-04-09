from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.color import Color
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static


class FilterScreen(ModalScreen[set[str] | None]):
    """Multiselect filter pop-over.

    Returns the selected status set on confirm, or None on cancel.
    """

    DEFAULT_CSS = (Path(__file__).parent / "styles" / "filter_screen.tcss").read_text(encoding="utf-8")

    def __init__(
        self,
        title: str,
        options: list[tuple[str, str]],
        selected: set[str],
    ) -> None:
        super().__init__()
        self._title = title
        self._options = options       # [(value, display_label), ...] — value=="" means separator
        self._selected = set(selected)
        self._cursor = next((i for i, (v, _) in enumerate(options) if v != ""), 0)

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._title, id="fs-title")
            for i, (value, label) in enumerate(self._options):
                if value == "":
                    yield Static(f"  {label}", id=f"fs-opt-{i}", classes="fs-separator")
                else:
                    mark = "◉" if value in self._selected else "○"
                    cls = "fs-option -cursor" if i == self._cursor else "fs-option"
                    yield Static(f" {mark}  {label}", id=f"fs-opt-{i}", classes=cls)
            yield Static("space toggle · t toggle group · enter confirm · esc cancel", id="fs-hint")

    def on_mount(self) -> None:
        self.styles.background = Color(0, 0, 0, a=0.6)

    # --- rendering ---

    def _refresh_options(self) -> None:
        for i, (value, label) in enumerate(self._options):
            w = self.query_one(f"#fs-opt-{i}", Static)
            if value == "":
                continue
            mark = "◉" if value in self._selected else "○"
            w.update(f" {mark}  {label}")
            if i == self._cursor:
                w.add_class("-cursor")
            else:
                w.remove_class("-cursor")

    # --- navigation ---

    def _next_selectable(self, pos: int, direction: int) -> int:
        """Return the nearest selectable index from pos, moving in direction (+1/-1)."""
        i = pos
        while 0 <= i < len(self._options):
            if self._options[i][0] != "":
                return i
            i += direction
        return pos

    def _move_cursor(self, direction: int) -> None:
        candidate = self._next_selectable(self._cursor + direction, direction)
        if 0 <= candidate < len(self._options):
            self._cursor = candidate
        self._refresh_options()

    # --- selection ---

    def _toggle_current(self) -> None:
        value = self._options[self._cursor][0]
        if value in self._selected:
            self._selected.discard(value)
        else:
            self._selected.add(value)
        self._refresh_options()

    def _toggle_group(self) -> None:
        group = self._group_values()
        if group.issubset(self._selected):
            self._selected -= group
        else:
            self._selected |= group
        self._refresh_options()

    def _group_values(self) -> set[str]:
        """Return all selectable values in the same section as the cursor."""
        separator = next((i for i, (v, _) in enumerate(self._options) if v == ""), None)
        if separator is None:
            return {v for v, _ in self._options if v != ""}
        if self._cursor < separator:
            return {v for i, (v, _) in enumerate(self._options) if v != "" and i < separator}
        return {v for i, (v, _) in enumerate(self._options) if v != "" and i > separator}

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
            self._move_cursor(-1)
        elif key == "down":
            event.stop()
            self._move_cursor(1)
        elif key == "space":
            event.stop()
            self._toggle_current()
        elif key == "t":
            event.stop()
            self._toggle_group()
