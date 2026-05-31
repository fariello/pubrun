"""Exhaustive CLI tests for pubrun command-line interface."""
import json
import os
import sys
import subprocess
import pytest
from pathlib import Path

PYTHON = sys.executable


def run_pubrun(*args, cwd=None):
    """Helper to invoke pubrun CLI and return the completed process."""
    cmd = [PYTHON, "-m", "pubrun"] + list(args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or os.getcwd(),
        timeout=30
    )


class TestCliHelp:

    def test_help_exits_zero(self):
        result = run_pubrun("--help")
        assert result.returncode == 0

    def test_help_mentions_pubrun(self):
        result = run_pubrun("--help")
        assert "pubrun" in result.stdout.lower()

    def test_report_help(self):
        result = run_pubrun("report", "--help")
        assert result.returncode == 0
        assert "report" in result.stdout.lower()

    def test_methods_help(self):
        result = run_pubrun("methods", "--help")
        assert result.returncode == 0

    def test_diff_help(self):
        result = run_pubrun("diff", "--help")
        assert result.returncode == 0

    def test_rerun_help(self):
        result = run_pubrun("rerun", "--help")
        assert result.returncode == 0

    def test_meta_help(self):
        result = run_pubrun("meta", "--help")
        assert result.returncode == 0

    def test_cite_help(self):
        result = run_pubrun("cite", "--help")
        assert result.returncode == 0

    def test_version_exits_zero(self):
        result = run_pubrun("--version")
        assert result.returncode == 0

    def test_version_prints_version_string(self):
        result = run_pubrun("--version")
        assert "pubrun" in result.stdout.lower()
        # Should contain a version-like pattern (digits and dots)
        import re
        assert re.search(r"\d+\.\d+", result.stdout)


class TestCliInfo:

    def test_info_exits_zero(self):
        result = run_pubrun("--info")
        assert result.returncode == 0

    def test_info_prints_system_info(self):
        result = run_pubrun("--info")
        output = result.stdout.lower()
        assert "python" in output or "system" in output or "pubrun" in output


class TestCliShowConfig:

    def test_show_config_exits_zero(self):
        result = run_pubrun("--show-config")
        assert result.returncode == 0

    def test_show_config_prints_toml(self):
        result = run_pubrun("--show-config")
        # Should contain TOML section headers
        assert "[core]" in result.stdout or "core" in result.stdout


class TestCliCreateConfig:

    def test_create_config_writes_file(self, tmp_path):
        dest = str(tmp_path / ".pubrun.toml")
        result = run_pubrun("--create-config", dest, cwd=str(tmp_path))
        assert result.returncode == 0
        assert Path(dest).exists()
        content = Path(dest).read_text(encoding="utf-8")
        assert "[core]" in content

    def test_create_config_refuses_overwrite(self, tmp_path):
        dest = str(tmp_path / ".pubrun.toml")
        # Create file first
        Path(dest).write_text("existing content", encoding="utf-8")
        result = run_pubrun("--create-config", dest, cwd=str(tmp_path))
        assert result.returncode == 1
        # Original content should be preserved
        assert Path(dest).read_text(encoding="utf-8") == "existing content"


class TestCliCite:

    def test_cite_apa(self):
        result = run_pubrun("cite", "--style", "apa")
        assert result.returncode == 0
        assert "pubrun" in result.stdout.lower() or "fariello" in result.stdout.lower()

    def test_cite_bibtex(self):
        result = run_pubrun("cite", "--style", "bibtex")
        assert result.returncode == 0
        assert "pubrun" in result.stdout.lower() or "@" in result.stdout

    def test_cite_mla(self):
        result = run_pubrun("cite", "--style", "mla")
        assert result.returncode == 0

    def test_cite_chicago(self):
        result = run_pubrun("cite", "--style", "chicago")
        assert result.returncode == 0


