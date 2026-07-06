"""Tests for scoped pause/resume of capture (IPD 20260705-scoped-pause-resume).

`pubrun.paused()` suspends RECORDING on the calling thread (mute semantics):
output still goes to the terminal and subprocesses still run, but the console
tee and subprocess spy do not record while paused. Thread-local: another thread
keeps being captured. Resource sampling and annotate/phase are NOT paused.

The `TestCharacterization` class pins pre-change behavior (must stay green after
the feature lands). The remaining classes test the new `paused()` behavior.
"""
import os
import sys
import threading
import time

import pytest


# ---------------------------------------------------------------------------
# Step 1: characterization gate (pin CURRENT behavior; must stay green after)
# ---------------------------------------------------------------------------

class TestCharacterization:
    """Behavior that must NOT regress when pause/resume lands."""

    def test_disable_spy_bypasses_and_restores(self):
        from pubrun.capture.subprocesses import SubprocessSpy, disable_spy
        SubprocessSpy._records = []
        SubprocessSpy.install(max_records=100)
        try:
            import subprocess
            # Recorded normally.
            subprocess.Popen([sys.executable, "-c", "pass"]).wait()
            baseline = len(SubprocessSpy._records)
            assert baseline >= 1
            # Inside disable_spy: not recorded.
            with disable_spy():
                subprocess.Popen([sys.executable, "-c", "pass"]).wait()
            assert len(SubprocessSpy._records) == baseline
            # After: recording resumes.
            subprocess.Popen([sys.executable, "-c", "pass"]).wait()
            assert len(SubprocessSpy._records) == baseline + 1
        finally:
            SubprocessSpy.uninstall()

    def test_disable_spy_nests(self):
        from pubrun.capture.subprocesses import SubprocessSpy, disable_spy
        SubprocessSpy._records = []
        SubprocessSpy.install(max_records=100)
        try:
            import subprocess
            with disable_spy():
                with disable_spy():
                    subprocess.Popen([sys.executable, "-c", "pass"]).wait()
                # Still bypassed after inner exit (outer still open).
                subprocess.Popen([sys.executable, "-c", "pass"]).wait()
                assert len(SubprocessSpy._records) == 0
            # Both closed -> recording resumes.
            subprocess.Popen([sys.executable, "-c", "pass"]).wait()
            assert len(SubprocessSpy._records) == 1
        finally:
            SubprocessSpy.uninstall()

    def test_tee_records_normally(self, tmp_path):
        from pubrun.capture.console import TqdmSafeTee
        log = tmp_path / "out.log"
        with open(log, "w", encoding="utf-8") as f:
            tee = TqdmSafeTee(sys.__stdout__, f, timestamped=False)
            tee.write("hello\n")
            tee.flush()
        assert "hello" in log.read_text(encoding="utf-8")
