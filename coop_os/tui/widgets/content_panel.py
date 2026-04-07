from __future__ import annotations

from typing import Any

from textual.containers import ScrollableContainer
from textual.widget import Widget
from textual.widgets import Markdown

from coop_os.tui.widgets.structured_editor import StructuredEditor
from coop_os.tui.widgets.text_area import DetailTextArea


class ContentPanel(Widget):
    """Right panel: Markdown viewer, raw TextArea editor, and structured editor.

    Modes are toggled via CSS classes — no widget is ever unmounted, so layout
    is stable and there are no re-render artifacts.

    CSS classes:
      (none)             → view mode (Markdown visible)
      -editing           → raw edit mode (agent / skill files)
      -editing-struct    → structured edit mode (milestone / task / note)
    """

    def compose(self):
        with ScrollableContainer(classes="cp-viewer"):
            yield Markdown("")
        yield DetailTextArea(
            "", language="markdown", theme="vscode_dark", classes="cp-raw-editor"
        )
        yield StructuredEditor()

    # ── Public interface ───────────────────────────────────────────────────

    def show_view(self, md: str):
        """Switch to view mode and update Markdown content."""
        self.remove_class("-editing")
        self.remove_class("-editing-struct")
        self.remove_class("-view-struct")
        return self.query_one(Markdown).update(md)

    def enter_edit(self, text: str) -> None:
        """Raw edit mode for agent/skill (plain markdown files)."""
        ta = self.query_one(".cp-raw-editor", DetailTextArea)
        ta.load_text(text)
        ta.move_cursor((0, 0))
        self.remove_class("-editing-struct")
        self.add_class("-editing")
        ta.focus()

    def show_struct_view(self, item: Any, kind: str) -> None:
        """Structured view mode (read-only) for milestone / task / note."""
        se = self.query_one(StructuredEditor)
        se.load(item, kind)
        se.set_editable(False)
        self.remove_class("-editing")
        self.remove_class("-editing-struct")
        self.add_class("-view-struct")

    def enter_structured_edit(self, item: Any, kind: str, select_all: bool = False) -> None:
        """Structured edit mode for milestone / task / note."""
        se = self.query_one(StructuredEditor)
        se.load(item, kind)
        se.set_editable(True)
        self.remove_class("-editing")
        self.remove_class("-view-struct")
        self.add_class("-editing-struct")
        se.focus_first(select_all=select_all)

    def clear(self) -> None:
        """Switch to view mode and clear the Markdown content."""
        self.remove_class("-editing")
        self.remove_class("-editing-struct")
        self.remove_class("-view-struct")
        self.query_one(Markdown).update("")

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def is_editing(self) -> bool:
        return self.has_class("-editing") or self.has_class("-editing-struct")

    @property
    def editor_text(self) -> str:
        if self.has_class("-editing"):
            return self.query_one(".cp-raw-editor", DetailTextArea).text
        if self.has_class("-editing-struct"):
            return self.query_one(StructuredEditor).editor_text
        return ""
