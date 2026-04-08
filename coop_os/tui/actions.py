from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
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

    from coop_os.tui.state import StateManager

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

    sm: StateManager
    selected: Nav | None

    # CoopOSApp helpers
    def _sync_state(self) -> None: ...
    def _reload(self) -> None: ...
    def _item(self) -> Role | Milestone | Task | Note | Context | Skill | None: ...
    def _show_edit(self, select_all: bool = False) -> None: ...
    def _show_view(self) -> Worker[None]: ...
    def _update_right_hints(self) -> None: ...

    # ActionsMixin methods called cross-method (declared here so self: _CoopOSHost resolves them)
    def _next_nav_after_file_delete(self, nav: Nav) -> Nav: ...
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
        if content.is_editing or not self.sm.state:
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
                new_id = self.sm.store.roles.next_id()
                new_item = Role(id=new_id, title=f"Role {new_id.rsplit('-', 1)[-1]}")
                self.sm.store.roles.save(new_item)
                kind = "role"
            case "milestones":
                new_id = self.sm.store.milestones.next_id()
                new_item = Milestone(
                    id=new_id,
                    title=f"Milestone {new_id.rsplit('-', 1)[-1]}",
                    start_date=today,
                    end_date="",
                )
                self.sm.store.milestones.save(new_item)
                kind = "milestone"
            case "tasks":
                parent: str | None = None
                if self.selected and self.selected.kind == "task":
                    current = next((t for t in self.sm.state.tasks if t.id == self.selected.id), None)
                    parent = current.parent if current else None
                new_id = self.sm.store.tasks.next_id()
                new_item = Task(
                    id=new_id,
                    title=f"Task {new_id.rsplit('-', 1)[-1]}",
                    start_date=today,
                    parent=parent,
                )
                self.sm.store.tasks.save(new_item)
                kind = "task"
            case "contexts":
                new_id = self.sm.store.contexts.next_id()
                new_item = Context(id=new_id, title=f"Context {new_id.rsplit('-', 1)[-1]}")
                self.sm.store.contexts.save(new_item)
                kind = "context"
            case "skills":
                new_item = Skill(
                    id=self.sm.store.skills.next_id(),
                    command="new-skill",
                )
                self.sm.store.skills.save(new_item)
                kind = "skill"
            case _:
                new_id = self.sm.store.notes.next_id()
                new_item = Note(id=new_id, title=f"Note {new_id.rsplit('-', 1)[-1]}", date=today)
                self.sm.store.notes.save(new_item)
                kind = "note"

        self._sync_state()
        self.selected = Nav(kind, new_item.id, section)
        self.query_one(NavTree).focus_nav(self.selected)
        self._show_edit(select_all=True)

    def action_new_subtask(self: _CoopOSHost) -> None:
        content = self.query_one(ContentPanel)
        if content.is_editing or not self.sm.state:
            return
        if not self.selected or self.selected.kind != "task":
            return
        today = date.today().isoformat()
        new_id = self.sm.store.tasks.next_id()
        new_item = Task(
            id=new_id,
            title=f"Task {new_id.rsplit('-', 1)[-1]}",
            start_date=today,
            parent=self.selected.id,
        )
        self.sm.store.tasks.save(new_item)
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
        if nav.kind in ("task_file", "task_dir"):
            name = Path(nav.id).name
        else:
            item = self._item()
            name = getattr(item, "title", None) or getattr(item, "name", None) or nav.id

        next_nav = self._next_nav_after_delete(nav)
        self._confirm_and_delete(nav, name, next_nav)

    def _next_nav_after_file_delete(self: _CoopOSHost, nav: Nav) -> Nav:
        """Return the Nav to focus after a task_file or task_dir is deleted."""
        tree = self.query_one(NavTree)
        for node in tree.iter_all_nodes(tree.root):
            if not (isinstance(node.data, Nav) and node.data.id == nav.id and node.data.kind == nav.kind):
                continue
            parent_node = node.parent
            if parent_node is None:
                break
            siblings = [
                n for n in parent_node.children
                if isinstance(n.data, Nav) and n.data.kind in ("task_file", "task_dir")
            ]
            idx = next((i for i, n in enumerate(siblings) if isinstance(n.data, Nav) and n.data.id == nav.id), None)
            if idx is None:
                break
            if idx + 1 < len(siblings):
                d = siblings[idx + 1].data
                return d if isinstance(d, Nav) else Nav("section", "", "tasks")
            if idx > 0:
                d = siblings[idx - 1].data
                return d if isinstance(d, Nav) else Nav("section", "", "tasks")
            # Last child — go to parent; tree rebuild will close it if empty
            parent_data = parent_node.data
            if isinstance(parent_data, Nav) and parent_data.kind in ("task", "task_dir"):
                return parent_data
            break
        return Nav("section", "", "tasks")

    def _next_nav_after_delete(self: _CoopOSHost, nav: Nav) -> Nav:
        """Return the Nav to focus after *nav* is deleted."""
        if nav.kind in ("task_file", "task_dir"):
            return self._next_nav_after_file_delete(nav)
        if nav.kind == "task" and self.sm.state:
            deleted = next((t for t in self.sm.state.tasks if t.id == nav.id), None)
            parent_id = deleted.parent if deleted else None
            siblings = [t for t in self.sm.state.tasks if t.parent == parent_id]
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
        if nav.kind in ("task_file", "task_dir"):
            p = Path(nav.id)
            if p.is_file():
                p.unlink()
                deleted = True
            elif p.is_dir():
                shutil.rmtree(p)
                deleted = True
            else:
                deleted = False
        else:
            store = self.sm.store.store_for(nav.kind)
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
            setattr(self.sm, attr, result)
            self._reload()
            self._update_right_hints()

    @work
    async def action_filter_roles(self: _CoopOSHost) -> None:
        await self._open_filter("Filter Roles", RoleStatus, self.sm.role_filters, "role_filters")

    @work
    async def action_filter_milestones(self: _CoopOSHost) -> None:
        await self._open_filter("Filter Milestones", MilestoneStatus, self.sm.milestone_filters, "milestone_filters")

    @work
    async def action_filter_tasks(self: _CoopOSHost) -> None:
        await self._open_filter("Filter Tasks", TaskStatus, self.sm.task_filters, "task_filters")
