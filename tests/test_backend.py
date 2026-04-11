"""Unit tests for coop_os.backend (models, store, parser wrappers)."""
from __future__ import annotations

from pathlib import Path

import pytest

from coop_os.backend.models import (
    Context,
    Milestone,
    MilestoneStatus,
    Note,
    ProjectState,
    Role,
    RoleStatus,
    Skill,
    Task,
    TaskStatus,
)
from coop_os.backend.store import (
    ContextStore,
    MilestoneStore,
    NoteStore,
    ProjectStore,
    RoleStore,
    SkillStore,
    TaskStore,
    _next_id,
    sanitize_filename,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_root(tmp_path: Path) -> Path:
    """Return a project root with the coop_os/context structure pre-created."""
    root = tmp_path / "project"
    root.mkdir()
    return root


# ── sanitize_filename ─────────────────────────────────────────────────────────


def test_sanitize_filename_preserves_case_and_spaces() -> None:
    assert sanitize_filename("Hello World") == "Hello World"


def test_sanitize_filename_replaces_slash() -> None:
    assert sanitize_filename("foo/bar") == "foo-bar"


def test_sanitize_filename_replaces_backslash() -> None:
    assert sanitize_filename("foo\\bar") == "foo-bar"


def test_sanitize_filename_strips_leading_trailing_whitespace() -> None:
    assert sanitize_filename("  Hello  ") == "Hello"


def test_sanitize_filename_trims_to_60_chars() -> None:
    long = "a" * 70
    assert len(sanitize_filename(long)) <= 60


def test_sanitize_filename_empty_string() -> None:
    assert sanitize_filename("") == ""


# ── _next_id ──────────────────────────────────────────────────────────────────


def test_next_id_empty_list() -> None:
    assert _next_id([], "task") == "task-1"


def test_next_id_increments() -> None:
    assert _next_id(["task-1", "task-2", "task-3"], "task") == "task-4"


def test_next_id_skips_gaps() -> None:
    # Uses max, so gaps don't matter
    assert _next_id(["task-1", "task-5"], "task") == "task-6"


def test_next_id_ignores_wrong_prefix() -> None:
    assert _next_id(["role-1", "role-2"], "task") == "task-1"


def test_next_id_ignores_malformed() -> None:
    assert _next_id(["task-abc", "task-1"], "task") == "task-2"


# ── Models ────────────────────────────────────────────────────────────────────


def test_role_defaults() -> None:
    r = Role(id="role-1", title="Engineer")
    assert r.status == RoleStatus.ACTIVE
    assert r.description == ""


def test_milestone_defaults() -> None:
    m = Milestone(id="milestone-1", title="Launch")
    assert m.status == MilestoneStatus.ACTIVE
    assert m.role is None
    assert m.start_date == ""


def test_task_defaults() -> None:
    t = Task(id="task-1", title="Write tests")
    assert t.status == TaskStatus.TODO
    assert t.parent is None
    assert t.milestone is None


def test_note_defaults() -> None:
    n = Note(id="note-1", title="My Note")
    assert n.scanned is False
    assert n.date == ""
    assert n.content == ""


def test_project_state_empty() -> None:
    state = ProjectState()
    assert state.roles == []
    assert state.tasks == []
    assert state.errors == []


# ── RoleStore ─────────────────────────────────────────────────────────────────


def test_role_save_and_load(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RoleStore(root)
    role = Role(id="role-1", title="Engineer", description="Build things")
    store.save(role)
    roles, errors = store.load_all()
    assert errors == []
    assert len(roles) == 1
    assert roles[0].id == "role-1"
    assert roles[0].title == "Engineer"
    assert roles[0].description == "Build things"


def test_role_save_updates_existing(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RoleStore(root)
    role = Role(id="role-1", title="Engineer")
    store.save(role)
    role.title = "Senior Engineer"
    store.save(role)
    roles, _ = store.load_all()
    assert len(roles) == 1
    assert roles[0].title == "Senior Engineer"


def test_role_delete(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RoleStore(root)
    role = Role(id="role-1", title="Engineer")
    store.save(role)
    assert store.delete("role-1") is True
    roles, _ = store.load_all()
    assert roles == []


def test_role_delete_nonexistent(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RoleStore(root)
    assert store.delete("role-99") is False


def test_role_next_id_empty(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RoleStore(root)
    assert store.next_id() == "role-1"


def test_role_next_id_increments(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RoleStore(root)
    store.save(Role(id="role-1", title="A"))
    store.save(Role(id="role-2", title="B"))
    assert store.next_id() == "role-3"


def test_role_find_path(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RoleStore(root)
    role = Role(id="role-1", title="Engineer")
    store.save(role)
    path = store.find_path("role-1")
    assert path is not None
    assert path.exists()


def test_role_load_empty_dir(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RoleStore(root)
    roles, errors = store.load_all()
    assert roles == []
    assert errors == []


def test_role_status_roundtrip(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RoleStore(root)
    role = Role(id="role-1", title="Inactive", status=RoleStatus.INACTIVE)
    store.save(role)
    roles, _ = store.load_all()
    assert roles[0].status == RoleStatus.INACTIVE


def test_role_duplicate_title_raises(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RoleStore(root)
    store.save(Role(id="role-1", title="Engineer"))
    with pytest.raises(ValueError, match="role named 'Engineer' already exists"):
        store.save(Role(id="role-2", title="Engineer"))


def test_role_update_same_title_does_not_raise(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RoleStore(root)
    store.save(Role(id="role-1", title="Engineer"))
    store.save(Role(id="role-1", title="Engineer"))  # update same ID — must not raise


# ── MilestoneStore ────────────────────────────────────────────────────────────


def test_milestone_save_and_load(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = MilestoneStore(root)
    ms = Milestone(id="milestone-1", title="v1.0", start_date="2026-01-01", end_date="2026-06-01", role="role-1")
    store.save(ms)
    milestones, errors = store.load_all()
    assert errors == []
    assert len(milestones) == 1
    loaded = milestones[0]
    assert loaded.id == "milestone-1"
    assert loaded.title == "v1.0"
    assert loaded.start_date == "2026-01-01"
    assert loaded.role == "role-1"


def test_milestone_without_role(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = MilestoneStore(root)
    ms = Milestone(id="milestone-1", title="Standalone")
    store.save(ms)
    milestones, _ = store.load_all()
    assert milestones[0].role is None


def test_milestone_delete(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = MilestoneStore(root)
    ms = Milestone(id="milestone-1", title="v1.0")
    store.save(ms)
    assert store.delete("milestone-1") is True
    milestones, _ = store.load_all()
    assert milestones == []


def test_milestone_next_id(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = MilestoneStore(root)
    assert store.next_id() == "milestone-1"
    store.save(Milestone(id="milestone-1", title="A"))
    assert store.next_id() == "milestone-2"


def test_milestone_duplicate_title_raises(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = MilestoneStore(root)
    store.save(Milestone(id="milestone-1", title="v1.0"))
    with pytest.raises(ValueError, match="milestone named 'v1.0' already exists"):
        store.save(Milestone(id="milestone-2", title="v1.0"))


def test_milestone_update_same_title_does_not_raise(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = MilestoneStore(root)
    store.save(Milestone(id="milestone-1", title="v1.0"))
    store.save(Milestone(id="milestone-1", title="v1.0"))  # update same ID — must not raise


# ── TaskStore ─────────────────────────────────────────────────────────────────


def test_task_save_and_load(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = TaskStore(root)
    task = Task(id="task-1", title="Write tests", description="Do it")
    store.save(task)
    tasks, errors = store.load_all()
    assert errors == []
    assert len(tasks) == 1
    assert tasks[0].id == "task-1"
    assert tasks[0].title == "Write tests"
    assert tasks[0].description == "Do it"
    assert tasks[0].parent is None


def test_task_save_updates_existing(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = TaskStore(root)
    task = Task(id="task-1", title="Write tests")
    store.save(task)
    task.status = TaskStatus.DONE
    store.save(task)
    tasks, _ = store.load_all()
    assert len(tasks) == 1
    assert tasks[0].status == TaskStatus.DONE


def test_task_delete(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = TaskStore(root)
    task = Task(id="task-1", title="Write tests")
    store.save(task)
    assert store.delete("task-1") is True
    tasks, _ = store.load_all()
    assert tasks == []


def test_task_delete_nonexistent(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = TaskStore(root)
    assert store.delete("task-99") is False


def test_task_subtask_nesting(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = TaskStore(root)
    parent = Task(id="task-1", title="Parent")
    child = Task(id="task-2", title="Child", parent="task-1")
    store.save(parent)
    store.save(child)
    tasks, errors = store.load_all()
    assert errors == []
    assert len(tasks) == 2
    parent_loaded = next(t for t in tasks if t.id == "task-1")
    child_loaded = next(t for t in tasks if t.id == "task-2")
    assert parent_loaded.parent is None
    assert child_loaded.parent == "task-1"


def test_task_next_id_empty(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = TaskStore(root)
    assert store.next_id() == "task-1"


def test_task_next_id_with_subtasks(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = TaskStore(root)
    parent = Task(id="task-1", title="Parent")
    child = Task(id="task-2", title="Child", parent="task-1")
    store.save(parent)
    store.save(child)
    assert store.next_id() == "task-3"


def test_task_find_path(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = TaskStore(root)
    task = Task(id="task-1", title="My Task")
    store.save(task)
    path = store.find_path("task-1")
    assert path is not None
    assert path.name == "description.md"
    assert path.exists()


def test_task_with_milestone(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = TaskStore(root)
    task = Task(id="task-1", title="Ship it", milestone="milestone-1")
    store.save(task)
    tasks, _ = store.load_all()
    assert tasks[0].milestone == "milestone-1"


def test_task_load_empty_dir(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = TaskStore(root)
    tasks, errors = store.load_all()
    assert tasks == []
    assert errors == []


# ── NoteStore ─────────────────────────────────────────────────────────────────


def test_note_save_and_load(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = NoteStore(root)
    note = Note(id="note-1", title="Daily", date="2026-04-07", content="Some text")
    store.save(note)
    notes, errors = store.load_all()
    assert errors == []
    assert len(notes) == 1
    assert notes[0].id == "note-1"
    assert notes[0].content == "Some text"
    assert notes[0].date == "2026-04-07"


def test_note_scanned_roundtrip(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = NoteStore(root)
    note = Note(id="note-1", title="Old note", scanned=True)
    store.save(note)
    notes, _ = store.load_all()
    assert notes[0].scanned is True


def test_note_delete(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = NoteStore(root)
    note = Note(id="note-1", title="Delete me")
    store.save(note)
    assert store.delete("note-1") is True
    notes, _ = store.load_all()
    assert notes == []


def test_note_next_id(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = NoteStore(root)
    assert store.next_id() == "note-1"


# ── ContextStore ─────────────────────────────────────────────────────────────


def test_context_save_and_load(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = ContextStore(root)
    ctx = Context(id="context-1", title="Architecture", content="# Overview\n\nDetails here.")
    store.save(ctx)
    contexts, errors = store.load_all()
    assert errors == []
    assert len(contexts) == 1
    assert contexts[0].id == "context-1"
    assert contexts[0].content == "# Overview\n\nDetails here."


def test_context_delete(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = ContextStore(root)
    ctx = Context(id="context-1", title="Temporary")
    store.save(ctx)
    assert store.delete("context-1") is True
    contexts, _ = store.load_all()
    assert contexts == []


# ── SkillStore ────────────────────────────────────────────────────────────────


def test_skill_save_and_load(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = SkillStore(root)
    skill = Skill(name="check-in", description="Daily morning check-in.", content="Run the check-in flow.")
    store.save(skill)
    skills, errors = store.load_all()
    assert errors == []
    assert len(skills) == 1
    assert skills[0].name == "check-in"
    assert skills[0].description == "Daily morning check-in."
    assert skills[0].content == "Run the check-in flow."


def test_skill_delete(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = SkillStore(root)
    skill = Skill(name="check-in", description="Daily morning check-in.")
    store.save(skill)
    assert store.delete("check-in") is True
    skills, _ = store.load_all()
    assert skills == []


# ── ProjectStore (integration) ────────────────────────────────────────────────


def test_project_store_load_empty(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    state = ProjectStore(root).load()
    assert isinstance(state, ProjectState)
    assert state.roles == []
    assert state.milestones == []
    assert state.tasks == []
    assert state.notes == []
    assert state.contexts == []
    assert state.skills == []
    assert state.errors == []


def test_project_store_load_all_types(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    ps = ProjectStore(root)
    ps.roles.save(Role(id="role-1", title="Engineer"))
    ps.milestones.save(Milestone(id="milestone-1", title="v1.0"))
    ps.tasks.save(Task(id="task-1", title="Ship it"))
    ps.notes.save(Note(id="note-1", title="Daily"))
    ps.contexts.save(Context(id="context-1", title="Spec"))
    ps.skills.save(Skill(name="check-in", description="Daily morning check-in."))

    state = ps.load()
    assert len(state.roles) == 1
    assert len(state.milestones) == 1
    assert len(state.tasks) == 1
    assert len(state.notes) == 1
    assert len(state.contexts) == 1
    assert len(state.skills) == 1
    assert state.errors == []


def test_project_store_find_item_path(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    ps = ProjectStore(root)
    ps.roles.save(Role(id="role-1", title="Engineer"))
    ps.tasks.save(Task(id="task-1", title="Ship it"))

    assert ps.find_item_path("role", "role-1") is not None
    assert ps.find_item_path("task", "task-1") is not None
    assert ps.find_item_path("role", "role-99") is None
    assert ps.find_item_path("unknown", "role-1") is None
