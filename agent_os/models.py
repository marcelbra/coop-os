from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    DONE = "done"
    CANCELLED = "cancelled"


class MilestoneStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Milestone(BaseModel):
    id: str
    title: str
    start_date: str = ""
    end_date: str = ""
    status: MilestoneStatus = MilestoneStatus.ACTIVE
    description: str = ""


class Task(BaseModel):
    id: str
    title: str
    status: TaskStatus = TaskStatus.TODO
    milestone: str | None = None
    label: str = ""
    dependencies: list[str] = []
    created_date: str = ""
    description: str = ""


class Note(BaseModel):
    id: str
    title: str
    date: str = ""
    scanned: bool = False
    content: str = ""


class Skill(BaseModel):
    id: str
    command: str
    content: str = ""


class ParseError(BaseModel):
    file: str
    error: str


class ProjectState(BaseModel):
    milestones: list[Milestone] = []
    tasks: list[Task] = []
    notes: list[Note] = []
    skills: list[Skill] = []
    errors: list[ParseError] = []
