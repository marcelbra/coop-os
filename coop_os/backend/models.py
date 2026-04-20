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


class RecurringTaskStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class OccurrenceStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    SKIPPED = "skipped"
    MISSED = "missed"


class TimePolicy(StrEnum):
    ALL_DAY = "all_day"
    TIMED = "timed"


class SyncState(StrEnum):
    NONE = "none"
    SYNCED = "synced"
    DIRTY = "dirty"
    DRIFT = "drift"
    ERROR = "error"


Status = (
    type[RoleStatus]
    | type[MilestoneStatus]
    | type[TaskStatus]
    | type[RecurringTaskStatus]
    | type[OccurrenceStatus]
)


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


class Attachment(BaseModel):
    filename: str  # as stored on disk (may differ from original if renamed)
    added_at: str  # ISO-8601 datetime, e.g. "2026-04-10T14:30:00"


class Task(BaseModel):
    id: str
    title: str
    start_date: str = ""
    end_date: str = ""
    status: TaskStatus = TaskStatus.TODO
    milestone: str | None = None
    parent: str | None = None
    description: str = ""
    attachments: list[Attachment] = []
    # Time policy — either all-day or a timed block with duration + IANA timezone.
    time_policy: TimePolicy = TimePolicy.ALL_DAY
    start_time: str = ""         # "HH:MM" 24h; empty when all_day
    duration_minutes: int = 0    # 0 when all_day
    timezone: str = ""           # IANA tz; empty = workspace default
    # Google Calendar sync — opt-in per task; coop-os is SSOT.
    sync_to_calendar: bool = False
    calendar_id: str = ""
    calendar_event_id: str = ""
    sync_state: SyncState = SyncState.NONE
    last_synced_at: str = ""
    last_synced_hash: str = ""


class RecurringTask(BaseModel):
    id: str                                           # "rtask-{n}"
    title: str
    status: RecurringTaskStatus = RecurringTaskStatus.ACTIVE
    role: str | None = None                           # "role-{n}" (optional)
    milestone: str | None = None                      # "milestone-{n}" (primary link)
    description: str = ""
    # Time policy — mirrors Task.
    time_policy: TimePolicy = TimePolicy.ALL_DAY
    start_time: str = ""
    duration_minutes: int = 0
    timezone: str = ""
    # Recurrence — RRULE authoritative, structured conveniences for common edits.
    rrule: str = ""              # iCal RRULE string (without the "RRULE:" prefix)
    dtstart: str = ""            # "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM" series anchor
    until: str = ""              # optional series end (ISO); mirrors UNTIL
    exdates: list[str] = []      # explicit skip dates (ISO); mirrors EXDATE
    # Google Calendar sync — same opt-in shape as Task.
    sync_to_calendar: bool = False
    calendar_id: str = ""
    calendar_event_id: str = ""
    sync_state: SyncState = SyncState.NONE
    last_synced_at: str = ""
    last_synced_hash: str = ""


class Occurrence(BaseModel):
    id: str                               # "occ-{rtask-id}-{YYYY-MM-DD}" deterministic
    recurring_task_id: str                # "rtask-{n}"
    date: str                             # ISO YYYY-MM-DD
    status: OccurrenceStatus = OccurrenceStatus.PENDING
    completed_at: str = ""                # ISO-8601 when marked done
    note: str = ""
    calendar_event_instance_id: str = ""  # remote recurringEventId + originalStartTime


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
    recurring_tasks: list[RecurringTask] = []
    occurrences: list[Occurrence] = []
    notes: list[Note] = []
    contexts: list[Context] = []
    skills: list[Skill] = []
    errors: list[ParseError] = []
