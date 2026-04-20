from __future__ import annotations

from pathlib import Path

SCANNED_ICONS: dict[str, str] = {"true": "✓", "false": "!"}

SYNC_STATE_ICONS: dict[str, str] = {
    "none": "·",
    "synced": "⇅",
    "dirty": "⟳",
    "drift": "≠",
    "error": "!",
}

TIME_POLICY_ICONS: dict[str, str] = {
    "all_day": "☼",
    "timed": "◷",
}

SYNC_TO_CALENDAR_ICONS: dict[str, str] = {"true": "↗", "false": "·"}

DEFAULT_WORKSPACE_TIMEZONE = "Europe/Amsterdam"

FILE_ICONS: dict[str, str] = {
    # Python
    ".py": "λ", ".ipynb": "λ",
    # JavaScript / TypeScript
    ".js": "◎", ".jsx": "◎", ".ts": "◎", ".tsx": "◎",
    # Shell
    ".sh": "$", ".bash": "$", ".zsh": "$", ".fish": "$",
    # Markup / docs
    ".md": "¶", ".rst": "¶",
    ".html": "◁", ".htm": "◁",
    ".xml": "◁",
    # Styles
    ".css": "≋", ".scss": "≋", ".sass": "≋",
    # Structured data
    ".json": "⊞", ".jsonc": "⊞",
    ".yml": "≈", ".yaml": "≈", ".toml": "≈", ".env": "≈", ".ini": "≈", ".cfg": "≈",
    # Tabular
    ".csv": "⊟", ".tsv": "⊟",
    # Database
    ".sql": "▦",
    # Plain text / logs
    ".txt": "≡", ".log": "≡",
    # Documents
    ".pdf": "▤",
    # Images
    ".png": "▣", ".jpg": "▣", ".jpeg": "▣", ".gif": "▣",
    ".svg": "▣", ".webp": "▣", ".ico": "▣",
}
FILE_ICON_DEFAULT = "·"
DIR_ICON = "▸"

# Maps file extensions to Textual TextArea language identifiers (tree-sitter).
FILE_LANGUAGES: dict[str, str] = {
    ".py": "python", ".ipynb": "python",
    ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash", ".fish": "bash",
    ".json": "json", ".jsonc": "json",
    ".yml": "yaml", ".yaml": "yaml",
    ".toml": "toml",
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "css", ".sass": "css",
    ".sql": "sql",
    ".xml": "xml",
    ".rs": "rust",
    ".go": "go",
    ".md": "markdown", ".markdown": "markdown",
}


class AppConfig:
    def __init__(
        self,
        task_statuses: dict[str, str],
        milestone_statuses: dict[str, str],
        role_statuses: dict[str, str],
        recurring_task_statuses: dict[str, str] | None = None,
        occurrence_statuses: dict[str, str] | None = None,
        workspace_timezone: str = DEFAULT_WORKSPACE_TIMEZONE,
    ) -> None:
        self.task_statuses = task_statuses        # value -> icon
        self.milestone_statuses = milestone_statuses
        self.role_statuses = role_statuses
        self.recurring_task_statuses = recurring_task_statuses or {}
        self.occurrence_statuses = occurrence_statuses or {}
        self.workspace_timezone = workspace_timezone


_MAPPING_SECTIONS = (
    "task_statuses", "milestone_statuses", "role_statuses",
    "recurring_task_statuses", "occurrence_statuses",
)


def read_config(root: Path) -> AppConfig:
    """Parse config.yml into an AppConfig. No external YAML library needed."""
    config_path = root / "config.yml"
    mappings: dict[str, dict[str, str]] = {name: {} for name in _MAPPING_SECTIONS}
    workspace_timezone = DEFAULT_WORKSPACE_TIMEZONE

    if not config_path.exists():
        return AppConfig(
            task_statuses=mappings["task_statuses"],
            milestone_statuses=mappings["milestone_statuses"],
            role_statuses=mappings["role_statuses"],
            recurring_task_statuses=mappings["recurring_task_statuses"],
            occurrence_statuses=mappings["occurrence_statuses"],
            workspace_timezone=workspace_timezone,
        )

    section: str | None = None
    for line in config_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indented = line.startswith((" ", "\t"))
        stripped = line.strip()
        if not indented:
            # Top-level line — either a section header or a scalar key:value pair.
            section = None
            if stripped.endswith(":") and ": " not in stripped:
                heading = stripped[:-1]
                section = heading if heading in _MAPPING_SECTIONS else None
                continue
            if ": " in stripped:
                key, _, val = stripped.partition(": ")
                if key.strip() == "workspace_timezone":
                    workspace_timezone = val.strip().strip('"') or DEFAULT_WORKSPACE_TIMEZONE
            continue
        if section is not None and ": " in stripped:
            key, _, val = stripped.partition(": ")
            icon = val.strip().strip('"')
            mappings[section][key.strip()] = icon

    return AppConfig(
        task_statuses=mappings["task_statuses"],
        milestone_statuses=mappings["milestone_statuses"],
        role_statuses=mappings["role_statuses"],
        recurring_task_statuses=mappings["recurring_task_statuses"],
        occurrence_statuses=mappings["occurrence_statuses"],
        workspace_timezone=workspace_timezone,
    )
