"""
pubrun status -- list and inspect runs.

Scans the configured output directory for run directories, classifies each
as completed/running/crashed, and renders tables or detailed views.
"""
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pubrun.capture.liveness import (
    get_cpu_percent,
    get_hostname,
    get_rss_bytes,
    is_same_process,
)
from pubrun.config import resolve_config
from pubrun.tracker import Run


# --------------------------------------------------------------------------
# Run classification
# --------------------------------------------------------------------------

# Status labels
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_RUNNING = "running"
STATUS_CRASHED = "crashed"
STATUS_GHOST = "ghost"


class RunInfo:
    """Lightweight descriptor for a single run directory."""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.run_id: Optional[str] = None
        self.script: Optional[str] = None
        self.status: str = STATUS_CRASHED  # default until proven otherwise
        self.exit_code: Optional[int] = None
        self.started_at_utc: Optional[float] = None
        self.ended_at_utc: Optional[float] = None
        self.elapsed: Optional[float] = None
        self.pid: Optional[int] = None
        self.hostname: Optional[str] = None
        self.git_commit: Optional[str] = None
        self.cwd: Optional[str] = None
        self.outcome: Optional[str] = None

        # Live process info (only for running)
        self.rss_bytes: Optional[int] = None
        self.cpu_percent: Optional[float] = None

        # Extra detail from manifest (for verbose/inspect)
        self.manifest: Optional[Dict[str, Any]] = None
        self.lock_data: Optional[Dict[str, Any]] = None
        self.event_count: Optional[int] = None
        self.console_log_size: Optional[int] = None
        self.signals_received: Optional[List[Dict[str, Any]]] = None

        self._classify()

    def _classify(self) -> None:
        """Determine run status from artifacts on disk."""
        manifest_path = self.run_dir / "manifest.json"
        lock_path = self.run_dir / Run.LOCK_FILENAME

        has_manifest = manifest_path.exists()
        has_lock = lock_path.exists()

        if has_manifest:
            self._load_from_manifest(manifest_path)
        elif has_lock:
            self._load_from_lock(lock_path)
        else:
            # No manifest, no lock -- parse what we can from directory name
            self._parse_dir_name()
            self.status = STATUS_CRASHED

    def _load_from_manifest(self, manifest_path: Path) -> None:
        """Load status from a completed run's manifest.json."""
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.manifest = data
            self.run_id = data.get("run", {}).get("run_id")
            self.outcome = data.get("status", {}).get("outcome", "unknown")

            timing = data.get("timing", {})
            self.started_at_utc = timing.get("started_at_utc")
            self.ended_at_utc = timing.get("ended_at_utc")
            self.elapsed = timing.get("elapsed_seconds")

            # Git
            git = data.get("git", {})
            self.git_commit = git.get("commit")

            # Invocation
            invocation = data.get("invocation", {})
            script_data = invocation.get("script", {})
            if isinstance(script_data, dict) and script_data.get("basename"):
                self.script = script_data["basename"]
            elif invocation.get("argv"):
                # Fallback: use first argv element (e.g. "-c", "train.py")
                self.script = Path(invocation["argv"][0]).stem

            # Signals/exit
            signals = data.get("signals", {})
            self.exit_code = signals.get("exit_code")
            self.signals_received = signals.get("signals_received", [])

            # Process
            process = data.get("process", {})
            self.pid = process.get("pid")
            self.hostname = data.get("host", {}).get("hostname")

            # Status mapping
            if self.outcome == "failed":
                self.status = STATUS_FAILED
            elif self.outcome == "ghost":
                self.status = STATUS_GHOST
            else:
                self.status = STATUS_COMPLETED

        except (json.JSONDecodeError, OSError):
            self._parse_dir_name()
            self.status = STATUS_CRASHED

    def _load_from_lock(self, lock_path: Path) -> None:
        """Load status from a lock file (in-progress or crashed)."""
        try:
            with open(lock_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.lock_data = data
            self.pid = data.get("pid")
            self.started_at_utc = data.get("started_at_utc")
            self.script = data.get("script")
            self.run_id = data.get("run_id")
            self.hostname = data.get("hostname")
            self.git_commit = data.get("git_commit")
            self.cwd = data.get("cwd")

            # Determine if the process is still alive
            current_host = get_hostname()
            if self.hostname and self.hostname != current_host:
                # Different host -- can't verify PID liveness
                # Assume running (could be on a cluster node)
                self.status = STATUS_RUNNING
                self.elapsed = time.time() - self.started_at_utc if self.started_at_utc else None
            elif self.pid and self.started_at_utc:
                if is_same_process(self.pid, self.started_at_utc):
                    self.status = STATUS_RUNNING
                    self.elapsed = time.time() - self.started_at_utc
                    # Fetch live resource usage
                    self.rss_bytes = get_rss_bytes(self.pid)
                    self.cpu_percent = get_cpu_percent(self.pid)
                else:
                    self.status = STATUS_CRASHED
                    self.elapsed = None  # Unknown when it died
            else:
                self.status = STATUS_CRASHED

            # Count events if available
            events_path = self.run_dir / "events.jsonl"
            if events_path.exists():
                try:
                    with open(events_path, "r", encoding="utf-8") as f:
                        self.event_count = sum(1 for _ in f)
                except OSError:
                    pass

            # Console log size
            console_path = self.run_dir / "console.log"
            if console_path.exists():
                try:
                    self.console_log_size = console_path.stat().st_size
                except OSError:
                    pass

        except (json.JSONDecodeError, OSError):
            self._parse_dir_name()
            self.status = STATUS_CRASHED

    def _parse_dir_name(self) -> None:
        """Extract what we can from the directory name pattern:
        pubrun-<script>-<timestamp>-<pid>-<run_id>
        """
        parts = self.run_dir.name.split("-")
        # Minimum expected: pubrun-script-timestamp-pid-runid
        if len(parts) >= 5 and parts[0] == "pubrun":
            self.script = parts[1]
            self.run_id = parts[-1]
            try:
                self.pid = int(parts[-2])
            except ValueError:
                pass


# --------------------------------------------------------------------------
# Scanning
# --------------------------------------------------------------------------

def scan_runs(output_dir: Optional[str] = None) -> List[RunInfo]:
    """Scan the output directory and return RunInfo for each run found.

    Args:
        output_dir: Override the configured output directory.  If None,
            uses the resolved config's ``[core].output_dir`` or ``./runs``.

    Returns:
        List of RunInfo objects, sorted by start time (most recent first).
    """
    if output_dir:
        base = Path(output_dir)
    else:
        config = resolve_config()
        base_str = config.get("core", {}).get("output_dir", "")
        base = Path(base_str) if base_str else Path.cwd() / "runs"

    if not base.exists():
        return []

    runs: List[RunInfo] = []
    for entry in base.iterdir():
        if entry.is_dir() and entry.name.startswith("pubrun-"):
            runs.append(RunInfo(entry))

    # Sort by start time (most recent first), with None-start at the end
    runs.sort(key=lambda r: r.started_at_utc or 0, reverse=True)
    return runs


def find_run(run_id_or_prefix: str, output_dir: Optional[str] = None) -> Optional[RunInfo]:
    """Find a specific run by ID or ID prefix.

    Args:
        run_id_or_prefix: Full run ID or a unique prefix.
        output_dir: Override the configured output directory.

    Returns:
        RunInfo for the matched run, or None if not found / ambiguous.
    """
    all_runs = scan_runs(output_dir)
    matches = [r for r in all_runs if r.run_id and r.run_id.startswith(run_id_or_prefix)]
    if len(matches) == 1:
        return matches[0]
    # Also try matching directory name suffix
    if not matches:
        matches = [r for r in all_runs if run_id_or_prefix in r.run_dir.name]
    if len(matches) == 1:
        return matches[0]
    return None


# --------------------------------------------------------------------------
# Formatting / rendering
# --------------------------------------------------------------------------

def _format_elapsed(seconds: Optional[float]) -> str:
    """Format elapsed seconds as a human-friendly string."""
    if seconds is None:
        return "-"
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}m{s:02d}s"
    else:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h{m:02d}m"


