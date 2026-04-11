#!/usr/bin/env python3
"""Seed a fresh coop-os workspace with realistic demo data.

Creates 5 roles, 16 milestones, 30 tasks (some nested), agent config,
5 skills, user context documents, and 2 unscanned notes.

Usage:
    uv run scripts/seed_workspace.py
    uv run scripts/seed_workspace.py --target /tmp/demo-workspace
"""

from __future__ import annotations

import argparse
from pathlib import Path


def write_file(path: Path, content: str) -> None:
    """Write content to path, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def seed_roles(workspace_dir: Path) -> None:
    roles_dir = workspace_dir / "roles"

    write_file(
        roles_dir / "role-1-Self.md",
        """\
---
id: role-1
status: active
title: Self
---

Focus on the important things. Produce more, consume less. Build strong daily routines and protect deep work.

**PMS Anchor:** Focus on important, produce > consume, openness to change, balance, fun

**Context:**
- Morning routine: journaling, reading, movement
- Protect deep work blocks — 4h minimum
- Weekly reflection every Sunday
- Therapy 1×/week

**Time Budget:** 3–4h/week
""",
    )

    write_file(
        roles_dir / "role-2-Health.md",
        """\
---
id: role-2
status: active
title: Health
---

Body as a long-term asset. Build sustainable fitness habits, sleep well, and train consistently.

**PMS Anchor:** Body as asset, longevity, eat good, sleep good

**Current regimen:**
- Running: 3×/week
- Strength: 2×/week 45min
- Sleep: target 23:30 bed, 08:00 wake

**Time Budget:** 8–10h/week
""",
    )

    write_file(
        roles_dir / "role-3-Career.md",
        """\
---
id: role-3
status: active
title: Career
---

Build technical depth, ship real things, and grow toward senior engineering. Side projects bridge gaps the day job doesn't cover.

**PMS Anchor:** Build skills, stay curious, ship things, learn by doing, bridge depth with impact

**Context:**
- Day job: software engineer, 4 days/week
- Side project: AI agent tool in early development
- Learning focus: ML/LLM fundamentals

**Time Budget:** 12–15h/week
""",
    )

    write_file(
        roles_dir / "role-4-Relationships.md",
        """\
---
id: role-4
status: active
title: Relationships
---

Invest in and deepen meaningful connections. Create shared memories. Stay intentional about visits and rituals.

**PMS Anchor:** Create memories, patience, listening, deepen friendships, invest in people

**Context:**
- Partner: prioritize quality time, plan trips together
- Family: monthly video calls, annual visit
- Friends: build local social circle

**Time Budget:** 5–8h/week
""",
    )

    write_file(
        roles_dir / "role-5-Finances.md",
        """\
---
id: role-5
status: active
title: Finances
---

Money gives freedom. Make smart, simple decisions. Build an emergency fund, start investing, and cut waste.

**PMS Anchor:** Money gives freedom, smart decisions, simplicity, diversify

**Context:**
- Income: stable employment + occasional freelance
- Goals: 6-month emergency fund, index fund investing, reduce discretionary spend

**Time Budget:** 1–2h/week
""",
    )


def seed_milestones(workspace_dir: Path) -> None:
    milestones_dir = workspace_dir / "milestones"

    # ── Self (role-1) ──────────────────────────────────────────────────────
    write_file(
        milestones_dir / "milestone-1-Establish morning routine.md",
        """\
---
end_date: ''
id: milestone-1
role: role-1
start_date: '2026-04-01'
status: active
title: Establish morning routine
---

A consistent 60-minute morning block: movement, reading, journaling. In place and running on autopilot.
""",
    )

    write_file(
        milestones_dir / "milestone-2-Read 12 books this year.md",
        """\
---
end_date: ''
id: milestone-2
role: role-1
start_date: '2026-01-01'
status: active
title: Read 12 books this year
---

One book per month minimum. Mix of fiction, philosophy, and technical content. Build the reading habit, not just the count.
""",
    )

    write_file(
        milestones_dir / "milestone-3-Complete therapy program.md",
        """\
---
end_date: ''
id: milestone-3
role: role-1
start_date: '2026-03-01'
status: active
title: Complete therapy program
---

