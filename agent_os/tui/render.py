from __future__ import annotations

from typing import cast

from agent_os.models import Milestone, Note, Task
from agent_os.tui.widgets.config import SCANNED_ICONS


def to_md(item: Milestone | Task | Note, kind: str) -> str:
    match kind:
        case "milestone":
            ms = cast(Milestone, item)
            return (
                f"# {ms.title}\n\n"
                f"| | |\n|:--|:--|\n"
                f"| id | `{ms.id}` |\n"
                f"| start | {ms.start_date} |\n"
                f"| end | {ms.end_date} |\n"
                f"| status | **{ms.status}** |\n\n"
                f"---\n\n{ms.description}"
            )
        case "task":
            task = cast(Task, item)
            labels = task.label if task.label else "—"
            deps = ", ".join(task.dependencies) if task.dependencies else "—"
            return (
                f"# {task.title}\n\n"
                f"| | |\n|:--|:--|\n"
                f"| id | `{task.id}` |\n"
                f"| status | **{task.status}** |\n"
                f"| milestone | {task.milestone or '—'} |\n"
                f"| labels | {labels} |\n"
                f"| depends | {deps} |\n"
                f"| created | {task.created_date} |\n\n"
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
