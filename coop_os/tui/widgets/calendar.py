from __future__ import annotations

import calendar as _cal_mod
from datetime import date as _date
from typing import Any

from textual.events import Key
from textual.message import Message
from textual.widget import Widget


class CalendarWidget(Widget):
    """Inline popup calendar for date field selection.

    Posts ``DateSelected`` when the user confirms a day, or ``Dismissed``
    when they press Escape or Left from the leftmost header position.
    """

    can_focus = True

    _MONTHS: list[str] = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    _DAYS: list[str] = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    class DateSelected(Message):
        def __init__(self, date: _date) -> None:
            super().__init__()
            self.date = date

    class Dismissed(Message):
        pass

    def __init__(
        self,
        initial: _date | None = None,
        attr_key: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        base = initial or _date.today()
        self._year: int = base.year
        self._month: int = base.month
        self.attr_key: str = attr_key
        self._mode: str = "cal"         # "cal" | "month" | "year"
        self._drop_cursor: int = 0
        # ("header", col) where col: 0=<  1=month  2=year  3=>
        # ("day", row, col) where row/col index the day grid
        self._focus: tuple[Any, ...] = ("header", 0)
        focus_date = initial if initial is not None else _date.today()
        if focus_date.year == self._year and focus_date.month == self._month:
            self._init_focus(focus_date)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _weeks(self) -> list[list[int | None]]:
        """Weeks as 7-element lists (Mo=0..Su=6). None for empty cells."""
        first_iso, num_days = _cal_mod.monthrange(self._year, self._month)
        # ISO Mon=0..Sun=6 — already Monday-first
        first_col = first_iso
        weeks: list[list[int | None]] = []
        week: list[int | None] = [None] * 7
        col = first_col
        for day in range(1, num_days + 1):
            week[col] = day
            col += 1
            if col == 7:
                weeks.append(week)
                week = [None] * 7
                col = 0
        if any(d is not None for d in week):
            weeks.append(week)
        return weeks

    def _year_range(self) -> list[int]:
        """Return the list of years [year-10 … year+10] for the year picker dropdown."""
        return list(range(self._year - 10, self._year + 11))

    def _init_focus(self, d: _date) -> None:
        """Position _focus on the day-grid cell that corresponds to the given date on first render."""
        for r, week in enumerate(self._weeks()):
            for c, day in enumerate(week):
                if day == d.day:
                    self._focus = ("day", r, c)
                    return

    def _adjust_height(self) -> None:
        if self._mode == "cal":
            self.styles.height = 2 + len(self._weeks())
        elif self._mode == "month":
            self.styles.height = 13
        else:
            self.styles.height = 1 + len(self._year_range())

    # ── Rendering ──────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._adjust_height()

    def _highlight(self, text: str, active: bool) -> str:
        return f"[reverse]{text}[/reverse]" if active else text

    def _header_line(self) -> str:
        focus = self._focus
        in_hdr = focus[0] == "header"
        prev = self._highlight("<", in_hdr and focus[1] == 0)
        mname = self._MONTHS[self._month - 1]
        month = self._highlight(mname, in_hdr and focus[1] == 1)
        year = self._highlight(str(self._year), in_hdr and focus[1] == 2)
        nxt = self._highlight(">", in_hdr and focus[1] == 3)
        return f"{prev} {month}  {year}  {nxt}"

    def render(self) -> str:
        if self._mode == "cal":
            lines = [self._header_line(), " ".join(self._DAYS)]
            for r, week in enumerate(self._weeks()):
                cells = []
                for c, day in enumerate(week):
                    if day is None:
                        cells.append("  ")
                    else:
                        txt = f"{day:2d}"
                        cells.append(self._highlight(txt, self._focus == ("day", r, c)))
                lines.append(" ".join(cells))
            return "\n".join(lines)

        elif self._mode == "month":
            lines = [self._header_line()]
            for i, m in enumerate(self._MONTHS):
                cur = i == self._drop_cursor
                label = f"> {m}" if cur else f"  {m}"
                lines.append(self._highlight(label, cur))
            return "\n".join(lines)

        else:  # year
            lines = [self._header_line()]
            for i, y in enumerate(self._year_range()):
                cur = i == self._drop_cursor
                label = f"> {y}" if cur else f"  {y}"
                lines.append(self._highlight(label, cur))
            return "\n".join(lines)

    # ── Key handling ───────────────────────────────────────────────────────

    def on_key(self, event: Key) -> None:
        if self._mode == "cal":
            self._cal_key(event)
        else:
            self._drop_key(event)

    def _cal_key(self, event: Key) -> None:  # noqa: C901
        key = event.key
        focus = self._focus

        if key == "escape":
            event.prevent_default()
            event.stop()
            self.post_message(CalendarWidget.Dismissed())

        elif key == "left":
            event.prevent_default()
            event.stop()
            if focus[0] == "header":
                if focus[1] > 0:
                    self._focus = ("header", focus[1] - 1)
                else:
                    self.post_message(CalendarWidget.Dismissed())
                    return
            elif focus[0] == "day":
                self._step_day(-1)
            self.refresh()

        elif key == "right":
            event.prevent_default()
            event.stop()
            if focus[0] == "header" and focus[1] < 3:
                self._focus = ("header", focus[1] + 1)
            elif focus[0] == "day":
                self._step_day(+1)
            self.refresh()

        elif key == "up":
            event.prevent_default()
            event.stop()
            if focus[0] == "day":
                if focus[1] == 0:
                    # Top row of days → jump to header <
                    self._focus = ("header", 0)
                else:
                    self._move_row(focus[1] - 1, focus[2])
            self.refresh()

        elif key == "down":
            event.prevent_default()
            event.stop()
            if focus[0] == "header":
                weeks = self._weeks()
                if weeks:
                    for c, d in enumerate(weeks[0]):
                        if d is not None:
                            self._focus = ("day", 0, c)
                            break
            elif focus[0] == "day":
                self._move_row(focus[1] + 1, focus[2])
            self.refresh()

        elif key == "enter":
            event.prevent_default()
            event.stop()
            if focus[0] == "header":
                self._header_action(focus[1])
            elif focus[0] == "day":
                weeks = self._weeks()
                day = weeks[focus[1]][focus[2]]
                if day:
                    self.post_message(
                        CalendarWidget.DateSelected(_date(self._year, self._month, day))
                    )
                    return
            self.refresh()

    def _drop_key(self, event: Key) -> None:
        key = event.key
        n = 12 if self._mode == "month" else len(self._year_range())

        if key in ("escape", "left"):
            event.prevent_default()
            event.stop()
            self._mode = "cal"
            self._adjust_height()
            self.refresh()

        elif key == "up":
            event.prevent_default()
            event.stop()
            self._drop_cursor = max(0, self._drop_cursor - 1)
            self.refresh()

        elif key == "down":
            event.prevent_default()
            event.stop()
            self._drop_cursor = min(n - 1, self._drop_cursor + 1)
            self.refresh()

        elif key == "enter":
            event.prevent_default()
            event.stop()
            if self._mode == "month":
                self._month = self._drop_cursor + 1
            else:
                self._year = self._year_range()[self._drop_cursor]
            self._mode = "cal"
            self._adjust_height()
            self.refresh()

    def _header_action(self, col: int) -> None:
        if col == 0:
            self._prev_month()
        elif col == 1:
            self._mode = "month"
            self._drop_cursor = self._month - 1
            self._adjust_height()
        elif col == 2:
            self._mode = "year"
            years = self._year_range()
            self._drop_cursor = years.index(self._year)
            self._adjust_height()
        elif col == 3:
            self._next_month()

    def _prev_month(self) -> None:
        if self._month == 1:
            self._month, self._year = 12, self._year - 1
        else:
            self._month -= 1
        self._adjust_height()

    def _next_month(self) -> None:
        if self._month == 12:
            self._month, self._year = 1, self._year + 1
        else:
            self._month += 1
        self._adjust_height()

    def _step_day(self, delta: int) -> None:
        """Move focus one day left/right, wrapping across rows."""
        focus = self._focus
        weeks = self._weeks()
        r, c = focus[1], focus[2]
        while True:
            c += delta
            if c < 0:
                r -= 1
                c = 6
            elif c > 6:
                r += 1
                c = 0
            if r < 0 or r >= len(weeks):
                return
            if weeks[r][c] is not None:
                self._focus = ("day", r, c)
                return

    def _move_row(self, target_row: int, col: int) -> None:
        """Move to target_row at same column (or nearest valid day)."""
        weeks = self._weeks()
        if target_row < 0 or target_row >= len(weeks):
            return
        if weeks[target_row][col] is not None:
            self._focus = ("day", target_row, col)
            return
        for dc in range(1, 7):
            if col + dc <= 6 and weeks[target_row][col + dc] is not None:
                self._focus = ("day", target_row, col + dc)
                return
            if col - dc >= 0 and weeks[target_row][col - dc] is not None:
                self._focus = ("day", target_row, col - dc)
                return
