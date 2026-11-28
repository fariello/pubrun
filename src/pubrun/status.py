"""
pubrun status -- list and inspect runs.

Scans the configured output directory for run directories, classifies each
as completed/running/crashed, and renders tables or detailed views.
"""
import json
import math
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Tuple, Union

from pubrun.capture.liveness import (
    get_cpu_percent,
    get_hostname,
    get_rss_bytes,
    is_same_process,
)
from pubrun.config import _section, resolve_config
from pubrun.report.output import use_color
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

VALID_STATUSES: Tuple[str, ...] = (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_INTERRUPTED,
    STATUS_BROKEN_PIPE,
    STATUS_RUNNING,
    STATUS_CRASHED,
    STATUS_GHOST,
)
_VALID_STATUS_SET = frozenset(VALID_STATUSES)


def _validate_status_tokens(tokens: List[str], *, flag_name: str = "--status") -> None:
    """Raise ValueError if any non-empty status token is not in VALID_STATUSES."""
    invalid = [t for t in tokens if t not in _VALID_STATUS_SET]
    if invalid:
        bad = ", ".join(repr(t) for t in invalid)
        valid_list = ", ".join(VALID_STATUSES)
        raise ValueError(
            f"Unknown status {bad} in {flag_name}. "
            f"Valid statuses are: {valid_list}."
        )


def _validate_limit(limit: Optional[int]) -> Optional[int]:
    """Validate limit is None or a non-negative integer (rejecting bool and < 0)."""
    if limit is None:
        return None
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise ValueError("limit must be a non-negative integer")
    return limit


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


def classify_timing_semantics(
    timing: Optional[Dict[str, Any]],
    *,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Classify manifest or live-run timing metadata into explicit display semantics.

    Handles explicit monotonic fields, legacy v1.0 wall-clock manifests (without
    ``duration_clock`` or ``elapsed_basis``), live running estimates, crashed
    estimates, session totals, and incomplete or malformed timing dicts safely.
    """
    if not isinstance(timing, dict):
        timing = {}

    if status == STATUS_RUNNING:
        return {
            "duration_clock": "wall_clock_estimated",
            "elapsed_basis": "running_estimate",
            "interval_scope": "tracked_interval",
            "label": "Elapsed (running, wall-clock estimate)",
            "is_legacy": False,
            "is_incomplete": False,
        }

    raw_clock = timing.get("duration_clock")
    duration_clock: Optional[str] = (
        raw_clock if isinstance(raw_clock, str) and raw_clock else None
    )
    raw_basis = timing.get("elapsed_basis")
    elapsed_basis: Optional[str] = (
        raw_basis if isinstance(raw_basis, str) and raw_basis else None
    )

    workload_val = _as_float(timing.get("workload_seconds"))
    elapsed_val = _as_float(timing.get("elapsed_seconds"))

    is_legacy = False
    if duration_clock is None and elapsed_basis is None and elapsed_val is not None:
        duration_clock = "wall_clock"
        elapsed_basis = "wall_clock_legacy"
        is_legacy = True

    raw_scope = timing.get("interval_scope")
    interval_scope = (
        raw_scope if isinstance(raw_scope, str) and raw_scope else "tracked_interval"
    )

    has_duration = (workload_val is not None) or (elapsed_val is not None)
    is_incomplete = not has_duration

    if elapsed_basis == "workload" and duration_clock == "monotonic":
        label = "Tracked workload (monotonic)"
    elif elapsed_basis == "session" and duration_clock == "monotonic":
        label = "Tracked session (monotonic)"
    elif elapsed_basis == "session":
        label = "Tracked session"
    elif elapsed_basis == "crashed_estimate":
        label = "Estimated elapsed (crashed, wall-clock)"
    elif elapsed_basis == "wall_clock_legacy":
        label = "Elapsed (legacy wall-clock, includes capture)"
    else:
        label = "Elapsed"

    return {
        "duration_clock": duration_clock,
        "elapsed_basis": elapsed_basis,
        "interval_scope": interval_scope,
        "label": label,
        "is_legacy": is_legacy,
        "is_incomplete": is_incomplete,
    }


class RunInfo:
    """Lightweight descriptor for a single run directory."""

    def __init__(self, run_dir: Path, *, keep_manifest: bool = True) -> None:
        self.run_dir = run_dir
        self._keep_manifest = keep_manifest
        self.run_id: Optional[str] = None
        self.script: Optional[str] = None
        self.args: Optional[str] = None  # Command-line arguments (after script name)
        self.status: str = STATUS_CRASHED  # default until proven otherwise
        self.exit_code: Optional[int] = None
        self.started_at_utc: Optional[float] = None
        self.ended_at_utc: Optional[float] = None
        self.elapsed: Optional[float] = None
        self.timing_semantics: Dict[str, Any] = classify_timing_semantics({})
        self.workload_seconds: Optional[float] = None
        self.startup_overhead_seconds: Optional[float] = None
        self.finalization_overhead_seconds: Optional[float] = None
        self.session_seconds: Optional[float] = None
        self.hardware_wait_seconds: Optional[float] = None
        self.background_hardware_seconds: Optional[float] = None
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
        self.config_notices: List[Dict[str, Any]] = []

        if run_dir is not None:
            self._classify()

    def load_manifest(self) -> Optional[Dict[str, Any]]:
        """Return the manifest dict, reading manifest.json on demand without retaining it."""
        if self.manifest is not None:
            return self.manifest
        if self.run_dir is None:
            return None
        manifest_path = self.run_dir / "manifest.json"
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def _populate_artifact_sizes(self) -> None:
        """Populate event_count and console_log_size via O(1) os.stat() calls."""
        events_path = self.run_dir / "events.jsonl"
        try:
            file_size = os.stat(events_path).st_size
            # Use 120 bytes per line as a fast O(1) estimate for JSONL event records.
            self.event_count = max(1, file_size // 120) if file_size > 0 else 0
        except OSError:
            pass

        split_total = 0
        found_split = False
        for log_name in ("stdout.log", "stderr.log"):
            try:
                split_total += os.stat(self.run_dir / log_name).st_size
                found_split = True
            except OSError:
                pass

        if found_split:
            self.console_log_size = split_total
        else:
            try:
                self.console_log_size = os.stat(self.run_dir / "console.log").st_size
            except OSError:
                pass

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
            if not isinstance(data, dict):
                return
            if self._keep_manifest:
                self.manifest = data

            git = _section(data, "git")
            if not self.git_commit:
                self.git_commit = git.get("commit")

            host = _section(data, "host")
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
            if not isinstance(data, dict):
                self._parse_dir_name()
                self.status = STATUS_CRASHED
                self.timing_semantics = classify_timing_semantics({}, status=self.status)
                return
            if self._keep_manifest:
                self.manifest = data
            self.run_id = _section(data, "run").get("run_id")
            self.outcome = _section(data, "status").get("outcome", "unknown")

            timing = _section(data, "timing")
            self.started_at_utc = _as_float(timing.get("started_at_utc"))
            self.ended_at_utc = _as_float(timing.get("ended_at_utc"))
            self.workload_seconds = _as_float(timing.get("workload_seconds"))
            self.startup_overhead_seconds = _as_float(timing.get("startup_overhead_seconds"))
            self.finalization_overhead_seconds = _as_float(
                timing.get("finalization_overhead_seconds")
            )
            self.session_seconds = _as_float(timing.get("session_seconds"))
            self.hardware_wait_seconds = _as_float(timing.get("hardware_wait_seconds"))
            self.background_hardware_seconds = _as_float(
                timing.get("background_hardware_seconds")
            )
            elapsed_raw = _as_float(timing.get("elapsed_seconds"))
            if timing.get("elapsed_basis") == "session" and elapsed_raw is not None:
                self.elapsed = elapsed_raw
            else:
                self.elapsed = (
                    self.workload_seconds
                    if self.workload_seconds is not None
                    else elapsed_raw
                )

            # Git
            git = _section(data, "git")
            self.git_commit = git.get("commit")

            # Invocation
            invocation = _section(data, "invocation")
            script_data = _section(invocation, "script")
            argv = invocation.get("argv")
            if script_data.get("basename"):
                self.script = script_data["basename"]
            elif isinstance(argv, list) and argv:
                # Fallback: use first argv element (e.g. "-c", "train.py").
                # Guard against a non-string argv[0] from a foreign/edited manifest.
                argv0 = argv[0]
                if isinstance(argv0, str):
                    self.script = Path(argv0).stem

            # Command-line arguments (everything after the script name). Coerce
            # every element to str so a non-string entry cannot crash the join.
            if isinstance(argv, list) and len(argv) > 1:
                self.args = " ".join(str(a) for a in argv[1:])

            # Signals/exit
            signals = _section(data, "signals")
            self.exit_code = _as_int(signals.get("exit_code"))
            self.signals_received = _as_signal_list(signals.get("signals_received", []))

            # Non-disruptive config notices (e.g. deprecated core.profile)
            cfg = _section(data, "config")
            notices = cfg.get("notices", [])
            if isinstance(notices, list):
                self.config_notices = [n for n in notices if isinstance(n, dict)]

            # Process
            process = _section(data, "process")
            self.pid = _as_int(process.get("pid"))
            # host.hostname is ``string | null`` per the schema; older crash
            # closeouts wrote a ``{"representation": ..., "value": ...}`` dict.
            host = _section(data, "host")
            hostname_val = host.get("hostname")
            if isinstance(hostname_val, dict):
                hostname_val = hostname_val.get("value")
            self.hostname = hostname_val if isinstance(hostname_val, str) and hostname_val else None

            # Status mapping
            if self.outcome == "failed":
                self.status = STATUS_FAILED
            elif self.outcome == "crashed":
                self.status = STATUS_CRASHED
            elif self.outcome == "interrupted":
                self.status = STATUS_INTERRUPTED
            elif self.outcome == "ghost":
                self.status = STATUS_GHOST
            elif self.outcome == "running":
                if (
                    (not self.hostname or self.hostname == get_hostname())
                    and self.pid
                    and self.pid > 0
                    and self.started_at_utc is not None
                    and is_same_process(
                        self.pid,
                        self.started_at_utc,
                        expected_script=self.script,
                    )
                ):
                    self.status = STATUS_RUNNING
                    if self.elapsed is None:
                        self.elapsed = max(0.0, time.time() - self.started_at_utc)
                    self.rss_bytes = get_rss_bytes(self.pid)
                    self.cpu_percent = get_cpu_percent(self.pid)
                else:
                    self.status = STATUS_CRASHED
            elif self._received_sigpipe():
                self.status = STATUS_BROKEN_PIPE
            else:
                self.status = STATUS_COMPLETED

            self.timing_semantics = classify_timing_semantics(timing, status=self.status)
            self._populate_artifact_sizes()

        except (json.JSONDecodeError, OSError):
            self._parse_dir_name()
            self.status = STATUS_CRASHED
            self.timing_semantics = classify_timing_semantics({}, status=self.status)

    def _load_from_lock(self, lock_path: Path) -> None:
        """Load status from a lock file (in-progress or crashed)."""
        try:
            with open(lock_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                self._parse_dir_name()
                self.status = STATUS_CRASHED
                self.timing_semantics = classify_timing_semantics({}, status=self.status)
                return
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
                age = time.time() - self.started_at_utc if self.started_at_utc is not None else 0.0
                if age > 172800:  # 48 hours
                    self.status = STATUS_CRASHED
                    self.elapsed = None
                else:
                    # Assume running (could be on a cluster node)
                    self.status = STATUS_RUNNING
                    self.elapsed = (
                        max(0.0, time.time() - self.started_at_utc)
                        if self.started_at_utc is not None
                        else None
                    )
            elif self.pid and self.started_at_utc is not None:
                if is_same_process(self.pid, self.started_at_utc, expected_script=self.script):
                    self.status = STATUS_RUNNING
                    self.elapsed = max(0.0, time.time() - self.started_at_utc)
                    # Fetch live resource usage
                    self.rss_bytes = get_rss_bytes(self.pid)
                    self.cpu_percent = get_cpu_percent(self.pid)
                else:
                    self.status = STATUS_CRASHED
                    self.elapsed = None  # Unknown when it died
            else:
                self.status = STATUS_CRASHED

            self.timing_semantics = classify_timing_semantics({}, status=self.status)
            self._populate_artifact_sizes()

        except (json.JSONDecodeError, OSError):
            self._parse_dir_name()
            self.status = STATUS_CRASHED
            self.timing_semantics = classify_timing_semantics({}, status=self.status)

    def _parse_dir_name(self) -> None:
        """Extract what we can from the directory name pattern:
        pubrun-<script>-<timestamp>-<pid>-<run_id>
        """
        parts = self.run_dir.name.split("-")
        # Minimum expected: pubrun-script-timestamp-pid-runid
        if len(parts) >= 5 and parts[0] == "pubrun":
            # The script name may itself contain hyphens; the last three parts
            # are always timestamp, pid, and run_id.
            self.script = "-".join(parts[1:-3])
            self.run_id = parts[-1]
            try:
                pid = int(parts[-2])
                # Only accept a plausible positive PID; a non-positive or absurd
                # value from a malformed dir name must not reach os.kill.
                self.pid = pid if pid > 0 else None
            except (ValueError, OverflowError):
                pass


_AGE_UNIT_DAYS = {
    "d": 1.0,
    "h": 1.0 / 24.0,
    "m": 1.0 / 1440.0,
    "s": 1.0 / 86400.0,
}


def _parse_older_than_days(older_than: Any) -> float:
    """Parse an age string ('7d', '24h', '30m', '90s', or bare days) into days.

    Raises ValueError for non-strings, empty strings, unknown units, malformed
    numbers, negative values, NaN, and infinity.
    """
    if not isinstance(older_than, str):
        raise ValueError(
            f"Invalid --older-than value {older_than!r}: expected a string such as '7d', '24h', '30m', '90s', or '3'."
        )
    val = older_than.strip().lower()
    if not val:
        raise ValueError(
            "Invalid --older-than value '': expected an age such as '7d', '24h', '30m', '90s', or '3'."
        )
    factor = 1.0
    number = val
    if val[-1] in _AGE_UNIT_DAYS:
        factor = _AGE_UNIT_DAYS[val[-1]]
        number = val[:-1].strip()
    try:
        amount = float(number)
    except ValueError:
        raise ValueError(
            f"Invalid --older-than value {older_than!r}: use a number with an optional unit "
            f"d (days), h (hours), m (minutes), or s (seconds)."
        ) from None
    if not math.isfinite(amount):
        raise ValueError(f"Invalid --older-than value {older_than!r}: age must be a finite number.")
    if amount < 0:
        raise ValueError(f"Invalid --older-than value {older_than!r}: age must not be negative.")
    return amount * factor


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
    _validate_limit(limit)

    # 1. Filter by status (validate non-empty tokens against VALID_STATUSES)
    if status_filter:
        allowed = [s.strip().lower() for s in status_filter.split(",") if s.strip()]
        _validate_status_tokens(allowed, flag_name="--status")
        if allowed:
            runs = [r for r in runs if r.status.lower() in allowed]
        else:
            runs = []

    # 1b. Exclude by status (validate non-empty tokens against VALID_STATUSES)
    if not_status_filter:
        excluded = [s.strip().lower() for s in not_status_filter.split(",") if s.strip()]
        _validate_status_tokens(excluded, flag_name="--not-status")
        if excluded:
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

    # 3. Filter by age (older_than). An invalid value raises rather than
    # silently disabling the filter, which would widen cleanup to every run.
    if older_than is not None:
        older_than_days = _parse_older_than_days(older_than)
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

    # 5. Limit (fail closed: limit == 0 returns [])
    if limit is not None:
        if limit == 0:
            return []
        runs = runs[:limit]

    return runs


def _crash_invocation_argv(lock_data: Dict[str, Any]) -> List[str]:
    """Rebuild a full ``invocation.argv`` (script first) from lock file data.

    The lock's ``argv`` holds ``sys.argv[1:]`` while ``sys_argv`` holds the full
    ``sys.argv``. Older lock files lack ``sys_argv``, so the script name is
    prepended to ``argv`` unless ``argv`` already starts with it.
    """
    sys_argv = lock_data.get("sys_argv")
    if isinstance(sys_argv, list) and sys_argv:
        return [str(a) for a in sys_argv]
    raw_argv = lock_data.get("argv")
    argv = [str(a) for a in raw_argv] if isinstance(raw_argv, list) else []
    script = lock_data.get("script")
    if isinstance(script, str) and script:
        if argv and (argv[0] == script or Path(argv[0]).stem == script):
            return argv
        return [script] + argv
    return argv


def can_safely_auto_close_crashed_run(
    run_dir: Path, lock_data: Optional[Dict[str, Any]]
) -> bool:
    """Return True only when a crashed run can be safely auto-closed on disk.

    Refuses to auto-close when:
    - ``.pubrun.lock`` is missing or unreadable (e.g. concurrent startup write),
    - the lock belongs to a different host (cannot verify remote PID liveness;
      protects long-running >48h HPC compute-node jobs), or
    - the recorded local PID is still alive for this run.
    """
    lock_path = run_dir / Run.LOCK_FILENAME
    if not lock_path.exists() or lock_path.is_symlink():
        return False

    disk_lock: Any = None
    try:
        with open(lock_path, "r", encoding="utf-8") as f:
            disk_lock = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False

    if not isinstance(disk_lock, dict):
        return False

    hostname = disk_lock.get("hostname")
    if isinstance(hostname, str) and hostname and hostname != get_hostname():
        return False

    pid = _as_int(disk_lock.get("pid"))
    started_at = _as_float(disk_lock.get("started_at_utc"))
    script = disk_lock.get("script")
    if not pid or pid <= 0 or started_at is None:
        return False

    return not is_same_process(
        pid,
        started_at,
        expected_script=script if isinstance(script, str) else None,
    )


def close_out_crashed_run(run_dir: Path, lock_data: Optional[Dict[str, Any]]) -> None:
    """Close out a crashed run by updating/writing manifest.json and removing the lock file."""
    manifest_path = run_dir / "manifest.json"
    lock_path = run_dir / Run.LOCK_FILENAME

    # TOCTOU re-check: if a live local process still owns the lock, never touch
    # its lock or manifest.
    if lock_path.exists():
        try:
            with open(lock_path, "r", encoding="utf-8") as f:
                disk_lock = json.load(f)
            if isinstance(disk_lock, dict):
                l_host = disk_lock.get("hostname")
                l_pid = _as_int(disk_lock.get("pid"))
                l_start = _as_float(disk_lock.get("started_at_utc"))
                l_script = disk_lock.get("script")
                if (
                    (not l_host or l_host == get_hostname())
                    and l_pid
                    and l_pid > 0
                    and l_start is not None
                    and is_same_process(
                        l_pid,
                        l_start,
                        expected_script=l_script if isinstance(l_script, str) else None,
                    )
                ):
                    return
        except (OSError, json.JSONDecodeError):
            pass

    lock_data = lock_data or {}
    started_at = lock_data.get("started_at_utc")

    manifest = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                manifest = loaded
        except Exception:
            pass

    # If the lock vanished and the manifest already carries a finalized terminal
    # outcome, the run completed between scan and closeout -- do not overwrite it.
    if not lock_path.exists() and manifest:
        existing_outcome = (
            manifest.get("status", {}).get("outcome")
            if isinstance(manifest.get("status"), dict)
            else None
        )
        if existing_outcome in ("completed", "failed", "interrupted", "ghost"):
            return

    if not manifest:
        # Compile what we can into a schema-valid fallback manifest
        lock_hostname = lock_data.get("hostname")
        fallback_hostname = lock_hostname if isinstance(lock_hostname, str) and lock_hostname else None
        raw_run_id = lock_data.get("run_id")
        if isinstance(raw_run_id, str) and raw_run_id:
            fallback_run_id = raw_run_id
        else:
            parts = run_dir.name.split("-")
            if len(parts) >= 5 and parts[0] == "pubrun" and parts[-1]:
                fallback_run_id = parts[-1]
            else:
                fallback_run_id = "unknown"
        fallback_started_at = _as_float(started_at)
        if fallback_started_at is None:
            for probe in (lock_path, run_dir):
                try:
                    if probe.exists():
                        fallback_started_at = float(probe.stat().st_mtime)
                        break
                except OSError:
                    pass
        if fallback_started_at is None:
            fallback_started_at = time.time()
        manifest = {
            "schema_version": "1.0",
            "manifest_type": "pubrun-manifest",
            "run": {
                "run_id": fallback_run_id,
                "capture_state": {"status": "partial"},
            },
            "status": {
                "outcome": "crashed",
                "capture_state": {"status": "complete"},
            },
            "timing": {
                "started_at_utc": fallback_started_at,
                "ended_at_utc": None,
                "elapsed_seconds": None,
                "duration_clock": None,
                "elapsed_basis": None,
                "interval_scope": "tracked_interval",
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
                "hostname": fallback_hostname,
                "capture_state": {"status": "partial"},
            },
            "invocation": {
                "script": {
                    "basename": Path(str(lock_data.get("script"))).name if isinstance(lock_data.get("script"), str) else None,
                } if isinstance(lock_data.get("script"), str) else {},
                "argv": _crash_invocation_argv(lock_data),
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

        raw_timing = manifest.get("timing")
        timing = raw_timing if isinstance(raw_timing, dict) else {}
        timing["ended_at_utc"] = ended_at
        started_at_val = _as_float(timing.get("started_at_utc"))
        if started_at_val is not None:
            timing["elapsed_seconds"] = max(0.0, ended_at - started_at_val)
            timing["duration_clock"] = "wall_clock_estimated"
            timing["elapsed_basis"] = "crashed_estimate"
        else:
            timing["elapsed_seconds"] = None
            timing["duration_clock"] = None
            timing["elapsed_basis"] = None
        timing["interval_scope"] = "tracked_interval"
        timing["capture_state"] = {"status": "partial"}
        manifest["timing"] = timing

    try:
        from pubrun.writer import _atomic_json_write
        _atomic_json_write(manifest_path, manifest, durability="fsync")
        if lock_path.exists():
            lock_path.unlink()
        from pubrun.report import output as _out
        _out.info(f"Closed out crashed run '{run_dir.name}' (process dead). Updated manifest.json.")
    except Exception as e:
        print(f"Warning: Failed to close out crashed run '{run_dir.name}': {e}", file=sys.stderr)


# --------------------------------------------------------------------------
# Scanning
# --------------------------------------------------------------------------

def _resolve_output_dir(output_dir: Optional[Union[str, "os.PathLike[str]"]] = None) -> Path:
    """Resolve the runs output directory from an override, config, or ./runs."""
    if output_dir:
        raw = os.fspath(output_dir)
        return Path(os.path.expanduser(os.path.expandvars(raw)))
    config = resolve_config()
    base_str = _section(config, "core").get("output_dir", "")
    if isinstance(base_str, str) and base_str:
        return Path(os.path.expanduser(os.path.expandvars(base_str)))
    return Path.cwd() / "runs"


def scan_runs(
    output_dir: Optional[str] = None,
    *,
    keep_manifest: bool = True,
) -> List[RunInfo]:
    """Scan the output directory and return RunInfo for each run found.

    Args:
        output_dir: Override the configured output directory.  If None,
            uses the resolved config's ``[core].output_dir`` or ``./runs``.
        keep_manifest: When True (default), retain each run's parsed
            ``manifest.json`` dict on ``RunInfo.manifest`` for backward
            compatibility. When False, release the dict immediately after
            extracting summary fields (use ``RunInfo.load_manifest()`` to
            reload on demand).

    Returns:
        List of RunInfo objects, sorted by start time (most recent first).
    """
    base = _resolve_output_dir(output_dir)
    if not base.exists():
        return []

    runs: List[RunInfo] = []
    try:
        with os.scandir(base) as it:
            for entry in it:
                try:
                    if not entry.name.startswith("pubrun-"):
                        continue
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                except OSError:
                    continue
                entry_path = Path(entry.path)
                try:
                    runs.append(RunInfo(entry_path, keep_manifest=keep_manifest))
                except Exception:
                    # Backstop: a single malformed/foreign run directory must never
                    # crash the whole listing. Numeric fields are coerced at the
                    # source (see _as_float/_as_int), but this guards any unforeseen
                    # bad field so the other runs still render. (IPD 20260705 EC-01.)
                    degraded = RunInfo._make_degraded(entry_path)
                    if degraded is not None:
                        runs.append(degraded)
    except OSError:
        return []

    # Sort by start time (most recent first), with None/non-numeric start last.
    runs.sort(key=lambda r: r.started_at_utc if isinstance(r.started_at_utc, (int, float)) else 0, reverse=True)
    return runs


class AmbiguousRunSelectorError(Exception):
    """A run selector matched multiple runs; refuse to guess.

    Carries either ``(by_recency, by_id)`` for recency-index vs exact-ID collisions
    or ``candidates`` for ambiguous ID-prefix / directory-substring matches.
    """

    def __init__(
        self,
        selector: str,
        by_recency: Optional[RunInfo] = None,
        by_id: Optional[RunInfo] = None,
        *,
        candidates: Optional[List[RunInfo]] = None,
    ) -> None:
        self.selector = selector
        self.by_recency = by_recency
        self.by_id = by_id
        if candidates is not None:
            self.candidates: List[RunInfo] = list(candidates)
        else:
            self.candidates = [c for c in (by_recency, by_id) if c is not None]

        if by_recency is not None and by_id is not None:
            msg = f"run selector {selector!r} is ambiguous (recency index vs run id)"
        else:
            ids = [c.run_id or c.run_dir.name for c in self.candidates]
            listed = ", ".join(ids[:10])
            if len(ids) > 10:
                listed += f", ... ({len(ids)} total)"
            msg = (
                f"run selector {selector!r} is ambiguous; "
                f"matched {len(self.candidates)} runs: {listed}"
            )
        super().__init__(msg)


def find_run(
    run_id_or_prefix: str,
    output_dir: Optional[str] = None,
    *,
    runs: Optional[List[RunInfo]] = None,
) -> Optional[RunInfo]:
    """Find a specific run by recency index, ID, ID prefix, or directory substring.

    Resolution order:
      1. A bare positive integer ``1 <= n <= len(all_runs)`` is a RECENCY INDEX
         (1 = most recent). If a run is literally named the exact integer and is
         not that recency entry, raise ``AmbiguousRunSelectorError``. Values above
         ``len(all_runs)`` fall through to ID/directory lookup.
      2. Exact/prefix match on ``run_id`` (unique match wins; multiple ambiguous
         matches raise ``AmbiguousRunSelectorError`` with ``candidates``).
      3. Directory-name substring match (unique match wins; multiple matches
         raise ``AmbiguousRunSelectorError`` with ``candidates``).

    Args:
        run_id_or_prefix: Recency index, full run ID, unique prefix, or directory substring.
        output_dir: Override the configured output directory.
        runs: Optional pre-scanned list of ``RunInfo`` objects to search without
            rescanning disk.

    Returns:
        RunInfo for the matched run, or None if not found.

    Raises:
        AmbiguousRunSelectorError: When the selector matches multiple runs.
    """
    sel = run_id_or_prefix.strip()
    if not sel:
        return None

    if runs is not None:
        all_runs = runs
    else:
        # Fast path for non-digit full run IDs (>= 8 chars): scan directory names
        # without opening every manifest.json, falling back to full scan if ambiguous
        # or if the run uses a custom directory name.
        if not sel.isdigit() and len(sel) >= 8:
            base = _resolve_output_dir(output_dir)
            if base.exists():
                suffix = "-" + sel
                suffix_matches: List[Path] = []
                substr_hits = 0
                try:
                    with os.scandir(base) as it:
                        for entry in it:
                            try:
                                if not entry.name.startswith("pubrun-"):
                                    continue
                                if not entry.is_dir(follow_symlinks=False):
                                    continue
                            except OSError:
                                continue
                            if sel in entry.name:
                                substr_hits += 1
                            if entry.name.endswith(suffix):
                                suffix_matches.append(Path(entry.path))
                except OSError:
                    suffix_matches = []
                if len(suffix_matches) == 1 and substr_hits == 1:
                    try:
                        candidate = RunInfo(suffix_matches[0], keep_manifest=False)
                        if candidate.run_id == sel:
                            return candidate
                    except Exception:
                        pass

        all_runs = scan_runs(output_dir, keep_manifest=False)

    # (1) Recency index: any bare positive integer 1 <= n <= len(all_runs) resolves
    # to all_runs[n - 1], with exact-ID collision guard.
    if sel.isdigit():
        n = int(sel)
        if n >= 1:
            by_recency = all_runs[n - 1] if n <= len(all_runs) else None
            exact_id = [r for r in all_runs if r.run_id == sel]
            other_exact = [r for r in exact_id if r is not by_recency]
            if by_recency is not None and other_exact:
                # One or more runs are literally named the same as the recency
                # index -> do not guess.
                raise AmbiguousRunSelectorError(
                    sel,
                    by_recency,
                    other_exact[0],
                    candidates=[by_recency, *other_exact],
                )
            if by_recency is not None:
                return by_recency
            # Out of range: fall through to id/dirname resolution.

    # (2) id / prefix match.
    matches = [r for r in all_runs if r.run_id and r.run_id.startswith(sel)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        exact = [r for r in matches if r.run_id == sel]
        if len(exact) == 1:
            return exact[0]
        raise AmbiguousRunSelectorError(sel, None, None, candidates=matches)

    # (3) directory-name substring match.
    matches = [r for r in all_runs if sel in r.run_dir.name]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise AmbiguousRunSelectorError(sel, None, None, candidates=matches)
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


def _format_duration_detail(seconds: Optional[float]) -> str:
    """Format a duration with millisecond visibility for sub-minute intervals."""
    val = _as_float(seconds)
    if val is None:
        return "unknown"
    clamped = max(0.0, val)
    if clamped < 60.0:
        return f"{clamped:.3f}s"
    return f"{_format_elapsed(clamped)} ({clamped:.1f}s)"


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


def _truncate(s: str, max_len: int, *, stream: Optional[TextIO] = None) -> str:
    """Truncate a string with ellipsis if too long, using ASCII '...' when needed."""
    if max_len <= 0:
        return ""
    if len(s) <= max_len:
        return s
    target = stream if stream is not None else sys.stdout
    encoding = getattr(target, "encoding", None) or "utf-8"
    try:
        "\u2026".encode(encoding)
        return s[:max_len - 1] + "\u2026"
    except (UnicodeEncodeError, LookupError):
        if max_len >= 3:
            return s[:max_len - 3] + "..."
        return s[:max_len]


def _get_terminal_width() -> int:
    """Get terminal width, with a sensible fallback."""
    try:
        return shutil.get_terminal_size().columns
    except (AttributeError, ValueError):
        return 80


def _status_marker(status: str, *, color: Optional[bool] = None) -> str:
    """Return a colored/styled status string for terminal output."""
    use_ansi = use_color(sys.stdout) if color is None else bool(color)
    if not use_ansi:
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
    code = colors.get(status, "")
    return f"{code}{status}{reset}" if code else status


# --------------------------------------------------------------------------
# Public rendering functions
# --------------------------------------------------------------------------

_NO_RUNS_GUIDANCE = (
    "No runs found.\n"
    "  To start tracking: add 'import pubrun' to your script and run it normally,\n"
    "  or run 'pubrun init' to create a .pubrun.toml configuration file."
)


def _render_summary(runs: List[RunInfo], *, color: Optional[bool] = None) -> str:
    """Render a 2-line summary: count, date range, status/exit frequencies."""
    from collections import Counter

    use_ansi = use_color(sys.stdout) if color is None else bool(color)
    bold = "\033[1m" if use_ansi else ""
    red = "\033[31m" if use_ansi else ""
    reset = "\033[0m" if use_ansi else ""

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
        date_range = f" | {_format_timestamp(earliest)} to {_format_timestamp(latest)}"

    # Status frequencies (colored per status)
    statuses = Counter(r.status for r in runs)
    status_parts = [f"{c} {_status_marker(s, color=use_ansi)}" for s, c in statuses.most_common()]
    status_str = ", ".join(status_parts)

    # Exit code frequencies (non-zero only, to keep it concise)
    exit_codes = Counter(r.exit_code for r in runs if r.exit_code is not None and r.exit_code != 0)
    exit_str = ""
    if exit_codes:
        exit_parts = [f"{red}exit {code}{reset}: {c}" for code, c in exit_codes.most_common(5)]
        exit_str = " | " + ", ".join(exit_parts)

    line1 = f"{bold}{count} runs{reset}{date_range}"
    line2 = f"  {status_str}{exit_str}"
    return f"{line1}\n{line2}"


def render_short_list(runs: List[RunInfo], all_runs: Optional[List[RunInfo]] = None) -> str:
    """Render a compact table of all runs.

    Args:
        runs: The runs to display in the table (may be filtered/limited).
        all_runs: The full unfiltered run set for the summary line. If None,
            uses ``runs`` for both the table and the summary.

    Columns: #, RUN ID, SCRIPT, [COMMIT when width >= 76], STARTED, STATUS, EXIT, ELAPSED
    """
    if not runs:
        if all_runs:
            return (
                f"0 of {len(all_runs)} runs matched the filter criteria. "
                "Run 'pubrun status' to list all runs."
            )
        return _NO_RUNS_GUIDANCE

    term_width = _get_terminal_width()

    # Recency index (#1 = most recent) from the FULL run set, so the number a user passes
    # to any command (`pubrun show 2`) matches what this column shows even when filtered.
    recency_of = {}
    _order = all_runs if all_runs is not None else runs
    for i, r in enumerate(_order, start=1):
        recency_of[id(r)] = i

    idx_width = max(4, len(str(len(_order))) + 2)
    show_commit = term_width >= 76

    # Calculate script column width: at least 8, flexible based on terminal.
    # Remaining space goes to script name, capped at 40% of terminal width.
    fixed_width = idx_width + 10 + (9 if show_commit else 0) + 18 + 12 + 6 + 8 + 2
    available = term_width - fixed_width
    script_max = max(8, min(available, int(term_width * 0.4)))

    # Header
    commit_hdr = f"{'COMMIT':<9}" if show_commit else ""
    hdr = (
        f"{'#':<{idx_width}}"
        f"{'RUN ID':<10}"
        f"{'SCRIPT':<{script_max}}"
        f"{commit_hdr}"
        f"{'STARTED':<18}"
        f"{'STATUS':<12}"
        f"{'EXIT':<6}"
        f"{'ELAPSED':<8}"
    )
    lines = [hdr, "-" * min(len(hdr), term_width)]

    for r in runs:
        idx = recency_of.get(id(r))
        idx_str = f"{idx}" if idx is not None else "-"
        run_id = (r.run_id or "-")[:8]
        # Show script name + args if there's enough space
        script_name = r.script or "-"
        if r.args:
            script_with_args = f"{script_name} {r.args}"
        else:
            script_with_args = script_name
        script = _truncate(script_with_args, script_max - 2)
        commit = (r.git_commit or "-")[:7]
        commit_cell = f"{commit:<9}" if show_commit else ""
        started = _format_timestamp(r.started_at_utc)
        # Pad from the visible status text so ANSI escapes (absent under
        # NO_COLOR / non-TTY) never shift the following columns.
        status = _status_marker(r.status) + " " * max(1, 12 - len(r.status))
        exit_code = str(r.exit_code) if r.exit_code is not None else "-"
        elapsed = _format_elapsed(r.elapsed)

        line = (
            f"{idx_str:<{idx_width}}"
            f"{run_id:<10}"
            f"{script:<{script_max}}"
            f"{commit_cell}"
            f"{started:<18}"
            f"{status}"
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

    # Discovery hint: point at the per-run detail when any listed run has config
    # notices (e.g. a deprecated setting), so they are not buried in the manifest.
    notice_runs = sum(1 for r in runs if getattr(r, "config_notices", None))
    if notice_runs:
        plural = "run has" if notice_runs == 1 else "runs have"
        lines.append(
            f"[WARN ] {notice_runs} {plural} config notices -- see `pubrun status <id>` "
            f"or `pubrun inspect`."
        )

    lines.append(
        "Tip: pass a # index (e.g. 'pubrun show 1' or 'pubrun diff 1 2') to any command."
    )

    return "\n".join(lines)


def render_verbose_list(runs: List[RunInfo], all_runs: Optional[List[RunInfo]] = None) -> str:
    """Render a detailed table with additional columns.

    Adds: PID, HOSTNAME, RSS (for running), CPU% (for running), EVENTS, SIGNALS
    """
    if not runs:
        if all_runs:
            return (
                f"0 of {len(all_runs)} runs matched the filter criteria. "
                "Run 'pubrun status' to list all runs."
            )
        return _NO_RUNS_GUIDANCE

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
    if run_info.ended_at_utc is not None:
        lines.append(f"  Ended:         {_format_timestamp(run_info.ended_at_utc)}")
    sem = getattr(run_info, "timing_semantics", None) or classify_timing_semantics(
        run_info.manifest.get("timing") if isinstance(run_info.manifest, dict) else None,
        status=run_info.status,
    )
    elapsed_label = sem.get("label", "Elapsed")
    elapsed_str = (
        "unknown"
        if run_info.elapsed is None or sem.get("is_incomplete")
        else _format_duration_detail(run_info.elapsed)
    )
    lines.append(f"  {elapsed_label}: {elapsed_str}")
    lines.append(
        "  Timing Scope:  tracked interval "
        "(start() to stop(), not full process lifetime if imported late)"
    )
    if run_info.startup_overhead_seconds is not None:
        lines.append(
            f"  Startup overhead: {_format_duration_detail(run_info.startup_overhead_seconds)}"
        )
    if run_info.finalization_overhead_seconds is not None:
        fin_str = _format_duration_detail(run_info.finalization_overhead_seconds)
        if run_info.hardware_wait_seconds is not None:
            fin_str += (
                f" (includes Hardware wait: {_format_duration_detail(run_info.hardware_wait_seconds)})"
            )
        lines.append(f"  Finalization overhead: {fin_str}")
    elif run_info.hardware_wait_seconds is not None:
        lines.append(
            f"  Hardware wait: {_format_duration_detail(run_info.hardware_wait_seconds)}"
        )
    if run_info.session_seconds is not None:
        lines.append(
            f"  Tracked session: {_format_duration_detail(run_info.session_seconds)}"
        )
    if run_info.background_hardware_seconds is not None:
        lines.append(
            f"  Background hardware (overlaps workload): "
            f"{_format_duration_detail(run_info.background_hardware_seconds)}"
        )
    lines.append(f"  Exit Code:     {run_info.exit_code if run_info.exit_code is not None else '-'}")
    lines.append("")

    # Config notices (e.g. deprecated core.profile) — surfaced, not buried in JSON.
    if run_info.config_notices:
        lines.append("  Notices:")
        for notice in run_info.config_notices:
            msg = notice.get("message", notice.get("code", "config notice"))
            lines.append(f"    [WARN ] {msg}")
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
            try:
                if not f.is_symlink() and f.is_file():
                    total += f.stat().st_size
            except OSError:
                continue
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


def _inspect_run_lock(run_dir: Path) -> Tuple[str, Optional[str]]:
    """Inspect a run directory's lock file and classify its deletion safety.

    Returns a tuple ``(state, remote_hostname)`` where ``state`` is one of:
    - ``"none"``: no lock file present
    - ``"symlink"``: lock file is a symlink (including broken symlink)
    - ``"unreadable"``: lock file cannot be parsed as a valid dict or lacks local PID/start time
    - ``"remote"``: readable lock owned by a non-empty hostname different from ``get_hostname()``
    - ``"active_local"``: local PID is still alive for this run
    - ``"stale_local"``: local PID is verified dead
    """
    lock_path = run_dir / Run.LOCK_FILENAME
    if lock_path.is_symlink():
        return "symlink", None
    if not lock_path.exists():
        return "none", None

    try:
        with open(lock_path, "r", encoding="utf-8") as f:
            disk_lock = json.load(f)
    except (OSError, json.JSONDecodeError):
        return "unreadable", None

    if not isinstance(disk_lock, dict):
        return "unreadable", None

    hostname = disk_lock.get("hostname")
    if isinstance(hostname, str) and hostname and hostname != get_hostname():
        return "remote", hostname

    pid = _as_int(disk_lock.get("pid"))
    started_at = _as_float(disk_lock.get("started_at_utc"))
    script = disk_lock.get("script")
    if not pid or pid <= 0 or started_at is None:
        return "unreadable", None

    if is_same_process(
        pid,
        started_at,
        expected_script=script if isinstance(script, str) else None,
    ):
        return "active_local", None
    return "stale_local", None


def safe_delete_run_dir(
    run_dir: Path,
    base_dir: Path,
    force_remote_locks: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Safely delete a run directory after symlink, confinement, and lock checks.

    Returns ``(True, None)`` when ``run_dir`` is deleted, or ``(False, reason)``
    when deletion is refused or ``shutil.rmtree`` raises ``OSError``.

    Safety guards enforced (and whether ``force_remote_locks`` can override):
    1. Symlink / non-directory rejection (NEVER bypassed).
    2. Parent-directory confinement ``run_dir.resolve().parent == base_dir.resolve()`` (NEVER bypassed).
    3. Symlinked, unreadable/corrupt, or active-local-PID lock refusal (NEVER bypassed).
    4. Remote-host lock refusal (bypassed ONLY when ``force_remote_locks=True``).
    """
    try:
        if run_dir.is_symlink() or not run_dir.is_dir():
            return False, "not a regular directory."
        if run_dir.resolve().parent != base_dir.resolve():
            return False, "path escapes output directory."
    except OSError as e:
        return False, str(e)

    lock_state, lock_host = _inspect_run_lock(run_dir)
    if lock_state == "symlink":
        return False, "lock file is a symlink."
    if lock_state == "unreadable":
        return False, "lock is unreadable or corrupt."
    if lock_state == "active_local":
        return False, "lock belongs to an active local process."
    if lock_state == "remote" and not force_remote_locks:
        host_note = f" ({lock_host})" if lock_host else ""
        return (
            False,
            f"lock belongs to a remote host{host_note}; re-run with --force-remote-locks to override.",
        )

    try:
        shutil.rmtree(run_dir)
    except OSError as e:
        return False, f"Failed to remove {run_dir.name}: {e}"
    return True, None


def _parse_selection_detailed(response: str, candidates: List[Any]) -> Tuple[List[Any], List[str]]:
    """Parse a selection string like '1-3,5,7-9' into ``(selected, ignored_tokens)``.

    Supports individual numbers, comma-separated numbers, and ranges.
    Each candidate is selected at most once (first-seen order is preserved).
    Invalid or out-of-range tokens are collected in ``ignored_tokens``.
    """
    selected: List[Any] = []
    ignored: List[str] = []
    seen: set = set()
    n = len(candidates)

    def _add(idx: int) -> None:
        if 0 <= idx < n and idx not in seen:
            seen.add(idx)
            selected.append(candidates[idx])

    for raw_part in response.split(","):
        part = raw_part.strip()
        if not part:
            continue
        compact = part.replace(" ", "")
        if "-" in compact and not compact.startswith("-"):
            # Range: "1-3"
            try:
                start_s, end_s = compact.split("-", 1)
                start_i = int(start_s) - 1
                end_i = int(end_s) - 1
            except ValueError:
                ignored.append(part)
                continue
            if start_i > end_i or end_i < 0 or start_i >= n:
                ignored.append(part)
                continue
            # Clamp before iterating so a huge range cannot hang.
            for idx in range(max(0, start_i), min(n - 1, end_i) + 1):
                _add(idx)
        else:
            # Single number
            try:
                idx = int(part) - 1
            except ValueError:
                ignored.append(part)
                continue
            if 0 <= idx < n:
                _add(idx)
            else:
                ignored.append(part)
    return selected, ignored


def _parse_selection(response: str, candidates: List[Any]) -> List[Any]:
    """Parse a selection string like '1-3,5,7-9' into a list of items.

    Supports individual numbers, comma-separated numbers, and ranges.
    Invalid indices are silently skipped, and each candidate is selected at
    most once (first-seen order is preserved).
    """
    selected, _ = _parse_selection_detailed(response, candidates)
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
    force_remote_locks: bool = False,
) -> int:
    """Interactively or automatically clean up old run directories.

    Args:
        output_dir: Override the configured output directory.
        older_than: Only consider runs older than this age (e.g. '7d', '24h').
        status_filter: Comma-separated status labels or list of statuses.
        yes: Skip confirmation prompt (non-interactive mode).
        dry_run: Show what would be deleted without deleting.
        filter_str: Regex or string query filter.
        limit: Limit number of runs to consider (0 deletes nothing; negative raises).
        exit_code: Filter by exit code.
        older_than_days: Backward-compatible float for age.
        not_filter_str: Exclude runs matching regex or substring.
        not_status_filter: Exclude runs with these comma-separated statuses.
        force_remote_locks: When True, allow deleting runs locked by a different host.
            Never bypasses symlink, directory-confinement, unreadable-lock, or
            active-local-PID checks.

    Returns:
        Number of run directories deleted.
    """
    # 0. Validate limit and status filters up front (fail closed).
    _validate_limit(limit)

    if not_status_filter:
        not_tokens = [s.strip().lower() for s in not_status_filter.split(",") if s.strip()]
        _validate_status_tokens(not_tokens, flag_name="--not-status")

    # 1. Resolve status filter (validate BEFORE stripping STATUS_RUNNING). An explicit
    # filter that normalizes to nothing deletes nothing: passing an empty filter
    # on to filter_runs would disable status filtering and match every run.
    if status_filter is not None:
        if isinstance(status_filter, str):
            raw_tokens: List[Any] = status_filter.split(",")
        else:
            try:
                raw_tokens = list(status_filter)
            except TypeError:
                raw_tokens = [status_filter]
        parsed_tokens: List[str] = []
        for token in raw_tokens:
            for piece in str(token).split(","):
                s = piece.strip().lower()
                if s and s not in parsed_tokens:
                    parsed_tokens.append(s)
        _validate_status_tokens(parsed_tokens, flag_name="--status")
        status_filter_list = [s for s in parsed_tokens if s != STATUS_RUNNING]
        if not status_filter_list:
            print("No deletable statuses selected (running runs are never deleted). Nothing to clean.")
            return 0
    else:
        status_filter_list = [
            STATUS_COMPLETED,
            STATUS_FAILED,
            STATUS_INTERRUPTED,
            STATUS_BROKEN_PIPE,
            STATUS_CRASHED,
            STATUS_GHOST,
        ]

    status_filter_str = ",".join(status_filter_list)

    # 2. Resolve older_than / older_than_days (invalid values raise ValueError)
    if older_than_days is not None:
        if isinstance(older_than_days, bool) or not isinstance(older_than_days, (int, float)):
            raise ValueError(
                f"Invalid older_than_days value {older_than_days!r}: expected a non-negative number of days."
            )
        if not math.isfinite(older_than_days):
            raise ValueError(f"Invalid older_than_days value {older_than_days!r}: age must be a finite number.")
        if older_than_days < 0:
            raise ValueError(f"Invalid older_than_days value {older_than_days!r}: age must not be negative.")
    if older_than is None and older_than_days is not None:
        older_than = f"{float(older_than_days)!r}d"

    all_runs = scan_runs(output_dir, keep_manifest=False)
    now = time.time()

    # 3. Apply standard filter_runs without slicing limit yet so excluded running
    # or remote-locked runs do not consume the user's requested limit.
    candidates = filter_runs(
        all_runs,
        filter_str=filter_str,
        status_filter=status_filter_str,
        limit=None,
        older_than=older_than,
        exit_code=exit_code,
        not_filter_str=not_filter_str,
        not_status_filter=not_status_filter,
    )
    # Defense in depth: a running run is never eligible, whatever the filters.
    candidates = [r for r in candidates if r.status != STATUS_RUNNING]

    # Exclude unverified remote-host locks up front unless explicitly overridden.
    if not force_remote_locks:
        eligible: List[RunInfo] = []
        skipped_remote = 0
        for r in candidates:
            lock_state, _ = _inspect_run_lock(r.run_dir)
            if lock_state == "remote":
                skipped_remote += 1
            else:
                eligible.append(r)
        candidates = eligible
        if skipped_remote:
            plural = "run" if skipped_remote == 1 else "runs"
            print(
                f"Note: skipped {skipped_remote} {plural} with an unverified remote-host lock "
                f"(re-run with --force-remote-locks if the remote job is confirmed dead)."
            )

    if limit is not None:
        if limit == 0:
            print("No runs match the cleanup criteria.")
            return 0
        candidates = candidates[:limit]

    if not candidates:
        print("No runs match the cleanup criteria.")
        return 0

    # Display candidates with terminal-width-adaptive columns
    term_width = _get_terminal_width()
    idx_width = max(4, len(str(len(candidates))) + 2)
    fixed_cols = idx_width + 10 + 13 + 6 + 14 + 10
    script_max = max(8, min(term_width - fixed_cols, int(term_width * 0.4)))

    hdr = (
        f"{'#':<{idx_width}}"
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
        exit_str = str(r.exit_code) if r.exit_code is not None else "-"
        age_seconds = (now - r.started_at_utc) if r.started_at_utc else None
        age = _format_age(age_seconds)
        size = _format_bytes(_dir_size(r.run_dir))
        print(
            f"{i:<{idx_width}}"
            f"{run_id:<10}"
            f"{script:<{script_max}}"
            f"{status:<13}"
            f"{exit_str:<6}"
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
        to_delete: List[RunInfo] = []
        prompt = "\nSelect runs to delete [numbers/ranges (e.g. 1-3,5), 'all', or Enter to cancel]: "
        for attempt in range(2):
            try:
                response = input(prompt).strip()
            except (KeyboardInterrupt, EOFError):
                print("\nCleanup cancelled.")
                return 0

            if response == "" or response.lower() in ("n", "no", "none"):
                print("Cleanup cancelled.")
                return 0
            if response.lower() == "all":
                to_delete = candidates
                break

            selected, ignored = _parse_selection_detailed(response, candidates)
            if ignored:
                print(f"Ignored invalid selection token(s): {', '.join(ignored)}")
            if selected:
                to_delete = selected
                break
            if attempt == 0:
                print(
                    f"No valid selections (enter 1-{len(candidates)}, a range like 1-3, 'all', or Enter to cancel). "
                    "Please try again."
                )
                prompt = "Select runs to delete: "
            else:
                print("No valid selections. Cleanup cancelled.")
                return 0

        # Show what will be deleted
        print(f"\nThe following {len(to_delete)} run(s) will be permanently deleted:\n")
        confirm_hdr = (
            f"{'#':<{idx_width}}"
            f"{'RUN ID':<10}"
            f"{'SCRIPT':<{script_max}}"
            f"{'STATUS':<13}"
            f"{'EXIT':<6}"
            f"{'AGE':<14}"
            f"{'SIZE':<10}"
        )
        print(confirm_hdr)
        print("-" * min(term_width, len(confirm_hdr)))
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
                f"{i:<{idx_width}}"
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

    # Resolve base output directory for symlink / parent-confinement checks before deletion.
    _clean_base_resolved = _resolve_output_dir(output_dir).resolve()

    # Delete
    deleted = 0
    for r in to_delete:
        ok, reason = safe_delete_run_dir(
            r.run_dir,
            _clean_base_resolved,
            force_remote_locks=force_remote_locks,
        )
        if ok:
            deleted += 1
        elif reason and reason.startswith("Failed to remove "):
            print(f"  {reason}", file=sys.stderr)
        else:
            print(f"  Skipped {r.run_dir.name}: {reason}", file=sys.stderr)

    print(f"\nDeleted {deleted} run(s).")
    return deleted
