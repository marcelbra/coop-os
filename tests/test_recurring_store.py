"""Tests for RecurringTaskStore and OccurrenceStore."""
from __future__ import annotations

from pathlib import Path

import pytest

from coop_os.backend.models import (
    Occurrence,
    OccurrenceStatus,
    RecurringTask,
    RecurringTaskStatus,
    TimePolicy,
)
from coop_os.backend.store import OccurrenceStore, ProjectStore, RecurringTaskStore


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    return root


def test_recurring_task_store_round_trip(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RecurringTaskStore(root)
    rtask = RecurringTask(
        id="rtask-1",
        title="Call mom",
        status=RecurringTaskStatus.ACTIVE,
        milestone="milestone-3",
        rrule="FREQ=WEEKLY;BYDAY=MO",
        dtstart="2026-04-20",
        time_policy=TimePolicy.TIMED,
        start_time="20:00",
        duration_minutes=20,
        timezone="Europe/Amsterdam",
        exdates=["2026-05-04"],
    )
    store.save(rtask)
    loaded, errors = store.load_all()
    assert errors == []
    assert len(loaded) == 1
    first = loaded[0]
    assert first.id == "rtask-1"
    assert first.title == "Call mom"
    assert first.rrule == "FREQ=WEEKLY;BYDAY=MO"
    assert first.time_policy == "timed"
    assert first.duration_minutes == 20
    assert first.timezone == "Europe/Amsterdam"
    assert first.exdates == ["2026-05-04"]


def test_recurring_task_store_next_id(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RecurringTaskStore(root)
    assert store.next_id() == "rtask-1"
    store.save(RecurringTask(id="rtask-1", title="A"))
    assert store.next_id() == "rtask-2"


def test_recurring_task_store_rejects_duplicate_title(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = RecurringTaskStore(root)
    store.save(RecurringTask(id="rtask-1", title="Call mom"))
    with pytest.raises(ValueError):
        store.save(RecurringTask(id="rtask-2", title="Call mom"))


def test_occurrence_store_build_id_and_upsert(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = OccurrenceStore(root)
    assert OccurrenceStore.build_id("rtask-1", "2026-04-20") == "occ-rtask-1-2026-04-20"
    occurrence = store.upsert("rtask-1", "2026-04-20", OccurrenceStatus.DONE, note="called")
    assert occurrence.id == "occ-rtask-1-2026-04-20"
    found = store.get("rtask-1", "2026-04-20")
    assert found is not None
    assert found.status == "done"
    assert found.note == "called"


def test_occurrence_store_upsert_is_idempotent(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = OccurrenceStore(root)
    store.upsert("rtask-1", "2026-04-20", OccurrenceStatus.DONE)
    store.upsert("rtask-1", "2026-04-20", OccurrenceStatus.SKIPPED, note="busy")
    all_items, _ = store.load_all()
    assert len(all_items) == 1
    assert all_items[0].status == "skipped"
    assert all_items[0].note == "busy"


def test_occurrence_store_in_range(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = OccurrenceStore(root)
    store.upsert("rtask-1", "2026-04-20", OccurrenceStatus.DONE)
    store.upsert("rtask-1", "2026-04-27", OccurrenceStatus.DONE)
    store.upsert("rtask-1", "2026-05-04", OccurrenceStatus.SKIPPED)
    in_range = store.in_range("2026-04-21", "2026-05-01")
    assert [occurrence.date for occurrence in in_range] == ["2026-04-27"]


def test_occurrence_store_for_series(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = OccurrenceStore(root)
    store.upsert("rtask-1", "2026-04-20", OccurrenceStatus.DONE)
    store.upsert("rtask-2", "2026-04-21", OccurrenceStatus.DONE)
    store.upsert("rtask-1", "2026-04-27", OccurrenceStatus.SKIPPED)
    dates = [occurrence.date for occurrence in store.for_series("rtask-1")]
    assert sorted(dates) == ["2026-04-20", "2026-04-27"]


def test_occurrence_store_delete(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = OccurrenceStore(root)
    store.upsert("rtask-1", "2026-04-20", OccurrenceStatus.DONE)
    occurrence_id = OccurrenceStore.build_id("rtask-1", "2026-04-20")
    assert store.delete(occurrence_id) is True
    assert store.delete(occurrence_id) is False
    assert store.get("rtask-1", "2026-04-20") is None


def test_project_store_exposes_recurring(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    project = ProjectStore(root)
    project.recurring_tasks.save(RecurringTask(id="rtask-1", title="Call mom"))
    project.occurrences.upsert("rtask-1", "2026-04-20", OccurrenceStatus.DONE)
    state = project.load()
    assert [rtask.id for rtask in state.recurring_tasks] == ["rtask-1"]
    assert [occurrence.id for occurrence in state.occurrences] == ["occ-rtask-1-2026-04-20"]
    assert state.errors == []


def test_occurrence_get_missing_returns_none(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    store = OccurrenceStore(root)
    assert store.get("rtask-1", "2026-04-20") is None