Work through the current therapy trajectory with clear goals. Weekly sessions, active homework, measurable progress on relationship patterns.
""",
    )

    # ── Health (role-2) ────────────────────────────────────────────────────
    write_file(
        milestones_dir / "milestone-4-Run first 5K.md",
        """\
---
end_date: ''
id: milestone-4
role: role-2
start_date: '2026-04-01'
status: active
title: Run first 5K
---

Complete a 5K run without stopping. Follow a structured plan. Race date TBD — preferably in June.
""",
    )

    write_file(
        milestones_dir / "milestone-5-Nail sleep protocol.md",
        """\
---
end_date: '2026-04-15'
id: milestone-5
role: role-2
start_date: '2026-03-15'
status: completed
title: Nail sleep protocol
---

Track sleep for 14 days, identify blockers, and establish a consistent sleep/wake schedule. Done — currently maintaining 23:30 / 08:00.
""",
    )

    write_file(
        milestones_dir / "milestone-6-Build gym habit.md",
        """\
---
end_date: ''
id: milestone-6
role: role-2
start_date: '2026-04-10'
status: active
title: Build gym habit
---

2×/week strength training locked in and on autopilot. Non-negotiable, regardless of schedule.
""",
    )

    # ── Career (role-3) ────────────────────────────────────────────────────
    write_file(
        milestones_dir / "milestone-7-Ship side project v1.md",
        """\
---
end_date: ''
id: milestone-7
role: role-3
start_date: '2026-03-01'
status: active
title: Ship side project v1
---

First external user on the AI agent tool. Ruthlessly minimal feature set — one working loop end-to-end.
""",
    )

    write_file(
        milestones_dir / "milestone-8-Complete ML certification.md",
        """\
---
end_date: ''
id: milestone-8
role: role-3
start_date: '2026-02-01'
status: active
title: Complete ML certification
---

Finish the fast.ai Practical Deep Learning track. Project-based, not just videos. Build something with each module.
""",
    )

    write_file(
        milestones_dir / "milestone-9-Build public portfolio.md",
        """\
---
end_date: ''
id: milestone-9
role: role-3
start_date: '2026-04-01'
status: active
title: Build public portfolio
---

Personal website live with 3 case studies. LinkedIn and GitHub up to date. Visible online presence as a senior engineer.
""",
    )

    write_file(
        milestones_dir / "milestone-10-Get senior promotion.md",
        """\
---
end_date: ''
id: milestone-10
role: role-3
start_date: '2026-01-01'
status: active
title: Get senior promotion
---

Clear performance review outcome: senior engineering title or equivalent. Feedback loop established with manager.
""",
    )

    # ── Relationships (role-4) ─────────────────────────────────────────────
    write_file(
        milestones_dir / "milestone-11-Plan summer trip.md",
        """\
---
end_date: ''
id: milestone-11
role: role-4
start_date: '2026-04-01'
status: active
title: Plan summer trip
---

A 1–2 week trip with partner, booked and planned. Destination open — ideally somewhere neither of us has been.
""",
    )

    write_file(
        milestones_dir / "milestone-12-Establish family call rhythm.md",
        """\
---
end_date: ''
id: milestone-12
role: role-4
start_date: '2026-04-01'
status: active
title: Establish family call rhythm
---

Monthly video call with parents and sibling locked in calendar. Consistent, not just reactive.
""",
    )

    write_file(
        milestones_dir / "milestone-13-Deepen local friendships.md",
        """\
---
end_date: ''
id: milestone-13
role: role-4
start_date: '2026-04-01'
status: active
title: Deepen local friendships
---

Move 3 local friendships from casual to close. Dinner parties, regular meetups, shared activities.
""",
    )

    # ── Finances (role-5) ──────────────────────────────────────────────────
    write_file(
        milestones_dir / "milestone-14-Build 6-month emergency fund.md",
        """\
---
end_date: ''
id: milestone-14
role: role-5
start_date: '2026-01-01'
status: active
title: Build 6-month emergency fund
---

6 months of expenses in a high-yield savings account. Current balance tracking toward target.
""",
    )

    write_file(
        milestones_dir / "milestone-15-Start investing.md",
        """\
