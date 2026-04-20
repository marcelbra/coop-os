---
description: Daily morning check-in. Reviews calendar, email, and active tasks to surface the top 3 priorities and the single most important thing for the day.
name: check-in
---

## Steps

1. **Check calendar**
   - Pull today's events via Google Calendar
   - Note hard commitments, deadlines, or energy-heavy blocks

2. **Check email**
   - Scan Gmail for anything urgent or requiring action today
   - Only surface what matters — don't summarize everything

3. **Check tasks**
   - Read task files in `tasks/` with status `in_progress`
   - Read task files in `tasks/` with status `todo`
   - Identify what's overdue, what's closest to done, what aligns with today's energy

4. **Check today's recurring occurrences**
   - For every `rtask-*.md` with `status: active`, compute whether today is an expected occurrence and whether an `occ-{rtask-id}-{today}.md` already exists. The Python path:
     ```
     uv run python -c "
     from datetime import date
     from pathlib import Path
     from coop_os.backend.store import ProjectStore
     from coop_os.backend.recurrence import expected_occurrences
     store = ProjectStore(Path('.'))
     state = store.load()
     today = date.today()
     for rt in state.recurring_tasks:
         if rt.status != 'active':
             continue
         if expected_occurrences(rt, today, today):
             existing = store.occurrences.get(rt.id, today.isoformat())
             print(rt.id, rt.title, 'done' if existing and existing.status == 'done' else 'pending')
     "
     ```
   - Surface pending occurrences in the briefing. Offer to mark done/skip inline.

5. **Synthesize and present**
   - Lead with: what's the one most important thing today?
   - Surface top 3 priorities (not more)
   - Flag anything urgent from email or calendar
   - Include today's recurring occurrences in the briefing, marked pending/done

6. **Open the floor**
   - End with: "What's on your mind?" or "Anything to add before we dive in?"
