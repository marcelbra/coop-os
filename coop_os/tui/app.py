from __future__ import annotations

import os
import signal
import types
from pathlib import Path
from types import SimpleNamespace

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.widgets import Tree

from coop_os.backend.models import (
    Context,
    Milestone,
    Note,
    Role,
    Skill,
    Task,
)
from coop_os.backend.store import ProjectStore
from coop_os.tui.actions import ActionsMixin
from coop_os.tui.nav import ContentNav, FileNav, Nav, StructuralNav, nav_from_parts, nav_to_parts
from coop_os.tui.session import SessionState, load_session, save_session
from coop_os.tui.state import StateManager
from coop_os.tui.styles import CSS as APP_CSS
from coop_os.tui.widgets import (
    ContentPanel,
    DetailTextArea,
    ExpansionState,
    FixedHeader,
    NavTree,
    SelectInput,
    SplitFooter,
    StructuredEditor,
)
from coop_os.tui.widgets.config import FILE_LANGUAGES

_SECTION_TO_KIND: dict[str, str] = {
    "roles": "role",
    "milestones": "milestone",
    "tasks": "task",
    "notes": "note",
    "contexts": "context",
    "skills": "skill",
}


class CoopOSApp(ActionsMixin, App[None]):
    TITLE = "coop-os"
    CSS = APP_CSS
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("r", "filter_roles", "role", show=False),
        Binding("m", "filter_milestones", "milestone", show=False),
        Binding("t", "filter_tasks", "task", show=False),
        Binding("n", "new_item", "new", show=False),
        Binding("ctrl+n", "new_subtask", "new subtask", show=False),
        Binding("d", "delete_item", "delete", show=False),
        Binding("ctrl+r", "refresh_state", "Refresh", show=False),
    ]

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        store = ProjectStore(root)
        self.sm = StateManager(store, root)
        self.selected: Nav | None = StructuralNav("section", "roles")

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield FixedHeader()
        with Horizontal():
            yield NavTree("coop-os", id="nav")
            yield ContentPanel(id="content")
        yield SplitFooter()

    def on_mount(self) -> None:
        session = load_session(self.root)
        self.sm.role_filters = session.role_filters
        self.sm.milestone_filters = session.milestone_filters
        self.sm.task_filters = session.task_filters
        if session.selected_kind:
            self.selected = nav_from_parts(session.selected_kind, session.selected_id, session.selected_section)
        self._reload(initial_expansion=ExpansionState(
            session.expanded_sections, session.expanded_tasks, session.expanded_dirs
        ))
        self._update_right_hints()
        for sig in (signal.SIGHUP, signal.SIGTERM):
            signal.signal(sig, self._on_termination_signal)

    def _on_termination_signal(self, signum: int, frame: types.FrameType | None) -> None:
        self._save_session()
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    def _save_session(self) -> None:
        try:
            tree = self.query_one(NavTree)
            expansion = tree.expanded_state()
            cursor_nav = self.selected
            if cursor_nav is None:
                cursor_node = tree.cursor_node
                if cursor_node is not None:
                    cursor_nav = cursor_node.data
            if cursor_nav is not None:
                sel_kind, sel_id, sel_section = nav_to_parts(cursor_nav)
            else:
                sel_kind, sel_id, sel_section = "section", "", "roles"
            save_session(self.root, SessionState(
                role_filters=self.sm.role_filters,
                milestone_filters=self.sm.milestone_filters,
                task_filters=self.sm.task_filters,
                expanded_sections=expansion.sections,
                expanded_tasks=expansion.tasks,
                expanded_dirs=expansion.dirs,
                selected_kind=sel_kind,
                selected_id=sel_id,
                selected_section=sel_section,
            ))
        except NoMatches:
            pass

    async def action_quit(self) -> None:
        self._save_session()
        await super().action_quit()

    # ── State ─────────────────────────────────────────────────────────────────

    def _sync_state(self, initial_expansion: ExpansionState | None = None) -> None:
        """Load state from disk and repopulate the tree.

        This is the single authoritative sync point between disk and UI. Call it
        any time the on-disk files change (after a save, create, or delete) to
        ensure self.state and the NavTree are consistent. It deliberately does
        not touch focus, view mode, or selection — callers own those concerns.
        """
        state = self.sm.load()
        visible_role_ids = self.sm.visible_role_ids()
        visible_milestone_ids = self.sm.visible_milestone_ids(visible_role_ids)
        self.query_one(NavTree).populate(
            state, self.root, self.sm.role_filters, self.sm.milestone_filters, self.sm.task_filters,
            task_dirs=self.sm.task_dirs(),
            visible_role_ids=visible_role_ids,
            visible_milestone_ids=visible_milestone_ids,
            initial_expansion=initial_expansion,
        )

    def _reload(self, initial_expansion: ExpansionState | None = None) -> None:
        # Capture both the selected item nav AND the cursor nav (which may be a
        # section header when no item is selected) before sync, so focus_nav can
        # restore the cursor even when cursor is on a section node (self.selected
        # is None for sections, so the old `if selected:` guard skipped focus_nav,
        # leaving cursor_line stale after rebuild — pointing to a divider).
        selected = self.selected
        tree = self.query_one(NavTree)
        cursor_nav: Nav | None = selected
        if cursor_nav is None:
            cursor_node = tree.cursor_node
            if cursor_node is not None:
                cursor_nav = cursor_node.data
        self._sync_state(initial_expansion)
        assert self.sm.state is not None
        if cursor_nav is not None:
            tree.focus_nav(cursor_nav)
        if selected is not None:
            self._show_view()
        if self.sm.state.errors:
            self.notify(
                f"{len(self.sm.state.errors)} parse error(s) — check files",
                severity="warning",
                timeout=4,
            )

    def reload_state(self) -> None:
        """Public reload entry point that preserves cursor and selection."""
        self._reload()

    def _item(self) -> Role | Milestone | Task | Note | Context | Skill | None:
        return self.sm.item(self.selected)

    def _item_path(self) -> Path | None:
        return self.sm.item_path(self.selected)

    def _update_footer_hints(self, nav: Nav | None) -> None:
        content = self.query_one(ContentPanel)
        editing = content.is_editing

        pairs: list[tuple[str, str]] = []
        if not editing and nav is not None:
            new_kind: str | None = None
            if isinstance(nav, StructuralNav) and nav.section in _SECTION_TO_KIND:
                new_kind = _SECTION_TO_KIND[nav.section]
            elif isinstance(nav, ContentNav) and nav.kind != "context":
                new_kind = nav.kind
            if new_kind:
                pairs.append(("n", f"new {new_kind}"))
            if isinstance(nav, ContentNav) and nav.kind == "task":
                pairs.append(("^n", "new subtask"))
            if isinstance(nav, ContentNav):
                pairs.append(("d", "delete"))

        self.query_one(SplitFooter).update_left(pairs)

    def _update_right_hints(self) -> None:
        active = {
            k for k, f in [
                ("r", self.sm.role_filters),
                ("m", self.sm.milestone_filters),
                ("t", self.sm.task_filters),
            ]
            if f
        }
        self.query_one(SplitFooter).update_right(
            "Filters",
            [("r", "role"), ("m", "milestone"), ("t", "task")],
            active,
        )

    # ── Tree navigation ───────────────────────────────────────────────────────

    @on(Tree.NodeHighlighted, "#nav")
    def on_node_highlighted(self, event: Tree.NodeHighlighted[Nav | None]) -> None:
        nav = event.node.data
        self._update_footer_hints(nav)
        content = self.query_one(ContentPanel)
        if content.is_editing:
            return
        if nav is None or isinstance(nav, StructuralNav):
            self.selected = None
            content.clear()
            return
        self.selected = nav
        self._show_view()

    @on(Tree.NodeSelected, "#nav")
    def on_node_selected(self, event: Tree.NodeSelected[Nav | None]) -> None:
        nav = event.node.data
        self._update_footer_hints(nav)
        content = self.query_one(ContentPanel)
        if nav is None or isinstance(nav, StructuralNav):
            self.selected = None
            content.clear()
            return
        if content.is_editing:
            self._save_current()
        self.selected = nav
        self._show_view()

    # ── Edit mode ─────────────────────────────────────────────────────────────

    @on(NavTree.EditRequested)
    def on_edit_requested(self, event: NavTree.EditRequested) -> None:
        self.selected = event.nav
        self._show_edit()

    @on(DetailTextArea.ExitRequested)
    def on_exit_requested(self) -> None:
        self._exit_edit_mode()

    @on(StructuredEditor.Changed)
    def on_structured_editor_changed(self) -> None:
        self._save_current()

    @on(SelectInput.ValueSelected)
    def on_select_value_selected(self) -> None:
        self._save_current()

    def _exit_edit_mode(self) -> None:
        self._save_current()
        content = self.query_one(ContentPanel)
        content.remove_class("-editing")
        content.remove_class("-editing-struct")
        content.remove_class("-view-struct")
        self._show_view()
        self._update_footer_hints(self.selected)
        tree = self.query_one(NavTree)
        tree.focus()
        if self.selected:
            tree.focus_nav(self.selected)

    # ── View / Edit ───────────────────────────────────────────────────────────

    @work(exclusive=True)
    async def _show_view(self) -> None:
        if not self.selected:
            return
        content = self.query_one(ContentPanel)
        if content.is_editing:
            return
        if isinstance(self.selected, FileNav) and self.selected.kind == "agent":
            path = self._item_path()
            if not path or not path.exists() or not self.sm.state:
                return
            text = path.read_text(encoding="utf-8")
            agent_doc = SimpleNamespace(content=text)
            content.show_struct_view(agent_doc, "agent", self.sm.cfg(), self.sm.state)
            self.query_one(NavTree).focus()
        elif isinstance(self.selected, FileNav) and self.selected.kind == "task_file":
            path = self._item_path()
            if not path or not path.exists() or not self.sm.state:
                return
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                await content.show_view("_Cannot be rendered yet :)_")
                self.query_one(NavTree).focus()
                return
            file_doc = SimpleNamespace(content=text, language=FILE_LANGUAGES.get(path.suffix.lower(), ""))
            content.show_struct_view(file_doc, "agent", self.sm.cfg(), self.sm.state)
            self.query_one(NavTree).focus()
        elif isinstance(self.selected, FileNav) and self.selected.kind == "task_dir":
            content.clear()
            self.query_one(NavTree).focus()
        else:
            item = self._item()
            if not item or not self.sm.state:
                return
            assert isinstance(self.selected, ContentNav)
            content.show_struct_view(item, self.selected.kind, self.sm.cfg(), self.sm.state)
            # Re-focus NavTree: show_struct_view applies -view-struct which makes
            # StructuredEditor visible; its focusable children can steal focus.
            self.query_one(NavTree).focus()

    def _show_edit(self, select_all: bool = False) -> None:
        content = self.query_one(ContentPanel)
        if not self.selected:
            return
        if isinstance(self.selected, FileNav) and self.selected.kind == "agent":
            path = self._item_path()
            if not path or not path.exists():
                return
            agent_doc = SimpleNamespace(content=path.read_text(encoding="utf-8"))
            if not self.sm.state:
                return
            content.enter_structured_edit(agent_doc, "agent", self.sm.cfg(), self.sm.state)
        elif isinstance(self.selected, FileNav) and self.selected.kind == "task_file":
            path = self._item_path()
            if not path or not path.exists() or not self.sm.state:
                return
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                return
            file_doc = SimpleNamespace(content=text, language=FILE_LANGUAGES.get(path.suffix.lower(), ""))
            content.enter_structured_edit(file_doc, "agent", self.sm.cfg(), self.sm.state)
        else:
            item = self._item()
            if not item or not self.sm.state:
                return
            assert isinstance(self.selected, ContentNav)
            content.enter_structured_edit(item, self.selected.kind, self.sm.cfg(), self.sm.state, select_all=select_all)

    # ── Auto-save ─────────────────────────────────────────────────────────────

    def _save_current(self) -> None:
        content = self.query_one(ContentPanel)
        if not self.selected or not content.is_editing:
            return
        path = self._item_path()
        if not path:
            return
        try:
            path.write_text(content.editor_text, encoding="utf-8")
            self._sync_state()
        except Exception as e:
            self.notify(str(e), severity="error", timeout=4)

    # ── Misc ──────────────────────────────────────────────────────────────────

    def action_refresh_state(self) -> None:
        self._reload()
        self.notify("Refreshed", severity="information", timeout=2)
