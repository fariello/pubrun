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
        # 'a.b' scalar and 'a.b.c' nested collide; preserve both without crashing.
        result = unflatten_manifest({"a.b": 1, "a.b.c": 2})
        assert result == {"a": {"b": 1}, "a.b.c": 2}

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


class TestDegradedPartialManifestConsumers:
    """Heavily degraded partial manifests render cleanly across status, diagnostics, checks, and methods."""

    def test_degraded_manifest_with_nulls_and_failed_sections_across_all_consumers(
        self, tmp_path, monkeypatch, capsys
    ):
        from pubrun.report.checks import manifest_findings
        from pubrun.report.diagnostics import print_report
        from pubrun.report.methods import generate_report, generate_report_multi
        from pubrun.status import scan_runs

        monkeypatch.setenv("NO_COLOR", "1")
        degraded = {
            "run": None,
            "timing": {"started_at_utc": "not-a-timestamp", "elapsed_seconds": "bad"},
            "status": None,
            "invocation": {
                "script": None,
                "argv": ["train.py", 1, None, {"k": "v"}],
                "capture_state": {"status": "failed", "detail": "argv fallback"},
            },
            "signals": {
                "exit_code": 0,
                "signals_received": ["not-a-dict", 13, {"signal": 15, "signal_name": None}],
                "capture_state": {"status": "failed", "detail": "signal hook failed"},
            },
            "host": {
                "hostname": {"representation": "redacted"},
                "os_name": None,
                "os_version": None,
                "capture_state": {"status": "failed", "detail": "host probe failed"},
            },
            "hardware": {
                "cpu": None,
                "memory_total_bytes": "not-bytes",
                "capture_state": {"status": "failed", "detail": "hardware probe failed"},
            },
            "python": {
                "executable": None,
                "version": "   ",
                "implementation": None,
                "capture_state": {"status": "failed", "detail": "python probe failed"},
            },
            "git": {
                "commit": 12345,
                "remote_url": None,
                "capture_state": {"status": "failed", "detail": "git probe failed"},
            },
            "packages": {
                "records": ["not-a-dict", {"name": None, "version": None}],
                "capture_state": {"status": "failed", "detail": "packages probe failed"},
            },
            "environment": {
                "variables": [None, {"name": "MY_KEY", "value": {"representation": None}}],
                "capture_state": {"status": "failed", "detail": "env probe failed"},
            },
            "config": {"notices": [None, "plain-notice", {"code": "c1", "message": "notice msg"}]},
            "subprocesses": [
                "not-a-dict",
                {"argv": ["echo", 42], "exit_code": 0, "started_at_utc": "bad", "ended_at_utc": 2.0},
            ],
            "errors": {
                "records": [
                    "not-a-dict",
                    {"kind": "capture-error", "section": None, "message": None, "type": "OSError"},
                    {"kind": "capture-error", "section": "events", "message": "disk full"},
                ],
                "capture_state": {"status": "partial", "detail": "3 additional capture error(s) omitted"},
            },
        }
        runs_dir = tmp_path / "runs"
        run_dir = _write_run(
            runs_dir,
            "pubrun-degraded-20260101T000000Z-777-degr0001",
            manifest=degraded,
        )
        manifest_path = run_dir / "manifest.json"

        # 1. status.scan_runs()
        scanned = scan_runs(str(runs_dir))
        assert len(scanned) == 1

        # 2. diagnostics.print_report() across depths and section extracts
        for depth in ("basic", "standard", "deep"):
            print_report(str(manifest_path), depth=depth)
            out = capsys.readouterr().out
            assert "\033" not in out
            assert "[WARN ]" in out
            assert "unknown" in out

        for sec in ("env", "packages"):
            print_report(str(manifest_path), section=sec)
            sec_out = capsys.readouterr().out
            assert "\033" not in sec_out
            assert "capture failed" in sec_out

        # Also verify out-of-range numeric timestamp does not raise OverflowError.
        overflow_manifest = dict(degraded)
        overflow_manifest["timing"] = {"started_at_utc": 1e30, "elapsed_seconds": float("nan")}
        overflow_path = tmp_path / "overflow_manifest.json"
        overflow_path.write_text(json.dumps(overflow_manifest, allow_nan=True), encoding="utf-8")
        print_report(str(overflow_path), depth="basic")
        assert "Started     : unknown" in capsys.readouterr().out

        # 3. checks.manifest_findings()
        findings = manifest_findings(degraded, current_hostname="other-host")
        codes = {f["code"] for f in findings}
        assert "packages_capture_failed" in codes
        assert "git_capture_failed" in codes
        assert "capture_error_events" in codes
        assert "capture_error_general" in codes
        assert "errors_capture_partial" in codes

        # 4. methods.generate_report() and generate_report_multi()
        md = generate_report(degraded, "markdown")
        tex = generate_report(degraded, "latex")
        assert "Package provenance was unavailable because package capture failed." in md
        assert "Package provenance was unavailable because package capture failed." in tex
        assert "Standard library dependencies" not in md

        healthy = {
            "host": {"os_name": "Linux"},
            "hardware": {"cpu": {"model": "Intel"}, "memory_total_bytes": 1024 ** 3},
            "python": {"version": "3.11.4", "implementation": "cpython"},
            "git": {"commit": "abcdef123456"},
            "packages": {"records": [{"name": "numpy", "version": "1.26.0"}]},
        }
        multi_md = generate_report_multi([healthy, degraded], "markdown")
        multi_tex = generate_report_multi([healthy, degraded], "latex")
        assert "(package capture failed)" in multi_md
        assert "(package capture failed)" in multi_tex
        assert "partial provenance across 1 of 2 runs" in multi_md
        assert "% Note: partial provenance across 1 of 2 runs;" in multi_tex


