"""Tests for report generation: methods, diagnostics utilities, and hydration."""
import json
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

    def test_contains_texttt_pubrun(self, sample_manifest):
        text = generate_report(sample_manifest, "latex")
        assert "\\texttt{pubrun}" in text


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
        """Empty python version doesn't crash."""
        manifest = {"host": {"os_name": "Linux"}, "python": {"version": ""}, "git": {"commit": "abc12345"}}
        result = generate_report(manifest)
        # Should not crash; may produce "v" or "unknown"
        assert isinstance(result, str)

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

    def test_basic_depth_shows_timing(self, tmp_path, capsys):
        """Basic depth includes timing information."""
        from pubrun.report.diagnostics import print_report
        manifest_path = self._make_manifest(tmp_path)
        print_report(manifest_path, "basic")
        output = capsys.readouterr().out
        assert "completed" in output.lower() or "60" in output

    def test_standard_depth_shows_git(self, tmp_path, capsys):
        """Standard depth includes git commit."""
        from pubrun.report.diagnostics import print_report
        manifest_path = self._make_manifest(tmp_path)
        print_report(manifest_path, "standard")
        output = capsys.readouterr().out
        assert "abcdef12" in output or "Git" in output

    def test_deep_depth_shows_packages(self, tmp_path, capsys):
        """Deep depth includes package listings."""
        from pubrun.report.diagnostics import print_report
        manifest_path = self._make_manifest(tmp_path)
        print_report(manifest_path, "deep")
        output = capsys.readouterr().out
        assert "torch" in output or "Packages" in output


class TestResourceMonitoring:
    """Unit tests for drawing utilization graphs and printing resources report."""

    def test_draw_ascii_chart_unicode(self, capsys, monkeypatch):
        from pubrun.report.diagnostics import draw_ascii_chart
        # Force Unicode support
        monkeypatch.setattr("pubrun.report.diagnostics._supports_unicode", lambda stream: True)
        
        data = [10.0, 20.0, 50.0, 90.0]
        timestamps = [100.0, 110.0, 120.0, 130.0]
        draw_ascii_chart(data, timestamps, "Test Chart", "%", height=5, width=20, use_color=False)
        output = capsys.readouterr().out
        
        # Verify title, labels and Unicode border characters
        assert "Test Chart" in output
        assert "└" in output
        assert "│" in output
        assert "─" in output
        assert "█" in output
        assert "Start: 0s" in output
        assert "End: 30s" in output

    def test_draw_ascii_chart_ascii_fallback(self, capsys, monkeypatch):
        from pubrun.report.diagnostics import draw_ascii_chart
        # Force non-Unicode support
        monkeypatch.setattr("pubrun.report.diagnostics._supports_unicode", lambda stream: False)
        
        data = [10.0, 20.0, 50.0, 90.0]
        timestamps = [100.0, 110.0, 120.0, 130.0]
        draw_ascii_chart(data, timestamps, "Test Chart", "%", height=5, width=20, use_color=False)
        output = capsys.readouterr().out
        
        assert "Test Chart" in output
        assert "+" in output
        assert "|" in output
        assert "-" in output
        assert "#" in output
        assert "Start: 0s" in output
        assert "End: 30s" in output

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


