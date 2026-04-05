from __future__ import annotations

import calendar as _cal_mod
from datetime import date as _date
from pathlib import Path
from typing import Any

import frontmatter as _fm
from textual import on
from textual.containers import Horizontal, ScrollableContainer
from textual.events import Click, Key, MouseDown
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Header, Input, Label, Markdown, Rule, TextArea, Tree

from agent_os.models import ProjectState
from agent_os.tui.nav import Nav, truncate_label

# ── Structured editor field definitions ───────────────────────────────────────

# (attr_key, display_label, visible_for_kinds, readonly)
FIELD_DEFS: list[tuple[str, str, frozenset[str], bool]] = [
    ("title",        "title",      frozenset({"milestone", "task", "note"}),                False),
    ("command",      "command",    frozenset({"skill"}),                                    False),
    ("date",         "date",       frozenset({"note"}),                                     False),
    ("scanned",      "scanned",    frozenset({"note"}),                                     False),
    ("start_date",   "start date", frozenset({"milestone"}),                                False),
    ("end_date",     "end date",   frozenset({"milestone"}),                                False),
    ("status",       "status",     frozenset({"milestone", "task"}),                        False),
    ("milestone",    "milestone",  frozenset({"task"}),                                     False),
    ("label",        "label",      frozenset({"task"}),                                     False),
    ("created_date", "created",    frozenset({"task"}),                                     False),
    ("id",           "id",         frozenset({"milestone", "task", "note", "skill"}),       True),
]

DATE_FIELDS: frozenset[str] = frozenset({"start_date", "end_date", "date", "created_date"})
SELECT_FIELDS: frozenset[str] = frozenset({"status", "label", "milestone", "scanned"})

BODY_ATTR: dict[str, str] = {
    "milestone": "description",
    "task": "description",
    "note": "content",
    "skill": "content",
}


class AppConfig:
    def __init__(
        self,
        task_statuses: dict[str, str],
        milestone_statuses: dict[str, str],
        label: list[str],
    ) -> None:
        self.task_statuses = task_statuses        # value -> icon
        self.milestone_statuses = milestone_statuses
        self.label = label


def _read_config(root: Path) -> AppConfig:
    """Parse config.yml into an AppConfig. No external YAML library needed."""
    config_path = root / "config.yml"
    task_statuses: dict[str, str] = {}
    milestone_statuses: dict[str, str] = {}
    label: list[str] = []

    if not config_path.exists():
        return AppConfig(task_statuses, milestone_statuses, label)

    section: str | None = None
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "task_statuses:":
            section = "task_statuses"
        elif stripped == "milestone_statuses:":
            section = "milestone_statuses"
        elif stripped == "label:":
            section = "label"
        elif stripped.startswith("- ") and section == "label":
            label.append(stripped[2:].strip())
        elif ": " in stripped and section in ("task_statuses", "milestone_statuses"):
            key, _, val = stripped.partition(": ")
            icon = val.strip().strip('"')
            if section == "task_statuses":
                task_statuses[key.strip()] = icon
            else:
                milestone_statuses[key.strip()] = icon

    return AppConfig(task_statuses, milestone_statuses, label)


class FixedHeader(Header):
    """Header that does not grow when clicked."""

    def _on_click(self) -> None:
        pass


class DetailTextArea(TextArea):
    """TextArea that posts ExitRequested when ← is pressed at column 0."""

    class ExitRequested(Message):
        """User wants to leave edit mode."""

    def on_mount(self) -> None:
        self.styles.scrollbar_size_vertical = 0
        self.styles.scrollbar_size_horizontal = 0

    def on_key(self, event: Key) -> None:
        if event.key == "left" and self.cursor_location[1] == 0:
            event.prevent_default()
            event.stop()
            self.post_message(DetailTextArea.ExitRequested())


