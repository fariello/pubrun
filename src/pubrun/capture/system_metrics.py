"""System-wide dynamic metrics: available memory, load average, and (Linux) iowait.

These make post-hoc I/O / contention diagnosis possible (e.g. "was this run starved for
RAM or blocked on a busy node?"). All reads are cheap, stdlib-only, and non-blocking
(single small ``/proc`` reads or ``os.getloadavg``); nothing here touches user files or
the host script. Every function is exception-safe and returns ``None``/``capture_state``
on failure rather than raising.

IMPORTANT: ``iowait`` from ``/proc/stat`` is a SYSTEM-WIDE, per-CPU counter — NOT process-
or cgroup-scoped — and the Linux kernel documents it as unreliable/misleading on
multi-core and shared nodes. On a shared HPC compute node it reflects the whole node, not
this run. It is surfaced as ``system_iowait_pct`` and must be treated as indicative only.
"""
import os
import sys
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("pubrun")


def get_system_memory() -> Optional[Dict[str, int]]:
    """System memory in bytes: total / available / free / cached (Linux only).

    Returns None on non-Linux or on any read failure.
    """
    try:
        if not sys.platform.startswith("linux") or not os.path.exists("/proc/meminfo"):
            return None
        wanted = {"MemTotal": "total_bytes", "MemAvailable": "available_bytes",
                  "MemFree": "free_bytes", "Cached": "cached_bytes"}
        out: Dict[str, int] = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                key = line.split(":", 1)[0]
                if key in wanted:
                    parts = line.split()
                    if len(parts) >= 2:
                        out[wanted[key]] = int(parts[1]) * 1024  # kB -> bytes
        return out or None
    except Exception as e:
        logger.debug(f"pubrun failed reading /proc/meminfo: {e}")
        return None


def get_load_average() -> Optional[Dict[str, float]]:
    """1/5/15-minute load averages via os.getloadavg(). None if unavailable."""
    try:
        one, five, fifteen = os.getloadavg()
        return {"1min": one, "5min": five, "15min": fifteen}
    except (OSError, AttributeError) as e:  # not available on some platforms
        logger.debug(f"pubrun failed reading load average: {e}")
        return None


def read_proc_stat_cpu_times() -> Optional[Tuple[int, int]]:
    """Return (iowait_ticks, total_cpu_ticks) from /proc/stat's aggregate 'cpu' line.

    Used to compute a delta between two samples. Linux only; None otherwise/on failure.
    """
    try:
        if not sys.platform.startswith("linux") or not os.path.exists("/proc/stat"):
            return None
        with open("/proc/stat", "r", encoding="utf-8") as f:
            first = f.readline()
        if not first.startswith("cpu "):
            return None
        # cpu  user nice system idle iowait irq softirq steal guest guest_nice
        fields = [int(x) for x in first.split()[1:]]
        if len(fields) < 5:
            return None
        iowait = fields[4]
        total = sum(fields)
        return iowait, total
    except Exception as e:
        logger.debug(f"pubrun failed reading /proc/stat: {e}")
        return None


def iowait_pct_between(prev: Optional[Tuple[int, int]],
                       curr: Optional[Tuple[int, int]]) -> Optional[float]:
    """Percent of CPU time spent in iowait between two /proc/stat samples.

    NODE-WIDE, indicative only (see module docstring). None if either sample is missing
    or the total did not advance.
    """
    if not prev or not curr:
        return None
    iowait_delta = curr[0] - prev[0]
    total_delta = curr[1] - prev[1]
    if total_delta <= 0:
        return None
    return round(100.0 * iowait_delta / total_delta, 2)