---
end_date: ''
id: milestone-15
role: role-5
start_date: '2026-04-01'
status: active
title: Start investing
---

First recurring investment in a low-cost index fund. Automate monthly contribution. Simple, not clever.
""",
    )

    write_file(
        milestones_dir / "milestone-16-Cut unnecessary spending.md",
        """\
---
end_date: ''
id: milestone-16
role: role-5
start_date: '2026-04-10'
status: active
title: Cut unnecessary spending
---

Audit all subscriptions and discretionary spending. Cancel anything unused. Target: reduce monthly outgoings by 15%.
""",
    )


def seed_tasks(workspace_dir: Path) -> None:  # noqa: PLR0915
    tasks_dir = workspace_dir / "tasks"

    # ── milestone-1: Morning routine ───────────────────────────────────────
    write_file(
        tasks_dir / "task-1-Design morning routine structure" / "description.md",
        """\
---
end_date: ''
id: task-1
milestone: milestone-1
parent: ''
start_date: '2026-04-01'
status: done
title: Design morning routine structure
---

Map out the ideal morning routine: what goes in, in what order, total time. Draw from existing research and personal energy patterns.
""",
    )

    write_file(
        tasks_dir / "task-1-Design morning routine structure" / "task-2-Shortlist 3 routine frameworks" / "description.md",
        """\
---
end_date: '2026-04-05'
id: task-2
milestone: milestone-1
parent: task-1
start_date: '2026-04-01'
status: done
title: Shortlist 3 routine frameworks
---

Research morning routine approaches. Pick 3 to compare. Write up pros/cons for each.
""",
    )

    write_file(
        tasks_dir / "task-1-Design morning routine structure" / "task-3-Run 1-week morning pilot" / "description.md",
        """\
---
end_date: ''
id: task-3
milestone: milestone-1
parent: task-1
start_date: '2026-04-07'
status: in_progress
title: Run 1-week morning pilot
---

Test the designed routine for 7 consecutive days. Log energy levels and adherence. Adjust and finalize.
""",
    )

    # ── milestone-2: Reading ───────────────────────────────────────────────
    write_file(
        tasks_dir / "task-4-Build reading backlog" / "description.md",
        """\
---
end_date: '2026-04-08'
id: task-4
milestone: milestone-2
parent: ''
start_date: '2026-04-01'
status: done
title: Build reading backlog
---

Collect all books on the to-read list into a single prioritized backlog. 20 titles minimum, ranked by urgency and interest.
""",
    )

    write_file(
        tasks_dir / "task-4-Build reading backlog" / "task-5-Set up reading tracker" / "description.md",
        """\
---
end_date: ''
id: task-5
milestone: milestone-2
parent: task-4
start_date: '2026-04-08'
status: in_progress
title: Set up reading tracker
---

Create a simple tracker to log books read, current progress, and notes per book. A markdown file is fine.
""",
    )

    # ── milestone-3: Therapy ───────────────────────────────────────────────
    write_file(
        tasks_dir / "task-6-Find a therapist" / "description.md",
        """\
---
end_date: ''
id: task-6
milestone: milestone-3
parent: ''
start_date: '2026-04-10'
status: todo
title: Find a therapist
---

Research therapists specializing in relationship patterns and attachment. Book an intake session with at least 2 candidates.
""",
    )

    # ── milestone-4: 5K ────────────────────────────────────────────────────
    write_file(
        tasks_dir / "task-7-Pick a 5K training plan" / "description.md",
        """\
---
end_date: '2026-04-03'
id: task-7
milestone: milestone-4
parent: ''
start_date: '2026-04-01'
status: done
title: Pick a 5K training plan
---

Research and select an 8–10 week 5K training plan suited to current fitness level.
""",
    )

    write_file(
        tasks_dir / "task-7-Pick a 5K training plan" / "task-8-Buy running shoes" / "description.md",
        """\
---
end_date: '2026-04-06'
id: task-8
milestone: milestone-4
parent: task-7
start_date: '2026-04-04'
status: done
title: Buy running shoes
---

