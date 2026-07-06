import os
import sys
import time
import threading
import logging
from typing import Any, Dict

logger = logging.getLogger("pubrun")

# Removed ctypes in favor of reliable OS wmic command for Python compatibility across Win10/11

# Per-poll timeout (seconds) for the macOS/Windows sampling subprocesses
# (ps/wmic). Bounds a hung tool so it cannot orphan the sampling thread.
# Overridable via [capture.resources].poll_timeout. (IPD 20260705 EC-11.)
_DEFAULT_POLL_TIMEOUT = 3.0
_poll_timeout = _DEFAULT_POLL_TIMEOUT


def set_poll_timeout(seconds: float) -> None:
    """Set the module-level subprocess poll timeout (seconds)."""
    global _poll_timeout
    try:
        _poll_timeout = float(seconds)
    except (TypeError, ValueError):
        _poll_timeout = _DEFAULT_POLL_TIMEOUT


def _get_rss_windows() -> int:
    try:
        import subprocess
        from pubrun.capture.subprocesses import disable_spy
        with disable_spy():
            out = subprocess.check_output(
                ["wmic", "process", "where", f"processid={os.getpid()}", "get", "WorkingSetSize"],
                text=True, stderr=subprocess.DEVNULL, timeout=_poll_timeout
            )
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        if len(lines) >= 2 and lines[1].isdigit():
            return int(lines[1])
    except Exception as e:
        logger.debug(f"pubrun failed Windows RSS poll: {e}")
        return -1  # unreadable (distinct from a legitimate 0); see EC-12
    return -1


def _get_rss_linux() -> int:
    try:
        with open('/proc/self/statm', 'r', encoding="utf-8") as f:
            # Second column in statm is Resident Set Size in pages
            pages = int(f.read().split()[1])
            # SC_PAGE_SIZE maps to physical RAM bytes
            return pages * os.sysconf("SC_PAGE_SIZE")
    except Exception as e:
        logger.debug(f"pubrun failed Linux RSS poll: {e}")
        return -1  # unreadable (distinct from a legitimate 0); see EC-12


def _get_rss_darwin() -> int:
    """Get current RSS on macOS via ps.

    Note: resource.getrusage(RUSAGE_SELF).ru_maxrss returns the PEAK RSS
    (high-water mark), not the current RSS. We use ps -o rss= for the
    actual current resident size. See BUG-01.
    """
    try:
        import subprocess
        from pubrun.capture.subprocesses import disable_spy
        with disable_spy():
            out = subprocess.check_output(
                ['ps', '-o', 'rss=', '-p', str(os.getpid())],
                text=True, stderr=subprocess.DEVNULL, timeout=_poll_timeout
            )
        return int(out.strip()) * 1024  # ps output is in KB
    except Exception as e:
        logger.debug(f"pubrun failed Mac RSS poll: {e}")
        return -1  # unreadable (distinct from a legitimate 0); see EC-12


def _get_tree_rss_linux() -> int:
    """Sum RSS across the process tree on Linux via /proc."""
    try:
        pid = os.getpid()
        total_rss = 0
        # Collect self + all descendants
        pids_to_check = [pid]
        visited = set()
        while pids_to_check:
            p = pids_to_check.pop()
            if p in visited:
                continue
            visited.add(p)
            # Read this process's RSS
            try:
                with open(f'/proc/{p}/statm', 'r') as f:
                    pages = int(f.read().split()[1])
                    total_rss += pages * os.sysconf("SC_PAGE_SIZE")
            except (OSError, IndexError, ValueError):
                continue
            # Find children of this process
            try:
                children_path = f'/proc/{p}/task/{p}/children'
                with open(children_path, 'r') as f:
                    child_pids = [int(c) for c in f.read().split() if c]
                    pids_to_check.extend(child_pids)
            except (OSError, ValueError):
                pass
        return total_rss
    except Exception as e:
        logger.debug(f"pubrun failed Linux tree RSS poll: {e}")
        return 0


