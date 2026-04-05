from __future__ import annotations

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
    ("name",         "name",       frozenset({"role"}),                                     False),
    ("emoji",        "emoji",      frozenset({"role"}),                                     False),
    ("title",        "title",      frozenset({"pms", "role", "milestone", "task", "note"}), False),
    ("date",         "date",       frozenset({"note"}),                                     False),
    ("scanned",      "scanned",    frozenset({"note"}),                                     False),
    ("role",         "role",       frozenset({"milestone"}),                                False),
    ("start_date",   "start date", frozenset({"milestone"}),                                False),
    ("end_date",     "end date",   frozenset({"milestone"}),                                False),
    ("status",       "status",     frozenset({"milestone", "task"}),                        False),
    ("milestone",    "milestone",  frozenset({"task"}),                                     False),
    ("labels",       "labels",     frozenset({"task"}),                                     False),
    ("dependencies", "depends on", frozenset({"task"}),                                     False),
    ("created_date", "created",    frozenset({"task"}),                                     False),
    ("id",           "id",         frozenset({"pms", "role", "milestone", "task", "note"}), True),
]

BODY_ATTR: dict[str, str] = {
    "pms": "content",
    "role": "content",
    "milestone": "description",
    "task": "description",
    "note": "content",
}


class FixedHeader(Header):
    """Header that does not grow when clicked."""

    def _on_click(self) -> None:
        pass


class DetailTextArea(TextArea):
    """TextArea that posts ExitRequested when ← is pressed at column 0."""

    class ExitRequested(Message):
        """User wants to leave edit mode."""

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

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._kind: str = ""

    def compose(self):
        for attr_key, label, _kinds, readonly in FIELD_DEFS:
            with Horizontal(classes="se-row", id=f"se-row-{attr_key}"):
                yield Label(label, classes="se-label")
                yield FieldInput(id=f"se-inp-{attr_key}", disabled=readonly)
        yield Rule(classes="se-sep")
        yield BodyTextArea("", id="se-body", language="markdown", theme="vscode_dark")

    def load(self, item: Any, kind: str) -> None:
        """Populate fields from *item* and show only the fields relevant to *kind*."""
        self._kind = kind
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
                self.query_one(f"#se-inp-{attr_key}", Input).value = val

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
            inp = self.query_one(f"#se-inp-{attr_key}", Input)
            inp.disabled = not editable
            if editable:
                inp.remove_class("se-view-disabled")
            else:
                inp.add_class("se-view-disabled")
        ta = self.query_one("#se-body", BodyTextArea)
        ta.read_only = not editable

    def focus_first(self) -> None:
        """Focus the first editable field, falling back to the body."""
        for attr_key, _label, kinds, readonly in FIELD_DEFS:
            if self._kind in kinds and not readonly:
                self.query_one(f"#se-inp-{attr_key}", FieldInput).focus()
                return
        self.query_one("#se-body", BodyTextArea).focus()

    def _visible_inputs(self) -> list[FieldInput]:
        """Non-readonly visible FieldInputs in display order."""
        result = []
        for attr_key, _label, kinds, readonly in FIELD_DEFS:
            if self._kind not in kinds or readonly:
                continue
            row = self.query_one(f"#se-row-{attr_key}")
            if row.display:
                result.append(self.query_one(f"#se-inp-{attr_key}", FieldInput))
        return result

    @on(FieldInput.Navigate)
    def _on_navigate(self, event: FieldInput.Navigate) -> None:
        event.stop()
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

    @property
    def editor_text(self) -> str:
        """Serialize current field values back to raw frontmatter format."""
        if not self._kind:
            return ""
        meta: dict[str, Any] = {}
        for attr_key, _label, kinds, _readonly in FIELD_DEFS:
            if self._kind not in kinds:
                continue
            val_str = self.query_one(f"#se-inp-{attr_key}", Input).value.strip()
            if attr_key == "scanned":
                meta[attr_key] = val_str.lower() in ("true", "yes", "1")
            elif attr_key in ("labels", "dependencies"):
                meta[attr_key] = [v.strip() for v in val_str.split(",") if v.strip()]
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
      -editing-struct    → structured edit mode (pms / role / milestone / task / note)
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
        """Structured view mode (read-only) for pms / role / milestone / task / note."""
        se = self.query_one(StructuredEditor)
        se.load(item, kind)
        se.set_editable(False)
        self.remove_class("-editing")
        self.remove_class("-editing-struct")
        self.add_class("-view-struct")

    def enter_structured_edit(self, item: Any, kind: str) -> None:
        """Structured edit mode for pms / role / milestone / task / note."""
        se = self.query_one(StructuredEditor)
        se.load(item, kind)
        se.set_editable(True)
        self.remove_class("-editing")
        self.remove_class("-view-struct")
        self.add_class("-editing-struct")
        se.focus_first()

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

        ctx = self.root.add(
            "Context", data=Nav("section", "", "context"), expand="context" in expanded
        )
        if state.pms:
            ctx.add_leaf(
                truncate_label("Personal Mission Statement"), data=Nav("pms", "pms", "context")
            )
        for r in state.roles:
            ctx.add_leaf(truncate_label(f"{r.emoji} {r.name}"), data=Nav("role", r.id, "context"))

        ms_icons = {"active": "•", "completed": "✓", "cancelled": "✗"}
        ms = self.root.add(
            "Milestones",
            data=Nav("section", "", "milestones"),
            expand="milestones" in expanded,
        )
        for m in state.milestones:
            ms.add_leaf(
                truncate_label(f"{ms_icons.get(m.status, '•')} {m.title}"),
                data=Nav("milestone", m.id, "milestones"),
            )

        task_icons = {
            "todo": "•", "in_progress": "▶", "waiting": "…",
            "done": "✓", "cancelled": "✗",
        }
        tasks = self.root.add(
            "Tasks", data=Nav("section", "", "tasks"), expand="tasks" in expanded
        )
        for t in state.tasks:
            tasks.add_leaf(
                truncate_label(f"{task_icons.get(t.status, '•')} {t.title}"),
                data=Nav("task", t.id, "tasks"),
            )

        notes = self.root.add(
            "Notes", data=Nav("section", "", "notes"), expand="notes" in expanded
        )
        for n in state.notes:
            icon = "•" if not n.scanned else "·"
            notes.add_leaf(truncate_label(f"{icon} {n.title}"), data=Nav("note", n.id, "notes"))

        skills_dir = root / "skills"
        if skills_dir.exists():
            skills = self.root.add(
                "Skills",
                data=Nav("section", "", "skills"),
                expand="skills" in expanded,
            )
            for p in sorted(skills_dir.glob("*.md")):
                skills.add_leaf(truncate_label(p.stem), data=Nav("skill", p.stem, "skills"))

        if (root / "AGENT.md").exists():
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
