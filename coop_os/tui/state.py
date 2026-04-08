from __future__ import annotations

from pathlib import Path

from coop_os.backend.models import (
    Context,
    Milestone,
    Note,
    ProjectState,
    Role,
    Skill,
    Task,
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
