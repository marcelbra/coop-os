from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import cast

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer
from textual.widgets import Footer, Header, Markdown

from agent_os import parser
from agent_os.models import PMS, Milestone, Note, ProjectState, Role, Task
from agent_os.tui.nav import Nav, _t
from agent_os.tui.render import to_md
from agent_os.tui.styles import CSS as APP_CSS
from agent_os.tui.widgets import DetailTextArea, NavTree


class AgentOSApp(App[None]):
    TITLE = "agent-os"
    CSS = APP_CSS
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("n", "new_item", "new", show=False),
        Binding("d", "delete_item", "delete", show=False),
        Binding("ctrl+m", "toggle_mode", "Mode", show=False),
        Binding("r", "refresh", "Refresh", show=False),
    ]

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        self.state: ProjectState | None = None
        self.selected: Nav | None = None
        self.in_detail: bool = False

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield NavTree("agent-os", id="nav")
            yield ScrollableContainer(id="detail")
        yield Footer()

    def on_mount(self) -> None:
        self._reload()

    # ── State ─────────────────────────────────────────────────────────────────

    def _reload(self) -> None:
        self.state = parser.read_project(self.root)
        self._populate_tree()
        if self.selected:
            self._show_view()
        if self.state.errors:
            self.notify(f"{len(self.state.errors)} parse error(s) — check files", severity="warning", timeout=4)

    def _populate_tree(self) -> None:
        tree = self.query_one("#nav", NavTree)
        tree.clear()
        s = self.state
        if not s:
            return

        ctx = tree.root.add("Context", data=Nav("section", "", "context"), expand=False)
        if s.pms:
            ctx.add_leaf(_t("Personal Mission Statement"), data=Nav("pms", "pms", "context"))
        for r in s.roles:
            emoji = r.emoji.replace("\uFE0F", "").replace("\uFE0E", "")
            ctx.add_leaf(_t(f"{emoji} {r.name}"), data=Nav("role", r.id, "context"))

        _ms_icon = {"active": "●", "completed": "✓", "cancelled": "✗"}
        ms_node = tree.root.add("Milestones", data=Nav("section", "", "milestones"), expand=False)
        for m in s.milestones:
            ms_node.add_leaf(_t(f"{_ms_icon.get(m.status, '·')} {m.title}"), data=Nav("milestone", m.id, "milestones"))

        _task_icon = {"todo": "·", "in_progress": "▶", "waiting": "…", "done": "✓", "cancelled": "✗"}
        tasks_node = tree.root.add("Tasks", data=Nav("section", "", "tasks"), expand=False)
        for t in s.tasks:
            tasks_node.add_leaf(_t(f"{_task_icon.get(t.status, '·')} {t.title}"), data=Nav("task", t.id, "tasks"))

        notes_node = tree.root.add("Notes", data=Nav("section", "", "notes"), expand=False)
        for n in s.notes:
            icon = "●" if not n.scanned else "·"
            notes_node.add_leaf(_t(f"{icon} {n.title}"), data=Nav("note", n.id, "notes"))

        skills_dir = self.root / "skills"
        if skills_dir.exists():
            skills_node = tree.root.add("Skills", data=Nav("section", "", "skills"), expand=False)
            for p in sorted(skills_dir.glob("*.md")):
                skills_node.add_leaf(_t(p.stem), data=Nav("skill", p.stem, "skills"))

        if (self.root / "AGENT.md").exists():
            tree.root.add_leaf("AGENT.md", data=Nav("agent", "agent", ""))

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
        show_new = (
            not self.in_detail
            and nav is not None
            and (
                (nav.kind == "section" and nav.section in ("context", "milestones", "tasks", "notes", "skills"))
                or nav.kind in ("pms", "role", "milestone", "task", "note", "skill")
            )
        )
        show_delete = (
            not self.in_detail
            and nav is not None
            and nav.kind in ("role", "milestone", "task", "note")
        )
        for key, action, show in (("n", "new_item", show_new), ("d", "delete_item", show_delete)):
            bindings = self._bindings.key_to_bindings.get(key, [])
            for i, b in enumerate(bindings):
                if b.action == action:
                    bindings[i] = replace(b, show=show)
        self.screen.refresh_bindings()

    # ── Tree navigation ───────────────────────────────────────────────────────

    @on(NavTree.NodeHighlighted, "#nav")
    def on_node_highlighted(self, event: NavTree.NodeHighlighted) -> None:
        nav = cast(Nav | None, event.node.data)
        self._update_footer_hints(nav)
        if self.in_detail:
            return
        if not nav or nav.kind == "section":
            self.selected = None
            self._clear_detail()
            return
        self.selected = nav
        self._show_view()

    @on(NavTree.NodeSelected, "#nav")
    def on_node_selected(self, event: NavTree.NodeSelected) -> None:
        nav = cast(Nav | None, event.node.data)
        self._update_footer_hints(nav)
        if not nav or nav.kind == "section":
            self.selected = None
            self._clear_detail()
            return
        if self.in_detail:
            self._save_current()
            self.in_detail = False
        self.selected = nav
        self._show_view()

    # ── View / Edit mode ──────────────────────────────────────────────────────

    @work(exclusive=True)
    async def _clear_detail(self) -> None:
        detail = self.query_one("#detail", ScrollableContainer)
        await detail.remove_children()

    @work(exclusive=True)
    async def _show_view(self) -> None:
        if not self.selected:
            return
        if self.selected.kind in ("agent", "skill"):
            path = self._item_path()
            md = path.read_text(encoding="utf-8") if path and path.exists() else ""
        else:
            item = self._item()
            if not item:
                return
            md = to_md(item, self.selected.kind)
        detail = self.query_one("#detail", ScrollableContainer)
        await detail.remove_children()
        await detail.mount(Markdown(md))

    @work(exclusive=True)
    async def _show_edit(self) -> None:
        path = self._item_path()
        if not path or not path.exists():
            return
        raw = path.read_text(encoding="utf-8")
        detail = self.query_one("#detail", ScrollableContainer)
        await detail.remove_children()
        ta = DetailTextArea(raw, id="f-body", language="markdown", theme="vscode_dark")
        await detail.mount(ta)
        ta.move_cursor((0, 0))
        ta.focus()

    def action_jump_to_detail(self) -> None:
        if not self.selected or self.selected.kind == "section":
            return
        self.in_detail = True
        self._show_edit()

    def action_leave_detail(self) -> None:
        if not self.in_detail:
            return
        self._save_current()
        self.in_detail = False
        self._show_view()
        self.call_after_refresh(self.query_one("#nav", NavTree).focus)

    def action_toggle_mode(self) -> None:
        if self.in_detail:
            self.action_leave_detail()
        else:
            self.action_jump_to_detail()

    # ── Auto-save ─────────────────────────────────────────────────────────────

    def _save_current(self) -> None:
        if not self.selected or not self.in_detail:
            return
        path = self._item_path()
        if not path:
            return
        try:
            ta = self.query_one("#f-body", DetailTextArea)
            path.write_text(ta.text, encoding="utf-8")
            self.state = parser.read_project(self.root)
        except Exception as e:
            self.notify(str(e), severity="error", timeout=4)

    # ── Create / Delete ───────────────────────────────────────────────────────

    def action_new_item(self) -> None:
        if self.in_detail or not self.state or (self.selected and self.selected.kind in ("agent", "skill")):
            return
        section = self.selected.section if self.selected else "notes"
        today = date.today().isoformat()
        new_item: Role | Milestone | Task | Note
        kind: str

        match section:
            case "context":
                new_item = Role(id=parser.next_role_id(self.root), name="New Role", emoji="⭐", title="")
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
                new_item = Task(id=parser.next_task_id(self.root), title="New Task", created_date=today)
                parser.write_task(self.root, new_item)
                kind = "task"
            case _:  # notes
                new_item = Note(id=parser.next_note_id(self.root), title="New Note", date=today)
                parser.write_note(self.root, new_item)
                kind = "note"

        self.state = parser.read_project(self.root)
        self._populate_tree()
        self.selected = Nav(kind, new_item.id, section)
        self.in_detail = True
        self._show_edit()

    def action_delete_item(self) -> None:
        if self.in_detail or not self.selected or self.selected.kind in ("section", "pms", "agent", "skill"):
            return
        nav = self.selected
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
            self.selected = None
            self._reload()
            self.notify("Deleted", severity="warning", timeout=2)

    # ── Misc ──────────────────────────────────────────────────────────────────

    def action_refresh(self) -> None:
        self._reload()
        self.notify("Refreshed", severity="information", timeout=2)