class FieldInput(Input):
    """Input field that navigates between fields (↑/↓) and exits edit mode (←)."""

    class Navigate(Message):
        def __init__(self, direction: int) -> None:
            super().__init__()
            self.direction = direction  # -1 = up, +1 = down

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._select_on_next_focus: bool = False

    def on_focus(self) -> None:
        if self._select_on_next_focus:
            self._select_on_next_focus = False
            self.call_after_refresh(self.action_select_all)
        else:
            self.call_after_refresh(self.action_home)

    def on_key(self, event: Key) -> None:
        if event.key == "up":
            event.prevent_default()
            event.stop()
            self.post_message(FieldInput.Navigate(-1))
        elif event.key == "down":
            event.prevent_default()
            event.stop()
            self.post_message(FieldInput.Navigate(+1))
        elif event.key == "left" and self.cursor_position == 0:
            event.prevent_default()
            event.stop()
            self.post_message(DetailTextArea.ExitRequested())


class DateFieldInput(FieldInput):
    """FieldInput with ISO date (YYYY-MM-DD) validation. Reverts on bad input."""

    class CalendarRequested(Message):
        def __init__(self, attr_key: str, current_value: str) -> None:
            super().__init__()
            self.attr_key = attr_key
            self.current_value = current_value

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._prev_value: str = ""

    def on_focus(self) -> None:
        super().on_focus()
        self._prev_value = self.value

    def on_blur(self) -> None:
        val = self.value.strip()
        if not val:
            return
        try:
            _date.fromisoformat(val)
        except ValueError:
            self.app.notify(
                f'Invalid date "{val}" — expected YYYY-MM-DD',
                severity="error",
                timeout=4,
            )
            self.value = self._prev_value

    def on_key(self, event: Key) -> None:
        super().on_key(event)
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            attr_key = (self.id or "").removeprefix("se-inp-")
            self.post_message(DateFieldInput.CalendarRequested(attr_key, self.value))


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
    _DAYS: list[str] = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]

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
        self._attr_key: str = attr_key
        self._mode: str = "cal"         # "cal" | "month" | "year"
        self._drop_cursor: int = 0
        # ("header", col) where col: 0=<  1=month  2=year  3=>
        # ("day", row, col) where row/col index the day grid
        self._focus: tuple = ("header", 0)
        if initial and initial.year == self._year and initial.month == self._month:
            self._init_focus(initial)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _weeks(self) -> list[list[int | None]]:
        """Weeks as 7-element lists (Su=0..Sa=6). None for empty cells."""
        first_iso, num_days = _cal_mod.monthrange(self._year, self._month)
        # ISO Mon=0..Sun=6 → Sunday-first Sun=0..Sat=6
        first_col = (first_iso + 1) % 7
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
        return list(range(self._year - 10, self._year + 11))

    def _init_focus(self, d: _date) -> None:
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

    def _hl(self, text: str, active: bool) -> str:
        return f"[reverse]{text}[/reverse]" if active else text

    def _header_line(self) -> str:
        f = self._focus
        in_hdr = f[0] == "header"
        prev = self._hl("<", in_hdr and f[1] == 0)
        mname = self._MONTHS[self._month - 1]
        month = self._hl(mname, in_hdr and f[1] == 1)
        year = self._hl(str(self._year), in_hdr and f[1] == 2)
        nxt = self._hl(">", in_hdr and f[1] == 3)
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
                        cells.append(self._hl(txt, self._focus == ("day", r, c)))
                lines.append(" ".join(cells))
            return "\n".join(lines)

        elif self._mode == "month":
            lines = [self._header_line()]
            for i, m in enumerate(self._MONTHS):
                cur = i == self._drop_cursor
                label = f"> {m}" if cur else f"  {m}"
                lines.append(self._hl(label, cur))
            return "\n".join(lines)

        else:  # year
            lines = [self._header_line()]
            for i, y in enumerate(self._year_range()):
                cur = i == self._drop_cursor
                label = f"> {y}" if cur else f"  {y}"
                lines.append(self._hl(label, cur))
            return "\n".join(lines)

    # ── Key handling ───────────────────────────────────────────────────────

    def on_key(self, event: Key) -> None:
        if self._mode == "cal":
            self._cal_key(event)
        else:
            self._drop_key(event)

    def _cal_key(self, event: Key) -> None:  # noqa: C901
        key = event.key
        f = self._focus

        if key == "escape":
            event.prevent_default()
            event.stop()
            self.post_message(CalendarWidget.Dismissed())

        elif key == "left":
            event.prevent_default()
            event.stop()
            if f[0] == "header":
                if f[1] > 0:
                    self._focus = ("header", f[1] - 1)
                else:
                    self.post_message(CalendarWidget.Dismissed())
                    return
            elif f[0] == "day":
                self._step_day(-1)
            self.refresh()

        elif key == "right":
            event.prevent_default()
            event.stop()
            if f[0] == "header" and f[1] < 3:
                self._focus = ("header", f[1] + 1)
            elif f[0] == "day":
                self._step_day(+1)
            self.refresh()

        elif key == "up":
            event.prevent_default()
            event.stop()
            if f[0] == "day":
                if f[1] == 0:
                    # Top row of days → jump to header <
                    self._focus = ("header", 0)
                else:
                    self._move_row(f[1] - 1, f[2])
            self.refresh()

        elif key == "down":
            event.prevent_default()
            event.stop()
            if f[0] == "header":
                weeks = self._weeks()
                if weeks:
                    for c, d in enumerate(weeks[0]):
                        if d is not None:
                            self._focus = ("day", 0, c)
                            break
            elif f[0] == "day":
                self._move_row(f[1] + 1, f[2])
            self.refresh()

        elif key == "enter":
            event.prevent_default()
            event.stop()
            if f[0] == "header":
                self._header_action(f[1])
            elif f[0] == "day":
                weeks = self._weeks()
                day = weeks[f[1]][f[2]]
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
        f = self._focus
        weeks = self._weeks()
        r, c = f[1], f[2]
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


