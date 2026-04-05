from __future__ import annotations

from pathlib import Path

from textual.containers import ScrollableContainer
from textual.events import Click, Key, MouseDown
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Header, Markdown, TextArea, Tree

from agent_os.models import ProjectState
from agent_os.tui.nav import Nav, truncate_label


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


class ContentPanel(Widget):
    """Right panel: Markdown viewer and TextArea editor are always mounted.

    Mode is toggled via the CSS class ``-editing`` — no widget is ever
    unmounted, so layout is stable and there are no re-render artifacts.
    """

    def compose(self):
        with ScrollableContainer(classes="cp-viewer"):
            yield Markdown("")
        yield DetailTextArea("", language="markdown", theme="vscode_dark")

    # ── Public interface ───────────────────────────────────────────────────

    def show_view(self, md: str):
        """Switch to view mode and update Markdown content.

        Returns an ``AwaitComplete`` that can be awaited by the caller.
        """
        self.remove_class("-editing")
        return self.query_one(Markdown).update(md)

    def enter_edit(self, text: str) -> None:
        """Switch to edit mode, load *text* into the editor, and focus it."""
        ta = self.query_one(DetailTextArea)
        ta.load_text(text)
        ta.move_cursor((0, 0))
        self.add_class("-editing")
        ta.focus()

    def clear(self) -> None:
        """Switch to view mode and clear the Markdown content."""
        self.remove_class("-editing")
        self.query_one(Markdown).update("")  # fire-and-forget

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def is_editing(self) -> bool:
        return self.has_class("-editing")

    @property
    def editor_text(self) -> str:
        return self.query_one(DetailTextArea).text


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
