"""Resource-usage view for the TUI: CPU / memory over a run's lifecycle.

Reuses the same per-sample series (`events.jsonl`) and peak/avg/min digest that `pubrun res`
renders on the CLI, so the numbers are identical. Degrades gracefully when a run has no
resource samples (short/old runs) or none captured.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Static

from pubrun.status import RunInfo


class RunResourcesView(Vertical):
    """Displays CPU/memory usage (summary + sparklines) for the selected run."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.run_info: Optional[RunInfo] = None

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Select a run to view its CPU and memory usage.", id="resources-body")
        )

    def display_run(self, run_info: RunInfo) -> None:
        """Render the resource digest for ``run_info`` (never raises)."""
        self.run_info = run_info
        body = self.query_one("#resources-body", Static)
        try:
            from pubrun.report.diagnostics import read_resource_series, format_resource_digest
            events = Path(run_info.run_dir) / "events.jsonl"
            if not events.exists():
                body.update("No resource samples recorded for this run "
                            "(no events.jsonl — the run was very short or resource capture "
                            "was off).")
                return
            series = read_resource_series(events)
            body.update(format_resource_digest(series))
        except Exception as e:  # a rendering hiccup must never crash the TUI
            body.update(f"Could not render resource usage: {type(e).__name__}: {e}")
