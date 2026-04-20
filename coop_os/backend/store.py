from __future__ import annotations

import re
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol

import frontmatter

from coop_os.backend.models import (
    Attachment,
    Context,
    Milestone,
    Note,
    Occurrence,
    OccurrenceStatus,
    ParseError,
    ProjectState,
    RecurringTask,
    Role,
    Skill,
    Task,
)

# ── Private helpers ───────────────────────────────────────────────────────────


def sanitize_filename(text: str) -> str:
    """Sanitize text for use as a filename component, preserving case and spaces.

    Replaces path separators and null bytes with hyphens, strips leading/trailing
    whitespace, and truncates at 60 characters.
    """
    text = re.sub(r"[/\\\x00]", "-", text)
    return text.strip()[:60]


def _next_id(ids: list[str], prefix: str) -> str:
    """Return the next sequential ID with the given type prefix (e.g. 'task-3')."""
    nums: list[int] = []
    for id_str in ids:
        if id_str.startswith(f"{prefix}-"):
            try:
                nums.append(int(id_str[len(prefix) + 1:]))
            except ValueError:
                pass
    return f"{prefix}-{max(nums, default=0) + 1}"


def _read_fm(path: Path) -> tuple[dict[str, Any], str]:
    post = frontmatter.load(str(path))
    return dict(post.metadata), post.content


