"""Tests for report generation: methods, diagnostics utilities, and hydration."""
import json
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
