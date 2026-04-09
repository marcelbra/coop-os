---
name: workspace-setup
description: Bootstrap a coop-os workspace from scratch. Use when workspace directories are empty or non-existent, when importing existing notes/files into the hierarchy, or when the user describes their life/work context and wants it structured as roles → milestones → tasks.
---

## Steps

### 1. Check Current State

Scan what already exists:
```
coop_os/workspace/roles/       ← any .md files?
coop_os/workspace/milestones/  ← any .md files?
coop_os/workspace/tasks/       ← any subdirs with description.md?
coop_os/user/context/          ← any personal context present?
```

Partial setups are fine — only add what's missing.

### 2. Gather Context

Look at what the user already gave you before asking anything.

**If their message contains substantive context** (roles, goals, life areas mentioned directly), acknowledge it and ask only about additional files:
> "You've already shared a good amount of context. Do you also have any notes or files to read through? If so, give me the path. Otherwise I'll work from what you've shared."

**If their message is thin**, ask more openly:
> "Do you have existing notes, documents, or files to use as a starting point — a folder of markdown notes, a project brief, a todo list? If so, give me the path."

If they point to a directory → go to step 3.
If they say no or gave context verbally → skip to step 4.

### 3. Read and Catalog the Context Directory

List all files by type:
- **Text-readable** (`.md`, `.txt`, `.json`, `.yaml`, `.csv`, etc.): read fully
- **Code files** (`.py`, `.js`, etc.): read — may contain comments revealing roles/goals
- **Binary/asset files** (images, PDFs, etc.): note names, infer from context

Extract signals from both files **and** the user's own words:

| Signal type | What to look for |
|-------------|-----------------|
| **Roles** | Life areas, identities, recurring contexts ("in my work as...", "as a parent...") |
| **Milestones** | Goals with endpoints ("I want to finish...", "by Q3...", named projects) |
| **Tasks** | Concrete action items, todos, "- [ ]", things in progress |
| **Context** | Bio, background, values — anything informational |

Never silently skip non-text files — ask the user what to do with each group.

### 4. Draft the Hierarchy

The chain must always be valid end-to-end: every milestone needs a role, every task needs a milestone.

- **Roles missing?** Infer from milestones' theme, or propose "General" — explain reasoning, ask.
- **Milestones also missing?** Propose "Ongoing Work" placeholder — explain, ask.
- **Only general text?** Extract key facts into `coop_os/user/context/` markdown files instead.
- **Non-text files?** Ask: copy to context dir with a companion `.md` description, or attach to a specific task?

### 5. Confirm Everything — One Decision at a Time

**Never create anything without explicit user approval.**

Present the full draft mapping, then go through it:
- Say what you're creating (role / milestone / task / context file), its title, where it's attached, and what it's based on
- Bundle related decisions of the same type; never bundle unrelated decisions
- Wait for clear approval before writing anything

Good:
> "I'd like to create three roles: Designer, Parent, and Runner. Keep all three, or adjust any?"

> "For the milestone 'Launch new website', I'd attach it to Designer. Does that make sense?"

Bad:
> "Does everything look good?" ← too vague

### 6. Create the Files

Write in order: roles → milestones → tasks → context files.

**Role** — `coop_os/workspace/roles/{id}-{slug}.md`
```markdown
---
id: role-1
title: Role Title
status: active
---

{description}
```

**Milestone** — `coop_os/workspace/milestones/{id}-{slug}.md`
```markdown
---
id: milestone-1
title: Milestone Title
status: active
start_date: 'YYYY-MM-DD'
end_date: ''
role: role-1
---

{description}
```

**Task** — `coop_os/workspace/tasks/{id}-{slug}/description.md`
```markdown
---
id: task-1
title: Task Title
status: todo
start_date: 'YYYY-MM-DD'
end_date: ''
milestone: milestone-1
parent: ''
---

{description}
```

**Context file** — `coop_os/user/context/{name}.md` — free-form markdown, H1 title, no frontmatter.

**ID + slug rules:** IDs are sequential per type (`role-1`, `role-2`, `milestone-1`, `task-1`). Slugs are kebab-case, max 40 chars.

**Non-text files:** Copy to agreed location + create a companion `.md` at the same path describing the file.

**On placeholder tasks:** When a milestone's tasks aren't named yet, don't create 3 near-identical placeholders. Create one clearly-labeled placeholder or ask the user for specifics first.

### 7. Wrap Up

Tell the user what was created:
> "Done. Created: 2 roles, 3 milestones, 7 tasks, 1 context file. Everything's in `coop_os/workspace/`. Run `make run` to see it in the TUI."

Note anything skipped or that needs follow-up.

---

*If the user gave any personal background — even verbally — consider distilling key facts into `coop_os/user/context/about-me.md`. Ask first.*