def _get_tree_rss_darwin() -> int:
    """Sum RSS across the entire process tree on macOS.

    Uses a single `ps -eo pid,ppid,rss` call to get all processes, then
    walks the tree in Python to find all descendants. Always includes self
    RSS even if there are no children. (BUG2-01 + BUG2-06)
    """
    try:
        import subprocess
        from pubrun.capture.subprocesses import disable_spy
        my_pid = os.getpid()

        # Single subprocess call: get pid, ppid, rss for ALL processes
        with disable_spy():
            out = subprocess.check_output(
                ['ps', '-eo', 'pid,ppid,rss'],
                text=True, stderr=subprocess.DEVNULL, timeout=_poll_timeout
            )

        # Parse into {pid: (ppid, rss_kb)} map
        children_of: dict = {}  # ppid -> [pid, ...]
        rss_of: dict = {}       # pid -> rss_bytes
        for line in out.strip().split('\n')[1:]:  # skip header
            parts = line.split()
            if len(parts) < 3:
                continue
            try:
                pid = int(parts[0])
                ppid = int(parts[1])
                rss_kb = int(parts[2])
                rss_of[pid] = rss_kb * 1024
                children_of.setdefault(ppid, []).append(pid)
            except (ValueError, IndexError):
                continue

        # Walk the tree from our PID to collect all descendants
        total_rss = rss_of.get(my_pid, 0)
        to_visit = list(children_of.get(my_pid, []))
        visited = {my_pid}
        while to_visit:
            p = to_visit.pop()
            if p in visited:
                continue
            visited.add(p)
            total_rss += rss_of.get(p, 0)
            to_visit.extend(children_of.get(p, []))

        return total_rss
    except Exception as e:
        logger.debug(f"pubrun failed Mac tree RSS poll: {e}")
        # Graceful fallback: return at least self RSS (clamp the -1 unreadable
        # sentinel to 0, since the tree consumer only checks > 0).
        return max(0, _get_rss_darwin())


