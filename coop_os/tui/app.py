from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Tree

from coop_os.backend.models import Doc, Milestone, Note, ProjectState, Role, Skill, Task
from coop_os.backend.store import ProjectStore
from coop_os.tui.confirm_delete import ConfirmDeleteScreen
from coop_os.tui.nav import Nav
from coop_os.tui.styles import CSS as APP_CSS
from coop_os.tui.widgets import ContentPanel, DetailTextArea, FixedHeader, NavTree, SelectInput, StructuredEditor

_SECTION_TO_KIND: dict[str, str] = {
    "roles": "role",
    "milestones": "milestone",
    "tasks": "task",
    "notes": "note",
    "docs": "doc",
    "skills": "skill",
}


class CoopOSApp(App[None]):
    TITLE = "coop-os"
    CSS = APP_CSS
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("n", "new_item", "new", show=False),
        Binding("ctrl+n", "new_subtask", "new subtask", show=False),
        Binding("d", "delete_item", "delete", show=False),
        Binding("r", "refresh_state", "Refresh", show=False),
    ]

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        self.store = ProjectStore(root)
        self.state: ProjectState | None = None
        self.selected: Nav | None = Nav("section", "", "docs")

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield FixedHeader()
        with Horizontal():
            yield NavTree("coop-os", id="nav")
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

    def _item(self) -> Role | Milestone | Task | Note | Doc | Skill | None:
        n = self.selected
        if not n or not self.state:
            return None
        s = self.state
        match n.kind:
            case "role":
                return next((r for r in s.roles if r.id == n.id), None)
            case "milestone":
                return next((m for m in s.milestones if m.id == n.id), None)
            case "task":
                return next((t for t in s.tasks if t.id == n.id), None)
            case "note":
                return next((nt for nt in s.notes if nt.id == n.id), None)
            case "doc":
                return next((d for d in s.docs if d.id == n.id), None)
            case "skill":
                return next((sk for sk in s.skills if sk.id == n.id), None)
            case _:
                return None

    def _item_path(self) -> Path | None:
        if not self.selected:
            return None
        if self.selected.kind == "agent":
            return self.root / "coop_os" / "agent" / "AGENT.md"
        return self.store.find_item_path(self.selected.kind, self.selected.id)

    def _update_footer_hints(self, nav: Nav | None) -> None:
        content = self.query_one(ContentPanel)
        editing = content.is_editing

        new_kind: str | None = None
        if not editing and nav is not None:
            if nav.kind == "section" and nav.section in _SECTION_TO_KIND:
                new_kind = _SECTION_TO_KIND[nav.section]
            elif nav.kind in ("role", "milestone", "task", "note", "skill"):
                new_kind = nav.kind

        show_new = new_kind is not None
        show_subtask = not editing and nav is not None and nav.kind == "task"
        deletable = {"role", "milestone", "task", "note", "doc", "skill"}
        show_delete = not editing and nav is not None and nav.kind in deletable

        hint_updates: list[tuple[str, str, bool, str | None]] = [
            ("n", "new_item", show_new, f"new {new_kind}" if new_kind else None),
            ("ctrl+n", "new_subtask", show_subtask, None),
            ("d", "delete_item", show_delete, None),
        ]
        for key, action, show, desc in hint_updates:
            bindings = self._bindings.key_to_bindings.get(key, [])
            for i, b in enumerate(bindings):
                if b.action == action:
                    if desc is not None:
                        bindings[i] = replace(b, show=show, description=desc)
                    else:
                        bindings[i] = replace(b, show=show)
        self.screen.refresh_bindings()

    # ── Tree navigation ───────────────────────────────────────────────────────

    @on(Tree.NodeHighlighted, "#nav")
    def on_node_highlighted(self, event: Tree.NodeHighlighted[Nav | None]) -> None:
        nav = event.node.data
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
    def on_node_selected(self, event: Tree.NodeSelected[Nav | None]) -> None:
        nav = event.node.data
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
    def on_edit_requested(self, event: NavTree.EditRequested) -> None:
        self.selected = event.nav
        self._show_edit()

    @on(DetailTextArea.ExitRequested)
    def on_exit_requested(self) -> None:
        self._exit_edit_mode()

    @on(StructuredEditor.Changed)
    def on_structured_editor_changed(self) -> None:
        self._save_current()
        tree = self.query_one(NavTree)
        assert self.state is not None
        tree.populate(self.state, self.root)

    @on(SelectInput.ValueSelected)
    def on_select_value_selected(self) -> None:
        self._save_current()
        tree = self.query_one(NavTree)
        assert self.state is not None
        tree.populate(self.state, self.root)

    def _exit_edit_mode(self) -> None:
        self._save_current()
        content = self.query_one(ContentPanel)
        content.remove_class("-editing")
        content.remove_class("-editing-struct")
        content.remove_class("-view-struct")
        self._show_view()
        self._update_footer_hints(self.selected)
        tree = self.query_one(NavTree)
        assert self.state is not None
        tree.populate(self.state, self.root)
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
        if self.selected.kind == "agent":
            path = self._item_path()
            md = path.read_text(encoding="utf-8") if path and path.exists() else ""
            await content.show_view(md)
        else:
            item = self._item()
            if not item:
                return
            content.show_struct_view(item, self.selected.kind)
            # Re-focus NavTree: show_struct_view applies -view-struct which makes
            # StructuredEditor visible; its focusable children can steal focus.
            self.query_one(NavTree).focus()

    def _show_edit(self, select_all: bool = False) -> None:
        content = self.query_one(ContentPanel)
        if not self.selected:
            return
        if self.selected.kind == "agent":
            path = self._item_path()
            if not path or not path.exists():
                return
            agent_doc = SimpleNamespace(content=path.read_text(encoding="utf-8"))
            content.enter_structured_edit(agent_doc, "agent")
        else:
            item = self._item()
            if not item:
                return
            content.enter_structured_edit(item, self.selected.kind, select_all=select_all)

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
        if self.selected and self.selected.kind == "agent":
            return

        if self.selected:
            section = self.selected.section
        else:
            cursor = self.query_one(NavTree).cursor_node
            nav = cursor.data if cursor else None
            section = nav.section if nav and nav.kind == "section" else "notes"

        today = date.today().isoformat()
        new_item: Role | Milestone | Task | Note | Doc | Skill
        kind: str

        match section:
            case "roles":
                new_item = Role(
                    id=self.store.roles.next_id(),
                    title="New Role",
                )
                self.store.roles.save(new_item)
                kind = "role"
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
                parent: str | None = None
                if self.selected and self.selected.kind == "task":
                    current = next((t for t in self.state.tasks if t.id == self.selected.id), None)
                    parent = current.parent if current else None
                new_item = Task(
                    id=self.store.tasks.next_id(),
                    title="New Task",
                    start_date=today,
                    parent=parent,
                )
                self.store.tasks.save(new_item)
                kind = "task"
            case "docs":
                new_item = Doc(
                    id=self.store.docs.next_id(),
                    title="New Document",
                )
                self.store.docs.save(new_item)
                kind = "doc"
            case "skills":
                new_item = Skill(
                    id=self.store.skills.next_id(),
                    command="new-skill",
                )
                self.store.skills.save(new_item)
                kind = "skill"
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
        self._show_edit(select_all=True)

    def action_new_subtask(self) -> None:
        content = self.query_one(ContentPanel)
        if content.is_editing or not self.state:
            return
        if not self.selected or self.selected.kind != "task":
            return
        today = date.today().isoformat()
        new_item = Task(
            id=self.store.tasks.next_id(),
            title="New Task",
            start_date=today,
            parent=self.selected.id,
        )
        self.store.tasks.save(new_item)
        self.state = self.store.load()
        tree = self.query_one(NavTree)
        tree.populate(self.state, self.root)
        self.selected = Nav("task", new_item.id, "tasks")
        tree.focus_nav(self.selected)
        self._show_edit(select_all=True)

    def action_delete_item(self) -> None:
        content = self.query_one(ContentPanel)
        if (
            content.is_editing
            or not self.selected
            or self.selected.kind in ("section", "agent")
        ):
            return
        nav = self.selected
        item = self._item()
        name = getattr(item, "title", None) or getattr(item, "name", None) or nav.id

        next_nav = self._next_nav_after_delete(nav)
        self._confirm_and_delete(nav, name, next_nav)

    def _next_nav_after_delete(self, nav: Nav) -> Nav:
        """Return the Nav to focus after *nav* is deleted."""
        if nav.kind == "task" and self.state:
            deleted = next((t for t in self.state.tasks if t.id == nav.id), None)
            parent_id = deleted.parent if deleted else None
            siblings = [t for t in self.state.tasks if t.parent == parent_id]
            idx = next((i for i, t in enumerate(siblings) if t.id == nav.id), None)
            if idx is not None and len(siblings) > 1:
                sibling = siblings[idx + 1] if idx + 1 < len(siblings) else siblings[idx - 1]
                return Nav("task", sibling.id, "tasks")
            if parent_id:
                return Nav("task", parent_id, "tasks")
        else:
            tree = self.query_one(NavTree)
            section_leaves = [
                node.data
                for node in tree.iter_all_nodes(tree.root)
                if isinstance(node.data, Nav)
                and node.data.kind == nav.kind
                and node.data.section == nav.section
            ]
            idx = next((i for i, n in enumerate(section_leaves) if n.id == nav.id), None)
            if idx is not None and len(section_leaves) > 1:
                sibling = section_leaves[idx + 1] if idx + 1 < len(section_leaves) else section_leaves[idx - 1]
                return sibling
        return Nav("section", "", nav.section)

    @work
    async def _confirm_and_delete(
        self, nav: Nav, name: str, next_nav: Nav | None
    ) -> None:
        if not await self.push_screen_wait(ConfirmDeleteScreen(name)):
            return
        store_map = {
            "role": self.store.roles,
            "milestone": self.store.milestones,
            "task": self.store.tasks,
            "note": self.store.notes,
            "doc": self.store.docs,
            "skill": self.store.skills,
        }
        store = store_map.get(nav.kind)
        deleted = store.delete(nav.id) if store else False
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
