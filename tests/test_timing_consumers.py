"""Behavioral compatibility and semantic labeling tests for timing consumers (IPD vrr1fv)."""
import asyncio
import contextlib
import io
import json
import os
import time
from pathlib import Path

import pytest

from pubrun.analysis.diff import _normalize_manifest, compare_manifests
from pubrun.analysis.render import print_diff
from pubrun.config import resolve_config
from pubrun.report.diagnostics import print_report
from pubrun.report.methods import generate_report, generate_report_multi
from pubrun.status import (
    RunInfo,
    STATUS_CRASHED,
    STATUS_RUNNING,
    _format_duration_detail,
    _format_elapsed,
    classify_timing_semantics,
    close_out_crashed_run,
    render_inspect,
    scan_runs,
)
from pubrun.tui.widgets.details import _format_subprocess_rows


FIXTURE_MANIFEST_PATH = Path(__file__).resolve().parent / "fixtures" / "sample_manifest.json"


def _load_legacy_fixture():
    return json.loads(FIXTURE_MANIFEST_PATH.read_text(encoding="utf-8"))


def _make_new_monotonic_manifest(
    *,
    workload_seconds: float = 1.234,
    startup_overhead_seconds: float = 0.042,
    finalization_overhead_seconds: float = 0.089,
    hardware_wait_seconds: float = 0.051,
    session_seconds: float = 1.365,
    background_hardware_seconds: float = 2.500,
    subprocesses=None,
):
    return {
        "schema_version": "1.0",
        "manifest_type": "pubrun-manifest",
        "meta_ref": None,
        "run": {
            "run_id": "new12345",
            "library_version": "1.5.0",
            "library_commit": "0123456789abcdef",
            "capture_state": {"status": "complete"},
        },
        "timing": {
            "started_at_utc": 1780250000.0,
            "workload_started_at_utc": 1780250000.042,
            "ended_at_utc": 1780250001.276,
            "finalized_at_utc": 1780250001.365,
            "elapsed_seconds": workload_seconds,
            "workload_seconds": workload_seconds,
            "startup_overhead_seconds": startup_overhead_seconds,
            "finalization_overhead_seconds": finalization_overhead_seconds,
            "session_seconds": session_seconds,
            "hardware_wait_seconds": hardware_wait_seconds,
            "background_hardware_seconds": background_hardware_seconds,
            "duration_clock": "monotonic",
            "elapsed_basis": "workload",
            "interval_scope": "tracked_interval",
            "capture_state": {"status": "complete"},
        },
        "invocation": {
            "argv": ["train.py", "--epochs", "10"],
            "command_line": "train.py --epochs 10",
            "rerun_command": "python train.py --epochs 10",
            "script": {"basename": "train.py"},
            "capture_state": {"status": "complete"},
        },
        "subprocesses": (
            subprocesses
            if subprocesses is not None
            else [
                {
                    "argv": ["echo", "hello"],
                    "started_at_utc": 1780250001.0,
                    "ended_at_utc": 1780249995.0,  # backward wall-clock jump
                    "elapsed_seconds": 0.25,
                    "duration_clock": "monotonic",
                    "exit_code": 0,
                    "capture_state": {"status": "complete"},
                }
            ]
        ),
        "process": {"pid": 22222, "capture_state": {"status": "complete"}},
        "python": {
            "executable": "/usr/bin/python3",
            "version": "3.11.5 (main)",
            "implementation": "cpython",
            "capture_state": {"status": "complete"},
        },
        "packages": {
            "records": [{"name": "numpy", "version": "1.26.0"}],
            "capture_state": {"status": "complete"},
        },
        "environment": {"variables": [], "capture_state": {"status": "complete"}},
        "git": {"commit": "abcdef1234567890", "branch": "main", "dirty": False, "capture_state": {"status": "complete"}},
        "errors": {"records": [], "capture_state": {"status": "complete"}},
        "hardware": {
            "cpu": {"model": "Test CPU", "logical_cores": 8, "architecture": "x86_64"},
            "memory_total_bytes": 16 * 1024**3,
            "gpus": [],
            "capture_state": {"status": "complete"},
        },
        "host": {
            "os_name": "Linux",
            "os_version": "6.1",
            "os_release": "6.1.0",
            "hostname": "test-node",
            "capture_state": {"status": "complete"},
        },
        "resources": {
            "peak_rss_bytes": 100 * 1024**2,
            "peak_cpu_percent": 40.0,
            "capture_state": {"status": "complete"},
        },
        "signals": {"exit_code": 0, "signals_received": [], "capture_state": {"status": "complete"}},
        "status": {"outcome": "completed", "capture_state": {"status": "complete"}},
    }


