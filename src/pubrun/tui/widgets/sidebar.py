"""
Sidebar widget for run selection, search, and filtering.
"""

from __future__ import annotations
from typing import Any, List, Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Tree
from rich.text import Text

from pubrun.status import (
    RunInfo,
    STATUS_BROKEN_PIPE,
    STATUS_COMPLETED,
    STATUS_CRASHED,
    STATUS_FAILED,
    STATUS_GHOST,
    STATUS_INTERRUPTED,
    STATUS_RUNNING,
    scan_runs,
)

_STATUS_COLORS = {
    STATUS_COMPLETED: "#a6e3a1",    # green
    STATUS_FAILED: "#f38ba8",       # red
    STATUS_INTERRUPTED: "#f9e2af",  # yellow/orange
    STATUS_BROKEN_PIPE: "#f9e2af",  # yellow/orange
    STATUS_RUNNING: "#89b4fa",      # blue
    STATUS_CRASHED: "#f38ba8",      # red
    STATUS_GHOST: "#a6adc8",        # gray
}


class RunsSidebar(Vertical):
    """Sidebar containing run search filtering and a tree view of detected runs."""

    def __init__(self, output_dir: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.output_dir = output_dir
        self.all_runs: List[RunInfo] = []

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search script/ID/args/status...", id="runs-search")
        yield Tree("Runs", id="runs-tree")

    def on_mount(self) -> None:
        tree = self.query_one("#runs-tree", Tree)
        tree.show_root = False
        self.load_runs()

    def load_runs(self, filter_text: Optional[str] = None) -> None:
        """Scan the runs folder on disk and render the tree view."""
        tree = self.query_one("#runs-tree", Tree)
        tree.clear()

        if filter_text is None:
            try:
                filter_text = self.query_one("#runs-search", Input).value.strip()
            except Exception:
                filter_text = ""

        try:
            self.all_runs = scan_runs(self.output_dir, keep_manifest=False)
        except Exception as e:
            self.all_runs = []
            tree.root.add_leaf(Text(f"Scan failed: {e}", style="red italic"))
            return

        self._render_tree(filter_text)

    def _render_tree(self, filter_text: str = "") -> None:
        """Filter ``self.all_runs`` purely in memory and repopulate the tree."""
        tree = self.query_one("#runs-tree", Tree)
        tree.clear()

        needle = filter_text.strip().lower()
        if needle:
            filtered_runs = [
                r for r in self.all_runs
                if (r.run_id and needle in r.run_id.lower())
                or (r.script and needle in r.script.lower())
                or (r.args and needle in r.args.lower())
                or (r.status and needle in r.status.lower())
            ]
        else:
            filtered_runs = self.all_runs

        if not filtered_runs:
            tree.root.add_leaf(Text("No runs found", style="dim italic"))
            return

        for r in filtered_runs:
            run_id = (r.run_id or "unknown")[:8]
            script_name = r.script or "unknown"
            status = r.status or "crashed"

            label = Text(script_name, style="bold")
            label.append(f" [{run_id}]", style="dim")

            color = _STATUS_COLORS.get(status, "#f38ba8")
            label.append(f" • {status.upper()}", style=color)

            tree.root.add_leaf(label, data={"type": "run", "id": r.run_id, "run_info": r})

        tree.root.expand()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "runs-search":
            self._render_tree(event.value.strip())
