"""Exhaustive CLI tests for pubrun command-line interface."""
import json
import os
import sys
import subprocess
import time
import pytest
from pathlib import Path

PYTHON = sys.executable


def _dead_pid() -> int:
    """Spawn a short-lived child, wait for exit, and return its now-dead PID."""
    proc = subprocess.Popen([PYTHON, "-c", "pass"])
    proc.wait(timeout=30)
    return proc.pid


def run_pubrun(*args, cwd=None, env=None):
    """Helper to invoke pubrun CLI and return the completed process."""
    cmd = [PYTHON, "-m", "pubrun"] + list(args)
    run_env = dict(os.environ)
    src_dir = Path(__file__).resolve().parents[1] / "src"
    if src_dir.is_dir():
        existing = run_env.get("PYTHONPATH", "")
        run_env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing}" if existing else str(src_dir)
    if env:
        run_env.update(env)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or os.getcwd(),
        env=run_env,
        timeout=30
    )


class TestCliHelp:

    def test_help_exits_zero(self):
        result = run_pubrun("--help")
        assert result.returncode == 0

    def test_help_mentions_pubrun(self):
        result = run_pubrun("--help")
        assert "pubrun" in result.stdout.lower()

    def test_help_command_translation_root(self):
        result = run_pubrun("help")
        assert result.returncode == 0
        assert "usage: pubrun" in result.stdout.lower()

    def test_help_command_translation_subcommand(self):
        result = run_pubrun("help", "report")
        assert result.returncode == 0
        assert "usage: pubrun report" in result.stdout.lower()

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

    def test_version_includes_commit_when_available(self):
        # In a git checkout / packaged wheel, --version surfaces the resolved commit hash.
        from pubrun import __commit__
        result = run_pubrun("--version")
        if __commit__:
            assert f"commit {__commit__}" in result.stdout
        else:
            assert "commit " not in result.stdout  # no stray/empty commit marker


class TestCliInfo:

    def test_info_exits_zero(self):
        result = run_pubrun("--info")
        assert result.returncode == 0

    def test_info_prints_system_info(self):
        result = run_pubrun("--info")
        assert "pubrun Hardware Diagnostics" in result.stdout


