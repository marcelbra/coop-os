#!/usr/bin/env python3
"""Reset the coop-os session state file.

Removes .coop-os-session.json from the project root, which causes the TUI to
start with a clean slate: no filters active, no expanded sections, and the
cursor at the default position.

Usage:
    uv run scripts/reset_session.py
    uv run scripts/reset_session.py --target /tmp/demo-workspace
"""

from __future__ import annotations

import argparse
from pathlib import Path


def reset(target: Path) -> None:
    """Delete the session file under target.

    The session file lives one level above coop_os/ — the project root.
    If the file does not exist, this is a no-op.
    """
    session_file = target.parent / ".coop-os-session.json"
    if session_file.exists():
        session_file.unlink()
        print(f"  removed {session_file}")
    else:
        print(f"  nothing to remove ({session_file} not found)")


def main() -> None:
    repo_root = Path(__file__).parent.parent
    default_target = repo_root / "coop_os"

    parser = argparse.ArgumentParser(
        description="Reset the coop-os session state file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run scripts/reset_session.py\n"
            "  uv run scripts/reset_session.py --target /tmp/demo-workspace\n"
        ),
    )
    parser.add_argument(
        "--target",
        default=str(default_target),
        help=f"Root coop_os directory to target (default: {default_target})",
    )
    args = parser.parse_args()

    target = Path(args.target)
    print(f"Resetting session at: {target.parent}/")
    reset(target)
    print("Done.")


if __name__ == "__main__":
    main()
