from __future__ import annotations

from pathlib import Path

from textual.events import Click, Key, MouseDown
from textual.message import Message
from textual.widgets import Tree
from textual.widgets._tree import TreeNode

from coop_os.backend.models import ProjectState, Task
from coop_os.tui.nav import Nav, truncate_label
from coop_os.tui.widgets.config import SCANNED_ICONS, AppConfig, read_config


class NavTree(Tree[Nav | None]):
    """File tree widget.  Owns navigation state; communicates via messages."""

    class EditRequested(Message):
        """User pressed → on a node and wants to enter edit mode."""

        def __init__(self, nav: Nav) -> None:
            super().__init__()
            self.nav = nav

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
        elif event.key == "up":
            self._handle_up(event)
        elif event.key == "enter":
            self._handle_enter(event)
        # "n" and "d" are NOT consumed here — they bubble to App BINDINGS.

    # ── Key handlers ──────────────────────────────────────────────────────

    def _handle_right(self, event: Key) -> None:
        node = self.cursor_node
        if not node:
            return
        nav = node.data
        if isinstance(nav, Nav) and nav.kind != "section":
            # Two-step: first → expands a collapsed branch (task with subtasks),
            # moving cursor to first child. Second → opens the editor.
            # Leaf nodes and already-expanded branches go straight to the editor.
            if node.children and not node.is_expanded:
                node.expand()
                first = list(node.children)[0]
                self.app.call_after_refresh(lambda n=first: self.move_cursor(n))
            else:
                self.post_message(NavTree.EditRequested(nav))
        else:
            # Section or root node: expand and navigate to first child.
            children = list(node.children)
            if not node.is_expanded:
                node.expand()
            if children:
                target = children[0]
                self.app.call_after_refresh(lambda n=target: self.move_cursor(n))
        event.stop()

    def _handle_left(self, event: Key) -> None:
        node = self.cursor_node
        if not node or node.parent is None:
            return
        self.move_cursor(node.parent)
        event.stop()

    def _handle_up(self, event: Key) -> None:
        node = self.cursor_node
        if not node or not node.parent:
            return
        siblings = list(node.parent.children)
        idx = siblings.index(node)
        if idx > 0:
            self.move_cursor(siblings[idx - 1])
        elif node.parent.parent is not None:
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
        expanded_tasks = {
            node.data.id
            for node in self.iter_all_nodes(self.root)
            if isinstance(node.data, Nav) and node.data.kind == "task" and node.is_expanded
        }
        self.clear()

        cfg = read_config(root)

        roles = self.root.add(
            "Roles",
            data=Nav("section", "", "roles"),
            expand="roles" in expanded,
        )
        for r in state.roles:
            roles.add_leaf(
                truncate_label(f"{cfg.role_statuses.get(r.status, '•')} {r.title}"),
                data=Nav("role", r.id, "roles"),
            )

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

        tasks_node = self.root.add(
            "Tasks", data=Nav("section", "", "tasks"), expand="tasks" in expanded
        )
        self._add_task_nodes(tasks_node, state.tasks, None, cfg, expanded_tasks)

        notes = self.root.add(
            "Notes", data=Nav("section", "", "notes"), expand="notes" in expanded
        )
        for n in state.notes:
            icon = SCANNED_ICONS["true"] if n.scanned else SCANNED_ICONS["false"]
            notes.add_leaf(truncate_label(f"{icon} {n.title}"), data=Nav("note", n.id, "notes"))

        docs = self.root.add(
            "Context", data=Nav("section", "", "docs"), expand="docs" in expanded
        )
        for d in state.docs:
            docs.add_leaf(truncate_label(f"• {d.title}"), data=Nav("doc", d.id, "docs"))

        if state.skills:
            skills = self.root.add(
                "Skills",
                data=Nav("section", "", "skills"),
                expand="skills" in expanded,
            )
            for s in state.skills:
                skills.add_leaf(truncate_label(s.command), data=Nav("skill", s.id, "skills"))

        if (root / "coop_os" / "context" / "AGENT.md").exists():
            self.root.add_leaf("AGENT.md", data=Nav("agent", "agent", ""))

    def focus_nav(self, nav: Nav) -> None:
        """Move the tree cursor to *nav*, expanding its section if needed."""
        if nav.kind == "section":
            for section in self.root.children:
                if isinstance(section.data, Nav) and section.data.section == nav.section:
                    self.app.call_after_refresh(lambda n=section: self.move_cursor(n))
                    return
            return
        for node in self.iter_all_nodes(self.root):
            if (
                isinstance(node.data, Nav)
                and node.data.id == nav.id
                and node.data.kind == nav.kind
            ):
                # Expand all ancestors up to root
                ancestor = node.parent
                while ancestor and ancestor is not self.root:
                    ancestor.expand()
                    ancestor = ancestor.parent
                self.app.call_after_refresh(lambda n=node: self.move_cursor(n))
                return

    def iter_all_nodes(self, node: TreeNode[Nav | None]) -> list[TreeNode[Nav | None]]:
        """Recursively collect all descendant nodes."""
        result: list[TreeNode[Nav | None]] = []
        for child in node.children:
            result.append(child)
            result.extend(self.iter_all_nodes(child))
        return result

    def _add_task_nodes(
        self,
        parent_node: TreeNode[Nav | None],
        all_tasks: list[Task],
        parent_id: str | None,
        cfg: AppConfig,
        expanded_tasks: set[str],
    ) -> None:
        children = [t for t in all_tasks if t.parent == parent_id]
        for t in children:
            label = truncate_label(f"{cfg.task_statuses.get(t.status, '•')} {t.title}")
            has_subtasks = any(c.parent == t.id for c in all_tasks)
            nav = Nav("task", t.id, "tasks")
            if has_subtasks:
                branch = parent_node.add(label, data=nav, expand=t.id in expanded_tasks)
                self._add_task_nodes(branch, all_tasks, t.id, cfg, expanded_tasks)
            else:
                parent_node.add_leaf(label, data=nav)