def _format_timestamp(epoch: Optional[float]) -> str:
    """Format a POSIX timestamp as a local datetime string."""
    if epoch is None:
        return "-"
    dt = datetime.fromtimestamp(epoch)
    return dt.strftime("%Y-%m-%d %H:%M")


def _format_bytes(nbytes: Optional[int]) -> str:
    """Format byte count as human-friendly string."""
    if nbytes is None:
        return "-"
    if nbytes < 1024:
        return f"{nbytes}B"
    elif nbytes < 1024 * 1024:
        return f"{nbytes / 1024:.0f}KB"
    elif nbytes < 1024 * 1024 * 1024:
        return f"{nbytes / (1024 * 1024):.1f}MB"
    else:
        return f"{nbytes / (1024 * 1024 * 1024):.2f}GB"


def _truncate(s: str, max_len: int) -> str:
    """Truncate a string with ellipsis if too long."""
    if len(s) <= max_len:
        return s
    return s[:max_len - 1] + "\u2026"


def _get_terminal_width() -> int:
    """Get terminal width, with a sensible fallback."""
    try:
        return shutil.get_terminal_size().columns
    except (AttributeError, ValueError):
        return 80


def _status_marker(status: str) -> str:
    """Return a colored/styled status string for terminal output."""
    # ANSI color codes (works on most terminals including Windows 10+)
    colors = {
        STATUS_COMPLETED: "\033[32m",   # green
        STATUS_FAILED: "\033[31m",      # red
        STATUS_RUNNING: "\033[33m",     # yellow
        STATUS_CRASHED: "\033[31m",     # red
        STATUS_GHOST: "\033[90m",       # gray
    }
    reset = "\033[0m"
    color = colors.get(status, "")
    return f"{color}{status}{reset}"


