from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from dateutil.rrule import rrulestr

from coop_os.backend.models import Occurrence, OccurrenceStatus, RecurringTask, Task

_RRULE_PREFIX_RE = re.compile(r"^\s*RRULE\s*:\s*", re.IGNORECASE)


def _strip_prefix(rrule_str: str) -> str:
    return _RRULE_PREFIX_RE.sub("", rrule_str)


def _parse_anchor(dtstart: str) -> datetime:
    """Parse an ISO date or datetime string into a datetime (midnight for dates)."""
    if "T" in dtstart:
        return datetime.fromisoformat(dtstart)
    return datetime.fromisoformat(dtstart + "T00:00:00")


def parse_rrule(rrule_str: str, dtstart: str):
    """Return a dateutil rrule object, raising ValueError on bad input.

    Accepts the RRULE body with or without the leading "RRULE:" prefix.
    """
    body = _strip_prefix(rrule_str)
    if not body:
        raise ValueError("rrule is empty")
    anchor = _parse_anchor(dtstart)
    try:
        return rrulestr(body, dtstart=anchor)
    except Exception as exc:
        raise ValueError(f"invalid rrule: {exc}") from exc


_FREQ_LABEL = {
    "YEARLY": "Yearly",
    "MONTHLY": "Monthly",
    "WEEKLY": "Weekly",
    "DAILY": "Daily",
    "HOURLY": "Hourly",
    "MINUTELY": "Minutely",
    "SECONDLY": "Secondly",
}
_BYDAY_LABEL = {"MO": "Mon", "TU": "Tue", "WE": "Wed", "TH": "Thu", "FR": "Fri", "SA": "Sat", "SU": "Sun"}


def summarize(rrule_str: str) -> str:
    """Return a short human-readable summary of the RRULE, e.g. "Weekly: Mon, Wed".

    Returns an empty string if the RRULE cannot be parsed — callers decide how to surface.
    """
    body = _strip_prefix(rrule_str)
    if not body:
        return ""
    parts: dict[str, str] = {}
    for pair in body.split(";"):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        parts[key.strip().upper()] = value.strip()
    freq = parts.get("FREQ", "")
    interval_raw = parts.get("INTERVAL", "1")
    try:
        interval = int(interval_raw)
    except ValueError:
        interval = 1
    label = _FREQ_LABEL.get(freq, freq.title() if freq else "")
    if not label:
        return ""
    if interval > 1:
        label = f"Every {interval} {label.lower()}"
    byday = parts.get("BYDAY", "")
    if byday:
        days = [_BYDAY_LABEL.get(token.strip().upper(), token) for token in byday.split(",") if token.strip()]
        label += f": {', '.join(days)}"
    return label


def expected_occurrences(rt: RecurringTask, start: date, end: date) -> list[date]:
    """Return series-local dates (inclusive range) that the RRULE would produce.

    Respects UNTIL (via the rrule string), workspace-level `until`, and EXDATE.
    """
    if not rt.rrule or not rt.dtstart:
        return []
    try:
        rule = parse_rrule(rt.rrule, rt.dtstart)
    except ValueError:
        return []
    start_dt = datetime(start.year, start.month, start.day)
    end_dt = datetime(end.year, end.month, end.day, 23, 59, 59)
    until_cap: datetime | None = None
    if rt.until:
        try:
            until_cap = _parse_anchor(rt.until)
        except ValueError:
            until_cap = None
    exdates = set(rt.exdates)
    result: list[date] = []
    for occurrence_dt in rule.between(start_dt, end_dt, inc=True):
        if until_cap is not None and occurrence_dt > until_cap:
            break
        occurrence_date = occurrence_dt.date()
        if occurrence_date.isoformat() in exdates:
            continue
        result.append(occurrence_date)
    return result


def next_occurrences(rt: RecurringTask, after: date, limit: int) -> list[date]:
    """Return up to `limit` future occurrence dates strictly after `after`."""
    if not rt.rrule or not rt.dtstart or limit <= 0:
        return []
    try:
        rule = parse_rrule(rt.rrule, rt.dtstart)
    except ValueError:
        return []
    anchor = datetime(after.year, after.month, after.day, 23, 59, 59)
    exdates = set(rt.exdates)
    result: list[date] = []
    for occurrence_dt in rule:
        if occurrence_dt <= anchor:
            continue
        occurrence_date = occurrence_dt.date()
        if occurrence_date.isoformat() in exdates:
            continue
        result.append(occurrence_date)
        if len(result) >= limit:
            break
    return result


@dataclass
class MissReport:
    done: list[date] = field(default_factory=list)
    skipped: list[date] = field(default_factory=list)
    missed: list[date] = field(default_factory=list)
    pending: list[date] = field(default_factory=list)


def diff_expected_vs_actual(expected: list[date], actual: list[Occurrence]) -> MissReport:
    """Classify expected dates against recorded occurrences.

    Dates present in `expected` but absent from `actual` are reported as missed
    (the ledger-writer decides whether to persist them).
    """
    by_date: dict[str, Occurrence] = {occ.date: occ for occ in actual}
    report = MissReport()
    for expected_date in expected:
        occurrence = by_date.get(expected_date.isoformat())
        if occurrence is None:
            report.missed.append(expected_date)
            continue
        match occurrence.status:
            case OccurrenceStatus.DONE:
                report.done.append(expected_date)
            case OccurrenceStatus.SKIPPED:
                report.skipped.append(expected_date)
            case OccurrenceStatus.MISSED:
                report.missed.append(expected_date)
            case OccurrenceStatus.PENDING:
                report.pending.append(expected_date)
    return report


_SYNC_FIELDS_RECURRING: tuple[str, ...] = (
    "title", "milestone", "role", "time_policy", "start_time",
    "duration_minutes", "timezone", "rrule", "dtstart", "until", "exdates",
)
_SYNC_FIELDS_TASK: tuple[str, ...] = (
    "title", "milestone", "start_date", "end_date", "time_policy", "start_time",
    "duration_minutes", "timezone",
)


def canonical_hash_recurring(rt: RecurringTask) -> str:
    """Deterministic hash of the fields that drive Calendar state for a series."""
    payload = {key: getattr(rt, key) for key in _SYNC_FIELDS_RECURRING}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def canonical_hash_task(task: Task) -> str:
    """Deterministic hash of the fields that drive Calendar state for a single task event."""
    payload = {key: getattr(task, key) for key in _SYNC_FIELDS_TASK}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
