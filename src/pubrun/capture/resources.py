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


def _get_tree_cpu_jiffies_linux() -> int:
    """Sum CPU time (utime+stime, in clock ticks/jiffies) across the process tree on Linux.

    Reads fields 14 (utime) + 15 (stime) from /proc/<pid>/stat for self + all descendants.
    This is CUMULATIVE CPU TIME, not an instantaneous percentage — the watcher turns the
    delta between two samples into a percentage over the wall interval (the correct way to
    measure tree CPU; a sum of per-process instantaneous %% would be window-sensitive and
    can mislead). Returns total jiffies, or -1 if unreadable.
    """
    try:
        pid = os.getpid()
        total = 0
        to_visit = [pid]
        visited = set()
        while to_visit:
            p = to_visit.pop()
            if p in visited:
                continue
            visited.add(p)
            try:
                with open(f'/proc/{p}/stat', 'r') as f:
                    # The comm field (2nd) may contain spaces/parens; split on the last ')'.
                    data = f.read()
                    rparen = data.rfind(')')
                    fields = data[rparen + 2:].split() if rparen != -1 else data.split()
                    # After the '(comm)' the fields are 0-indexed: state=0, ... utime=11, stime=12
                    utime = int(fields[11])
                    stime = int(fields[12])
                    total += utime + stime
            except (OSError, IndexError, ValueError):
                continue
            try:
                with open(f'/proc/{p}/task/{p}/children', 'r') as f:
                    to_visit.extend(int(c) for c in f.read().split() if c)
            except (OSError, ValueError):
                pass
        return total
    except Exception as e:
        logger.debug(f"pubrun failed Linux tree CPU poll: {e}")
        return -1