Get properly fitted running shoes at a specialist store. Gait analysis if available.
""",
    )

    write_file(
        tasks_dir / "task-7-Pick a 5K training plan" / "task-9-Complete week 1 of plan" / "description.md",
        """\
---
end_date: ''
id: task-9
milestone: milestone-4
parent: task-7
start_date: '2026-04-07'
status: in_progress
title: Complete week 1 of plan
---

Three runs this week as per the plan. Log distance, time, and how it felt.
""",
    )

    # ── milestone-5: Sleep ─────────────────────────────────────────────────
    write_file(
        tasks_dir / "task-10-Track sleep patterns for 14 days" / "description.md",
        """\
---
end_date: '2026-04-04'
id: task-10
milestone: milestone-5
parent: ''
start_date: '2026-03-20'
status: done
title: Track sleep patterns for 14 days
---

Use phone or watch data to log sleep time, wake time, and quality for 14 days. Identify patterns and blockers.
""",
    )

    # ── milestone-6: Gym ───────────────────────────────────────────────────
    write_file(
        tasks_dir / "task-11-Sign up for gym" / "description.md",
        """\
---
end_date: ''
id: task-11
milestone: milestone-6
parent: ''
start_date: '2026-04-10'
status: todo
title: Sign up for gym
---

Find and join a gym within 20 minutes of home. Monthly membership, no long contracts. Basic strength training equipment required.
""",
    )

    write_file(
        tasks_dir / "task-11-Sign up for gym" / "task-12-Find a gym near home" / "description.md",
        """\
---
end_date: ''
id: task-12
milestone: milestone-6
parent: task-11
start_date: '2026-04-10'
status: todo
title: Find a gym near home
---

Search for gyms within 3km. Check reviews, price, and hours. Shortlist top 3 for a trial visit.
""",
    )

    # ── milestone-7: Side project ──────────────────────────────────────────
    write_file(
        tasks_dir / "task-13-Define MVP feature list" / "description.md",
        """\
---
end_date: ''
id: task-13
milestone: milestone-7
parent: ''
start_date: '2026-04-01'
status: in_progress
title: Define MVP feature list
---

Write down the minimal set of features needed for one working loop. No roadmap — just what ships first.
""",
    )

    write_file(
        tasks_dir / "task-13-Define MVP feature list" / "task-14-Write technical spec" / "description.md",
        """\
---
end_date: ''
id: task-14
milestone: milestone-7
parent: task-13
start_date: '2026-04-08'
status: todo
title: Write technical spec
---

One-pager: stack, data model, API surface, deployment target. Enough to start building without re-deciding every 2 days.
""",
    )

    write_file(
        tasks_dir / "task-13-Define MVP feature list" / "task-15-Set up project repo" / "description.md",
        """\
---
end_date: ''
id: task-15
milestone: milestone-7
parent: task-13
start_date: '2026-04-10'
status: todo
title: Set up project repo
---

Create GitHub repo, add CI, basic README, and dev environment setup. Deploy to Fly.io or Railway.
""",
    )

    # ── milestone-8: ML cert ───────────────────────────────────────────────
    write_file(
        tasks_dir / "task-16-Enroll in online ML course" / "description.md",
        """\
---
end_date: '2026-03-01'
id: task-16
milestone: milestone-8
parent: ''
start_date: '2026-02-15'
status: done
title: Enroll in online ML course
---

Sign up for fast.ai Practical Deep Learning Part 1. Schedule dedicated study blocks, 3h/week minimum.
""",
    )

    write_file(
        tasks_dir / "task-16-Enroll in online ML course" / "task-17-Complete module 1" / "description.md",
        """\
---
end_date: '2026-03-15'
id: task-17
milestone: milestone-8
parent: task-16
start_date: '2026-03-01'
status: done
title: Complete module 1
---

Finish lessons 1–3 and build the image classifier project. Write a short reflection on what clicked.
""",
    )

    write_file(
        tasks_dir / "task-16-Enroll in online ML course" / "task-18-Complete module 2" / "description.md",
        """\
---
end_date: ''
id: task-18
milestone: milestone-8
parent: task-16
start_date: '2026-03-20'
status: in_progress
title: Complete module 2
---

