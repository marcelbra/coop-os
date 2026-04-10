from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

_TREE_WIDTH = 30
_LABEL_MAX = 22


def truncate_label(s: str) -> str:
    """Truncate a tree label to prevent horizontal overflow."""
    return s if len(s) <= _LABEL_MAX else s[: _LABEL_MAX - 1] + "…"


@dataclass
class Nav:
    kind: str  # role | milestone | task | note | context | skill | agent | section | task_file | task_dir
    id: str
    section: str  # roles | milestones | tasks | notes | contexts | skills | ""


DECORATIVE_NAV_KINDS = frozenset({"header", "sep"})
NON_CONTENT_NAV_KINDS = DECORATIVE_NAV_KINDS | frozenset({"root", "section"})


def is_decorative_nav(nav: Nav) -> bool:
    return nav.kind in DECORATIVE_NAV_KINDS


def is_content_nav(nav: Nav) -> bool:
    return nav.kind not in NON_CONTENT_NAV_KINDS


def choose_same_section_neighbor(
    previous_nav: Nav,
    previous_ids: Sequence[str],
    current_navs: Sequence[Nav],
) -> Nav | None:
    """Choose the best same-kind fallback using the previous visible order.

    Prefers the next surviving node in the old order, then the previous one.
    """
    if not is_content_nav(previous_nav):
        return None

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
