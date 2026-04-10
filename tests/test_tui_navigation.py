from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import pytest

from coop_os.backend.models import Milestone, Role, Task, TaskStatus
from coop_os.backend.store import ProjectStore
from coop_os.tui.app import CoopOSApp
from coop_os.tui.nav import ContentNav, FileNav, Nav, StructuralNav, choose_file_neighbor, choose_same_section_neighbor
from coop_os.tui.widgets import ContentPanel, NavTree


def _seed_workspace(root: Path) -> None:
    store = ProjectStore(root)
    for i in range(1, 4):
        store.roles.save(Role(id=f"role-{i}", title=f"Role {i}"))
    for i in range(1, 4):
        store.milestones.save(Milestone(id=f"milestone-{i}", title=f"Milestone {i}", role="role-1"))
    store.tasks.save(Task(id="task-1", title="Task 1", status=TaskStatus.TODO))
    store.tasks.save(Task(id="task-2", title="Task 1.1", parent="task-1", status=TaskStatus.WAITING))
    store.tasks.save(Task(id="task-3", title="Task 2", status=TaskStatus.DONE))


@asynccontextmanager
async def _run_app(root: Path) -> AsyncIterator[tuple[CoopOSApp, Any]]:
    app = CoopOSApp(root)
    async with app.run_test() as pilot:
        await pilot.pause()
        yield app, pilot


def _cursor_nav(tree: NavTree) -> Nav:
    node = tree.cursor_node
    assert node is not None
    data = node.data
    assert data is not None
    assert isinstance(data, (ContentNav, StructuralNav))
    return data


async def _press_and_pause(pilot: Any, *keys: str) -> None:
    for key in keys:
        await pilot.press(key)
        await pilot.pause()


@pytest.mark.parametrize(
    ("previous_nav", "previous_ids", "current_navs", "expected"),
    [
        (
            ContentNav("milestone", "milestone-2", "milestones"),
            ["milestone-1", "milestone-2", "milestone-3"],
            [
                ContentNav("milestone", "milestone-1", "milestones"),
                ContentNav("milestone", "milestone-2", "milestones"),
                ContentNav("milestone", "milestone-3", "milestones"),
            ],
            ContentNav("milestone", "milestone-2", "milestones"),
        ),
        (
            ContentNav("milestone", "milestone-2", "milestones"),
            ["milestone-1", "milestone-2", "milestone-3"],
            [
                ContentNav("milestone", "milestone-1", "milestones"),
                ContentNav("milestone", "milestone-3", "milestones"),
            ],
            ContentNav("milestone", "milestone-3", "milestones"),
        ),
        (
            ContentNav("milestone", "milestone-3", "milestones"),
            ["milestone-1", "milestone-2", "milestone-3"],
            [
                ContentNav("milestone", "milestone-1", "milestones"),
                ContentNav("milestone", "milestone-2", "milestones"),
            ],
            ContentNav("milestone", "milestone-2", "milestones"),
        ),
        (
            ContentNav("milestone", "milestone-2", "milestones"),
            ["milestone-1", "milestone-2", "milestone-3"],
            [],
            None,
        ),
    ],
)
def test_choose_same_section_neighbor(
    previous_nav: ContentNav, previous_ids: list[str], current_navs: list[ContentNav], expected: ContentNav | None
) -> None:
    assert choose_same_section_neighbor(previous_nav, previous_ids, current_navs) == expected


