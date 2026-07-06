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


# ---------------------------------------------------------------------------
# The paused() feature
# ---------------------------------------------------------------------------

class TestPausedSpy:
    """paused() suspends subprocess recording on the calling thread."""

    def test_spy_recording_suspended_and_resumed(self):
        import pubrun
        from pubrun.capture.subprocesses import SubprocessSpy
        SubprocessSpy._records = []
        SubprocessSpy.install(max_records=100)
        try:
            import subprocess
            subprocess.Popen([sys.executable, "-c", "pass"]).wait()
            before = len(SubprocessSpy._records)
            assert before >= 1
            with pubrun.paused():
                subprocess.Popen([sys.executable, "-c", "pass"]).wait()
            assert len(SubprocessSpy._records) == before  # not recorded
            subprocess.Popen([sys.executable, "-c", "pass"]).wait()
            assert len(SubprocessSpy._records) == before + 1  # resumed
        finally:
            SubprocessSpy.uninstall()

    def test_resume_on_exception(self):
        import pubrun
        from pubrun.capture.subprocesses import _spy_bypassed
        assert not _spy_bypassed()
        with pytest.raises(ValueError):
            with pubrun.paused():
                assert _spy_bypassed()
                raise ValueError("boom")
        assert not _spy_bypassed()  # resumed despite the exception

    def test_nested_paused(self):
        import pubrun
        from pubrun.capture.subprocesses import _spy_bypassed
        with pubrun.paused():
            with pubrun.paused():
                assert _spy_bypassed()
            assert _spy_bypassed()  # outer still open
        assert not _spy_bypassed()

    def test_disable_spy_inside_paused_does_not_resume_early(self):
        """A disable_spy() opened inside a paused() must not re-enable recording
        when it exits (the outer pause is still open)."""
        import pubrun
        from pubrun.capture.subprocesses import _spy_bypassed, disable_spy
        with pubrun.paused():
            with disable_spy():
                assert _spy_bypassed()
            assert _spy_bypassed()  # outer paused() still holds
        assert not _spy_bypassed()


class TestPausedConsole:
    """paused() suspends console recording on the calling thread (tee)."""

    def test_tee_recording_suspended(self, tmp_path):
        import pubrun
        from pubrun.capture.console import TqdmSafeTee
        log = tmp_path / "out.log"
        with open(log, "w", encoding="utf-8") as f:
            tee = TqdmSafeTee(sys.__stdout__, f, timestamped=False)
            tee.write("before\n")
            with pubrun.paused():
                tee.write("during-not-recorded\n")
            tee.write("after\n")
            tee.flush()
        text = log.read_text(encoding="utf-8")
        assert "before" in text
        assert "after" in text
        assert "during-not-recorded" not in text  # muted while paused

    def test_tee_passthrough_still_happens_while_paused(self, tmp_path):
        """Output still goes to the real stream even while recording is paused."""
        import io
        import pubrun
        from pubrun.capture.console import TqdmSafeTee
        sink = io.StringIO()
        log = tmp_path / "out.log"
        with open(log, "w", encoding="utf-8") as f:
            tee = TqdmSafeTee(sink, f, timestamped=False)
            with pubrun.paused():
                tee.write("visible-in-terminal\n")
        assert "visible-in-terminal" in sink.getvalue()      # passthrough
        assert "visible-in-terminal" not in log.read_text(encoding="utf-8")  # not recorded


class TestPausedThreadIsolation:
    """A paused() on one thread must NOT suspend another thread's recording."""

    def test_other_thread_still_records_spy(self):
        import pubrun
        from pubrun.capture.subprocesses import _spy_bypassed
        results = {}
        started = threading.Event()
        release = threading.Event()

        def worker():
            # While the main thread holds paused(), this thread must NOT be paused.
            started.wait(5)
            results["worker_bypassed"] = _spy_bypassed()
            release.set()

        t = threading.Thread(target=worker)
        t.start()
        with pubrun.paused():
            assert _spy_bypassed()          # main thread paused
            started.set()
            release.wait(5)
        t.join(5)
        assert results.get("worker_bypassed") is False  # worker unaffected

    def test_other_thread_still_records_console(self):
        import pubrun
        from pubrun.capture.console import _tee_paused
        results = {}
        started = threading.Event()
        release = threading.Event()

        def worker():
            started.wait(5)
            results["worker_paused"] = _tee_paused()
            release.set()

        t = threading.Thread(target=worker)
        t.start()
        with pubrun.paused():
            started.set()
            release.wait(5)
        t.join(5)
        assert results.get("worker_paused") is False


class TestPausedNotOverreaching:
    """annotate()/phase() still fire and resources still sample inside paused()."""

    def test_annotate_still_fires(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        import pubrun
        tracker = pubrun.start(events={"enabled": True})
        try:
            with pubrun.paused():
                pubrun.annotate("inside-paused-block")
        finally:
            rd = tracker.run_dir
            pubrun.stop()
        events = (rd / "events.jsonl").read_text(encoding="utf-8")
        assert "inside-paused-block" in events  # annotate is NOT paused


class TestPausedApiExposure:
    """paused() is reachable via top-level import and every mode alias."""

    def test_top_level_has_paused(self):
        import pubrun
        assert hasattr(pubrun, "paused")

    @pytest.mark.parametrize("mode", ["auto", "full", "noauto", "nopatch", "noconsole", "minimal"])
    def test_mode_alias_has_paused(self, mode):
        import json
        import subprocess
        script = f"import pubrun.{mode} as pubrun; print('OK' if hasattr(pubrun,'paused') else 'MISSING')"
        r = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, timeout=20,
            env={**os.environ, "PUBRUN_IMPORT_MODE": "", "PUBRUN_AUTO_START": ""},
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        assert "OK" in r.stdout, f"stdout: {r.stdout}"