class SelectInput(Widget):
    """Single-line selectable field; Enter opens an inline option list."""

    can_focus = True

    class ValueSelected(Message):
        """Posted after the user confirms a selection from the dropdown."""

    def __init__(self, options: list[str] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._options: list[str] = options or []
        self._display: list[str] = list(self._options)
        self._value: str = ""
        self._open: bool = False
        self._cursor: int = 0

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, v: str) -> None:
        self._value = v
        self.refresh()

    def set_options(self, options: list[str], display: list[str] | None = None) -> None:
        self._options = options
        self._display = display if display is not None else list(options)

    def render(self) -> str:
        if not self._open:
            try:
                return self._display[self._options.index(self._value)]
            except (ValueError, IndexError):
                return self._value
        lines = []
        for i, disp in enumerate(self._display):
            prefix = "> " if i == self._cursor else "  "
            lines.append(f"{prefix}{disp}")
        return "\n".join(lines)

    def _open_dropdown(self) -> None:
        self._open = True
        try:
            self._cursor = self._options.index(self._value.strip())
        except ValueError:
            self._cursor = 0
        n = max(len(self._options), 1)
        if self.parent:
            self.parent.styles.height = n
        self.styles.height = n
        self.refresh()

    def _close_dropdown(self) -> None:
        self._open = False
        if self.parent:
            self.parent.styles.height = 1
        self.styles.height = 1
        self.refresh()

    def on_key(self, event: Key) -> None:  # noqa: C901
        if self.disabled:
            return
        if not self._open:
            if event.key == "enter":
                event.prevent_default()
                event.stop()
                if self._options:
                    self._open_dropdown()
            elif event.key == "up":
                event.prevent_default()
                event.stop()
                self.post_message(FieldInput.Navigate(-1))
            elif event.key == "down":
                event.prevent_default()
                event.stop()
                self.post_message(FieldInput.Navigate(+1))
            elif event.key == "left":
                event.prevent_default()
                event.stop()
                self.post_message(DetailTextArea.ExitRequested())
        else:
            if event.key == "up":
                event.prevent_default()
                event.stop()
                self._cursor = max(0, self._cursor - 1)
                self.refresh()
            elif event.key == "down":
                event.prevent_default()
                event.stop()
                self._cursor = min(len(self._options) - 1, self._cursor + 1)
                self.refresh()
            elif event.key == "enter":
                event.prevent_default()
                event.stop()
                if self._options:
                    self._value = self._options[self._cursor]
                self._close_dropdown()
                self.post_message(SelectInput.ValueSelected())
            elif event.key in ("escape", "left"):
                event.prevent_default()
                event.stop()
                self._close_dropdown()

    def on_blur(self) -> None:
        if self._open:
            self._close_dropdown()


