---
id: skill-3
command: /scan-notes
---

## Steps

1. **Load unscanned notes**
   - Read all files in `notes/` where frontmatter has `scanned: false`
   - If none found, say so and stop

2. **For each unscanned note**, analyze the content and identify what actions make sense:
   - **Create task** — something specific to do (include suggested title, milestone, labels)
   - **Create milestone** — a new multi-month goal area emerging
   - **Update context** — a role, belief, or life-area fact has changed
   - **No action** — just informational, archive as-is

3. **Present proposals grouped by note**
   - Show the note title and date
   - List each proposed action with enough detail to act on
   - Ask: "Do these look right? Anything to skip or change?"

4. **Execute approved actions**
   - Create tasks / milestones / update context files as confirmed
   - Use templates from `templates/`
   - Tasks: `tasks/{next_id}-{slug}/description.md`
   - Milestones: `milestones/{next_id}-{slug}.md`
   - Context updates: `context/roles/{id}-{slug}.md`

5. **Mark notes as scanned**
   - Set `scanned: true` in the frontmatter of each processed note file