class ResourceWatcher(threading.Thread):
    def __init__(self, run_tracker: Any, interval_seconds: float, max_failures: int = 3,
                 scope: str = "process", system_metrics: bool = True):
        super().__init__(daemon=True)
        self.run_tracker = run_tracker
        self.interval = float(interval_seconds)
        self.max_failures = max_failures
        self._scope = scope
        self._system_metrics = system_metrics
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self.peak_rss_bytes = 0
        self.end_rss_bytes = 0
        self.peak_cpu_percent = 0.0
        # Tree-level metrics (only populated when scope="tree")
        self.peak_tree_rss_bytes = 0
        self.end_tree_rss_bytes = 0
        self.peak_tree_cpu_percent = 0.0
        self._last_times = None
        self._last_clock = None
        # Tree CPU is computed from the delta of summed CPU-TIME (jiffies) over the wall
        # interval — NOT a sum of per-process instantaneous cpu_percent.
        self._last_tree_jiffies = None
        self._last_tree_clock = None
        self._clk_tck = 0
        try:
            self._clk_tck = os.sysconf("SC_CLK_TCK")
        except (ValueError, OSError, AttributeError):
            self._clk_tck = 0
        self._sys_plat = sys.platform
        self._consecutive_failures = 0

        # System-wide dynamic metrics (available RAM, load average, node iowait).
        # We track the "worst" observed point (min available RAM, max load) plus the
        # start and last samples, mirroring the peak/end shape used for RSS/CPU.
        self._sysmem_start = None
        self._sysmem_last = None
        self._sysmem_min_available = None  # tuple carrying the sample at min available
        self._load_start = None
        self._load_last = None
        self._load_max_1min = None
        self._iowait_prev_raw = None       # last /proc/stat (iowait, total) sample
        self._iowait_pct_last = None
        self._iowait_pct_max = None
        self._proc_io_start = None          # /proc/self/io cumulative counters at start
        self._proc_io_last = None
        if self._system_metrics:
            self._capture_system_start()


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

    def _poll_tree_cpu(self) -> float:
        """Tree CPU% over the last interval, from the delta of summed CPU-TIME across the
        tree (correct method; see _get_tree_cpu_jiffies_linux). May exceed 100% on
        multi-core (it is "% of one core"); we do NOT clamp it. Returns 0.0 when unavailable
        (non-Linux, first sample, or unreadable) — negative deltas (a child exited between
        samples, dropping cumulative time) are floored to 0.

        Linux only for now: /proc CPU-time accounting is not available cross-platform without
        a per-process time-delta walk. On other platforms tree CPU stays unmeasured.
        """
        if not self._sys_plat.startswith("linux") or not self._clk_tck:
            return 0.0
        try:
            jiffies = _get_tree_cpu_jiffies_linux()
            clock = time.perf_counter()
            pct = 0.0
            if jiffies >= 0 and self._last_tree_jiffies is not None and self._last_tree_clock is not None:
                jiffy_delta = jiffies - self._last_tree_jiffies
                wall_delta = clock - self._last_tree_clock
                if wall_delta > 0 and jiffy_delta > 0:
                    cpu_seconds = jiffy_delta / self._clk_tck
                    pct = (cpu_seconds / wall_delta) * 100.0
            if jiffies >= 0:
                self._last_tree_jiffies = jiffies
                self._last_tree_clock = clock
            return float(round(max(0.0, pct), 1))
        except Exception as e:
            logger.debug(f"pubrun failed tree CPU poll: {e}")
            return 0.0

    def _capture_system_start(self) -> None:
        """Snapshot system memory / load / iowait baseline at watcher construction."""
        try:
            from pubrun.capture import system_metrics as _sm
            self._sysmem_start = _sm.get_system_memory()
            self._load_start = _sm.get_load_average()
            self._iowait_prev_raw = _sm.read_proc_stat_cpu_times()
            self._proc_io_start = _sm.get_proc_io()
        except Exception as e:  # never let baseline capture abort the run
            logger.debug(f"pubrun failed system-metrics baseline: {e}")

    def _sample_system_metrics(self) -> None:
        """Sample system memory / load / node iowait in the watcher loop (cheap /proc reads).

        Tracks worst-case (min available RAM, max load) plus the last sample. Fully
        exception-safe: a failure here must never disturb the RSS/CPU sampling or the run.
        """
        if not self._system_metrics:
            return
        try:
            from pubrun.capture import system_metrics as _sm
            mem = _sm.get_system_memory()
            load = _sm.get_load_average()
            curr_raw = _sm.read_proc_stat_cpu_times()
            iowait_pct = _sm.iowait_pct_between(self._iowait_prev_raw, curr_raw)
            proc_io = _sm.get_proc_io()

            with self._lock:
                if proc_io is not None:
                    if self._proc_io_start is None:
                        self._proc_io_start = proc_io
                    self._proc_io_last = proc_io
                if mem is not None:
                    if self._sysmem_start is None:
                        self._sysmem_start = mem
                    self._sysmem_last = mem
                    avail = mem.get("available_bytes")
                    if avail is not None:
                        prev = self._sysmem_min_available
                        if prev is None or avail < prev.get("available_bytes", avail) + 1:
                            if prev is None or avail < prev.get("available_bytes", float("inf")):
                                self._sysmem_min_available = mem
                if load is not None:
                    if self._load_start is None:
                        self._load_start = load
                    self._load_last = load
                    one = load.get("1min")
                    if one is not None and (self._load_max_1min is None or one > self._load_max_1min):
                        self._load_max_1min = one
                if curr_raw is not None:
                    self._iowait_prev_raw = curr_raw
                if iowait_pct is not None:
                    self._iowait_pct_last = iowait_pct
                    if self._iowait_pct_max is None or iowait_pct > self._iowait_pct_max:
                        self._iowait_pct_max = iowait_pct
        except Exception as e:
            logger.debug(f"pubrun failed system-metrics sample: {e}")

    def _update_metrics(self) -> None:
        rss = self._poll_rss()
        cpu_pct = self._poll_cpu()
        tree_rss = self._poll_tree_rss() if self._scope == "tree" else 0
        tree_cpu = self._poll_tree_cpu() if self._scope == "tree" else 0.0
        self._sample_system_metrics()

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

            if tree_cpu > self.peak_tree_cpu_percent:
                self.peak_tree_cpu_percent = tree_cpu

        payload = {"rss_bytes": rss_bytes, "cpu_percent": cpu_pct}
        if tree_rss > 0:
            payload["tree_rss_bytes"] = tree_rss
        if self._scope == "tree" and tree_cpu > 0:
            payload["tree_cpu_percent"] = tree_cpu
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
            peak_tree_cpu = self.peak_tree_cpu_percent
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
            # Tree CPU% ("of one core"; may exceed 100% on multi-core). Linux-only; None
            # where unmeasured. Computed from summed CPU-time deltas, not instantaneous %.
            result["peak_tree_cpu_percent"] = peak_tree_cpu if peak_tree_cpu > 0 else None

        if self._system_metrics:
            with self._lock:
                sysmem_start = self._sysmem_start
                sysmem_last = self._sysmem_last
                sysmem_min = self._sysmem_min_available
                load_start = self._load_start
                load_last = self._load_last
                load_max = self._load_max_1min
                iowait_last = self._iowait_pct_last
                iowait_max = self._iowait_pct_max
                proc_io_start = self._proc_io_start
                proc_io_last = self._proc_io_last
            # Only emit sections we actually captured (Linux for memory/iowait; load is
            # broadly available). Absent -> omit rather than emit misleading nulls.
            if sysmem_start or sysmem_last:
                result["system_memory"] = {
                    "start": sysmem_start,
                    "last": sysmem_last,
                    "min_available": sysmem_min,
                }
            if load_start or load_last:
                result["load_average"] = {
                    "start": load_start,
                    "last": load_last,
                    "max_1min": load_max,
                }
            if iowait_last is not None or iowait_max is not None:
                # NODE-WIDE, indicative only (see system_metrics module docstring).
                result["system_iowait_pct"] = {"last": iowait_last, "max": iowait_max}
            if proc_io_start or proc_io_last:
                # Cumulative per-PROCESS I/O byte counters (this run's process). The
                # start->last delta is the run's I/O volume. Linux /proc/self/io.
                io_obj = {"start": proc_io_start, "last": proc_io_last}
                if proc_io_start and proc_io_last:
                    io_obj["delta"] = {
                        k: proc_io_last.get(k, 0) - proc_io_start.get(k, 0)
                        for k in ("rchar", "wchar", "read_bytes", "write_bytes")
                        if k in proc_io_last and k in proc_io_start
                    }
                result["io_counters"] = io_obj
        return result
