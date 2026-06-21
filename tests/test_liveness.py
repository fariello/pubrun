"""Tests for pubrun.capture.liveness -- cross-platform process liveness checks."""
import os
import sys
import time

import pytest

from pubrun.capture.liveness import (
    get_cpu_percent,
    get_hostname,
    get_process_start_time,
    get_rss_bytes,
    is_pid_alive,
    is_same_process,
)


class TestIsPidAlive:
    """Tests for PID liveness detection."""

    def test_current_process_is_alive(self):
        """Our own PID should always be alive."""
        assert is_pid_alive(os.getpid()) is True

    def test_nonexistent_pid_is_dead(self):
        """An extremely high PID that cannot exist should be dead."""
        # PID 4000000 is beyond realistic on most systems
        assert is_pid_alive(4000000) is False

    def test_pid_zero_is_not_alive(self):
        """PID 0 (kernel scheduler on Unix) should not be reported as alive via signal."""
        # On Unix, kill(0, 0) sends signal to the process group, so we skip that.
        # On Windows, PID 0 is the System Idle Process.
        if sys.platform != "win32":
            # PID 0 with os.kill sends to the process group -- different semantics
            pass
        else:
            assert is_pid_alive(0) is False


class TestGetProcessStartTime:
    """Tests for process start time retrieval."""

    def test_current_process_has_start_time(self):
        """Our own process should have a retrievable start time."""
        start = get_process_start_time(os.getpid())
        if start is None:
            pytest.skip("Platform does not support start time retrieval")
        # Start time should be recent (within the last hour for a test)
        assert start > time.time() - 3600
        assert start <= time.time()

    def test_dead_pid_returns_none(self):
        """A non-existent PID should return None."""
        result = get_process_start_time(4000000)
        assert result is None


class TestIsSameProcess:
    """Tests for PID + start-time matching."""

    def test_same_process_matches(self):
        """Our own PID with current time should match."""
        # The start time we pass needs to be close to the actual process start.
        # Since we don't know our exact start time here, use a generous tolerance.
        start = get_process_start_time(os.getpid())
        if start is None:
            pytest.skip("Platform does not support start time retrieval")
        assert is_same_process(os.getpid(), start, tolerance=5.0) is True

    def test_dead_pid_does_not_match(self):
        """A dead PID should not match."""
        assert is_same_process(4000000, time.time()) is False

    def test_wrong_start_time_does_not_match(self):
        """Alive PID but wrong start time (PID recycling) should not match when no script name is given."""
        start = get_process_start_time(os.getpid())
        if start is None:
            pytest.skip("Platform does not support start time retrieval")
        # Use a start time from 2 days ago -- beyond the default 24h tolerance
        assert is_same_process(os.getpid(), start - 172800) is False

    def test_expected_script_matches(self):
        """If expected_script matches the actual process command line, it matches."""
        from pubrun.capture.liveness import _PLATFORM, _check_command_linux, _check_command_macos, _check_command_windows
        functional = False
        if _PLATFORM == "linux":
            functional = _check_command_linux(os.getpid(), "pytest") is not None
        elif _PLATFORM == "darwin":
            functional = _check_command_macos(os.getpid(), "pytest") is not None
        elif _PLATFORM == "win32":
            functional = _check_command_windows(os.getpid(), "pytest") is not None

        if not functional:
            pytest.skip("Command-line checking is not functional on this platform")

        # Our own process should be running "pytest"
        assert is_same_process(os.getpid(), time.time(), expected_script="pytest") is True

    def test_expected_script_mismatch(self):
        """If expected_script does not match, it should return False immediately (recycled PID)."""
        from pubrun.capture.liveness import _PLATFORM, _check_command_linux, _check_command_macos, _check_command_windows
        functional = False
        if _PLATFORM == "linux":
            functional = _check_command_linux(os.getpid(), "pytest") is not None
        elif _PLATFORM == "darwin":
            functional = _check_command_macos(os.getpid(), "pytest") is not None
        elif _PLATFORM == "win32":
            functional = _check_command_windows(os.getpid(), "pytest") is not None

        if not functional:
            pytest.skip("Command-line checking is not functional on this platform")

        # Even if the start time is identical (current process), script name mismatch fails
        start = get_process_start_time(os.getpid())
        if start is None:
            pytest.skip("Platform does not support start time retrieval")
        assert is_same_process(os.getpid(), start, expected_script="nonexistent_script_xyz.py") is False

    def test_default_generous_tolerance(self):
        """The default tolerance should be 24 hours, so a start time off by 12 hours matches."""
        start = get_process_start_time(os.getpid())
        if start is None:
            pytest.skip("Platform does not support start time retrieval")
        # Off by 12 hours (43200 seconds) - within default 24h tolerance
        assert is_same_process(os.getpid(), start - 43200) is True


class TestGetRssBytes:
    """Tests for RSS memory retrieval."""

    def test_current_process_has_rss(self):
        """Our own process should report some RSS."""
        rss = get_rss_bytes(os.getpid())
        if rss is None:
            pytest.skip("Platform does not support RSS retrieval")
        # Any Python process uses at least a few MB
        assert rss > 1_000_000

    def test_dead_pid_returns_none(self):
        """A non-existent PID should return None."""
        result = get_rss_bytes(4000000)
        assert result is None


class TestGetCpuPercent:
    """Tests for CPU usage retrieval."""

    def test_current_process_returns_float(self):
        """Our own process should return a float (possibly 0.0)."""
        cpu = get_cpu_percent(os.getpid())
        if cpu is None:
            pytest.skip("Platform does not support CPU retrieval")
        assert isinstance(cpu, float)
        assert cpu >= 0.0

    def test_dead_pid_returns_none(self):
        """A non-existent PID should return None."""
        result = get_cpu_percent(4000000)
        assert result is None


class TestGetHostname:
    """Tests for hostname retrieval."""

    def test_returns_nonempty_string(self):
        """Hostname should be a non-empty string."""
        hostname = get_hostname()
        assert isinstance(hostname, str)
        assert len(hostname) > 0