# --------------------------------------------------------------------------
# Public rendering functions
# --------------------------------------------------------------------------

def render_short_list(runs: List[RunInfo]) -> str:
    """Render a compact table of all runs.

    Columns: RUN ID, SCRIPT, COMMIT, STARTED, STATUS, EXIT, ELAPSED
    """
    if not runs:
        return "No runs found."

    term_width = _get_terminal_width()

    # Calculate script column width: at least 8, flexible based on terminal
    # Fixed columns take ~65 chars. Rest goes to script name.
    fixed_width = 10 + 9 + 18 + 12 + 6 + 8 + 6  # spacers between columns
    script_max = max(8, term_width - fixed_width)
    script_max = min(script_max, 24)  # cap at 24

    # Header
    hdr = (
        f"{'RUN ID':<10}"
        f"{'SCRIPT':<{script_max}}"
        f"{'COMMIT':<9}"
        f"{'STARTED':<18}"
        f"{'STATUS':<12}"
        f"{'EXIT':<6}"
        f"{'ELAPSED':<8}"
    )
    lines = [hdr, "-" * min(len(hdr), term_width)]

    for r in runs:
        run_id = (r.run_id or "-")[:8]
        script = _truncate(r.script or "-", script_max - 2)
        commit = (r.git_commit or "-")[:7]
        started = _format_timestamp(r.started_at_utc)
        status = _status_marker(r.status)
        exit_code = str(r.exit_code) if r.exit_code is not None else "-"
        elapsed = _format_elapsed(r.elapsed)

        line = (
            f"{run_id:<10}"
            f"{script:<{script_max}}"
            f"{commit:<9}"
            f"{started:<18}"
            f"{status:<21}"  # extra width for ANSI escape codes
            f"{exit_code:<6}"
            f"{elapsed:<8}"
        )
        lines.append(line)

    return "\n".join(lines)


