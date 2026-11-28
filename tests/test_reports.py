"""Tests for report generation: methods, diagnostics utilities, and hydration."""
import json
import os
import subprocess
import sys
import time
import pytest
from pathlib import Path

from pubrun.report.methods import generate_report, extract_highlighted_packages, bytes_to_gb
from pubrun.report.utils import hydrate_manifest


class TestBytesToGb:

    def test_zero(self):
        assert bytes_to_gb(0) == 0.0

    def test_none(self):
        assert bytes_to_gb(None) == 0.0

    def test_one_gb(self):
        assert bytes_to_gb(1024 ** 3) == 1.0

    def test_32_gb(self):
        assert bytes_to_gb(32 * 1024 ** 3) == 32.0

    def test_fractional(self):
        result = bytes_to_gb(int(1.5 * 1024 ** 3))
        assert 1.4 <= result <= 1.6


class TestExtractHighlightedPackages:

    def test_detects_torch(self, sample_manifest):
        found = extract_highlighted_packages(sample_manifest)
        names = [f.split(" ")[0] for f in found]
        assert "torch" in names

    def test_detects_numpy(self, sample_manifest):
        found = extract_highlighted_packages(sample_manifest)
        names = [f.split(" ")[0] for f in found]
        assert "numpy" in names

    def test_includes_version(self, sample_manifest):
        found = extract_highlighted_packages(sample_manifest)
        torch_entry = [f for f in found if f.startswith("torch")]
        assert len(torch_entry) == 1
        assert "(v2.0.1)" in torch_entry[0]

    def test_empty_packages(self):
        manifest = {"packages": {"records": []}}
        assert extract_highlighted_packages(manifest) == []

    def test_no_packages_section(self):
        assert extract_highlighted_packages({}) == []

    def test_case_insensitive(self):
        manifest = {"packages": {"records": [{"name": "NumPy", "version": "1.24"}]}}
        found = extract_highlighted_packages(manifest)
        assert len(found) == 1


class TestGenerateReportMarkdown:

    def test_contains_computational_methods(self, sample_manifest):
        text = generate_report(sample_manifest, "markdown")
        assert "Computational Methods" in text

    def test_contains_os_name(self, sample_manifest):
        text = generate_report(sample_manifest, "markdown")
        assert "Linux" in text

    def test_contains_cpu(self, sample_manifest):
        text = generate_report(sample_manifest, "markdown")
        assert "i7-12700H" in text

    def test_contains_ram(self, sample_manifest):
        text = generate_report(sample_manifest, "markdown")
        assert "32.0" in text

    def test_contains_python_version(self, sample_manifest):
        text = generate_report(sample_manifest, "markdown")
        assert "3.10.12" in text

    def test_contains_git_commit(self, sample_manifest):
        text = generate_report(sample_manifest, "markdown")
        # First 8 chars of the commit
        assert "a1b2c3d4" in text

    def test_contains_packages(self, sample_manifest):
        text = generate_report(sample_manifest, "markdown")
        assert "torch" in text or "numpy" in text

    def test_contains_pubrun_reference(self, sample_manifest):
        text = generate_report(sample_manifest, "markdown")
        assert "pubrun" in text


class TestGenerateReportLatex:

    def test_contains_subsection(self, sample_manifest):
        text = generate_report(sample_manifest, "latex")
        assert "\\subsection" in text

    def test_escapes_underscores(self):
        manifest = {
            "host": {"os_name": "Linux_WSL"},
            "hardware": {"cpu": {"model": "cpu"}, "memory_total_bytes": 0},
            "python": {"version": "3.10", "implementation": "cpython"},
            "git": {"commit": "abcdef1234567890", "remote_url": {"value": None}},
            "packages": {"records": []}
        }
        text = generate_report(manifest, "latex")
        assert "Linux\\_WSL" in text

    def test_contains_pubrun_citation(self, sample_manifest):
        text = generate_report(sample_manifest, "latex")
        # The methods paragraph names pubrun (now with its version) and cites it.
        assert "pubrun" in text
        assert "\\cite{fariello_pubrun_2026}" in text


