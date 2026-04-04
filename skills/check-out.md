# Check-out Routine

Triggered by: "check out", "let's check out", "wrap up", "end of day", "signing off", "that's it for today"

## Steps

1. **Review what moved today**
   - Run: `backlog task list -s "In Progress" --plain`
   - Ask Marcel: "What did you actually get done today?" — don't assume, ask
   - Update task statuses based on his answers (`backlog task edit <id> -s Done` etc.)
   - Add notes or final summaries to completed tasks

2. **Capture loose ends**
   - "Anything that came up today that's not in the backlog yet?"
   - Create tasks for anything new with `backlog task create`

3. **Flag blockers**
   - Any task stuck? Note it with `backlog task edit <id> --append-notes "Blocked: ..."`

4. **Preview tomorrow**
   - Pull tomorrow's calendar events
   - Suggest top 3 priorities for tomorrow based on tasks + calendar
   - Keep it brief — just plant the seed

5. **Close**
   - One sentence on how the day went (honest, not cheerleader)
   - "Rest well." and done.