def _write_run(runs_dir: Path, dirname: str, manifest: dict) -> Path:
    run_dir = runs_dir / dirname
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run_dir


class TestTimingSemanticsClassifierAndFormatting:
    """Unit tests for classify_timing_semantics, _format_duration_detail, and _format_elapsed."""

    def test_format_elapsed_backward_compatibility(self):
        assert _format_elapsed(-10) == "-00:00:10"
        assert _format_elapsed(None) == "unknown"
        assert _format_elapsed(0) == "00:00:00"
        assert _format_elapsed(45.6) == "00:00:46"

    def test_format_duration_detail_precision_and_guards(self):
        assert _format_duration_detail(None) == "unknown"
        assert _format_duration_detail(float("nan")) == "unknown"
        assert _format_duration_detail("bad") == "unknown"
        assert _format_duration_detail(True) == "unknown"
        assert _format_duration_detail(-3.5) == "0.000s"
        assert _format_duration_detail(0.0) == "0.000s"
        assert _format_duration_detail(0.0123) == "0.012s"
        assert _format_duration_detail(59.9) == "59.900s"
        assert _format_duration_detail(65.2) == "00:01:05 (65.2s)"

    def test_classify_all_semantic_paths(self):
        # Running status overrides even a startup manifest carrying monotonic metadata
        live = classify_timing_semantics(
            {"duration_clock": "monotonic", "elapsed_basis": "workload", "elapsed_seconds": None},
            status=STATUS_RUNNING,
        )
        assert live["duration_clock"] == "wall_clock_estimated"
        assert live["elapsed_basis"] == "running_estimate"
        assert live["interval_scope"] == "tracked_interval"
        assert live["label"] == "Elapsed (running, wall-clock estimate)"
        assert live["is_legacy"] is False
        assert live["is_incomplete"] is False

        # New monotonic workload
        mono = classify_timing_semantics(
            {"duration_clock": "monotonic", "elapsed_basis": "workload", "workload_seconds": 0.0, "elapsed_seconds": 0.0}
        )
        assert mono["label"] == "Tracked workload (monotonic)"
        assert mono["is_legacy"] is False
        assert mono["is_incomplete"] is False

        # Session monotonic and non-monotonic
        sess_mono = classify_timing_semantics(
            {"duration_clock": "monotonic", "elapsed_basis": "session", "elapsed_seconds": 5.0}
        )
        assert sess_mono["label"] == "Tracked session (monotonic)"
        assert sess_mono["is_incomplete"] is False

        sess_wall = classify_timing_semantics(
            {"duration_clock": "wall_clock", "elapsed_basis": "session", "elapsed_seconds": 5.0}
        )
        assert sess_wall["label"] == "Tracked session"

        # Crashed estimate
        crashed = classify_timing_semantics(
            {"duration_clock": "wall_clock_estimated", "elapsed_basis": "crashed_estimate", "elapsed_seconds": 12.0}
        )
        assert crashed["label"] == "Estimated elapsed (crashed, wall-clock)"
        assert crashed["is_legacy"] is False
        assert crashed["is_incomplete"] is False

        # Legacy v1.0 manifest (no clock/basis, numeric elapsed)
        legacy = classify_timing_semantics({"started_at_utc": 100.0, "elapsed_seconds": 45.5})
        assert legacy["duration_clock"] == "wall_clock"
        assert legacy["elapsed_basis"] == "wall_clock_legacy"
        assert legacy["label"] == "Elapsed (legacy wall-clock, includes capture)"
        assert legacy["is_legacy"] is True
        assert legacy["is_incomplete"] is False

        # Incomplete, ghost, and corrupt inputs never crash and are not inferred legacy
        for bad in (None, "not-a-dict", 42, {}, {"elapsed_seconds": None}, {"elapsed_seconds": "bad"}, {"elapsed_seconds": True}, {"elapsed_seconds": float("nan")}):
            res = classify_timing_semantics(bad)
            assert res["is_legacy"] is False
            assert res["is_incomplete"] is True
            assert res["label"] == "Elapsed"


