from __future__ import annotations

from pathlib import Path

from rich.text import Text
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
        self.show_root = False
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
        elif event.key == "down":
            self._handle_down(event)
        elif event.key == "enter":
            self._handle_enter(event)
        # "n" and "d" are NOT consumed here — they bubble to App BINDINGS.

    # ── Key handlers ──────────────────────────────────────────────────────

    def _is_interactive(self, node: TreeNode[Nav | None]) -> bool:
        return isinstance(node.data, Nav) and node.data.kind not in ("group", "separator")

    def _handle_right(self, event: Key) -> None:
        node = self.cursor_node
        if not node:
            return
        nav = node.data
        if not isinstance(nav, Nav) or nav.kind in ("group", "separator"):
            event.stop()
            return
        if nav.kind != "section":
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
            # Section node: expand and navigate to first child.
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
            event.stop()
            return
        siblings = list(node.parent.children)
        idx = siblings.index(node)
        candidate_idx = idx - 1
        while candidate_idx >= 0:
            candidate = siblings[candidate_idx]
            if self._is_interactive(candidate):
                self.move_cursor(candidate)
                event.stop()
                return
            candidate_idx -= 1
        # No interactive sibling above — move to parent (including root).
        self.move_cursor(node.parent)
        event.stop()

    def _handle_down(self, event: Key) -> None:
        node = self.cursor_node
        if not node:
            event.stop()
            return
        # When on root, scan its children for the first interactive node.
        children_to_scan: list[TreeNode[Nav | None]]
        if node.parent is None:
            children_to_scan = list(node.children)
        else:
            siblings = list(node.parent.children)
            idx = siblings.index(node)
            children_to_scan = siblings[idx + 1:]
        for candidate in children_to_scan:
            if self._is_interactive(candidate):
                self.move_cursor(candidate)
                event.stop()
                return
        event.stop()

    def _handle_enter(self, event: Key) -> None:
        node = self.cursor_node
        if not node:
            return
        nav = node.data
        if isinstance(nav, Nav) and nav.kind in ("group", "separator"):
            event.stop()
            return
        if not (isinstance(nav, Nav) and nav.kind != "section"):
            node.toggle()
            event.stop()

    # ── Data methods ──────────────────────────────────────────────────────

    def populate(self, state: ProjectState, root: Path) -> None:
        """Rebuild tree from *state*, preserving section expansion."""
        expanded = {
            node.data.section
            for node in self.iter_all_nodes(self.root)
            if isinstance(node.data, Nav) and node.data.kind == "section" and node.is_expanded
        }
        expanded_tasks = {
            node.data.id
            for node in self.iter_all_nodes(self.root)
            if isinstance(node.data, Nav) and node.data.kind == "task" and node.is_expanded
        }
        self.clear()

        cfg = read_config(root)

        def _add_group_header(label: str) -> None:
            self.root.add_leaf(Text(label, style="#7a9eb8"), data=Nav("group", "", ""))

        def _add_separator() -> None:
            line = "─" * 22
            self.root.add_leaf(Text(line, style="#30363d"), data=Nav("separator", "", ""))

        # ── User group ────────────────────────────────────────────
        _add_group_header("User")
        _add_separator()
        docs = self.root.add(
            "○  Context", data=Nav("section", "", "docs"), expand="docs" in expanded
        )
        for d in state.docs:
            docs.add_leaf(truncate_label(f"• {d.title}"), data=Nav("doc", d.id, "docs"))
        notes = self.root.add(
            "○  Notes", data=Nav("section", "", "notes"), expand="notes" in expanded
        )
        for n in state.notes:
            icon = SCANNED_ICONS["true"] if n.scanned else SCANNED_ICONS["false"]
            notes.add_leaf(truncate_label(f"{icon} {n.title}"), data=Nav("note", n.id, "notes"))
        _add_separator()

        # ── Agent group ───────────────────────────────────────────
        _add_group_header("Agent")
        _add_separator()
        if (root / "coop_os" / "context" / "AGENT.md").exists():
            self.root.add_leaf("◈  AGENT.md", data=Nav("agent", "agent", ""))
        if state.skills:
            skills = self.root.add(
                "◈  Skills",
                data=Nav("section", "", "skills"),
                expand="skills" in expanded,
            )
            for s in state.skills:
                skills.add_leaf(truncate_label(s.command), data=Nav("skill", s.id, "skills"))
        _add_separator()

        # ── To dos group ──────────────────────────────────────────
        _add_group_header("To dos")
        _add_separator()
        roles = self.root.add(
            "⌄  Roles",
            data=Nav("section", "", "roles"),
            expand="roles" in expanded,
        )
        for r in state.roles:
            roles.add_leaf(
                truncate_label(f"{cfg.role_statuses.get(r.status, '•')} {r.title}"),
                data=Nav("role", r.id, "roles"),
            )
        ms = self.root.add(
            "⌄  Milestones",
            data=Nav("section", "", "milestones"),
            expand="milestones" in expanded,
        )
        for m in state.milestones:
            ms.add_leaf(
                truncate_label(f"{cfg.milestone_statuses.get(m.status, '•')} {m.title}"),
                data=Nav("milestone", m.id, "milestones"),
            )
        tasks_node = self.root.add(
            "⌄  Tasks", data=Nav("section", "", "tasks"), expand="tasks" in expanded
        )
        self._add_task_nodes(tasks_node, state.tasks, None, cfg, expanded_tasks)
        _add_separator()

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
