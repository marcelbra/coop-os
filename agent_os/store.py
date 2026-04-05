from __future__ import annotations

import re
import shutil
from pathlib import Path

import frontmatter

from agent_os.models import (
    PMS,
    Milestone,
    Note,
    ParseError,
    ProjectState,
    Role,
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


def _read_fm(path: Path) -> tuple[dict, str]:
    post = frontmatter.load(str(path))
    return dict(post.metadata), post.content


def _write_fm(path: Path, metadata: dict, content: str) -> None:
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


# ── Entity stores ─────────────────────────────────────────────────────────────


class PMSStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._path = root / "context" / "0-pms.md"

    def load(self) -> tuple[PMS | None, ParseError | None]:
        if not self._path.exists():
            return None, ParseError(file="context/0-pms.md", error="Required file missing")
        try:
            meta, content = _read_fm(self._path)
            return PMS(id="pms", title=meta.get("title", "Personal Mission Statement"), content=content), None
        except Exception as e:
            return None, ParseError(file="context/0-pms.md", error=str(e))

    def save(self, pms: PMS) -> None:
        _write_fm(self._path, {"id": "pms", "title": pms.title}, pms.content)


class RoleStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._dir = root / "context" / "roles"

    def load_all(self) -> tuple[list[Role], list[ParseError]]:
        roles: list[Role] = []
        errors: list[ParseError] = []
        if not self._dir.exists():
            return roles, errors
        for path in sorted(self._dir.glob("*.md")):
            try:
                meta, content = _read_fm(path)
                roles.append(Role(
                    id=str(meta["id"]),
                    name=str(meta["name"]),
                    emoji=str(meta["emoji"]),
                    title=str(meta["title"]),
                    content=content,
                ))
            except Exception as e:
                errors.append(ParseError(file=f"context/roles/{path.name}", error=str(e)))
        return roles, errors

    def next_id(self) -> str:
        return _next_id([_fm_id(p) for p in self._dir.glob("*.md")] if self._dir.exists() else [], "role")

    def save(self, role: Role) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        existing = _find_file_by_id(self._dir, role.id)
        path = existing or self._dir / f"{role.id}-{_slugify(role.name)}.md"
        _write_fm(path, {"id": role.id, "name": role.name, "emoji": role.emoji, "title": role.title}, role.content)

    def delete(self, role_id: str) -> bool:
        path = _find_file_by_id(self._dir, role_id)
        if path:
            path.unlink()
            return True
        return False

    def find_path(self, role_id: str) -> Path | None:
        return _find_file_by_id(self._dir, role_id)


class MilestoneStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._dir = root / "milestones"

    def load_all(self) -> tuple[list[Milestone], list[ParseError]]:
        milestones: list[Milestone] = []
        errors: list[ParseError] = []
        if not self._dir.exists():
            return milestones, errors
        for path in sorted(self._dir.glob("*.md")):
            try:
                meta, content = _read_fm(path)
                milestones.append(Milestone(
                    id=str(meta["id"]),
                    title=str(meta["title"]),
                    role=str(meta.get("role", "")),
                    start_date=str(meta.get("start_date", "")),
                    end_date=str(meta.get("end_date", "")),
                    status=meta.get("status", "active"),
                    description=content,
                ))
            except Exception as e:
                errors.append(ParseError(file=f"milestones/{path.name}", error=str(e)))
        return milestones, errors

    def next_id(self) -> str:
        return _next_id([_fm_id(p) for p in self._dir.glob("*.md")] if self._dir.exists() else [], "milestone")

    def save(self, ms: Milestone) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        existing = _find_file_by_id(self._dir, ms.id)
        path = existing or self._dir / f"{ms.id}-{_slugify(ms.title)}.md"
        _write_fm(path, {
            "id": ms.id,
            "title": ms.title,
            "role": ms.role,
            "start_date": ms.start_date,
            "end_date": ms.end_date,
            "status": str(ms.status),
        }, ms.description)

    def delete(self, ms_id: str) -> bool:
        path = _find_file_by_id(self._dir, ms_id)
        if path:
            path.unlink()
            return True
        return False

    def find_path(self, ms_id: str) -> Path | None:
        return _find_file_by_id(self._dir, ms_id)


class TaskStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._dir = root / "tasks"

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
                    status=meta.get("status", "todo"),
                    milestone=str(meta["milestone"]) if meta.get("milestone") else None,
                    labels=list(meta.get("labels", [])),
                    dependencies=[str(d) for d in meta.get("dependencies", [])],
                    created_date=str(meta.get("created_date", "")),
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
        ]
        return _next_id(ids, "task")

    def save(self, task: Task) -> None:
        existing_dir = _find_task_dir(self._dir, task.id)
        task_dir = existing_dir or self._dir / f"{task.id}-{_slugify(task.title)}"
        task_dir.mkdir(parents=True, exist_ok=True)
        meta: dict = {
            "id": task.id,
            "title": task.title,
            "status": str(task.status),
            "created_date": task.created_date,
            "labels": task.labels,
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


class NoteStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._dir = root / "notes"

    def load_all(self) -> tuple[list[Note], list[ParseError]]:
        notes: list[Note] = []
        errors: list[ParseError] = []
        if not self._dir.exists():
            return notes, errors
        for path in sorted(self._dir.glob("*.md")):
            try:
                meta, content = _read_fm(path)
                notes.append(Note(
                    id=str(meta["id"]),
                    title=str(meta["title"]),
                    date=str(meta.get("date", "")),
                    scanned=bool(meta.get("scanned", False)),
                    content=content,
                ))
            except Exception as e:
                errors.append(ParseError(file=f"notes/{path.name}", error=str(e)))
        return notes, errors

    def next_id(self) -> str:
        return _next_id([_fm_id(p) for p in self._dir.glob("*.md")] if self._dir.exists() else [], "note")

    def save(self, note: Note) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        existing = _find_file_by_id(self._dir, note.id)
        path = existing or self._dir / f"{note.id}-{_slugify(note.title)}.md"
        _write_fm(path, {"id": note.id, "title": note.title, "date": note.date, "scanned": note.scanned}, note.content)

    def delete(self, note_id: str) -> bool:
        path = _find_file_by_id(self._dir, note_id)
        if path:
            path.unlink()
            return True
        return False

    def find_path(self, note_id: str) -> Path | None:
        return _find_file_by_id(self._dir, note_id)


# ── Project store ─────────────────────────────────────────────────────────────


class ProjectStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.pms = PMSStore(root)
        self.roles = RoleStore(root)
        self.milestones = MilestoneStore(root)
        self.tasks = TaskStore(root)
        self.notes = NoteStore(root)

    def load(self) -> ProjectState:
        pms, pms_err = self.pms.load()
        roles, role_errs = self.roles.load_all()
        milestones, ms_errs = self.milestones.load_all()
        tasks, task_errs = self.tasks.load_all()
        notes, note_errs = self.notes.load_all()
        errors = ([pms_err] if pms_err else []) + role_errs + ms_errs + task_errs + note_errs
        return ProjectState(pms=pms, roles=roles, milestones=milestones, tasks=tasks, notes=notes, errors=errors)

    def find_item_path(self, kind: str, item_id: str) -> Path | None:
        match kind:
            case "pms":
                p = self.root / "context" / "0-pms.md"
                return p if p.exists() else None
            case "role":
                return self.roles.find_path(item_id)
            case "milestone":
                return self.milestones.find_path(item_id)
            case "task":
                return self.tasks.find_path(item_id)
            case "note":
                return self.notes.find_path(item_id)
        return None
