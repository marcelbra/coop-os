from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import frontmatter

from agent_os.models import (
    Milestone,
    Note,
    ParseError,
    ProjectState,
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


# ── Entity stores ─────────────────────────────────────────────────────────────


class MilestoneStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._dir = root / "agent_os" / "content" / "milestones"

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
        self._dir = root / "agent_os" / "content" / "tasks"

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
                    label=str(meta.get("label", "")),
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
        meta: dict[str, Any] = {
            "id": task.id,
            "title": task.title,
            "status": str(task.status),
            "created_date": task.created_date,
            "label": task.label,
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
        self._dir = root / "agent_os" / "content" / "notes"

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


class SkillStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._dir = root / "agent_os" / "content" / "skills"

    def load_all(self) -> tuple[list[Skill], list[ParseError]]:
        skills: list[Skill] = []
        errors: list[ParseError] = []
        if not self._dir.exists():
            return skills, errors
        for path in sorted(self._dir.glob("*.md")):
            try:
                meta, content = _read_fm(path)
                skills.append(Skill(
                    id=str(meta["id"]),
                    command=str(meta["command"]),
                    content=content,
                ))
            except Exception as e:
                errors.append(ParseError(file=f"agent_os/content/skills/{path.name}", error=str(e)))
        return skills, errors

    def next_id(self) -> str:
        return _next_id([_fm_id(p) for p in self._dir.glob("*.md")] if self._dir.exists() else [], "skill")

    def save(self, skill: Skill) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        existing = _find_file_by_id(self._dir, skill.id)
        path = existing or self._dir / f"{skill.id}-{_slugify(skill.command)}.md"
        _write_fm(path, {"id": skill.id, "command": skill.command}, skill.content)

    def delete(self, skill_id: str) -> bool:
        path = _find_file_by_id(self._dir, skill_id)
        if path:
            path.unlink()
            return True
        return False

    def find_path(self, skill_id: str) -> Path | None:
        return _find_file_by_id(self._dir, skill_id)


# ── Project store ─────────────────────────────────────────────────────────────


class ProjectStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.milestones = MilestoneStore(root)
        self.tasks = TaskStore(root)
        self.notes = NoteStore(root)
        self.skills = SkillStore(root)

    def load(self) -> ProjectState:
        milestones, ms_errs = self.milestones.load_all()
        tasks, task_errs = self.tasks.load_all()
        notes, note_errs = self.notes.load_all()
        skills, skill_errs = self.skills.load_all()
        errors = ms_errs + task_errs + note_errs + skill_errs
        return ProjectState(milestones=milestones, tasks=tasks, notes=notes, skills=skills, errors=errors)

    def find_item_path(self, kind: str, item_id: str) -> Path | None:
        match kind:
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
