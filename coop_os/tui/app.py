from __future__ import annotations

import os
import re
import shutil
import signal
import time
import types
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import frontmatter as _fm
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.events import Paste
from textual.timer import Timer
from textual.widgets import Tree

from coop_os.backend.models import (
    Attachment,
    Context,
    Milestone,
    Note,
    Role,
    Skill,
    Task,
)
from coop_os.backend.store import ProjectStore, sanitize_filename
from coop_os.tui.actions import ActionsMixin
from coop_os.tui.keybindings_screen import KeybindingsScreen
from coop_os.tui.nav import ContentNav, FileNav, Nav, StructuralNav, nav_from_parts, nav_to_parts
from coop_os.tui.session import SessionState, load_session, save_session
from coop_os.tui.state import StateManager
from coop_os.tui.styles import CSS as APP_CSS
from coop_os.tui.watcher import FileSnapshot
from coop_os.tui.widgets import (
    ContentPanel,
    DetailTextArea,
    ExpansionState,
    FixedHeader,
    NavTree,
    SelectInput,
    SplitFooter,
    StructuredEditor,
)
from coop_os.tui.widgets.config import FILE_LANGUAGES

_SECTION_TO_KIND: dict[str, str] = {
    "roles": "role",
    "milestones": "milestone",
    "tasks": "task",
    "notes": "note",
    "contexts": "context",
    "skills": "skill",
}

# Match flat .md files: role-1-My Title.md  →  group 1="role-1", group 2="My Title"
_FLAT_FILE_RENAME_RE = re.compile(r"^([a-z]+-\d+)-(.+)\.md$")
# Match task directory names: task-1-My Task  →  group 1="task-1", group 2="My Task"
_TASK_DIR_RENAME_RE = re.compile(r"^(task-\d+)-(.+)$")


