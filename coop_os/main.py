from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coop_os.backend.models import ParseError, RecurringTask, Task
from coop_os.backend.recurrence import parse_rrule
from coop_os.backend.store import ProjectStore
from coop_os.tui import CoopOSApp


def _ensure_skills_installed(root: Path) -> None:
    """Abort with a clear message if agent skills are not installed at ``<root>/.claude/skills``.

    Skills are shipped as source under ``coop_os/agent/skills`` and must be installed into
    the project's ``.claude/skills`` directory via the ``skills`` npm CLI before the app can run.
    """
    skills_dir = root / ".claude" / "skills"
    if skills_dir.is_dir() and any(skills_dir.iterdir()):
        return
    message_lines = [
        "error: agent skills are not installed.",
        f"  expected directory: {skills_dir}",
        "",
        "Install them with one of:",
        "  npx skills add marcelbra/coop-os                    # from PyPI",
        "  npx --yes skills add ./coop_os/agent/skills --all   # from a clone",
        "  make install                                        # from a clone (runs the above)",
        "",
        "Requires Node.js / npx: https://nodejs.org",
    ]
    print("\n".join(message_lines), file=sys.stderr)
    sys.exit(1)


def _cmd_start(root: Path) -> None:
    _ensure_skills_installed(root)
    CoopOSApp(root=root).run()


_ISO_DATE_RE = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?)?$")
_HHMM_RE = __import__("re").compile(r"^\d{2}:\d{2}$")


def _validate_time_policy(
    item: Task | RecurringTask, label: str, errors: list[ParseError], file_hint: str
) -> None:
    """Enforce time-policy consistency for Task and RecurringTask."""
    if item.time_policy == "all_day":
        if item.start_time or item.duration_minutes:
            errors.append(ParseError(
                file=file_hint,
                error=f"{label}: time_policy=all_day but start_time/duration_minutes set",
            ))
    else:
        if not item.start_time:
            errors.append(ParseError(file=file_hint, error=f"{label}: time_policy=timed requires start_time"))
        elif not _HHMM_RE.match(item.start_time):
            errors.append(ParseError(
                file=file_hint, error=f"{label}: start_time '{item.start_time}' must be HH:MM"
            ))
        if item.duration_minutes <= 0:
            errors.append(ParseError(
                file=file_hint, error=f"{label}: time_policy=timed requires duration_minutes > 0"
            ))


def _validate_rrule_and_dates(rtask: RecurringTask, hint: str, errors: list[ParseError]) -> None:
    """Validate RRULE parsing, dtstart/until ISO format, ordering, and EXDATE format."""
    if rtask.rrule:
        if not rtask.dtstart:
            errors.append(ParseError(file=hint, error=f"{rtask.id}: rrule requires dtstart"))
        else:
            try:
                parse_rrule(rtask.rrule, rtask.dtstart)
            except ValueError as exc:
                errors.append(ParseError(file=hint, error=f"{rtask.id}: {exc}"))
    for iso_field, iso_value in (("dtstart", rtask.dtstart), ("until", rtask.until)):
        if iso_value and not _ISO_DATE_RE.match(iso_value):
            errors.append(ParseError(
                file=hint, error=f"{rtask.id}: {iso_field}='{iso_value}' not ISO date/time"
            ))
    if rtask.until and rtask.dtstart and rtask.until < rtask.dtstart:
        errors.append(ParseError(file=hint, error=f"{rtask.id}: until before dtstart"))
    for exdate in rtask.exdates:
        if not _ISO_DATE_RE.match(exdate):
            errors.append(ParseError(file=hint, error=f"{rtask.id}: exdate '{exdate}' not ISO date"))


def _validate_recurring_task(
    rtask: RecurringTask, milestone_ids: set[str], role_ids: set[str], errors: list[ParseError]
) -> None:
    hint = f"recurring_tasks/{rtask.id}"
    if rtask.milestone and rtask.milestone not in milestone_ids:
        errors.append(ParseError(file=hint, error=f"{rtask.id}: unknown milestone '{rtask.milestone}'"))
    if rtask.role and rtask.role not in role_ids:
        errors.append(ParseError(file=hint, error=f"{rtask.id}: unknown role '{rtask.role}'"))
    _validate_time_policy(rtask, rtask.id, errors, hint)
    _validate_rrule_and_dates(rtask, hint, errors)


def _validate_task_sync(
    task: Task, milestone_ids: set[str], errors: list[ParseError]
) -> None:
    hint = f"tasks/{task.id}"
    if task.milestone and task.milestone not in milestone_ids:
        errors.append(ParseError(file=hint, error=f"{task.id}: unknown milestone '{task.milestone}'"))
    _validate_time_policy(task, task.id, errors, hint)


def _cmd_validate(root: Path) -> None:
    store = ProjectStore(root)
    state = store.load()

    extra_errors: list[ParseError] = []
    milestone_ids = {milestone.id for milestone in state.milestones}
    role_ids = {role.id for role in state.roles}
    rtask_ids = {rtask.id for rtask in state.recurring_tasks}

    for task in state.tasks:
        _validate_task_sync(task, milestone_ids, extra_errors)
    for rtask in state.recurring_tasks:
        _validate_recurring_task(rtask, milestone_ids, role_ids, extra_errors)
    for occurrence in state.occurrences:
        hint = f"occurrences/{occurrence.id}"
        if occurrence.recurring_task_id not in rtask_ids:
            extra_errors.append(ParseError(
                file=hint, error=f"{occurrence.id}: unknown recurring_task '{occurrence.recurring_task_id}'"
            ))
        if not _ISO_DATE_RE.match(occurrence.date):
            extra_errors.append(ParseError(file=hint, error=f"{occurrence.id}: date '{occurrence.date}' not ISO"))

    all_errors = list(state.errors) + extra_errors
    if all_errors:
        print(f"Found {len(all_errors)} parse error(s):\n")
        for err in all_errors:
            print(f"  File:  {err.file}")
            print(f"  Error: {err.error}\n")
        sys.exit(1)
    r = len(state.roles)
    m = len(state.milestones)
    t = len(state.tasks)
    rt = len(state.recurring_tasks)
    occ = len(state.occurrences)
    c = len(state.contexts)
    summary = (
        f"OK — {r} roles, {m} milestones, {t} tasks, {rt} recurring, "
        + f"{occ} occurrences, {c} contexts parsed successfully."
    )
    print(summary)


def main() -> None:
    p = argparse.ArgumentParser(description="coop-os: personal life OS")
    sub = p.add_subparsers(dest="cmd")

    start = sub.add_parser("start", help="Start the TUI")
    start.add_argument("--root", type=Path, default=Path.cwd(),
                       help="Project root directory (default: cwd)")

    validate = sub.add_parser("validate", help="Parse all workspace files and report errors")
    validate.add_argument("--root", type=Path, default=Path.cwd(),
                          help="Project root directory (default: cwd)")

    args = p.parse_args()
    cmd: str | None = args.cmd
    root: Path = getattr(args, "root", Path.cwd())

    if cmd == "start":
        _cmd_start(root.resolve())
    elif cmd == "validate":
        _cmd_validate(root.resolve())
    else:
        p.print_help()


if __name__ == "__main__":
    main()
