from __future__ import annotations

import argparse
import sys
from pathlib import Path

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


def _cmd_validate(root: Path) -> None:
    store = ProjectStore(root)
    state = store.load()
    if state.errors:
        print(f"Found {len(state.errors)} parse error(s):\n")
        for err in state.errors:
            print(f"  File:  {err.file}")
            print(f"  Error: {err.error}\n")
        sys.exit(1)
    else:
        r, m, t, c = len(state.roles), len(state.milestones), len(state.tasks), len(state.contexts)
        print(f"OK — {r} roles, {m} milestones, {t} tasks, {c} contexts parsed successfully.")


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
