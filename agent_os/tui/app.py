from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import cast

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Tree

from agent_os.models import Milestone, Note, ProjectState, Task
from agent_os.store import ProjectStore
from agent_os.tui.confirm_delete import ConfirmDeleteScreen
from agent_os.tui.nav import Nav
from agent_os.tui.styles import CSS as APP_CSS
from agent_os.tui.widgets import ContentPanel, DetailTextArea, FixedHeader, NavTree


class AgentOSApp(App[None]):
    TITLE = "agent-os"
    CSS = APP_CSS
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("n", "new_item", "new", show=False),
        Binding("d", "delete_item", "delete", show=False),
        Binding("r", "refresh_state", "Refresh", show=False),
    ]

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        self.store = ProjectStore(root)
        self.state: ProjectState | None = None
        self.selected: Nav | None = None
        for d in ("milestones", "tasks", "notes"):
            (root / d).mkdir(parents=True, exist_ok=True)

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield FixedHeader()
        with Horizontal():
            yield NavTree("agent-os", id="nav")
            yield ContentPanel(id="content")
        yield Footer()

    def on_mount(self) -> None:
        self._reload()

    # ── State ─────────────────────────────────────────────────────────────────

    def _reload(self) -> None:
        self.state = self.store.load()
        tree = self.query_one(NavTree)
        tree.populate(self.state, self.root)
        if self.selected:
            tree.focus_nav(self.selected)
            self._show_view()
        if self.state.errors:
            self.notify(
                f"{len(self.state.errors)} parse error(s) — check files",
                severity="warning",
                timeout=4,
            )

    def _item(self) -> Milestone | Task | Note | None:
        n = self.selected
        if not n or not self.state:
            return None
        s = self.state
        match n.kind:
            case "milestone":
                return next((m for m in s.milestones if m.id == n.id), None)
            case "task":
                return next((t for t in s.tasks if t.id == n.id), None)
            case "note":
                return next((nt for nt in s.notes if nt.id == n.id), None)
        return None

    def _item_path(self) -> Path | None:
        if not self.selected:
            return None
        if self.selected.kind == "agent":
            return self.root / "AGENT.md"
        if self.selected.kind == "skill":
            return self.root / "skills" / f"{self.selected.id}.md"
        return self.store.find_item_path(self.selected.kind, self.selected.id)

    def _update_footer_hints(self, nav: Nav | None) -> None:
        content = self.query_one(ContentPanel)
        show_new = (
            not content.is_editing
            and nav is not None
            and (
                nav.kind == "section"
                and nav.section in ("milestones", "tasks", "notes", "skills")
                or nav.kind in ("milestone", "task", "note", "skill")
            )
        )
        show_delete = (
            not content.is_editing
            and nav is not None
            and nav.kind in ("milestone", "task", "note")
        )
        for key, action, show in (
            ("n", "new_item", show_new),
            ("d", "delete_item", show_delete),
        ):
            bindings = self._bindings.key_to_bindings.get(key, [])
            for i, b in enumerate(bindings):
                if b.action == action:
                    bindings[i] = replace(b, show=show)
        self.screen.refresh_bindings()

    # ── Tree navigation ───────────────────────────────────────────────────────

    @on(Tree.NodeHighlighted, "#nav")
    def on_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        nav = cast(Nav | None, event.node.data)
        self._update_footer_hints(nav)
        content = self.query_one(ContentPanel)
        if content.is_editing:
            return
        if not nav or nav.kind == "section":
            self.selected = None
            content.clear()
            return
        self.selected = nav
        self._show_view()

    @on(Tree.NodeSelected, "#nav")
    def on_node_selected(self, event: Tree.NodeSelected) -> None:
        nav = cast(Nav | None, event.node.data)
        self._update_footer_hints(nav)
        content = self.query_one(ContentPanel)
        if not nav or nav.kind == "section":
            self.selected = None
            content.clear()
            return
        if content.is_editing:
            self._save_current()
        self.selected = nav
        self._show_view()

    # ── Edit mode ─────────────────────────────────────────────────────────────

    @on(NavTree.EditRequested)
    def on_edit_requested(self) -> None:
        if self.selected and self.selected.kind != "section":
            self._show_edit()

    @on(DetailTextArea.ExitRequested)
    def on_exit_requested(self) -> None:
        self._exit_edit_mode()

    def _exit_edit_mode(self) -> None:
        self._save_current()
        content = self.query_one(ContentPanel)
        content.remove_class("-editing")
        content.remove_class("-editing-struct")
        content.remove_class("-view-struct")
        self._show_view()
        self._update_footer_hints(self.selected)
        self.call_after_refresh(self.query_one(NavTree).focus)

    # ── View / Edit ───────────────────────────────────────────────────────────

    @work(exclusive=True)
    async def _show_view(self) -> None:
        if not self.selected:
            return
        content = self.query_one(ContentPanel)
        if content.is_editing:
            return
        if self.selected.kind in ("agent", "skill"):
            path = self._item_path()
            md = path.read_text(encoding="utf-8") if path and path.exists() else ""
            await content.show_view(md)
        else:
            item = self._item()
            if not item:
                return
            content.show_struct_view(item, self.selected.kind)

    def _show_edit(self) -> None:
        content = self.query_one(ContentPanel)
        if not self.selected:
            return
        if self.selected.kind in ("agent", "skill"):
            path = self._item_path()
            if not path or not path.exists():
                return
            content.enter_edit(path.read_text(encoding="utf-8"))
        else:
            item = self._item()
            if not item:
                return
            content.enter_structured_edit(item, self.selected.kind)

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
            self.state = self.store.load()
        except Exception as e:
            self.notify(str(e), severity="error", timeout=4)

    # ── Create / Delete ───────────────────────────────────────────────────────

    def action_new_item(self) -> None:
        content = self.query_one(ContentPanel)
        if content.is_editing or not self.state:
            return
        if self.selected and self.selected.kind in ("agent", "skill"):
            return

        if self.selected:
            section = self.selected.section
        else:
            cursor = self.query_one(NavTree).cursor_node
            nav = cast(Nav | None, cursor.data if cursor else None)
            section = nav.section if nav and nav.kind == "section" else "notes"

        today = date.today().isoformat()
        new_item: Milestone | Task | Note
        kind: str

        match section:
            case "milestones":
                new_item = Milestone(
                    id=self.store.milestones.next_id(),
                    title="New Milestone",
                    start_date=today,
                    end_date="",
                )
                self.store.milestones.save(new_item)
                kind = "milestone"
            case "tasks":
                new_item = Task(
                    id=self.store.tasks.next_id(),
                    title="New Task",
                    created_date=today,
                )
                self.store.tasks.save(new_item)
                kind = "task"
            case _:
                new_item = Note(
                    id=self.store.notes.next_id(), title="New Note", date=today
                )
                self.store.notes.save(new_item)
                kind = "note"

        self.state = self.store.load()
        tree = self.query_one(NavTree)
        tree.populate(self.state, self.root)
        self.selected = Nav(kind, new_item.id, section)
        tree.focus_nav(self.selected)
        self._show_edit()

    def action_delete_item(self) -> None:
        content = self.query_one(ContentPanel)
        if (
            content.is_editing
            or not self.selected
            or self.selected.kind in ("section", "agent", "skill")
        ):
            return
        nav = self.selected
        item = self._item()
        name = getattr(item, "title", None) or getattr(item, "name", None) or nav.id

        tree = self.query_one(NavTree)
        section_leaves = [
            leaf.data
            for section in tree.root.children
            for leaf in section.children
            if isinstance(leaf.data, Nav)
            and leaf.data.kind in ("milestone", "task", "note")
            and leaf.data.section == nav.section
        ]
        idx = next((i for i, n in enumerate(section_leaves) if n.id == nav.id), None)
        if idx is not None and len(section_leaves) > 1:
            next_nav: Nav = (
                section_leaves[idx + 1]
                if idx + 1 < len(section_leaves)
                else section_leaves[idx - 1]
            )
        else:
            next_nav = Nav("section", "", nav.section)

        self._confirm_and_delete(nav, name, next_nav)

    @work
    async def _confirm_and_delete(
        self, nav: Nav, name: str, next_nav: Nav | None
    ) -> None:
        if not await self.push_screen_wait(ConfirmDeleteScreen(name)):
            return
        deleted = False
        match nav.kind:
            case "milestone":
                deleted = self.store.milestones.delete(nav.id)
            case "task":
                deleted = self.store.tasks.delete(nav.id)
            case "note":
                deleted = self.store.notes.delete(nav.id)
        if deleted:
            self.selected = next_nav if next_nav and next_nav.kind != "section" else None
            self._reload()
            self.notify("Deleted", severity="warning", timeout=2)
            if next_nav:
                self.query_one(NavTree).focus_nav(next_nav)
                if next_nav.kind != "section":
                    self._show_view()

    # ── Misc ──────────────────────────────────────────────────────────────────

    def action_refresh_state(self) -> None:
        self._reload()
        self.notify("Refreshed", severity="information", timeout=2)