def test_enter_on_collapsed_branch_moves_to_first_child(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(StructuralNav("section", "tasks"))
            await pilot.pause()
            await _press_and_pause(pilot, "right")
            assert _cursor_nav(tree) == ContentNav("task", "task-1", "tasks")

            await _press_and_pause(pilot, "enter")
            assert _cursor_nav(tree) == ContentNav("task", "task-2", "tasks")

    asyncio.run(scenario())


def test_right_on_collapsed_branch_moves_to_first_child(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(StructuralNav("section", "tasks"))
            await pilot.pause()
            await _press_and_pause(pilot, "right", "right")
            assert _cursor_nav(tree) == ContentNav("task", "task-2", "tasks")

    asyncio.run(scenario())


def test_right_on_leaf_enters_edit_mode(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            content = app.query_one(ContentPanel)
            tree.focus_nav(ContentNav("task", "task-3", "tasks"))
            await pilot.pause()

            await _press_and_pause(pilot, "right")
            assert _cursor_nav(tree) == ContentNav("task", "task-3", "tasks")
            assert content.is_editing
            assert app.selected == ContentNav("task", "task-3", "tasks")

    asyncio.run(scenario())


def test_right_on_expanded_branch_enters_edit_mode(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            content = app.query_one(ContentPanel)
            tree.focus_nav(StructuralNav("section", "tasks"))
            await pilot.pause()

            await _press_and_pause(pilot, "right", "right", "left")
            assert _cursor_nav(tree) == ContentNav("task", "task-1", "tasks")

            await _press_and_pause(pilot, "right")
            assert _cursor_nav(tree) == ContentNav("task", "task-1", "tasks")
            assert content.is_editing
            assert app.selected == ContentNav("task", "task-1", "tasks")

    asyncio.run(scenario())


def test_down_from_last_child_moves_to_next_sibling_outside_subtree(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(StructuralNav("section", "tasks"))
            await pilot.pause()
            await _press_and_pause(pilot, "right", "enter")
            assert _cursor_nav(tree) == ContentNav("task", "task-2", "tasks")

            await _press_and_pause(pilot, "down")
            assert _cursor_nav(tree) == ContentNav("task", "task-3", "tasks")

    asyncio.run(scenario())


def test_up_from_next_sibling_returns_to_parent_not_previous_descendant(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(StructuralNav("section", "tasks"))
            await pilot.pause()
            await _press_and_pause(pilot, "right", "enter", "down")
            assert _cursor_nav(tree) == ContentNav("task", "task-3", "tasks")

            await _press_and_pause(pilot, "up")
            assert _cursor_nav(tree) == ContentNav("task", "task-1", "tasks")

    asyncio.run(scenario())


def test_reload_preserves_section_header_focus(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(StructuralNav("section", "tasks"))
            await pilot.pause()
            assert _cursor_nav(tree) == StructuralNav("section", "tasks")

            app.sm.role_filters = {"role-1"}
            app.reload_state()
            await pilot.pause()
            assert _cursor_nav(tree) == StructuralNav("section", "tasks")

    asyncio.run(scenario())


def test_reload_moves_filtered_milestone_to_next_visible_neighbor(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(ContentNav("milestone", "milestone-2", "milestones"))
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("milestone", "milestone-2", "milestones")

            app.sm.milestone_filters = {"milestone-1", "milestone-3"}
            app.reload_state()
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("milestone", "milestone-3", "milestones")

    asyncio.run(scenario())


def test_reload_moves_filtered_milestone_to_previous_visible_neighbor_when_no_next(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(ContentNav("milestone", "milestone-3", "milestones"))
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("milestone", "milestone-3", "milestones")

            app.sm.milestone_filters = {"milestone-1", "milestone-2"}
            app.reload_state()
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("milestone", "milestone-2", "milestones")

    asyncio.run(scenario())


def test_reload_moves_filtered_milestone_to_section_header_when_section_is_empty(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(ContentNav("milestone", "milestone-2", "milestones"))
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("milestone", "milestone-2", "milestones")

            app.sm.role_filters = {"role-2"}
            app.reload_state()
            await pilot.pause()
            assert _cursor_nav(tree) == StructuralNav("section", "milestones")

    asyncio.run(scenario())


def test_reload_moves_filtered_role_to_next_visible_neighbor(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(ContentNav("role", "role-2", "roles"))
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("role", "role-2", "roles")

            app.sm.role_filters = {"role-1", "role-3"}
            app.reload_state()
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("role", "role-3", "roles")

    asyncio.run(scenario())


def test_reload_moves_filtered_role_to_previous_visible_neighbor_when_no_next(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(ContentNav("role", "role-3", "roles"))
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("role", "role-3", "roles")

            app.sm.role_filters = {"role-1", "role-2"}
            app.reload_state()
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("role", "role-2", "roles")

    asyncio.run(scenario())


def test_reload_moves_filtered_role_to_section_header_when_section_is_empty(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(ContentNav("role", "role-2", "roles"))
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("role", "role-2", "roles")

            app.sm.role_filters = {"inactive"}
            app.reload_state()
            await pilot.pause()
            assert _cursor_nav(tree) == StructuralNav("section", "roles")

    asyncio.run(scenario())


def test_reload_moves_filtered_task_to_next_visible_neighbor(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(ContentNav("task", "task-2", "tasks"))
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("task", "task-2", "tasks")

            app.sm.task_filters = {TaskStatus.TODO.value, TaskStatus.DONE.value}
            app.reload_state()
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("task", "task-3", "tasks")

    asyncio.run(scenario())


def test_reload_moves_filtered_task_to_previous_visible_neighbor_when_no_next(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(ContentNav("task", "task-3", "tasks"))
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("task", "task-3", "tasks")

            app.sm.task_filters = {TaskStatus.TODO.value, TaskStatus.WAITING.value}
            app.reload_state()
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("task", "task-1", "tasks")

    asyncio.run(scenario())


def test_reload_moves_filtered_task_to_section_header_when_section_is_empty(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(ContentNav("task", "task-3", "tasks"))
            await pilot.pause()
            assert _cursor_nav(tree) == ContentNav("task", "task-3", "tasks")

            app.sm.task_filters = {TaskStatus.CANCELLED.value}
            app.reload_state()
            await pilot.pause()
            assert _cursor_nav(tree) == StructuralNav("section", "tasks")

    asyncio.run(scenario())


def test_next_nav_after_delete_for_top_level_task_prefers_next_sibling(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            await pilot.pause()
            next_nav = app.next_nav_after_delete(ContentNav("task", "task-1", "tasks"))
            assert next_nav == ContentNav("task", "task-3", "tasks")

    asyncio.run(scenario())


def test_next_nav_after_delete_for_lone_subtask_returns_parent(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            await pilot.pause()
            next_nav = app.next_nav_after_delete(ContentNav("task", "task-2", "tasks"))
            assert next_nav == ContentNav("task", "task-1", "tasks")

    asyncio.run(scenario())


# ── choose_file_neighbor ──────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("current", "previous", "surviving", "expected"),
    [
        # exact match survives
        ("/t/aaa.md", ["/t/aaa.md", "/t/zzz.md"], ["/t/aaa.md", "/t/zzz.md"], "/t/aaa.md"),
        # deleted first → prefer next
        ("/t/aaa.md", ["/t/aaa.md", "/t/zzz.md"], ["/t/zzz.md"], "/t/zzz.md"),
        # deleted last → prefer previous
        ("/t/zzz.md", ["/t/aaa.md", "/t/zzz.md"], ["/t/aaa.md"], "/t/aaa.md"),
        # no survivors
        ("/t/aaa.md", ["/t/aaa.md"], [], None),
    ],
)
def test_choose_file_neighbor(
    current: str, previous: list[str], surviving: list[str], expected: str | None
) -> None:
    assert choose_file_neighbor(current, previous, surviving) == expected


# ── task_file fallback on reload ──────────────────────────────────────────────

def _seed_workspace_with_task_extras(root: Path) -> tuple[Path, Path, Path]:
    store = ProjectStore(root)
    store.tasks.save(Task(id="task-1", title="Task 1", status=TaskStatus.TODO))
    task_dirs = store.tasks.all_task_dirs()
    task1_dir = task_dirs["task-1"]
    aaa = task1_dir / "aaa.md"
    subdir = task1_dir / "bbb-dir"
    zzz = task1_dir / "zzz.md"
    aaa.write_text("# AAA")
    subdir.mkdir()
    (subdir / "file.md").write_text("# inner")
    zzz.write_text("# ZZZ")
    return aaa, subdir, zzz


def test_reload_moves_missing_task_file_to_next_surviving_sibling(tmp_path: Path) -> None:
    aaa, _subdir, zzz = _seed_workspace_with_task_extras(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(FileNav("task_file", aaa))
            await pilot.pause()
            assert tree.cursor_node is not None
            assert tree.cursor_node.data == FileNav("task_file", aaa)

            aaa.unlink()
            app.reload_state()
            await pilot.pause()

            assert tree.cursor_node is not None
            assert tree.cursor_node.data == FileNav("task_dir", _subdir)

    asyncio.run(scenario())


def test_reload_moves_missing_task_file_to_previous_surviving_sibling_when_no_next(tmp_path: Path) -> None:
    aaa, _subdir, zzz = _seed_workspace_with_task_extras(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(FileNav("task_file", zzz))
            await pilot.pause()
            assert tree.cursor_node is not None
            assert tree.cursor_node.data == FileNav("task_file", zzz)

            zzz.unlink()
            app.reload_state()
            await pilot.pause()

            assert tree.cursor_node is not None
            assert tree.cursor_node.data == FileNav("task_dir", _subdir)

    asyncio.run(scenario())


def test_reload_moves_missing_task_file_to_task_dir_sibling(tmp_path: Path) -> None:
    """Fallback crosses kind boundary: task_file deleted, nearest sibling is task_dir."""
    aaa, subdir, zzz = _seed_workspace_with_task_extras(tmp_path)

    async def scenario() -> None:
        async with _run_app(tmp_path) as (app, pilot):
            tree = app.query_one(NavTree)
            tree.focus_nav(FileNav("task_file", aaa))
            await pilot.pause()

            aaa.unlink()
            zzz.unlink()  # remove both files, only subdir remains
            app.reload_state()
            await pilot.pause()

            assert tree.cursor_node is not None
            assert tree.cursor_node.data == FileNav("task_dir", subdir)

    asyncio.run(scenario())
