from __future__ import annotations

_TITLE_KINDS = frozenset({"role", "milestone", "task", "note", "context", "recurring_task"})
_ID_KINDS = frozenset({
    "role", "milestone", "task", "note", "context", "recurring_task", "occurrence",
})
_DATE_KINDS = frozenset({"milestone", "task"})
_STATUS_KINDS = frozenset({"role", "milestone", "task", "recurring_task", "occurrence"})
_TASK_RTASK = frozenset({"task", "recurring_task"})
_RTASK_ONLY = frozenset({"recurring_task"})
_TASK_ONLY = frozenset({"task"})
_NOTE_OCC = frozenset({"note", "occurrence"})
_OCC_ONLY = frozenset({"occurrence"})

# (attr_key, display_label, visible_for_kinds, readonly)
FIELD_DEFS: list[tuple[str, str, frozenset[str], bool]] = [
    ("title",             "title",             _TITLE_KINDS,                 False),
    ("name",              "name",              frozenset({"skill"}),         False),
    ("description",       "description",       frozenset({"skill"}),         False),
    ("date",              "date",              _NOTE_OCC,                    False),
    ("scanned",           "scanned",           frozenset({"note"}),          False),
    ("start_date",        "start date",        _DATE_KINDS,                  False),
    ("end_date",          "end date",          _DATE_KINDS,                  False),
    ("status",            "status",            _STATUS_KINDS,                False),
    ("role",              "role",              frozenset({"milestone", "recurring_task"}), False),
    ("milestone",         "milestone",         _TASK_RTASK,                  False),
    ("parent",            "parent",            _TASK_ONLY,                   True),
    ("time_policy",       "time policy",       _TASK_RTASK,                  False),
    ("start_time",        "start time",        _TASK_RTASK,                  False),
    ("duration_minutes",  "duration (min)",    _TASK_RTASK,                  False),
    ("timezone",          "timezone",          _TASK_RTASK,                  False),
    ("rrule",             "rrule",             _RTASK_ONLY,                  False),
    ("dtstart",           "dtstart",           _RTASK_ONLY,                  False),
    ("until",             "until",             _RTASK_ONLY,                  False),
    ("exdates",           "exdates",           _RTASK_ONLY,                  False),
    ("sync_to_calendar",  "sync to cal",       _TASK_RTASK,                  False),
    ("calendar_id",       "calendar id",       _TASK_RTASK,                  False),
    ("calendar_event_id", "calendar event id", _TASK_RTASK,                  True),
    ("sync_state",        "sync state",        _TASK_RTASK,                  True),
    ("last_synced_at",    "last synced at",    _TASK_RTASK,                  True),
    ("recurring_task_id", "recurring task",    _OCC_ONLY,                    True),
    ("completed_at",      "completed at",      _OCC_ONLY,                    True),
    ("id",                "id",                _ID_KINDS,                    True),
]

DATE_FIELDS: frozenset[str] = frozenset({"start_date", "end_date", "date", "dtstart", "until"})
TIME_FIELDS: frozenset[str] = frozenset({"start_time"})
INT_FIELDS: frozenset[str] = frozenset({"duration_minutes"})
BOOL_FIELDS: frozenset[str] = frozenset({"scanned", "sync_to_calendar"})
SELECT_FIELDS: frozenset[str] = frozenset({
    "status", "role", "milestone", "scanned", "time_policy", "sync_to_calendar", "sync_state",
})
LIST_FIELDS: frozenset[str] = frozenset({"exdates"})

BODY_ATTR: dict[str, str] = {
    "role": "description",
    "milestone": "description",
    "task": "description",
    "recurring_task": "description",
    "occurrence": "note",
    "note": "content",
    "context": "content",
    "skill": "content",
    "agent": "content",
}