def _write_fm(path: Path, metadata: dict[str, Any], content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(content, **metadata)
    path.write_text(frontmatter.dumps(post), encoding="utf-8")


def _fm_id(path: Path) -> str:
    try:
        meta, _ = _read_fm(path)
        return str(meta.get("id", ""))
    except Exception:
        return ""


def _find_file_by_id(directory: Path, item_id: str) -> Path | None:
    """Glob for all *.md files in a directory, returning the first whose frontmatter 'id' field matches the given id."""
    if not directory.exists():
        return None
    return next((p for p in directory.glob("*.md") if _fm_id(p) == item_id), None)


_TASK_DIR_RE = re.compile(r"^task-\d+-")


def _is_task_dir(path: Path) -> bool:
    return path.is_dir() and bool(_TASK_DIR_RE.match(path.name))


def _id_sort_key(path: Path) -> int:
    """Sort key for paths named like '{prefix}-{n}-{slug}': returns n as int."""
    match = re.search(r"-(\d+)(?:-|$)", path.name)
    return int(match.group(1)) if match else 0


def _find_task_dir(search_dir: Path, task_id: str) -> Path | None:
    """Recursively find a task directory by ID under *search_dir*."""
    if not search_dir.exists():
        return None
    for d in search_dir.iterdir():
        if not _is_task_dir(d):
            continue
        desc = d / "description.md"
        if desc.exists() and _fm_id(desc) == task_id:
            return d
        found = _find_task_dir(d, task_id)
        if found:
            return found
    return None


def _collect_task_ids(search_dir: Path) -> list[str]:
    """Recursively collect all task IDs under *search_dir*."""
    ids: list[str] = []
    if not search_dir.exists():
        return ids
    for d in search_dir.iterdir():
        if not _is_task_dir(d):
            continue
        desc = d / "description.md"
        if desc.exists():
            ids.append(_fm_id(desc))
        ids.extend(_collect_task_ids(d))
    return ids


# ── Serialization helpers for the time-policy / sync / recurrence fields ─────


def _apply_time_policy_meta(meta: dict[str, Any], item: RecurringTask | Task) -> None:
    """Serialize time-policy-related fields into *meta*, omitting zero-value defaults."""
    if str(item.time_policy) != "all_day":
        meta["time_policy"] = str(item.time_policy)
    if item.start_time:
        meta["start_time"] = item.start_time
    if item.duration_minutes:
        meta["duration_minutes"] = item.duration_minutes
    if item.timezone:
        meta["timezone"] = item.timezone


def _apply_recurrence_meta(meta: dict[str, Any], item: RecurringTask) -> None:
    if item.rrule:
        meta["rrule"] = item.rrule
    if item.dtstart:
        meta["dtstart"] = item.dtstart
    if item.until:
        meta["until"] = item.until
    if item.exdates:
        meta["exdates"] = list(item.exdates)


def _apply_sync_meta(meta: dict[str, Any], item: RecurringTask | Task) -> None:
    if item.sync_to_calendar:
        meta["sync_to_calendar"] = True
    if item.calendar_id:
        meta["calendar_id"] = item.calendar_id
    if item.calendar_event_id:
        meta["calendar_event_id"] = item.calendar_event_id
    if str(item.sync_state) != "none":
        meta["sync_state"] = str(item.sync_state)
    if item.last_synced_at:
        meta["last_synced_at"] = item.last_synced_at
    if item.last_synced_hash:
        meta["last_synced_hash"] = item.last_synced_hash


# ── Base store for flat-file entities ─────────────────────────────────────────


class _HasId(Protocol):
    id: str


class FlatFileStore[T: _HasId](ABC):
    """Base class for stores that persist each item as a single .md file."""

    def __init__(self, root: Path, rel_dir: str, prefix: str, label: str | None = None) -> None:
        self._dir = root / "coop_os" / rel_dir
        self._prefix = prefix
        self._label = label or (prefix + "s")

    @abstractmethod
    def _parse(self, meta: dict[str, Any], content: str) -> T: ...

    @abstractmethod
    def _to_meta_content(self, item: T) -> tuple[dict[str, Any], str]: ...

    @abstractmethod
    def _file_slug(self, item: T) -> str: ...

    def load_all(self) -> tuple[list[T], list[ParseError]]:
        items: list[T] = []
        errors: list[ParseError] = []
        if not self._dir.exists():
            return items, errors
        for path in sorted(self._dir.glob("*.md"), key=_id_sort_key):
            try:
                meta, content = _read_fm(path)
                items.append(self._parse(meta, content))
            except Exception as e:
                errors.append(ParseError(file=f"{self._label}/{path.name}", error=str(e)))
        return items, errors

    def next_id(self) -> str:
        ids = [_fm_id(p) for p in self._dir.glob("*.md")] if self._dir.exists() else []
        return _next_id(ids, self._prefix)

    def save(self, item: T) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        existing = _find_file_by_id(self._dir, item.id)
        path = existing or self._dir / f"{item.id}-{sanitize_filename(self._file_slug(item))}.md"
        meta, content = self._to_meta_content(item)
        _write_fm(path, meta, content)

    def delete(self, item_id: str) -> bool:
        path = _find_file_by_id(self._dir, item_id)
        if path:
            path.unlink()
            return True
        return False

    def find_path(self, item_id: str) -> Path | None:
        return _find_file_by_id(self._dir, item_id)


# ── Entity stores ─────────────────────────────────────────────────────────────


class RoleStore(FlatFileStore[Role]):
    def __init__(self, root: Path) -> None:
        super().__init__(root, "workspace/roles", "role")

    def _parse(self, meta: dict[str, Any], content: str) -> Role:
        return Role(
            id=str(meta["id"]),
            title=str(meta["title"]),
            status=meta.get("status", "active"),
            description=content,
        )

    def _to_meta_content(self, item: Role) -> tuple[dict[str, Any], str]:
        return {
            "id": item.id,
            "title": item.title,
            "status": str(item.status),
        }, item.description

    def _file_slug(self, item: Role) -> str:
        return item.title

    def save(self, item: Role) -> None:
        existing_roles, _ = self.load_all()
        if any(r.title == item.title and r.id != item.id for r in existing_roles):
            raise ValueError(f"A role named '{item.title}' already exists.")
        super().save(item)


class MilestoneStore(FlatFileStore[Milestone]):
    def __init__(self, root: Path) -> None:
        super().__init__(root, "workspace/milestones", "milestone")

    def _parse(self, meta: dict[str, Any], content: str) -> Milestone:
        return Milestone(
            id=str(meta["id"]),
            title=str(meta["title"]),
            start_date=str(meta.get("start_date", "")),
            end_date=str(meta.get("end_date", "")),
            status=meta.get("status", "active"),
            role=str(meta["role"]) if meta.get("role") else None,
            description=content,
        )

    def _to_meta_content(self, item: Milestone) -> tuple[dict[str, Any], str]:
        meta: dict[str, Any] = {
            "id": item.id,
            "title": item.title,
            "start_date": item.start_date,
            "end_date": item.end_date,
            "status": str(item.status),
        }
        if item.role:
            meta["role"] = item.role
        return meta, item.description

    def _file_slug(self, item: Milestone) -> str:
        return item.title

    def save(self, item: Milestone) -> None:
        existing_milestones, _ = self.load_all()
        if any(m.title == item.title and m.id != item.id for m in existing_milestones):
            raise ValueError(f"A milestone named '{item.title}' already exists.")
        super().save(item)


class TaskStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._dir = root / "coop_os" / "workspace" / "tasks"

    def _load_from_dir(
        self, search_dir: Path, parent_id: str | None, tasks: list[Task], errors: list[ParseError]
    ) -> None:
        """Recursively load tasks from a directory tree, appending to tasks and errors lists.

        The 'parent:' frontmatter field is intentionally ignored — directory nesting
        is the authoritative parent-child relationship.
        """
        for task_dir in sorted((d for d in search_dir.iterdir() if _is_task_dir(d)), key=_id_sort_key):
            desc_path = task_dir / "description.md"
            if not desc_path.exists():
                errors.append(ParseError(file=f"tasks/.../{task_dir.name}", error="Missing description.md"))
                continue
            try:
                meta, content = _read_fm(desc_path)
                # parent is derived from directory nesting, not from the frontmatter
                # field. The frontmatter `parent:` is written for human readability /
                # agent access but is intentionally ignored here — directory location
                # is authoritative.
                tasks.append(Task(
                    id=str(meta["id"]),
                    title=str(meta["title"]),
                    start_date=str(meta.get("start_date", "")),
                    end_date=str(meta.get("end_date", "")),
                    status=meta.get("status", "todo"),
                    milestone=str(meta["milestone"]) if meta.get("milestone") else None,
                    parent=parent_id,
                    description=content,
                    attachments=[
                        Attachment(**attachment)
                        for attachment in meta.get("attachments", [])
                        if (task_dir / attachment["filename"]).exists()
                    ],
                    time_policy=meta.get("time_policy", "all_day"),
                    start_time=str(meta.get("start_time", "")),
                    duration_minutes=int(meta.get("duration_minutes", 0)),
                    timezone=str(meta.get("timezone", "")),
                    sync_to_calendar=bool(meta.get("sync_to_calendar", False)),
                    calendar_id=str(meta.get("calendar_id", "")),
                    calendar_event_id=str(meta.get("calendar_event_id", "")),
                    sync_state=meta.get("sync_state", "none"),
                    last_synced_at=str(meta.get("last_synced_at", "")),
                    last_synced_hash=str(meta.get("last_synced_hash", "")),
                ))
                self._load_from_dir(task_dir, str(meta["id"]), tasks, errors)
            except Exception as e:
                errors.append(ParseError(file=f"tasks/.../{task_dir.name}/description.md", error=str(e)))

    def load_all(self) -> tuple[list[Task], list[ParseError]]:
        tasks: list[Task] = []
        errors: list[ParseError] = []
        if not self._dir.exists():
            return tasks, errors
        self._load_from_dir(self._dir, None, tasks, errors)
        return tasks, errors

    def next_id(self) -> str:
        return _next_id(_collect_task_ids(self._dir), "task")

    def save(self, task: Task) -> None:
        existing_dir = _find_task_dir(self._dir, task.id)
        if existing_dir:
            task_dir = existing_dir
        elif task.parent:
            parent_dir = _find_task_dir(self._dir, task.parent)
            base = parent_dir if parent_dir else self._dir
            task_dir = base / f"{task.id}-{sanitize_filename(task.title)}"
        else:
            task_dir = self._dir / f"{task.id}-{sanitize_filename(task.title)}"
        task_dir.mkdir(parents=True, exist_ok=True)
        meta: dict[str, Any] = {
            "id": task.id,
            "title": task.title,
            "start_date": task.start_date,
            "end_date": task.end_date,
            "status": str(task.status),
        }
        if task.milestone:
            meta["milestone"] = task.milestone
        if task.parent:
            meta["parent"] = task.parent
        if task.attachments:
            meta["attachments"] = [attachment.model_dump() for attachment in task.attachments]
        _apply_time_policy_meta(meta, task)
        _apply_sync_meta(meta, task)
        _write_fm(task_dir / "description.md", meta, task.description)

    def delete(self, task_id: str) -> bool:
        task_dir = _find_task_dir(self._dir, task_id)
        if task_dir:
            shutil.rmtree(task_dir)
            return True
        return False

    def find_path(self, task_id: str) -> Path | None:
        task_dir = _find_task_dir(self._dir, task_id)
        return task_dir / "description.md" if task_dir else None

    def all_task_dirs(self) -> dict[str, Path]:
        """Return a mapping of task_id -> task_dir_path for every known task."""
        result: dict[str, Path] = {}
        self._collect_dirs(self._dir, result)
        return result

    def _collect_dirs(self, search_dir: Path, result: dict[str, Path]) -> None:
        """Recursively populate result dict with task_id → task_dir mappings for all task directories under root."""
        if not search_dir.exists():
            return
        for subdir in search_dir.iterdir():
            if _is_task_dir(subdir):
                desc = subdir / "description.md"
                if desc.exists():
                    task_id = _fm_id(desc)
                    if task_id:
                        result[task_id] = subdir
                self._collect_dirs(subdir, result)


class NoteStore(FlatFileStore[Note]):
    def __init__(self, root: Path) -> None:
        super().__init__(root, "user/notes", "note")

    def _parse(self, meta: dict[str, Any], content: str) -> Note:
        return Note(
            id=str(meta["id"]),
            title=str(meta["title"]),
            date=str(meta.get("date", "")),
            scanned=bool(meta.get("scanned", False)),
            content=content,
        )

    def _to_meta_content(self, item: Note) -> tuple[dict[str, Any], str]:
        return {
            "id": item.id,
            "title": item.title,
            "date": item.date,
            "scanned": item.scanned,
        }, item.content

    def _file_slug(self, item: Note) -> str:
        return item.title


class ContextStore(FlatFileStore[Context]):
    def __init__(self, root: Path) -> None:
        super().__init__(root, "user/context", "context")

    def _parse(self, meta: dict[str, Any], content: str) -> Context:
        return Context(
            id=str(meta["id"]),
            title=str(meta["title"]),
            content=content,
        )

    def _to_meta_content(self, item: Context) -> tuple[dict[str, Any], str]:
        return {"id": item.id, "title": item.title}, item.content

    def _file_slug(self, item: Context) -> str:
        return item.title


class RecurringTaskStore(FlatFileStore[RecurringTask]):
    def __init__(self, root: Path) -> None:
        super().__init__(root, "workspace/recurring_tasks", "rtask", label="recurring_tasks")

    def _parse(self, meta: dict[str, Any], content: str) -> RecurringTask:
        return RecurringTask(
            id=str(meta["id"]),
            title=str(meta["title"]),
            status=meta.get("status", "active"),
            role=str(meta["role"]) if meta.get("role") else None,
            milestone=str(meta["milestone"]) if meta.get("milestone") else None,
            description=content,
            time_policy=meta.get("time_policy", "all_day"),
            start_time=str(meta.get("start_time", "")),
            duration_minutes=int(meta.get("duration_minutes", 0)),
            timezone=str(meta.get("timezone", "")),
            rrule=str(meta.get("rrule", "")),
            dtstart=str(meta.get("dtstart", "")),
            until=str(meta.get("until", "")),
            exdates=[str(date_str) for date_str in meta.get("exdates", [])],
            sync_to_calendar=bool(meta.get("sync_to_calendar", False)),
            calendar_id=str(meta.get("calendar_id", "")),
            calendar_event_id=str(meta.get("calendar_event_id", "")),
            sync_state=meta.get("sync_state", "none"),
            last_synced_at=str(meta.get("last_synced_at", "")),
            last_synced_hash=str(meta.get("last_synced_hash", "")),
        )

    def _to_meta_content(self, item: RecurringTask) -> tuple[dict[str, Any], str]:
        meta: dict[str, Any] = {
            "id": item.id,
            "title": item.title,
            "status": str(item.status),
        }
        if item.role:
            meta["role"] = item.role
        if item.milestone:
            meta["milestone"] = item.milestone
        _apply_time_policy_meta(meta, item)
        _apply_recurrence_meta(meta, item)
        _apply_sync_meta(meta, item)
        return meta, item.description

    def _file_slug(self, item: RecurringTask) -> str:
        return item.title

    def save(self, item: RecurringTask) -> None:
        existing_items, _ = self.load_all()
        if any(other.title == item.title and other.id != item.id for other in existing_items):
            raise ValueError(f"A recurring task named '{item.title}' already exists.")
        super().save(item)


_OCC_ID_RE = re.compile(r"^occ-(rtask-\d+)-(\d{4}-\d{2}-\d{2})$")


class OccurrenceStore:
    """Flat per-occurrence store keyed by deterministic IDs.

    IDs have the form ``occ-{rtask-id}-{YYYY-MM-DD}`` and filenames mirror the ID with
    no title slug, which gives O(1) path lookups for ``(series, date)`` pairs and makes
    date-range queries (used by weekly-review) cheap via filename globbing.
    """

    def __init__(self, root: Path) -> None:
        self._dir = root / "coop_os" / "workspace" / "occurrences"

    def _path_for(self, occurrence_id: str) -> Path:
        return self._dir / f"{occurrence_id}.md"

    @staticmethod
    def build_id(recurring_task_id: str, date: str) -> str:
        return f"occ-{recurring_task_id}-{date}"

    def load_all(self) -> tuple[list[Occurrence], list[ParseError]]:
        items: list[Occurrence] = []
        errors: list[ParseError] = []
        if not self._dir.exists():
            return items, errors
        for path in sorted(self._dir.glob("occ-*.md")):
            try:
                meta, content = _read_fm(path)
                items.append(Occurrence(
                    id=str(meta["id"]),
                    recurring_task_id=str(meta["recurring_task_id"]),
                    date=str(meta["date"]),
                    status=meta.get("status", "pending"),
                    completed_at=str(meta.get("completed_at", "")),
                    note=content or str(meta.get("note", "")),
                    calendar_event_instance_id=str(meta.get("calendar_event_instance_id", "")),
                ))
            except Exception as e:
                errors.append(ParseError(file=f"occurrences/{path.name}", error=str(e)))
        return items, errors

    def for_series(self, recurring_task_id: str) -> list[Occurrence]:
        occurrences, _ = self.load_all()
        return [occurrence for occurrence in occurrences if occurrence.recurring_task_id == recurring_task_id]

    def in_range(self, start: str, end: str) -> list[Occurrence]:
        """Return occurrences with ISO date strings in ``[start, end]`` (inclusive)."""
        occurrences, _ = self.load_all()
        return [occurrence for occurrence in occurrences if start <= occurrence.date <= end]

    def get(self, recurring_task_id: str, date: str) -> Occurrence | None:
        path = self._path_for(self.build_id(recurring_task_id, date))
        if not path.exists():
            return None
        try:
            meta, content = _read_fm(path)
            return Occurrence(
                id=str(meta["id"]),
                recurring_task_id=str(meta["recurring_task_id"]),
                date=str(meta["date"]),
                status=meta.get("status", "pending"),
                completed_at=str(meta.get("completed_at", "")),
                note=content,
                calendar_event_instance_id=str(meta.get("calendar_event_instance_id", "")),
            )
        except Exception:
            return None

    def save(self, occurrence: Occurrence) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        meta: dict[str, Any] = {
            "id": occurrence.id,
            "recurring_task_id": occurrence.recurring_task_id,
            "date": occurrence.date,
            "status": str(occurrence.status),
        }
        if occurrence.completed_at:
            meta["completed_at"] = occurrence.completed_at
        if occurrence.calendar_event_instance_id:
            meta["calendar_event_instance_id"] = occurrence.calendar_event_instance_id
        _write_fm(self._path_for(occurrence.id), meta, occurrence.note)

    def upsert(
        self,
        recurring_task_id: str,
        date: str,
        status: OccurrenceStatus | str,
        note: str = "",
        completed_at: str = "",
    ) -> Occurrence:
        occurrence = Occurrence(
            id=self.build_id(recurring_task_id, date),
            recurring_task_id=recurring_task_id,
            date=date,
            status=OccurrenceStatus(str(status)),
            completed_at=completed_at,
            note=note,
        )
        self.save(occurrence)
        return occurrence

    def delete(self, item_id: str) -> bool:
        """Remove the occurrence with the given deterministic ID, if it exists."""
        if not _OCC_ID_RE.match(item_id):
            return False
        path = self._path_for(item_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def find_path(self, item_id: str) -> Path | None:
        if not _OCC_ID_RE.match(item_id):
            return None
        path = self._path_for(item_id)
        return path if path.exists() else None


class SkillStore:
    def __init__(self, root: Path) -> None:
        self._dir = root / "coop_os" / "agent" / "skills"

    def load_all(self) -> tuple[list[Skill], list[ParseError]]:
        items: list[Skill] = []
        errors: list[ParseError] = []
        if not self._dir.exists():
            return items, errors
        for path in sorted(self._dir.glob("*/SKILL.md")):
            try:
                meta, content = _read_fm(path)
                items.append(Skill(
                    name=str(meta["name"]),
                    description=str(meta.get("description", "")),
                    content=content,
                ))
            except Exception as e:
                errors.append(ParseError(file=f"coop_os/agent/skills/{path.parent.name}/SKILL.md", error=str(e)))
        return items, errors

    def save(self, item: Skill) -> None:
        skill_dir = self._dir / item.name
        skill_dir.mkdir(parents=True, exist_ok=True)
        _write_fm(skill_dir / "SKILL.md", {"name": item.name, "description": item.description}, item.content)

    def find_path(self, item_id: str) -> Path | None:
        path = self._dir / item_id / "SKILL.md"
        return path if path.exists() else None

    def next_new_name(self) -> str:
        n = 1
        while (self._dir / f"new-skill-{n}").exists():
            n += 1
        return f"new-skill-{n}"

    def delete(self, item_id: str) -> bool:
        skill_dir = self._dir / item_id
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            return True
        return False


# ── Project store ─────────────────────────────────────────────────────────────


class ProjectStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.roles = RoleStore(root)
        self.milestones = MilestoneStore(root)
        self.tasks = TaskStore(root)
        self.recurring_tasks = RecurringTaskStore(root)
        self.occurrences = OccurrenceStore(root)
        self.notes = NoteStore(root)
        self.contexts = ContextStore(root)
        self.skills = SkillStore(root)

    def store_for(
        self, kind: str
    ) -> (
        RoleStore
        | MilestoneStore
        | TaskStore
        | RecurringTaskStore
        | OccurrenceStore
        | NoteStore
        | ContextStore
        | SkillStore
        | None
    ):
        return {
            "role": self.roles,
            "milestone": self.milestones,
            "task": self.tasks,
            "recurring_task": self.recurring_tasks,
            "occurrence": self.occurrences,
            "note": self.notes,
            "context": self.contexts,
            "skill": self.skills,
        }.get(kind)

    def load(self) -> ProjectState:
        roles, role_errs = self.roles.load_all()
        milestones, ms_errs = self.milestones.load_all()
        tasks, task_errs = self.tasks.load_all()
        recurring_tasks, rtask_errs = self.recurring_tasks.load_all()
        occurrences, occ_errs = self.occurrences.load_all()
        notes, note_errs = self.notes.load_all()
        contexts, ctx_errs = self.contexts.load_all()
        skills, skill_errs = self.skills.load_all()
        errors = (
            role_errs + ms_errs + task_errs + rtask_errs + occ_errs
            + note_errs + ctx_errs + skill_errs
        )
        return ProjectState(
            roles=roles,
            milestones=milestones,
            tasks=tasks,
            recurring_tasks=recurring_tasks,
            occurrences=occurrences,
            notes=notes,
            contexts=contexts,
            skills=skills,
            errors=errors,
        )

    def find_item_path(self, kind: str, item_id: str) -> Path | None:
        store = self.store_for(kind)
        return store.find_path(item_id) if store else None
