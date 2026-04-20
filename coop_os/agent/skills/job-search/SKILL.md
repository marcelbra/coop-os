---
description: Research European AI/ML companies matching the user's target profile. Surfaces candidates from VC portfolios, funding trackers, job boards, HN "Who is Hiring", and alumni networks. Proposes additions to the candidate pool; optionally promotes applied companies into "<Company> process" tasks under milestone-9.
name: job-search
---

## Purpose

Reproduce a systematic job-search research sweep. The goal is to find AI-native Series A–C (or equivalent) European companies that match the user's target profile — not legacy companies with an AI bolt-on. Every candidate is captured in the pool so nothing is researched twice.

## Required reading before running

- `coop_os/user/context/context-5-Job search profile & pool.md` — profile filter, full candidate pool (acts as exclusion list), and process convention. **Load this first every run.**
- `coop_os/workspace/milestones/milestone-9-Switch jobs — target 130-140k gross.md` — the milestone this work feeds.
- Existing `<Company> process` tasks under `coop_os/workspace/tasks/` — tone reference for any new process task.

## Steps

1. **Load context**
   - Read `context-5` (profile + pool + convention).
   - List existing `<Company> process` tasks under `milestone-9`.
   - Read the umbrella research task (`task-5-Job search research`) for the rolling plan — which sources are queued, which were swept recently.

2. **Pick a search axis for this run** — offer the user a menu, or accept a user-specified axis:

   | Axis | Sources |
   |------|---------|
   | VC portfolio | Index, Balderton, Accel EU, Creandum, La Famiglia, Point Nine, Lakestar, Atomico, EQT Ventures, Northzone, Cherry Ventures, Earlybird, HV Capital, Speedinvest, Molten |
   | Funding tracker | Dealroom.co, Crunchbase, Sifted AI 100, EU-Startups rankings |
   | Job board | Wellfound, Welcome to the Jungle / Otta, Berlin Startup Jobs, SwissDevJobs, Landing.jobs, ai-jobs.net |
   | HN "Who is Hiring" | Latest monthly HN thread, filter for EU + AI/ML |
   | Alumni | ETH AI Center, TU Munich entrepreneurship network, CDTM Munich |
   | Funding-round news | Google Alerts for `"Series A" OR "Series B" AI agent Europe` |

   Run **one axis per session**. Bigger sweeps fragment the review.

3. **Fetch + filter**
   - Use `WebFetch` / `WebSearch` against the chosen source.
   - Apply the profile filter from `context-5`: AI-native, Series A–C (or well-funded seed), <200 people, shipping product, EU / Remote-EU, recent funding.
   - Cross-reference every candidate against the pool table (case-insensitive on `company`). **Skip anything already tracked** — do not re-propose.
   - Target **5–15 net-new candidates per run**.

4. **Propose additions**
   - Present candidates grouped by source.
   - For each: `company · location · funding · backers · 1-line fit note · role URL (if found)`.
   - Flag stage-mismatches (seed / public / >200 people / consultancy) as `stage-mismatch` rather than drop silently — let the user override.
   - Never fabricate funding numbers or backers. If a source doesn't state it, leave the cell `—` and mark the row for manual verification.
   - Ask: **"Which add to the pool as `candidate`? Any to promote to `applied` already?"**

5. **Write approved additions to the pool**
   - Append rows to the table in `context-5-Job search profile & pool.md`.
   - Required columns: `company`, `location`, `funding`, `backers`, `fit_note`, `role_url`, `researched_on` (today), `status`.
   - Default `status: candidate`. Use `applied` only if the user explicitly confirms.
   - The PostToolUse hook runs `uv run coop-os validate` automatically — fix any parse error before moving on.

6. **(Optional) Promote `applied` rows into `<Company> process` tasks**
   - For any new `applied` row, create `coop_os/workspace/tasks/task-{next-id}-<Company> process/description.md`.
   - Frontmatter: `id`, `title: "<Company> process"`, `start_date: today`, `end_date: ''`, `status: todo`, `milestone: milestone-9`, `parent: ''`.
   - Body: one paragraph — current state + next action. Match the tone of existing tasks (`task-1-Altura process`, `task-4-Mistral process`).
   - Determine `task-{next-id}` by reading `coop_os/workspace/tasks/` and taking `max(id) + 1`.

7. **Update the umbrella research task**
   - Append a bullet under "This week's axes" in `task-5-Job search research/description.md`: what axis ran, how many net-new added, what's queued next.
   - Move any surprising market signal (funding, acquisitions, hiring surges) into its "Notes" section.

8. **Wrap up**
   - Summarize: axis swept · companies surfaced · added to pool · promoted to applied.
   - If end of day, suggest `/check-out`.

## Defaults and guardrails

- **Dedup on company name, case-insensitive.** A renamed company (e.g. "Leya" → "Legora") goes in as one row with both names in the `company` cell, separated by `/`.
- **No fabrication.** Funding, backers, headcount — only claim what the source states. `—` for unknowns.
- **Stage-mismatches surfaced, not hidden.** The user may want to pursue a seed company with strong backers (e.g. Mirelo, backed by Index + a16z) even though it fails the Series A–C filter.
- **Acquired / shut down** — status `archived`, with a one-line note (e.g. Humanloop → Anthropic, Jan 2026).
- **One axis per run.** Fragmented sweeps across multiple sources make review impossible.

## Interview-phase convention

This skill stops at the `<Company> process` task. Interview phases scheduled later become **nested subtasks** under the process task's directory — see "Process convention" in `context-5`. Subtask ids come from the global task sequence; `parent` frontmatter is ignored on load (directory nesting is authoritative).
