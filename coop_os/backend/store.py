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
    ParseError,
    ProjectState,
    Role,
    Skill,
    Task,
)

# ── Private helpers ───────────────────────────────────────────────────────────


def _slugify(text: str) -> str:
    """Convert a string to a URL-safe slug.

    Lowercases, strips non-word chars, collapses whitespace/underscores to hyphens, truncates at 40 chars.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text[:40]


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
        if task.attachments:
            meta["attachments"] = [attachment.model_dump() for attachment in task.attachments]
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
        self.notes = NoteStore(root)
        self.contexts = ContextStore(root)
        self.skills = SkillStore(root)

    def store_for(
        self, kind: str
    ) -> RoleStore | MilestoneStore | TaskStore | NoteStore | ContextStore | SkillStore | None:
        return {
            "role": self.roles,
            "milestone": self.milestones,
            "task": self.tasks,
            "note": self.notes,
            "context": self.contexts,
            "skill": self.skills,
        }.get(kind)

    def load(self) -> ProjectState:
        roles, role_errs = self.roles.load_all()
        milestones, ms_errs = self.milestones.load_all()
        tasks, task_errs = self.tasks.load_all()
        notes, note_errs = self.notes.load_all()
        contexts, ctx_errs = self.contexts.load_all()
        skills, skill_errs = self.skills.load_all()
        errors = role_errs + ms_errs + task_errs + note_errs + ctx_errs + skill_errs
        return ProjectState(
            roles=roles,
            milestones=milestones,
            tasks=tasks,
            notes=notes,
            contexts=contexts,
            skills=skills,
            errors=errors,
        )

    def find_item_path(self, kind: str, item_id: str) -> Path | None:
        store = self.store_for(kind)
        return store.find_path(item_id) if store else None
