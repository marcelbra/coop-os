from __future__ import annotations

import re
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol

import frontmatter

from agent_os.backend.models import (
    Milestone,
    Note,
    ParseError,
    ProjectState,
    Role,
    Skill,
    Task,
)

# ── Private helpers ───────────────────────────────────────────────────────────


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text[:40]


def _next_id(ids: list[str], prefix: str) -> str:
    """Return the next sequential ID with the given type prefix (e.g. 'task-3')."""
    nums: list[int] = []
    for i in ids:
        if i.startswith(f"{prefix}-"):
            try:
                nums.append(int(i[len(prefix) + 1:]))
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
    if not directory.exists():
        return None
    return next((p for p in directory.glob("*.md") if _fm_id(p) == item_id), None)


def _find_task_dir(tasks_dir: Path, task_id: str) -> Path | None:
    if not tasks_dir.exists():
        return None

    def _match(d: Path) -> bool:
        return d.is_dir() and (d / "description.md").exists() and _fm_id(d / "description.md") == task_id

    return next((d for d in tasks_dir.iterdir() if _match(d)), None)


# ── Base store for flat-file entities ─────────────────────────────────────────


class _HasId(Protocol):
    id: str


class FlatFileStore[T: _HasId](ABC):
    """Base class for stores that persist each item as a single .md file."""

    def __init__(self, root: Path, rel_dir: str, prefix: str, label: str | None = None) -> None:
        self._dir = root / "agent_os" / rel_dir
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
        for path in sorted(self._dir.glob("*.md")):
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
        path = existing or self._dir / f"{item.id}-{_slugify(self._file_slug(item))}.md"
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
        super().__init__(root, "context/roles", "role")

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


class MilestoneStore(FlatFileStore[Milestone]):
    def __init__(self, root: Path) -> None:
        super().__init__(root, "context/milestones", "milestone")

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


class TaskStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._dir = root / "agent_os" / "context" / "tasks"

    def load_all(self) -> tuple[list[Task], list[ParseError]]:
        tasks: list[Task] = []
        errors: list[ParseError] = []
        if not self._dir.exists():
            return tasks, errors
        for task_dir in sorted(d for d in self._dir.iterdir() if d.is_dir()):
            desc_path = task_dir / "description.md"
            if not desc_path.exists():
                errors.append(ParseError(file=f"tasks/{task_dir.name}", error="Missing description.md"))
                continue
            try:
                meta, content = _read_fm(desc_path)
                tasks.append(Task(
                    id=str(meta["id"]),
                    title=str(meta["title"]),
                    start_date=str(meta.get("start_date", "")),
                    end_date=str(meta.get("end_date", "")),
                    status=meta.get("status", "todo"),
                    milestone=str(meta["milestone"]) if meta.get("milestone") else None,
                    dependencies=[str(d) for d in meta.get("dependencies", [])],
                    description=content,
                ))
            except Exception as e:
                errors.append(ParseError(file=f"tasks/{task_dir.name}/description.md", error=str(e)))
        return tasks, errors

    def next_id(self) -> str:
        ids = [
            _fm_id(td / "description.md")
            for td in self._dir.iterdir()
            if td.is_dir() and (td / "description.md").exists()
        ] if self._dir.exists() else []
        return _next_id(ids, "task")

    def save(self, task: Task) -> None:
        existing_dir = _find_task_dir(self._dir, task.id)
        task_dir = existing_dir or self._dir / f"{task.id}-{_slugify(task.title)}"
        task_dir.mkdir(parents=True, exist_ok=True)
        meta: dict[str, Any] = {
            "id": task.id,
            "title": task.title,
            "start_date": task.start_date,
            "end_date": task.end_date,
            "status": str(task.status),
            "dependencies": task.dependencies,
        }
        if task.milestone:
            meta["milestone"] = task.milestone
        _write_fm(task_dir / "description.md", meta, task.description)

    def delete(self, task_id: str) -> bool:
        d = _find_task_dir(self._dir, task_id)
        if d:
            shutil.rmtree(d)
            return True
        return False

    def find_path(self, task_id: str) -> Path | None:
        d = _find_task_dir(self._dir, task_id)
        return d / "description.md" if d else None


class NoteStore(FlatFileStore[Note]):
    def __init__(self, root: Path) -> None:
        super().__init__(root, "context/notes", "note")

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


class SkillStore(FlatFileStore[Skill]):
    def __init__(self, root: Path) -> None:
        super().__init__(root, "skills", "skill", label="agent_os/skills")

    def _parse(self, meta: dict[str, Any], content: str) -> Skill:
        return Skill(
            id=str(meta["id"]),
            command=str(meta["command"]),
            content=content,
        )

    def _to_meta_content(self, item: Skill) -> tuple[dict[str, Any], str]:
        return {"id": item.id, "command": item.command}, item.content

    def _file_slug(self, item: Skill) -> str:
        return item.command


# ── Project store ─────────────────────────────────────────────────────────────


class ProjectStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.roles = RoleStore(root)
        self.milestones = MilestoneStore(root)
        self.tasks = TaskStore(root)
        self.notes = NoteStore(root)
        self.skills = SkillStore(root)

    def load(self) -> ProjectState:
        roles, role_errs = self.roles.load_all()
        milestones, ms_errs = self.milestones.load_all()
        tasks, task_errs = self.tasks.load_all()
        notes, note_errs = self.notes.load_all()
        skills, skill_errs = self.skills.load_all()
        errors = role_errs + ms_errs + task_errs + note_errs + skill_errs
        return ProjectState(
            roles=roles,
            milestones=milestones,
            tasks=tasks,
            notes=notes,
            skills=skills,
            errors=errors,
        )

    def find_item_path(self, kind: str, item_id: str) -> Path | None:
        match kind:
            case "role":
                return self.roles.find_path(item_id)
            case "milestone":
                return self.milestones.find_path(item_id)
            case "task":
                return self.tasks.find_path(item_id)
            case "note":
                return self.notes.find_path(item_id)
            case "skill":
                return self.skills.find_path(item_id)
            case _:
                return None
