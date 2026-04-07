from __future__ import annotations

import re
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol

import frontmatter

from coop_os.backend.models import (
    Doc,
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


_TASK_DIR_RE = re.compile(r"^task-\d+-")


def _is_task_dir(d: Path) -> bool:
    return d.is_dir() and bool(_TASK_DIR_RE.match(d.name))


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
        self._dir = root / "coop_os" / "context" / "tasks"

    def _load_from_dir(
        self, search_dir: Path, parent_id: str | None, tasks: list[Task], errors: list[ParseError]
    ) -> None:
        for task_dir in sorted(d for d in search_dir.iterdir() if _is_task_dir(d)):
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
            task_dir = base / f"{task.id}-{_slugify(task.title)}"
        else:
            task_dir = self._dir / f"{task.id}-{_slugify(task.title)}"
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


class DocStore(FlatFileStore[Doc]):
    def __init__(self, root: Path) -> None:
        super().__init__(root, "context/docs", "doc")

    def _parse(self, meta: dict[str, Any], content: str) -> Doc:
        return Doc(
            id=str(meta["id"]),
            title=str(meta["title"]),
            content=content,
        )

    def _to_meta_content(self, item: Doc) -> tuple[dict[str, Any], str]:
        return {"id": item.id, "title": item.title}, item.content

    def _file_slug(self, item: Doc) -> str:
        return item.title


class SkillStore(FlatFileStore[Skill]):
    def __init__(self, root: Path) -> None:
        super().__init__(root, "skills", "skill", label="coop_os/skills")

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
        self.docs = DocStore(root)
        self.skills = SkillStore(root)

    def load(self) -> ProjectState:
        roles, role_errs = self.roles.load_all()
        milestones, ms_errs = self.milestones.load_all()
        tasks, task_errs = self.tasks.load_all()
        notes, note_errs = self.notes.load_all()
        docs, doc_errs = self.docs.load_all()
        skills, skill_errs = self.skills.load_all()
        errors = role_errs + ms_errs + task_errs + note_errs + doc_errs + skill_errs
        return ProjectState(
            roles=roles,
            milestones=milestones,
            tasks=tasks,
            notes=notes,
            docs=docs,
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
            case "doc":
                return self.docs.find_path(item_id)
            case "skill":
                return self.skills.find_path(item_id)
            case _:
                return None