class BodyTextArea(DetailTextArea):
    """Body textarea: cursor line only highlighted when focused; ↑ at row 0 moves to fields."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.highlight_cursor_line = False

    def on_focus(self) -> None:
        self.highlight_cursor_line = True

    def on_blur(self) -> None:
        self.highlight_cursor_line = False

    def on_key(self, event: Key) -> None:
        super().on_key(event)
        if event.key == "up" and self.cursor_location[0] == 0:
            event.prevent_default()
            event.stop()
            self.post_message(FieldInput.Navigate(-1))


class StructuredEditor(Widget):
    """Always-mounted structured editor for frontmatter documents.

    Renders one Input per frontmatter field (read-only for ``id``) and a
    DetailTextArea for the free-text body. Hidden by default; shown when
    ContentPanel has the ``-editing-struct`` class.
    """

    class Changed(Message):
        """Posted when focus moves between fields, so the app can save and refresh."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._kind: str = ""

    def compose(self):
        for attr_key, label, _kinds, readonly in FIELD_DEFS:
            with Horizontal(classes="se-row", id=f"se-row-{attr_key}"):
                yield Label(label, classes="se-label")
                if attr_key in SELECT_FIELDS:
                    yield SelectInput(id=f"se-inp-{attr_key}")
                else:
                    cls = DateFieldInput if attr_key in DATE_FIELDS else FieldInput
                    yield cls(id=f"se-inp-{attr_key}", disabled=readonly)
        yield Rule(classes="se-sep")
        yield BodyTextArea("", id="se-body", language="markdown", theme="vscode_dark")

    def load(self, item: Any, kind: str) -> None:  # noqa: C901
        """Populate fields from *item* and show only the fields relevant to *kind*."""
        for cal in self.query(CalendarWidget):
            cal.remove()
        self._kind = kind

        root = getattr(self.app, "root", None)
        cfg = _read_config(root) if root else AppConfig({}, {}, [])
        state: ProjectState | None = getattr(self.app, "state", None)
        milestone_ids = [m.id for m in state.milestones] if state else []

        for attr_key, _label, kinds, _readonly in FIELD_DEFS:
            row = self.query_one(f"#se-row-{attr_key}")
            visible = kind in kinds
            row.display = visible
            if visible:
                raw = getattr(item, attr_key, None)
                if isinstance(raw, list):
                    val = ", ".join(str(v) for v in raw)
                elif isinstance(raw, bool):
                    val = "true" if raw else "false"
                elif raw is None:
                    val = ""
                else:
                    val = str(raw)

                widget = self.query_one(f"#se-inp-{attr_key}")
                if attr_key in SELECT_FIELDS:
                    display: list[str] | None = None
                    if attr_key == "status":
                        icons = cfg.task_statuses if kind == "task" else cfg.milestone_statuses
                        options: list[str] = list(icons.keys())
                        display = [f"{icons[s]} {s}" for s in options]
                    elif attr_key == "label":
                        options = cfg.label
                    elif attr_key == "milestone":
                        options = [""] + milestone_ids
                    else:  # scanned
                        options = ["true", "false"]
                    widget.set_options(options, display)  # type: ignore[union-attr]
                    widget.value = val  # type: ignore[union-attr]
                else:
                    widget.value = val  # type: ignore[union-attr]

        body_attr = BODY_ATTR.get(kind, "content")
        body = getattr(item, body_attr, "") or ""
        ta = self.query_one("#se-body", BodyTextArea)
        ta.load_text(body)
        ta.move_cursor((0, 0))

    def set_editable(self, editable: bool) -> None:
        """Toggle between view (read-only) and edit mode for non-readonly fields."""
        for attr_key, _label, kinds, readonly in FIELD_DEFS:
            if self._kind not in kinds or readonly:
                continue
            widget = self.query_one(f"#se-inp-{attr_key}")
            widget.disabled = not editable
            if editable:
                widget.remove_class("se-view-disabled")
            else:
                widget.add_class("se-view-disabled")
        ta = self.query_one("#se-body", BodyTextArea)
        ta.read_only = not editable

    def focus_first(self, select_all: bool = False) -> None:
        """Focus the first editable field, falling back to the body."""
        for cal in self.query(CalendarWidget):
            cal.remove()
        for attr_key, _label, kinds, readonly in FIELD_DEFS:
            if self._kind in kinds and not readonly:
                inp = self.query_one(f"#se-inp-{attr_key}", FieldInput)
                if select_all:
                    inp._select_on_next_focus = True
                inp.focus()
                return
        self.query_one("#se-body", BodyTextArea).focus()

    def _visible_inputs(self) -> list[Widget]:
        """Non-readonly visible field widgets in display order."""
        result = []
        for attr_key, _label, kinds, readonly in FIELD_DEFS:
            if self._kind not in kinds or readonly:
                continue
            row = self.query_one(f"#se-row-{attr_key}")
            if row.display:
                result.append(self.query_one(f"#se-inp-{attr_key}"))
        return result

    @on(FieldInput.Navigate)
    def _on_navigate(self, event: FieldInput.Navigate) -> None:
        event.stop()
        for cal in self.query(CalendarWidget):
            cal.remove()
        inputs = self._visible_inputs()
        if not inputs:
            return
        focused = self.app.focused
        try:
            idx = inputs.index(focused)  # type: ignore[arg-type]
        except ValueError:
            # Came from BodyTextArea going up — focus last field
            if event.direction == -1:
                inputs[-1].focus()
            return
        new_idx = idx + event.direction
        if new_idx < 0:
            pass  # already at top field, nowhere to go
        elif new_idx >= len(inputs):
            self.query_one("#se-body", BodyTextArea).focus()
        else:
            inputs[new_idx].focus()
        self.post_message(StructuredEditor.Changed())

    @on(DateFieldInput.CalendarRequested)
    def _on_calendar_requested(self, event: DateFieldInput.CalendarRequested) -> None:
        event.stop()
        for cal in self.query(CalendarWidget):
            cal.remove()
        try:
            initial = _date.fromisoformat(event.current_value.strip())
        except (ValueError, AttributeError):
            initial = None
            if event.attr_key == "end_date":
                try:
                    start_val = self.query_one("#se-inp-start_date").value.strip()  # type: ignore[union-attr]
                    initial = _date.fromisoformat(start_val)
                except Exception:
                    pass
        row = self.query_one(f"#se-row-{event.attr_key}")
        cal = CalendarWidget(initial=initial, attr_key=event.attr_key, id="se-calendar")
        self.mount(cal, after=row)
        self.call_after_refresh(cal.focus)

    @on(CalendarWidget.DateSelected)
    def _on_cal_date_selected(self, event: CalendarWidget.DateSelected) -> None:
        event.stop()
        for cal in list(self.query(CalendarWidget)):
            attr_key = cal._attr_key
            cal.remove()
            if attr_key:
                inp = self.query_one(f"#se-inp-{attr_key}")
                inp.value = event.date.isoformat()  # type: ignore[union-attr]
                inp.focus()
        self.post_message(StructuredEditor.Changed())

    @on(CalendarWidget.Dismissed)
    def _on_cal_dismissed(self, event: CalendarWidget.Dismissed) -> None:
        event.stop()
        for cal in list(self.query(CalendarWidget)):
            attr_key = cal._attr_key
            cal.remove()
            if attr_key:
                try:
                    self.query_one(f"#se-inp-{attr_key}").focus()
                except Exception:
                    pass

    @property
    def editor_text(self) -> str:
        """Serialize current field values back to raw frontmatter format."""
        if not self._kind:
            return ""
        meta: dict[str, Any] = {}
        for attr_key, _label, kinds, _readonly in FIELD_DEFS:
            if self._kind not in kinds:
                continue
            widget = self.query_one(f"#se-inp-{attr_key}")
            val_str = widget.value.strip()  # type: ignore[union-attr]
            if attr_key == "scanned":
                meta[attr_key] = val_str.lower() in ("true", "yes", "1")
            else:
                meta[attr_key] = val_str
        body = self.query_one("#se-body", BodyTextArea).text
        post = _fm.Post(body, **meta)
        return _fm.dumps(post)