class TestConfigCwdUtf8AndSections:
    """1o1cua E-01: deleted CWD, non-UTF-8 TOML, and scalar TOML sections."""

    def test_deleted_cwd_degrades_safely_in_config_and_inactive_policy(self, monkeypatch):
        from pubrun import config as cfg_mod
        from pubrun import core as core_mod

        def _missing_cwd():
            raise FileNotFoundError("No such file or directory")

        monkeypatch.setattr(Path, "cwd", staticmethod(_missing_cwd))
        monkeypatch.setattr(core_mod, "_INACTIVE_POLICY_CACHE", None)
        monkeypatch.setattr(core_mod, "_LOCAL_CONFIG_PATHS_MEMO", None)

        assert cfg_mod.load_local_config() is None
        cfg = cfg_mod.resolve_config()
        assert cfg["core"]["profile"] == "default"
        # Inactive annotate must not raise when CWD is gone.
        core_mod.annotate("deleted cwd test")

    def test_utf16_bom_and_invalid_utf8_local_toml_warn_and_fallback(
        self, tmp_path, monkeypatch, caplog
    ):
        import logging
        from pubrun.config import resolve_config

        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path))
        toml_path = tmp_path / ".pubrun.toml"

        # UTF-16 BOM
        toml_path.write_bytes('[core]\nprofile = "deep"\n'.encode("utf-16"))
        with caplog.at_level(logging.WARNING, logger="pubrun"):
            cfg = resolve_config()
        assert cfg["core"]["profile"] == "default"
        assert any("ignoring malformed config file" in r.getMessage() for r in caplog.records)

        # Invalid UTF-8 bytes
        caplog.clear()
        toml_path.write_bytes(b"\x80\x81\xfe\xff invalid bytes")
        with caplog.at_level(logging.WARNING, logger="pubrun"):
            cfg2 = resolve_config()
        assert cfg2["core"]["profile"] == "default"
        assert any("ignoring malformed config file" in r.getMessage() for r in caplog.records)

    def test_scalar_toml_sections_do_not_crash_config_events_writer_or_core(
        self, tmp_path, monkeypatch
    ):
        from pubrun import config as cfg_mod
        from pubrun import core as core_mod
        from pubrun import writer as writer_mod
        from pubrun.events import EventStream

        assert cfg_mod._section("not-a-dict", "core") == {}
        assert cfg_mod._section({"core": "bad"}, "core") == {}
        assert cfg_mod._section({"core": {"a": 1}}, "core") == {"a": 1}

        # _resolve_layers with scalar overrides["core"] + flat shortcut
        resolved = cfg_mod.resolve_config({"core": "bad", "output_dir": str(tmp_path)})
        assert isinstance(resolved["core"], dict)
        assert resolved["core"]["output_dir"] == str(tmp_path)

        # profile_deprecation_notice with scalar core
        assert cfg_mod.profile_deprecation_notice({"core": "bad"}) is None

        # .pubrun.toml with scalar sections
        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path))
        (tmp_path / ".pubrun.toml").write_text(
            'core = "bad"\nevents = false\nmethods = "bad"\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(core_mod, "_INACTIVE_POLICY_CACHE", None)
        assert core_mod._inactive_policy() == "ignore"

        # Non-string on_inactive_annotate falls back to "ignore"
        monkeypatch.setattr(
            cfg_mod,
            "resolve_config",
            lambda overrides=None: {"events": {"on_inactive_annotate": 123}},
        )
        monkeypatch.setattr(core_mod, "_INACTIVE_POLICY_CACHE", None)
        assert core_mod._inactive_policy() == "ignore"

        # EventStream with scalar events section
        stream = EventStream(tmp_path, config={"events": False})
        assert stream._max_events == 1_000_000
        assert stream._flush_interval == 100
        stream.close()

        # Writer durability + write_artifacts with scalar core/methods
        assert writer_mod._resolve_durability({"core": "bad"}, stage="startup") == "fsync"

        class _ScalarRun:
            def __init__(self, rdir):
                self.run_dir = rdir
                self.config = {"core": "bad", "methods": "bad"}
                self._finalized = False

            def _finalize_state(self):
                self._finalized = True

            def to_manifest_dict(self):
                return {"run": {"run_id": "scalar01"}}

        run_dir = tmp_path / "scalar_run"
        w = writer_mod.ArtifactWriter(_ScalarRun(run_dir))
        assert w.write_artifacts() is True
        assert (run_dir / "methods.md").exists()


class TestStrictJsonEventBoundsAndWriterHardening:
    """1o1cua E-02: strict RFC 8259 JSON, EventStream bounds, refresh skip, durability cap."""

    def test_event_stream_bound_validation(self, tmp_path, caplog):
        import logging
        from pubrun.events import EventStream

        for bad_max in (True, False, -1, "100", 1.5, None):
            caplog.clear()
            with caplog.at_level(logging.WARNING, logger="pubrun"):
                s = EventStream(tmp_path, config={"events": {"max_tracked_events": bad_max}})
            try:
                assert s._max_events == 1_000_000
                assert any("max_tracked_events" in r.getMessage() for r in caplog.records)
            finally:
                s.close()

        # 0 is valid for max_tracked_events (no warning)
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="pubrun"):
            s0 = EventStream(tmp_path, config={"events": {"max_tracked_events": 0}})
        try:
            assert s0._max_events == 0
            assert not any("max_tracked_events" in r.getMessage() for r in caplog.records)
        finally:
            s0.close()

        for bad_flush in (True, False, 0, -5, "10", 2.5, None):
            caplog.clear()
            with caplog.at_level(logging.WARNING, logger="pubrun"):
                s = EventStream(tmp_path, config={"events": {"flush_interval_events": bad_flush}})
            try:
                assert s._flush_interval == 100
                assert any("flush_interval_events" in r.getMessage() for r in caplog.records)
            finally:
                s.close()

    def test_strict_json_sanitization_and_cycles_in_events_and_writer(self, tmp_path, caplog):
        import logging
        from pubrun.events import EventStream
        from pubrun.writer import (
            _atomic_json_write,
            _sanitize_json_value,
            _serialize_config_and_digest,
        )

        def _reject_constant(token):
            raise AssertionError(f"Non-standard JSON constant emitted: {token}")

        # Shared non-cyclic DAG succeeds
        shared = {"v": float("nan")}
        dag = {"a": shared, "b": shared, "seq": [float("inf"), float("-inf"), (1.5, float("nan"))]}
        sanitized = _sanitize_json_value(dag)
        assert sanitized == {"a": {"v": None}, "b": {"v": None}, "seq": [None, None, (1.5, None)]}

        # Cycle raises ValueError("Circular reference detected")
        cyc_dict: dict = {}
        cyc_dict["self"] = cyc_dict
        with pytest.raises(ValueError, match="Circular reference detected"):
            _sanitize_json_value(cyc_dict)

        cyc_list: list = []
        cyc_list.append(cyc_list)
        with pytest.raises(ValueError, match="Circular reference detected"):
            _sanitize_json_value(cyc_list)

        # _atomic_json_write produces strict JSON and preserves default=str
        target = tmp_path / "strict.json"
        _atomic_json_write(
            target,
            {"nan": float("nan"), "inf": float("inf"), "ninf": float("-inf"), "p": tmp_path},
        )
        raw_text = target.read_text(encoding="utf-8")
        loaded = json.loads(raw_text, parse_constant=_reject_constant)
        assert loaded == {"nan": None, "inf": None, "ninf": None, "p": str(tmp_path)}

        # _atomic_json_write cleans up tmp on circular reference
        cyc_target = tmp_path / "cycle.json"
        with pytest.raises(ValueError, match="Circular reference detected"):
            _atomic_json_write(cyc_target, cyc_dict)
        assert not cyc_target.exists()
        assert list(tmp_path.glob("*.tmp")) == []

        # _serialize_config_and_digest produces strict JSON
        payload, _digest = _serialize_config_and_digest({"x": float("inf"), "p": tmp_path})
        assert json.loads(payload, parse_constant=_reject_constant) == {
            "x": None,
            "p": str(tmp_path),
        }

        # EventStream.emit: NaN/Inf -> null; cycle -> warning; unserializable -> TypeError warning
        stream = EventStream(tmp_path, config={"events": {"enabled": True}})
        try:
            stream.emit(
                "annotation",
                name="floats",
                payload={"a": float("nan"), "b": [float("inf"), float("-inf")]},
            )
            with caplog.at_level(logging.WARNING, logger="pubrun"):
                stream.emit("annotation", name="cycle", payload=cyc_dict)
                stream.emit("annotation", name="bad_type", payload={"obj": object()})
        finally:
            stream.close()

        lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0], parse_constant=_reject_constant)
        assert rec["payload"] == {"a": None, "b": [None, None]}
        warn_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
        assert any("Circular reference detected" in m for m in warn_msgs)
        assert any("not JSON-serializable" in m for m in warn_msgs)

    def test_writer_refresh_skips_config_serialization_and_detects_finalize_mutations(
        self, tmp_path, monkeypatch
    ):
        from pubrun import writer as writer_mod

        class _Run:
            def __init__(self, rdir):
                self.run_dir = rdir
                self.config = {"core": {"artifact_durability": "fsync"}, "x": 1}
                self._finalized = False

            def _finalize_state(self):
                self._finalized = True

            def to_manifest_dict(self):
                return {"run": {"run_id": "ref00001"}}

        run_dir = tmp_path / "refresh_run"
        run = _Run(run_dir)
        w = writer_mod.ArtifactWriter(run)

        calls = []
        real_ser = writer_mod._serialize_config_and_digest

        def _spy_ser(cfg):
            calls.append(dict(cfg))
            return real_ser(cfg)

        monkeypatch.setattr(writer_mod, "_serialize_config_and_digest", _spy_ser)

        assert w.write_startup_manifest() is True
        assert len(calls) == 1

        # Hardware refresh must skip _serialize_config_and_digest completely
        assert w.write_startup_manifest(is_refresh=True) is True
        assert len(calls) == 1

        # In-place mutation must still be detected on finalize
        run.config["x"] = 2
        assert w.write_artifacts() is True
        assert len(calls) == 2
        assert json.loads((run_dir / "config.resolved.json").read_text(encoding="utf-8"))["x"] == 2

    def test_durability_warning_set_capped_at_256(self, monkeypatch):
        from pubrun import writer as writer_mod

        monkeypatch.setattr(writer_mod, "_warned_invalid_durability", set())
        for i in range(300):
            assert (
                writer_mod._resolve_durability(
                    {"core": {"artifact_durability": f"invalid_{i}"}}, stage="startup"
                )
                == "fsync"
            )
        assert isinstance(writer_mod._warned_invalid_durability, set)
        assert len(writer_mod._warned_invalid_durability) == 256
        # .discard() compatibility preserved
        writer_mod._warned_invalid_durability.discard("invalid_0")
        assert len(writer_mod._warned_invalid_durability) == 255
