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

4. **Create files**
   - Write role files to `coop_os/workspace/roles/`
   - Write milestone files to `coop_os/workspace/milestones/`
   - Write task directories to `coop_os/workspace/tasks/`

5. **Wrap up**
   - Summarize what was created
   - Suggest: run `check-in` to activate the workspace
