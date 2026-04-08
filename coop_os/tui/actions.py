from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from textual import work

from coop_os.backend.models import (
    Context,
    Milestone,
    MilestoneStatus,
    Note,
    Role,
    RoleStatus,
    Skill,
    Task,
    TaskStatus,
)
from coop_os.tui.confirm_delete import ConfirmDeleteScreen
from coop_os.tui.filter_screen import FilterScreen
from coop_os.tui.nav import Nav
from coop_os.tui.widgets import ContentPanel, NavTree

if TYPE_CHECKING:
    from textual.app import App
    from textual.worker import Worker

    from coop_os.backend.models import ProjectState
    from coop_os.backend.store import ProjectStore

    _HostBase = App[None]
else:
    _HostBase = object


class _CoopOSHost(_HostBase):
    """Concrete base class that declares the CoopOSApp interface ActionsMixin depends on.

    Stub methods here are overridden by CoopOSApp; the declarations give the type
    checker a precise view of what `self` has access to inside ActionsMixin. At
    runtime the MRO puts CoopOSApp before this class, so the stubs are never called.

    Textual App methods (query_one, push_screen_wait, notify, …) are covered by
    __getattr__ because re-declaring their overloaded signatures would conflict with
    App's own definitions.
    """

    store: ProjectStore
    state: ProjectState | None
    selected: Nav | None
    role_filters: set[str]
    milestone_filters: set[str]
    task_filters: set[str]

    # CoopOSApp helpers
    def _sync_state(self) -> None: ...
    def _reload(self) -> None: ...
    def _item(self) -> Role | Milestone | Task | Note | Context | Skill | None: ...
    def _show_edit(self, select_all: bool = False) -> None: ...
    def _show_view(self) -> Worker[None]: ...
    def _update_right_hints(self) -> None: ...

    # ActionsMixin methods called cross-method (declared here so self: _CoopOSHost resolves them)
    def _next_nav_after_delete(self, nav: Nav) -> Nav: ...
    def _confirm_and_delete(self, nav: Nav, name: str, next_nav: Nav | None) -> Worker[None]: ...
    async def _open_filter(
        self,
        title: str,
        status_enum: type[RoleStatus | MilestoneStatus | TaskStatus],
        current: set[str],
        attr: str,
    ) -> None: ...

class ActionsMixin(_CoopOSHost):
    """CRUD and filter actions for CoopOSApp.

    Extracted to keep app.py focused on layout, state, and event wiring.
    """

    # ── Create / Delete ───────────────────────────────────────────────────────

    def action_new_item(self: _CoopOSHost) -> None:
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
        new_item: Role | Milestone | Task | Note | Context | Skill
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
            case "contexts":
                new_item = Context(
                    id=self.store.contexts.next_id(),
                    title="New Document",
                )
                self.store.contexts.save(new_item)
                kind = "context"
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

        self._sync_state()
        self.selected = Nav(kind, new_item.id, section)
        self.query_one(NavTree).focus_nav(self.selected)
        self._show_edit(select_all=True)

    def action_new_subtask(self: _CoopOSHost) -> None:
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
        self._sync_state()
        self.selected = Nav("task", new_item.id, "tasks")
        self.query_one(NavTree).focus_nav(self.selected)
        self._show_edit(select_all=True)

    def action_delete_item(self: _CoopOSHost) -> None:
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

    def _next_nav_after_delete(self: _CoopOSHost, nav: Nav) -> Nav:
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
        self: _CoopOSHost, nav: Nav, name: str, next_nav: Nav | None
    ) -> None:
        if not await self.push_screen_wait(ConfirmDeleteScreen(name)):
            return
        store = self.store.store_for(nav.kind)
        deleted = store.delete(nav.id) if store else False
        if deleted:
            self.selected = next_nav if next_nav and next_nav.kind != "section" else None
            self._reload()
            self.notify("Deleted", severity="warning", timeout=2)
            if next_nav:
                self.query_one(NavTree).focus_nav(next_nav)
                if next_nav.kind != "section":
                    self._show_view()

    # ── Filter ────────────────────────────────────────────────────────────────

    async def _open_filter(
        self: _CoopOSHost,
        title: str,
        status_enum: type[RoleStatus | MilestoneStatus | TaskStatus],
        current: set[str],
        attr: str,
    ) -> None:
        if self.query_one(ContentPanel).is_editing:
            return
        options = [(s.value, s.value.replace("_", " ").title()) for s in status_enum]
        result = await self.push_screen_wait(FilterScreen(title, options, current))
        if result is not None:
            setattr(self, attr, result)
            self._reload()
            self._update_right_hints()

    @work
    async def action_filter_roles(self: _CoopOSHost) -> None:
        await self._open_filter("Filter Roles", RoleStatus, self.role_filters, "role_filters")

    @work
    async def action_filter_milestones(self: _CoopOSHost) -> None:
        await self._open_filter("Filter Milestones", MilestoneStatus, self.milestone_filters, "milestone_filters")

    @work
    async def action_filter_tasks(self: _CoopOSHost) -> None:
        await self._open_filter("Filter Tasks", TaskStatus, self.task_filters, "task_filters")
