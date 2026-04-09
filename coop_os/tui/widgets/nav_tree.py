from __future__ import annotations

import re
from pathlib import Path

from rich.text import Text
from textual.events import Click, Key, MouseDown
from textual.message import Message
from textual.widgets import Tree
from textual.widgets._tree import TreeNode

from coop_os.backend.models import ProjectState, Task
from coop_os.tui.nav import Nav, truncate_label
from coop_os.tui.widgets.config import DIR_ICON, FILE_ICON_DEFAULT, FILE_ICONS, SCANNED_ICONS, AppConfig, read_config

_TASK_DIR_PREFIX = re.compile(r"^task-\d+-")


def _file_icon(path: Path) -> str:
    return FILE_ICONS.get(path.suffix.lower(), FILE_ICON_DEFAULT)


def _list_task_extras(task_dir: Path) -> list[Path]:
    """Return items in task_dir that are not description.md or child task dirs."""
    return sorted(
        p for p in task_dir.iterdir()
        if p.name != "description.md" and not _TASK_DIR_PREFIX.match(p.name)
    )


class NavTree(Tree[Nav | None]):
    """File tree widget.  Owns navigation state; communicates via messages."""

    ICON_NODE = ""
    ICON_NODE_EXPANDED = ""

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

    # ── Expand/collapse icon updates ──────────────────────────────────────

    _WORKSPACE_SECTIONS = ("roles", "milestones", "tasks")

    def on_tree_node_expanded(self, event: Tree.NodeExpanded[Nav | None]) -> None:
        node = event.node
        nav = node.data
        if isinstance(nav, Nav) and nav.kind == "section" and nav.section in self._WORKSPACE_SECTIONS:
            node.set_label(str(node.label).replace("▶", "▼", 1))

    def on_tree_node_collapsed(self, event: Tree.NodeCollapsed[Nav | None]) -> None:
        node = event.node
        nav = node.data
        if isinstance(nav, Nav) and nav.kind == "section" and nav.section in self._WORKSPACE_SECTIONS:
            node.set_label(str(node.label).replace("▼", "▶", 1))

    # ── Key handlers ──────────────────────────────────────────────────────

    def _is_interactive(self, node: TreeNode[Nav | None]) -> bool:
        return isinstance(node.data, Nav)

    def _handle_right(self, event: Key) -> None:
        node = self.cursor_node
        if not node:
            return
        nav = node.data
        if not isinstance(nav, Nav):
            event.stop()
            return
        _EDITABLE_KINDS = {"role", "milestone", "task", "note", "context", "skill", "agent", "task_file"}
        if nav.kind != "section":
            # Two-step: first → expands a collapsed branch (task with subtasks),
            # moving cursor to first child. Second → opens the editor.
            # Leaf nodes and already-expanded branches go straight to the editor.
            if node.children and not node.is_expanded:
                node.expand()
                first = list(node.children)[0]
                self.app.call_after_refresh(lambda n=first: self.move_cursor(n))
            elif nav.kind in _EDITABLE_KINDS:
                self.post_message(NavTree.EditRequested(nav))
        else:
            # Section node: expand and navigate to first child.
            # Do nothing if the section is empty — don't rotate the triangle.
            children = list(node.children)
            if not children:
                event.stop()
                return
            if not node.is_expanded:
                node.expand()
            target = children[0]
            self.app.call_after_refresh(lambda n=target: self.move_cursor(n))
        event.stop()

    def _handle_left(self, event: Key) -> None:
        node = self.cursor_node
        if not node or node.parent is None:
            return
        self.move_cursor(node.parent)
        event.stop()

    # ── Navigation contract ───────────────────────────────────────────────
    # Up   : move to the previous *sibling* (skip non-interactive ones), then
    #        to parent if there is no sibling above.  Never dives into the
    #        children of a previous sibling — always lands on section headers.
    # Down : if the current node is expanded and has children, descend into
    #        the first child.  Otherwise find the next interactive sibling.
    #        If no sibling follows, climb to the parent and repeat (so the
    #        last child of a section falls through to the next section).
    # ─────────────────────────────────────────────────────────────────────

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
        # No interactive sibling above — go to parent (unless already at root level).
        if node.parent is not self.root:
            self.move_cursor(node.parent)
        event.stop()

    def _handle_down(self, event: Key) -> None:
        node = self.cursor_node
        if not node:
            event.stop()
            return
        # Descend into children when the node is expanded.
        if node.is_expanded and node.children:
            self.move_cursor(list(node.children)[0])
            event.stop()
            return
        # No children to enter — find next interactive sibling, climbing when needed.
        current = node
        while current is not self.root:
            parent = current.parent
            if parent is None:
                break
            siblings = list(parent.children)
            idx = siblings.index(current)
            for candidate in siblings[idx + 1:]:
                if self._is_interactive(candidate):
                    self.move_cursor(candidate)
                    event.stop()
                    return
            # Exhausted siblings at this level; climb and try the parent's siblings.
            current = parent
        event.stop()

    def _handle_enter(self, event: Key) -> None:
        node = self.cursor_node
        if not node:
            return
        nav = node.data
        if not isinstance(nav, Nav):
            event.stop()
            return
        if node.children:
            if node.is_expanded:
                node.collapse()
            else:
                node.expand()
                first = list(node.children)[0]
                self.app.call_after_refresh(lambda n=first: self.move_cursor(n))
        event.stop()

    # ── Data methods ──────────────────────────────────────────────────────

    def _expanded_state(self) -> tuple[set[str], set[str], set[str]]:
        all_nodes = self.iter_all_nodes(self.root)
        expanded = {
            n.data.section
            for n in all_nodes
            if isinstance(n.data, Nav) and n.data.kind == "section" and n.is_expanded
        }
        expanded_tasks = {
            n.data.id
            for n in all_nodes
            if isinstance(n.data, Nav) and n.data.kind == "task" and n.is_expanded
        }
        expanded_dirs = {
            n.data.id
            for n in all_nodes
            if isinstance(n.data, Nav) and n.data.kind == "task_dir" and n.is_expanded
        }
        return expanded, expanded_tasks, expanded_dirs

    @staticmethod
    def _section_label(arrow: str, name: str, filtered: bool) -> Text:
        t = Text()
        t.append(f"{arrow}  {name}")
        if filtered:
            t.append(" ·", style="#58a6ff")
        return t

    def _build_workspaces(
        self,
        state: ProjectState,
        expanded: set[str],
        expanded_tasks: set[str],
        expanded_dirs: set[str],
        cfg: AppConfig,
        role_filters: set[str],
        milestone_filters: set[str],
        task_filters: set[str],
        task_dirs: dict[str, Path],
        visible_role_ids: set[str],
        visible_milestone_ids: set[str],
    ) -> None:
        visible_roles = [r for r in state.roles if not role_filters or r.id in visible_role_ids]
        roles_expand = "roles" in expanded and bool(visible_roles)
        roles_node = self.root.add(
            self._section_label("▼" if roles_expand else "▶", "Roles", bool(role_filters)),
            data=Nav("section", "", "roles"),
            expand=roles_expand,
        )
        for r in visible_roles:
            roles_node.add_leaf(
                truncate_label(f"{cfg.role_statuses.get(r.status, '•')} {r.title}"),
                data=Nav("role", r.id, "roles"),
            )

        ms_filter_active = bool(role_filters or milestone_filters)
        visible_milestones = [
            m for m in state.milestones
            if not ms_filter_active or m.id in visible_milestone_ids
        ]
        ms_expand = "milestones" in expanded and bool(visible_milestones)
        ms_node = self.root.add(
            self._section_label("▼" if ms_expand else "▶", "Milestones", bool(milestone_filters)),
            data=Nav("section", "", "milestones"),
            expand=ms_expand,
        )
        for m in visible_milestones:
            ms_node.add_leaf(
                truncate_label(f"{cfg.milestone_statuses.get(m.status, '•')} {m.title}"),
                data=Nav("milestone", m.id, "milestones"),
            )

        ms_ids_for_tasks = visible_milestone_ids if ms_filter_active else None
        has_visible_tasks = any(
            t for t in state.tasks
            if t.parent is None
            and (not task_filters or t.status in task_filters)
            and (ms_ids_for_tasks is None or t.milestone is None or t.milestone in ms_ids_for_tasks)
        )
        tasks_expand = "tasks" in expanded and has_visible_tasks
        tasks_node = self.root.add(
            self._section_label("▼" if tasks_expand else "▶", "Tasks", bool(task_filters)),
            data=Nav("section", "", "tasks"),
            expand=tasks_expand,
        )
        self._add_task_nodes(
            tasks_node, state.tasks, None, cfg, expanded_tasks, task_filters, task_dirs, expanded_dirs,
            ms_ids_for_tasks,
        )

    def populate(
        self,
        state: ProjectState,
        root: Path,
        role_filters: set[str] | None = None,
        milestone_filters: set[str] | None = None,
        task_filters: set[str] | None = None,
        task_dirs: dict[str, Path] | None = None,
        visible_role_ids: set[str] | None = None,
        visible_milestone_ids: set[str] | None = None,
    ) -> None:
        """Rebuild tree from *state*, preserving section expansion.

        Pass pre-computed *visible_role_ids* and *visible_milestone_ids* from
        StateManager so filtering logic lives in one place.
        """
        role_filters = role_filters or set()
        milestone_filters = milestone_filters or set()
        task_filters = task_filters or set()
        task_dirs = task_dirs or {}
        visible_role_ids = visible_role_ids or set()
        visible_milestone_ids = visible_milestone_ids or set()

        expanded, expanded_tasks, expanded_dirs = self._expanded_state()
        self.clear()

        cfg = read_config(root)

        def _header(label: str) -> None:
            self.root.add_leaf(Text(label, style="#7a9eb8"), data=None)

        def _sep() -> None:
            self.root.add_leaf(Text("─" * 22, style="#30363d"), data=None)

        # ── Workspaces group ──────────────────────────────────────
        _header("Workspaces")
        _sep()
        self._build_workspaces(
            state, expanded, expanded_tasks, expanded_dirs,
            cfg, role_filters, milestone_filters, task_filters, task_dirs,
            visible_role_ids, visible_milestone_ids,
        )
        _sep()

        # ── User group ────────────────────────────────────────────
        _header("User")
        _sep()
        docs = self.root.add(
            "○  Context", data=Nav("section", "", "contexts"), expand="contexts" in expanded
        )
        for d in state.contexts:
            docs.add_leaf(truncate_label(f"• {d.title}"), data=Nav("context", d.id, "contexts"))
        notes = self.root.add(
            "○  Notes", data=Nav("section", "", "notes"), expand="notes" in expanded
        )
        for n in state.notes:
            icon = SCANNED_ICONS["true"] if n.scanned else SCANNED_ICONS["false"]
            notes.add_leaf(truncate_label(f"{icon} {n.title}"), data=Nav("note", n.id, "notes"))
        _sep()

        # ── Agent group ───────────────────────────────────────────
        _header("Agent")
        _sep()
        if (root / "coop_os" / "agent" / "AGENT.md").exists():
            self.root.add_leaf("◈  AGENT.md", data=Nav("agent", "agent", ""))
        if state.skills:
            skills = self.root.add(
                "◈  Skills",
                data=Nav("section", "", "skills"),
                expand="skills" in expanded,
            )
            for s in state.skills:
                skills.add_leaf(truncate_label(s.name), data=Nav("skill", s.id, "skills"))
        _sep()

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

    def _add_path_node(self, parent_node: TreeNode[Nav | None], path: Path, expanded_dirs: set[str]) -> None:
        """Recursively add a filesystem file or directory node under *parent_node*."""
        icon = _file_icon(path) if path.is_file() else DIR_ICON
        label = truncate_label(f"{icon}  {path.name}")
        if path.is_dir():
            children = sorted(path.iterdir())
            if children:
                expanded = str(path) in expanded_dirs
                node = parent_node.add(label, data=Nav("task_dir", str(path), "tasks"), expand=expanded)
                for child in children:
                    self._add_path_node(node, child, expanded_dirs)
            else:
                parent_node.add_leaf(label, data=Nav("task_dir", str(path), "tasks"))
        else:
            parent_node.add_leaf(label, data=Nav("task_file", str(path), "tasks"))

    def _add_task_nodes(
        self,
        parent_node: TreeNode[Nav | None],
        all_tasks: list[Task],
        parent_id: str | None,
        cfg: AppConfig,
        expanded_tasks: set[str],
        task_filters: set[str],
        task_dirs: dict[str, Path],
        expanded_dirs: set[str],
        visible_milestone_ids: set[str] | None = None,
    ) -> None:
        children = [t for t in all_tasks if t.parent == parent_id]
        for t in children:
            if task_filters and t.status not in task_filters:
                continue
            if (
                parent_id is None
                and visible_milestone_ids is not None
                and t.milestone is not None
                and t.milestone not in visible_milestone_ids
            ):
                continue
            label = truncate_label(f"{cfg.task_statuses.get(t.status, '•')} {t.title}")
            has_subtasks = any(c.parent == t.id for c in all_tasks)
            task_dir = task_dirs.get(t.id)
            extra = _list_task_extras(task_dir) if task_dir else []
            nav = Nav("task", t.id, "tasks")
            if has_subtasks or extra:
                branch = parent_node.add(label, data=nav, expand=t.id in expanded_tasks)
                self._add_task_nodes(
                    branch, all_tasks, t.id, cfg, expanded_tasks, task_filters, task_dirs, expanded_dirs
                )
                for p in extra:
                    self._add_path_node(branch, p, expanded_dirs)
            else:
                parent_node.add_leaf(label, data=nav)