def render_verbose_list(runs: List[RunInfo]) -> str:
    """Render a detailed table with additional columns.

    Adds: PID, HOSTNAME, RSS (for running), CPU% (for running), EVENTS, SIGNALS
    """
    if not runs:
        return "No runs found."

    lines = []
    for r in runs:
        run_id = (r.run_id or "-")[:8]
        script = r.script or "-"
        commit = (r.git_commit or "-")[:7]
        started = _format_timestamp(r.started_at_utc)
        status = _status_marker(r.status)
        exit_code = str(r.exit_code) if r.exit_code is not None else "-"
        elapsed = _format_elapsed(r.elapsed)
        pid = str(r.pid) if r.pid else "-"
        hostname = r.hostname or "-"
        rss = _format_bytes(r.rss_bytes) if r.status == STATUS_RUNNING else "-"
        cpu = f"{r.cpu_percent:.1f}%" if r.cpu_percent is not None and r.status == STATUS_RUNNING else "-"
        sig_count = str(len(r.signals_received)) if r.signals_received else "0"
        events = str(r.event_count) if r.event_count is not None else "-"

        lines.append(
            f"  Run ID:    {run_id}\n"
            f"  Script:    {script}\n"
            f"  Commit:    {commit}\n"
            f"  Status:    {status}\n"
            f"  Started:   {started}\n"
            f"  Elapsed:   {elapsed}\n"
            f"  Exit Code: {exit_code}\n"
            f"  PID:       {pid}\n"
            f"  Host:      {hostname}\n"
            f"  RSS:       {rss}\n"
            f"  CPU:       {cpu}\n"
            f"  Events:    {events}\n"
            f"  Signals:   {sig_count}\n"
            f"  Directory: {r.run_dir}\n"
        )

    sep = "\n" + "─" * 40 + "\n\n"
    return sep.join(lines)


def render_inspect(run_info: RunInfo) -> str:
    """Render detailed information about a single run."""
    lines: List[str] = []

    lines.append(f"Run: {run_info.run_id or '-'}")
    lines.append(f"{'=' * 50}")
    lines.append("")

    # Core info
    lines.append(f"  Script:        {run_info.script or '-'}")
    lines.append(f"  Status:        {_status_marker(run_info.status)}")
    lines.append(f"  Started:       {_format_timestamp(run_info.started_at_utc)}")
    if run_info.ended_at_utc:
        lines.append(f"  Ended:         {_format_timestamp(run_info.ended_at_utc)}")
    lines.append(f"  Elapsed:       {_format_elapsed(run_info.elapsed)}")
    lines.append(f"  Exit Code:     {run_info.exit_code if run_info.exit_code is not None else '-'}")
    lines.append("")

    # Process info
    lines.append(f"  PID:           {run_info.pid or '-'}")
    lines.append(f"  Hostname:      {run_info.hostname or '-'}")
    if run_info.cwd:
        lines.append(f"  Working Dir:   {run_info.cwd}")
    lines.append("")

    # Git
    lines.append(f"  Git Commit:    {run_info.git_commit or '-'}")
    lines.append("")

    # Live resource info (running only)
    if run_info.status == STATUS_RUNNING:
        lines.append("  Live Resources:")
        lines.append(f"    RSS Memory:  {_format_bytes(run_info.rss_bytes)}")
        cpu_str = f"{run_info.cpu_percent:.1f}%" if run_info.cpu_percent is not None else "-"
        lines.append(f"    CPU Usage:   {cpu_str}")
        lines.append("")

    # Events and console
    if run_info.event_count is not None:
        lines.append(f"  Events:        {run_info.event_count}")
    if run_info.console_log_size is not None:
        lines.append(f"  Console Log:   {_format_bytes(run_info.console_log_size)}")

    # Signals
    if run_info.signals_received:
        lines.append(f"  Signals ({len(run_info.signals_received)}):")
        for sig in run_info.signals_received:
            sig_name = sig.get("signal_name", "?")
            sig_time = _format_timestamp(sig.get("timestamp_utc"))
            lines.append(f"    {sig_name} at {sig_time}")
    else:
        lines.append(f"  Signals:       none")
    lines.append("")

    # Directory
    lines.append(f"  Directory:     {run_info.run_dir}")
    lines.append("")

    return "\n".join(lines)
