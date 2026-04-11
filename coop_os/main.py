from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coop_os.backend.store import ProjectStore
from coop_os.iterm_launch import launch as iterm_launch
from coop_os.tui import CoopOSApp


def _cmd_start(root: Path) -> None:
    CoopOSApp(root=root).run()


def _cmd_launch(root: Path, horizontal: bool) -> None:
    iterm_launch(root, horizontal=horizontal)


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

    launch = sub.add_parser("launch", help="Open iTerm2 with TUI and agent panes side by side")
    launch.add_argument("--root", type=Path, default=Path.cwd(),
                        help="Project root directory (default: cwd)")
    launch.add_argument("--horizontal", action="store_true",
                        help="Split top/bottom instead of left/right")

    args = p.parse_args()
    cmd: str | None = args.cmd
    root: Path = getattr(args, "root", Path.cwd())

    if cmd == "start":
        _cmd_start(root.resolve())
    elif cmd == "validate":
        _cmd_validate(root.resolve())
    elif cmd == "launch":
        _cmd_launch(root.resolve(), horizontal=args.horizontal)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
