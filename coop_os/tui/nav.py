from __future__ import annotations

from dataclasses import dataclass

_TREE_WIDTH = 30
_LABEL_MAX = 22


def truncate_label(s: str) -> str:
    """Truncate a tree label to prevent horizontal overflow."""
    return s if len(s) <= _LABEL_MAX else s[: _LABEL_MAX - 1] + "…"


@dataclass
class Nav:
    kind: str  # milestone | task | note | section | agent | skill | group | separator
    id: str
    section: str  # milestones | tasks | notes | skills | ""
