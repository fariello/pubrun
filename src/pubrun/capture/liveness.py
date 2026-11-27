"""
Cross-platform process liveness checking, RSS, and CPU queries.

All functions use only the Python standard library.  Platform-specific
branches handle Linux (/proc), macOS (ps), and Windows (ctypes/wmic).
"""
import os
import platform
import subprocess
import sys
import time
from typing import Any, Optional, Tuple


_PLATFORM = sys.platform  # 'linux', 'darwin', 'win32'


def _sysconf(name: str) -> int:
    """Return ``os.sysconf(name)``; raises ``AttributeError`` where ``os.sysconf`` is absent (Windows)."""
    return int(getattr(os, "sysconf")(name))


# --------------------------------------------------------------------------
# PID liveness
# --------------------------------------------------------------------------

def is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID exists.

    Returns True if the process is alive, False otherwise.
    Does not guarantee the process is the *same* one (PID recycling).
    """
    # Reject impossible PIDs before touching os.kill. On POSIX, os.kill(0, 0)
    # signals the caller's process GROUP and os.kill(-1, 0) signals every
    # process the user can reach -- both return without raising, which would be
    # a false "alive" verdict. None/non-positive PIDs come from malformed or
    # foreign lock/manifest files. (IPD 20260705 EC-05.)
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    if _PLATFORM == "win32":
        return _is_pid_alive_windows(pid)
    else:
        # Unix (Linux + macOS): signal 0 checks existence without killing.
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # Process exists but we don't own it -- still alive.
            return True
        except (OSError, OverflowError):
            # OverflowError: an absurdly large PID from a corrupt dir name.
            return False


def get_process_start_time(pid: int) -> Optional[float]:
    """Return the process creation time as a POSIX epoch float, or None.

    Used to detect PID recycling: if the recorded start time doesn't match
    the actual process creation time, the PID was reused.
    """
    if _PLATFORM == "linux":
        return _get_start_time_linux(pid)
    elif _PLATFORM == "darwin":
        return _get_start_time_macos(pid)
    elif _PLATFORM == "win32":
        return _get_start_time_windows(pid)
    return None


# Generic interpreter/flag tokens that are NOT distinctive enough to confirm a
# same-process match on their own -- e.g. a recycled PID also running "python"
# would spuriously match. When expected_script is one of these (or too short),
# the script check is inconclusive and we fall through to start-time timing.
# (IPD 20260705 EC-06.)
_GENERIC_SCRIPT_TOKENS = frozenset(
    {"python", "python2", "python3", "python3.8", "python3.9", "python3.10",
     "python3.11", "python3.12", "python3.13", "python3.14", "-c", "-m",
     "__main__", "sh", "bash", "env", "interactive"}
)


def _script_is_generic(expected_script: str) -> bool:
    """True if expected_script is too generic to confirm a match alone."""
    from pathlib import Path
    base = Path(expected_script).name
    return len(base) < 3 or base in _GENERIC_SCRIPT_TOKENS


_SCRIPT_SUFFIXES = (".py", ".pyw")
# Bound on how many whitespace-split tokens are re-joined when looking for a
# script path that contains spaces (ps/wmic command lines are split on spaces).
_MAX_JOINED_TOKENS = 8


def _sanitize_script_name(name: str) -> str:
    """Apply the same sanitization the tracker uses for the recorded script name."""
    import re
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "_", name)


def _script_name_forms(tok: str) -> set:
    """Names under which a command-line token may have been recorded.

    The lock file records a sanitized stem (``my train.py`` -> ``my_train``) and
    a manifest records the basename (``train.py``), so both, raw and sanitized,
    count as exact. Only a ``.py``/``.pyw`` suffix is stripped, so
    ``train.py.bak`` never yields ``train.py``.
    """
    from pathlib import PurePath
    name = PurePath(tok).name
    forms = {name, _sanitize_script_name(name)}
    for suffix in _SCRIPT_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            stem = name[: -len(suffix)]
            forms.add(stem)
            forms.add(_sanitize_script_name(stem))
    return forms


def _candidate_tokens(tokens):
    """Yield each token, then runs of adjacent tokens re-joined with a space."""
    for tok in tokens:
        yield tok
    n = len(tokens)
    for i in range(n):
        for j in range(i + 2, min(n, i + _MAX_JOINED_TOKENS) + 1):
            yield " ".join(tokens[i:j])


def _match_script_in_tokens(expected_script: str, tokens) -> Optional[bool]:
    """Given the command-line tokens of a process, decide whether it is running
    ``expected_script``.

    Returns True on an exact basename match (confirmed same process), False when
    the script name appears nowhere at all (confirmed mismatch / recycled PID),
    and None when the only evidence is a substring (ambiguous) so the caller
    falls through to start-time timing. (IPD 20260705 EC-06.)
    """
    tokens = [t for t in tokens if t]
    if not tokens:
        return None
    exact = False
    substring = False
    for tok in _candidate_tokens(tokens):
        if tok == expected_script or expected_script in _script_name_forms(tok):
            exact = True
            break
        if expected_script in tok or expected_script in _sanitize_script_name(tok):
            substring = True
    if exact:
        return True
    if substring:
        # Substring-only evidence is not trustworthy (e.g. train.py vs
        # train_backup.py); let timing decide.
        return None
    return False


def _check_command_linux(pid: int, expected_script: str) -> Optional[bool]:
    if _script_is_generic(expected_script):
        return None
    try:
        with open(f"/proc/{pid}/cmdline", "r", encoding="utf-8", errors="replace") as f:
            cmdline = f.read()
        if not cmdline:
            return None
        parts = cmdline.split("\x00")
        return _match_script_in_tokens(expected_script, parts)
    except (OSError, ValueError):
        return None


def _check_command_macos(pid: int, expected_script: str) -> Optional[bool]:
    if _script_is_generic(expected_script):
        return None
    try:
        result = subprocess.run(
            ["ps", "-o", "command=", "-p", str(pid)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            cmdline = result.stdout.strip()
            if cmdline:
                return _match_script_in_tokens(expected_script, cmdline.split())
        return None
    except Exception:
        return None


def _check_command_windows(pid: int, expected_script: str) -> Optional[bool]:
    if _script_is_generic(expected_script):
        return None
    try:
        result = subprocess.run(
            ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
            if len(lines) >= 2:
                cmdline = lines[1]
                return _match_script_in_tokens(expected_script, cmdline.split())
        return None
    except Exception:
        return None


def is_same_process(
    pid: int,
    expected_start_utc: float,
    expected_script: Optional[str] = None,
    tolerance: float = 86400.0,
) -> bool:
    """Check if a PID is alive AND matches the expected process/script/start time.

    Args:
        pid: Process ID to check.
        expected_start_utc: POSIX timestamp when the run originally started.
        expected_script: Basename of the script that was executed. If provided,
            we attempt to verify that the target process is indeed running this
            script before falling back to timing validation.
        tolerance: Seconds of allowed difference between recorded start and
            actual process creation time. Default is 24 hours (86400s) to be
            resilient against virtualization / VM suspend-resume time drifts.
    """
    if not is_pid_alive(pid):
        return False

    if expected_script:
        match_status = None
        if _PLATFORM == "linux":
            match_status = _check_command_linux(pid, expected_script)
        elif _PLATFORM == "darwin":
            match_status = _check_command_macos(pid, expected_script)
        elif _PLATFORM == "win32":
            match_status = _check_command_windows(pid, expected_script)

        if match_status is True:
            # Confirmed exact-basename match -> same process.
            return True
        elif match_status is False:
            # Script confirmed absent from the command line -> recycled PID.
            return False
        # match_status is None: inconclusive (substring-only or generic token);
        # fall through to start-time timing.

    actual_start = get_process_start_time(pid)
    if actual_start is None:
        # Start time is genuinely unreadable (e.g. ps/wmic slow, lstart didn't
        # parse, or permission denied on /proc/<pid>/stat). We have no POSITIVE
        # evidence of a mismatch, so stay conservative and assume the run is
        # still alive rather than falsely reporting it crashed. Flipping this to
        # "crashed" is the documented macOS PID-liveness flake source.
        # (IPD 20260705 EC-07.)
        return True

    # Only a readable start time that DIFFERS beyond tolerance is positive
    # mismatch evidence.
    try:
        return abs(actual_start - expected_start_utc) < tolerance
    except (TypeError, ValueError):
        # expected_start_utc was non-numeric (foreign/edited lock) -> can't
        # prove a mismatch; stay conservative.
        return True


# --------------------------------------------------------------------------
# RSS memory (bytes)
# --------------------------------------------------------------------------

def get_rss_bytes(pid: int) -> Optional[int]:
    """Return current RSS (Resident Set Size) in bytes for the given PID."""
    if _PLATFORM == "linux":
        return _get_rss_linux(pid)
    elif _PLATFORM == "darwin":
        return _get_rss_macos(pid)
    elif _PLATFORM == "win32":
        return _get_rss_windows(pid)
    return None


# --------------------------------------------------------------------------
# CPU percent (snapshot-based, not interval)
# --------------------------------------------------------------------------

def get_cpu_percent(pid: int) -> Optional[float]:
    """Return a CPU usage estimate for the given PID.

    On Linux, computes percent from /proc/<pid>/stat cumulative times
    against system uptime.  On macOS, reads from ``ps``.  On Windows,
    uses wmic.

    Note: This is a point-in-time estimate, not a sampled interval.
    """
    if _PLATFORM == "linux":
        return _get_cpu_linux(pid)
    elif _PLATFORM == "darwin":
        return _get_cpu_macos(pid)
    elif _PLATFORM == "win32":
        return _get_cpu_windows(pid)
    return None


# ==========================================================================
# Linux implementations (/proc filesystem)
# ==========================================================================

def _get_start_time_linux(pid: int) -> Optional[float]:
    """Read process start time from /proc/<pid>/stat."""
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            stat_line = f.read()
        # Fields are space-separated, but comm (field 2) can contain spaces
        # and is enclosed in parentheses.
        right_paren = stat_line.rfind(")")
        fields = stat_line[right_paren + 2:].split()
        # Field index 19 (0-based after comm) = starttime in clock ticks
        starttime_ticks = int(fields[19])
        clock_ticks = _sysconf("SC_CLK_TCK")

        # Get system boot time
        with open("/proc/stat", "r") as f:
            for line in f:
                if line.startswith("btime "):
                    boot_time = int(line.split()[1])
                    break
            else:
                return None

        return boot_time + (starttime_ticks / clock_ticks)
    except (OSError, IndexError, ValueError):
        return None


def _get_rss_linux(pid: int) -> Optional[int]:
    """Read RSS from /proc/<pid>/status (VmRSS line, in kB)."""
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    # Format: "VmRSS:    12345 kB"
                    parts = line.split()
                    return int(parts[1]) * 1024  # kB -> bytes
    except (OSError, IndexError, ValueError):
        pass
    return None


def _get_cpu_linux(pid: int) -> Optional[float]:
    """Estimate CPU% from /proc/<pid>/stat cumulative times vs elapsed."""
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            stat_line = f.read()
        right_paren = stat_line.rfind(")")
        fields = stat_line[right_paren + 2:].split()

        # utime (field 11) + stime (field 12), in clock ticks
        utime = int(fields[11])
        stime = int(fields[12])
        starttime_ticks = int(fields[19])

        clock_ticks = _sysconf("SC_CLK_TCK")
        total_cpu_seconds = (utime + stime) / clock_ticks

        # Elapsed time since process start
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.read().split()[0])

        process_elapsed = uptime_seconds - (starttime_ticks / clock_ticks)
        if process_elapsed <= 0:
            return 0.0

        # Percent of one core
        return (total_cpu_seconds / process_elapsed) * 100.0
    except (OSError, IndexError, ValueError, ZeroDivisionError):
        return None


# ==========================================================================
# macOS implementations (ps command)
# ==========================================================================

def _get_start_time_macos(pid: int) -> Optional[float]:
    """Get process start time via ps -o lstart=."""
    try:
        env = dict(os.environ)
        env["LC_ALL"] = "C"
        env["LC_TIME"] = "C"
        result = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            capture_output=True, text=True, timeout=5, env=env
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        # With LC_ALL=C the output is "Thu May 31 14:02:17 2026".
        return _parse_c_locale_lstart(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, OSError):
        return None


_C_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_c_locale_lstart(text: str) -> Optional[float]:
    """Parse a C-locale ``ps -o lstart=`` string as local time, without strptime.

    ``datetime.strptime`` matches ``%a``/``%b`` against the host Python process's
    LC_TIME, so it rejects English names when Python runs under another locale.
    """
    parts = text.split()
    if len(parts) != 5:
        return None
    _weekday, mon, day, hms, year = parts
    month = _C_MONTHS.get(mon.lower())
    if month is None:
        return None
    try:
        hour, minute, second = (int(x) for x in hms.split(":"))
        from datetime import datetime
        return datetime(int(year), month, int(day), hour, minute, second).timestamp()
    except (ValueError, OverflowError):
        return None


def _get_rss_macos(pid: int) -> Optional[int]:
    """Get RSS via ps -o rss= (output in kilobytes)."""
    try:
        result = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        return int(result.stdout.strip()) * 1024  # kB -> bytes
    except (subprocess.TimeoutExpired, ValueError, OSError):
        return None


def _get_cpu_macos(pid: int) -> Optional[float]:
    """Get CPU% via ps -o %cpu=."""
    try:
        result = subprocess.run(
            ["ps", "-o", "%cpu=", "-p", str(pid)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, OSError):
        return None


# ==========================================================================
# Windows implementations (ctypes / wmic)
# ==========================================================================

def _get_win_kernel32() -> Any:
    """Return a kernel32 DLL handle with explicit argtypes/restype on Windows."""
    import ctypes
    import ctypes.wintypes

    windll_obj = getattr(ctypes, "windll", None)
    windll_k32 = getattr(windll_obj, "kernel32", None)
    win_dll_cls = getattr(ctypes, "WinDLL", None)
    # Honor monkeypatched fake kernel32 objects in unit tests (on both Linux and
    # Windows), while using a private WinDLL with explicit argtypes/restype in
    # real Windows execution.
    if win_dll_cls is not None and isinstance(windll_k32, win_dll_cls):
        kernel32 = win_dll_cls("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [
            ctypes.wintypes.DWORD,
            ctypes.wintypes.BOOL,
            ctypes.wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [
            ctypes.wintypes.HANDLE,
            ctypes.POINTER(ctypes.wintypes.DWORD),
        ]
        kernel32.GetExitCodeProcess.restype = ctypes.wintypes.BOOL
        kernel32.GetProcessTimes.argtypes = [
            ctypes.wintypes.HANDLE,
            ctypes.POINTER(ctypes.wintypes.FILETIME),
            ctypes.POINTER(ctypes.wintypes.FILETIME),
            ctypes.POINTER(ctypes.wintypes.FILETIME),
            ctypes.POINTER(ctypes.wintypes.FILETIME),
        ]
        kernel32.GetProcessTimes.restype = ctypes.wintypes.BOOL
        kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
        kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
        return kernel32
    return ctypes.windll.kernel32  # type: ignore[attr-defined]


def _is_pid_alive_windows(pid: int) -> bool:
    """Check PID liveness on Windows using kernel32.OpenProcess."""
    # A Windows process id is a DWORD (0 .. 2**32-1). An absurd PID from a corrupt dir name
    # would overflow the ctypes argument (raising ctypes.ArgumentError, which is NOT an
    # OverflowError subclass), so reject out-of-range ids up front rather than at the call.
    if pid <= 0 or pid > 0xFFFFFFFF:
        return False
    try:
        import ctypes
        import ctypes.wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259

        kernel32 = _get_win_kernel32()
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.wintypes.DWORD()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return bool(exit_code.value == STILL_ACTIVE)
            return False
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        # Any failure (incl. ctypes.ArgumentError wrapping an OverflowError for an
        # out-of-range PID) means "not alive" — never propagate a raise.
        return False


def _get_start_time_windows(pid: int) -> Optional[float]:
    """Get process creation time on Windows via kernel32.GetProcessTimes."""
    if pid <= 0 or pid > 0xFFFFFFFF:
        return None
    try:
        import ctypes
        import ctypes.wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

        kernel32 = _get_win_kernel32()
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return None
        try:
            creation = ctypes.wintypes.FILETIME()
            exit_t = ctypes.wintypes.FILETIME()
            kernel_t = ctypes.wintypes.FILETIME()
            user_t = ctypes.wintypes.FILETIME()

            if not kernel32.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exit_t),
                ctypes.byref(kernel_t),
                ctypes.byref(user_t),
            ):
                return None

            # FILETIME is 100-nanosecond intervals since 1601-01-01
            # Convert to POSIX epoch
            ft = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
            EPOCH_DIFF = 116444736000000000  # 100-ns intervals between 1601 and 1970
            posix_us = (ft - EPOCH_DIFF) / 10_000_000
            return posix_us
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return None


def _get_rss_windows(pid: int) -> Optional[int]:
    """Get working set size via GetProcessMemoryInfo (falling back to wmic)."""
    if pid <= 0 or pid > 0xFFFFFFFF:
        return None
    try:
        import ctypes
        import ctypes.wintypes

        class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.wintypes.DWORD),
                ("PageFaultCount", ctypes.wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        PROCESS_VM_READ = 0x0010
        kernel32 = _get_win_kernel32()
        handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid
        )
        if not handle:
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            try:
                get_mem = getattr(kernel32, "K32GetProcessMemoryInfo", None)
                if get_mem is None:
                    psapi = ctypes.WinDLL("psapi", use_last_error=True)  # type: ignore[attr-defined]
                    get_mem = psapi.GetProcessMemoryInfo
                get_mem.argtypes = [
                    ctypes.wintypes.HANDLE,
                    ctypes.POINTER(_PROCESS_MEMORY_COUNTERS),
                    ctypes.wintypes.DWORD,
                ]
                get_mem.restype = ctypes.wintypes.BOOL
                counters = _PROCESS_MEMORY_COUNTERS()
                counters.cb = ctypes.sizeof(counters)
                if get_mem(handle, ctypes.byref(counters), counters.cb):
                    return int(counters.WorkingSetSize)
            finally:
                kernel32.CloseHandle(handle)
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["wmic", "process", "where", f"ProcessId={pid}", "get", "WorkingSetSize"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return None
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        # First line is header "WorkingSetSize", second is the value
        if len(lines) >= 2:
            return int(lines[1])  # Already in bytes
    except (subprocess.TimeoutExpired, ValueError, OSError):
        pass
    return None


def _get_cpu_windows(pid: int) -> Optional[float]:
    """Estimate CPU% on Windows via kernel32.GetProcessTimes.

    Falls back to None if unavailable.
    """
    if pid <= 0 or pid > 0xFFFFFFFF:
        return None
    try:
        import ctypes
        import ctypes.wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel32 = _get_win_kernel32()
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return None
        try:
            creation = ctypes.wintypes.FILETIME()
            exit_t = ctypes.wintypes.FILETIME()
            kernel_t = ctypes.wintypes.FILETIME()
            user_t = ctypes.wintypes.FILETIME()

            if not kernel32.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exit_t),
                ctypes.byref(kernel_t),
                ctypes.byref(user_t),
            ):
                return None

            # Total CPU time in 100-ns intervals
            kernel_time = (kernel_t.dwHighDateTime << 32) | kernel_t.dwLowDateTime
            user_time = (user_t.dwHighDateTime << 32) | user_t.dwLowDateTime
            total_cpu_100ns = kernel_time + user_time

            # Process creation time
            ft = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
            EPOCH_DIFF = 116444736000000000
            create_posix = (ft - EPOCH_DIFF) / 10_000_000

            elapsed = time.time() - create_posix
            if elapsed <= 0:
                return 0.0

            total_cpu_seconds = total_cpu_100ns / 10_000_000
            return (total_cpu_seconds / elapsed) * 100.0
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return None


# --------------------------------------------------------------------------
# Hostname utility
# --------------------------------------------------------------------------

def get_hostname() -> str:
    """Return the current machine's hostname."""
    return platform.node()
