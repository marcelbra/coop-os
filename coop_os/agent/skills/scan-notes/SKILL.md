---
description: Process unscanned notes into tasks and milestones. Reads notes with scanned:false frontmatter, proposes actions, and marks them as processed.
name: scan-notes
---

## Steps

1. **Load unscanned notes**
   - Read all files in `notes/` where frontmatter has `scanned: false`
   - If none found, say so and stop

2. **For each unscanned note**, analyze the content and identify what actions make sense:
   - **Create task** — something specific to do (include suggested title, milestone, labels)
   - **Create milestone** — a new multi-month goal area emerging
   - **No action** — just informational, archive as-is

3. **Present proposals grouped by note**
   - Show the note title and date
   - List each proposed action with enough detail to act on
   - Ask: "Do these look right? Anything to skip or change?"

4. **Execute approved actions** — follow the Authoring Workflow and Workspace Schema in `AGENT.md`:
   - Draft → confirm → write → validate (hook auto-runs `uv run coop-os validate`)
   - Tasks live at `tasks/task-{n}-{title}/description.md`
   - Milestones live at `milestones/milestone-{n}-{title}.md`
   - Use the typed-ID format and valid status enums documented in `AGENT.md`

5. **Mark notes as scanned**
   - Set `scanned: true` in the frontmatter of each processed note file
