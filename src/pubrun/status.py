"""
pubrun status -- list and inspect runs.

Scans the configured output directory for run directories, classifies each
as completed/running/crashed, and renders tables or detailed views.
"""
import json
import os
import shutil
import sys
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
STATUS_INTERRUPTED = "interrupted"
STATUS_BROKEN_PIPE = "broken pipe"
STATUS_RUNNING = "running"
STATUS_CRASHED = "crashed"
STATUS_GHOST = "ghost"


class RunInfo:
    """Lightweight descriptor for a single run directory."""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.run_id: Optional[str] = None
        self.script: Optional[str] = None
        self.args: Optional[str] = None  # Command-line arguments (after script name)
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

    def _received_sigpipe(self) -> bool:
        """Check if SIGPIPE was received during the run."""
        if not self.signals_received:
            return False
        return any(
            s.get("signal_name") == "SIGPIPE" or s.get("signal") == 13
            for s in self.signals_received
        )

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

            # Command-line arguments (everything after the script name)
            argv = invocation.get("argv", [])
            if len(argv) > 1:
                self.args = " ".join(argv[1:])

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
            elif self.outcome == "crashed":
                self.status = STATUS_CRASHED
            elif self.outcome == "interrupted":
                self.status = STATUS_INTERRUPTED
            elif self.outcome == "ghost":
                self.status = STATUS_GHOST
            elif self._received_sigpipe():
                self.status = STATUS_BROKEN_PIPE
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

            # Command-line arguments from lock file
            argv = data.get("argv", [])
            if argv:
                self.args = " ".join(argv)

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


def filter_runs(
    runs: List[RunInfo],
    filter_str: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: Optional[int] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
) -> List[RunInfo]:
    """Filter a list of runs by search pattern, status, age limit, limit count, and exit code."""
    # 1. Filter by status
    if status_filter:
        allowed = [s.strip().lower() for s in status_filter.split(",")]
        runs = [r for r in runs if r.status.lower() in allowed]

    # 2. Filter by search string/regex
    if filter_str:
        import re
        try:
            rx = re.compile(filter_str, re.IGNORECASE)
            runs = [r for r in runs if (
                (r.script and rx.search(r.script)) or
                (r.args and rx.search(r.args)) or
                (r.run_id and rx.search(r.run_id))
            )]
        except re.error:
            q = filter_str.lower()
            runs = [r for r in runs if (
                (r.script and q in r.script.lower()) or
                (r.args and q in r.args.lower()) or
                (r.run_id and q in r.run_id.lower())
            )]

    # 3. Filter by age (older_than)
    if older_than:
        val = older_than.strip().lower()
        older_than_days = None
        try:
            if val.endswith("d"):
                older_than_days = float(val[:-1])
            elif val.endswith("h"):
                older_than_days = float(val[:-1]) / 24.0
            else:
                older_than_days = float(val)
        except ValueError:
            pass

        if older_than_days is not None:
            now = time.time()
            filtered = []
            for r in runs:
                if r.started_at_utc is None:
                    continue
                age_days = (now - r.started_at_utc) / 86400.0
                if age_days >= older_than_days:
                    filtered.append(r)
            runs = filtered

    # 4. Filter by exit code
    if exit_code is not None:
        runs = [r for r in runs if r.exit_code == exit_code]

    # 5. Limit
    if limit is not None and limit > 0:
        runs = runs[:limit]

    return runs


