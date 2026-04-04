from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual.binding import Binding
from textual.events import Click, Key, MouseDown
from textual.widgets import TextArea, Tree

from agent_os.tui.nav import Nav

if TYPE_CHECKING:
    from agent_os.tui.app import AgentOSApp


class DetailTextArea(TextArea):
    """Jumps to tree when ← is pressed at column 0 of any line."""

    def on_key(self, event: Key) -> None:
        if event.key == "left" and self.cursor_location[1] == 0:
            event.prevent_default()
            event.stop()
            # Defer so this key event is fully done before focus moves to the tree.
            app = cast("AgentOSApp", self.app)
            self.app.call_after_refresh(app.action_leave_detail)


class NavTree(Tree):
    BINDINGS = [
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
    ]

    def on_mouse_down(self, event: MouseDown) -> None:
        event.prevent_default()
        event.stop()

    def on_click(self, event: Click) -> None:
        event.prevent_default()
        event.stop()

    def on_key(self, event: Key) -> None:
        app = cast("AgentOSApp", self.app)
        if event.key == "right":
            self._handle_right(event, app)
        elif event.key == "left":
            self._handle_left(event)
        elif event.key == "enter":
            self._handle_enter(event)
        elif not app.in_detail:
            self._handle_action_key(event, app)

    def _handle_right(self, event: Key, app: AgentOSApp) -> None:
        node = self.cursor_node
        if not node:
            pass
        elif isinstance(node.data, Nav) and node.data.kind != "section":
            # leaf: enter detail
            app.action_jump_to_detail()
            event.stop()
        else:
            # root or section: expand then move cursor after re-render
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
            pass  # root: do nothing
        elif isinstance(node.data, Nav) and node.data.kind != "section":
            # leaf: jump to parent section
            self.move_cursor(node.parent)
            event.stop()
        else:
            # section node: jump to root
            self.move_cursor(node.parent)
            event.stop()

    def _handle_enter(self, event: Key) -> None:
        node = self.cursor_node
        if node and not (isinstance(node.data, Nav) and node.data.kind != "section"):
            # root or section: toggle expand/collapse, stay on node
            node.toggle()
            event.stop()

    def _handle_action_key(self, event: Key, app: AgentOSApp) -> None:
        _action_map = {"n": "new", "d": "delete"}
        if event.key in _action_map:
            getattr(app, f"action_{_action_map[event.key]}_item")()
            event.stop()
