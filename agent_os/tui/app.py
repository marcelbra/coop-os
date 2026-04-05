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

from agent_os import parser
from agent_os.models import PMS, Milestone, Note, ProjectState, Role, Task
from agent_os.tui.confirm_delete import ConfirmDeleteScreen
from agent_os.tui.nav import Nav
from agent_os.tui.render import to_md
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
        self.state: ProjectState | None = None
        self.selected: Nav | None = None
        for d in ("context/roles", "milestones", "tasks", "notes"):
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
        self.state = parser.read_project(self.root)
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

    def _item(self) -> PMS | Role | Milestone | Task | Note | None:
        n = self.selected
        if not n or not self.state:
            return None
        s = self.state
        match n.kind:
            case "pms":
                return s.pms
            case "role":
                return next((r for r in s.roles if r.id == n.id), None)
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
        return parser.find_item_path(self.root, self.selected.kind, self.selected.id)

    def _update_footer_hints(self, nav: Nav | None) -> None:
        content = self.query_one(ContentPanel)
        show_new = (
            not content.is_editing
            and nav is not None
            and (
                nav.kind == "section"
                and nav.section in ("context", "milestones", "tasks", "notes", "skills")
                or nav.kind in ("pms", "role", "milestone", "task", "note", "skill")
            )
        )
        show_delete = (
            not content.is_editing
            and nav is not None
            and nav.kind in ("role", "milestone", "task", "note")
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
        self.query_one(ContentPanel).remove_class("-editing")
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
        else:
            item = self._item()
            if not item:
                return
            md = to_md(item, self.selected.kind)
        await content.show_view(md)

    def _show_edit(self) -> None:
        path = self._item_path()
        if not path or not path.exists():
            return
        self.query_one(ContentPanel).enter_edit(
            path.read_text(encoding="utf-8")
        )

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
            self.state = parser.read_project(self.root)
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
        new_item: Role | Milestone | Task | Note
        kind: str

        match section:
            case "context":
                new_item = Role(
                    id=parser.next_role_id(self.root),
                    name="New Role",
                    emoji="⭐",
                    title="",
                )
                parser.write_role(self.root, new_item)
                kind = "role"
            case "milestones":
                first_role = self.state.roles[0].id if self.state.roles else ""
                new_item = Milestone(
                    id=parser.next_milestone_id(self.root),
                    title="New Milestone",
                    role=first_role,
                    start_date=today,
                    end_date="",
                )
                parser.write_milestone(self.root, new_item)
                kind = "milestone"
            case "tasks":
                new_item = Task(
                    id=parser.next_task_id(self.root),
                    title="New Task",
                    created_date=today,
                )
                parser.write_task(self.root, new_item)
                kind = "task"
            case _:
                new_item = Note(
                    id=parser.next_note_id(self.root), title="New Note", date=today
                )
                parser.write_note(self.root, new_item)
                kind = "note"

        self.state = parser.read_project(self.root)
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
            or self.selected.kind in ("section", "pms", "agent", "skill")
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
            and leaf.data.kind in ("role", "milestone", "task", "note")
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
            case "role":
                deleted = parser.delete_role(self.root, nav.id)
            case "milestone":
                deleted = parser.delete_milestone(self.root, nav.id)
            case "task":
                deleted = parser.delete_task(self.root, nav.id)
            case "note":
                deleted = parser.delete_note(self.root, nav.id)
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
