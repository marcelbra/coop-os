from __future__ import annotations

# (attr_key, display_label, visible_for_kinds, readonly)
FIELD_DEFS: list[tuple[str, str, frozenset[str], bool]] = [
    ("title",       "title",       frozenset({"role", "milestone", "task", "note", "context"}),           False),
    ("name",        "name",        frozenset({"skill"}),                                                   False),
    ("description", "description", frozenset({"skill"}),                                                   False),
    ("date",        "date",        frozenset({"note"}),                                                    False),
    ("scanned",     "scanned",     frozenset({"note"}),                                                    False),
    ("start_date",  "start date",  frozenset({"milestone", "task"}),                                       False),
    ("end_date",    "end date",    frozenset({"milestone", "task"}),                                       False),
    ("status",      "status",      frozenset({"role", "milestone", "task"}),                               False),
    ("role",        "role",        frozenset({"milestone"}),                                               False),
    ("milestone",   "milestone",   frozenset({"task"}),                                                    False),
    ("parent",      "parent",      frozenset({"task"}),                                                    True),
    ("id",          "id",          frozenset({"role", "milestone", "task", "note", "context"}),            True),
]

DATE_FIELDS: frozenset[str] = frozenset({"start_date", "end_date", "date"})
SELECT_FIELDS: frozenset[str] = frozenset({"status", "role", "milestone", "scanned"})

BODY_ATTR: dict[str, str] = {
    "role": "description",
    "milestone": "description",
    "task": "description",
    "note": "content",
    "context": "content",
    "skill": "content",
    "agent": "content",
}