class ResourceWatcher(threading.Thread):
    def __init__(self, run_tracker: Any, interval_seconds: float, max_failures: int = 3,
                 scope: str = "process"):
        super().__init__(daemon=True)
        self.run_tracker = run_tracker
        self.interval = float(interval_seconds)
        self.max_failures = max_failures
        self._scope = scope
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self.peak_rss_bytes = 0
        self.end_rss_bytes = 0
        self.peak_cpu_percent = 0.0
        # Tree-level metrics (only populated when scope="tree")
        self.peak_tree_rss_bytes = 0
        self.end_tree_rss_bytes = 0
        self._last_times = None
        self._last_clock = None
        self._sys_plat = sys.platform
        self._consecutive_failures = 0


    def _poll_rss(self) -> int:
        """Return current RSS in bytes, or -1 if the reading was unreadable
        (error/timeout/unsupported platform). A return of 0 means a genuine
        zero, which must NOT count as a failure. (IPD 20260705 EC-12.)"""
        if self._sys_plat == "win32":
            return _get_rss_windows()
        elif self._sys_plat.startswith("linux"):
            return _get_rss_linux()
        elif self._sys_plat == "darwin":
            return _get_rss_darwin()
        return -1

    def run(self) -> None:
        """Background polling loop. Samples immediately, then at each interval."""
        # Check instantly so we don't skip short runs
        self._update_metrics()

        while not self._stop_event.wait(timeout=self.interval):
            self._update_metrics()

    def _poll_cpu(self) -> float:
        """CPU% for the MAIN process over the last interval.

        Uses only the process's own user+system time — NOT children_user/
        children_system. Reaped children's cumulative CPU lands in the
        children_* counters all at once when a batch of subprocesses exits, which
        over a short interval produced absurd spikes (e.g. 5000%+) for a
        mostly-idle orchestrator. Child CPU belongs to the "tree" scope metric,
        not the main-process CPU%. Result is clamped to a sane ceiling
        (100% * logical cores) as defense-in-depth against clock/counter jitter.
        """
        try:
            current_times = os.times()
            current_clock = time.perf_counter()
            cpu_pct = 0.0

            if self._last_times is not None and self._last_clock is not None:
                user_delta = current_times.user - self._last_times.user
                sys_delta = current_times.system - self._last_times.system
                wall_delta = current_clock - self._last_clock

                if wall_delta > 0:
                    cpu_pct = ((user_delta + sys_delta) / wall_delta) * 100.0

            self._last_times = current_times
            self._last_clock = current_clock

            # Clamp: negative (counter wrap) -> 0; cap at 100% per logical core.
            if cpu_pct < 0:
                cpu_pct = 0.0
            cores = os.cpu_count() or 1
            ceiling = 100.0 * cores
            if cpu_pct > ceiling:
                cpu_pct = ceiling
            return float(round(cpu_pct, 1))
        except Exception as e:
            logger.debug(f"pubrun failed CPU poll: {e}")
            return 0.0

    def _poll_tree_rss(self) -> int:
        """Poll the total RSS across the process tree."""
        if self._sys_plat.startswith("linux"):
            return _get_tree_rss_linux()
        elif self._sys_plat == "darwin":
            return _get_tree_rss_darwin()
        # Windows tree not yet implemented; return 0 (graceful fallback).
        return 0

    def _update_metrics(self) -> None:
        rss = self._poll_rss()
        cpu_pct = self._poll_cpu()
        tree_rss = self._poll_tree_rss() if self._scope == "tree" else 0

        # rss == -1 means the poll was UNREADABLE (error/timeout); rss >= 0 is a
        # successful reading (0 being a legitimate value). Only unreadable polls
        # count toward the consecutive-failure self-abort, so a transient blip
        # cannot permanently disable telemetry. (IPD 20260705 EC-12.)
        readable = rss >= 0
        rss_bytes = rss if readable else 0

        updated = False

        with self._lock:
            if readable:
                self._consecutive_failures = 0
                if rss_bytes > self.peak_rss_bytes:
                    self.peak_rss_bytes = rss_bytes
                updated = True
            else:
                self._consecutive_failures += 1
                if self._consecutive_failures >= self.max_failures:
                    self._stop_event.set() # Soft-abort the daemon purely for safety; OS hook is broken.

            if cpu_pct > self.peak_cpu_percent:
                self.peak_cpu_percent = cpu_pct

            if tree_rss > 0 and tree_rss > self.peak_tree_rss_bytes:
                self.peak_tree_rss_bytes = tree_rss

        payload = {"rss_bytes": rss_bytes, "cpu_percent": cpu_pct}
        if tree_rss > 0:
            payload["tree_rss_bytes"] = tree_rss
        if updated or cpu_pct > 0:
            if getattr(self.run_tracker, "event_stream", None):
                self.run_tracker.event_stream.emit("resource_sample", payload=payload)

    def stop(self) -> None:
        """Signal the polling thread to stop, wait for it, and take one final measurement."""
        self._stop_event.set()
        # Wait for the daemon thread to finish its current cycle.
        # Cap at 5s to prevent long hangs if OS polling is stuck.
        self.join(timeout=min(self.interval + 1, 5))
        # Only take final measurement if the thread actually stopped (P2-E7).
        # If it's still alive (stuck in I/O), skip to avoid concurrent field access.
        if not self.is_alive():
            self._update_metrics()
            end_rss = self._poll_rss()
            end_tree_rss = self._poll_tree_rss() if self._scope == "tree" else 0
            with self._lock:
                self.end_rss_bytes = end_rss
                if self.end_rss_bytes > self.peak_rss_bytes:
                    self.peak_rss_bytes = self.end_rss_bytes
                if end_tree_rss > 0:
                    self.end_tree_rss_bytes = end_tree_rss
                    if end_tree_rss > self.peak_tree_rss_bytes:
                        self.peak_tree_rss_bytes = end_tree_rss

    def to_manifest_dict(self) -> Dict[str, Any]:
        """Build the ``resources`` manifest section dict."""
        with self._lock:
            peak_rss = self.peak_rss_bytes
            end_rss = self.end_rss_bytes
            peak_cpu = self.peak_cpu_percent
            peak_tree = self.peak_tree_rss_bytes
            end_tree = self.end_tree_rss_bytes
        result: Dict[str, Any] = {
            "scope": self._scope,
            "peak_rss_bytes": peak_rss if peak_rss > 0 else None,
            "end_rss_bytes": end_rss if end_rss > 0 else None,
            "peak_cpu_percent": peak_cpu if peak_cpu > 0 else None,
            "capture_state": {"status": "complete"}
        }
        if self._scope == "tree":
            result["peak_tree_rss_bytes"] = peak_tree if peak_tree > 0 else None
            result["end_tree_rss_bytes"] = end_tree if end_tree > 0 else None
        return result
