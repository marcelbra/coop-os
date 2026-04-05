"""Backward-compatible wrappers — prefer using ProjectStore directly."""
from __future__ import annotations

from pathlib import Path

from agent_os.models import Milestone, Note, ParseError, ProjectState, Task
from agent_os.store import ProjectStore


def read_project(root: Path) -> ProjectState:
    return ProjectStore(root).load()


def find_item_path(root: Path, kind: str, item_id: str) -> Path | None:
    return ProjectStore(root).find_item_path(kind, item_id)


def read_milestones(root: Path) -> tuple[list[Milestone], list[ParseError]]:
    return ProjectStore(root).milestones.load_all()


def read_tasks(root: Path) -> tuple[list[Task], list[ParseError]]:
    return ProjectStore(root).tasks.load_all()


def read_notes(root: Path) -> tuple[list[Note], list[ParseError]]:
    return ProjectStore(root).notes.load_all()


def write_milestone(root: Path, ms: Milestone) -> None:
    ProjectStore(root).milestones.save(ms)


def write_task(root: Path, task: Task) -> None:
    ProjectStore(root).tasks.save(task)


def write_note(root: Path, note: Note) -> None:
    ProjectStore(root).notes.save(note)


def delete_milestone(root: Path, ms_id: str) -> bool:
    return ProjectStore(root).milestones.delete(ms_id)


def delete_task(root: Path, task_id: str) -> bool:
    return ProjectStore(root).tasks.delete(task_id)


def delete_note(root: Path, note_id: str) -> bool:
    return ProjectStore(root).notes.delete(note_id)


def next_milestone_id(root: Path) -> str:
    return ProjectStore(root).milestones.next_id()


def next_task_id(root: Path) -> str:
    return ProjectStore(root).tasks.next_id()


def next_note_id(root: Path) -> str:
    return ProjectStore(root).notes.next_id()
