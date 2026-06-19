"""
Sidebar widget for run selection, search, and filtering.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from pathlib import Path

from textual.containers import Vertical
from textual.widgets import Tree, Input, Static
from textual.widgets.tree import TreeNode
from rich.text import Text

from pubrun.status import scan_runs, RunInfo, STATUS_COMPLETED, STATUS_FAILED, STATUS_INTERRUPTED, STATUS_BROKEN_PIPE, STATUS_RUNNING, STATUS_CRASHED, STATUS_GHOST

class RunsSidebar(Vertical):
    """Sidebar containing run search filtering and a tree view of detected runs."""

    def __init__(self, output_dir: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.output_dir = output_dir
        self.all_runs: List[RunInfo] = []

    def compose(self):
        yield Input(placeholder="Search script/ID...", id="runs-search")
        yield Tree("Runs", id="runs-tree")

    def on_mount(self) -> None:
        tree = self.query_one("#runs-tree", Tree)
        tree.show_root = False
        self.load_runs()

    def load_runs(self, filter_text: str = "") -> None:
        """Scan the runs folder and populate the tree view, optionally filtering by search text."""
        tree = self.query_one("#runs-tree", Tree)
        tree.clear()

        try:
            self.all_runs = scan_runs(self.output_dir)
        except Exception as e:
            self.all_runs = []
            tree.root.add_leaf(Text(f"Scan failed: {e}", style="red italic"))
            return

        filtered_runs = self.all_runs
        if filter_text:
            filter_text = filter_text.lower()
            filtered_runs = [
                r for r in self.all_runs 
                if (r.run_id and filter_text in r.run_id.lower()) or 
                   (r.script and filter_text in r.script.lower())
            ]

        if not filtered_runs:
            tree.root.add_leaf(Text("No runs found", style="dim italic"))
            return

        # Add runs to the tree
        status_colors = {
            STATUS_COMPLETED: "#a6e3a1",   # green
            STATUS_FAILED: "#f38ba8",      # red
            STATUS_INTERRUPTED: "#f9e2af", # yellow/orange
            STATUS_BROKEN_PIPE: "#f9e2af", # yellow/orange
            STATUS_RUNNING: "#89b4fa",     # blue
            STATUS_CRASHED: "#f38ba8",     # red
            STATUS_GHOST: "#a6adc8",       # gray
        }

        for r in filtered_runs:
            run_id = (r.run_id or "unknown")[:8]
            script_name = r.script or "unknown"
            status = r.status or "crashed"

            # Create colored text label
            label = Text(script_name, style="bold")
            label.append(f" [{run_id}]", style="dim")
            
            # Colored status indicator
            color = status_colors.get(status, "#f38ba8")
            label.append(f" • {status.upper()}", style=color)

            tree.root.add(label, data={"type": "run", "id": r.run_id, "run_info": r})

        # Expand tree root to show children
        tree.root.expand()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "runs-search":
            self.load_runs(event.value.strip())
