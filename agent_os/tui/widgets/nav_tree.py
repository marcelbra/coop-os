from __future__ import annotations

from pathlib import Path

from textual.events import Click, Key, MouseDown
from textual.message import Message
from textual.widgets import Tree

from agent_os.models import ProjectState
from agent_os.tui.nav import Nav, truncate_label
from agent_os.tui.widgets.config import SCANNED_ICONS, read_config


class NavTree(Tree[Nav | None]):
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

        cfg = read_config(root)

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
            icon = SCANNED_ICONS["true"] if n.scanned else SCANNED_ICONS["false"]
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
