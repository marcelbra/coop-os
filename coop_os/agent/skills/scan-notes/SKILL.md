---
description: Process unscanned notes into tasks and milestones. Reads notes with scanned:false
  frontmatter, proposes actions, and marks them as processed.
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

4. **Execute approved actions**
   - Create tasks / milestones as confirmed
   - Tasks: use `tasks/template.md`, place at `tasks/{next_id}-{slug}/description.md`
   - Milestones: use `milestones/template.md`, place at `milestones/{next_id}-{slug}.md`

5. **Mark notes as scanned**
   - Set `scanned: true` in the frontmatter of each processed note file