#!/usr/bin/env python3
"""Migrate coop_os/ directory layout to the new user/agent/work structure.

Run once from the project root:  python scripts/migrate_disk_layout.py
"""
import shutil
import sys
from pathlib import Path

root = Path.cwd()
ctx = root / "coop_os" / "context"
moves = [
    (ctx / "docs",     root / "coop_os" / "user" / "context"),
    (ctx / "notes",    root / "coop_os" / "user" / "notes"),
    (ctx / "roles",    root / "coop_os" / "work" / "roles"),
    (ctx / "milestones", root / "coop_os" / "work" / "milestones"),
    (ctx / "tasks",    root / "coop_os" / "work" / "tasks"),
    (ctx / "AGENT.md", root / "coop_os" / "agent" / "AGENT.md"),
    (root / "coop_os" / "skills", root / "coop_os" / "agent" / "skills"),
]

for src, dst in moves:
    if not src.exists():
        print(f"skip (missing): {src}")
        continue
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    print(f"moved: {src} -> {dst}")

# Remove now-empty context/ dir
if ctx.exists() and not any(ctx.iterdir()):
    ctx.rmdir()
    print(f"removed empty: {ctx}")

print("Done.")
