---
description: Weekly review workflow. Best done Sunday evening or Friday afternoon. Covers task progress, habits, goal tracking, and next-week planning.
name: weekly-review
---

## Steps

1. **Review the week**
   - Which tasks moved to `done` this week?
   - Which stalled or were deferred? Why?
   - Any milestones completed or significantly advanced?

2. **Audit recurring tasks**
   - For every active `RecurringTask`, diff expected vs. actual occurrences for the week:
     ```
     uv run python -c "
     from datetime import date, timedelta
     from pathlib import Path
     from coop_os.backend.store import ProjectStore
     from coop_os.backend.recurrence import diff_expected_vs_actual, expected_occurrences
     store = ProjectStore(Path('.'))
     state = store.load()
     today = date.today()
     start_of_week = today - timedelta(days=today.weekday())  # Monday
     end_of_week = start_of_week + timedelta(days=6)
     for rt in state.recurring_tasks:
         if rt.status != 'active':
             continue
         expected = expected_occurrences(rt, start_of_week, end_of_week)
         if not expected:
             continue
         actual = store.occurrences.for_series(rt.id)
         report = diff_expected_vs_actual(expected, actual)
         print(rt.id, rt.title, 'done', len(report.done), 'skipped', len(report.skipped), 'missed', len(report.missed))
     "
     ```
   - For each expected-but-absent date, write a `MISSED` occurrence so the ledger is exhaustive. Use `store.occurrences.upsert(rtask_id, iso_date, OccurrenceStatus.MISSED)`.
   - Render streaks (consecutive weeks where `done_count >= target_count`) and note misses without judgment. Flag `sync_state: drift` items — Calendar edits that weren't reflected back.

3. **Check milestone health**
   - Any milestones with no progress this week?
   - Anything stalling that needs a decision or action?

4. **Plan next week**
   - What are the 3–5 most important things next week?
   - Block time for deep work if needed

5. **Capture reflections**
   - What went well? What would you change?
   - Any patterns worth noting?
