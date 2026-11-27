"""
Log viewer widget for interactive console logs and event stream navigation.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, List, Optional, Tuple

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, RichLog, Select

from pubrun.status import _format_bytes
from pubrun.tui.widgets.config import _is_select_empty

MAX_LOG_BYTES = 2 * 1024 * 1024  # 2 MiB tail window
MAX_LOG_LINES = 5000

_LOG_PRIORITY = {
    "stdout.log": 0,
    "stderr.log": 1,
    "console.log": 2,
}


def _log_sort_key(path: Path) -> Tuple[int, str, str]:
    """Deterministic sort key: stdout.log, stderr.log, legacy console.log, then alphabetical."""
    return (_LOG_PRIORITY.get(path.name, 3), path.name.lower(), path.name)


def _read_bounded_tail(
    path: Path,
    max_bytes: int = MAX_LOG_BYTES,
    max_lines: int = MAX_LOG_LINES,
) -> Tuple[str, bool, int]:
    """Read at most the final ``max_lines`` lines within ``max_bytes`` of EOF.

    Uses binary ``seek()`` so multi-hundred-MB logs never allocate full-file RAM.
    Returns ``(text, was_truncated, file_size_bytes)``.
    """
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        byte_truncated = file_size > max_bytes
        if byte_truncated:
            f.seek(file_size - max_bytes)
            raw = f.read(max_bytes)
            if b"\n" in raw:
                raw = raw.split(b"\n", 1)[1]
        else:
            f.seek(0)
            raw = f.read()

    decoded = raw.decode("utf-8", errors="replace")
    lines = decoded.splitlines()
    line_truncated = len(lines) > max_lines
    if line_truncated:
        lines = lines[-max_lines:]
    return ("\n".join(lines), byte_truncated or line_truncated, file_size)


class LogViewer(Vertical):
    """Component to select, load, and display log files associated with a run."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.run_dir: Optional[Path] = None
        self.log_files: List[Path] = []

    def compose(self) -> ComposeResult:
        with Horizontal(id="viewer-controls"):
            yield Select([], id="select-log-file", prompt="No logs available")
            yield Button("Wrap: OFF", id="btn-toggle-wrap", variant="primary")
            yield Button("Refresh", id="btn-refresh-log", variant="success")
        yield RichLog(id="log-content-area", classes="log-area")

    def display_run_logs(self, run_dir: Path) -> None:
        """Scan the run directory for log files and populate the selection dropdown."""
        self.run_dir = run_dir
        self.log_files = []

        select_widget = self.query_one("#select-log-file", Select)
        log_content = self.query_one("#log-content-area", RichLog)
        log_content.clear()

        if not run_dir or not run_dir.exists():
            with select_widget.prevent(Select.Changed):
                select_widget.set_options([])
            return

        # Scan for log files (.log, .jsonl, .txt) and sort deterministically.
        try:
            for entry in run_dir.iterdir():
                if entry.is_file() and entry.suffix in (".log", ".jsonl", ".txt"):
                    self.log_files.append(entry)
        except OSError:
            pass

        self.log_files.sort(key=_log_sort_key)

        if not self.log_files:
            with select_widget.prevent(Select.Changed):
                select_widget.set_options([])
            log_content.write("No log files found in this run directory.")
            log_content.write(
                'Tip: Enable console capture via [console].capture_mode = "standard" '
                "in .pubrun.toml or `import pubrun.full`."
            )
            return

        options = [(f.name, str(f)) for f in self.log_files]
        default_val = str(self.log_files[0])

        with select_widget.prevent(Select.Changed):
            select_widget.set_options(options)
            select_widget.value = default_val

        self.load_log_file(default_val)

    def load_log_file(self, file_path_str: str) -> None:
        """Load a bounded tail of the selected log file into the RichLog display."""
        log_content = self.query_one("#log-content-area", RichLog)
        log_content.clear()

        try:
            p = Path(file_path_str)
            if p.exists():
                content, truncated, file_size = _read_bounded_tail(p)
                if truncated:
                    log_content.write(
                        f"[Truncated: showing last {MAX_LOG_LINES:,} lines within final "
                        f"2 MiB of {_format_bytes(file_size)} file]"
                    )
                log_content.write(content)
            else:
                log_content.write("Selected log file does not exist.")
        except Exception as e:
            log_content.write(f"Failed to load log file: {e}")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-log-file" and not _is_select_empty(event.value) and event.value:
            self.load_log_file(str(event.value))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-toggle-wrap":
            log_content = self.query_one("#log-content-area", RichLog)
            log_content.wrap = not log_content.wrap
            btn = self.query_one("#btn-toggle-wrap", Button)
            btn.label = "Wrap: ON" if log_content.wrap else "Wrap: OFF"
            select_widget = self.query_one("#select-log-file", Select)
            if not _is_select_empty(select_widget.value) and select_widget.value:
                self.load_log_file(str(select_widget.value))
        elif event.button.id == "btn-refresh-log":
            select_widget = self.query_one("#select-log-file", Select)
            if not _is_select_empty(select_widget.value) and select_widget.value:
                self.load_log_file(str(select_widget.value))
