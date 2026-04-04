# Scan Notes

Triggered by: `/scan-notes`, "scan my notes", "let's go through my notes", "process my notes"

## Steps

1. **Load unscanned notes**
   - Read all files in `notes/` where `scanned: false`
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
   - Write directly to the appropriate directory using the template files in `templates/`
   - For tasks: create `tasks/{next_id}-{slug}/description.md`
   - For milestones: create `milestones/{next_id}-{slug}.md`
   - For context updates: edit the relevant `context/roles/{id}-{slug}.md`

5. **Mark notes as scanned**
   - For each processed note: PUT /api/notes/{id} with `scanned: true`