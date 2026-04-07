from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent

CSS = (_DIR / "app.tcss").read_text(encoding="utf-8") + (_DIR / "confirm_delete.tcss").read_text(encoding="utf-8")
