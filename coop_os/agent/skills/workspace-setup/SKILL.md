---
description: Bootstrap or expand a coop-os workspace. Gathers context, drafts the hierarchy, confirms with user, then creates files.
name: workspace-setup
---

## Steps

1. **Gather context**
   - Ask: What are your main life areas right now?
   - Ask: What are you actively working toward in each area?
   - Ask: Any existing notes or lists to import?

2. **Draft hierarchy**
   - Propose roles (5–8 life areas)
   - Propose milestones per role (1–3 per role, active goals only)
   - Propose seed tasks for any clear next actions

3. **Confirm with user**
   - Show the full proposed structure before creating anything
   - Ask: "Does this feel right? Anything to add, remove, or rename?"

4. **Create files** — follow the Authoring Workflow and Workspace Schema in `AGENT.md`:
   - For every file: draft → confirm with user → write → validate (hook auto-runs `uv run coop-os validate`) → fix and re-validate until clean
   - Roles: `workspace/roles/role-{n}-{title}.md`
   - Milestones: `workspace/milestones/milestone-{n}-{title}.md`
   - Tasks: `workspace/tasks/task-{n}-{title}/description.md`
   - Use the typed-ID format, valid status enums, and `end_date` (not `deadline`) as documented in `AGENT.md`

5. **Wrap up**
   - Summarize what was created
   - Suggest: run `check-in` to activate the workspace