class ContentPanel(Widget):
    """Right panel: Markdown viewer, raw TextArea editor, and structured editor.

    Modes are toggled via CSS classes — no widget is ever unmounted, so layout
    is stable and there are no re-render artifacts.

    CSS classes:
      (none)             → view mode (Markdown visible)
      -editing           → raw edit mode (agent / skill files)
      -editing-struct    → structured edit mode (milestone / task / note)
    """

    def compose(self):
        with ScrollableContainer(classes="cp-viewer"):
            yield Markdown("")
        yield DetailTextArea(
            "", language="markdown", theme="vscode_dark", classes="cp-raw-editor"
        )
        yield StructuredEditor()

    # ── Public interface ───────────────────────────────────────────────────

    def show_view(self, md: str):
        """Switch to view mode and update Markdown content."""
        self.remove_class("-editing")
        self.remove_class("-editing-struct")
        self.remove_class("-view-struct")
        return self.query_one(Markdown).update(md)

    def enter_edit(self, text: str) -> None:
        """Raw edit mode for agent/skill (plain markdown files)."""
        ta = self.query_one(".cp-raw-editor", DetailTextArea)
        ta.load_text(text)
        ta.move_cursor((0, 0))
        self.remove_class("-editing-struct")
        self.add_class("-editing")
        ta.focus()

    def show_struct_view(self, item: Any, kind: str) -> None:
        """Structured view mode (read-only) for milestone / task / note."""
        se = self.query_one(StructuredEditor)
        se.load(item, kind)
        se.set_editable(False)
        self.remove_class("-editing")
        self.remove_class("-editing-struct")
        self.add_class("-view-struct")

    def enter_structured_edit(self, item: Any, kind: str, select_all: bool = False) -> None:
        """Structured edit mode for milestone / task / note."""
        se = self.query_one(StructuredEditor)
        se.load(item, kind)
        se.set_editable(True)
        self.remove_class("-editing")
        self.remove_class("-view-struct")
        self.add_class("-editing-struct")
        se.focus_first(select_all=select_all)

    def clear(self) -> None:
        """Switch to view mode and clear the Markdown content."""
        self.remove_class("-editing")
        self.remove_class("-editing-struct")
        self.remove_class("-view-struct")
        self.query_one(Markdown).update("")

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def is_editing(self) -> bool:
        return self.has_class("-editing") or self.has_class("-editing-struct")

    @property
    def editor_text(self) -> str:
        if self.has_class("-editing"):
            return self.query_one(".cp-raw-editor", DetailTextArea).text
        if self.has_class("-editing-struct"):
            return self.query_one(StructuredEditor).editor_text
        return ""


