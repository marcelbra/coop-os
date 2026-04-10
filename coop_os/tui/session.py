from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict, cast

SESSION_FILE = ".coop-os-session.json"


class _SessionData(TypedDict, total=False):
    role_filters: list[str]
    milestone_filters: list[str]
    task_filters: list[str]
    expanded_sections: list[str]
    expanded_tasks: list[str]
    expanded_dirs: list[str]
    selected_kind: str
    selected_id: str
    selected_section: str


@dataclass
class SessionState:
    role_filters: set[str] = field(default_factory=set)
    milestone_filters: set[str] = field(default_factory=set)
    task_filters: set[str] = field(default_factory=set)
    expanded_sections: set[str] = field(default_factory=set)
    expanded_tasks: set[str] = field(default_factory=set)
    expanded_dirs: set[str] = field(default_factory=set)
    selected_kind: str = "section"
    selected_id: str = ""
    selected_section: str = "roles"


def load_session(root: Path) -> SessionState:
    path = root / SESSION_FILE
    if not path.exists():
        return SessionState()
    try:
        data = cast(_SessionData, json.loads(path.read_text(encoding="utf-8")))
        return SessionState(
            role_filters=set(data.get("role_filters", [])),
            milestone_filters=set(data.get("milestone_filters", [])),
            task_filters=set(data.get("task_filters", [])),
            expanded_sections=set(data.get("expanded_sections", [])),
            expanded_tasks=set(data.get("expanded_tasks", [])),
            expanded_dirs=set(data.get("expanded_dirs", [])),
            selected_kind=data.get("selected_kind", "section"),
            selected_id=data.get("selected_id", ""),
            selected_section=data.get("selected_section", "roles"),
        )
    except Exception:
        return SessionState()


def save_session(root: Path, state: SessionState) -> None:
    path = root / SESSION_FILE
    try:
        data = {
            "role_filters": sorted(state.role_filters),
            "milestone_filters": sorted(state.milestone_filters),
            "task_filters": sorted(state.task_filters),
            "expanded_sections": sorted(state.expanded_sections),
            "expanded_tasks": sorted(state.expanded_tasks),
            "expanded_dirs": sorted(state.expanded_dirs),
            "selected_kind": state.selected_kind,
            "selected_id": state.selected_id,
            "selected_section": state.selected_section,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass
