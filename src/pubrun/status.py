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


def _as_float(value: Any) -> Optional[float]:
    """Coerce a value read from a manifest/lock JSON to a finite float, or None.

    Manifests and lock files can be truncated by a killed process, hand-edited,
    or produced by a different pubrun version, so a field that should be a POSIX
    epoch may arrive as a string, bool, None, NaN, or infinity. Routing every
    numeric timing field through this single choke point keeps all downstream
    arithmetic (elapsed = now - started_at, sorting, formatting) safe by
    construction. (IPD 20260705 EC-01/EC-02/EC-03.)
    """
    if isinstance(value, bool):  # bool is an int subclass; never a timestamp
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        # Reject NaN / +-inf, which would crash datetime.fromtimestamp and
        # poison comparisons.
        if f != f or f in (float("inf"), float("-inf")):
            return None
        return f
    return None


def _as_int(value: Any) -> Optional[int]:
    """Coerce a value read from a manifest/lock JSON to an int, or None.

    Used for PID and exit-code fields, which must be integers before they reach
    ``os.kill``/liveness checks. (IPD 20260705 EC-01/EC-05.)
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        f = float(value)
        if f != f or f in (float("inf"), float("-inf")):
            return None
        return int(f)
    return None


def _as_signal_list(value: Any) -> List[Dict[str, Any]]:
    """Coerce a ``signals_received`` value to a list of dicts, dropping junk.

    A version-drifted or hand-edited manifest may store this as a non-list, or
    a list containing non-dict entries; iterating those with ``.get`` would
    raise. (IPD 20260705 EC-04.)
    """
    if not isinstance(value, list):
        return []
    return [s for s in value if isinstance(s, dict)]


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

        if run_dir is not None:
            self._classify()

    @classmethod
    def _make_degraded(cls, run_dir: Path) -> Optional["RunInfo"]:
        """Build a RunInfo with only defaults + the directory, skipping the
        artifact-parsing that raised. Used as the scan_runs backstop so one
        unreadable run cannot crash the whole listing. (IPD 20260705 EC-01.)
        """
        try:
            info = cls(None)  # type: ignore[arg-type]  # skips _classify
            info.run_dir = run_dir
            info.status = STATUS_CRASHED
            try:
                info.run_id = run_dir.name.split("-")[-1]
            except Exception:
                pass
            return info
        except Exception:
            return None

    def _enrich_from_manifest(self, manifest_path: Path) -> None:
        """Enrich a running/crashed run's metadata using the startup manifest."""
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.manifest = data

            git = data.get("git", {})
            if not self.git_commit:
                self.git_commit = git.get("commit")

            host = data.get("host", {})
            if isinstance(host, dict):
                hostname_val = host.get("hostname")
                if isinstance(hostname_val, dict):
                    self.hostname = hostname_val.get("value") or self.hostname
                elif isinstance(hostname_val, str):
                    self.hostname = hostname_val or self.hostname
        except Exception:
            pass

    def _classify(self) -> None:
        """Determine run status from artifacts on disk."""
        manifest_path = self.run_dir / "manifest.json"
        lock_path = self.run_dir / Run.LOCK_FILENAME

        has_manifest = manifest_path.exists()
        has_lock = lock_path.exists()

        if has_lock:
            self._load_from_lock(lock_path)
            if has_manifest:
                self._enrich_from_manifest(manifest_path)
        elif has_manifest:
            self._load_from_manifest(manifest_path)
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
            self.started_at_utc = _as_float(timing.get("started_at_utc"))
            self.ended_at_utc = _as_float(timing.get("ended_at_utc"))
            self.elapsed = _as_float(timing.get("elapsed_seconds"))

            # Git
            git = data.get("git", {})
            self.git_commit = git.get("commit")

            # Invocation
            invocation = data.get("invocation", {})
            script_data = invocation.get("script", {})
            if isinstance(script_data, dict) and script_data.get("basename"):
                self.script = script_data["basename"]
            elif invocation.get("argv"):
                # Fallback: use first argv element (e.g. "-c", "train.py").
                # Guard against a non-string argv[0] from a foreign/edited manifest.
                argv0 = invocation["argv"][0]
                if isinstance(argv0, str):
                    self.script = Path(argv0).stem

            # Command-line arguments (everything after the script name). Coerce
            # every element to str so a non-string entry cannot crash the join.
            argv = invocation.get("argv", [])
            if isinstance(argv, list) and len(argv) > 1:
                self.args = " ".join(str(a) for a in argv[1:])

            # Signals/exit
            signals = data.get("signals", {})
            self.exit_code = _as_int(signals.get("exit_code"))
            self.signals_received = _as_signal_list(signals.get("signals_received", []))

            # Process
            process = data.get("process", {})
            self.pid = _as_int(process.get("pid"))
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
            self.pid = _as_int(data.get("pid"))
            self.started_at_utc = _as_float(data.get("started_at_utc"))
            self.script = data.get("script")
            self.run_id = data.get("run_id")
            self.hostname = data.get("hostname")
            self.git_commit = data.get("git_commit")
            self.cwd = data.get("cwd")

            # Command-line arguments from lock file. Coerce every element to str
            # so a non-string entry (foreign/edited lock) cannot crash the join.
            argv = data.get("argv", [])
            if isinstance(argv, list) and argv:
                self.args = " ".join(str(a) for a in argv)

            # Determine if the process is still alive
            current_host = get_hostname()
            if self.hostname and self.hostname != current_host:
                # Different host -- can't verify PID liveness
                # If started more than 48 hours ago, assume crashed (stale lock from synced dir or dead node)
                age = time.time() - self.started_at_utc if self.started_at_utc else 0
                if age > 172800:  # 48 hours
                    self.status = STATUS_CRASHED
                    self.elapsed = None
                else:
                    # Assume running (could be on a cluster node)
                    self.status = STATUS_RUNNING
                    self.elapsed = time.time() - self.started_at_utc if self.started_at_utc else None
            elif self.pid and self.started_at_utc:
                if is_same_process(self.pid, self.started_at_utc, expected_script=self.script):
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

            # Count events if available.
            # PERF-10: estimate from file size instead of reading every line.
            # Average JSONL event line is ~120 bytes; this gives a fast O(1) estimate.
            events_path = self.run_dir / "events.jsonl"
            if events_path.exists():
                try:
                    file_size = events_path.stat().st_size
                    if file_size > 0:
                        # Use 120 bytes per line as a reasonable estimate for
                        # JSON event records. Accurate within ~20% for typical runs.
                        self.event_count = max(1, file_size // 120)
                    else:
                        self.event_count = 0
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
                pid = int(parts[-2])
                # Only accept a plausible positive PID; a non-positive or absurd
                # value from a malformed dir name must not reach os.kill.
                self.pid = pid if pid > 0 else None
            except (ValueError, OverflowError):
                pass


def filter_runs(
    runs: List[RunInfo],
    filter_str: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: Optional[int] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
    not_filter_str: Optional[str] = None,
    not_status_filter: Optional[str] = None,
) -> List[RunInfo]:
    """Filter a list of runs by search pattern, status, age limit, limit count, and exit code."""
    # 1. Filter by status
    if status_filter:
        allowed = [s.strip().lower() for s in status_filter.split(",")]
        runs = [r for r in runs if r.status.lower() in allowed]

    # 1b. Exclude by status
    if not_status_filter:
        excluded = [s.strip().lower() for s in not_status_filter.split(",")]
        runs = [r for r in runs if r.status.lower() not in excluded]

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

    # 2b. Exclude by search string/regex
    if not_filter_str:
        import re
        try:
            rx = re.compile(not_filter_str, re.IGNORECASE)
            runs = [r for r in runs if not (
                (r.script and rx.search(r.script)) or
                (r.args and rx.search(r.args)) or
                (r.run_id and rx.search(r.run_id))
            )]
        except re.error:
            q = not_filter_str.lower()
            runs = [r for r in runs if not (
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
    """Close out a crashed run by updating/writing manifest.json and removing the lock file."""
    manifest_path = run_dir / "manifest.json"
    lock_path = run_dir / Run.LOCK_FILENAME

    lock_data = lock_data or {}
    started_at = lock_data.get("started_at_utc")

    manifest = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            pass

    if not manifest:
        # Compile what we can into a fallback manifest
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
                    "basename": Path(str(lock_data.get("script"))).name if isinstance(lock_data.get("script"), str) else None,
                } if isinstance(lock_data.get("script"), str) else {},
                "argv": lock_data.get("argv", []),
                "capture_state": {"status": "partial"},
            },
            "git": {
                "commit": lock_data.get("git_commit"),
                "capture_state": {"status": "partial"},
            }
        }
    else:
        # Update status of existing manifest to crashed
        manifest["status"] = {
            "outcome": "crashed",
            "capture_state": {"status": "complete"},
        }

        # Estimate ended_at_utc from lock file modification time if available, or current time
        ended_at = time.time()
        if lock_path.exists():
            try:
                ended_at = lock_path.stat().st_mtime
            except OSError:
                pass

        timing = manifest.get("timing", {})
        timing["ended_at_utc"] = ended_at
        if timing.get("started_at_utc"):
            timing["elapsed_seconds"] = ended_at - timing["started_at_utc"]
        timing["capture_state"] = {"status": "partial"}
        manifest["timing"] = timing

    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        if lock_path.exists():
            lock_path.unlink()
        from pubrun.report import output as _out
        _out.info(f"Closed out crashed run '{run_dir.name}' (process dead). Updated manifest.json.")
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
            try:
                runs.append(RunInfo(entry))
            except Exception:
                # Backstop: a single malformed/foreign run directory must never
                # crash the whole listing. Numeric fields are coerced at the
                # source (see _as_float/_as_int), but this guards any unforeseen
                # bad field so the other runs still render. (IPD 20260705 EC-01.)
                degraded = RunInfo._make_degraded(entry)
                if degraded is not None:
                    runs.append(degraded)

    # Sort by start time (most recent first), with None/non-numeric start last.
    runs.sort(key=lambda r: r.started_at_utc if isinstance(r.started_at_utc, (int, float)) else 0, reverse=True)
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


# Display timezone preference for the CLI render. Timestamps are always STORED
# as UTC epochs; this only controls how status/show/inspect render them. Local
# is the default (researchers reason in local time); `pubrun ... --utc` sets
# this True. Kept as a module flag so it does not have to thread through every
# render function signature (KISS). (IPD 20260705 EC-17.)
_DISPLAY_UTC = False


def set_display_utc(utc: bool) -> None:
    """Set the CLI timestamp display timezone (True = UTC, False = local)."""
    global _DISPLAY_UTC
    _DISPLAY_UTC = bool(utc)


def _format_timestamp(epoch: Optional[float], utc: Optional[bool] = None) -> str:
    """Format a POSIX timestamp for display.

    Timestamps are stored as UTC epochs. By default they render in the viewer's
    LOCAL time; when the ``--utc`` flag is set (via ``set_display_utc``) or
    ``utc=True`` is passed, they render UTC with a ``Z`` suffix. Any non-numeric
    / out-of-range epoch (from a malformed or foreign manifest) degrades to
    ``"-"`` rather than crashing the render. (IPD 20260705 EC-03/EC-17.)
    """
    if epoch is None or not isinstance(epoch, (int, float)):
        return "-"
    use_utc = _DISPLAY_UTC if utc is None else utc
    try:
        if use_utc:
            dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M") + "Z"
        dt = datetime.fromtimestamp(epoch)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, OverflowError, OSError):
        return "-"


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

def _render_summary(runs: List[RunInfo]) -> str:
    """Render a 2-line summary: count, date range, status/exit frequencies."""
    from collections import Counter

    no_color = os.environ.get("NO_COLOR", "")
    bold = "" if no_color else "\033[1m"
    dim = "" if no_color else "\033[2m"
    red = "" if no_color else "\033[31m"
    reset = "" if no_color else "\033[0m"

    count = len(runs)
    # Date range (runs are sorted most-recent-first)
    earliest = None
    latest = None
    for r in runs:
        if r.started_at_utc is not None:
            if earliest is None or r.started_at_utc < earliest:
                earliest = r.started_at_utc
            if latest is None or r.started_at_utc > latest:
                latest = r.started_at_utc

    date_range = ""
    if earliest and latest:
        date_range = f" {dim}|{reset} {_format_timestamp(earliest)} to {_format_timestamp(latest)}"

    # Status frequencies (colored per status)
    statuses = Counter(r.status for r in runs)
    status_parts = [f"{c} {_status_marker(s)}" for s, c in statuses.most_common()]
    status_str = f"{dim},{reset} ".join(status_parts)

    # Exit code frequencies (non-zero only, to keep it concise)
    exit_codes = Counter(r.exit_code for r in runs if r.exit_code is not None and r.exit_code != 0)
    exit_str = ""
    if exit_codes:
        exit_parts = [f"{red}exit {code}{reset}: {c}" for code, c in exit_codes.most_common(5)]
        exit_str = f" {dim}|{reset} " + f"{dim},{reset} ".join(exit_parts)

    line1 = f"{bold}{count} runs{reset}{date_range}"
    line2 = f"  {status_str}{exit_str}"
    return f"{line1}\n{line2}"


def render_short_list(runs: List[RunInfo], all_runs: Optional[List[RunInfo]] = None) -> str:
    """Render a compact table of all runs.

    Args:
        runs: The runs to display in the table (may be filtered/limited).
        all_runs: The full unfiltered run set for the summary line. If None,
            uses ``runs`` for both the table and the summary.

    Columns: RUN ID, SCRIPT, COMMIT, STARTED, STATUS, EXIT, ELAPSED
    """
    if not runs:
        return (
            "No runs found.\n"
            "  To start tracking: import pubrun in your script,\n"
            "  or run: pubrun run -- python your_script.py"
        )

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

    # Append summary (based on full run set if provided)
    summary_runs = all_runs if all_runs is not None else runs
    lines.append("")
    summary = _render_summary(summary_runs)
    if all_runs is not None and len(all_runs) != len(runs):
        summary += f" (showing {len(runs)})"
    lines.append(summary)

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
        events = f"~{r.event_count} (est.)" if r.event_count else ("0" if r.event_count == 0 else "-")

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
        events_str = f"~{run_info.event_count} (est.)" if run_info.event_count else "0"
        lines.append(f"  Events:        {events_str}")
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
    not_filter_str: Optional[str] = None,
    not_status_filter: Optional[str] = None,
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
        not_filter_str=not_filter_str,
        not_status_filter=not_status_filter,
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
        from pubrun.report import output as _out
        _out.info("Dry run: no files were deleted.", stream=sys.stdout)
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

    # UX-06: Print summary before deleting (even with -y) so user sees what happened.
    total_size = sum(_dir_size(r.run_dir) for r in to_delete)
    print(f"\nDeleting {len(to_delete)} run(s) ({_format_bytes(total_size)})...")

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
