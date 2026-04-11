from __future__ import annotations

from typing import Any

from textual.containers import ScrollableContainer
from textual.events import MouseDown
from textual.widget import Widget
from textual.widgets import Markdown

from coop_os.backend.models import ProjectState
from coop_os.tui.widgets.config import AppConfig
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

    def on_mount(self) -> None:
        # The viewer is a scroll container shown in non-editing modes. It never
        # needs keyboard focus — mouse-wheel scrolling works without it — so
        # we disable focusability here to prevent it from stealing focus from
        # the NavTree when the user clicks the content panel in view mode.
        self.query_one(".cp-viewer").can_focus = False

    def on_mouse_down(self, event: MouseDown) -> None:
        """Prevent content-panel children from stealing focus in non-editing modes.

        Two mechanisms work together here:
        - on_mount sets can_focus=False on .cp-viewer, which is the primary fix:
          Markdown widgets are not focusable by default, so the ScrollableContainer
          was the only child that could steal focus in view mode.
        - This handler is belt-and-suspenders: it covers ContentPanel itself and any
          future focusable children added to the view-mode layout.

        The intent is that in view mode the NavTree always retains keyboard focus so
        that arrow-key navigation keeps working after the user clicks to read content.
        """
        if not self.has_class("-editing") and not self.has_class("-editing-struct"):
            event.prevent_default()
            event.stop()

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

    def show_struct_view(self, item: Any, kind: str, cfg: AppConfig, state: ProjectState) -> None:
        """Structured view mode (read-only) for milestone / task / note."""
        se = self.query_one(StructuredEditor)
        se.load(item, kind, cfg, state)
        se.set_editable(False)
        self.remove_class("-editing")
        self.remove_class("-editing-struct")
        self.add_class("-view-struct")

    def enter_structured_edit(
        self, item: Any, kind: str, cfg: AppConfig, state: ProjectState, select_all: bool = False
    ) -> None:
        """Structured edit mode for milestone / task / note."""
        se = self.query_one(StructuredEditor)
        se.load(item, kind, cfg, state)
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