class CoopOSApp(ActionsMixin, App[None]):
    TITLE = "coop-os"
    CSS = APP_CSS
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("r", "filter_roles", "role", show=False),
        Binding("m", "filter_milestones", "milestone", show=False),
        Binding("t", "filter_tasks", "task", show=False),
        Binding("n", "new_item", "new", show=False),
        Binding("ctrl+n", "new_subtask", "new subtask", show=False),
        Binding("d", "delete_item", "delete", show=False),
        Binding("ctrl+r", "refresh_state", "Refresh", show=False),
        Binding("k", "show_keybindings", "keys", show=False),
    ]

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        store = ProjectStore(root)
        self.sm = StateManager(store, root)
        self.selected: Nav | None = StructuralNav("section", "roles")
        self._file_snapshot: FileSnapshot = FileSnapshot(root)
        self._pending_reload: bool = False
        self._last_change_at: float = 0.0
        self._pending_changes: set[str] = set()
        self._watcher_timer: Timer | None = None

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield FixedHeader()
        with Horizontal():
            yield NavTree("coop-os", id="nav")
            yield ContentPanel(id="content")
        yield SplitFooter()

    def on_mount(self) -> None:
        session = load_session(self.root)
        self.sm.role_filters = session.role_filters
        self.sm.milestone_filters = session.milestone_filters
        self.sm.task_filters = session.task_filters
        if session.selected_kind:
            self.selected = nav_from_parts(session.selected_kind, session.selected_id, session.selected_section)
        self._reload(initial_expansion=ExpansionState(
            session.expanded_sections, session.expanded_tasks, session.expanded_dirs
        ))
        self._update_right_hints()
        for sig in (signal.SIGHUP, signal.SIGTERM):
            signal.signal(sig, self._on_termination_signal)
        self._file_snapshot.build()
        self._watcher_timer = self.set_interval(0.15, self._on_watch_tick, name="file-watcher")

    def _on_termination_signal(self, signum: int, frame: types.FrameType | None) -> None:
        self._save_session()
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    def _save_session(self) -> None:
        try:
            tree = self.query_one(NavTree)
            expansion = tree.expanded_state()
            cursor_nav = self.selected
            if cursor_nav is None:
                cursor_node = tree.cursor_node
                if cursor_node is not None:
                    cursor_nav = cursor_node.data
            if cursor_nav is not None:
                sel_kind, sel_id, sel_section = nav_to_parts(cursor_nav)
            else:
                sel_kind, sel_id, sel_section = "section", "", "roles"
            save_session(self.root, SessionState(
                role_filters=self.sm.role_filters,
                milestone_filters=self.sm.milestone_filters,
                task_filters=self.sm.task_filters,
                expanded_sections=expansion.sections,
                expanded_tasks=expansion.tasks,
                expanded_dirs=expansion.dirs,
                selected_kind=sel_kind,
                selected_id=sel_id,
                selected_section=sel_section,
            ))
        except NoMatches:
            pass

    async def action_quit(self) -> None:
        self._save_session()
        await super().action_quit()

    # ── State ─────────────────────────────────────────────────────────────────

    def _sync_state(self, initial_expansion: ExpansionState | None = None) -> None:
        """Load state from disk and repopulate the tree.

        This is the single authoritative sync point between disk and UI. Call it
        any time the on-disk files change (after a save, create, or delete) to
        ensure self.state and the NavTree are consistent. It deliberately does
        not touch focus, view mode, or selection — callers own those concerns.
        """
        state = self.sm.load()
        visible_role_ids = self.sm.visible_role_ids()
        visible_milestone_ids = self.sm.visible_milestone_ids(visible_role_ids)
        self.query_one(NavTree).populate(
            state, self.root, self.sm.role_filters, self.sm.milestone_filters, self.sm.task_filters,
            task_dirs=self.sm.task_dirs(),
            visible_role_ids=visible_role_ids,
            visible_milestone_ids=visible_milestone_ids,
            initial_expansion=initial_expansion,
        )

    def _reload(self, initial_expansion: ExpansionState | None = None) -> None:
        """Reload state from disk while preserving the cursor position.

        Cursor-preservation contract: captures `selected` and `cursor_nav` before
        sync (section headers set selected=None, so the old guard missed cursor
        restoration on header nodes). After _sync_state completes, restores cursor
        via focus_nav. Also triggers _show_view only when an item is selected, and
        emits a parse-error notification if errors are present.
        """
        # Capture both the selected item nav AND the cursor nav (which may be a
        # section header when no item is selected) before sync, so focus_nav can
        # restore the cursor even when cursor is on a section node (self.selected
        # is None for sections, so the old `if selected:` guard skipped focus_nav,
        # leaving cursor_line stale after rebuild — pointing to a divider).
        selected = self.selected
        tree = self.query_one(NavTree)
        cursor_nav: Nav | None = selected
        if cursor_nav is None:
            cursor_node = tree.cursor_node
            if cursor_node is not None:
                cursor_nav = cursor_node.data
        self._sync_state(initial_expansion)
        assert self.sm.state is not None
        content = self.query_one(ContentPanel)
        if cursor_nav is not None and not content.is_editing:
            tree.focus_nav(cursor_nav, top_aligned=initial_expansion is not None)
        if selected is not None:
            self._show_view()
        if self.sm.state.errors:
            self.notify(
                f"{len(self.sm.state.errors)} parse error(s) — check files",
                severity="warning",
                timeout=4,
            )

    def reload_state(self) -> None:
        """Public reload entry point that preserves cursor and selection."""
        self._reload()

    def _item(self) -> Role | Milestone | Task | Note | Context | Skill | None:
        return self.sm.item(self.selected)

    def _item_path(self) -> Path | None:
        return self.sm.item_path(self.selected)

    def _update_footer_hints(self, nav: Nav | None) -> None:
        content = self.query_one(ContentPanel)
        editing = content.is_editing

        pairs: list[tuple[str, str]] = []
        if not editing and nav is not None:
            new_kind: str | None = None
            if isinstance(nav, StructuralNav) and nav.section in _SECTION_TO_KIND:
                new_kind = _SECTION_TO_KIND[nav.section]
            elif isinstance(nav, ContentNav) and nav.kind != "context":
                new_kind = nav.kind
            if new_kind:
                pairs.append(("n", f"new {new_kind}"))
            if isinstance(nav, ContentNav) and nav.kind == "task":
                pairs.append(("^n", "new subtask"))
                pairs.append(("drop", "attach file"))
            if isinstance(nav, ContentNav):
                pairs.append(("d", "delete"))

        self.query_one(SplitFooter).update_left(pairs)

    def _update_right_hints(self) -> None:
        active = {
            k for k, f in [
                ("r", self.sm.role_filters),
                ("m", self.sm.milestone_filters),
                ("t", self.sm.task_filters),
            ]
            if f
        }
        self.query_one(SplitFooter).update_right(
            "Filters",
            [("r", "role"), ("m", "milestone"), ("t", "task")],
            active,
        )

    # ── Tree navigation ───────────────────────────────────────────────────────

    @on(Tree.NodeHighlighted, "#nav")
    def on_node_highlighted(self, event: Tree.NodeHighlighted[Nav | None]) -> None:
        nav = event.node.data
        self._update_footer_hints(nav)
        content = self.query_one(ContentPanel)
        if content.is_editing:
            return
        if nav is None or isinstance(nav, StructuralNav):
            self.selected = None
            content.clear()
            return
        self.selected = nav
        self._show_view()

    @on(Tree.NodeSelected, "#nav")
    def on_node_selected(self, event: Tree.NodeSelected[Nav | None]) -> None:
        nav = event.node.data
        self._update_footer_hints(nav)
        content = self.query_one(ContentPanel)
        if nav is None or isinstance(nav, StructuralNav):
            self.selected = None
            content.clear()
            return
        if content.is_editing:
            self._save_current()
        self.selected = nav
        self._show_view()

    # ── Edit mode ─────────────────────────────────────────────────────────────

    @on(NavTree.EditRequested)
    def on_edit_requested(self, event: NavTree.EditRequested) -> None:
        self.selected = event.nav
        self._show_edit()

    @on(DetailTextArea.ExitRequested)
    def on_exit_requested(self) -> None:
        self._exit_edit_mode()

    @on(StructuredEditor.Changed)
    def on_structured_editor_changed(self) -> None:
        self._save_current()

    @on(SelectInput.ValueSelected)
    def on_select_value_selected(self) -> None:
        self._save_current()

    def _clear_edit_classes(self) -> None:
        content = self.query_one(ContentPanel)
        content.remove_class("-editing")
        content.remove_class("-editing-struct")
        content.remove_class("-view-struct")

    def _exit_edit_mode(self) -> None:
        self._save_current()
        self._clear_edit_classes()
        self._show_view()
        self._update_footer_hints(self.selected)
        tree = self.query_one(NavTree)
        tree.focus()
        if self.selected:
            tree.focus_nav(self.selected)

    # ── View / Edit ───────────────────────────────────────────────────────────

    @work(exclusive=True)
    async def _show_view(self) -> None:
        """Dispatch to the correct content view based on the selected nav item.

        Four dispatch paths:
        1. FileNav("agent") — reads AGENT.md and shows the structured view
        2. FileNav("task_file") — reads the file and shows the structured view with the file's language
        3. FileNav("task_dir") — clears the content panel (no file to show)
        4. ContentNav — looks up the item in state and shows the structured view
        """
        if not self.selected:
            return
        content = self.query_one(ContentPanel)
        if content.is_editing:
            return
        if isinstance(self.selected, FileNav) and self.selected.kind == "agent":
            path = self._item_path()
            if not path or not path.exists() or not self.sm.state:
                return
            text = path.read_text(encoding="utf-8")
            agent_doc = SimpleNamespace(content=text)
            content.show_struct_view(agent_doc, "agent", self.sm.cfg(), self.sm.state)
            self.query_one(NavTree).focus()
        elif isinstance(self.selected, FileNav) and self.selected.kind == "task_file":
            path = self._item_path()
            if not path or not path.exists() or not self.sm.state:
                return
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                await content.show_view("_Cannot be rendered yet :)_")
                self.query_one(NavTree).focus()
                return
            file_doc = SimpleNamespace(content=text, language=FILE_LANGUAGES.get(path.suffix.lower(), ""))
            content.show_struct_view(file_doc, "agent", self.sm.cfg(), self.sm.state)
            self.query_one(NavTree).focus()
        elif isinstance(self.selected, FileNav) and self.selected.kind == "task_dir":
            content.clear()
            self.query_one(NavTree).focus()
        else:
            item = self._item()
            if not item or not self.sm.state:
                return
            assert isinstance(self.selected, ContentNav)
            content.show_struct_view(item, self.selected.kind, self.sm.cfg(), self.sm.state)
            # Re-focus NavTree: show_struct_view applies -view-struct which makes
            # StructuredEditor visible; its focusable children can steal focus.
            self.query_one(NavTree).focus()

    def _show_edit(self, select_all: bool = False) -> None:
        content = self.query_one(ContentPanel)
        if not self.selected:
            return
        if isinstance(self.selected, FileNav) and self.selected.kind == "agent":
            path = self._item_path()
            if not path or not path.exists():
                return
            self._file_snapshot.ensure_tracked(path)
            agent_doc = SimpleNamespace(content=path.read_text(encoding="utf-8"))
            if not self.sm.state:
                return
            content.enter_structured_edit(agent_doc, "agent", self.sm.cfg(), self.sm.state)
        elif isinstance(self.selected, FileNav) and self.selected.kind == "task_file":
            path = self._item_path()
            if not path or not path.exists() or not self.sm.state:
                return
            self._file_snapshot.ensure_tracked(path)
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                return
            file_doc = SimpleNamespace(content=text, language=FILE_LANGUAGES.get(path.suffix.lower(), ""))
            content.enter_structured_edit(file_doc, "agent", self.sm.cfg(), self.sm.state)
        else:
            item = self._item()
            if not item or not self.sm.state:
                return
            assert isinstance(self.selected, ContentNav)
            path = self._item_path()
            if path:
                self._file_snapshot.ensure_tracked(path)
            content.enter_structured_edit(item, self.selected.kind, self.sm.cfg(), self.sm.state, select_all=select_all)

    # ── Auto-save ─────────────────────────────────────────────────────────────

    def _save_current(self) -> None:
        content = self.query_one(ContentPanel)
        if not self.selected or not content.is_editing:
            return
        path = self._item_path()
        if not path:
            return
        new_text = content.editor_text
        try:
            path.write_text(new_text, encoding="utf-8")
            actual_path = self._rename_to_match_title(path, new_text)
            if actual_path != path:
                if isinstance(self.selected, ContentNav) and self.selected.kind == "task":
                    self._file_snapshot.build()
                else:
                    self._file_snapshot.mark_renamed(path, actual_path)
            else:
                self._file_snapshot.mark_written(path)
            self._sync_state()
        except Exception as e:
            self.notify(str(e), severity="error", timeout=4)

    def _rename_to_match_title(self, current_path: Path, new_text: str) -> Path:
        """Rename file or task dir if the title no longer matches the path name.

        Returns the path where the content now lives (unchanged if no rename needed).
        Only acts on ContentNav items — FileNav items and skills are left untouched.
        """
        if not isinstance(self.selected, ContentNav):
            return current_path
        if self.selected.kind == "skill":
            return current_path
        post = _fm.loads(new_text)
        new_title = str(post.metadata.get("title", ""))
        if not new_title:
            return current_path
        new_safe = sanitize_filename(new_title)
        item_id = self.selected.id
        if self.selected.kind == "task":
            task_dir = current_path.parent        # current_path is description.md
            desired_name = f"{item_id}-{new_safe}"
            if task_dir.name == desired_name:
                return current_path
            new_task_dir = task_dir.parent / desired_name
            task_dir.rename(new_task_dir)
            return new_task_dir / "description.md"
        else:
            desired_name = f"{item_id}-{new_safe}.md"
            if current_path.name == desired_name:
                return current_path
            new_path = current_path.parent / desired_name
            current_path.rename(new_path)
            return new_path

    # ── Drag-and-drop file attachment ─────────────────────────────────────────

    def on_paste(self, event: Paste) -> None:
        """Handle file drops via terminal paste events.

        Terminal emulators inject dragged file paths as paste events. We intercept
        these only when the editor is not open and the cursor is on a task or on a
        file/dir that lives inside a task directory, then copy the files into the
        task directory and persist attachment metadata.
        """
        content = self.query_one(ContentPanel)
        if content.is_editing:
            return
        task_dirs = self.sm.task_dirs()
        task_id = self._resolve_target_task_id(self.selected, task_dirs)
        if task_id is None:
            return
        paths = self._parse_file_paths(event.text)
        if not paths:
            return
        event.stop()
        task_dir = task_dirs.get(task_id)
        if not task_dir:
            return
        task = self.sm.item(ContentNav("task", task_id, "tasks"))
        if not isinstance(task, Task):
            return
        new_attachments = list(task.attachments)
        added_names: list[str] = []
        for source in paths:
            dest_name = self._resolve_attachment_name(task_dir, source.name)
            shutil.copy2(source, task_dir / dest_name)
            new_attachments.append(Attachment(
                filename=dest_name,
                added_at=datetime.now().isoformat(timespec="seconds"),
            ))
            added_names.append(dest_name)
        self.sm.store.tasks.save(task.model_copy(update={"attachments": new_attachments}))
        self._reload()
        self.notify(f"Attached: {', '.join(added_names)}", severity="information", timeout=3)

    @staticmethod
    def _resolve_target_task_id(nav: Nav | None, task_dirs: dict[str, Path]) -> str | None:
        """Return the task ID that should receive a file drop for the given nav.

        Handles two cases:
        - Cursor is on a task node directly → use that task.
        - Cursor is on a file or dir that lives inside a task directory → find
          the deepest owning task (deepest = most specific, handles subtask nesting).
        """
        if isinstance(nav, ContentNav) and nav.kind == "task":
            return nav.id
        if isinstance(nav, FileNav) and nav.kind in ("task_file", "task_dir"):
            matching = {
                task_id: task_dir
                for task_id, task_dir in task_dirs.items()
                if nav.path.is_relative_to(task_dir)
            }
            if matching:
                return max(matching, key=lambda tid: len(matching[tid].parts))
        return None

    @staticmethod
    def _parse_file_paths(text: str) -> list[Path]:
        """Parse pasted text into a list of existing file paths.

        Handles quoted paths, shell-escaped spaces, and multi-line paste (one path
        per line). Returns only paths that exist and are regular files.
        """
        paths: list[Path] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            for quote in ("'", '"'):
                if line.startswith(quote) and line.endswith(quote):
                    line = line[1:-1]
            line = re.sub(r"\\(.)", r"\1", line)
            candidate = Path(line)
            if candidate.exists() and candidate.is_file():
                paths.append(candidate)
        return paths

    @staticmethod
    def _resolve_attachment_name(task_dir: Path, filename: str) -> str:
        """Return a non-conflicting filename within task_dir.

        If *filename* already exists, appends '-2', '-3', etc. until a free name
        is found.
        """
        if not (task_dir / filename).exists():
            return filename
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 2
        while (task_dir / f"{stem}-{counter}{suffix}").exists():
            counter += 1
        return f"{stem}-{counter}{suffix}"

    # ── File watcher ──────────────────────────────────────────────────────────

    def _on_watch_tick(self) -> None:
        """Poll for external file changes every 150 ms.

        Debounces bursts of changes (e.g. the AI agent writing many files in
        quick succession) by waiting 300 ms of quiet before acting, so a rapid
        sequence of writes produces a single reload rather than many.
        Timing: 150 ms poll + 300 ms debounce → visible within ~450 ms of an
        external write.
        """
        try:
            changed = self._file_snapshot.scan()
            if changed:
                self._pending_reload = True
                self._last_change_at = time.monotonic()
                self._pending_changes |= changed
            if self._pending_reload and time.monotonic() - self._last_change_at >= 0.30:
                self._pending_reload = False
                self._handle_external_change(self._pending_changes)
                self._pending_changes = set()
        except Exception as exc:
            self.notify(f"File watcher error: {exc}", severity="error", timeout=10)

    @staticmethod
    def _rename_key(path: Path) -> tuple[tuple[Path, str], str] | None:
        """Return ((context_dir, item_id), slug) for a rename-detectable .md path, or None.

        Two patterns are recognised:
        - Flat file:       {dir}/{prefix-N}-{slug}.md   → context_dir=dir, id=prefix-N
        - Task description: {tasks}/{task-N}-{slug}/description.md → context_dir=tasks, id=task-N
        """
        if path.name == "description.md":
            task_match = _TASK_DIR_RENAME_RE.match(path.parent.name)
            if task_match:
                return (path.parent.parent, task_match.group(1)), task_match.group(2)
        elif path.suffix == ".md":
            flat_match = _FLAT_FILE_RENAME_RE.match(path.name)
            if flat_match:
                return (path.parent, flat_match.group(1)), flat_match.group(2)
        return None

    def _write_title_from_slug(self, path: Path, new_slug: str) -> None:
        """Overwrite the frontmatter 'title' in *path* with *new_slug* if it differs."""
        try:
            post = _fm.load(str(path))
            if str(post.metadata.get("title", "")) == new_slug:
                return
            post.metadata["title"] = new_slug
            path.write_text(_fm.dumps(post), encoding="utf-8")
            self._file_snapshot.mark_written(path)
        except Exception as exc:
            self.notify(f"Failed to update title in {path.name}: {exc}", severity="warning", timeout=4.0)

    def _apply_renames_to_frontmatter(self, changed_paths: set[str]) -> None:
        """Update frontmatter titles when .md files are renamed externally.

        Detects rename pairs — a path that disappeared (old) and a path that appeared
        (new) in the same directory with the same item ID — and updates the frontmatter
        'title' in the new file to match the new filename slug. This completes
        bidirectional sync: the TUI renames files when the title changes in the editor
        (_rename_to_match_title); here we update the title when the file is renamed
        externally so the NavTree label reflects the new name without the user also
        having to edit the frontmatter manually.
        """
        all_paths = [Path(p) for p in changed_paths]
        removed: list[Path] = [path for path in all_paths if not path.exists()]
        present: list[Path] = [path for path in all_paths if path.exists()]

        removed_by_key: dict[tuple[Path, str], Path] = {}
        for path in removed:
            result = self._rename_key(path)
            if result:
                key, _ = result
                removed_by_key[key] = path

        if not removed_by_key:
            return

        for path in present:
            result = self._rename_key(path)
            if result is None:
                continue
            lookup_key, new_slug = result
            if lookup_key not in removed_by_key:
                continue
            # Rename pair confirmed: update frontmatter title to match the new slug.
            self._write_title_from_slug(path, new_slug)

    def _handle_external_change(self, changed_paths: set[str]) -> None:
        """React to external file changes detected by the watcher.

        First syncs frontmatter titles from any detected filename renames, then
        applies conflict resolution:
        - If the user is editing the exact file that changed: notify, force-exit
          edit mode without saving, and reload so the agent's version is displayed.
        - If the user is editing a different file: reload the tree silently without
          disturbing the editor. The user can keep typing.
        - If the user is not editing: reload silently.
        """
        self._apply_renames_to_frontmatter(changed_paths)
        content = self.query_one(ContentPanel)
        if content.is_editing:
            editing_path = self._item_path()
            if editing_path and str(editing_path) in changed_paths:
                self.notify(
                    f"'{editing_path.name}' was updated on disk — your unsaved edits were overwritten.",
                    severity="warning",
                    timeout=6.0,
                )
                self._clear_edit_classes()
                self._update_footer_hints(self.selected)
        self._reload()

    # ── Misc ──────────────────────────────────────────────────────────────────

    def action_refresh_state(self) -> None:
        self._reload()
        self.notify("Refreshed", severity="information", timeout=2)

    def action_show_keybindings(self) -> None:
        self.push_screen(KeybindingsScreen())
