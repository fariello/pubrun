"""Tests for the edge-case / failure-mode hardening (IPD 20260705-assess-edge-cases).

Covers the malformed-input, external-tool, and hygiene fixes EC-01..EC-26.
Liveness (EC-05/06/07) is tested in test_liveness.py; the resource-watcher
failure semantics (EC-12) in test_resources.py.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest


def _write_run(runs_dir: Path, name: str, manifest=None, lock=None) -> Path:
    """Create a run directory under runs_dir with an optional manifest/lock."""
    run_dir = runs_dir / name
    run_dir.mkdir(parents=True)
    if manifest is not None:
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if lock is not None:
        (run_dir / ".pubrun.lock").write_text(json.dumps(lock), encoding="utf-8")
    return run_dir


class TestStatusReaderTolerance:
    """EC-01/02/03/04: malformed manifests/locks must not crash the listing."""

    def test_string_started_at_utc_does_not_crash_scan(self, tmp_path):
        from pubrun.status import scan_runs
        runs = tmp_path / "runs"
        # A good run plus one with a string timestamp (foreign/edited manifest).
        _write_run(runs, "pubrun-good-20260101T000000Z-111-aaaa1111", manifest={
            "run": {"run_id": "aaaa1111"},
            "status": {"outcome": "completed"},
            "timing": {"started_at_utc": 1780000000.0, "ended_at_utc": 1780000100.0},
        })
        _write_run(runs, "pubrun-bad-20260101T000000Z-222-bbbb2222", manifest={
            "run": {"run_id": "bbbb2222"},
            "status": {"outcome": "completed"},
            "timing": {"started_at_utc": "2026-01-01", "ended_at_utc": None},
        })
        result = scan_runs(str(runs))  # must not raise
        assert len(result) == 2
        ids = {r.run_id for r in result}
        assert "aaaa1111" in ids and "bbbb2222" in ids

    def test_out_of_range_and_nan_epoch_render(self, tmp_path):
        from pubrun.status import scan_runs, _format_timestamp
        runs = tmp_path / "runs"
        _write_run(runs, "pubrun-x-20260101T000000Z-333-cccc3333", manifest={
            "run": {"run_id": "cccc3333"},
            "status": {"outcome": "completed"},
            "timing": {"started_at_utc": 1e30},  # out of range for fromtimestamp
        })
        result = scan_runs(str(runs))
        assert len(result) == 1
        # _format_timestamp degrades bad epochs to "-" rather than raising.
        assert _format_timestamp(1e30) == "-"
        assert _format_timestamp(float("nan")) == "-"
        assert _format_timestamp("not-a-number") == "-"  # type: ignore[arg-type]
        assert _format_timestamp(None) == "-"

    def test_non_dict_signals_received_does_not_crash(self, tmp_path):
        from pubrun.status import scan_runs
        runs = tmp_path / "runs"
        _write_run(runs, "pubrun-sig-20260101T000000Z-444-dddd4444", manifest={
            "run": {"run_id": "dddd4444"},
            "status": {"outcome": "completed"},
            "timing": {"started_at_utc": 1780000000.0},
            "signals": {"signals_received": ["not-a-dict", 13, {"signal_name": "SIGPIPE"}]},
        })
        result = scan_runs(str(runs))  # must not raise
        assert len(result) == 1
        # The junk entries are dropped; the valid SIGPIPE dict survives.
        assert result[0].signals_received == [{"signal_name": "SIGPIPE"}]

    def test_non_string_argv_does_not_crash(self, tmp_path):
        from pubrun.status import scan_runs
        runs = tmp_path / "runs"
        _write_run(runs, "pubrun-argv-20260101T000000Z-555-eeee5555", manifest={
            "run": {"run_id": "eeee5555"},
            "status": {"outcome": "completed"},
            "timing": {"started_at_utc": 1780000000.0},
            "invocation": {"argv": ["train.py", 1, 2, None]},
        })
        result = scan_runs(str(runs))  # must not raise
        assert len(result) == 1

    def test_utc_display_flag(self):
        from pubrun.status import _format_timestamp
        # 2021-01-01 00:00:00 UTC
        epoch = 1609459200.0
        assert _format_timestamp(epoch, utc=True).endswith("Z")
        assert "2021-01-01" in _format_timestamp(epoch, utc=True)


class TestPackagesNullName:
    """EC-08: a None distribution name must not crash get_packages."""

    def test_none_name_yields_partial_not_crash(self, monkeypatch):
        import pubrun.capture.packages as pkgs

        class FakeDist:
            version = "1.0"
            metadata = {"Name": None}

            def locate_file(self, x):
                return "/tmp/x"

            def read_text(self, x):
                return None

        monkeypatch.setattr(
            "importlib.metadata.distributions", lambda: [FakeDist()]
        )
        result = pkgs.get_packages({"capture": {"packages": {"mode": "full-environment"}}})
        # Must return without raising; records sorted with the None name coerced.
        assert "records" in result
        assert result["capture_state"]["status"] in ("complete", "partial")


class TestManualSubprocessCap:
    """EC-09: manual subprocess records are bounded."""

    def test_cap_bounds_records(self):
        from pubrun.core import _append_manual_subprocess_record

        class FakeRun:
            config = {"capture": {"subprocesses": {"max_tracked_commands": 5}}}

        run = FakeRun()
        for i in range(20):
            _append_manual_subprocess_record(run, {"argv": [str(i)]})
        assert len(run.manual_subprocess_records) == 5


class TestConfigTolerance:
    """EC-14: a malformed .pubrun.toml must not crash config resolution."""

    def test_malformed_local_config_is_skipped(self, tmp_path, monkeypatch):
        from pubrun.config import resolve_config
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        (tmp_path / ".pubrun.toml").write_text("this is = = not valid toml [[[", encoding="utf-8")
        # Must not raise; falls back to defaults + valid layers.
        cfg = resolve_config()
        assert cfg.get("core", {}).get("profile") == "default"

    def test_valid_local_config_still_applies(self, tmp_path, monkeypatch):
        from pubrun.config import resolve_config
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        (tmp_path / ".pubrun.toml").write_text("[core]\nprofile = \"deep\"\n", encoding="utf-8")
        cfg = resolve_config()
        assert cfg["core"]["profile"] == "deep"


class TestGitTimeout:
    """EC-13: a git timeout is recorded distinctly, not as 'not a repo'."""

    def test_git_timeout_status(self, monkeypatch):
        import pubrun.capture.git as gitmod

        def fake_run(*a, **k):
            raise subprocess.TimeoutExpired(cmd="git", timeout=5)

        monkeypatch.setattr(gitmod.subprocess, "run", fake_run)
        result = gitmod.get_git({"capture": {"git": {"enabled": True, "timeout": 5}}})
        assert result["capture_state"]["status"] == "timeout"


class TestExcepthookRestore:
    """EC-15: restoring the excepthook must not clobber a later-installed hook."""

    def test_later_hook_survives(self):
        import sys as _sys
        from pubrun.capture.signals import SignalExitCapture

        original = _sys.excepthook
        try:
            # __init__ installs the excepthook wrapper.
            sc = SignalExitCapture()
            # A third party installs its own hook AFTER pubrun.
            def third_party(exc_type, exc_value, exc_tb):
                pass
            _sys.excepthook = third_party
            sc._restore_excepthook()
            # Our restore must NOT have clobbered the third-party hook.
            assert _sys.excepthook is third_party
        finally:
            _sys.excepthook = original


class TestConsoleTeeGuard:
    """EC-16: tee passthrough tolerates a closed/broken original stream."""

    def test_closed_stream_does_not_raise(self):
        from pubrun.capture.console import TqdmSafeTee

        class ClosedStream:
            def write(self, data):
                raise ValueError("I/O operation on closed file")

        tee = TqdmSafeTee(ClosedStream(), log_file=None)
        # Must not raise out of write().
        assert tee.write("hello") == len("hello")


class TestDiffRobustness:
    """EC-18/19: diff tolerates malformed manifests and bool/int aliasing."""

    def test_unflatten_prefix_collision(self):
        from pubrun.analysis.diff import unflatten_manifest
        # 'a.b' scalar and 'a.b.c' nested collide; must not raise.
        result = unflatten_manifest({"a.b": 1, "a.b.c": 2})
        assert result  # produced something without crashing

    def test_normalize_tolerates_non_list_sections(self):
        from pubrun.analysis.diff import _normalize_manifest
        manifest = {
            "environment": {"variables": {"not": "a list"}},
            "packages": {"records": None},
        }
        # Must not raise.
        flat = _normalize_manifest(manifest, [], "deep")
        assert isinstance(flat, dict)

    def test_list_diff_bool_int_not_aliased(self):
        """When a list diff IS triggered, bool/int must not alias in the
        added/removed computation. Use a list whose length differs so the
        top-level != is True and the list_diff branch runs."""
        from pubrun.analysis.diff import compare_manifests
        a = {"x": {"items": [1, 2]}}
        b = {"x": {"items": [True, 2, 3]}}
        report = compare_manifests(a, b, ignores=[], depth="deep")
        mod = report["modified"].get("x.items")
        assert mod is not None and mod["type"] == "list_diff"
        # True is present in b but not (as a bool) in a -> added; 1 removed.
        assert True in mod["added"]
        assert 1 in mod["removed"]
        # 3 is a plain new int.
        assert 3 in mod["added"]

    def test_compare_manifests_ignores_default_is_safe(self):
        from pubrun.analysis.diff import compare_manifests
        # Called twice with no ignores; the default must not be a shared mutable.
        compare_manifests({"a": 1}, {"a": 2})
        r = compare_manifests({"a": 1}, {"a": 2})
        assert "a" in r["modified"]


class TestPrintNormalization:
    """EC-21: pubrun.print tolerates sep=None/end=None."""

    def test_sep_none_does_not_raise(self, capsys):
        from pubrun.core import print as pubrun_print
        # Builtin print accepts sep=None; our wrapper must too.
        pubrun_print("a", "b", sep=None, end=None)
        out = capsys.readouterr().out
        assert "a" in out and "b" in out
