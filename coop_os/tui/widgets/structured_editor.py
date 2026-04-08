from __future__ import annotations

from datetime import date as _date
from typing import Any, cast

import frontmatter as _fm
from textual import on
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, Rule

from coop_os.backend.models import ProjectState
from coop_os.backend.schema import BODY_ATTR, DATE_FIELDS, FIELD_DEFS, SELECT_FIELDS
from coop_os.tui.widgets.body_text_area import BodyTextArea
from coop_os.tui.widgets.calendar import CalendarWidget
from coop_os.tui.widgets.config import SCANNED_ICONS, AppConfig
from coop_os.tui.widgets.date_field_input import DateFieldInput
from coop_os.tui.widgets.field_input import FieldInput
from coop_os.tui.widgets.select_input import SelectInput


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
        yield Rule(classes="se-sep", id="se-sep")
        yield BodyTextArea("", id="se-body", language="markdown", theme="vscode_dark")

    def load(self, item: Any, kind: str, cfg: AppConfig, state: ProjectState) -> None:  # noqa: C901
        """Populate fields from *item* and show only the fields relevant to *kind*."""
        for cal in self.query(CalendarWidget):
            cal.remove()
        self._kind = kind

        role_ids = [r.id for r in state.roles]
        milestone_ids = [m.id for m in state.milestones]

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
                        if kind == "task":
                            icons = cfg.task_statuses
                        elif kind == "role":
                            icons = cfg.role_statuses
                        else:
                            icons = cfg.milestone_statuses
                        options: list[str] = list(icons.keys())
                        display = [f"{icons[s]} {s}" for s in options]
                    elif attr_key == "role":
                        options = [""] + role_ids
                    elif attr_key == "milestone":
                        options = [""] + milestone_ids
                    else:  # scanned
                        options = list(SCANNED_ICONS.keys())
                        display = [f"{SCANNED_ICONS[s]} {s}" for s in options]
                    sel = cast(SelectInput, widget)
                    sel.set_options(options, display)
                    sel.value = val
                else:
                    cast(FieldInput, widget).value = val

        has_visible_fields = any(kind in kinds for _, _, kinds, _ in FIELD_DEFS)
        self.query_one("#se-sep", Rule).display = has_visible_fields

        body_attr = BODY_ATTR.get(kind, "content")
        body = getattr(item, body_attr, "") or ""
        ta = self.query_one("#se-body", BodyTextArea)
        language = getattr(item, "language", None)
        if language is not None:
            ta.language = language or None
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
                    inp.select_on_next_focus = True
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
            idx = inputs.index(cast(Widget, focused))
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
                    start_val = cast(FieldInput, self.query_one("#se-inp-start_date")).value.strip()
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
            attr_key = cal.attr_key
            cal.remove()
            if attr_key:
                inp = self.query_one(f"#se-inp-{attr_key}")
                cast(FieldInput, inp).value = event.date.isoformat()
                inp.focus()
        self.post_message(StructuredEditor.Changed())

    @on(CalendarWidget.Dismissed)
    def _on_cal_dismissed(self, event: CalendarWidget.Dismissed) -> None:
        event.stop()
        for cal in list(self.query(CalendarWidget)):
            attr_key = cal.attr_key
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
        if self._kind == "agent":
            return self.query_one("#se-body", BodyTextArea).text
        meta: dict[str, Any] = {}
        for attr_key, _label, kinds, _readonly in FIELD_DEFS:
            if self._kind not in kinds:
                continue
            widget = self.query_one(f"#se-inp-{attr_key}")
            val_str = cast(FieldInput, widget).value.strip()
            if attr_key == "scanned":
                meta[attr_key] = val_str.lower() in ("true", "yes", "1")
            else:
                meta[attr_key] = val_str
        body = self.query_one("#se-body", BodyTextArea).text
        post = _fm.Post(body, **meta)
        return _fm.dumps(post)