class TestHydrateManifest:

    def test_no_meta_ref(self, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        manifest = {"meta_ref": None, "host": {"os": "Linux"}}
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        result, warnings = hydrate_manifest(str(manifest_path), manifest)
        assert result == manifest
        assert len(warnings) == 0

    def test_warns_on_missing_meta_ref(self, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        manifest = {"meta_ref": "missing_parent.json"}
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        result, warnings = hydrate_manifest(str(manifest_path), manifest)
        assert len(warnings) >= 1
        assert "not found" in warnings[0].lower() or "missing" in warnings[0].lower() or "Security" in warnings[0]

    def test_warns_on_non_json_meta_ref(self, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        manifest = {"meta_ref": "/etc/passwd"}
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        result, warnings = hydrate_manifest(str(manifest_path), manifest)
        assert len(warnings) >= 1
        assert "Security" in warnings[0] or "security" in warnings[0].lower()

    def test_hydrates_from_valid_parent(self, tmp_path):
        # Create parent meta with hardware data
        parent_data = {
            "hardware": {"cpu": {"model": "i9-13900K"}, "memory_total_bytes": 68719476736,
                         "capture_state": {"status": "complete"}}
        }
        parent_path = tmp_path / "meta.json"
        parent_path.write_text(json.dumps(parent_data), encoding="utf-8")

        # Create child manifest with suppressed hardware section referencing parent
        manifest = {
            "meta_ref": "meta.json",
            "hardware": {"capture_state": {"status": "suppressed"}}
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result, warnings = hydrate_manifest(str(manifest_path), manifest)
        # Suppressed hardware section should be hydrated from parent
        assert result.get("hardware", {}).get("cpu", {}).get("model") == "i9-13900K"
        assert result.get("hardware", {}).get("is_hydrated") is True


class TestGenerateReportDegradedManifests:
    """Test generate_report() with missing or empty manifest sections."""

    def test_missing_git_section(self):
        """No git section produces 'unknown' commit in output."""
        manifest = {"host": {"os_name": "Linux"}, "python": {"version": "3.11.0"}}
        result = generate_report(manifest)
        assert "unknown" in result

    def test_git_commit_none(self):
        """git.commit = None uses 'unavailable' (truncated to 8 chars in output)."""
        manifest = {"host": {"os_name": "Linux"}, "git": {"commit": None}, "python": {"version": "3.11.0"}}
        result = generate_report(manifest)
        # "unavailable"[:8] = "unavaila" due to template truncation
        assert "unavaila" in result

    def test_git_commit_empty_string(self):
        """git.commit = '' uses 'unavailable' (truncated to 8 chars in output)."""
        manifest = {"host": {"os_name": "Linux"}, "git": {"commit": ""}, "python": {"version": "3.11.0"}}
        result = generate_report(manifest)
        assert "unavaila" in result

    def test_missing_hardware_section(self):
        """No hardware section uses 'unknown CPU'."""
        manifest = {"host": {"os_name": "Linux"}, "python": {"version": "3.11.0"}, "git": {"commit": "abc12345"}}
        result = generate_report(manifest)
        assert "unknown CPU" in result

    def test_empty_python_version(self):
        """Empty python version renders explicit unknown version and implementation."""
        manifest = {"host": {"os_name": "Linux"}, "python": {"version": ""}, "git": {"commit": "abc12345"}}
        result = generate_report(manifest)
        assert "Python unknown (Unknown)" in result

    def test_twelve_non_highlighted_packages_truncation(self):
        """More than 10 non-highlighted packages truncate after the first 10 with total count."""
        records = [{"name": f"custom-pkg-{i:02d}", "version": f"1.{i}.0"} for i in range(1, 13)]
        manifest = {
            "host": {"os_name": "Linux"},
            "hardware": {"cpu": {"model": "EPYC"}, "memory_total_bytes": 16 * 1024 ** 3},
            "python": {"version": "3.11.0", "implementation": "cpython"},
            "git": {"commit": "abc12345"},
            "packages": {"records": records, "capture_state": {"status": "complete"}},
        }
        result = generate_report(manifest)
        assert "and 2 additional packages (12 total)." in result
        assert "custom-pkg-01 (v1.1.0)" in result
        assert "custom-pkg-10 (v1.10.0)" in result
        assert "custom-pkg-11" not in result

    def test_missing_packages_section(self):
        """No packages section uses 'Standard library dependencies'."""
        manifest = {"host": {"os_name": "Linux"}, "python": {"version": "3.11.0"}, "git": {"commit": "abc12345"}}
        result = generate_report(manifest)
        assert "Standard library dependencies" in result

    def test_empty_packages_records(self):
        """Empty packages.records uses 'Standard library dependencies'."""
        manifest = {
            "host": {"os_name": "Linux"}, "python": {"version": "3.11.0"},
            "git": {"commit": "abc12345"}, "packages": {"records": []}
        }
        result = generate_report(manifest)
        assert "Standard library dependencies" in result

    def test_latex_format_with_underscores_in_remote_url(self):
        """LaTeX format escapes underscores in git remote URL."""
        manifest = {
            "host": {"os_name": "Linux"}, "python": {"version": "3.11.0"},
            "git": {"commit": "abc12345", "remote_url": {"value": "git@github.com:user/my_project.git"}}
        }
        result = generate_report(manifest, format_type="latex")
        assert "\\_" in result  # underscores escaped
        assert "my_project" not in result.replace("\\_", "XX")  # raw underscore gone

    def test_missing_host_section(self):
        """No host section uses 'an unknown OS'."""
        manifest = {"python": {"version": "3.11.0"}, "git": {"commit": "abc12345"}}
        result = generate_report(manifest)
        assert "unknown OS" in result


class TestGenerateMetaSnapshotUnit:
    """Unit tests for generate_meta_snapshot() -- structure and content."""

    def test_produces_valid_json_file(self, tmp_path, capsys):
        """generate_meta_snapshot writes valid JSON to the specified path."""
        from pubrun.report.meta_snapshot import generate_meta_snapshot
        out_path = str(tmp_path / "meta.json")
        generate_meta_snapshot(out_path, "basic")

        assert (tmp_path / "meta.json").exists()
        with open(tmp_path / "meta.json", "r") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_manifest_type_is_meta_snapshot(self, tmp_path, capsys):
        """manifest_type field is 'pubrun-meta-snapshot'."""
        from pubrun.report.meta_snapshot import generate_meta_snapshot
        out_path = str(tmp_path / "meta.json")
        generate_meta_snapshot(out_path, "basic")

        with open(tmp_path / "meta.json", "r") as f:
            data = json.load(f)
        assert data["manifest_type"] == "pubrun-meta-snapshot"

    def test_required_keys_present(self, tmp_path, capsys):
        """All required top-level keys are present."""
        from pubrun.report.meta_snapshot import generate_meta_snapshot
        out_path = str(tmp_path / "meta.json")
        generate_meta_snapshot(out_path, "deep")

        with open(tmp_path / "meta.json", "r") as f:
            data = json.load(f)

        required = ["manifest_type", "timing", "hardware", "python", "packages", "git", "environment", "host"]
        for key in required:
            assert key in data, f"Missing required key: {key}"

    def test_timing_has_started_at(self, tmp_path, capsys):
        """timing.started_at_utc is a recent timestamp."""
        from pubrun.report.meta_snapshot import generate_meta_snapshot
        out_path = str(tmp_path / "meta.json")
        generate_meta_snapshot(out_path, "basic")

        with open(tmp_path / "meta.json", "r") as f:
            data = json.load(f)
        assert isinstance(data["timing"]["started_at_utc"], float)
        assert data["timing"]["started_at_utc"] > time.time() - 60

    def test_default_output_path(self, tmp_path, monkeypatch, capsys):
        """Empty output_path defaults to cwd/runs/meta.json."""
        from pubrun.report.meta_snapshot import generate_meta_snapshot
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        generate_meta_snapshot("", "basic")

        default_path = tmp_path / "runs" / "meta.json"
        assert default_path.exists()


class TestPrintReportUnit:
    """Unit tests for print_report() at each depth level."""

    def _make_manifest(self, tmp_path):
        """Create a minimal manifest for testing."""
        manifest = {
            "schema_version": "1.0",
            "manifest_type": "pubrun-manifest",
            "run": {"run_id": "test1234"},
            "timing": {"started_at_utc": 1780250000.0, "ended_at_utc": 1780250060.0, "elapsed_seconds": 60.0},
            "invocation": {"argv": ["train.py", "--lr", "0.01"], "script": {"basename": "train.py"}},
            "status": {"outcome": "completed", "capture_state": {"status": "complete"}},
            "python": {"version": "3.11.5 (CPython)", "capture_state": {"status": "complete"}},
            "git": {"commit": "abcdef1234567890", "branch": "main", "dirty": False, "capture_state": {"status": "complete"}},
            "hardware": {"cpu": {"model": "Intel i9-13900K"}, "memory_total_bytes": 34359738368, "capture_state": {"status": "complete"}},
            "host": {"os_name": "Linux", "hostname": "gpu-node-01", "capture_state": {"status": "complete"}},
            "packages": {"records": [{"name": "torch", "version": "2.0.1"}], "capture_state": {"status": "complete"}},
            "process": {"pid": 12345, "capture_state": {"status": "complete"}},
            "environment": {"variables": [], "capture_state": {"status": "complete"}},
            "capture": {"output_base_dir": str(tmp_path), "capture_state": {"status": "complete"}},
            "signals": {"signals_received": [], "exit_code": 0, "capture_state": {"status": "complete"}},
            "errors": {"records": [], "capture_state": {"status": "complete"}},
            "config": {"capture_state": {"status": "complete"}},
            "resources": {"capture_state": {"status": "suppressed"}},
            "console": {},
            "subprocesses": [],
            "meta_ref": None,
        }
        run_dir = tmp_path / "runs" / "pubrun-test"
        run_dir.mkdir(parents=True)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return str(manifest_path)

    def test_basic_depth_shows_timing(self, tmp_path, capsys, monkeypatch):
        """Basic depth includes timing information."""
        from pubrun.report.diagnostics import print_report
        monkeypatch.setenv("NO_COLOR", "1")
        manifest_path = self._make_manifest(tmp_path)
        print_report(manifest_path, "basic")
        output = capsys.readouterr().out
        assert "Status      : completed (0)" in output
        assert "Elapsed (legacy wall-clock, includes capture) : 00:01:00 (60.0s)" in output
        assert not any("Git Commit" in line for line in output.splitlines())

    def test_standard_depth_shows_git(self, tmp_path, capsys, monkeypatch):
        """Standard depth includes git commit."""
        from pubrun.report.diagnostics import print_report
        monkeypatch.setenv("NO_COLOR", "1")
        manifest_path = self._make_manifest(tmp_path)
        print_report(manifest_path, "standard")
        output = capsys.readouterr().out
        assert "Git Commit  : abcdef12 (unknown origin)" in output
        assert "Packages    : 1 recorded" in output
        assert "[ Packages ]" not in output

    def test_deep_depth_shows_packages(self, tmp_path, capsys, monkeypatch):
        """Deep depth includes package listings."""
        from pubrun.report.diagnostics import print_report
        monkeypatch.setenv("NO_COLOR", "1")
        manifest_path = self._make_manifest(tmp_path)
        print_report(manifest_path, "deep")
        output = capsys.readouterr().out
        assert "[ Packages ]" in output
        assert "torch==2.0.1" in output


class TestResourceMonitoring:
    """Unit tests for drawing utilization graphs and printing resources report."""

    def test_draw_ascii_chart_unicode(self, capsys, monkeypatch):
        from pubrun.report.diagnostics import draw_ascii_chart
        # Force Unicode support
        monkeypatch.setattr("pubrun.report.diagnostics._supports_unicode", lambda stream: True)

        data = [10.0, 20.0, 50.0, 90.0]
        timestamps = [100.0, 110.0, 120.0, 130.0]
        draw_ascii_chart(data, timestamps, "Test Chart", "%", height=5, width=20, use_color=False, use_utc=True)
        output = capsys.readouterr().out

        # Verify title, labels and Unicode border characters
        assert "Test Chart" in output
        assert "└" in output
        assert "│" in output
        assert "─" in output
        assert "█" in output
        assert "Timeline" in output
        assert "Elapsed" in output
        assert "1970-01-01 00:01:40Z" in output
        assert "1970-01-01 00:02:10Z" in output
        assert "00:00:00" in output
        assert "00:00:30" in output

    def test_draw_ascii_chart_ascii_fallback(self, capsys, monkeypatch):
        from pubrun.report.diagnostics import draw_ascii_chart
        # Force non-Unicode support
        monkeypatch.setattr("pubrun.report.diagnostics._supports_unicode", lambda stream: False)

        data = [10.0, 20.0, 50.0, 90.0]
        timestamps = [100.0, 110.0, 120.0, 130.0]
        draw_ascii_chart(data, timestamps, "Test Chart", "%", height=5, width=20, use_color=False, use_utc=True)
        output = capsys.readouterr().out

        assert "Test Chart" in output
        assert "+" in output
        assert "|" in output
        assert "-" in output
        assert "#" in output
        assert "Timeline" in output
        assert "Elapsed" in output
        assert "1970-01-01 00:01:40Z" in output
        assert "1970-01-01 00:02:10Z" in output
        assert "00:00:00" in output
        assert "00:00:30" in output

    def test_draw_ascii_chart_local_default_vs_utc(self, capsys):
        from datetime import datetime, timezone
        from pubrun.report.diagnostics import draw_ascii_chart

        data = [10.0, 50.0]
        timestamps = [100.0, 130.0]
        expected_local = datetime.fromtimestamp(100.0, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")

        draw_ascii_chart(data, timestamps, "Local Chart", "%", height=4, width=40, use_color=False)
        local_out = capsys.readouterr().out
        assert expected_local in local_out
        assert "00:01:40Z" not in local_out

        draw_ascii_chart(data, timestamps, "UTC Chart", "%", height=4, width=40, use_color=False, use_utc=True)
        utc_out = capsys.readouterr().out
        assert "1970-01-01 00:01:40Z" in utc_out
        assert "1970-01-01 00:02:10Z" in utc_out

    def test_print_resources_report_no_samples(self, tmp_path, capsys):
        from pubrun.report.diagnostics import print_resources_report
        manifest = {
            "run": {"run_id": "test_res"},
            "timing": {"started_at_utc": 100.0},
            "status": {"outcome": "completed"},
            "invocation": {"script": {"basename": "test.py"}},
            "resources": {"peak_rss_bytes": 1024**2 * 50, "peak_cpu_percent": 15.0}
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        print_resources_report(str(manifest_path))
        output = capsys.readouterr().out
        assert "RESOURCE MONITORING" in output
        assert "test_res" in output
        assert "50.00 MB" in output
        assert "15.0%" in output
        assert "No events.jsonl file found" in output

    def test_print_resources_report_with_samples(self, tmp_path, capsys, monkeypatch):
        from pubrun.report.diagnostics import print_resources_report
        monkeypatch.setenv("NO_COLOR", "1")

        manifest = {
            "run": {"run_id": "test_res_2"},
            "timing": {"started_at_utc": 100.0},
            "status": {"outcome": "completed"},
            "invocation": {"script": {"basename": "test.py"}},
            "resources": {"peak_rss_bytes": 1024**3 * 2, "peak_cpu_percent": 85.0}
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        events = [
            {"type": "resource_sample", "timestamp_utc": 100.0, "payload": {"rss_bytes": int(1024**3), "cpu_percent": 10.0}},
            {"type": "resource_sample", "timestamp_utc": 110.0, "payload": {"rss_bytes": int(1024**3 * 1.5), "cpu_percent": 40.0}},
            {"type": "resource_sample", "timestamp_utc": 120.0, "payload": {"rss_bytes": int(1024**3 * 2.0), "cpu_percent": 80.0}},
        ]
        events_path = tmp_path / "events.jsonl"
        with open(events_path, "w", encoding="utf-8") as ef:
            for ev in events:
                ef.write(json.dumps(ev) + "\n")

        print_resources_report(str(manifest_path))
        output = capsys.readouterr().out
        assert "RESOURCE MONITORING" in output
        assert "CPU Utilization History" in output
        assert "Memory (RSS) History" in output
        assert "GB" in output
        # Ensure color code escapes are NOT in output because NO_COLOR is set
        assert "\033" not in output

    def test_draw_ascii_chart_average(self, capsys, monkeypatch):
        from pubrun.report.diagnostics import draw_ascii_chart
        # Force non-Unicode support for simple character asserting
        monkeypatch.setattr("pubrun.report.diagnostics._supports_unicode", lambda stream: False)

        data = [0.0, 100.0, 0.0, 0.0, 100.0, 0.0]
        timestamps = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]

        # Test with max (default)
        draw_ascii_chart(data, timestamps, "Max Chart", "%", height=5, width=2, use_color=False, average=False)
        output_max = capsys.readouterr().out

        # Test with average
        draw_ascii_chart(data, timestamps, "Avg Chart", "%", height=5, width=2, use_color=False, average=True)
        output_avg = capsys.readouterr().out

        assert "Max Chart" in output_max
        assert "Avg Chart" in output_avg
        assert "#" in output_max
        assert "#" in output_avg
        assert output_max != output_avg

    def test_print_resources_report_average(self, tmp_path, capsys, monkeypatch):
        from pubrun.report.diagnostics import print_resources_report
        monkeypatch.setenv("NO_COLOR", "1")

        manifest = {
            "run": {"run_id": "test_res_avg"},
            "timing": {"started_at_utc": 100.0},
            "status": {"outcome": "completed"},
            "invocation": {"script": {"basename": "test.py"}},
            "resources": {"peak_rss_bytes": 1024**2 * 10, "peak_cpu_percent": 50.0}
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        events = [
            {"type": "resource_sample", "timestamp_utc": 100.0, "payload": {"rss_bytes": int(1024**2 * 5), "cpu_percent": 10.0}},
            {"type": "resource_sample", "timestamp_utc": 110.0, "payload": {"rss_bytes": int(1024**2 * 10), "cpu_percent": 90.0}},
            {"type": "resource_sample", "timestamp_utc": 120.0, "payload": {"rss_bytes": int(1024**2 * 6), "cpu_percent": 20.0}},
        ]
        events_path = tmp_path / "events.jsonl"
        with open(events_path, "w", encoding="utf-8") as ef:
            for ev in events:
                ef.write(json.dumps(ev) + "\n")

        # Just verify it executes with average=True without error
        print_resources_report(str(manifest_path), average=True)
        output = capsys.readouterr().out
        assert "RESOURCE MONITORING" in output
        assert "CPU Utilization History" in output


class TestPartialManifestDiagnosticsAndMethods:
    """Behavioral tests for partial manifests across print_report and methods exports (IPD 26euz0)."""

    def _run_with_failed_engines(self, tmp_path, monkeypatch, fail_engines):
        """Execute a real pubrun Run with fault injection into the requested engines."""
        import pubrun.tracker as tracker_mod
        from pubrun import get_current_run, start

        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        tracker_mod._active_run = None

        def _boom(engine_name):
            def _raise(*args, **kwargs):
                raise RuntimeError(f"{engine_name} probe failed --token=sk-secret999999")
            return _raise

        engine_targets = {
            "packages": "get_packages",
            "environment": "get_environment",
            "git": "get_git",
            "hardware": "get_hardware",
            "host": "get_host",
            "python": "get_python_runtime",
        }
        for eng in fail_engines:
            monkeypatch.setattr(tracker_mod, engine_targets[eng], _boom(eng))

        run = start(
            console={"capture_mode": "off"},
            events={"enabled": False},
            capture={
                "subprocesses": {"enabled": False},
                "resources": {"depth": "off"},
                "signals": {"enabled": False},
            },
        )
        if getattr(run, "_hardware_future_done", None) is not None:
            run._hardware_future_done.wait(timeout=3.0)
        run_dir = run.run_dir
        run.stop()
        assert get_current_run() is None
        manifest_path = run_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return manifest_path, manifest

    def test_print_report_real_partial_manifest_all_depths_sections_and_no_color(
        self, tmp_path, monkeypatch, capsys
    ):
        from pubrun.report.diagnostics import print_report

        manifest_path, manifest = self._run_with_failed_engines(
            tmp_path, monkeypatch, ["packages", "environment", "git", "hardware", "host", "python"]
        )
        assert manifest["packages"]["capture_state"]["status"] == "failed"
        assert manifest["environment"]["capture_state"]["status"] == "failed"

        # NO_COLOR enabled: zero ANSI escape codes across all depths and section extracts.
        monkeypatch.setenv("NO_COLOR", "1")
        for depth in ("basic", "standard", "deep"):
            print_report(str(manifest_path), depth=depth)
            out = capsys.readouterr().out
            assert "\033" not in out
            assert "[WARN ]" in out
            assert "Capture failed for section(s):" in out
            assert "Capture errors recorded" in out
            assert "sk-secret999999" not in out
            if depth in ("standard", "deep"):
                assert "capture failed" in out
                assert "0 recorded" not in out
                assert "0 captured" not in out
                assert "Not found or un-tracked" not in out

        print_report(str(manifest_path), section="env")
        env_out = capsys.readouterr().out
        assert "\033" not in env_out
        assert "capture failed" in env_out
        assert "(None captured)" not in env_out

        print_report(str(manifest_path), section="packages")
        pkg_out = capsys.readouterr().out
        assert "\033" not in pkg_out
        assert "capture failed" in pkg_out
        assert "(None captured)" not in pkg_out

        # With color enabled (NO_COLOR unset), still renders cleanly with warnings.
        monkeypatch.delenv("NO_COLOR", raising=False)
        print_report(str(manifest_path), depth="standard")
        colored_out = capsys.readouterr().out
        assert "[WARN ]" in colored_out
        assert "capture failed" in colored_out

    def test_print_report_caps_errors_records_and_surfaces_truncation(
        self, tmp_path, monkeypatch, capsys
    ):
        from pubrun.report.diagnostics import print_report

        monkeypatch.setenv("NO_COLOR", "1")
        records = [
            {
                "kind": "capture-error",
                "type": "RuntimeError",
                "section": f"sec_{i}",
                "stage": "bootstrap",
                "message": f"error number {i} " + ("x" * 220),
                "traceback": None,
            }
            for i in range(14)
        ]
        manifest = {
            "run": {"run_id": "trunc01"},
            "timing": {"started_at_utc": 1780250000.0, "elapsed_seconds": 5.0},
            "status": {"outcome": "completed"},
            "invocation": {"script": {"basename": "train.py"}, "argv": ["train.py"]},
            "errors": {
                "records": records,
                "capture_state": {
                    "status": "partial",
                    "detail": "36 additional capture error(s) omitted",
                },
            },
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        print_report(str(manifest_path), depth="basic")
        out = capsys.readouterr().out
        assert "\033" not in out
        assert "Capture errors recorded (14):" in out
        assert "sec_0/bootstrap" in out
        assert "sec_9/bootstrap" in out
        assert "sec_10/bootstrap" not in out
        assert "... (+4 more capture error(s))" in out
        assert "36 additional capture error(s) omitted" in out
        # Long single-record messages are bounded with ellipsis.
        assert "..." in out

    def test_methods_single_and_multi_honest_on_real_failed_engines(
        self, tmp_path, monkeypatch
    ):
        from pubrun.report.methods import generate_report_multi

        _, partial_manifest = self._run_with_failed_engines(
            tmp_path, monkeypatch, ["packages", "hardware", "host", "python"]
        )
        # Single-run Markdown
        md = generate_report(partial_manifest, "markdown")
        assert "Standard library dependencies were utilized." not in md
        assert "Package provenance was unavailable because package capture failed." in md
        assert "partial provenance; capture failed for:" in md
        for sec in ("hardware", "host", "packages", "python"):
            assert sec in md

        # Single-run LaTeX with underscored failed section name
        partial_with_underscore = dict(partial_manifest)
        partial_with_underscore["data_files"] = {
            "capture_state": {"status": "failed", "detail": "io probe failed"}
        }
        tex = generate_report(partial_with_underscore, "latex")
        assert "Standard library dependencies were utilized." not in tex
        assert "Package provenance was unavailable because package capture failed." in tex
        assert "% Note: partial provenance; capture failed for:" in tex
        assert "data\\_files" in tex

        # Suppressed packages wording
        suppressed_manifest = {
            "host": {"os_name": "Linux"},
            "hardware": {"cpu": {"model": "Intel"}, "memory_total_bytes": 1024 ** 3},
            "python": {"version": "3.11.0", "implementation": "cpython"},
            "git": {"commit": "abcdef123456"},
            "packages": {"records": [], "capture_state": {"status": "suppressed"}},
        }
        md_supp = generate_report(suppressed_manifest, "markdown")
        assert "Package capture was disabled by configuration." in md_supp
        assert "Standard library dependencies" not in md_supp
        assert "partial provenance" not in md_supp

        # Multi-run: healthy manifests[0], failed manifests[1]
        healthy = {
            "run": {"library_version": "1.3.1", "library_commit": "0123456789abcdef"},
            "host": {"os_name": "Linux", "capture_state": {"status": "complete"}},
            "hardware": {
                "cpu": {"model": "Intel Core i7"},
                "memory_total_bytes": 16 * 1024 ** 3,
                "capture_state": {"status": "complete"},
            },
            "python": {"version": "3.11.4 final", "implementation": "cpython", "capture_state": {"status": "complete"}},
            "git": {"commit": "abcdef1234567890", "capture_state": {"status": "complete"}},
            "packages": {
                "records": [{"name": "numpy", "version": "1.26.0"}],
                "capture_state": {"status": "complete"},
            },
        }
        multi_md = generate_report_multi([healthy, partial_manifest], "markdown")
        assert "(package capture failed)" in multi_md
        assert "(standard library only)" not in multi_md
        assert "partial provenance across 1 of 2 runs" in multi_md
        assert "packages" in multi_md

        multi_tex = generate_report_multi([healthy, partial_with_underscore], "latex")
        assert "(package capture failed)" in multi_tex
        assert "(standard library only)" not in multi_tex
        assert "% Note: partial provenance across 1 of 2 runs;" in multi_tex
        assert "data\\_files" in multi_tex

        # Healthy complete manifests remain unchanged (no partial provenance disclosure)
        healthy_single = generate_report(healthy, "markdown")
        assert "partial provenance" not in healthy_single
        healthy_multi = generate_report_multi([healthy, healthy], "markdown")
        assert "partial provenance" not in healthy_multi


class TestMethodsFileProvenanceDistinction:
    """Behavioral tests for honest file-provenance evidence in methods reports (IPD hm32d9)."""

    def _base_manifest(self, **over):
        m = {
            "run": {"library_version": "1.5.0", "library_commit": "0123456789abcdef"},
            "host": {"os_name": "Linux"},
            "hardware": {"cpu": {"model": "Intel Core i7"}, "memory_total_bytes": 16 * 1024**3},
            "python": {"version": "3.11.5 final", "implementation": "cpython"},
            "git": {"commit": "abcdef1234567890"},
            "packages": {"records": [{"name": "numpy", "version": "1.26.0"}]},
        }
        m.update(over)
        return m

    def test_empty_or_malformed_data_files_is_byte_identical(self):
        from pubrun.report.methods import generate_report_multi

        baseline = self._base_manifest()
        empty_variants = [
            self._base_manifest(data_files={"inputs": [], "outputs": []}),
            self._base_manifest(data_files={"inputs": [], "outputs": [], "mixed": []}),
            self._base_manifest(data_files=None),
            self._base_manifest(data_files={"inputs": "not-a-list", "outputs": [None, 1]}),
        ]
        for fmt in ("markdown", "latex"):
            expected_single = generate_report(baseline, fmt)
            expected_multi = generate_report_multi([baseline, baseline], fmt)
            for variant in empty_variants:
                assert generate_report(variant, fmt) == expected_single
                assert generate_report_multi([variant, baseline], fmt) == expected_multi

    def test_single_run_markdown_and_latex_placement_and_honest_evidence_breakdown(self):
        m = self._base_manifest(
            data_files={
                "inputs": [
                    {
                        "path": "data/verified.csv",
                        "hash_status": "completed",
                        "hash_algorithm": "sha512",
                        "sha256": None,
                        "digest": {"algorithm": "sha512", "value": "a" * 128},
                        "evidence_source": "observed",
                        "evidence_strength": "verified_content",
                    },
                    {
                        "path": "data/asserted.parquet",
                        "hash_status": "asserted",
                        "evidence_source": "asserted",
                        "evidence_strength": "asserted_content",
                        "caller_digest": {"algorithm": "sha256", "value": "b" * 64, "verified": None},
                    },
                    {
                        "path": "data/stat.csv",
                        "hash_status": "disabled",
                        "evidence_source": "observed",
                        "evidence_strength": "metadata_only",
                    },
                    {
                        "path": "data/huge.bin",
                        "hash_status": "over_budget",
                        "evidence_source": "observed",
                        "evidence_strength": "metadata_only",
                    },
                ],
                "outputs": [
                    {
                        "path": "out/pending.pt",
                        "hash_status": "pending",
                        "evidence_source": "none",
                        "evidence_strength": "path_only",
                    },
                    {
                        "path": "out/failed.csv",
                        "hash_status": "failed",
                        "hash_status_detail": "caller_digest_mismatch",
                        "evidence_source": "observed",
                        "evidence_strength": "changed_unverified",
                    },
                ],
                "mixed": [
                    {
                        "path": "work/state.db",
                        "hash_status": "file_changed",
                        "change_detected": True,
                        "evidence_source": "observed",
                        "evidence_strength": "changed_unverified",
                    }
                ],
            }
        )

        md = generate_report(m, "markdown")
        assert "Data file provenance tracked 7 file records" in md
        assert "1 with independently verified content digest" in md
        assert "1 with caller-asserted digest (unverified)" in md
        assert "1 recorded by path or stat metadata only" in md
        assert "1 skipped as over hashing budget" in md
        assert "1 pending output record (unhashed)" in md
        assert "1 changed during capture (unverified)" in md
        assert "1 with failed or unavailable hashing" in md
        assert md.index("Data file provenance tracked") < md.index("**References:**")

        tex = generate_report(m, "latex")
        assert "Data file provenance tracked 7 file records" in tex
        assert tex.index("Data file provenance tracked") < tex.index("%% Ensure you add")

    def test_unverified_and_asserted_files_never_claimed_verified(self):
        m = self._base_manifest(
            data_files={
                "inputs": [
                    {
                        "path": "ext/a.parquet",
                        "hash_status": "asserted",
                        "evidence_source": "asserted",
                        "evidence_strength": "asserted_content",
                    },
                    {
                        "path": "ext/b.csv",
                        "hash_status": "disabled",
                        "evidence_source": "observed",
                        "evidence_strength": "path_only",
                    },
                ],
                "outputs": [],
                "mixed": [],
            }
        )
        md = generate_report(m, "markdown")
        assert "independently verified" not in md
        assert "caller-asserted" in md
        assert "path or stat metadata only" in md

    def test_escape_latex_helper_escapes_underscores_and_percent(self):
        from pubrun.report.methods import _escape_latex

        assert _escape_latex("data_files 100% checked") == "data\\_files 100\\% checked"

    def test_multi_run_aggregates_when_first_manifest_empty_and_preserves_partial_notes(self):
        from pubrun.report.methods import generate_report_multi

        m_empty = self._base_manifest(data_files={"inputs": [], "outputs": [], "mixed": []})
        m_tracked = self._base_manifest(
            data_files={
                "inputs": [
                    {
                        "path": "data/in.csv",
                        "hash_status": "completed",
                        "sha256": "a" * 64,
                        "evidence_source": "observed",
                        "evidence_strength": "verified_content",
                    },
                    {
                        "path": "ext/asserted.parquet",
                        "hash_status": "asserted",
                        "evidence_source": "asserted",
                        "evidence_strength": "asserted_content",
                    },
                ],
                "outputs": [],
                "mixed": [],
            },
            git={"capture_state": {"status": "failed", "detail": "git crashed"}},
        )

        md = generate_report_multi([m_empty, m_tracked], "markdown")
        assert "across 1 of 2 runs tracked 2 file records" in md
        assert "1 with independently verified content digest" in md
        assert "1 with caller-asserted digest (unverified)" in md
        assert "partial provenance across 1 of 2 runs" in md

        tex = generate_report_multi([m_empty, m_tracked], "latex")
        assert "% Note: data file provenance across 1 of 2 runs tracked 2 file records" in tex
        assert "% Note: partial provenance across 1 of 2 runs;" in tex

    def test_digestless_completed_records_are_not_counted_verified(self):
        from pubrun.report.methods import generate_report_multi

        recs = [
            {"path": "data/no-digest.csv", "hash_status": "completed", "evidence_strength": "verified_content"},
            {"path": "data/empty-sha256.csv", "evidence_strength": "verified_content", "sha256": ""},
            {"path": "data/blank-digest.csv", "hash_status": "completed", "digest": {"algorithm": "sha256", "value": "  "}},
            {"path": "data/hashed.csv", "hash_status": "completed", "evidence_strength": "verified_content", "sha256": "a" * 64},
        ]
        m = self._base_manifest(data_files={"inputs": recs, "outputs": [], "mixed": []})
        expected_single = (
            "Data file provenance tracked 4 file records "
            "(1 with independently verified content digest, 3 recorded by path or stat metadata only)."
        )
        assert expected_single in generate_report(m, "markdown")
        assert expected_single in generate_report(m, "latex")
        assert (
            "across 2 of 2 runs tracked 8 file records "
            "(2 with independently verified content digests, 6 recorded by path or stat metadata only)"
            in generate_report_multi([m, m], "markdown")
        )

    @pytest.mark.parametrize(
        "rec, expected",
        [
            ({"hash_status": "completed"}, "identified_only"),
            ({"evidence_strength": "verified_content", "sha256": ""}, "identified_only"),
            ({"hash_status": "completed", "digest": {"algorithm": "sha256", "value": "  "}}, "identified_only"),
            ({"hash_status": "completed", "sha256": "a" * 64}, "verified"),
            (
                {"hash_status": "completed", "sha256": None, "digest": {"algorithm": "sha512", "value": "a" * 128}},
                "verified",
            ),
            ({"md5": "e" * 32}, "verified"),
            ({}, "identified_only"),
            (
                {"hash_status": "asserted", "evidence_source": "asserted", "evidence_strength": "asserted_content"},
                "asserted",
            ),
            ({"hash_status": "file_changed", "change_detected": True}, "changed"),
            (
                {
                    "hash_status": "completed",
                    "sha256": "a" * 64,
                    "caller_digest": {"algorithm": "sha256", "value": "b" * 64, "verified": False},
                },
                "failed",
            ),
            ({"hash_status": "over_budget"}, "over_budget"),
            ({"hash_status": "pending"}, "pending"),
            ({"hash_status": "disabled"}, "identified_only"),
            ({"hash_status": "unavailable"}, "unavailable"),
        ],
    )
    def test_shared_classifier_requires_nonempty_digest(self, rec, expected):
        from pubrun.report.file_evidence import _classify_file_record

        assert _classify_file_record(rec) == expected
        md = generate_report(
            self._base_manifest(data_files={"inputs": [rec], "outputs": [], "mixed": []}),
            "markdown",
        )
        assert ("independently verified content digest" in md) is (expected == "verified")

    def test_run_stop_writes_verified_methods_without_loading_reproducibility(self, tmp_path):
        script = "\n".join(
            [
                "import pathlib, sys",
                "import pubrun.noauto as pubrun",
                'pathlib.Path("in.csv").write_text("x\\n")',
                "run = pubrun.start()",
                'pubrun.register_input("in.csv", level="hash")',
                "pubrun.stop()",
                'assert "pubrun.report.reproducibility" not in sys.modules, sorted(sys.modules)',
                'text = (pathlib.Path(run.run_dir) / "methods.md").read_text(encoding="utf-8")',
                'assert "1 file record (1 with independently verified content digest)" in text, text',
                'print("OK")',
            ]
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(tmp_path),
            env={**os.environ, "XDG_CONFIG_HOME": str(tmp_path), "APPDATA": str(tmp_path)},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        assert result.stdout.strip() == "OK"


class TestDiagnosticsDataFilesDisplay:
    """Behavioral tests for diagnostics Data Files display classification and rendering."""

    @pytest.mark.parametrize(
        "rec, expected",
        [
            ({"hash_status": "completed"}, "metadata-only"),
            ({"evidence_strength": "verified_content"}, "metadata-only"),
            ({"evidence_strength": "verified_content", "digest": {"value": "   "}}, "metadata-only"),
            ({"hash_status": "completed", "sha256": ""}, "metadata-only"),
            ({"hash_status": "completed", "md5": "  "}, "metadata-only"),
            ({"hash_status": "completed", "evidence_strength": "path_only"}, "path-only"),
            (
                {
                    "hash_status": "completed",
                    "sha256": None,
                    "digest": {"algorithm": "sha512", "value": "1234567890abcdef" * 8},
                },
                "verified",
            ),
            ({"hash_status": "completed", "sha256": "a" * 64}, "verified"),
            ({"hash_status": "completed", "md5": "b" * 32}, "verified"),
            ({"md5": "c" * 32}, "verified"),
            ({"hash_status": "disabled", "evidence_strength": "path_only"}, "path-only"),
            ({"hash_status": "disabled", "evidence_strength": "metadata_only"}, "metadata-only"),
            ({}, "metadata-only"),
            ({"hash_status": "over_budget"}, "over-budget"),
            ({"hash_status": "asserted"}, "asserted"),
            ({"evidence_strength": "asserted_content"}, "asserted"),
            ({"evidence_source": "asserted"}, "asserted"),
            ({"hash_status": "file_changed"}, "changed"),
            ({"change_detected": True}, "changed"),
            ({"evidence_strength": "changed_unverified"}, "changed"),
            ({"hash_status": "failed"}, "failed"),
            ({"hash_status_detail": "caller_digest_mismatch"}, "failed"),
            (
                {
                    "hash_status": "completed",
                    "sha256": "a" * 64,
                    "caller_digest": {"algorithm": "sha256", "value": "b" * 64, "verified": False},
                },
                "failed",
            ),
            ({"hash_status": "unavailable"}, "unavailable"),
            ({"evidence_strength": "unavailable"}, "unavailable"),
            ({"hash_status": "pending"}, "pending"),
        ],
    )
    def test_classify_file_record_display_badges(self, rec, expected):
        from pubrun.report.diagnostics import _classify_file_record_display

        assert _classify_file_record_display(rec) == expected

    def test_extract_display_digest_supports_digest_sha256_and_sanitized_md5(self):
        from pubrun.report.diagnostics import _extract_display_digest

        assert (
            _extract_display_digest(
                {"digest": {"algorithm": "sha512", "value": "1234567890abcdef" * 8}, "sha256": "f" * 64, "md5": "e" * 32},
                "verified",
            )
            == "sha512:1234567890ab"
        )
        assert (
            _extract_display_digest({"sha256": "abcdef0123456789" * 4, "md5": "e" * 32}, "verified")
            == "sha256:abcdef012345"
        )
        assert (
            _extract_display_digest({"md5": "0123456789abcdef0123456789abcdef"}, "verified")
            == "md5:0123456789ab"
        )
        assert (
            _extract_display_digest({"md5": "\x1b[31m9876543210fe\n\tdcba\x1b[0m"}, "verified")
            == "md5:9876543210fe"
        )
        assert _extract_display_digest({"md5": "   "}, "verified") is None
        assert _extract_display_digest({"md5": "0123456789abcdef" * 2}, "metadata-only") is None
        assert _extract_display_digest({"sha256": "a" * 64}, "failed") is None

    def test_summarize_and_print_data_files_block_require_nonempty_digest(self):
        import io
        from pubrun.report.diagnostics import _print_data_files_block, _summarize_data_files

        manifest = {
            "data_files": {
                "inputs": [
                    {"path": "data/no_digest.csv", "hash_status": "completed"},
                    {
                        "path": "data/blank_digest.csv",
                        "evidence_strength": "verified_content",
                        "digest": {"algorithm": "sha256", "value": "   "},
                    },
                    {
                        "path": "data/digest_ok.csv",
                        "hash_status": "completed",
                        "digest": {"algorithm": "sha512", "value": "1111222233334444" * 8},
                    },
                    {
                        "path": "data/sha256_ok.csv",
                        "hash_status": "completed",
                        "sha256": "aaaabbbbccccdddd" * 4,
                    },
                    {
                        "path": "data/legacy_md5.csv",
                        "md5": "\x1b[32mdeadbeef1234\x1b[0m567890abcdef123456",
                    },
                    {"path": "data/path_only.csv", "hash_status": "disabled", "evidence_strength": "path_only"},
                    {"path": "data/huge.bin", "hash_status": "over_budget"},
                    {
                        "path": "data/asserted.parquet",
                        "hash_status": "asserted",
                        "caller_digest": {"algorithm": "sha256", "value": "5555666677778888" * 4, "verified": None},
                    },
                    {"path": "data/missing.csv", "hash_status": "unavailable"},
                    {
                        "path": "data/mismatch.csv",
                        "hash_status": "completed",
                        "sha256": "9999000011112222" * 4,
                        "caller_digest": {"algorithm": "sha256", "value": "0000111122223333" * 4, "verified": False},
                    },
                ],
                "outputs": [
                    {"path": "out/pending.pt", "hash_status": "pending"},
                ],
                "mixed": [
                    {"path": "work/state.db", "hash_status": "file_changed", "change_detected": True},
                ],
            }
        }

        counts = _summarize_data_files(manifest["data_files"])
        assert counts == {
            "total": 12,
            "verified": 3,
            "asserted": 1,
            "identified_only": 3,
            "over_budget": 1,
            "changed": 1,
            "failed_or_unavailable": 2,
            "pending": 1,
        }

        buf = io.StringIO()
        _print_data_files_block(manifest, use_color=False, out=buf)
        rendered = buf.getvalue()

        assert "\x1b[" not in rendered
        assert "[metadata-only] data/no_digest.csv" in rendered
        assert "[verified] data/no_digest.csv" not in rendered
        assert "[metadata-only] data/blank_digest.csv" in rendered
        assert "[verified] data/blank_digest.csv" not in rendered
        assert "[verified] data/digest_ok.csv (input) sha512:111122223333" in rendered
        assert "[verified] data/sha256_ok.csv (input) sha256:aaaabbbbcccc" in rendered
        assert "[verified] data/legacy_md5.csv (input) md5:deadbeef1234" in rendered
        assert "[path-only] data/path_only.csv" in rendered
        assert "[over-budget] data/huge.bin" in rendered
        assert "[asserted] data/asserted.parquet (input) sha256:555566667777" in rendered
        assert "[unavailable] data/missing.csv" in rendered
        assert "[failed] data/mismatch.csv" in rendered
        assert "999900001111" not in rendered
        assert "[pending] out/pending.pt" in rendered
        assert "[changed] work/state.db" in rendered


class TestMethodsGpuPackagesDoiAndLatex:
    """Regression tests for caeqdz E-01: GPUs, honest packages, Zenodo DOI, 10-char LaTeX."""

    def _base(self, **over):
        m = {
            "run": {"library_version": "1.4.0", "library_commit": "0123456789abcdef"},
            "host": {"os_name": "Linux"},
            "hardware": {"cpu": {"model": "AMD EPYC 7763"}, "memory_total_bytes": 64 * 1024**3},
            "python": {"version": "3.11.6 final", "implementation": "cpython"},
            "git": {"commit": "abcdef1234567890", "remote_url": {"value": "https://example.org/org/repo"}},
            "packages": {"records": []},
        }
        m.update(over)
        return m

    def test_gpu_single_multi_identical_and_malformed(self):
        # Single GPU
        m_single = self._base(
            hardware={
                "cpu": {"model": "EPYC"},
                "memory_total_bytes": 32 * 1024**3,
                "gpus": [{"model": "NVIDIA H100", "memory_total_bytes": 80 * 1024**3, "driver_version": "550.54"}],
            }
        )
        md_single = generate_report(m_single, "markdown")
        tex_single = generate_report(m_single, "latex")
        assert "NVIDIA H100 (80.0 GB VRAM, driver 550.54)" in md_single
        assert "NVIDIA H100 (80.0 GB VRAM, driver 550.54)" in tex_single
        assert "1x NVIDIA H100" not in md_single

        # Multi identical GPUs grouped
        m_multi = self._base(
            hardware={
                "cpu": {"model": "EPYC"},
                "memory_total_bytes": 32 * 1024**3,
                "gpus": [
                    {"model": "NVIDIA A100", "memory_total_bytes": 80 * 1024**3, "driver_version": "535.104"},
                    {"model": "NVIDIA A100", "memory_total_bytes": 80 * 1024**3, "driver_version": "535.104"},
                ],
            }
        )
        assert "2x NVIDIA A100 (80.0 GB VRAM, driver 535.104)" in generate_report(m_multi, "markdown")
        assert "2x NVIDIA A100 (80.0 GB VRAM, driver 535.104)" in generate_report(m_multi, "latex")

        # Missing / empty / malformed GPUs omit GPU text cleanly
        baseline = generate_report(self._base(), "markdown")
        for bad_gpus in ([], None, "not-a-list", [None, {}, {"model": ""}, {"model": 123}]):
            m_bad = self._base(
                hardware={"cpu": {"model": "AMD EPYC 7763"}, "memory_total_bytes": 64 * 1024**3, "gpus": bad_gpus}
            )
            assert generate_report(m_bad, "markdown") == baseline
            assert "accelerated by" not in generate_report(m_bad, "markdown")

    def test_non_highlighted_third_party_packages_honest_and_empty_preserved(self):
        m_non_hl = self._base(
            packages={"records": [{"name": "polars", "version": "0.20.0"}, {"name": "biopython", "version": "1.83"}]}
        )
        md = generate_report(m_non_hl, "markdown")
        tex = generate_report(m_non_hl, "latex")
        assert "Standard library dependencies were utilized." not in md
        assert "Standard library dependencies were utilized." not in tex
        assert "polars (v0.20.0)" in md and "biopython (v1.83)" in md
        assert "polars (v0.20.0)" in tex and "biopython (v1.83)" in tex

        # Empty packages preserves stdlib wording
        md_empty = generate_report(self._base(packages={"records": []}), "markdown")
        assert "Standard library dependencies were utilized." in md_empty

    def test_zenodo_doi_in_markdown_and_latex(self):
        m = self._base()
        md = generate_report(m, "markdown")
        tex = generate_report(m, "latex")
        assert "https://doi.org/10.5281/zenodo.20801582" in md
        assert "10.5281/zenodo.20801582" in tex
        assert "doi" in tex and "{10.5281/zenodo.20801582}" in tex

    def test_escape_latex_all_10_special_chars_single_pass(self):
        from pubrun.report.methods import _escape_latex

        raw = r"\&%$#_{}~^"
        escaped = _escape_latex(raw)
        assert escaped == r"\textbackslash{}\&\%\$\#\_\{\}\textasciitilde{}\textasciicircum{}"
        assert r"\textbackslash\{\}" not in escaped

        m = self._base(
            host={"os_name": r"Linux\dev&100%"},
            hardware={
                "cpu": {"model": r"CPU_#1$2{3}~4^5"},
                "memory_total_bytes": 16 * 1024**3,
                "gpus": [{"model": r"GPU_A&B\C", "driver_version": "535_1^2"}],
            },
            packages={"records": [{"name": "my_pkg", "version": "1.0~rc1"}]},
        )
        tex = generate_report(m, "latex")
        assert r"\textbackslash{}" in tex
        assert r"\textbackslash\{\}" not in tex
        assert r"CPU\_\#1\$2\{3\}\textasciitilde{}4\textasciicircum{}5" in tex
        assert r"GPU\_A\&B\textbackslash{}C" in tex
        assert r"1.0\textasciitilde{}rc1" in tex


class TestDiffEngineCrossOsMultisetAndSanitize:
    """Regression tests for caeqdz E-02: cross-OS diff, compiled ignores, NaN, Counter, strict JSON."""

    def test_cross_os_path_and_subprocess_basename(self):
        from pubrun.analysis.diff import compare_manifests

        win_a = {
            "host": {"os_name": "Windows"},
            "environment": {"variables": [{"name": "PATH", "value": r"C:\Python311;C:\Tools"}]},
            "subprocesses": [{"argv": [r"C:\Python311\python.exe", "run.py"]}],
        }
        win_b = {
            "host": {"os_name": "Windows"},
            "environment": {"variables": [{"name": "PATH", "value": r"C:\Python311;C:\Tools;C:\CUDA\bin"}]},
            "subprocesses": [
                {"argv": [r"C:\Python311\python.exe", "run.py"]},
                {"argv": [r"D:\bin\git.exe", "status"]},
            ],
        }
        diff = compare_manifests(win_a, win_b, depth="standard")
        path_mod = diff["modified"]["environment.PATH"]
        assert path_mod["type"] == "path_split"
        assert path_mod["added"] == [r"C:\CUDA\bin"]
        assert path_mod["removed"] == []
        assert diff["added"]["subprocesses.by_command.git.exe"] == 1
        assert "subprocesses.by_command.python.exe" not in diff["modified"]

        posix_a = {
            "host": {"os_name": "Linux"},
            "environment": {"variables": [{"name": "PATH", "value": "/usr/bin:/bin"}]},
            "subprocesses": [{"argv": ["/usr/bin/python3", "run.py"]}],
        }
        posix_b = {
            "host": {"os_name": "Darwin"},
            "environment": {"variables": [{"name": "PATH", "value": "/usr/bin:/opt/bin"}]},
            "subprocesses": [{"argv": ["/opt/homebrew/bin/python3", "run.py"]}],
        }
        diff_posix = compare_manifests(posix_a, posix_b, depth="standard")
        assert diff_posix["modified"]["environment.PATH"]["added"] == ["/opt/bin"]
        assert diff_posix["modified"]["environment.PATH"]["removed"] == ["/bin"]
        assert "subprocesses.by_command.python3" not in diff_posix["modified"]

    def test_compiled_case_sensitive_wildcards_and_none_name_skip(self):
        from pubrun.analysis.diff import _normalize_manifest

        manifest = {
            "environment": {
                "variables": [
                    {"name": None, "value": "x"},
                    {"name": "", "value": "y"},
                    {"name": 123, "value": "z"},
                    {"name": "KEEP_VAR", "value": "1"},
                    {"name": "DROP_1", "value": "2"},
                    {"name": "drop_1", "value": "3"},
                    {"name": "MATCH_a", "value": "4"},
                ]
            },
            "packages": {
                "records": [
                    {"name": None, "version": "1.0"},
                    {"name": "", "version": "1.0"},
                    {"name": "numpy", "version": "1.26"},
                ]
            },
        }
        flat = _normalize_manifest(
            manifest,
            ignores=["environment.DROP_?", "environment.MATCH_[ab]"],
            depth="standard",
        )
        assert "environment.None" not in flat
        assert "packages.None" not in flat
        assert "environment." not in flat
        assert "packages." not in flat
        assert "environment.DROP_1" not in flat
        assert "environment.MATCH_a" not in flat
        # Case-sensitive wildcard must NOT drop lowercase drop_1
        assert flat["environment.drop_1"] == "3"
        assert flat["environment.KEEP_VAR"] == "1"
        assert flat["packages.numpy"] == "1.26"

    def test_nan_equality_bool_int_distinction_and_multiset_list_diff(self):
        from pubrun.analysis.diff import compare_manifests

        nan1, nan2 = float("nan"), float("nan")
        rep_nan = compare_manifests(
            {"score": nan1, "vals": [1, nan1], "flag": True},
            {"score": nan2, "vals": [1, nan2], "flag": 1},
            show_same=True,
        )
        assert "score" in rep_nan["same"]
        assert "vals" in rep_nan["same"]
        assert "score" not in rep_nan["modified"]
        assert "vals" not in rep_nan["modified"]
        assert "flag" in rep_nan["modified"]

        rep_dup = compare_manifests({"items": ["a", "a", "b"]}, {"items": ["a", "b"]})
        mod = rep_dup["modified"]["items"]
        assert mod["type"] == "list_diff"
        assert mod["removed"] == ["a"]
        assert mod["added"] == []
        assert mod["order_changed"] is False

    def test_export_manifest_sanitizes_non_finite_floats_strict_json(self):
        from pubrun.analysis.diff import export_manifest

        raw = {"metrics": {"a": float("nan"), "b": float("inf"), "c": float("-inf"), "ok": 1.5}}
        exported = export_manifest(raw, [], fmt="json", depth="deep")
        assert "NaN" not in exported
        assert "Infinity" not in exported
        parsed = json.loads(exported)
        assert parsed["metrics"] == {"a": None, "b": None, "c": None, "ok": 1.5}


class TestDiagnosticsGuardsAndResponsiveLayout:
    """Regression tests for caeqdz E-03: read_resource_series, chart, sparkline, duration, packages grid."""

    def test_read_resource_series_prefilter_and_finite_guards(self, tmp_path):
        from pubrun.report.diagnostics import read_resource_series

        ev_path = tmp_path / "events.jsonl"
        rows = [
            json.dumps({"type": "phase", "timestamp_utc": 100.0, "payload": {"name": "load"}}),
            "{not-valid-json",
            json.dumps({"type": "resource_sample", "timestamp_utc": 101.0, "payload": {"rss_bytes": True, "cpu_percent": 10.0}}),
            json.dumps({"type": "resource_sample", "timestamp_utc": 102.0, "payload": {"rss_bytes": float("nan"), "cpu_percent": 10.0}}, allow_nan=True),
            json.dumps({"type": "resource_sample", "timestamp_utc": 103.0, "payload": {"rss_bytes": 1024, "cpu_percent": 25.0, "tree_rss_bytes": float("inf")}}, allow_nan=True),
            json.dumps({"type": "resource_sample", "timestamp_utc": 104.0, "payload": {"rss_bytes": 2048, "cpu_percent": 50.0, "tree_rss_bytes": 4096, "tree_cpu_percent": 60.0}}),
        ]
        ev_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        series = read_resource_series(ev_path)
        assert series["timestamps"] == [103.0, 104.0]
        assert series["rss"] == [1024.0, 2048.0]
        assert series["cpu"] == [25.0, 50.0]
        assert series["tree_rss"] == [4096.0]
        assert series["tree_cpu"] == [60.0]

    def test_draw_ascii_chart_edge_cases(self):
        import io
        from pubrun.report.diagnostics import draw_ascii_chart

        # Empty / all-NaN
        buf = io.StringIO()
        draw_ascii_chart([], [], "Empty", "%", out=buf)
        assert "No valid resource samples to plot." in buf.getvalue()

        buf_nan = io.StringIO()
        draw_ascii_chart([float("nan")], [100.0], "NaN", "%", out=buf_nan)
        assert "No valid resource samples to plot." in buf_nan.getvalue()

        # height=1, width=1, out-of-range timestamps, narrow width
        buf_tiny = io.StringIO()
        draw_ascii_chart([10.0, 20.0], [1e30, 1e30 + 10], "Tiny", "%", height=1, width=1, use_color=False, out=buf_tiny)
        out_tiny = buf_tiny.getvalue()
        assert "Tiny" in out_tiny
        assert "unknown" in out_tiny

        buf_narrow = io.StringIO()
        draw_ascii_chart([10.0, 50.0], [100.0, 130.0], "Narrow", "%", height=3, width=4, use_color=False, use_utc=True, out=buf_narrow)
        assert "Narrow" in buf_narrow.getvalue()

    def test_sparkline_guards_and_ascii_fallback(self):
        import io
        from pubrun.report.diagnostics import _sparkline

        assert _sparkline([]) == ""
        assert _sparkline([float("nan"), float("inf"), True]) == ""
        assert _sparkline([1.0, 2.0], width=0) == ""
        ascii_spark = _sparkline([0.0, 5.0, 10.0], ascii_only=True)
        assert ascii_spark and ascii_spark.isascii()

        ascii_stream = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
        stream_spark = _sparkline([0.0, 5.0, 10.0], stream=ascii_stream)
        assert stream_spark and stream_spark.isascii()

    @pytest.mark.parametrize("bad", ["", "   ", "abc", "0", "0s", "-10s", "nan", "inf", "-inf", "infs"])
    def test_parse_duration_rejects_invalid_values(self, bad):
        from pubrun.report.diagnostics import parse_duration

        with pytest.raises(ValueError) as exc_info:
            parse_duration(bad)
        assert "'30s'" in str(exc_info.value)

    @pytest.mark.parametrize("term_cols,expected_data_lines", [(50, 6), (80, 3), (110, 2)])
    def test_print_packages_block_responsive_columns(self, monkeypatch, term_cols, expected_data_lines):
        import io
        import shutil
        from pubrun.report.diagnostics import _print_packages_block

        monkeypatch.setattr(shutil, "get_terminal_size", lambda fallback=(80, 24): os.terminal_size((term_cols, 24)))
        manifest = {
            "packages": {
                "records": [{"name": f"pkg{i}", "version": "1.0"} for i in range(6)],
            }
        }
        buf = io.StringIO()
        _print_packages_block(manifest, use_color=False, out=buf)
        lines = [ln for ln in buf.getvalue().splitlines() if "==" in ln]
        assert len(lines) == expected_data_lines


class TestMetaSnapshotAndHydrationHardening:
    """Regression tests for caeqdz E-04: atomic meta.json, next steps, .JSON case, drift prose."""

    def test_generate_meta_snapshot_atomic_sanitized_and_next_steps(self, tmp_path, monkeypatch, capsys):
        from pubrun.report import meta_snapshot

        monkeypatch.setattr(
            meta_snapshot,
            "get_hardware",
            lambda cfg: {"cpu": {"model": "EPYC", "freq_ghz": float("nan")}, "capture_state": {"status": "complete"}},
        )
        monkeypatch.setattr(
            meta_snapshot,
            "get_python_runtime",
            lambda cfg: {"version": "3.11.8", "capture_state": {"status": "complete"}},
        )
        monkeypatch.setattr(
            meta_snapshot,
            "get_packages",
            lambda cfg: {"records": [], "capture_state": {"status": "complete"}},
        )
        monkeypatch.setattr(
            meta_snapshot,
            "get_git",
            lambda cfg: {"commit": "abc12345", "capture_state": {"status": "complete"}},
        )
        monkeypatch.setattr(
            meta_snapshot,
            "get_environment",
            lambda cfg: {"variables": [], "capture_state": {"status": "complete"}},
        )
        monkeypatch.setattr(
            meta_snapshot,
            "get_host",
            lambda cfg: {"hostname": "hpc-01", "os_name": "Linux", "capture_state": {"status": "complete"}},
        )

        out_path = tmp_path / "shared" / "meta.json"
        meta_snapshot.generate_meta_snapshot(str(out_path), "basic")

        # No leftover temp files and strict JSON (NaN -> null)
        assert out_path.exists()
        assert not list(out_path.parent.glob("*.tmp"))
        raw = out_path.read_text(encoding="utf-8")
        assert "NaN" not in raw
        parsed = json.loads(raw)
        assert parsed["hardware"]["cpu"]["freq_ghz"] is None

        # Copy-pasteable next steps including valid TOML
        stdout = capsys.readouterr().out
        assert f'export PUBRUN_META_REF="{out_path.resolve()}"' in stdout
        assert "[report]" in stdout
        toml_line = [ln.strip() for ln in stdout.splitlines() if "meta_ref_allowed_dirs" in ln][0]
        assert json.dumps(str(out_path.resolve().parent)) in toml_line

    def test_uppercase_json_extension_preserves_security_order_and_drift_prose(self, tmp_path):
        from pubrun.report.utils import hydrate_manifest_with_report

        # 1. Uppercase .JSON inside manifest dir hydrates cleanly and emits clear drift prose.
        parent_meta = {
            "manifest_type": "pubrun-meta-snapshot",
            "timing": {"started_at_utc": 1000.0},
            "hardware": {"cpu": {"model": "Xeon"}, "capture_state": {"status": "complete"}},
        }
        (tmp_path / "META.JSON").write_text(json.dumps(parent_meta), encoding="utf-8")
        child = {
            "meta_ref": "META.JSON",
            "timing": {"started_at_utc": 1200.0},
            "invocation": {"script": {"mtime": 1100.0}},
            "hardware": {"capture_state": {"status": "suppressed"}},
        }
        hydrated, warnings, report = hydrate_manifest_with_report(str(tmp_path / "manifest.json"), child)
        assert report.status == "hydrated"
        assert hydrated["hardware"]["cpu"]["model"] == "Xeon"
        assert any(w.startswith("Drift Detected:") and "pubrun meta" in w for w in warnings)
        assert all("was tracking structurally" not in w for w in warnings)

        # 2. Security check order preserved: .TXT outside dir -> invalid_extension; .JSON outside dir -> blocked_by_policy.
        sub = tmp_path / "sub"
        sub.mkdir()
        _, _, rep_txt = hydrate_manifest_with_report(str(sub / "manifest.json"), {"meta_ref": "../SECRET.TXT"})
        assert rep_txt.status == "invalid_extension"
        _, _, rep_ext_json = hydrate_manifest_with_report(str(sub / "manifest.json"), {"meta_ref": "../META.JSON"})
        assert rep_ext_json.status == "blocked_by_policy"
