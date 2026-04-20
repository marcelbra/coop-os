---
description: Push coop-os tasks and recurring tasks to Google Calendar and reconcile per-instance skips/reschedules back. coop-os is the source of truth; Calendar is the projection.
name: calendar-sync
---

## When to run

- User asks to "sync calendar" or "push calendar".
- After a batch of recurring-task edits.
- Once a day to reconcile instance cancellations made in Calendar.

## Contract

- **coop-os is SSOT.** Title/time/RRULE edits in Calendar are overwritten on the next push and flagged as drift.
- **Per-instance cancellations and reschedules in Calendar flow back** as `Occurrence` records and `exdates`. This is the one legitimate direction Calendar is an input — users naturally skip events in their calendar UI.
- **Only items with `sync_to_calendar: true` sync.** Everything else is ignored.

## Steps

### 1. Load state

- Read every `workspace/recurring_tasks/rtask-*.md` where `sync_to_calendar: true`.
- Read every `workspace/tasks/**/description.md` where `sync_to_calendar: true` and `start_date` is non-empty.
- Skip items whose `status` is `archived` or `cancelled` — treat as delete candidates if they have a `calendar_event_id`.

### 2. Classify each item

For each item, compare its current canonical hash against `last_synced_hash`:

```
uv run python -c "
from coop_os.backend.recurrence import canonical_hash_recurring, canonical_hash_task
from coop_os.backend.store import ProjectStore
from pathlib import Path
store = ProjectStore(Path('.'))
state = store.load()
# print id → current hash for everything with sync_to_calendar: true
for rt in state.recurring_tasks:
    if rt.sync_to_calendar:
        print(rt.id, canonical_hash_recurring(rt))
for t in state.tasks:
    if t.sync_to_calendar:
        print(t.id, canonical_hash_task(t))
"
```

Buckets:

| Condition | Action |
|---|---|
| `calendar_event_id == ""` | **CREATE** |
| `calendar_event_id != ""` and `current_hash != last_synced_hash` | **UPDATE** |
| `status in (archived, cancelled)` and `calendar_event_id != ""` | **DELETE** |
| else | verify remote via `get_event`; if `event.updated > last_synced_at`, flag DRIFT |

### 3. Build the event body

**For `RecurringTask`:**
- Title: `rtask.title`
- `recurrence: ["RRULE:<rtask.rrule>"]` — prepend `EXDATE:` lines per `exdate` (e.g. `["RRULE:FREQ=WEEKLY;BYDAY=MO", "EXDATE;VALUE=DATE:20260504"]`)
- If `time_policy == "all_day"`: `start: {date: dtstart}`, `end: {date: dtstart + 1 day}`
- If `time_policy == "timed"`: `start: {dateTime: f"{dtstart}T{start_time}:00", timeZone: timezone}`, `end: dateTime + duration_minutes`, same timezone

**For `Task`:**
- Title: `task.title`
- If `time_policy == "all_day"`: all-day event on `start_date` (or through `end_date` if set)
- If `time_policy == "timed"`: timed block at `start_time` for `duration_minutes` in `timezone`
- No `recurrence` field.

**Default timezone** comes from `config.yml` `workspace_timezone` (currently `Europe/Amsterdam`) when the item leaves it empty.

### 4. Execute via MCP

- CREATE: `mcp__claude_ai_Google_Calendar__create_event` — capture returned `event.id`.
- UPDATE: `mcp__claude_ai_Google_Calendar__update_event` with the same body.
- DELETE: `mcp__claude_ai_Google_Calendar__delete_event`.

Use `calendar_id` if non-empty; otherwise the user's primary calendar.

### 5. Write back

For each pushed item, update the file frontmatter:

- `calendar_event_id` — set on CREATE, cleared on DELETE.
- `last_synced_at` — UTC ISO-8601 (e.g. `2026-04-19T14:30:00Z`).
- `last_synced_hash` — the hash computed in step 2.
- `sync_state` — `synced` (or `drift` / `error`).

Then run `uv run coop-os validate` to confirm files still parse.

### 6. Reconcile occurrences (RecurringTask only)

For each synced series, fetch instances in `[today-14d, today+7d]`:

- `mcp__claude_ai_Google_Calendar__list_events` with `calendarId`, `timeMin`, `timeMax`, `singleEvents: true`.
- Filter to events whose `recurringEventId` matches the series `calendar_event_id`.

For each returned instance:

- **Cancelled** (`status: "cancelled"`): upsert `Occurrence(status=skipped)` for that date, and ensure the date is in `rt.exdates`. Persist via:
  ```
  uv run python -c "
  from coop_os.backend.store import ProjectStore
  from coop_os.backend.models import OccurrenceStatus
  from pathlib import Path
  store = ProjectStore(Path('.'))
  store.occurrences.upsert('rtask-1', '2026-05-04', OccurrenceStatus.SKIPPED, note='cancelled in Calendar')
  "
  ```
- **Overridden** (`start != originalStartTime`): upsert `Occurrence(status=pending, note="rescheduled …")` and do not fight the override on the next push.

### 7. Report

Render a table: `item | action | remote id | drift?`. Summarise errors with file hints so the user can fix and re-run.

## Notes

- **Auth** lives in the Claude Code MCP config; no secrets in the repo.
- **Draft-only Gmail** is a separate safety guarantee; this skill never touches email.
- **Rate limiting**: batches up to ~50 items per run should be fine on the free tier. Chunk if you get 429s.
- **Never hard-delete a series** from inside this skill — only from coop-os (user sets `status: archived`).