Lessons 4–6, NLP and tabular data. Build a text classifier. Notebook published to GitHub.
""",
    )

    # ── milestone-9: Portfolio ─────────────────────────────────────────────
    write_file(
        tasks_dir / "task-19-Write 3 portfolio case studies" / "description.md",
        """\
---
end_date: ''
id: task-19
milestone: milestone-9
parent: ''
start_date: '2026-04-10'
status: todo
title: Write 3 portfolio case studies
---

Document 3 projects in a consistent format: problem, approach, outcome, learnings. 500–800 words each.
""",
    )

    write_file(
        tasks_dir / "task-20-Set up personal website" / "description.md",
        """\
---
end_date: ''
id: task-20
milestone: milestone-9
parent: ''
start_date: '2026-04-10'
status: todo
title: Set up personal website
---

Simple static site: about, projects, writing. No overengineering — ship a clean site in under 2 days. Vercel or Netlify.
""",
    )

    # ── milestone-10: Promotion ────────────────────────────────────────────
    write_file(
        tasks_dir / "task-21-Request performance review feedback" / "description.md",
        """\
---
end_date: ''
id: task-21
milestone: milestone-10
parent: ''
start_date: '2026-04-05'
status: waiting
title: Request performance review feedback
---

Ask manager for explicit feedback on promotion track. What's missing? What's the timeline? Waiting for Q2 review cycle to open.
""",
    )

    # ── milestone-11: Summer trip ──────────────────────────────────────────
    write_file(
        tasks_dir / "task-22-Research trip destinations" / "description.md",
        """\
---
end_date: '2026-04-09'
id: task-22
milestone: milestone-11
parent: ''
start_date: '2026-04-01'
status: done
title: Research trip destinations
---

Shortlist 5 destinations for summer. Criteria: neither of us has been there, good food, nature + city mix.
""",
    )

    write_file(
        tasks_dir / "task-22-Research trip destinations" / "task-23-Book flights" / "description.md",
        """\
---
end_date: ''
id: task-23
milestone: milestone-11
parent: task-22
start_date: '2026-04-10'
status: in_progress
title: Book flights
---

Compare flights for the top 2 shortlisted destinations. Book once agreed with partner. Budget: €400/person.
""",
    )

    write_file(
        tasks_dir / "task-22-Research trip destinations" / "task-24-Plan trip itinerary" / "description.md",
        """\
---
end_date: ''
id: task-24
milestone: milestone-11
parent: task-22
start_date: '2026-04-15'
status: todo
title: Plan trip itinerary
---

Draft a day-by-day itinerary once destination and flights are confirmed. Loose structure — not a minute-by-minute schedule.
""",
    )

    # ── milestone-12: Family calls ─────────────────────────────────────────
    write_file(
        tasks_dir / "task-25-Schedule monthly family video call" / "description.md",
        """\
---
end_date: ''
id: task-25
milestone: milestone-12
parent: ''
start_date: '2026-04-10'
status: todo
title: Schedule monthly family video call
---

Set up a recurring calendar invite for the first Sunday of each month. Confirm with family that the time works.
""",
    )

    # ── milestone-13: Friends ──────────────────────────────────────────────
    write_file(
        tasks_dir / "task-26-Organize dinner for friends" / "description.md",
        """\
---
end_date: ''
id: task-26
milestone: milestone-13
parent: ''
start_date: '2026-04-10'
status: todo
title: Organize dinner for friends
---

Host a dinner at home for 4–6 friends. Good food, no agenda. Build the habit of regular hosting.
""",
    )

    write_file(
        tasks_dir / "task-26-Organize dinner for friends" / "task-27-Send dinner invitations" / "description.md",
        """\
---
end_date: ''
id: task-27
milestone: milestone-13
parent: task-26
start_date: '2026-04-12'
status: todo
title: Send dinner invitations
---

Message 6 people for a dinner in the last week of April. Confirm date and dietary restrictions.
""",
    )

    # ── milestone-14: Emergency fund ───────────────────────────────────────
    write_file(
        tasks_dir / "task-28-Calculate monthly savings capacity" / "description.md",
        """\
