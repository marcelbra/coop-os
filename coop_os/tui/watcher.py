"""File snapshot watcher for detecting external disk changes.

Maintains an mtime_ns snapshot of all .md files under the watched directories
and reports whether any have changed since the last scan. Used to drive the
TUI's live auto-refresh when the AI agent (or any external process) modifies
files on disk while the app is open.
"""
from __future__ import annotations

import os
from pathlib import Path

_SKIP_DIRS: frozenset[str] = frozenset({".git", "__pycache__", ".mypy_cache", ".ruff_cache"})


class FileSnapshot:
    """Tracks mtime_ns for all .md files under the watched directories.

    Typical usage:
    1. Call build() once at startup to initialise the baseline snapshot.
    2. Call scan() on each poll tick — it returns the set of paths that changed,
       were added, or were removed since the previous scan.
    3. Call mark_written(path) immediately after the app itself writes a file so
       the next scan does not treat that write as an external change.
    """

    def __init__(self, watch_dirs: list[Path]) -> None:
        self._watch_dirs = watch_dirs
        self._snapshot: dict[str, int] = {}

    def build(self) -> None:
        """Take the initial snapshot. Call once after the app has fully loaded."""
        self._snapshot = self._collect()

    def scan(self) -> set[str]:
        """Rescan and return the set of changed path strings since the last scan.

        A path is included if its mtime changed, if it is new, or if it was
        removed. Returns an empty set when nothing changed.
        """
        current = self._collect()
        all_keys = set(current) | set(self._snapshot)
        changed = {key for key in all_keys if current.get(key) != self._snapshot.get(key)}
        self._snapshot = current
        return changed

    def mark_written(self, path: Path) -> None:
        """Advance the snapshot entry for *path* to its current mtime.

        Call this immediately after the app writes a file so the next scan does
        not report that write as an external change (which would incorrectly
        trigger a Case-B warning while the user is editing).
        """
        key = str(path)
        try:
            self._snapshot[key] = os.stat(key).st_mtime_ns
        except OSError:
            pass

    # ── Internal ──────────────────────────────────────────────────────────────

    def _collect(self) -> dict[str, int]:
        """Walk all watched directories and collect mtime_ns for every .md file."""
        result: dict[str, int] = {}
        for watch_dir in self._watch_dirs:
            if not watch_dir.exists():
                continue
            for dirpath, dirnames, filenames in os.walk(watch_dir):
                dirnames[:] = [dirname for dirname in dirnames if dirname not in _SKIP_DIRS]
                for filename in filenames:
                    if not filename.endswith(".md"):
                        continue
                    full_path = os.path.join(dirpath, filename)
                    try:
                        result[full_path] = os.stat(full_path).st_mtime_ns
                    except OSError:
                        pass  # file disappeared mid-scan — skip silently
        return result
