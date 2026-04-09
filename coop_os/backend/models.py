from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class RoleStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


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


Status = type[RoleStatus] | type[MilestoneStatus] | type[TaskStatus]


class Role(BaseModel):
    id: str
    title: str
    status: RoleStatus = RoleStatus.ACTIVE
    description: str = ""


class Milestone(BaseModel):
    id: str
    title: str
    start_date: str = ""
    end_date: str = ""
    status: MilestoneStatus = MilestoneStatus.ACTIVE
    role: str | None = None
    description: str = ""


class Task(BaseModel):
    id: str
    title: str
    start_date: str = ""
    end_date: str = ""
    status: TaskStatus = TaskStatus.TODO
    milestone: str | None = None
    parent: str | None = None
    description: str = ""


class Note(BaseModel):
    id: str
    title: str
    date: str = ""
    scanned: bool = False
    content: str = ""


class Context(BaseModel):
    id: str
    title: str
    content: str = ""


class Skill(BaseModel):
    name: str
    description: str = ""
    content: str = ""

    @property
    def id(self) -> str:
        return self.name


class ParseError(BaseModel):
    file: str
    error: str


class ProjectState(BaseModel):
    roles: list[Role] = []
    milestones: list[Milestone] = []
    tasks: list[Task] = []
    notes: list[Note] = []
    contexts: list[Context] = []
    skills: list[Skill] = []
    errors: list[ParseError] = []