---
end_date: '2026-04-05'
id: task-28
milestone: milestone-14
parent: ''
start_date: '2026-04-01'
status: done
title: Calculate monthly savings capacity
---

Review last 3 months of bank statements. Calculate actual monthly surplus after all fixed and variable expenses.
""",
    )

    write_file(
        tasks_dir / "task-29-Open high-yield savings account" / "description.md",
        """\
---
end_date: ''
id: task-29
milestone: milestone-14
parent: ''
start_date: '2026-04-05'
status: in_progress
title: Open high-yield savings account
---

Compare savings accounts. Open one with the highest rate and no lock-in. Set up automatic monthly transfer.
""",
    )

    # ── milestone-15: Investing ────────────────────────────────────────────
    write_file(
        tasks_dir / "task-30-Research index funds" / "description.md",
        """\
---
end_date: ''
id: task-30
milestone: milestone-15
parent: ''
start_date: '2026-04-10'
status: todo
title: Research index funds
---

Compare VWCE and S&P 500 trackers. Decide on a broker. Open account and set up a recurring monthly buy.
""",
    )


def seed_agent(coop_os_dir: Path) -> None:
    agent_dir = coop_os_dir / "agent"

    write_file(
        agent_dir / "AGENT.md",
        """\
# Agent Driver File

This file defines how Claude operates as a personal life co-pilot within coop-os.
Load this file at the start of every session.

---

## Role

You are the user's personal agent. You help manage life across all active roles and milestones — work, health, finances, relationships, and whatever else the user tracks here.

You operate on the coop-os file system. Read and write files according to the structure below.

---

## System Structure

| Path | Contents |
|------|----------|
| `coop_os/workspace/roles/` | One file per life role |
| `coop_os/workspace/milestones/` | Active and completed milestones |
| `coop_os/workspace/tasks/` | Task folders — `{id}-{title}/description.md` each |
| `coop_os/user/notes/` | Raw notes pending review |
| `coop_os/user/context/` | Personal context documents |
| `coop_os/agent/skills/` | Skill definitions — what this agent can do |

---

## Skills

Skills live in `coop_os/agent/skills/`. Invoke the relevant skill when the user's request matches.

| Skill | When to use |
|-------|-------------|
| `check-in` | User wants to start their day, review priorities, or get a morning briefing |
| `check-out` | User wants to wrap up the day, review progress, or plan tomorrow |
| `weekly-review` | User wants a full week retrospective or to plan the coming week |
| `scan-notes` | User wants to process raw notes into tasks or milestones |
| `workspace-setup` | Workspace directories are empty or user wants to import existing context |

---

## Session Setup

At the start of every session (unless a skill is triggered immediately):

1. Load role files from `coop_os/workspace/roles/`
2. Scan `coop_os/workspace/tasks/` for in-progress and overdue items
3. Check `coop_os/workspace/milestones/` for anything stalled or due soon
4. Greet the user with a brief status snapshot: what's active, what needs attention

---

## Operating Principles

- Be direct and structured. Match the user's communication style.
- Don't over-explain.
- When the user is vague, ask one focused question.
- Surface blockers proactively.
- The system itself is a living project — suggest improvements when you notice friction.
""",
    )

    write_file(
        agent_dir / "skills" / "check-in" / "SKILL.md",
        """\
---
description: Daily morning check-in. Reviews calendar, email, and active tasks to
  surface the top 3 priorities and the single most important thing for the day.
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

4. **Synthesize and present**
   - Lead with: what's the one most important thing today?
   - Surface top 3 priorities (not more)
   - Flag anything urgent from email or calendar

5. **Open the floor**
   - End with: "What's on your mind?" or "Anything to add before we dive in?"
""",
    )

    write_file(
        agent_dir / "skills" / "check-out" / "SKILL.md",
        """\
---
description: Daily end-of-day check-out. Reviews what moved, captures loose ends,
  flags blockers, and previews tomorrow's priorities.
name: check-out
---

## Steps

1. **Review today's tasks**
   - What moved from `todo` to `done` or `in_progress`?
   - What was planned but didn't happen? Why?

2. **Capture loose ends**
   - Any decisions made that should be written down?
   - Any new tasks or ideas that surfaced today?