def close_out_crashed_run(run_dir: Path, lock_data: Optional[Dict[str, Any]]) -> None:
    """Close out a crashed run by writing a fallback manifest.json and removing the lock file."""
    manifest_path = run_dir / "manifest.json"
    lock_path = run_dir / Run.LOCK_FILENAME
    
    if manifest_path.exists():
        return
        
    lock_data = lock_data or {}
    started_at = lock_data.get("started_at_utc")
    
    # Compile what we can into a fallback manifest (with ended_at_utc / elapsed_seconds set to None since they are unknown)
    manifest = {
        "schema_version": "1.0",
        "manifest_type": "pubrun-manifest",
        "run": {
            "run_id": lock_data.get("run_id"),
            "capture_state": {"status": "partial"},
        },
        "status": {
            "outcome": "crashed",
            "capture_state": {"status": "complete"},
        },
        "timing": {
            "started_at_utc": started_at,
            "ended_at_utc": None,
            "elapsed_seconds": None,
            "capture_state": {"status": "partial"},
        },
        "capture": {
            "output_base_dir": None,
            "run_dir": str(run_dir),
            "capture_state": {"status": "unavailable"},
        },
        "process": {
            "pid": lock_data.get("pid"),
            "capture_state": {"status": "partial"},
        },
        "host": {
            "hostname": {
                "representation": "plain",
                "value": lock_data.get("hostname"),
            } if lock_data.get("hostname") else {
                "representation": "unavailable",
                "value": None,
            },
            "capture_state": {"status": "partial"},
        },
        "invocation": {
            "script": {
                "basename": Path(lock_data.get("script")).name if lock_data.get("script") else None,
            } if lock_data.get("script") else {},
            "argv": lock_data.get("argv", []),
            "capture_state": {"status": "partial"},
        },
        "git": {
            "commit": lock_data.get("git_commit"),
            "capture_state": {"status": "partial"},
        }
    }
    
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        if lock_path.exists():
            lock_path.unlink()
        print(f"[*] Closed out crashed run '{run_dir.name}' (process dead). Generated fallback manifest.json.", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Failed to close out crashed run '{run_dir.name}': {e}", file=sys.stderr)


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
    """Format elapsed seconds as a human-friendly string in HH:MM:SS (or Xd HH:MM:SS if >= 24h) format."""
    if seconds is None:
        return "unknown"
    
    is_negative = seconds < 0
    total_seconds = int(round(abs(seconds)))
    
    s = total_seconds % 60
    m = (total_seconds // 60) % 60
    h = total_seconds // 3600
    
    if h >= 24:
        days = h // 24
        hours = h % 24
        formatted = f"{days}d {hours:02d}:{m:02d}:{s:02d}"
    else:
        formatted = f"{h:02d}:{m:02d}:{s:02d}"
        
    return f"-{formatted}" if is_negative else formatted


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
    if os.environ.get("NO_COLOR", ""):
        return status
    # ANSI color codes (works on most terminals including Windows 10+)
    colors = {
        STATUS_COMPLETED: "\033[32m",   # green
        STATUS_FAILED: "\033[31m",      # red
        STATUS_INTERRUPTED: "\033[35m", # magenta
        STATUS_BROKEN_PIPE: "\033[33m", # yellow (warning, not error)
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

    # Calculate script column width: at least 8, flexible based on terminal.
    # Fixed columns take ~69 chars. Remaining space goes to script name,
    # capped at 40% of terminal width to keep the table balanced.
    fixed_width = 10 + 9 + 18 + 12 + 6 + 8 + 6  # spacers between columns
    available = term_width - fixed_width
    script_max = max(8, min(available, int(term_width * 0.4)))

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
        # Show script name + args if there's enough space
        script_name = r.script or "-"
        if r.args:
            script_with_args = f"{script_name} {r.args}"
        else:
            script_with_args = script_name
        script = _truncate(script_with_args, script_max - 2)
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

        args = r.args or "-"

        lines.append(
            f"  Run ID:    {run_id}\n"
            f"  Script:    {script}\n"
            f"  Args:      {args}\n"
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

    sep = "\n" + "-" * 40 + "\n\n"
    return sep.join(lines)


def render_inspect(run_info: RunInfo) -> str:
    """Render detailed information about a single run."""
    lines: List[str] = []

    lines.append(f"Run: {run_info.run_id or '-'}")
    lines.append(f"{'=' * 50}")
    lines.append("")

    # Core info
    lines.append(f"  Script:        {run_info.script or '-'}")
    if run_info.args:
        lines.append(f"  Arguments:     {run_info.args}")
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


# --------------------------------------------------------------------------
# Cleanup
# --------------------------------------------------------------------------

def _dir_size(path: Path) -> int:
    """Calculate total size of a directory in bytes."""
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    except OSError:
        pass
    return total


def _format_age(seconds: Optional[float]) -> str:
    """Format age in human-friendly terms."""
    if seconds is None:
        return "unknown"
    if seconds < 0:
        seconds = 0.0
    days = int(seconds // 86400)
    if days == 0:
        hours = int(seconds // 3600)
        if hours == 0:
            return f"{int(seconds // 60)}m ago"
        return f"{hours}h ago"
    elif days == 1:
        return "1 day ago"
    else:
        return f"{days} days ago"


def _parse_selection(response: str, candidates: List[Any]) -> List[Any]:
    """Parse a selection string like '1-3,5,7-9' into a list of items.

    Supports individual numbers, comma-separated numbers, and ranges.
    Invalid indices are silently skipped.
    """
    selected: List[Any] = []
    parts = [p.strip() for p in response.replace(" ", "").split(",")]
    for part in parts:
        if "-" in part and not part.startswith("-"):
            # Range: "1-3"
            try:
                start_s, end_s = part.split("-", 1)
                start_i = int(start_s) - 1
                end_i = int(end_s) - 1
                for idx in range(start_i, end_i + 1):
                    if 0 <= idx < len(candidates):
                        selected.append(candidates[idx])
            except (ValueError, IndexError):
                continue
        else:
            # Single number
            try:
                idx = int(part) - 1
                if 0 <= idx < len(candidates):
                    selected.append(candidates[idx])
            except (ValueError, IndexError):
                continue
    return selected


def clean_runs(
    output_dir: Optional[str] = None,
    older_than: Optional[str] = None,
    status_filter: Optional[Any] = None,
    yes: bool = False,
    dry_run: bool = False,
    filter_str: Optional[str] = None,
    limit: Optional[int] = None,
    exit_code: Optional[int] = None,
    # Backward compatibility:
    older_than_days: Optional[float] = None,
) -> int:
    """Interactively or automatically clean up old run directories.

    Args:
        output_dir: Override the configured output directory.
        older_than: Only consider runs older than this age (e.g. '7d', '24h').
        status_filter: Comma-separated status labels or list of statuses.
        yes: Skip confirmation prompt (non-interactive mode).
        dry_run: Show what would be deleted without deleting.
        filter_str: Regex or string query filter.
        limit: Limit number of runs to consider.
        exit_code: Filter by exit code.
        older_than_days: Backward-compatible float for age.

    Returns:
        Number of run directories deleted.
    """
    all_runs = scan_runs(output_dir)
    now = time.time()

    # 1. Resolve status filter (must never include STATUS_RUNNING)
    if status_filter is not None:
        if isinstance(status_filter, list):
            status_filter_list = [s.strip().lower() for s in status_filter]
        else:
            status_filter_list = [s.strip().lower() for s in str(status_filter).split(",")]
        status_filter_list = [s for s in status_filter_list if s != STATUS_RUNNING]
    else:
        status_filter_list = [STATUS_COMPLETED, STATUS_FAILED, STATUS_INTERRUPTED, STATUS_BROKEN_PIPE, STATUS_CRASHED, STATUS_GHOST]

    status_filter_str = ",".join(status_filter_list)

    # 2. Resolve older_than / older_than_days
    if older_than is None and older_than_days is not None:
        older_than = f"{older_than_days}d"

    # 3. Apply standard filter_runs
    candidates = filter_runs(
        all_runs,
        filter_str=filter_str,
        status_filter=status_filter_str,
        limit=limit,
        older_than=older_than,
        exit_code=exit_code,
    )

    if not candidates:
        print("No runs match the cleanup criteria.")
        return 0

    # Display candidates with terminal-width-adaptive columns
    term_width = _get_terminal_width()
    # Fixed columns: #(4) + RUN_ID(10) + STATUS(13) + EXIT(6) + AGE(14) + SIZE(10) = 57
    fixed_cols = 4 + 10 + 13 + 6 + 14 + 10
    script_max = max(8, min(term_width - fixed_cols, int(term_width * 0.4)))

    hdr = (
        f"{'#':<4}"
        f"{'RUN ID':<10}"
        f"{'SCRIPT':<{script_max}}"
        f"{'STATUS':<13}"
        f"{'EXIT':<6}"
        f"{'AGE':<14}"
        f"{'SIZE':<10}"
    )
    print(f"\n{hdr}")
    print("-" * min(len(hdr), term_width))
    for i, r in enumerate(candidates, 1):
        run_id = (r.run_id or "-")[:8]
        # Show script + args if space permits
        script_name = r.script or "-"
        if r.args:
            script_with_args = f"{script_name} {r.args}"
        else:
            script_with_args = script_name
        script = _truncate(script_with_args, script_max - 2)
        status = r.status
        exit_code = str(r.exit_code) if r.exit_code is not None else "-"
        age_seconds = (now - r.started_at_utc) if r.started_at_utc else None
        age = _format_age(age_seconds)
        size = _format_bytes(_dir_size(r.run_dir))
        print(
            f"{i:<4}"
            f"{run_id:<10}"
            f"{script:<{script_max}}"
            f"{status:<13}"
            f"{exit_code:<6}"
            f"{age:<14}"
            f"{size:<10}"
        )

    print(f"\n{len(candidates)} run(s) eligible for removal.")

    if dry_run:
        print("[dry run] No files were deleted.")
        return 0

    # Confirmation -- nothing is selected by default, requires explicit choice
    if not yes:
        try:
            prompt = "\nSelect runs to delete [numbers/ranges (e.g. 1-3,5), 'all', or Enter to cancel]: "
            response = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nCleanup cancelled.")
            return 0

        if response == "":
            print("Cleanup cancelled.")
            return 0
        elif response.lower() in ("n", "no", "none"):
            print("Cleanup cancelled.")
            return 0
        elif response.lower() == "all":
            to_delete = candidates
        else:
            # Parse comma-separated numbers and ranges (e.g. "1-3,5,7-9")
            to_delete = _parse_selection(response, candidates)
            if not to_delete:
                print("No valid selections. Cleanup cancelled.")
                return 0

        # Show what will be deleted
        print(f"\nThe following {len(to_delete)} run(s) will be permanently deleted:\n")
        print(
            f"{'#':<4}"
            f"{'RUN ID':<10}"
            f"{'SCRIPT':<{script_max}}"
            f"{'STATUS':<13}"
            f"{'EXIT':<6}"
            f"{'AGE':<14}"
            f"{'SIZE':<10}"
        )
        print("-" * min(term_width, 4 + 10 + script_max + 13 + 6 + 14 + 10))
        for i, r in enumerate(to_delete, 1):
            run_id = (r.run_id or "-")[:8]
            script_name = r.script or "-"
            if r.args:
                script_with_args = f"{script_name} {r.args}"
            else:
                script_with_args = script_name
            script_d = _truncate(script_with_args, script_max - 2)
            status_d = r.status
            exit_d = str(r.exit_code) if r.exit_code is not None else "-"
            age_s = (now - r.started_at_utc) if r.started_at_utc else None
            age_d = _format_age(age_s)
            size_d = _format_bytes(_dir_size(r.run_dir))
            print(
                f"{i:<4}"
                f"{run_id:<10}"
                f"{script_d:<{script_max}}"
                f"{status_d:<13}"
                f"{exit_d:<6}"
                f"{age_d:<14}"
                f"{size_d:<10}"
            )

        try:
            confirm = input(f"\nConfirm: permanently delete {len(to_delete)} run(s)? [y/N] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nCleanup cancelled.")
            return 0
        if confirm not in ("y", "yes"):
            print("Cleanup cancelled.")
            return 0
    else:
        to_delete = candidates

    # Delete
    deleted = 0
    for r in to_delete:
        try:
            shutil.rmtree(r.run_dir)
            deleted += 1
        except OSError as e:
            print(f"  Failed to remove {r.run_dir.name}: {e}", file=sys.stderr)

    print(f"\nDeleted {deleted} run(s).")
    return deleted
