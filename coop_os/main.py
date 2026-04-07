from __future__ import annotations

import argparse
from pathlib import Path

from coop_os.tui import CoopOSApp


def main() -> None:
    p = argparse.ArgumentParser(description="coop-os: personal life OS")
    sub = p.add_subparsers(dest="cmd")

    start = sub.add_parser("start", help="Start the TUI")
    start.add_argument("--root", type=Path, default=Path.cwd(),
                       help="Project root directory (default: cwd)")

    args = p.parse_args()

    if args.cmd == "start":
        CoopOSApp(root=args.root.resolve()).run()
    else:
        p.print_help()


if __name__ == "__main__":
    main()
