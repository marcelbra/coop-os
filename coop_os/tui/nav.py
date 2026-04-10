from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

_TREE_WIDTH = 30
_LABEL_MAX = 22


def truncate_label(s: str) -> str:
    """Truncate a tree label to prevent horizontal overflow."""
    return s if len(s) <= _LABEL_MAX else s[: _LABEL_MAX - 1] + "…"


ContentKind = Literal["role", "milestone", "task", "note", "context", "skill"]
FileKind = Literal["agent", "task_file", "task_dir"]
StructKind = Literal["section", "root", "header", "sep"]


@dataclass
class ContentNav:
    kind: ContentKind
    id: str    # entity ID, e.g. "task-1"
    section: str  # "roles" | "milestones" | "tasks" | "notes" | "contexts" | "skills"


@dataclass
class FileNav:
    kind: FileKind
    path: Path  # filesystem path


@dataclass
class StructuralNav:
    kind: StructKind
    section: str = field(default="")  # only meaningful for kind="section"


Nav = ContentNav | FileNav | StructuralNav


def is_decorative_nav(nav: Nav) -> bool:
    return isinstance(nav, StructuralNav) and nav.kind in ("header", "sep")


def is_content_nav(nav: Nav) -> bool:
    return isinstance(nav, ContentNav)


def nav_from_parts(kind: str, id_or_path: str, section: str) -> Nav:
    """Reconstruct a Nav from its serialized string parts (used for session restore)."""
    if kind in ("role", "milestone", "task", "note", "context", "skill"):
        return ContentNav(kind, id_or_path, section)
    if kind in ("agent", "task_file", "task_dir"):
        return FileNav(kind, Path(id_or_path))
    if kind in ("section", "root", "header", "sep"):
        return StructuralNav(kind, section)
    raise ValueError(f"nav_from_parts: unknown kind {kind!r}")


def nav_to_parts(nav: Nav) -> tuple[str, str, str]:
    """Serialize a Nav to (kind, id_or_path, section) strings (used for session save)."""
    if isinstance(nav, ContentNav):
        return nav.kind, nav.id, nav.section
    if isinstance(nav, FileNav):
        return nav.kind, str(nav.path), ""
    return nav.kind, "", nav.section


def choose_file_neighbor(
    current_path: str,
    previous_paths: Sequence[str],
    surviving_paths: Sequence[str],
) -> str | None:
    """Choose the nearest surviving file path from the previous order.

    Prefers the next surviving path in the old order, then the previous one.
    """
    if not surviving_paths:
        return None
    if current_path in surviving_paths:
        return current_path
    if current_path not in previous_paths:
        return surviving_paths[0]
    index = previous_paths.index(current_path)
    surviving_set = set(surviving_paths)
    for p in previous_paths[index + 1:]:
        if p in surviving_set:
            return p
    for p in reversed(previous_paths[:index]):
        if p in surviving_set:
            return p
    return None


def choose_same_section_neighbor(
    previous_nav: ContentNav,
    previous_ids: Sequence[str],
    current_navs: Sequence[ContentNav],
) -> ContentNav | None:
    """Choose the best same-kind fallback using the previous visible order.

    Prefers the next surviving node in the old order, then the previous one.
    """
    matching = [
        nav for nav in current_navs
        if nav.kind == previous_nav.kind and nav.section == previous_nav.section
    ]
    if not matching:
        return None

    exact = next((nav for nav in matching if nav.id == previous_nav.id), None)
    if exact is not None:
        return exact

    try:
        index = previous_ids.index(previous_nav.id)
    except ValueError:
        return matching[0]

    current_by_id = {nav.id: nav for nav in matching}
    for candidate_id in previous_ids[index + 1:]:
        candidate = current_by_id.get(candidate_id)
        if candidate is not None:
            return candidate
    for candidate_id in reversed(previous_ids[:index]):
        candidate = current_by_id.get(candidate_id)
        if candidate is not None:
            return candidate
    return None
