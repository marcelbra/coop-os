from __future__ import annotations

from pathlib import Path

from coop_os.backend.models import (
    Context,
    Milestone,
    MilestoneStatus,
    Note,
    ProjectState,
    Role,
    RoleStatus,
    Skill,
    Status,
    Task,
    TaskStatus,
)
from coop_os.backend.store import ProjectStore
from coop_os.tui.nav import Nav
from coop_os.tui.widgets.config import AppConfig, read_config

_KIND_TO_COLLECTION: dict[str, str] = {
    "role": "roles",
    "milestone": "milestones",
    "task": "tasks",
    "note": "notes",
    "context": "contexts",
    "skill": "skills",
}


class StateManager:
    def __init__(self, store: ProjectStore, root: Path) -> None:
        self.store = store
        self.root = root
        self.state: ProjectState | None = None
        self.role_filters: set[str] = set()
        self.milestone_filters: set[str] = set()
        self.task_filters: set[str] = set()

    @staticmethod
    def _status_values(enum_type: Status) -> set[str]:
        return {s.value for s in enum_type}

    @staticmethod
    def _allowed_by(value: str | None, active_filter: set[str]) -> bool:
        """Return True when the filter is inactive or the value is explicitly included."""
        return not active_filter or value in active_filter

    @classmethod
    def _split_filter(cls, filters: set[str], status_enum: Status) -> tuple[set[str], set[str]]:
        """Partition a filter set into (status values, id values)."""
        statuses = cls._status_values(status_enum)
        return filters & statuses, filters - statuses

    @classmethod
    def _prune_to_reachable(cls, filters: set[str], status_enum: Status, reachable_ids: set[str]) -> set[str]:
        """Drop ID-based filter values no longer in reachable_ids; always keep status values."""
        return {v for v in filters if v in cls._status_values(status_enum) or v in reachable_ids}

    def visible_role_ids(self) -> set[str]:
        assert self.state
        status_filter, id_filter = self._split_filter(self.role_filters, RoleStatus)
        return {
            r.id for r in self.state.roles
            if self._allowed_by(r.status, status_filter) and self._allowed_by(r.id, id_filter)
        }

    def milestones_in_role_scope(self, visible_role_ids: set[str]) -> list[Milestone]:
        assert self.state
        if not self.role_filters:
            return list(self.state.milestones)
        return [m for m in self.state.milestones if m.role is None or m.role in visible_role_ids]

    def visible_milestone_ids(self, visible_role_ids: set[str]) -> set[str]:
        assert self.state
        status_filter, id_filter = self._split_filter(self.milestone_filters, MilestoneStatus)
        return {
            m.id for m in self.milestones_in_role_scope(visible_role_ids)
            if self._allowed_by(m.status, status_filter) and self._allowed_by(m.id, id_filter)
        }

    def prune_downstream_filters(self) -> None:
        """Remove downstream ID selections that no longer belong to a visible upstream item."""
        if not self.state:
            return

        visible_role_ids = self.visible_role_ids()

        if self.role_filters:
            reachable_milestones = {m.id for m in self.state.milestones if m.role is None or m.role in visible_role_ids}
            self.milestone_filters = self._prune_to_reachable(
                self.milestone_filters, MilestoneStatus, reachable_milestones
            )

        if self.role_filters or self.milestone_filters:
            self.task_filters &= self._status_values(TaskStatus)

    def load(self) -> ProjectState:
        """Load from disk. Returns the new state."""
        self.state = self.store.load()
        return self.state

    def cfg(self) -> AppConfig:
        return read_config(self.root)

    def item(self, nav: Nav | None) -> Role | Milestone | Task | Note | Context | Skill | None:
        """Look up the item for *nav* in current state."""
        if not nav or not self.state:
            return None
        attr = _KIND_TO_COLLECTION.get(nav.kind)
        if not attr:
            return None
        return next((i for i in getattr(self.state, attr) if i.id == nav.id), None)

    def task_dirs(self) -> dict[str, Path]:
        """Return a mapping of task_id -> task_dir_path for all tasks."""
        return self.store.tasks.all_task_dirs()

    def item_path(self, nav: Nav | None) -> Path | None:
        """Resolve disk path for the item pointed to by *nav*."""
        if not nav:
            return None
        if nav.kind == "agent":
            return self.root / "coop_os" / "agent" / "AGENT.md"
        if nav.kind == "task_file":
            return Path(nav.id)
        return self.store.find_item_path(nav.kind, nav.id)
