"""
Log viewer widget for interactive console logs and event stream navigation.
"""

from __future__ import annotations
import contextlib
from pathlib import Path
from typing import Dict, Any, List, Optional

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Select, Static, RichLog, Button

class LogViewer(Vertical):
    """Component to select, load, and display log files associated with a run."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.run_dir: Optional[Path] = None
        self.log_files: List[Path] = []

    def compose(self) -> ComposeResult:
        with Horizontal(id="viewer-controls"):
            yield Select([], id="select-log-file", prompt="No logs available")
            yield Button("Wrap Text", id="btn-toggle-wrap", variant="primary")
            yield Button("Refresh", id="btn-refresh-log", variant="success")
        yield RichLog(id="log-content-area", max_lines=5000, classes="log-area")

    def display_run_logs(self, run_dir: Path) -> None:
        """Scan the run directory for log files and populate the selection dropdown."""
        self.run_dir = run_dir
        self.log_files = []

        select_widget = self.query_one("#select-log-file", Select)
        log_content = self.query_one("#log-content-area", RichLog)
        log_content.clear()

        if not run_dir or not run_dir.exists():
            select_widget.set_options([])
            return

        # Scan for log files (.log or .jsonl)
        try:
            for entry in run_dir.iterdir():
                if entry.is_file() and entry.suffix in (".log", ".jsonl", ".txt"):
                    self.log_files.append(entry)
        except OSError:
            pass

        if not self.log_files:
            select_widget.set_options([])
            log_content.write("No log files found in this run directory.")
            return

        # Build options list
        options = [(f.name, str(f)) for f in self.log_files]
        select_widget.set_options(options)
        
        # Default select the first available log (often console.log, stdout.log)
        # Try to prioritize console.log or stdout.log
        default_val = None
        for f in self.log_files:
            if f.name in ("console.log", "stdout.log"):
                default_val = str(f)
                break
        if not default_val and self.log_files:
            default_val = str(self.log_files[0])

        if default_val:
            select_widget.value = default_val
            self.load_log_file(default_val)

    def load_log_file(self, file_path_str: str) -> None:
        """Load and print log contents to the RichLog display."""
        log_content = self.query_one("#log-content-area", RichLog)
        log_content.clear()

        try:
            p = Path(file_path_str)
            if p.exists():
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                
                # Write to the RichLog widget
                log_content.write(content)
            else:
                log_content.write("Selected log file does not exist.")
        except Exception as e:
            log_content.write(f"Failed to load log file: {e}")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-log-file" and event.value:
            self.load_log_file(str(event.value))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-toggle-wrap":
            log_content = self.query_one("#log-content-area", RichLog)
            log_content.wrap = not log_content.wrap
        elif event.button.id == "btn-refresh-log":
            select_widget = self.query_one("#select-log-file", Select)
            if select_widget.value:
                self.load_log_file(str(select_widget.value))