class TestCliMeta:

    def test_meta_default_creates_file(self, tmp_path):
        result = run_pubrun("meta", cwd=str(tmp_path))
        assert result.returncode == 0
        # Default output goes to runs/meta.json
        meta_path = tmp_path / "runs" / "meta.json"
        assert meta_path.exists()
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        assert "host" in data or "python" in data or "hardware" in data

    def test_meta_to_file(self, tmp_path):
        out_path = str(tmp_path / "meta.json")
        result = run_pubrun("meta", "--out", out_path, cwd=str(tmp_path))
        assert result.returncode == 0
        assert Path(out_path).exists()
        data = json.loads(Path(out_path).read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_meta_basic_depth(self, tmp_path):
        result = run_pubrun("meta", "--basic", cwd=str(tmp_path))
        assert result.returncode == 0

    def test_meta_deep_depth(self, tmp_path):
        result = run_pubrun("meta", "--deep", cwd=str(tmp_path))
        assert result.returncode == 0


class TestCliReport:

    @pytest.fixture
    def run_dir(self, tmp_path):
        """Create a real run to test report commands against."""
        from pubrun import start as pubrun_start
        import pubrun.tracker
        pubrun.tracker._active_run = None
        old_cwd = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            tracker = pubrun_start()
            tracker.stop()
            return str(tracker.run_dir)
        finally:
            Path.cwd = old_cwd
            pubrun.tracker._active_run = None

    def test_report_valid_run(self, run_dir):
        result = run_pubrun("report", run_dir)
        assert result.returncode == 0

    def test_report_basic_depth(self, run_dir):
        result = run_pubrun("report", run_dir, "--basic")
        assert result.returncode == 0

    def test_report_deep_depth(self, run_dir):
        result = run_pubrun("report", run_dir, "--deep")
        assert result.returncode == 0

    def test_report_invalid_path(self, tmp_path):
        result = run_pubrun("report", str(tmp_path / "nonexistent"))
        assert result.returncode != 0


class TestCliMethods:

    @pytest.fixture
    def run_dir(self, tmp_path):
        """Create a real run to test methods command against."""
        from pubrun import start as pubrun_start
        import pubrun.tracker
        pubrun.tracker._active_run = None
        old_cwd = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            tracker = pubrun_start()
            tracker.stop()
            return str(tracker.run_dir)
        finally:
            Path.cwd = old_cwd
            pubrun.tracker._active_run = None

    def test_methods_markdown(self, run_dir):
        result = run_pubrun("methods", run_dir)
        assert result.returncode == 0
        assert "Computational Methods" in result.stdout

    def test_methods_latex(self, run_dir):
        result = run_pubrun("methods", run_dir, "--format", "latex")
        assert result.returncode == 0
        assert "\\subsection" in result.stdout


class TestCliRerun:

    @pytest.fixture
    def run_dir(self, tmp_path):
        """Create a real run to test rerun command against."""
        from pubrun import start as pubrun_start
        import pubrun.tracker
        pubrun.tracker._active_run = None
        old_cwd = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            tracker = pubrun_start()
            tracker.stop()
            return str(tracker.run_dir)
        finally:
            Path.cwd = old_cwd
            pubrun.tracker._active_run = None

    def test_rerun_prints_command(self, run_dir):
        result = run_pubrun("rerun", run_dir)
        assert result.returncode == 0
        assert "cd " in result.stdout or "python" in result.stdout


class TestCliDiff:

    @pytest.fixture
    def two_runs(self, tmp_path):
        """Create two runs to diff."""
        from pubrun import start as pubrun_start
        import pubrun.tracker

        dirs = []
        old_cwd = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            for _ in range(2):
                pubrun.tracker._active_run = None
                tracker = pubrun_start()
                tracker.stop()
                dirs.append(str(tracker.run_dir))
        finally:
            Path.cwd = old_cwd
            pubrun.tracker._active_run = None
        return dirs

    def test_diff_two_valid_runs(self, two_runs):
        result = run_pubrun("diff", two_runs[0], two_runs[1])
        assert result.returncode == 0

    def test_diff_no_color(self, two_runs):
        result = run_pubrun("diff", two_runs[0], two_runs[1], "--no-color")
        assert result.returncode == 0

    def test_diff_export_txt(self, two_runs):
        result = run_pubrun("diff", two_runs[0], two_runs[1], "--export", "txt")
        assert result.returncode == 0

    def test_diff_export_json(self, two_runs):
        result = run_pubrun("diff", two_runs[0], two_runs[1], "--export", "json")
        assert result.returncode == 0

    def test_diff_invalid_paths(self, tmp_path):
        result = run_pubrun("diff", "/nonexistent/a", "/nonexistent/b")
        assert result.returncode != 0


class TestCliRunTests:

    def test_run_tests_exits_zero(self, tmp_path):
        result = run_pubrun("--run-tests", cwd=str(tmp_path))
        assert result.returncode == 0


class TestCliNoCommand:

    def test_no_args_prints_help(self):
        result = run_pubrun()
        # Should print help and exit 0 (no error)
        assert result.returncode == 0
        assert "pubrun" in result.stdout.lower() or "usage" in result.stdout.lower()


class TestCliErrorExitCodes:
    """Test that CLI commands exit 1 on error conditions."""

    def test_methods_missing_manifest_exits_1(self, tmp_path):
        """pubrun methods with non-existent run dir exits 1."""
        result = run_pubrun("methods", str(tmp_path / "nonexistent"), cwd=str(tmp_path))
        assert result.returncode == 1

    def test_rerun_missing_manifest_exits_1(self, tmp_path):
        """pubrun rerun with non-existent run dir exits 1."""
        result = run_pubrun("rerun", str(tmp_path / "nonexistent"), cwd=str(tmp_path))
        assert result.returncode == 1

    def test_rerun_manifest_without_rerun_command_exits_1(self, tmp_path):
        """pubrun rerun with a manifest lacking rerun_command exits 1."""
        run_dir = tmp_path / "runs" / "pubrun-test"
        run_dir.mkdir(parents=True)
        manifest = {"invocation": {"rerun_command": None}}
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        result = run_pubrun("rerun", str(run_dir), cwd=str(tmp_path))
        assert result.returncode == 1

    def test_diff_export_bad_format_exits_1(self, tmp_path):
        """pubrun diff --export badformat exits 1."""
        # Need two valid run dirs with manifests for diff to get to format check
        for name in ("a", "b"):
            d = tmp_path / name
            d.mkdir()
            (d / "manifest.json").write_text(json.dumps({
                "schema_version": "1.0", "manifest_type": "pubrun-manifest",
                "status": {"outcome": "completed"}
            }), encoding="utf-8")

        result = run_pubrun("diff", str(tmp_path / "a"), str(tmp_path / "b"),
                           "--export", "yaml", cwd=str(tmp_path))
        assert result.returncode == 1
        assert "unsupported" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_status_nonexistent_run_id_exits_1(self, tmp_path):
        """pubrun status <nonexistent_id> exits 1."""
        result = run_pubrun("status", "zzzznonexistent", "--dir", str(tmp_path),
                           cwd=str(tmp_path))
        assert result.returncode == 1
        assert "no run found" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_cite_unknown_style_exits_1(self, tmp_path):
        """pubrun cite --style unknown exits 1."""
        result = run_pubrun("cite", "--style", "unknown_style", cwd=str(tmp_path))
        # argparse rejects unknown choices with exit code 2
        assert result.returncode != 0