class NavTree(Tree):
    """File tree widget.  Owns navigation state; communicates via messages."""

    class EditRequested(Message):
        """User pressed → on a leaf and wants to enter edit mode."""

    def on_mount(self) -> None:
        # Inline styles have the highest priority — guaranteed to hide scrollbar.
        self.styles.scrollbar_size_vertical = 0
        self.styles.scrollbar_size_horizontal = 0

    def on_mouse_down(self, event: MouseDown) -> None:
        event.prevent_default()
        event.stop()

    def on_click(self, event: Click) -> None:
        event.prevent_default()
        event.stop()

    def on_key(self, event: Key) -> None:
        if event.key == "right":
            self._handle_right(event)
        elif event.key == "left":
            self._handle_left(event)
        elif event.key == "enter":
            self._handle_enter(event)
        # "n" and "d" are NOT consumed here — they bubble to App BINDINGS.

    # ── Key handlers ──────────────────────────────────────────────────────

    def _handle_right(self, event: Key) -> None:
        node = self.cursor_node
        if not node:
            return
        if isinstance(node.data, Nav) and node.data.kind != "section":
            self.post_message(NavTree.EditRequested())
            event.stop()
        else:
            children = list(node.children)
            if not node.is_expanded:
                node.expand()
            if children:
                target = children[0]
                self.app.call_after_refresh(lambda: self.move_cursor(target))
            event.stop()

    def _handle_left(self, event: Key) -> None:
        node = self.cursor_node
        if not node or node.parent is None:
            return
        self.move_cursor(node.parent)
        event.stop()

    def _handle_enter(self, event: Key) -> None:
        node = self.cursor_node
        if node and not (isinstance(node.data, Nav) and node.data.kind != "section"):
            node.toggle()
            event.stop()

    # ── Data methods ──────────────────────────────────────────────────────

    def populate(self, state: ProjectState, root: Path) -> None:
        """Rebuild tree from *state*, preserving section expansion."""
        expanded = {
            node.data.section
            for node in self.root.children
            if isinstance(node.data, Nav) and node.is_expanded
        }
        self.clear()

        cfg = _read_config(root)

        ms = self.root.add(
            "Milestones",
            data=Nav("section", "", "milestones"),
            expand="milestones" in expanded,
        )
        for m in state.milestones:
            ms.add_leaf(
                truncate_label(f"{cfg.milestone_statuses.get(m.status, '•')} {m.title}"),
                data=Nav("milestone", m.id, "milestones"),
            )

        tasks = self.root.add(
            "Tasks", data=Nav("section", "", "tasks"), expand="tasks" in expanded
        )
        for t in state.tasks:
            tasks.add_leaf(
                truncate_label(f"{cfg.task_statuses.get(t.status, '•')} {t.title}"),
                data=Nav("task", t.id, "tasks"),
            )

        notes = self.root.add(
            "Notes", data=Nav("section", "", "notes"), expand="notes" in expanded
        )
        for n in state.notes:
            icon = "•" if n.scanned else "·"
            notes.add_leaf(truncate_label(f"{icon} {n.title}"), data=Nav("note", n.id, "notes"))

        if state.skills:
            skills = self.root.add(
                "Skills",
                data=Nav("section", "", "skills"),
                expand="skills" in expanded,
            )
            for s in state.skills:
                skills.add_leaf(truncate_label(s.command), data=Nav("skill", s.id, "skills"))

        if (root / "content" / "AGENT.md").exists():
            self.root.add_leaf("AGENT.md", data=Nav("agent", "agent", ""))

    def focus_nav(self, nav: Nav) -> None:
        """Move the tree cursor to *nav*, expanding its section if needed."""
        if nav.kind == "section":
            for section in self.root.children:
                if isinstance(section.data, Nav) and section.data.section == nav.section:
                    self.app.call_after_refresh(lambda n=section: self.move_cursor(n))
                    return
            return
        for section in self.root.children:
            for leaf in section.children:
                if (
                    isinstance(leaf.data, Nav)
                    and leaf.data.id == nav.id
                    and leaf.data.kind == nav.kind
                ):
                    section.expand()
                    self.app.call_after_refresh(lambda n=leaf: self.move_cursor(n))
                    return
