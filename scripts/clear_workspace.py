#!/usr/bin/env python3
"""Clear all managed coop-os workspace content.

Removes workspace data dirs (roles, milestones, tasks), user data dirs
(notes, context), and the session file. Does not touch agent skills.

Usage:
    uv run scripts/clear_workspace.py
    uv run scripts/clear_workspace.py --target /tmp/demo-workspace
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def clear(target: Path) -> None:
    """Delete all managed context under target.

    Removes workspace data dirs (roles, milestones, tasks), user data dirs
    (notes, context), and the session file. Does not touch agent skills.
    The session file lives one level above coop_os/ — the project root.
    """
    workspace_dir = target / "workspace"
    for managed_dir in (
        workspace_dir / "roles",
        workspace_dir / "milestones",
        workspace_dir / "tasks",
        target / "user" / "notes",
        target / "user" / "context",
    ):
        if managed_dir.exists():
            shutil.rmtree(managed_dir)
            print(f"  removed {managed_dir}")

    session_file = target.parent / ".coop-os-session.json"
    if session_file.exists():
        session_file.unlink()
        print(f"  removed {session_file}")


def main() -> None:
    repo_root = Path(__file__).parent.parent
    default_target = repo_root / "coop_os"

    parser = argparse.ArgumentParser(
        description="Clear all managed coop-os workspace content.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run scripts/clear_workspace.py\n"
            "  uv run scripts/clear_workspace.py --target /tmp/demo-workspace\n"
        ),
    )
    parser.add_argument(
        "--target",
        default=str(default_target),
        help=f"Root coop_os directory to clear (default: {default_target})",
    )
    args = parser.parse_args()

    target = Path(args.target)
    print(f"Clearing workspace at: {target}/")
    clear(target)
    print("Done.")


if __name__ == "__main__":
    main()
