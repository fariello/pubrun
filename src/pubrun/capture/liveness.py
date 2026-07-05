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
from typing import Optional, Tuple


_PLATFORM = sys.platform  # 'linux', 'darwin', 'win32'


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
     "sh", "bash", "env", "interactive"}
)


def _script_is_generic(expected_script: str) -> bool:
    """True if expected_script is too generic to confirm a match alone."""
    from pathlib import Path
    base = Path(expected_script).name
    return len(base) < 3 or base in _GENERIC_SCRIPT_TOKENS


def _match_script_in_tokens(expected_script: str, tokens) -> Optional[bool]:
    """Given the command-line tokens of a process, decide whether it is running
    ``expected_script``.

    Returns True on an exact basename match (confirmed same process), False when
    the script name appears nowhere at all (confirmed mismatch / recycled PID),
    and None when the only evidence is a substring (ambiguous) so the caller
    falls through to start-time timing. (IPD 20260705 EC-06.)
    """
    from pathlib import Path
    tokens = [t for t in tokens if t]
    if not tokens:
        return None
    exact = False
    substring = False
    for tok in tokens:
        if Path(tok).name == expected_script or tok == expected_script:
            exact = True
            break
        if expected_script in tok:
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
        with open(f"/proc/{pid}/cmdline", "r", encoding="utf-8") as f:
            cmdline = f.read()
        if not cmdline:
            return None
        parts = cmdline.split("\x00")
        return _match_script_in_tokens(expected_script, parts)
    except OSError:
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
        clock_ticks = os.sysconf("SC_CLK_TCK")

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

        clock_ticks = os.sysconf("SC_CLK_TCK")
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
        result = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        # Output format: "Thu May 31 14:02:17 2026" (locale-independent format)
        from datetime import datetime
        dt = datetime.strptime(result.stdout.strip(), "%a %b %d %H:%M:%S %Y")
        return dt.timestamp()
    except (subprocess.TimeoutExpired, ValueError, OSError):
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

def _is_pid_alive_windows(pid: int) -> bool:
    """Check PID liveness on Windows using kernel32.OpenProcess."""
    try:
        import ctypes
        import ctypes.wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.wintypes.DWORD()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return exit_code.value == STILL_ACTIVE
            return False
        finally:
            kernel32.CloseHandle(handle)
    except (OSError, AttributeError, ValueError):
        return False


def _get_start_time_windows(pid: int) -> Optional[float]:
    """Get process creation time on Windows via kernel32.GetProcessTimes."""
    try:
        import ctypes
        import ctypes.wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
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
    except (OSError, AttributeError, ValueError):
        return None


def _get_rss_windows(pid: int) -> Optional[int]:
    """Get working set size via wmic."""
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
    """Estimate CPU% on Windows via wmic or ctypes.

    Uses a two-sample approach with a brief sleep for accuracy.
    Falls back to None if unavailable.
    """
    try:
        import ctypes
        import ctypes.wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
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
    except (OSError, AttributeError, ValueError, ZeroDivisionError):
        return None


# --------------------------------------------------------------------------
# Hostname utility
# --------------------------------------------------------------------------

def get_hostname() -> str:
    """Return the current machine's hostname."""
    return platform.node()