3. **Flag blockers**
   - Is anything `waiting` on someone else?
   - Is any `in_progress` task stuck? What's the blocker?

4. **Preview tomorrow**
   - What are the top 3 things for tomorrow?
   - Any calendar blocks or constraints to account for?

5. **Close out**
   - End with: "Good work today. See you tomorrow."
""",
    )

    write_file(
        agent_dir / "skills" / "scan-notes" / "SKILL.md",
        """\
---
description: Process unscanned notes into tasks and milestones. Reads notes with
  scanned:false frontmatter, proposes actions, and marks them as processed.
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
   - Create tasks: place at `tasks/{next_id}-{title}/description.md`
   - Create milestones: place at `milestones/{next_id}-{title}.md`

5. **Mark notes as scanned**
   - Set `scanned: true` in the frontmatter of each processed note file
""",
    )

    write_file(
        agent_dir / "skills" / "weekly-review" / "SKILL.md",
        """\
---
description: Weekly review workflow. Best done Sunday evening or Friday afternoon.
  Covers task progress, habits, goal tracking, and next-week planning.
name: weekly-review
---

## Steps

1. **Review the week**
   - Which tasks moved to `done` this week?
   - Which stalled or were deferred? Why?
   - Any milestones completed or significantly advanced?

2. **Check habits**
   - Review `recurring-habits.md` — which habits hit target frequency?
   - Note wins and misses without judgment

3. **Check milestone health**
   - Any milestones with no progress this week?
   - Anything stalling that needs a decision or action?

4. **Plan next week**
   - What are the 3–5 most important things next week?
   - Block time for deep work if needed

5. **Capture reflections**
   - What went well? What would you change?
   - Any patterns worth noting?
""",
    )

    write_file(
        agent_dir / "skills" / "workspace-setup" / "SKILL.md",
        """\
---
description: Bootstrap or expand a coop-os workspace. Gathers context, drafts the
  hierarchy, confirms with user, then creates files.
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
""",
    )


def seed_user(coop_os_dir: Path) -> None:
    user_dir = coop_os_dir / "user"

    write_file(
        user_dir / "context" / "context-1-Personal Mission Statement.md",
        """\
---
id: context-1
title: Personal Mission Statement
---

# Personal Mission Statement

*Pure values and principles — the "why". Last updated: April 2026*

---

## Self

- Focus on the important things in life
- Produce more. Consume less.
- Always be open to change and a bit of risk
- Read and stay up to date with current ideas
- Try new things to widen the horizon
- Find balance between extremes
- Don't forget to have fun

---

## Health

- Keep the heart young
- Build strength that lasts into old age
- Prevent injuries, stay mobile and flexible
- Eat well. Sleep well.

---

## Career

- Build skills and refine them over time
- Stay curious across domains
- Solve real problems — build for real users
- Bridge technical depth with business impact
- Ship things. Learn by doing.

---

## Relationships

- Create memories with the people who matter
- Patience, listening, presence
- Invest in friendships, don't let them drift
- Build something with family

---

## Finances

- Money gives freedom — make smart, simple decisions
- Diversify. Stay flexible.
- Don't over-optimize. Keep it boring.
""",
    )

    write_file(
        user_dir / "context" / "context-2-Life Framework Overview.md",
        """\
---
id: context-2
title: Life Framework Overview
---

# Life Framework Overview

This system is built on a three-layer hierarchy:

**Personal Mission Statement (PMS)** → the "why". Pure values, not actions. Reviewed quarterly.

**Roles** → the "what". The 5–8 areas of life that matter. Each role has a clear focus, context, and time budget.

**Milestones** → multi-month goals within a role. Concrete outcomes, not habits. Each milestone belongs to exactly one role.

**Tasks** → the actual work. Nested folders under `workspace/tasks/`. Each task has a status and links to a milestone.

---

## Review Cadence

| Frequency | What |
|-----------|------|
| Daily | Check-in (morning) + Check-out (evening) |
| Weekly | Weekly review (Sunday evening) |
| Monthly | Milestone health check |
| Quarterly | PMS review + role rebalancing |

---

## Principles