class TestCliShowConfig:

    def test_show_config_exits_zero(self):
        result = run_pubrun("--show-config")
        assert result.returncode == 0

    def test_show_config_prints_toml(self):
        result = run_pubrun("--show-config")
        assert "[core]" in result.stdout.splitlines()


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

    def test_create_config_prompt_eof_abandons(self, tmp_path):
        result = subprocess.run(
            [sys.executable, "-m", "pubrun", "--create-config"],
            cwd=str(tmp_path),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 1
        assert "Configuration abandoned." in result.stderr
        assert "Traceback" not in result.stderr
        assert not (tmp_path / ".pubrun.toml").exists()


class TestCliInit:
    """`pubrun init` is the primary first-use entry point: it writes a commented
    .pubrun.toml in the current directory and prints getting-started guidance."""

    def test_init_writes_config_and_prints_guidance(self, tmp_path):
        result = run_pubrun("init", cwd=str(tmp_path))
        assert result.returncode == 0
        config = tmp_path / ".pubrun.toml"
        assert config.exists()
        content = config.read_text(encoding="utf-8")
        assert "[core]" in content
        # Getting-started guidance is printed.
        assert "Getting started:" in result.stdout
        assert "import pubrun" in result.stdout

    def test_init_refuses_to_overwrite_existing_config(self, tmp_path):
        """Characterization test: init must not clobber an existing .pubrun.toml.

        Current behavior (src/pubrun/__main__.py: _create_config) refuses and
        exits non-zero, leaving the existing file byte-for-byte unchanged.
        """
        config = tmp_path / ".pubrun.toml"
        original = "existing content"
        config.write_text(original, encoding="utf-8")

        result = run_pubrun("init", cwd=str(tmp_path))

        assert result.returncode == 1
        assert "Refusing to overwrite" in (result.stdout + result.stderr)
        # The existing file is untouched.
        assert config.read_text(encoding="utf-8") == original


class TestCliCite:

    def test_cite_apa(self):
        result = run_pubrun("cite", "--style", "apa")
        assert result.returncode == 0
        assert "pubrun" in result.stdout.lower() or "fariello" in result.stdout.lower()
        # DOI must flow through to the citation (placeholder or real).
        assert "zenodo" in result.stdout.lower() or "doi.org" in result.stdout.lower()
        # Citation surface uses the PUBLICATION name, never the legal name.
        assert "G. R." not in result.stdout

    def test_cite_bibtex(self):
        result = run_pubrun("cite", "--style", "bibtex")
        assert result.returncode == 0
        assert "pubrun" in result.stdout.lower() or "@" in result.stdout
        assert "doi" in result.stdout.lower() and "zenodo" in result.stdout.lower()
        # bibtex author is the publication name "Gabriele Fariello", not legal name.
        assert "Gabriele Fariello" in result.stdout
        assert "G. R." not in result.stdout

    def test_cite_mla(self):
        result = run_pubrun("cite", "--style", "mla")
        assert result.returncode == 0
        assert "zenodo" in result.stdout.lower()
        assert "G. R." not in result.stdout

    def test_cite_chicago(self):
        result = run_pubrun("cite", "--style", "chicago")
        assert result.returncode == 0
        assert "zenodo" in result.stdout.lower()
        assert "G. R." not in result.stdout


class TestCitationConsistency:
    """Drift guard: author name, DOI, version, and license must agree across
    CITATION.cff, .zenodo.json, README.md, and `pubrun cite` output.

    CITATION.cff is parsed with a tiny stdlib line reader (NOT PyYAML) because the
    project is zero-runtime-dependency and PyYAML is not a declared dependency; the
    fields asserted here (given-names/family-names, version, license, and the DOI
    `value:`) are flat scalars, so line parsing is sufficient and keeps tests dep-free.
    """

    @staticmethod
    def _repo_root():
        # tests/ -> repo root
        return Path(__file__).resolve().parent.parent

    @classmethod
    def _cff_fields(cls):
        text = (cls._repo_root() / "CITATION.cff").read_text(encoding="utf-8")
        fields = {}
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith("#") or ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip().lstrip("- ").strip()
            val = val.strip().strip('"')
            # first occurrence wins for the flat scalars we care about
            fields.setdefault(key, val)
        return fields

    def test_zenodo_json_valid_and_publication_name(self):
        data = json.loads((self._repo_root() / ".zenodo.json").read_text(encoding="utf-8"))
        assert data["upload_type"] == "software"
        assert data["license"] == "Apache-2.0"
        creator = data["creators"][0]
        assert creator["name"] == "Fariello, Gabriele"  # publication form
        assert "G. R." not in creator["name"]
        assert creator["orcid"] == "0000-0002-0326-4752"
        assert creator["affiliation"] == "University of Rhode Island"

    def test_cff_parses_and_publication_name(self):
        f = self._cff_fields()
        assert f["cff-version"] == "1.2.0"
        assert f["given-names"] == "Gabriele"     # publication form, NOT "Gabriele G. R."
        assert f["family-names"] == "Fariello"
        assert f["license"] == "Apache-2.0"
        assert "version" in f and f["version"]
        assert "orcid" in f["orcid"]  # value contains the orcid.org URL
        assert "0000-0002-0326-4752" in f["orcid"]

    def test_doi_agrees_across_surfaces(self):
        f = self._cff_fields()
        cff_doi = f["value"]  # the identifiers: - type: doi / value: line
        assert "zenodo" in cff_doi
        assert "PENDING" not in cff_doi
        # README and research-use docs carry the same DOI string.
        readme = (self._repo_root() / "README.md").read_text(encoding="utf-8")
        assert cff_doi in readme
        research_use = (self._repo_root() / "docs" / "research-use.md").read_text(encoding="utf-8")
        assert cff_doi in research_use
        # pubrun cite emits the same DOI in every style.
        for style in ("apa", "mla", "chicago", "bibtex"):
            out = run_pubrun("cite", "--style", style).stdout
            assert cff_doi in out, f"{style} citation missing DOI {cff_doi}"

    def test_cff_version_matches_package(self):
        from pubrun import __version__
        f = self._cff_fields()
        assert f["version"] == __version__


class TestCliMeta:

    def test_meta_default_creates_file(self, tmp_path):
        result = run_pubrun("meta", cwd=str(tmp_path))
        assert result.returncode == 0
        # Default output goes to runs/meta.json
        meta_path = tmp_path / "runs" / "meta.json"
        assert meta_path.exists()
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        assert {"host", "python", "hardware"} <= set(data)

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
        data = json.loads((tmp_path / "runs" / "meta.json").read_text(encoding="utf-8"))
        assert set(data["packages"]) == {"capture_state"}

    def test_meta_deep_depth(self, tmp_path):
        result = run_pubrun("meta", "--deep", cwd=str(tmp_path))
        assert result.returncode == 0
        data = json.loads((tmp_path / "runs" / "meta.json").read_text(encoding="utf-8"))
        assert "records" in data["packages"]


class TestCliReport:

    @pytest.fixture
    def run_dir(self, tmp_path):
        """Create a real run to test report commands against."""
        from pubrun import start as pubrun_start
        import pubrun.tracker
        pubrun.tracker._active_run = None
        try:
            tracker = pubrun_start()
            tracker.stop()
            return str(tracker.run_dir)
        finally:
            pubrun.tracker._active_run = None

    def test_report_valid_run(self, run_dir, tmp_path):
        manifest = json.loads((Path(run_dir) / "manifest.json").read_text(encoding="utf-8"))
        run_id = manifest["run"]["run_id"]
        res_basic = run_pubrun("report", run_dir, "--basic", cwd=str(tmp_path), env={"NO_COLOR": "1"})
        res_default = run_pubrun("report", run_dir, cwd=str(tmp_path), env={"NO_COLOR": "1"})
        res_deep = run_pubrun("report", run_dir, "--deep", cwd=str(tmp_path), env={"NO_COLOR": "1"})
        assert res_basic.returncode == 0
        assert res_default.returncode == 0
        assert res_deep.returncode == 0
        assert run_id in res_default.stdout
        assert "[ Packages ]" not in res_basic.stdout
        assert "[ Packages ]" not in res_default.stdout
        assert "[ Packages ]" in res_deep.stdout
        assert len(res_basic.stdout.splitlines()) < len(res_default.stdout.splitlines()) < len(res_deep.stdout.splitlines())

    def test_report_basic_depth(self, run_dir, tmp_path):
        result = run_pubrun("report", run_dir, "--basic", cwd=str(tmp_path), env={"NO_COLOR": "1"})
        assert result.returncode == 0
        assert "[ Packages ]" not in result.stdout

    def test_report_deep_depth(self, run_dir, tmp_path):
        result = run_pubrun("report", run_dir, "--deep", cwd=str(tmp_path), env={"NO_COLOR": "1"})
        assert result.returncode == 0
        assert "[ Packages ]" in result.stdout

    def test_report_invalid_path(self, tmp_path):
        result = run_pubrun("report", str(tmp_path / "nonexistent"), cwd=str(tmp_path), env={"NO_COLOR": "1"})
        assert result.returncode != 0


class TestCliMethods:

    @pytest.fixture
    def run_dir(self, tmp_path):
        """Create a real run to test methods command against."""
        from pubrun import start as pubrun_start
        import pubrun.tracker
        pubrun.tracker._active_run = None
        try:
            tracker = pubrun_start()
            tracker.stop()
            return str(tracker.run_dir)
        finally:
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
        try:
            tracker = pubrun_start()
            tracker.stop()
            return str(tracker.run_dir)
        finally:
            pubrun.tracker._active_run = None

    def test_rerun_prints_command(self, run_dir):
        result = run_pubrun("rerun", run_dir)
        assert result.returncode == 0
        assert "cd " in result.stdout or "python" in result.stdout

    def test_rerun_running_run(self, tmp_path):
        import time
        run_dir = tmp_path / "runs" / "pubrun-running"
        run_dir.mkdir(parents=True)
        lock_data = {
            "run_id": "running-id",
            "pid": 12345,
            "started_at_utc": time.time() - 3600,
            "script": "train.py",
            "argv": ["--epochs", "10"],
            "sys_argv": ["train.py", "--epochs", "10"],
            "hostname": "otherhost",
            "cwd": "/some/cwd"
        }
        with open(run_dir / ".pubrun.lock", "w", encoding="utf-8") as f:
            json.dump(lock_data, f)

        result = run_pubrun("rerun", str(run_dir))
        assert result.returncode == 0
        assert "[WARN ]" in result.stderr
        assert "is currently running" in result.stderr
        if sys.platform == "win32":
            assert "cd /some/cwd" in result.stdout
            assert "python train.py --epochs 10" in result.stdout
        else:
            assert "cd /some/cwd && python train.py --epochs 10" in result.stdout

    def test_rerun_crashed_run_reconstruction(self, tmp_path):
        import time
        run_dir = tmp_path / "runs" / "pubrun-crashed"
        run_dir.mkdir(parents=True)
        lock_data = {
            "run_id": "crashed-id",
            "pid": 12345,
            "started_at_utc": time.time() - 200000,
            "script": "train.py",
            "argv": ["--epochs", "10"],
            "sys_argv": ["train.py", "--epochs", "10"],
            "hostname": "otherhost",
            "cwd": "/some/cwd"
        }
        with open(run_dir / ".pubrun.lock", "w", encoding="utf-8") as f:
            json.dump(lock_data, f)

        result = run_pubrun("rerun", str(run_dir))
        assert result.returncode == 0
        assert "[WARN ]" in result.stderr
        assert "is currently crashed" in result.stderr
        if sys.platform == "win32":
            assert "cd /some/cwd" in result.stdout
            assert "python train.py --epochs 10" in result.stdout
        else:
            assert "cd /some/cwd && python train.py --epochs 10" in result.stdout

    def test_rerun_crashed_run_no_color(self, tmp_path):
        import time
        run_dir = tmp_path / "runs" / "pubrun-crashed-nocolor"
        run_dir.mkdir(parents=True)
        lock_data = {
            "run_id": "crashed-nocolor-id",
            "pid": 12345,
            "started_at_utc": time.time() - 200000,
            "script": "train.py",
            "argv": ["--epochs", "10"],
            "sys_argv": ["train.py", "--epochs", "10"],
            "hostname": "otherhost",
            "cwd": "/some/cwd"
        }
        with open(run_dir / ".pubrun.lock", "w", encoding="utf-8") as f:
            json.dump(lock_data, f)

        result = run_pubrun("rerun", str(run_dir), "--no-color")
        assert result.returncode == 0
        assert "[WARN ]" in result.stderr
        assert "\033[" not in result.stderr
        assert "is currently crashed" in result.stderr
        if sys.platform == "win32":
            assert "cd /some/cwd" in result.stdout
            assert "python train.py --epochs 10" in result.stdout
        else:
            assert "cd /some/cwd && python train.py --epochs 10" in result.stdout


class TestCliDiff:

    @pytest.fixture
    def two_runs(self, tmp_path, monkeypatch):
        """Create two runs with deterministic basic, standard, and deep differences."""
        from pubrun import start as pubrun_start
        import pubrun.tracker

        dirs = []
        try:
            for idx in range(2):
                monkeypatch.setenv("PUBRUN_TEST_DIFF_ENV", f"run-{idx}")
                pubrun.tracker._active_run = None
                tracker = pubrun_start(
                    capture={"inputs": {"compute_md5": bool(idx)}},
                )
                tracker.stop()
                dirs.append(str(tracker.run_dir))
        finally:
            pubrun.tracker._active_run = None
        return dirs

    def test_diff_two_valid_runs(self, two_runs, tmp_path):
        res_basic = run_pubrun("diff", two_runs[0], two_runs[1], "--basic", "--no-color", cwd=str(tmp_path))
        res_standard = run_pubrun("diff", two_runs[0], two_runs[1], "--standard", "--no-color", cwd=str(tmp_path))
        res_deep = run_pubrun("diff", two_runs[0], two_runs[1], "--deep", "--no-color", cwd=str(tmp_path))
        assert res_basic.returncode == 0
        assert res_standard.returncode == 0
        assert res_deep.returncode == 0
        assert len({res_basic.stdout, res_standard.stdout, res_deep.stdout}) == 3

    def test_diff_no_color(self, two_runs, tmp_path):
        res_color = run_pubrun("diff", two_runs[0], two_runs[1], cwd=str(tmp_path), env={"NO_COLOR": ""})
        res_no_color = run_pubrun(
            "diff", two_runs[0], two_runs[1], "--no-color", cwd=str(tmp_path), env={"NO_COLOR": ""}
        )
        assert res_color.returncode == 0
        assert res_no_color.returncode == 0
        assert "\x1b[" in res_color.stdout
        assert "\x1b[" not in res_no_color.stdout

    def test_diff_export_txt(self, two_runs, tmp_path):
        result = run_pubrun("diff", two_runs[0], two_runs[1], "--export", "txt", cwd=str(tmp_path))
        assert result.returncode == 0
        name_a = Path(two_runs[0]).name
        out_a = tmp_path / f".pubrun_diff_A_{name_a}_clean.txt"
        assert out_a.exists()
        first_line = out_a.read_text(encoding="utf-8").splitlines()[0]
        assert " = " in first_line
        assert f"Successfully exported semantic baseline A to: .pubrun_diff_A_{name_a}_clean.txt" in result.stdout

    def test_diff_export_json(self, two_runs, tmp_path):
        result = run_pubrun("diff", two_runs[0], two_runs[1], "--export", "json", cwd=str(tmp_path))
        assert result.returncode == 0
        name_a = Path(two_runs[0]).name
        name_b = Path(two_runs[1]).name
        out_a = tmp_path / f".pubrun_diff_A_{name_a}_clean.json"
        out_b = tmp_path / f".pubrun_diff_B_{name_b}_clean.json"
        assert out_a.exists()
        assert out_b.exists()
        assert isinstance(json.loads(out_a.read_text(encoding="utf-8")), dict)
        assert isinstance(json.loads(out_b.read_text(encoding="utf-8")), dict)

    def test_diff_standard(self, two_runs, tmp_path):
        result = run_pubrun("diff", two_runs[0], two_runs[1], "--standard", "--no-color", cwd=str(tmp_path))
        assert result.returncode == 0
        assert "--- Pubrun Diagnostic Difference ---" in result.stdout

    def test_diff_deep(self, two_runs, tmp_path):
        result = run_pubrun("diff", two_runs[0], two_runs[1], "--deep", "--no-color", cwd=str(tmp_path))
        assert result.returncode == 0
        assert "--- Pubrun Diagnostic Difference ---" in result.stdout

    def test_diff_invalid_paths(self, tmp_path):
        result = run_pubrun("diff", "/nonexistent/a", "/nonexistent/b", cwd=str(tmp_path))
        assert result.returncode != 0

    def test_diff_default_no_args(self, two_runs, tmp_path):
        result = run_pubrun("diff", cwd=str(tmp_path))
        assert result.returncode == 0
        assert "auto-detected" in result.stderr.lower()

    def test_diff_default_one_arg(self, two_runs, tmp_path):
        result = run_pubrun("diff", two_runs[0], cwd=str(tmp_path))
        assert result.returncode == 0
        assert "comparing" in result.stderr.lower()

    def test_diff_default_no_args_insufficient_runs(self, tmp_path):
        from pubrun import start as pubrun_start
        import pubrun.tracker

        try:
            pubrun.tracker._active_run = None
            tracker = pubrun_start()
            tracker.stop()
        finally:
            pubrun.tracker._active_run = None

        result = run_pubrun("diff", cwd=str(tmp_path))
        assert result.returncode != 0
        assert "need at least 2 runs" in result.stderr.lower()

    def test_diff_help_has_filter_flags(self, tmp_path):
        """diff now exposes the standard run filters (-f/-F)."""
        result = run_pubrun("diff", "--help", cwd=str(tmp_path))
        assert result.returncode == 0
        assert "--filter" in result.stdout and "--not-filter" in result.stdout

    def test_diff_filter_matching_selects_pair(self, two_runs, tmp_path):
        """-f matching all runs still auto-selects the two most recent."""
        # `.` is a regex that matches every run (any run_id char), so the pair is
        # still found and auto-selected — proving the filter plumbing keeps >=2 runs.
        result = run_pubrun("diff", "-f", ".", cwd=str(tmp_path))
        assert result.returncode == 0
        assert "auto-detected" in result.stderr.lower()

    def test_diff_filter_zero_match_errors(self, two_runs, tmp_path):
        """-f matching no runs errors clearly, never a silent unfiltered fallback."""
        result = run_pubrun("diff", "-f", "zzz_no_such_run_xyz", cwd=str(tmp_path))
        assert result.returncode != 0
        assert "filter" in result.stderr.lower()
        # must NOT have fallen back to the unfiltered auto-detect pair
        assert "auto-detected" not in result.stderr.lower()


class TestCliFilterFlagConsistency:
    """1.4.0: `-f` means `--filter` on every filter-capable command, including the
    breaking change on `combined` (was `--force`)."""

    def test_combined_f_is_filter_not_force(self):
        """BREAKING (1.4.0): combined -f is now --filter; force is --force (long-only)."""
        import re
        result = run_pubrun("combined", "--help")
        assert result.returncode == 0
        out = result.stdout
        # -f maps to --filter now. argparse renders this as "-f, --filter" (Python 3.13+)
        # or "-f QUERY, --filter QUERY" (<= 3.12), so match version-independently.
        assert re.search(r"-f(?: \w+)?, --filter", out), out
        # ...and force is long-only (no short -f alias for --force).
        assert "--force" in out
        assert not re.search(r"-f(?: \w+)?, --force", out)

    def test_clean_f_is_filter(self):
        """clean has no pre-existing -f, so -f must map to --filter."""
        import re
        result = run_pubrun("clean", "--help")
        assert result.returncode == 0
        assert re.search(r"-f(?: \w+)?, --filter", result.stdout), result.stdout


class TestCliRunTests:

    def test_run_tests_exits_zero(self, tmp_path, monkeypatch):
        """P3-T15: Test --run-tests command exits 0, defusing recursive pytest call."""
        import subprocess
        original_run = subprocess.run

        def mock_run(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) > 2 and cmd[2] == "pytest":
                return subprocess.CompletedProcess(cmd, 0, stdout="Mocked pytest success", stderr="")
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = run_pubrun("--run-tests", cwd=str(tmp_path))
        assert result.returncode == 0

    def test_run_tests_end_to_end_mock_validates_manifest(self, tmp_path):
        """The built-in self-test's end-to-end mock must actually run a tracked script
        and confirm it produced a manifest (not silently pass on a broken run).

        Runs outside a source checkout (no tests/ + tox.ini in cwd) so the recursive
        PyTest matrix branch is skipped and only the mock-script validation executes.
        """
        result = run_pubrun("--run-tests", cwd=str(tmp_path))
        assert result.returncode == 0
        out = result.stdout
        # The mock training script ran without crashing...
        assert "Mock script executed without crashing" in out
        # ...and the self-test reached its validation summary (manifest was read).
        assert "Validation complete" in out
        # ...and the subprocess spy line was emitted (manifest.subprocesses was parsed).
        assert "Subprocess spy captured" in out

    def test_run_tests_mock_run_manifest_is_wellformed(self, tmp_path):
        """Regression: the mock self-test run must produce a real, parseable manifest
        with the expected phases/annotations — guarding against the self-test silently
        'passing' on a manifest it never actually validated.

        Reproduces the self-test's mock workload directly so we can assert on the
        manifest it leaves behind (the CLI path swallows manifest errors by design)."""
        import json
        import subprocess

        script = (
            "import time, os\n"
            "import pubrun\n"
            "tracker = pubrun.start()\n"
            "pubrun.annotate('initializing_model', layers=3, opt='adam')\n"
            "with pubrun.phase('epoch_1'):\n"
            "    os.system('echo hi')\n"
            "print('done')\n"
            # Finalize explicitly so the manifest is deterministically 'completed' before the
            # process exits; relying on the atexit finalizer races the parent's manifest read on
            # a contended runner (seen as outcome 'running' on fast CI).
            "pubrun.stop()\n"
        )
        script_path = tmp_path / "mock_training.py"
        script_path.write_text(script, encoding="utf-8")
        env = dict(os.environ, PUBRUN_AUTO_START="true")
        r = subprocess.run([PYTHON, str(script_path)], cwd=str(tmp_path),
                           env=env, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr

        runs = list((tmp_path / "runs").iterdir())
        assert runs, "self-test mock produced no run directory"
        manifest = json.loads((runs[0] / "manifest.json").read_text(encoding="utf-8"))
        # Well-formed core structure.
        assert manifest["schema_version"] == "1.0"
        assert manifest["manifest_type"] == "pubrun-manifest"
        assert manifest["status"]["outcome"] == "completed"


class TestCliNoCommand:

    def test_no_args_prints_help(self):
        result = run_pubrun()
        # Should print help and exit 0 (no error)
        assert result.returncode == 0
        assert result.stdout.splitlines()[0].startswith("usage: pubrun ")


class TestCliBugReport:

    @pytest.mark.parametrize("cmd", ["report-bug", "feedback"])
    def test_report_bug_and_feedback_open_browser_and_print_diagnostics(self, cmd, monkeypatch, capsys):
        """report-bug and feedback both print diagnostics and open the GitHub issues URL."""
        import webbrowser
        import sys
        from pubrun.__main__ import main

        browser_opened_url = None

        def mock_open(url, *args, **kwargs):
            nonlocal browser_opened_url
            browser_opened_url = url
            return True

        monkeypatch.setattr(webbrowser, "open", mock_open)
        monkeypatch.setattr(sys, "argv", ["pubrun", cmd])

        try:
            main()
        except SystemExit as e:
            assert e.code == 0 or e.code is None

        captured = capsys.readouterr()
        stdout_lower = captured.out.lower()
        assert "python version" in stdout_lower
        assert "platform" in stdout_lower
        assert "github.com/fariello/pubrun/issues/new" in captured.out
        assert browser_opened_url == "https://github.com/fariello/pubrun/issues/new"

    @pytest.mark.parametrize("old", ["bug-report", "issue"])
    def test_old_bugreport_names_are_gone(self, old):
        """The pre-1.4.0 names bug-report/issue were removed (hard rename)."""
        result = run_pubrun(old)
        assert result.returncode != 0  # argparse invalid-choice


class TestCliSubcommandErrors:

    def test_subcommand_invalid_argument_error(self):
        result = run_pubrun("report", "--foo")
        assert result.returncode == 2
        assert "usage: pubrun report" in result.stderr.lower()
        assert "pubrun report: error: unrecognized arguments: --foo" in result.stderr


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
        assert "Unsupported export format 'yaml'. Use 'txt' or 'json'." in result.stderr

    def test_status_nonexistent_run_id_exits_1(self, tmp_path):
        """pubrun status <nonexistent_id> exits 1."""
        result = run_pubrun("status", "zzzznonexistent", "--dir", str(tmp_path),
                           cwd=str(tmp_path))
        assert result.returncode == 1
        assert "No run found matching 'zzzznonexistent'." in result.stderr

    def test_cite_unknown_style_exits_1(self, tmp_path):
        """pubrun cite --style unknown exits 1."""
        result = run_pubrun("cite", "--style", "unknown_style", cwd=str(tmp_path))
        # argparse rejects unknown choices with exit code 2
        assert result.returncode != 0

    def test_report_running_or_crashed_run(self, tmp_path):
        """pubrun report when the run is running or crashed (only has lock file)."""
        run_dir = tmp_path / "runs" / "pubrun-crashed"
        run_dir.mkdir(parents=True)
        # Create a mock lock file
        lock_data = {
            "run_id": "crashed-id",
            "pid": 99999,
            "started_at_utc": time.time() - 3 * 86400,
            "script": "train.py",
            "argv": ["train.py", "--epochs", "10"],
            "hostname": "localhost"
        }
        with open(run_dir / ".pubrun.lock", "w", encoding="utf-8") as f:
            json.dump(lock_data, f)

        # Let's run `pubrun report` with the path
        result = run_pubrun("report", str(run_dir), cwd=str(tmp_path), env={"NO_COLOR": "1"})
        assert result.returncode == 1
        assert "[ERROR] Run directory 'pubrun-crashed' is currently crashed and does not contain a manifest.json." in result.stderr
        assert "  - Arguments: train.py --epochs 10" in result.stderr
        assert "Status: CRASHED" in result.stderr
        assert "crashed-id" in result.stderr
        assert "train.py" in result.stderr
        assert "localhost" in result.stderr

    def test_report_auto_detected_crashed_run_with_suggestion(self, tmp_path):
        """pubrun report auto-detection gets a crashed run and suggests the latest completed run."""
        # 1. Create a completed run
        completed_dir = tmp_path / "runs" / "pubrun-completed"
        completed_dir.mkdir(parents=True)
        manifest = {
            "schema_version": "1.0",
            "manifest_type": "pubrun-manifest",
            "run": {"run_id": "completed-id"},
            "status": {"outcome": "completed"}
        }
        with open(completed_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        # 2. Create a crashed run (more recent)
        crashed_dir = tmp_path / "runs" / "pubrun-crashed"
        crashed_dir.mkdir(parents=True)
        lock_data = {
            "run_id": "crashed-id",
            "pid": 99999,
            "started_at_utc": time.time() - 3 * 86400,
            "script": "train.py",
            "argv": ["train.py", "--epochs", "10"],
            "hostname": "localhost"
        }
        with open(crashed_dir / ".pubrun.lock", "w", encoding="utf-8") as f:
            json.dump(lock_data, f)

        # Set mtime of crashed run to be greater
        os.utime(completed_dir, (time.time() - 100, time.time() - 100))
        os.utime(crashed_dir, (time.time(), time.time()))

        # Run report without arguments
        result = run_pubrun("report", cwd=str(tmp_path), env={"NO_COLOR": "1"})
        assert result.returncode == 1
        assert "Status: CRASHED" in result.stderr
        assert "Suggestion:" in result.stderr
        assert "pubrun-completed" in result.stderr


class TestCliColorControl:

    def test_status_no_color_env(self, tmp_path):
        # Create a run in tmp_path
        from pubrun import start as pubrun_start
        import pubrun.tracker
        pubrun.tracker._active_run = None
        try:
            tracker = pubrun_start()
            tracker.stop()
        finally:
            pubrun.tracker._active_run = None

        # Run pubrun status in a piped subprocess (non-TTY): default emits zero ANSI
        env_piped = os.environ.copy()
        env_piped.pop("NO_COLOR", None)
        env_piped.pop("FORCE_COLOR", None)
        cmd = [sys.executable, "-m", "pubrun", "status", "--dir", str(tmp_path / "runs")]
        res_piped = subprocess.run(cmd, capture_output=True, text=True, env=env_piped, cwd=str(tmp_path))

        # Run pubrun status WITH color via FORCE_COLOR=1 (piped stdout is not a TTY)
        env_with_color = env_piped.copy()
        env_with_color["FORCE_COLOR"] = "1"
        res_color = subprocess.run(cmd, capture_output=True, text=True, env=env_with_color, cwd=str(tmp_path))

        # Run pubrun status WITHOUT color (NO_COLOR overrides FORCE_COLOR)
        env_no_color = env_with_color.copy()
        env_no_color["NO_COLOR"] = "1"
        res_no_color = subprocess.run(cmd, capture_output=True, text=True, env=env_no_color, cwd=str(tmp_path))

        # Run pubrun status WITHOUT color (global flag overrides FORCE_COLOR)
        cmd_flag = [sys.executable, "-m", "pubrun", "--no-color", "status", "--dir", str(tmp_path / "runs")]
        res_flag = subprocess.run(cmd_flag, capture_output=True, text=True, env=env_with_color, cwd=str(tmp_path))

        # Check ANSI gating: piped default has none, FORCE_COLOR enables it, NO_COLOR/--no-color disable it
        assert "\033[" not in res_piped.stdout
        assert "\033[" in res_color.stdout
        assert "\033[2m" not in res_color.stdout
        assert "\033[" not in res_no_color.stdout
        assert "\033[" not in res_flag.stdout

    def test_report_no_color_any_position(self, tmp_path):
        # Create a run in tmp_path
        from pubrun import start as pubrun_start
        import pubrun.tracker
        pubrun.tracker._active_run = None
        try:
            tracker = pubrun_start()
            tracker.stop()
        finally:
            pubrun.tracker._active_run = None

        run_dirs = list((tmp_path / "runs").glob("pubrun-*"))
        assert len(run_dirs) == 1
        run_dir = run_dirs[0]

        env_with_color = os.environ.copy()
        env_with_color.pop("NO_COLOR", None)

        # Run pubrun report <run_dir> --no-color (flag after subcommand args)
        cmd_report = [sys.executable, "-m", "pubrun", "report", str(run_dir), "--no-color"]
        res_report = subprocess.run(cmd_report, capture_output=True, text=True, env=env_with_color, cwd=str(tmp_path))
        assert res_report.returncode == 0
        assert "\033[" not in res_report.stdout

    def test_run_preserves_no_color_arg(self, tmp_path):
        cmd = [
            sys.executable, "-m", "pubrun", "run", "--",
            sys.executable, "-c", "import sys; print(' '.join(sys.argv))", "arg1", "--no-color"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path))
        assert res.returncode == 0
        assert "--no-color" in res.stdout

    def test_global_no_color_with_run_preserves_arg(self, tmp_path):
        cmd = [
            sys.executable, "-m", "pubrun", "--no-color", "run", "--",
            sys.executable, "-c", "import sys; print(' '.join(sys.argv))", "arg1", "--no-color"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path))
        assert res.returncode == 0
        assert "--no-color" in res.stdout


class TestCliReportUsabilityDetails:

    def test_report_failed_run_with_details(self, tmp_path):
        run_dir = tmp_path / "runs" / "pubrun-failed"
        run_dir.mkdir(parents=True)
        manifest = {
            "schema_version": "1.0",
            "manifest_type": "pubrun-manifest",
            "run": {"run_id": "failed-run-id"},
            "status": {"outcome": "failed"},
            "signals": {
                "exit_code": 1,
                "exit_exception": "ValueError: Invalid parameter",
                "signals_received": [
                    {"signal": 15, "signal_name": "SIGTERM", "timestamp_utc": 1234567.0}
                ]
            }
        }
        with open(run_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        # Print report WITH color
        env_with_color = os.environ.copy()
        env_with_color.pop("NO_COLOR", None)
        cmd = [sys.executable, "-m", "pubrun", "report", str(run_dir)]
        res_color = subprocess.run(cmd, capture_output=True, text=True, env=env_with_color)
        assert res_color.returncode == 0
        assert "PUBRUN DIAGNOSTICS" in res_color.stdout
        assert "failed" in res_color.stdout
        assert "1" in res_color.stdout
        assert "Exception" in res_color.stdout
        assert "ValueError: Invalid parameter" in res_color.stdout
        assert "Signals" in res_color.stdout
        assert "SIGTERM" in res_color.stdout
        # Unicode box boundaries or fallback ASCII should be present
        if sys.platform == "win32":
            assert "┌" in res_color.stdout or "+" in res_color.stdout
            assert "└" in res_color.stdout or "+" in res_color.stdout
        else:
            assert "┌" in res_color.stdout
            assert "└" in res_color.stdout

        # Print report WITHOUT color
        env_no_color = os.environ.copy()
        env_no_color["NO_COLOR"] = "1"
        res_no_color = subprocess.run(cmd, capture_output=True, text=True, env=env_no_color)
        assert res_no_color.returncode == 0
        assert "PUBRUN DIAGNOSTICS" in res_no_color.stdout
        assert "Status      : failed (1)" in res_no_color.stdout
        assert "Exception   : ValueError: Invalid parameter" in res_no_color.stdout
        assert "Signals     : SIGTERM" in res_no_color.stdout
        # ASCII boundary instead of Unicode box
        assert "===" in res_no_color.stdout
        assert "┌" not in res_no_color.stdout
        # No ANSI escape codes
        assert "\033[" not in res_no_color.stdout

    def test_report_crashed_run_tails_stderr(self, tmp_path):
        from pubrun.capture.liveness import get_hostname
        current_host = get_hostname()
        run_dir = tmp_path / "runs" / "pubrun-crashed"
        run_dir.mkdir(parents=True)
        # Create a mock lock file to simulate crashed run
        lock_data = {
            "run_id": "crashed-id",
            "pid": _dead_pid(),
            "started_at_utc": time.time() - 60,
            "script": "train.py",
            "argv": ["train.py", "--epochs", "10"],
            "hostname": current_host
        }
        with open(run_dir / ".pubrun.lock", "w", encoding="utf-8") as f:
            json.dump(lock_data, f)

        # Write more than 10 lines to stderr.log
        stderr_lines = [f"Line {i}\n" for i in range(1, 15)]
        with open(run_dir / "stderr.log", "w", encoding="utf-8") as f:
            f.writelines(stderr_lines)

        # Run report
        cmd = [sys.executable, "-m", "pubrun", "report", str(run_dir)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 1
        assert "Run directory 'pubrun-crashed' is currently crashed" in res.stderr
        assert "ERRO" in res.stderr
        assert "Last 10 lines of stderr.log:" in res.stderr
        # Check that we only see lines 5 to 14 (which are the last 10 lines)
        assert "Line 1\n" not in res.stderr
        assert "Line 4\n" not in res.stderr
        assert "Line 5\n" in res.stderr
        assert "Line 14\n" in res.stderr

    def test_report_crashed_run_tails_stdout_fallback(self, tmp_path):
        from pubrun.capture.liveness import get_hostname
        current_host = get_hostname()
        run_dir = tmp_path / "runs" / "pubrun-crashed-fallback"
        run_dir.mkdir(parents=True)
        # Create a mock lock file to simulate crashed run
        lock_data = {
            "run_id": "crashed-id",
            "pid": _dead_pid(),
            "started_at_utc": time.time() - 60,
            "script": "train.py",
            "argv": ["train.py", "--epochs", "10"],
            "hostname": current_host
        }
        with open(run_dir / ".pubrun.lock", "w", encoding="utf-8") as f:
            json.dump(lock_data, f)

        # Write more than 10 lines to stdout.log
        stdout_lines = [f"Out Line {i}\n" for i in range(1, 15)]
        with open(run_dir / "stdout.log", "w", encoding="utf-8") as f:
            f.writelines(stdout_lines)

        # Run report
        cmd = [sys.executable, "-m", "pubrun", "report", str(run_dir)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 1
        assert "Last 10 lines of stdout.log:" in res.stderr
        assert "Out Line 1\n" not in res.stderr
        assert "Out Line 4\n" not in res.stderr
        assert "Out Line 5\n" in res.stderr
        assert "Out Line 14\n" in res.stderr


class TestCliNewFeatures:

    def test_faulthandler_segfault_captured(self, tmp_path):
        script = """
import os, sys, ctypes
os.environ["PUBRUN_AUTO_START"] = "false"
import pubrun
tracker = pubrun.start(profile="standard", console={"capture_mode": "standard"})
# trigger segfault
ctypes.string_at(0)
"""
        script_file = tmp_path / "segfault.py"
        script_file.write_text(script, encoding="utf-8")

        env = os.environ.copy()
        res = subprocess.run([sys.executable, str(script_file)], env=env, capture_output=True, text=True, cwd=str(tmp_path))

        runs_dir = tmp_path / "runs"
        assert runs_dir.exists()
        run_folders = list(runs_dir.iterdir())
        assert len(run_folders) == 1
        run_dir = run_folders[0]

        stderr_log = run_dir / "stderr.log"
        assert stderr_log.exists()
        content = stderr_log.read_text(encoding="utf-8")
        # Under different platforms/interpreters, faulthandler might dump different headers or tracebacks.
        # We assert either standard segfault output or string_at / ctypes reference.
        assert any(x in content for x in ("Segmentation fault", "string_at", "ctypes"))

    def test_excepthook_stream_flushing(self, tmp_path):
        script = """
import os, sys
os.environ["PUBRUN_AUTO_START"] = "false"
import pubrun
tracker = pubrun.start(profile="standard", console={"capture_mode": "standard"})
sys.stdout.write("FLUSH_TEST_STDOUT")
sys.stderr.write("FLUSH_TEST_STDERR")
raise ValueError("TEST_EXCEPTION")
"""
        script_file = tmp_path / "flushing.py"
        script_file.write_text(script, encoding="utf-8")

        env = os.environ.copy()
        subprocess.run([sys.executable, str(script_file)], env=env, capture_output=True, text=True, cwd=str(tmp_path))

        runs_dir = tmp_path / "runs"
        assert runs_dir.exists()
        run_dir = list(runs_dir.iterdir())[0]

        stdout_log = run_dir / "stdout.log"
        stderr_log = run_dir / "stderr.log"

        assert stdout_log.exists()
        assert stderr_log.exists()

        assert "FLUSH_TEST_STDOUT" in stdout_log.read_text(encoding="utf-8")
        assert "FLUSH_TEST_STDERR" in stderr_log.read_text(encoding="utf-8")
        assert "TEST_EXCEPTION" in stderr_log.read_text(encoding="utf-8")

    def test_status_filtering_options(self, tmp_path):
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir(parents=True)
        base = time.time() - 4 * 86400

        # Create completed run
        run_completed = runs_dir / "pubrun-completed"
        run_completed.mkdir()
        (run_completed / "manifest.json").write_text(json.dumps({
            "schema_version": "1.0", "manifest_type": "pubrun-manifest",
            "run": {"run_id": "comp-id"},
            "status": {"outcome": "completed"},
            "invocation": {"script": {"basename": "train.py"}, "argv": ["train.py", "--lr", "0.01"]},
            "timing": {"started_at_utc": base}
        }), encoding="utf-8")

        # Create failed run
        run_failed = runs_dir / "pubrun-failed"
        run_failed.mkdir()
        (run_failed / "manifest.json").write_text(json.dumps({
            "schema_version": "1.0", "manifest_type": "pubrun-manifest",
            "run": {"run_id": "fail-id"},
            "status": {"outcome": "failed"},
            "invocation": {"script": {"basename": "eval.py"}, "argv": ["eval.py", "--batch", "32"]},
            "timing": {"started_at_utc": base + 100}
        }), encoding="utf-8")

        # Create crashed run
        run_crashed = runs_dir / "pubrun-crashed"
        run_crashed.mkdir()
        (run_crashed / ".pubrun.lock").write_text(json.dumps({
            "run_id": "crash-id", "pid": 99999, "started_at_utc": base + 200,
            "script": "preprocess.py", "argv": ["preprocess.py", "--split", "train"],
            "hostname": "otherhost"
        }), encoding="utf-8")

        # Verify status filter: completed
        cmd = [sys.executable, "-m", "pubrun", "status", "--dir", str(runs_dir), "--status", "completed"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "comp-id" in res.stdout
        assert "fail-id" not in res.stdout

        # Verify status filter: failed
        cmd = [sys.executable, "-m", "pubrun", "status", "--dir", str(runs_dir), "--status", "failed"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "fail-id" in res.stdout
        assert "comp-id" not in res.stdout

        # Verify limit: 1
        cmd = [sys.executable, "-m", "pubrun", "status", "--dir", str(runs_dir), "--limit", "1"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "crash-id" in res.stdout
        assert "fail-id" not in res.stdout
        assert "comp-id" not in res.stdout

        # Verify filter: "train"
        cmd = [sys.executable, "-m", "pubrun", "status", "--dir", str(runs_dir), "-f", "train"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "comp-id" in res.stdout
        assert "crash-id" in res.stdout
        assert "fail-id" not in res.stdout

        # Verify not-status filter: completed
        cmd = [sys.executable, "-m", "pubrun", "status", "--dir", str(runs_dir), "-S", "completed"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "comp-id" not in res.stdout
        assert "fail-id" in res.stdout
        assert "crash-id" in res.stdout

        # Verify not-filter: "train"
        cmd = [sys.executable, "-m", "pubrun", "status", "--dir", str(runs_dir), "-F", "train"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "fail-id" in res.stdout
        assert "comp-id" not in res.stdout
        assert "crash-id" not in res.stdout

    def test_subcommand_help_examples(self):
        for sub in ("report", "methods", "rerun", "diff", "meta", "status", "clean", "combined", "cite", "run", "ui", "tui", "gui", "self-check", "inspect"):
            cmd = [sys.executable, "-m", "pubrun", sub, "--help"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            assert res.returncode == 0
            assert "Examples:" in res.stdout
            after_examples = res.stdout.split("Examples:", 1)[1]
            expected_cmd = "ui" if sub in ("tui", "gui") else sub
            assert f"  pubrun {expected_cmd}" in after_examples

    def test_pbr_alias_registered_in_pyproject(self):
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject_path.exists()
        content = pyproject_path.read_text(encoding="utf-8")
        assert 'pbr = "pubrun.__main__:main"' in content

    def test_pbr_me_easter_egg(self):
        # Invoke main directly with modified argv[0] and argv[1]
        import sys
        from unittest.mock import patch
        from pubrun.__main__ import main

        with patch.object(sys, 'argv', ['/path/to/pbr', 'me']):
            # Capture stdout
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                with pytest.raises(SystemExit) as exc_info:
                    main()
            assert exc_info.value.code == 0
            assert f.getvalue().strip() == "ASAP"

    def test_empty_invocation_shows_help_and_run_count(self):
        import sys
        from unittest.mock import patch
        from pubrun.__main__ import main

        with patch("pubrun.status.scan_runs") as mock_scan:
            mock_scan.return_value = [object()]

            with patch.object(sys, 'argv', ['pubrun']):
                import io
                from contextlib import redirect_stdout
                f = io.StringIO()
                with redirect_stdout(f):
                    main()
                output = f.getvalue()
                assert output.splitlines()[0].startswith("usage: pubrun ")
                assert "Found 1 run(s) in the output directory." in output


class TestCliResourcesAliases:

    def test_res_average_flag(self):
        import sys
        from unittest.mock import patch
        from pubrun.__main__ import main

        # Test that 'pbr res --average 16528343' passes average=True to _run_resources
        with patch("pubrun.__main__._run_resources") as mock_run_resources:
            with patch.object(sys, 'argv', ['pbr', 'res', '--average', '16528343']):
                try:
                    main()
                except SystemExit:
                    pass
            mock_run_resources.assert_called_once_with(
                '16528343',
                filter_str=None,
                status_filter=None,
                older_than=None,
                exit_code=None,
                not_filter_str=None,
                not_status_filter=None,
                average=True,
                last=None,
                metric='all',
                width=None
            )

    def test_res_last_flag(self):
        import sys
        from unittest.mock import patch
        from pubrun.__main__ import main

        # Test that 'pbr res --last 10m 16528343' passes last='10m' to _run_resources
        with patch("pubrun.__main__._run_resources") as mock_run_resources:
            with patch.object(sys, 'argv', ['pbr', 'res', '--last', '10m', '16528343']):
                try:
                    main()
                except SystemExit:
                    pass
            mock_run_resources.assert_called_once_with(
                '16528343',
                filter_str=None,
                status_filter=None,
                older_than=None,
                exit_code=None,
                not_filter_str=None,
                not_status_filter=None,
                average=False,
                last='10m',
                metric='all',
                width=None
            )

    def test_res_width_flag(self):
        import sys
        from unittest.mock import patch
        from pubrun.__main__ import main

        # Test that 'pbr res --width 60 16528343' passes width=60 to _run_resources
        with patch("pubrun.__main__._run_resources") as mock_run_resources:
            with patch.object(sys, 'argv', ['pbr', 'res', '--width', '60', '16528343']):
                try:
                    main()
                except SystemExit:
                    pass
            mock_run_resources.assert_called_once_with(
                '16528343',
                filter_str=None,
                status_filter=None,
                older_than=None,
                exit_code=None,
                not_filter_str=None,
                not_status_filter=None,
                average=False,
                last=None,
                metric='all',
                width=60
            )

    def test_run_id_subcommand_swapping(self):
        import sys
        from unittest.mock import patch
        from pubrun.__main__ import main

        # Test swapping of 'pbr 16528343 cpu' -> 'pbr cpu 16528343'
        with patch("pubrun.__main__._run_resources") as mock_run_resources:
            with patch.object(sys, 'argv', ['pbr', '16528343', 'cpu']):
                try:
                    main()
                except SystemExit:
                    pass
            mock_run_resources.assert_called_once_with(
                '16528343',
                filter_str=None,
                status_filter=None,
                older_than=None,
                exit_code=None,
                not_filter_str=None,
                not_status_filter=None,
                average=False,
                last=None,
                metric='cpu',
                width=None
            )

        # Test swapping of 'pbr 16528343 cpu --width 60' -> 'pbr cpu 16528343 --width 60'
        with patch("pubrun.__main__._run_resources") as mock_run_resources:
            with patch.object(sys, 'argv', ['pbr', '16528343', 'cpu', '--width', '60']):
                try:
                    main()
                except SystemExit:
                    pass
            mock_run_resources.assert_called_once_with(
                '16528343',
                filter_str=None,
                status_filter=None,
                older_than=None,
                exit_code=None,
                not_filter_str=None,
                not_status_filter=None,
                average=False,
                last=None,
                metric='cpu',
                width=60
            )

    def test_resources_alias_routes_like_res(self):
        """`pubrun resources <run>` must route identically to `pubrun res <run>`.

        README.md documents `resources` as a backward-compatible alias of `res`.
        Previously the alias was unregistered and errored with "unknown command".
        """
        import sys
        from unittest.mock import patch
        from pubrun.__main__ import main

        with patch("pubrun.__main__._run_resources") as mock_run_resources:
            with patch.object(sys, 'argv', ['pbr', 'resources', '16528343']):
                try:
                    main()
                except SystemExit:
                    pass
            mock_run_resources.assert_called_once_with(
                '16528343',
                filter_str=None,
                status_filter=None,
                older_than=None,
                exit_code=None,
                not_filter_str=None,
                not_status_filter=None,
                average=False,
                last=None,
                metric='all',
                width=None
            )

    def test_resources_alias_recency_index_and_no_color(self):
        """Regression for the hand-maintained subcommands set (__main__.py:1891).

        The alias must also be recognized by the pre-subcommand run-ID swapping
        and the --no-color positioning logic, or `pbr resources 1` / `pbr 1
        resources` / `pbr --no-color resources 1` mis-parse.
        """
        import sys
        from unittest.mock import patch
        from pubrun.__main__ import main

        # Recency index as a positional after the alias.
        with patch("pubrun.__main__._run_resources") as mock_run_resources:
            with patch.object(sys, 'argv', ['pbr', 'resources', '1']):
                try:
                    main()
                except SystemExit:
                    pass
            mock_run_resources.assert_called_once_with(
                '1',
                filter_str=None,
                status_filter=None,
                older_than=None,
                exit_code=None,
                not_filter_str=None,
                not_status_filter=None,
                average=False,
                last=None,
                metric='all',
                width=None
            )

        # Pre-subcommand run-ID swapping: 'pbr 1 resources' -> 'pbr resources 1'.
        with patch("pubrun.__main__._run_resources") as mock_run_resources:
            with patch.object(sys, 'argv', ['pbr', '1', 'resources']):
                try:
                    main()
                except SystemExit:
                    pass
            mock_run_resources.assert_called_once_with(
                '1',
                filter_str=None,
                status_filter=None,
                older_than=None,
                exit_code=None,
                not_filter_str=None,
                not_status_filter=None,
                average=False,
                last=None,
                metric='all',
                width=None
            )

        # --no-color placed before the alias must be stripped without breaking it.
        with patch("pubrun.__main__._run_resources") as mock_run_resources:
            with patch.object(sys, 'argv', ['pbr', '--no-color', 'resources', '1']):
                try:
                    main()
                except SystemExit:
                    pass
            mock_run_resources.assert_called_once_with(
                '1',
                filter_str=None,
                status_filter=None,
                older_than=None,
                exit_code=None,
                not_filter_str=None,
                not_status_filter=None,
                average=False,
                last=None,
                metric='all',
                width=None
            )

    def test_dead_dispatch_aliases_error_cleanly(self, capsys):
        """`monitor`/`chart`/`stats` were dead dispatch strings; they must error
        as unknown commands, not silently route to resources."""
        import sys
        from unittest.mock import patch
        from pubrun.__main__ import main

        for dead in ("monitor", "chart", "stats"):
            with patch.object(sys, 'argv', ['pbr', dead]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 2, f"'{dead}' should exit with code 2"
                captured = capsys.readouterr()
                assert f"unknown command '{dead}'" in captured.err


class TestCliRerunPreflightAndShowReproducibility:
    """Behavioral CLI tests for `pubrun rerun --preflight` and `pubrun show` reproducibility (IPD 3lqtlt)."""

    @staticmethod
    def _make_run(tmp_path: Path, name: str, *, rerun_command, extra: dict = None) -> Path:
        import platform
        import socket

        run_dir = tmp_path / "runs" / name
        run_dir.mkdir(parents=True, exist_ok=True)
        script = tmp_path / "work.py"
        if not script.exists():
            script.write_text("print('hi')\n", encoding="utf-8")
        manifest = {
            "schema_version": "1.0",
            "manifest_type": "pubrun-manifest",
            "run": {"run_id": name, "capture_state": {"status": "complete"}},
            "timing": {"started_at_utc": 1780250000.0, "elapsed_seconds": 3.0},
            "status": {"outcome": "completed", "exit_code": 0, "capture_state": {"status": "complete"}},
            "host": {
                "hostname": socket.gethostname(),
                "os_name": platform.system(),
                "capture_state": {"status": "complete"},
            },
            "python": {
                "version": platform.python_version(),
                "executable": sys.executable,
                "capture_state": {"status": "complete"},
            },
            "hardware": {"cpu": {"model": "TestCPU"}, "memory_total_bytes": 8 * 1024**3, "capture_state": {"status": "complete"}},
            "packages": {"mode": "full-environment", "records": [], "capture_state": {"status": "complete"}},
            "git": {"capture_state": {"status": "suppressed"}},
            "invocation": {
                "entrypoint_type": "script",
                "script": {"path": str(script), "basename": "work.py"},
                "argv": [str(script)],
                "working_directory": {"path": str(tmp_path)},
                "rerun_command": rerun_command,
            },
            "resources": {"scope": "tree", "capture_state": {"status": "complete"}},
            "console": {"capture_mode": "standard", "capture_state": {"status": "complete"}},
            "subprocesses": [],
            "capture": {"subprocesses_enabled": True, "file_provenance_available": True},
            "pubrun_imports": {"selected_mode": "auto", "selected_behavior": {"patch_subprocesses": True}},
            "determinism": {"registered_seeds": [{"name": "random", "value": 1}]},
            "config": {"notices": []},
            "errors": {"records": [], "capture_state": {"status": "complete"}},
            "data_files": {"inputs": [], "outputs": [], "mixed": []},
        }
        if extra:
            manifest.update(extra)
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return run_dir

    def test_rerun_default_stdout_is_pipe_clean(self, tmp_path):
        cmd_str = f"cd {tmp_path} && python work.py --epochs 3"
        run_dir = self._make_run(tmp_path, "pubrun-pipe-clean", rerun_command=cmd_str)
        res = run_pubrun("rerun", str(run_dir), env={"NO_COLOR": "1"})
        assert res.returncode == 0
        assert res.stderr == ""
        expected = cmd_str.replace(" && python ", "\npython ").replace("'", '"') if sys.platform == "win32" else cmd_str
        assert res.stdout.strip() == expected

    @pytest.mark.parametrize(
        "extra_flags",
        [
            ["--strict"],
            ["--fail-on", "warn"],
            ["--fail-on", "mismatch"],
            ["--fail-on", "unknown"],
            ["--json"],
        ],
    )
    def test_rerun_rejects_preflight_only_flags_without_preflight(self, tmp_path, extra_flags):
        run_dir = self._make_run(tmp_path, "pubrun-badflags", rerun_command="python work.py")
        res = run_pubrun("rerun", str(run_dir), *extra_flags, env={"NO_COLOR": "1"})
        assert res.returncode == 2
        assert res.stdout == ""
        assert "--preflight" in res.stderr

    def test_rerun_preflight_missing_rerun_command_exits_1_cleanly(self, tmp_path):
        run_dir = self._make_run(tmp_path, "pubrun-nocmd", rerun_command=None)
        res = run_pubrun("rerun", str(run_dir), "--preflight", env={"NO_COLOR": "1"})
        assert res.returncode == 1
        assert res.stdout == ""
        assert "rerun_command" in res.stderr

        res_json = run_pubrun("rerun", str(run_dir), "--preflight", "--json", env={"NO_COLOR": "1"})
        assert res_json.returncode == 1
        assert res_json.stdout == ""

    def test_rerun_preflight_separates_stderr_and_stdout_and_never_executes(self, tmp_path):
        from pubrun.report.reproducibility import NON_GUARANTEE_DISCLAIMER

        marker = tmp_path / "must_not_exist.txt"
        sentinel_script = tmp_path / "side_effect.py"
        sentinel_script.write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
            encoding="utf-8",
        )
        cmd_str = f"cd {tmp_path} && python {sentinel_script}"
        run_dir = self._make_run(tmp_path, "pubrun-pf-sep", rerun_command=cmd_str)

        res = run_pubrun("rerun", str(run_dir), "--preflight", env={"NO_COLOR": "1"})
        assert res.returncode == 0, res.stderr
        assert "\033[" not in res.stdout
        assert "\033[" not in res.stderr
        expected = cmd_str.replace(" && python ", "\npython ").replace("'", '"') if sys.platform == "win32" else cmd_str
        assert res.stdout.strip() == expected
        assert "Summary:" in res.stderr
        assert "Preflight [" in res.stderr
        assert NON_GUARANTEE_DISCLAIMER in res.stderr
        assert not marker.exists(), "pubrun rerun --preflight must never execute the recorded command"

    def test_rerun_preflight_strict_and_fail_on_suppress_stdout_on_mismatch_and_redaction(self, tmp_path):
        # 1. Package mismatch -> --strict and --fail-on mismatch exit 1 with empty stdout.
        mm_dir = self._make_run(
            tmp_path,
            "pubrun-pf-mismatch",
            rerun_command=f"cd {tmp_path} && python work.py",
            extra={
                "packages": {
                    "mode": "full-environment",
                    "records": [{"name": "nonexistent-pkg-for-rerun-test", "version": "1.2.3"}],
                    "capture_state": {"status": "complete"},
                }
            },
        )
        res_strict = run_pubrun("rerun", str(mm_dir), "--preflight", "--strict", env={"NO_COLOR": "1"})
        assert res_strict.returncode == 1
        assert res_strict.stdout == ""
        assert "Summary:" in res_strict.stderr

        res_mm = run_pubrun(
            "rerun", str(mm_dir), "--preflight", "--fail-on", "mismatch", env={"NO_COLOR": "1"}
        )
        assert res_mm.returncode == 1
        assert res_mm.stdout == ""

        # 2. Redacted rerun_command -> advisory on stderr; non-strict prints command, strict suppresses stdout.
        red_cmd = f"cd {tmp_path} && python work.py --api-key [REDACTED]"
        red_dir = self._make_run(tmp_path, "pubrun-pf-redacted", rerun_command=red_cmd)

        res_red = run_pubrun("rerun", str(red_dir), "--preflight", env={"NO_COLOR": "1"})
        assert res_red.returncode == 0
        assert "[REDACTED]" in res_red.stdout
        assert "[REDACTED]" in res_red.stderr
        assert "not directly executable" in res_red.stderr.lower()

        res_red_strict = run_pubrun(
            "rerun", str(red_dir), "--preflight", "--fail-on", "mismatch", env={"NO_COLOR": "1"}
        )
        assert res_red_strict.returncode == 1
        assert res_red_strict.stdout == ""

        # 3. --preflight --json emits structured payload with executable_as_printed.
        res_red_json = run_pubrun(
            "rerun", str(red_dir), "--preflight", "--json", env={"NO_COLOR": "1"}
        )
        assert res_red_json.returncode == 0
        payload = json.loads(res_red_json.stdout)
        assert payload["executable_as_printed"] is False
        assert "[REDACTED]" in payload["rerun_command"]
        assert payload["assessment"]["mode"] == "preflight"
        assert payload["assessment"]["preflight"]["requested"] is True

        res_red_json_strict = run_pubrun(
            "rerun", str(red_dir), "--preflight", "--strict", "--json", env={"NO_COLOR": "1"}
        )
        assert res_red_json_strict.returncode == 1
        payload_strict = json.loads(res_red_json_strict.stdout)
        assert payload_strict["executable_as_printed"] is False

    def test_rerun_preflight_lock_file_running_and_crashed_runs(self, tmp_path):
        import time

        run_dir = tmp_path / "runs" / "pubrun-lock-pf"
        run_dir.mkdir(parents=True)
        lock_data = {
            "run_id": "lock-pf-id",
            "pid": 99999,
            "started_at_utc": time.time() - 200000,
            "script": "train.py",
            "argv": ["--token", "[REDACTED]"],
            "sys_argv": ["train.py", "--token", "[REDACTED]"],
            "hostname": "otherhost",
            "cwd": str(tmp_path),
        }
        (run_dir / ".pubrun.lock").write_text(json.dumps(lock_data), encoding="utf-8")

        # Human mode without --strict: warns preflight needs finalized manifest, prints inferred command.
        res = run_pubrun("rerun", str(run_dir), "--preflight", env={"NO_COLOR": "1"})
        assert res.returncode == 0
        assert "manifest.json" in res.stderr
        assert "inferred" in res.stderr.lower()
        assert "[REDACTED]" in res.stderr
        assert "train.py" in res.stdout

        # Strict / --fail-on mode: exits 1 with empty stdout.
        res_strict = run_pubrun(
            "rerun", str(run_dir), "--preflight", "--fail-on", "unknown", env={"NO_COLOR": "1"}
        )
        assert res_strict.returncode == 1
        assert res_strict.stdout == ""

        # JSON mode: valid JSON with unknown preflight status and inferred evidence_status.
        res_json = run_pubrun("rerun", str(run_dir), "--preflight", "--json", env={"NO_COLOR": "1"})
        assert res_json.returncode == 0
        data = json.loads(res_json.stdout)
        assert data["executable_as_printed"] is False
        assert data["assessment"]["mode"] == "preflight"
        assert data["assessment"]["preflight"]["requested"] is True
        assert data["assessment"]["preflight"]["status"] == "unknown"
        assert any(f["evidence_status"] == "inferred" for f in data["assessment"]["findings"])

        # JSON + --strict exits 1 while still emitting valid JSON.
        res_json_strict = run_pubrun(
            "rerun", str(run_dir), "--preflight", "--strict", "--json", env={"NO_COLOR": "1"}
        )
        assert res_json_strict.returncode == 1
        assert json.loads(res_json_strict.stdout)["assessment"]["preflight"]["status"] == "unknown"

    def test_show_reproducibility_depths_sections_and_meta_ref(self, tmp_path):
        from pubrun.report.reproducibility import NON_GUARANTEE_DISCLAIMER

        run_dir = self._make_run(
            tmp_path,
            "pubrun-show-repro",
            rerun_command=f"cd {tmp_path} && python work.py",
            extra={
                "meta_ref": "meta.json",
                "hardware": {"capture_state": {"status": "suppressed"}},
                "environment": {
                    "variables": [
                        {"name": "FOO", "value": {"representation": "plain", "value": "bar"}}
                    ]
                },
                "packages": {
                    "mode": "full-environment",
                    "records": [{"name": "pytest", "version": "8.0.0"}],
                    "capture_state": {"status": "complete"},
                },
            },
        )
        (run_dir / "meta.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "manifest_type": "pubrun-meta-snapshot",
                    "timing": {"started_at_utc": 1780249900.0},
                    "hardware": {
                        "cpu": {"model": "ParentCPU"},
                        "memory_total_bytes": 16 * 1024**3,
                        "capture_state": {"status": "complete"},
                    },
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "stdout.log").write_text("log line\n", encoding="utf-8")

        # Standard depth includes Reproducibility summary, inherited note, disclaimer, preflight nudge.
        res_std = run_pubrun("show", str(run_dir), env={"NO_COLOR": "1"})
        assert res_std.returncode == 0, res_std.stderr
        assert "\033[" not in res_std.stdout
        assert "--- Reproducibility ---" in res_std.stdout
        assert "Inherited from parent snapshot: hardware" in res_std.stdout
        assert "Next step:" in res_std.stdout
        assert NON_GUARANTEE_DISCLAIMER in res_std.stdout
        assert "pubrun inspect --preflight" in res_std.stdout

        # Deep depth also includes Reproducibility summary and zero ANSI DIM codes when colored.
        env_color = dict(os.environ)
        env_color.pop("NO_COLOR", None)
        res_deep = run_pubrun("show", str(run_dir), "--deep", env={"NO_COLOR": ""})
        assert res_deep.returncode == 0, res_deep.stderr
        assert "--- Reproducibility ---" in res_deep.stdout
        repro_block = res_deep.stdout.split("--- Reproducibility ---", 1)[1].split("--- Deep Information ---", 1)[0]
        assert "\033[2m" not in repro_block

        # Basic depth excludes Reproducibility summary.
        res_basic = run_pubrun("show", str(run_dir), "--basic", env={"NO_COLOR": "1"})
        assert res_basic.returncode == 0
        assert "--- Reproducibility ---" not in res_basic.stdout

        # Section extracts (logs, env, packages) remain untouched.
        for sec in ("logs", "env", "packages"):
            res_sec = run_pubrun("show", str(run_dir), sec, env={"NO_COLOR": "1"})
            assert res_sec.returncode == 0
            assert "--- Reproducibility ---" not in res_sec.stdout
            assert "PUBRUN DIAGNOSTICS" not in res_sec.stdout
