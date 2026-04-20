"""Tests for recurrence helpers — RRULE parsing, summaries, expected-vs-actual diff, hash stability."""
from __future__ import annotations

from datetime import date

import pytest

from coop_os.backend.models import (
    Occurrence,
    OccurrenceStatus,
    RecurringTask,
    Task,
    TimePolicy,
)
from coop_os.backend.recurrence import (
    canonical_hash_recurring,
    canonical_hash_task,
    diff_expected_vs_actual,
    expected_occurrences,
    next_occurrences,
    parse_rrule,
    summarize,
)


def _series(**overrides) -> RecurringTask:
    fields = dict(
        id="rtask-1",
        title="Call mom",
        rrule="FREQ=WEEKLY;BYDAY=MO",
        dtstart="2026-04-20",  # a Monday
    )
    fields.update(overrides)
    return RecurringTask(**fields)


def test_parse_rrule_accepts_bare_and_prefixed() -> None:
    from datetime import datetime
    rule_bare = parse_rrule("FREQ=WEEKLY", "2026-04-20")
    rule_prefixed = parse_rrule("RRULE:FREQ=WEEKLY", "2026-04-20")
    anchor = datetime(2026, 4, 19)
    assert list(rule_bare.xafter(anchor, count=1)) == list(rule_prefixed.xafter(anchor, count=1))


def test_parse_rrule_rejects_empty() -> None:
    with pytest.raises(ValueError):
        parse_rrule("", "2026-04-20")


def test_parse_rrule_rejects_bad_syntax() -> None:
    with pytest.raises(ValueError):
        parse_rrule("THIS_IS_NOT_A_RULE", "2026-04-20")


def test_summarize_weekly_with_byday() -> None:
    assert summarize("FREQ=WEEKLY;BYDAY=MO,WE") == "Weekly: Mon, Wed"


def test_summarize_interval_pluralises() -> None:
    assert summarize("FREQ=WEEKLY;INTERVAL=2") == "Every 2 weekly"


def test_summarize_monthly() -> None:
    assert summarize("FREQ=MONTHLY;BYMONTHDAY=1") == "Monthly"


def test_summarize_empty() -> None:
    assert summarize("") == ""


def test_summarize_bad_input_returns_empty() -> None:
    assert summarize("not an rrule") == ""


def test_expected_occurrences_returns_dates_in_range() -> None:
    rt = _series()
    dates = expected_occurrences(rt, date(2026, 4, 1), date(2026, 5, 1))
    assert dates == [date(2026, 4, 20), date(2026, 4, 27)]


def test_expected_occurrences_excludes_exdates() -> None:
    rt = _series(exdates=["2026-04-27"])
    dates = expected_occurrences(rt, date(2026, 4, 1), date(2026, 5, 1))
    assert dates == [date(2026, 4, 20)]


def test_expected_occurrences_respects_until() -> None:
    rt = _series(until="2026-04-22")
    dates = expected_occurrences(rt, date(2026, 4, 1), date(2026, 5, 1))
    assert dates == [date(2026, 4, 20)]


def test_expected_occurrences_month_boundary() -> None:
    rt = _series(dtstart="2026-04-27")  # Monday
    dates = expected_occurrences(rt, date(2026, 4, 27), date(2026, 5, 4))
    assert date(2026, 4, 27) in dates
    assert date(2026, 5, 4) in dates


def test_expected_occurrences_empty_when_no_rrule() -> None:
    rt = RecurringTask(id="rtask-2", title="x")
    assert expected_occurrences(rt, date(2026, 1, 1), date(2027, 1, 1)) == []


def test_next_occurrences_skips_past() -> None:
    rt = _series()
    upcoming = next_occurrences(rt, date(2026, 4, 20), limit=2)
    assert upcoming == [date(2026, 4, 27), date(2026, 5, 4)]


def test_next_occurrences_applies_exdate() -> None:
    rt = _series(exdates=["2026-04-27"])
    upcoming = next_occurrences(rt, date(2026, 4, 20), limit=2)
    assert upcoming == [date(2026, 5, 4), date(2026, 5, 11)]


def test_diff_classifies_statuses() -> None:
    expected = [date(2026, 4, 20), date(2026, 4, 27), date(2026, 5, 4)]
    actual = [
        Occurrence(id="o1", recurring_task_id="rtask-1", date="2026-04-20", status=OccurrenceStatus.DONE),
        Occurrence(id="o2", recurring_task_id="rtask-1", date="2026-04-27", status=OccurrenceStatus.SKIPPED),
    ]
    report = diff_expected_vs_actual(expected, actual)
    assert report.done == [date(2026, 4, 20)]
    assert report.skipped == [date(2026, 4, 27)]
    assert report.missed == [date(2026, 5, 4)]


def test_canonical_hash_stable_under_noop_edit() -> None:
    rt_1 = _series()
    rt_2 = _series()
    assert canonical_hash_recurring(rt_1) == canonical_hash_recurring(rt_2)


def test_canonical_hash_changes_with_rrule_change() -> None:
    before = canonical_hash_recurring(_series())
    after = canonical_hash_recurring(_series(rrule="FREQ=WEEKLY;BYDAY=TU"))
    assert before != after


def test_canonical_hash_ignores_sync_state() -> None:
    """`sync_state` and `last_synced_at` are intentionally excluded from the canonical hash,
    so a successful sync never trips drift detection on the next run."""
    before = canonical_hash_recurring(_series())
    after = canonical_hash_recurring(_series(calendar_event_id="abc", last_synced_at="2026-04-20T10:00:00"))
    assert before == after


def test_canonical_hash_task_round_trip() -> None:
    task = Task(id="task-1", title="t", start_date="2026-04-20", time_policy=TimePolicy.TIMED,
                start_time="09:00", duration_minutes=30, timezone="Europe/Amsterdam")
    before = canonical_hash_task(task)
    after = canonical_hash_task(task.model_copy(update={"calendar_event_id": "abc"}))
    assert before == after