- Milestones are outcomes, not activities.
- One task in progress at a time per role, when possible.
- If something's been `waiting` for more than 2 weeks, make a decision.
- The system should help you focus, not create more busywork.
""",
    )

    write_file(
        user_dir / "context" / "context-3-Recurring Habits.md",
        """\
---
id: context-3
title: Recurring Habits
---

# Recurring Habits

Habits are not tasks — they don't live in the task system. They're tracked here as a reference for the weekly review.

| Habit | Role | Frequency | Duration |
|-------|------|-----------|----------|
| Morning journaling | Self | 5×/week | 15 min |
| Reading | Self | 7×/week | 30 min |
| Running | Health | 3×/week | 30–45 min |
| Strength training | Health | 2×/week | 45 min |
| Meditation | Self | 5×/week | 10 min |
| Weekly reflection | Self | 1×/week | 30 min |
| Family call | Relationships | 1×/month | 60 min |
""",
    )

    write_file(
        user_dir / "context" / "docs" / "reading-list.md",
        """\
# Reading List

Books to read this year, roughly prioritized.

## In Progress

- *Deep Work* — Cal Newport

## Up Next

- *The Almanack of Naval Ravikant* — Eric Jorgenson
- *Thinking, Fast and Slow* — Daniel Kahneman
- *The Psychology of Money* — Morgan Housel

## Backlog

- *Atomic Habits* — James Clear
- *Zero to One* — Peter Thiel
- *The Pragmatic Programmer* — David Thomas & Andrew Hunt
- *Designing Data-Intensive Applications* — Martin Kleppmann
- *A Philosophy of Software Design* — John Ousterhout
- *The Mom Test* — Rob Fitzpatrick
""",
    )

    write_file(
        user_dir / "notes" / "note-1-Weekly braindump.md",
        """\
---
date: '2026-04-10'
id: note-1
scanned: false
title: Weekly braindump
---

Things on my mind this week:

- Need to finally book those flights for the summer trip — we keep saying we'll do it
- The ML course module 2 is taking longer than expected, might need to drop the pace
- Should start the personal website this weekend — even a one-pager would be enough
- Been putting off calling family again. Need to make the recurring calendar invite actually happen.
- Finances feel a bit unstructured — want to automate savings and stop manually tracking
""",
    )

    write_file(
        user_dir / "notes" / "note-2-Project ideas.md",
        """\
---
date: '2026-04-09'
id: note-2
scanned: false
title: Project ideas
---

Random ideas I don't want to lose:

1. CLI tool that generates a daily brief from tasks + calendar — basically an automated check-in
2. Browser extension that blocks distracting sites during deep work blocks
3. Simple habit tracker that posts a weekly summary to a private Slack channel
4. A Notion-to-markdown sync tool — tired of being locked in

Not sure any of these are worth building right now. Maybe a quick spike on #1 since it's adjacent to the side project.
""",
    )


def main() -> None:
    repo_root = Path(__file__).parent.parent
    default_target = repo_root / "coop_os"

    parser = argparse.ArgumentParser(
        description="Seed a fresh coop-os workspace with demo data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run scripts/seed_workspace.py\n"
            "  uv run scripts/seed_workspace.py --target /tmp/demo-workspace\n"
        ),
    )
    parser.add_argument(
        "--target",
        default=str(default_target),
        help=f"Root coop_os directory to seed into (default: {default_target})",
    )
    args = parser.parse_args()

    target = Path(args.target)

    print(f"Seeding workspace at: {target}/")

    workspace_dir = target / "workspace"
    seed_roles(workspace_dir)
    seed_milestones(workspace_dir)
    seed_tasks(workspace_dir)
    seed_agent(target)
    seed_user(target)

    print("Done.")
    print(f"  roles:      5   → {workspace_dir}/roles/")
    print(f"  milestones: 16  → {workspace_dir}/milestones/")
    print(f"  tasks:      30  → {workspace_dir}/tasks/")
    print(f"  skills:     5   → {target}/agent/skills/")
    print(f"  user docs:  4   → {target}/user/context/")
    print(f"  notes:      2   → {target}/user/notes/")


if __name__ == "__main__":
    main()
