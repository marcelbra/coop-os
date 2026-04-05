from __future__ import annotations

from pathlib import Path

# ── Structured editor field definitions ───────────────────────────────────────

# (attr_key, display_label, visible_for_kinds, readonly)
FIELD_DEFS: list[tuple[str, str, frozenset[str], bool]] = [
    ("title",        "title",      frozenset({"milestone", "task", "note"}),                False),
    ("command",      "command",    frozenset({"skill"}),                                    False),
    ("date",         "date",       frozenset({"note"}),                                     False),
    ("scanned",      "scanned",    frozenset({"note"}),                                     False),
    ("start_date",   "start date", frozenset({"milestone"}),                                False),
    ("end_date",     "end date",   frozenset({"milestone"}),                                False),
    ("status",       "status",     frozenset({"milestone", "task"}),                        False),
    ("milestone",    "milestone",  frozenset({"task"}),                                     False),
    ("label",        "label",      frozenset({"task"}),                                     False),
    ("created_date", "created",    frozenset({"task"}),                                     False),
    ("id",           "id",         frozenset({"milestone", "task", "note", "skill"}),       True),
]

DATE_FIELDS: frozenset[str] = frozenset({"start_date", "end_date", "date", "created_date"})
SELECT_FIELDS: frozenset[str] = frozenset({"status", "label", "milestone", "scanned"})

BODY_ATTR: dict[str, str] = {
    "milestone": "description",
    "task": "description",
    "note": "content",
    "skill": "content",
    "agent": "content",
}


class AppConfig:
    def __init__(
        self,
        task_statuses: dict[str, str],
        milestone_statuses: dict[str, str],
        label: list[str],
    ) -> None:
        self.task_statuses = task_statuses        # value -> icon
        self.milestone_statuses = milestone_statuses
        self.label = label


def read_config(root: Path) -> AppConfig:
    """Parse config.yml into an AppConfig. No external YAML library needed."""
    config_path = root / "config.yml"
    task_statuses: dict[str, str] = {}
    milestone_statuses: dict[str, str] = {}
    label: list[str] = []

    if not config_path.exists():
        return AppConfig(task_statuses, milestone_statuses, label)

    section: str | None = None
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "task_statuses:":
            section = "task_statuses"
        elif stripped == "milestone_statuses:":
            section = "milestone_statuses"
        elif stripped == "label:":
            section = "label"
        elif stripped.startswith("- ") and section == "label":
            label.append(stripped[2:].strip())
        elif ": " in stripped and section in ("task_statuses", "milestone_statuses"):
            key, _, val = stripped.partition(": ")
            icon = val.strip().strip('"')
            if section == "task_statuses":
                task_statuses[key.strip()] = icon
            else:
                milestone_statuses[key.strip()] = icon

    return AppConfig(task_statuses, milestone_statuses, label)