class TestLegacyAndMonotonicConsumers:
    """End-to-end consumer tests for legacy v1.0 and new monotonic manifests."""

    def test_legacy_fixture_across_status_inspect_diagnostics_and_methods(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("NO_COLOR", "1")
        legacy = _load_legacy_fixture()
        run_dir = _write_run(tmp_path / "runs", "pubrun-train-legacy-12345-a1b2c3d4", legacy)

        info = RunInfo(run_dir)
        assert info.timing_semantics["is_legacy"] is True
        assert info.timing_semantics["label"] == "Elapsed (legacy wall-clock, includes capture)"
        assert info.elapsed == pytest.approx(45.530865)
        assert info.startup_overhead_seconds is None

        inspect_out = render_inspect(info)
        assert "Elapsed (legacy wall-clock, includes capture): 45.531s" in inspect_out
        assert "tracked interval" in inspect_out.lower()
        assert "Startup overhead" not in inspect_out

        print_report(str(run_dir / "manifest.json"), depth="deep")
        report_out = capsys.readouterr().out
        assert "\033[" not in report_out
        assert "Elapsed (legacy wall-clock, includes capture)" in report_out
        assert "45.531s" in report_out
        assert "tracked interval" in report_out.lower()
        assert "pip install torch (10.0s, wall-clock)" in report_out

        # Methods report reads legacy manifest cleanly without fabricating duration claims
        md = generate_report(legacy, "markdown")
        tex = generate_report(legacy, "latex")
        assert "Computational Methods" in md
        assert "45.53" not in md
        assert "45.53" not in tex

    def test_monotonic_manifest_separates_overheads_without_summing_overlaps(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("NO_COLOR", "1")
        manifest = _make_new_monotonic_manifest(
            workload_seconds=0.500,
            startup_overhead_seconds=0.012,
            finalization_overhead_seconds=0.045,
            hardware_wait_seconds=0.020,
            session_seconds=0.557,
            background_hardware_seconds=2.500,
        )
        run_dir = _write_run(tmp_path / "runs", "pubrun-train-new-22222-new12345", manifest)

        info = RunInfo(run_dir)
        assert info.timing_semantics["is_legacy"] is False
        assert info.timing_semantics["label"] == "Tracked workload (monotonic)"
        assert info.elapsed == pytest.approx(0.500)
        assert info.startup_overhead_seconds == pytest.approx(0.012)
        assert info.finalization_overhead_seconds == pytest.approx(0.045)
        assert info.hardware_wait_seconds == pytest.approx(0.020)
        assert info.session_seconds == pytest.approx(0.557)
        assert info.background_hardware_seconds == pytest.approx(2.500)

        inspect_out = render_inspect(info)
        assert "Tracked workload (monotonic): 0.500s" in inspect_out
        assert "Startup overhead: 0.012s" in inspect_out
        assert "Finalization overhead: 0.045s (includes Hardware wait: 0.020s)" in inspect_out
        assert "Tracked session: 0.557s" in inspect_out
        assert "Background hardware (overlaps workload): 2.500s" in inspect_out
        # Must NOT sum overlapping background hardware (2.5s) into workload (0.5s -> 3.0s)
        assert "3.000s" not in inspect_out
        assert "tracked interval" in inspect_out.lower()
        assert "not full process lifetime" in inspect_out.lower()

        print_report(str(run_dir / "manifest.json"), depth="deep")
        report_out = capsys.readouterr().out
        assert "\033[" not in report_out
        assert "Tracked workload (monotonic) : 0.500s" in report_out
        assert "Startup overhead : 0.012s" in report_out
        assert "Finalization overhead : 0.045s (includes Hardware wait: 0.020s)" in report_out
        assert "Tracked session : 0.557s" in report_out
        assert "Background hardware : 2.500s (overlaps workload)" in report_out
        assert "3.000s" not in report_out
        assert "tracked interval" in report_out.lower()
        assert "not full application lifetime" in report_out.lower()
        # Monotonic subprocess duration preferred over backward UTC timestamps
        assert "echo hello (0.25s, monotonic)" in report_out

        # Methods single and multi handle legacy + new manifests without overstating timing precision
        legacy = _load_legacy_fixture()
        md_new = generate_report(manifest, "markdown")
        md_multi = generate_report_multi([manifest, legacy], "markdown")
        tex_multi = generate_report_multi([manifest, legacy], "latex")
        for text in (md_new, md_multi, tex_multi):
            assert "0.500" not in text
            assert "2.500" not in text
            assert "monotonic" not in text.lower()
            assert "full application lifetime" not in text.lower()

    def test_zero_second_monotonic_manifest_and_subprocess(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("NO_COLOR", "1")
        manifest = _make_new_monotonic_manifest(
            workload_seconds=0.0,
            startup_overhead_seconds=0.0,
            finalization_overhead_seconds=0.0,
            hardware_wait_seconds=0.0,
            session_seconds=0.0,
            background_hardware_seconds=0.0,
            subprocesses=[
                {
                    "argv": ["true"],
                    "started_at_utc": 1780250000.0,
                    "ended_at_utc": 1780250000.0,
                    "elapsed_seconds": 0.0,
                    "duration_clock": "monotonic",
                    "exit_code": 0,
                    "capture_state": {"status": "complete"},
                }
            ],
        )
        run_dir = _write_run(tmp_path / "runs", "pubrun-zero-1-zero0001", manifest)
        info = RunInfo(run_dir)
        assert info.elapsed == 0.0
        assert info.timing_semantics["is_incomplete"] is False
        assert "Tracked workload (monotonic): 0.000s" in render_inspect(info)

        print_report(str(run_dir / "manifest.json"), depth="deep")
        out = capsys.readouterr().out
        assert "Tracked workload (monotonic) : 0.000s" in out
        assert "true (0.0s, monotonic)" in out

    def test_real_producer_manifest_consumed_end_to_end(self, tmp_path, monkeypatch, capsys):
        """Exercise a real Run() manifest from e1fwy2 + 8co0wy through all consumers."""
        import sys
        import pubrun.noauto as pubrun

        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        run = pubrun.start(
            console={"capture_mode": "off"},
            events={"enabled": False},
            capture={"resources": {"depth": "off"}, "signals": {"enabled": False}},
        )
        pubrun.subprocess.run([sys.executable, "-c", "pass"], check=True)
        run_dir = run.run_dir
        run.stop()

        info = RunInfo(run_dir)
        assert info.timing_semantics["label"] == "Tracked workload (monotonic)"
        assert info.elapsed is not None and info.elapsed >= 0.0
        assert info.startup_overhead_seconds is not None and info.startup_overhead_seconds >= 0.0
        inspect_out = render_inspect(info)
        assert "Tracked workload (monotonic):" in inspect_out
        assert "Startup overhead:" in inspect_out

        print_report(str(run_dir / "manifest.json"), depth="deep")
        report_out = capsys.readouterr().out
        assert "Tracked workload (monotonic)" in report_out
        assert "monotonic)" in report_out


class TestLiveRunningAndCrashedCloseout:
    """Live lock clamping, startup-manifest enrichment safety, and crashed closeout."""

    def test_live_lock_enriched_with_startup_manifest_uses_running_estimate_and_clamps_local(
        self, tmp_path, monkeypatch
    ):
        from pubrun import status as status_mod

        run_dir = tmp_path / "runs" / "pubrun-live-1234-live0001"
        run_dir.mkdir(parents=True)
        # Future started_at_utc simulates a backward wall-clock jump while process is running
        future_start = time.time() + 120.0
        lock_data = {
            "pid": os.getpid(),
            "started_at_utc": future_start,
            "script": "live.py",
            "run_id": "live0001",
            "hostname": status_mod.get_hostname(),
            "cwd": str(tmp_path),
        }
        (run_dir / ".pubrun.lock").write_text(json.dumps(lock_data), encoding="utf-8")
        # Startup manifest carrying monotonic workload metadata on disk
        startup_manifest = {
            "schema_version": "1.0",
            "run": {"run_id": "live0001"},
            "status": {"outcome": "running"},
            "timing": {
                "started_at_utc": future_start,
                "ended_at_utc": None,
                "elapsed_seconds": None,
                "workload_seconds": None,
                "duration_clock": "monotonic",
                "elapsed_basis": "workload",
                "interval_scope": "tracked_interval",
                "capture_state": {"status": "partial"},
            },
            "git": {"commit": "deadbeef1234"},
        }
        (run_dir / "manifest.json").write_text(json.dumps(startup_manifest), encoding="utf-8")

        monkeypatch.setattr(status_mod, "is_same_process", lambda *a, **kw: True)
        info = RunInfo(run_dir)
        assert info.status == STATUS_RUNNING
        assert info.elapsed == 0.0
        assert info.timing_semantics["elapsed_basis"] == "running_estimate"
        assert info.timing_semantics["duration_clock"] == "wall_clock_estimated"
        assert info.timing_semantics["label"] == "Elapsed (running, wall-clock estimate)"
        assert info.git_commit == "deadbeef1234"

        inspect_out = render_inspect(info)
        assert "Elapsed (running, wall-clock estimate): 0.000s" in inspect_out
        assert "Tracked workload (monotonic)" not in inspect_out

    def test_remote_host_live_lock_clamps_negative_elapsed(self, tmp_path):
        run_dir = tmp_path / "runs" / "pubrun-remote-99-rem00001"
        run_dir.mkdir(parents=True)
        future_start = time.time() + 60.0
        lock_data = {
            "pid": 99999,
            "started_at_utc": future_start,
            "script": "train.py",
            "run_id": "rem00001",
            "hostname": "remote-cluster-node-never-local",
        }
        (run_dir / ".pubrun.lock").write_text(json.dumps(lock_data), encoding="utf-8")

        info = RunInfo(run_dir)
        assert info.status == STATUS_RUNNING
        assert info.elapsed == 0.0
        assert info.timing_semantics["label"] == "Elapsed (running, wall-clock estimate)"

    def test_crashed_closeout_backward_mtime_clamps_and_preserves_workload_none(self, tmp_path):
        run_dir = tmp_path / "runs" / "pubrun-crash-1-crsh0001"
        run_dir.mkdir(parents=True)
        manifest = {
            "schema_version": "1.0",
            "run": {"run_id": "crsh0001"},
            "status": {"outcome": "running"},
            "timing": {
                "started_at_utc": 2000.0,
                "ended_at_utc": None,
                "elapsed_seconds": None,
                "workload_seconds": None,
                "duration_clock": "monotonic",
                "elapsed_basis": "workload",
                "interval_scope": "tracked_interval",
                "capture_state": {"status": "partial"},
            },
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        lock_path = run_dir / ".pubrun.lock"
        lock_data = {"run_id": "crsh0001", "pid": 999999, "started_at_utc": 2000.0}
        lock_path.write_text(json.dumps(lock_data), encoding="utf-8")
        # Set lock mtime BEFORE started_at_utc to simulate clock skew/rollback
        os.utime(lock_path, (1500.0, 1500.0))

        close_out_crashed_run(run_dir, lock_data)
        updated = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        t = updated["timing"]
        assert updated["status"]["outcome"] == "crashed"
        assert t["ended_at_utc"] == pytest.approx(1500.0)
        assert t["elapsed_seconds"] == 0.0
        assert t["workload_seconds"] is None
        assert t["duration_clock"] == "wall_clock_estimated"
        assert t["elapsed_basis"] == "crashed_estimate"
        assert t["interval_scope"] == "tracked_interval"
        assert t["capture_state"] == {"status": "partial"}

        info = RunInfo(run_dir)
        assert info.status == STATUS_CRASHED
        assert info.elapsed == 0.0
        assert info.timing_semantics["label"] == "Estimated elapsed (crashed, wall-clock)"
        assert "Estimated elapsed (crashed, wall-clock): 0.000s" in render_inspect(info)

    def test_crashed_closeout_missing_or_corrupt_started_at_degrades_to_none(self, tmp_path):
        run_dir = tmp_path / "runs" / "pubrun-crash-bad-crsh0002"
        run_dir.mkdir(parents=True)
        manifest = {
            "schema_version": "1.0",
            "run": {"run_id": "crsh0002"},
            "status": {"outcome": "running"},
            "timing": {"started_at_utc": "not-a-number"},
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        close_out_crashed_run(run_dir, {"run_id": "crsh0002"})
        updated = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        t = updated["timing"]
        assert t["elapsed_seconds"] is None
        assert t["duration_clock"] is None
        assert t["elapsed_basis"] is None
        assert t["interval_scope"] == "tracked_interval"
        assert t["capture_state"] == {"status": "partial"}

    def test_crashed_closeout_lock_only_fallback_sets_timing_fields(self, tmp_path):
        run_dir = tmp_path / "runs" / "pubrun-lockonly-1-crsh0003"
        run_dir.mkdir(parents=True)
        lock_data = {"run_id": "crsh0003", "pid": 999999, "started_at_utc": 1700000000.0}
        (run_dir / ".pubrun.lock").write_text(json.dumps(lock_data), encoding="utf-8")

        close_out_crashed_run(run_dir, lock_data)
        updated = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        t = updated["timing"]
        assert t["ended_at_utc"] is None
        assert t["elapsed_seconds"] is None
        assert t["duration_clock"] is None
        assert t["elapsed_basis"] is None
        assert t["interval_scope"] == "tracked_interval"
        assert t["capture_state"] == {"status": "partial"}


class TestIncompleteAndMalformedTiming:
    """Incomplete, null, and corrupt timing inputs degrade cleanly across CLI and helpers."""

    @pytest.mark.parametrize(
        "timing_val",
        [
            {},
            None,
            "corrupt-string",
            {"started_at_utc": None, "ended_at_utc": None, "elapsed_seconds": None},
            {"started_at_utc": 1e30, "elapsed_seconds": "bad"},
            {"started_at_utc": True, "elapsed_seconds": False},
            {"started_at_utc": 1780250000.0, "elapsed_seconds": None, "workload_seconds": None, "duration_clock": "monotonic", "elapsed_basis": "workload"},
        ],
    )
    def test_status_inspect_and_print_report_handle_malformed_timing(self, tmp_path, monkeypatch, capsys, timing_val):
        monkeypatch.setenv("NO_COLOR", "1")
        manifest = {
            "run": {"run_id": "badtime1"},
            "status": {"outcome": "completed"},
            "timing": timing_val,
            "invocation": {"script": {"basename": "bad.py"}, "argv": ["bad.py"]},
            "subprocesses": "not-a-list",
        }
        run_dir = _write_run(tmp_path / "runs", "pubrun-bad-1-badtime1", manifest)
        info = RunInfo(run_dir)
        assert info.elapsed is None
        assert info.timing_semantics["is_incomplete"] is True

        inspect_out = render_inspect(info)
        assert "unknown" in inspect_out

        print_report(str(run_dir / "manifest.json"), depth="deep")
        report_out = capsys.readouterr().out
        assert "unknown" in report_out
        assert "\033[" not in report_out

    def test_subprocess_rows_helper_guards_and_fallback(self):
        assert _format_subprocess_rows(None) == []
        assert _format_subprocess_rows("bad") == []

        rows = _format_subprocess_rows(
            [
                None,
                "not-a-dict",
                {
                    "argv": ["python", 42],
                    "started_at_utc": 1780250010.0,
                    "ended_at_utc": 1780250000.0,  # backward wall clock
                    "elapsed_seconds": 0.125,
                    "duration_clock": "monotonic",
                    "exit_code": 0,
                },
                {
                    "argv": ["pip", "install", "torch"],
                    "started_at_utc": 1715280010.0,
                    "ended_at_utc": 1715280020.0,
                    "exit_code": 0,
                },
                {
                    "argv": ["sleep", "10"],
                    "started_at_utc": 1715280010.0,
                    "ended_at_utc": None,
                    "exit_code": None,
                },
            ]
        )
        assert len(rows) == 3
        assert rows[0][0] == "python 42"
        assert rows[0][2] == "0.125s (mono)"
        assert rows[0][3] == "0"
        assert rows[1][0] == "pip install torch"
        assert rows[1][2] == "10.000s (wall)"
        assert rows[2][2] == "-"
        assert rows[2][3] == "Running"


class TestMixedTimingDiffs:
    """Mixed legacy vs monotonic manifest diffs across engine, inline, and table renderers."""

    def _render_diff(self, report, **kw):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_diff(report, **kw)
        return buf.getvalue()

    def test_mixed_legacy_vs_new_differing_elapsed_attaches_note_and_renders(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        legacy = _load_legacy_fixture()
        new_m = _make_new_monotonic_manifest(workload_seconds=12.5)

        diff = compare_manifests(legacy, new_m, ignores=[], depth="deep")
        mod_elapsed = diff["modified"]["timing.elapsed_seconds"]
        assert mod_elapsed["type"] == "standard"
        assert mod_elapsed["old"] == pytest.approx(45.530865)
        assert mod_elapsed["new"] == pytest.approx(12.5)
        assert (
            mod_elapsed["note"]
            == "timing definition changed (wall_clock_legacy/wall_clock -> workload/monotonic)"
        )
        assert diff["modified"]["timing.duration_clock"]["old"] == "wall_clock"
        assert diff["modified"]["timing.duration_clock"]["new"] == "monotonic"
        assert diff["modified"]["timing.elapsed_basis"]["old"] == "wall_clock_legacy"
        assert diff["modified"]["timing.elapsed_basis"]["new"] == "workload"

        inline_out = self._render_diff(diff, no_color=True, depth="deep")
        assert "\033[" not in inline_out
        assert "note: timing definition changed (wall_clock_legacy/wall_clock -> workload/monotonic)" in inline_out

        table_out = self._render_diff(diff, no_color=True, table=True)
        assert "\033[" not in table_out
        assert "timing definition changed (wall_clock_legacy/wall_clock -> workload/monotonic)" in table_out

    def test_mixed_legacy_vs_new_equal_elapsed_still_surfaces_definition_change(self):
        legacy = _load_legacy_fixture()
        new_m = _make_new_monotonic_manifest(workload_seconds=45.530865)

        diff = compare_manifests(legacy, new_m, ignores=[], depth="deep")
        assert "timing.elapsed_seconds" not in diff["modified"]
        assert diff["modified"]["timing.duration_clock"] == {
            "type": "standard",
            "old": "wall_clock",
            "new": "monotonic",
        }
        assert diff["modified"]["timing.elapsed_basis"] == {
            "type": "standard",
            "old": "wall_clock_legacy",
            "new": "workload",
        }

    def test_default_basic_and_standard_still_ignore_timing(self):
        conf = resolve_config().get("diff", {})
        legacy = _load_legacy_fixture()
        new_m = _make_new_monotonic_manifest(workload_seconds=12.5)

        for depth, key in (("basic", "ignore_basic"), ("standard", "ignore_standard")):
            diff = compare_manifests(legacy, new_m, ignores=conf.get(key, []), depth=depth)
            all_keys = set(diff["added"]) | set(diff["removed"]) | set(diff["modified"])
            assert not any(k.startswith("timing") for k in all_keys)

    def test_normalize_respects_per_key_timing_ignores(self):
        legacy = _load_legacy_fixture()
        flat = _normalize_manifest(legacy, ignores=["timing.duration_clock"], depth="deep")
        assert "timing.duration_clock" not in flat
        assert flat["timing.elapsed_basis"] == "wall_clock_legacy"


class TestTuiTimingViews:
    """Textual Pilot tests for RunDetailsView and DiffView (skipped when textual absent)."""

    def test_tui_details_legacy_monotonic_incomplete_and_lock_only(self, tmp_path):
        pytest.importorskip("textual")
        from textual.widgets import DataTable
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.details import RunDetailsView

        runs_dir = tmp_path / "runs"
        legacy_dir = _write_run(runs_dir, "pubrun-leg-1-a1b2c3d4", _load_legacy_fixture())
        new_dir = _write_run(
            runs_dir,
            "pubrun-new-2-new12345",
            _make_new_monotonic_manifest(
                workload_seconds=0.500,
                startup_overhead_seconds=0.015,
                finalization_overhead_seconds=0.040,
                hardware_wait_seconds=0.025,
                session_seconds=0.555,
                background_hardware_seconds=1.800,
            ),
        )
        incomplete_dir = _write_run(
            runs_dir,
            "pubrun-inc-3-inc12345",
            {
                "run": {"run_id": "inc12345"},
                "status": {"outcome": "completed"},
                "timing": {"started_at_utc": 1780250000.0, "elapsed_seconds": None},
            },
        )
        lock_only_dir = runs_dir / "pubrun-lockonly-4-lck12345"
        lock_only_dir.mkdir(parents=True)
        (lock_only_dir / ".pubrun.lock").write_text(
            json.dumps(
                {
                    "run_id": "lck12345",
                    "pid": 999999,
                    "started_at_utc": time.time() - 50.0,
                    "script": "dead.py",
                }
            ),
            encoding="utf-8",
        )

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs_dir))
            async with app.run_test() as pilot:
                details = app.query_one("#details-view", RunDetailsView)
                sub_table = details.query_one("#subprocesses-table", DataTable)

                # Verify widened Elapsed column
                elapsed_cols = [c for c in sub_table.columns.values() if str(c.label) == "Elapsed"]
                assert elapsed_cols and elapsed_cols[0].width == 18

                # 1. Legacy run
                details.display_run(RunInfo(legacy_dir))
                await pilot.pause()
                gen_legacy = str(details.query_one("#lbl-general-info").render())
                assert "Elapsed (legacy wall-clock, includes capture):" in gen_legacy
                assert "45.531s" in gen_legacy
                assert "tracked interval" in gen_legacy.lower()
                assert sub_table.row_count == 1
                assert sub_table.get_row_at(0)[2] == "10.000s (wall)"

                # 2. New monotonic run
                details.display_run(RunInfo(new_dir))
                await pilot.pause()
                gen_new = str(details.query_one("#lbl-general-info").render())
                assert "Tracked workload (monotonic):" in gen_new
                assert "0.500s" in gen_new
                assert "Startup overhead:" in gen_new and "0.015s" in gen_new
                assert "Finalization overhead:" in gen_new and "0.040s" in gen_new
                assert "Hardware wait: 0.025s" in gen_new
                assert "Tracked session:" in gen_new and "0.555s" in gen_new
                assert "Background hardware (overlaps workload):" in gen_new and "1.800s" in gen_new
                assert "2.300s" not in gen_new  # overlaps not summed
                assert sub_table.row_count == 1
                assert sub_table.get_row_at(0)[2] == "0.250s (mono)"

                # 3. Incomplete timing renders '-'
                details.display_run(RunInfo(incomplete_dir))
                await pilot.pause()
                gen_inc = str(details.query_one("#lbl-general-info").render())
                assert "Elapsed: -" in gen_inc

                # 4. Lock-only crashed run (r.manifest is None) renders safely
                lock_info = RunInfo(lock_only_dir)
                assert lock_info.manifest is None
                details.display_run(lock_info)
                await pilot.pause()
                gen_lock = str(details.query_one("#lbl-general-info").render())
                assert "Elapsed: -" in gen_lock

        asyncio.run(_drive())

    def test_tui_diff_view_passes_depth_and_renders_timing_note(self, tmp_path):
        pytest.importorskip("textual")
        from textual.widgets import RichLog, Select, TabbedContent
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.diff import DiffView

        runs_dir = tmp_path / "runs"
        legacy_dir = _write_run(runs_dir, "pubrun-leg-1-a1b2c3d4", _load_legacy_fixture())
        new_dir = _write_run(
            runs_dir,
            "pubrun-new-2-new12345",
            _make_new_monotonic_manifest(workload_seconds=12.5),
        )

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs_dir))
            async with app.run_test(size=(120, 40)) as pilot:
                app.query_one("#workspace-tabs", TabbedContent).active = "tab-diff"
                await pilot.pause()
                diff_view = app.query_one("#diff-view", DiffView)
                diff_view.populate_dropdowns(scan_runs(str(runs_dir)))
                diff_view.query_one("#select-diff-a", Select).value = str(legacy_dir)
                diff_view.query_one("#select-diff-b", Select).value = str(new_dir)
                diff_view.query_one("#select-diff-depth", Select).value = "deep"
                await pilot.pause()
                diff_view.run_difference()
                await pilot.pause()

                log = diff_view.query_one("#diff-output-area", RichLog)
                rendered = "\n".join(line.text for line in log.lines)
                assert "timing.elapsed_seconds" in rendered
                assert (
                    "Note: timing definition changed (wall_clock_legacy/wall_clock -> workload/monotonic)"
                    in rendered
                )
                # Confirm depth="deep" was forwarded (derived invocation keys are kept only at deep)
                assert "invocation.command_line" in rendered
                assert "timing.duration_clock" in rendered

        asyncio.run(_drive())
