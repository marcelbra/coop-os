from __future__ import annotations

from typing import cast

from agent_os.backend.models import Milestone, Note, Role, Task
from agent_os.tui.widgets.config import SCANNED_ICONS


def to_md(item: Role | Milestone | Task | Note, kind: str) -> str:
    match kind:
        case "role":
            role = cast(Role, item)
            return (
                f"# {role.title}\n\n"
                f"| | |\n|:--|:--|\n"
                f"| id | `{role.id}` |\n"
                f"| status | **{role.status}** |\n\n"
                f"---\n\n{role.description}"
            )
        case "milestone":
            ms = cast(Milestone, item)
            return (
                f"# {ms.title}\n\n"
                f"| | |\n|:--|:--|\n"
                f"| id | `{ms.id}` |\n"
                f"| start | {ms.start_date} |\n"
                f"| end | {ms.end_date} |\n"
                f"| status | **{ms.status}** |\n"
                f"| role | {ms.role or '—'} |\n\n"
                f"---\n\n{ms.description}"
            )
        case "task":
            task = cast(Task, item)
            deps = ", ".join(task.dependencies) if task.dependencies else "—"
            return (
                f"# {task.title}\n\n"
                f"| | |\n|:--|:--|\n"
                f"| id | `{task.id}` |\n"
                f"| start | {task.start_date or '—'} |\n"
                f"| end | {task.end_date or '—'} |\n"
                f"| status | **{task.status}** |\n"
                f"| milestone | {task.milestone or '—'} |\n"
                f"| depends | {deps} |\n\n"
                f"---\n\n{task.description}"
            )
        case "note":
            note = cast(Note, item)
            scanned = f"yes {SCANNED_ICONS['true']}" if note.scanned else f"**no {SCANNED_ICONS['false']}**"
            return (
                f"# {note.title}\n\n"
                f"| | |\n|:--|:--|\n"
                f"| id | `{note.id}` |\n"
                f"| date | {note.date} |\n"
                f"| scanned | {scanned} |\n\n"
                f"---\n\n{note.content}"
            )
        case _:
            pass
    return ""
