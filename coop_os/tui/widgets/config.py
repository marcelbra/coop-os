from __future__ import annotations

from pathlib import Path

SCANNED_ICONS: dict[str, str] = {"true": "✓", "false": "!"}


class AppConfig:
    def __init__(
        self,
        task_statuses: dict[str, str],
        milestone_statuses: dict[str, str],
        role_statuses: dict[str, str],
    ) -> None:
        self.task_statuses = task_statuses        # value -> icon
        self.milestone_statuses = milestone_statuses
        self.role_statuses = role_statuses


def read_config(root: Path) -> AppConfig:
    """Parse config.yml into an AppConfig. No external YAML library needed."""
    config_path = root / "config.yml"
    task_statuses: dict[str, str] = {}
    milestone_statuses: dict[str, str] = {}
    role_statuses: dict[str, str] = {}

    if not config_path.exists():
        return AppConfig(task_statuses, milestone_statuses, role_statuses)

    section: str | None = None
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "task_statuses:":
            section = "task_statuses"
        elif stripped == "milestone_statuses:":
            section = "milestone_statuses"
        elif stripped == "role_statuses:":
            section = "role_statuses"
        elif ": " in stripped and section in ("task_statuses", "milestone_statuses", "role_statuses"):
            key, _, val = stripped.partition(": ")
            icon = val.strip().strip('"')
            if section == "task_statuses":
                task_statuses[key.strip()] = icon
            elif section == "milestone_statuses":
                milestone_statuses[key.strip()] = icon
            else:
                role_statuses[key.strip()] = icon

    return AppConfig(task_statuses, milestone_statuses, role_statuses)
