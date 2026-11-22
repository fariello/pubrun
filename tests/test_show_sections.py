"""Tests for show subcommand, section filtering, and standalone resource commands."""
import json
import os
import sys
import subprocess
import pytest
from pathlib import Path

PYTHON = sys.executable


def run_pubrun(*args, cwd=None):
    """Helper to invoke pubrun CLI and return the completed process."""
    cmd = [str(PYTHON), "-m", "pubrun"] + [str(a) for a in args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else os.getcwd(),
        timeout=30
    )


@pytest.fixture
def run_dir(tmp_path):
    """Create a real pubrun execution to test show/resources against."""
    run_dir_path = tmp_path / "runs" / "pubrun-20260623-173536-abcdef"
    run_dir_path.mkdir(parents=True, exist_ok=True)

    # Write manifest.json
    manifest = {
        "run": {"run_id": "20260623-173536-abcdef"},
        "timing": {"started_at_utc": 100.0, "elapsed_seconds": 20.0},
        "status": {"outcome": "completed"},
        "invocation": {"script": {"basename": "test_script.py"}, "argv": ["--epochs", "5"]},
        "resources": {"peak_rss_bytes": 1024**2 * 180, "peak_cpu_percent": 55.0, "end_rss_bytes": 1024**2 * 180},
        "environment": {"variables": [{"name": "MY_TEST_VAR", "value": {"representation": "plain", "value": "test_value"}}]},
        "packages": {"records": [{"name": "numpy", "version": "1.24.0"}, {"name": "torch", "version": "2.0.1"}]}
    }
    manifest_path = run_dir_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    # Write events.jsonl
    events = [
        {"type": "resource_sample", "timestamp_utc": 100.0, "payload": {"rss_bytes": int(1024**2 * 150), "cpu_percent": 45.0}},
        {"type": "resource_sample", "timestamp_utc": 110.0, "payload": {"rss_bytes": int(1024**2 * 180), "cpu_percent": 55.0}},
    ]
    events_path = run_dir_path / "events.jsonl"
    with open(events_path, "w", encoding="utf-8") as ef:
        for ev in events:
            ef.write(json.dumps(ev) + "\n")

    # Write stdout.log and stderr.log
    stdout_log = run_dir_path / "stdout.log"
    stderr_log = run_dir_path / "stderr.log"
    stdout_log.write_text("Standard Output Log Content\n", encoding="utf-8")
    stderr_log.write_text("Standard Error Log Content\n", encoding="utf-8")

    return run_dir_path


def test_show_full_report(run_dir, tmp_path):
    """pubrun show <run_dir> should display full report."""
    result = run_pubrun("show", str(run_dir), cwd=str(tmp_path))
    assert result.returncode == 0
    assert "PUBRUN DIAGNOSTICS" in result.stdout
    assert "Basic Information" in result.stdout
    assert "Standard Information" in result.stdout


def test_show_env(run_dir, tmp_path):
    """pubrun show <run_dir> env should display only environment variables."""
    result = run_pubrun("show", str(run_dir), "env", cwd=str(tmp_path))
    assert result.returncode == 0
    assert "Environment Variables" in result.stdout
    assert "PUBRUN DIAGNOSTICS" not in result.stdout


def test_show_packages(run_dir, tmp_path):
    """pubrun show <run_dir> packages should display only packages."""
    result = run_pubrun("show", str(run_dir), "packages", cwd=str(tmp_path))
    assert result.returncode == 0
    assert "Packages" in result.stdout
    assert "PUBRUN DIAGNOSTICS" not in result.stdout


def test_show_logs(run_dir, tmp_path):
    """pubrun show <run_dir> logs should print stdout and stderr logs."""
    result = run_pubrun("show", str(run_dir), "logs", cwd=str(tmp_path))
    assert result.returncode == 0
    assert "Standard Output Log Content" in result.stdout
    assert "Standard Error Log Content" in result.stdout
    assert "PUBRUN DIAGNOSTICS" not in result.stdout


def test_show_option_shifting_env(run_dir, tmp_path):
    """pubrun show env should shift 'env' to section and default to latest run."""
    # Since we run inside tmp_path where the run_dir was generated:
    result = run_pubrun("show", "env", cwd=str(tmp_path))
    assert result.returncode == 0
    assert "Environment Variables" in result.stdout
    assert "PUBRUN DIAGNOSTICS" not in result.stdout


def test_show_option_shifting_packages(run_dir, tmp_path):
    """pubrun show packages should shift 'packages' to section and default to latest run."""
    result = run_pubrun("show", "packages", cwd=str(tmp_path))
    assert result.returncode == 0
    assert "Packages" in result.stdout
    assert "PUBRUN DIAGNOSTICS" not in result.stdout


def test_show_option_shifting_logs(run_dir, tmp_path):
    """pubrun show logs should shift 'logs' to section and default to latest run."""
    result = run_pubrun("show", "logs", cwd=str(tmp_path))
    assert result.returncode == 0
    assert "Standard Output Log Content" in result.stdout
    assert "Standard Error Log Content" in result.stdout


def test_hidden_report_command(run_dir, tmp_path):
    """report command should work exactly like show (including option shifting) but be hidden."""
    # Check execution
    result = run_pubrun("report", "env", cwd=str(tmp_path))
    assert result.returncode == 0
    assert "Environment Variables" in result.stdout

    # Check help does not list 'report' but lists 'show'
    result_help = run_pubrun("--help", cwd=str(tmp_path))
    assert "show " in result_help.stdout
    # report is suppressed/hidden
    assert "  report " not in result_help.stdout


def test_cpu_command(run_dir, tmp_path):
    """cpu command should only print CPU utilization chart."""
    result = run_pubrun("cpu", str(run_dir), cwd=str(tmp_path))
    assert result.returncode == 0
    assert "CPU Utilization History" in result.stdout
    assert "Memory (RSS) History" not in result.stdout


def test_mem_command(run_dir, tmp_path):
    """mem command should only print Memory utilization chart."""
    result = run_pubrun("mem", str(run_dir), cwd=str(tmp_path))
    assert result.returncode == 0
    assert "Memory (RSS) History" in result.stdout
    assert "CPU Utilization History" not in result.stdout


def test_res_command(run_dir, tmp_path):
    """res command should print both CPU and Memory utilization charts."""
    result = run_pubrun("res", str(run_dir), cwd=str(tmp_path))
    assert result.returncode == 0
    assert "CPU Utilization History" in result.stdout
    assert "Memory (RSS) History" in result.stdout


def test_width_option(run_dir, tmp_path):
    """Test that passing -w/--width overrides the chart width."""
    result = run_pubrun("cpu", str(run_dir), "--width", "45", cwd=str(tmp_path))
    assert result.returncode == 0
    axis_lines = [line for line in result.stdout.splitlines() if "└" in line or "+" in line]
    # Check that at least one axis line exists with length = 13 spaces + 1 corner + 45 width = 59
    assert any(len(line.rstrip()) == 59 for line in axis_lines)


def test_swapped_command_args(run_dir, tmp_path):
    """Passing run ID before subcommand should swap and execute correctly."""
    result = run_pubrun(str(run_dir), "cpu", cwd=str(tmp_path))
    assert result.returncode == 0
    assert "CPU Utilization History" in result.stdout


class TestShowDataFilesProvenance:
    """Behavioral tests for File Provenance rendering in pubrun show / print_report (IPD hm32d9)."""

    def _rich_manifest(self):
        return {
            "run": {"run_id": "20261121-120000-fp01"},
            "timing": {"started_at_utc": 1780250000.0, "elapsed_seconds": 12.0},
            "status": {"outcome": "completed"},
            "invocation": {"script": {"basename": "train.py"}, "argv": ["train.py"]},
            "host": {"os_name": "Linux", "hostname": "node-1"},
            "hardware": {"cpu": {"model": "TestCPU"}, "memory_total_bytes": 8 * 1024**3},
            "python": {"version": "3.11.5", "executable": "/usr/bin/python3"},
            "git": {"commit": "abcdef1234567890"},
            "environment": {"variables": [{"name": "MODE", "value": {"representation": "plain", "value": "prod"}}]},
            "packages": {"records": [{"name": "numpy", "version": "1.26.0"}]},
            "data_files": {
                "inputs": [
                    {
                        "path": "data/train.csv",
                        "role": "input",
                        "mode": "rb",
                        "label": "train_set",
                        "hash_status": "completed",
                        "hash_algorithm": "sha512",
                        "sha256": None,
                        "digest": {"algorithm": "sha512", "value": "1234567890abcdef" * 8},
                        "evidence_source": "observed",
                        "evidence_strength": "verified_content",
                    },
                    {
                        "path": "ext/features.parquet",
                        "role": "input",
                        "label": "ext\n\x1b[31minjected\x1b[0m\tlabel",
                        "hash_status": "asserted",
                        "hash_algorithm": "sha256",
                        "caller_digest": {"algorithm": "sha256", "value": "fedcba9876543210" * 4, "verified": None},
                        "digest": {"algorithm": "sha256", "value": "fedcba9876543210" * 4},
                        "evidence_source": "asserted",
                        "evidence_strength": "asserted_content",
                    },
                    {
                        "path": "data/stat_only.csv",
                        "role": "input",
                        "mode": "r",
                        "hash_status": "disabled",
                        "evidence_source": "observed",
                        "evidence_strength": "metadata_only",
                    },
                    {
                        "path": "data/name_only\nline2.csv",
                        "role": "input",
                        "hash_status": "disabled",
                        "evidence_source": "observed",
                        "evidence_strength": "path_only",
                    },
                    {
                        "path": "data/huge.bin",
                        "role": "input",
                        "hash_status": "over_budget",
                        "hash_status_detail": "file size exceeded max_hash_bytes",
                        "digest": {"algorithm": "sha256", "value": "aaaa1111bbbb2222" * 4},
                        "evidence_source": "observed",
                        "evidence_strength": "metadata_only",
                    },
                    {
                        "path": "data/missing.csv",
                        "role": "input",
                        "hash_status": "unavailable",
                        "hash_status_detail": "file does not exist",
                        "evidence_source": "none",
                        "evidence_strength": "unavailable",
                    },
                    {
                        "path": "data/corrupt.csv",
                        "role": "input",
                        "hash_status": "failed",
                        "hash_status_detail": "caller_digest_mismatch",
                        "caller_digest": {"algorithm": "sha256", "value": "9999888877776666" * 4, "verified": False},
                        "evidence_source": "observed",
                        "evidence_strength": "changed_unverified",
                    },
                ],
                "outputs": [
                    {
                        "path": "out/model.pt",
                        "role": "output",
                        "hash_status": "pending",
                        "evidence_source": "none",
                        "evidence_strength": "path_only",
                    }
                ],
                "mixed": [
                    {
                        "path": "work/state.db",
                        "role": "input_output",
                        "mode": "r+",
                        "hash_status": "file_changed",
                        "change_detected": True,
                        "hash_status_detail": "file changed during hashing",
                        "sha256": "deadbeef00001111" * 4,
                        "evidence_source": "observed",
                        "evidence_strength": "changed_unverified",
                    }
                ],
            },
        }

    def test_cli_show_standard_and_deep_with_no_color_and_all_badges(self, tmp_path):
        run_path = tmp_path / "runs" / "pubrun-20261121-120000-fp01"
        run_path.mkdir(parents=True)
        (run_path / "manifest.json").write_text(json.dumps(self._rich_manifest()), encoding="utf-8")

        env = dict(os.environ)
        src_dir = Path(__file__).resolve().parents[1] / "src"
        if src_dir.is_dir():
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing}" if existing else str(src_dir)
        env["NO_COLOR"] = "1"

        res_std = subprocess.run(
            [str(PYTHON), "-m", "pubrun", "show", str(run_path)],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            env=env,
            timeout=30,
        )
        assert res_std.returncode == 0, res_std.stderr
        assert "\033[" not in res_std.stdout
        assert "Data Files" in res_std.stdout
        assert "9 tracked" in res_std.stdout
        assert "1 verified" in res_std.stdout
        assert "1 asserted" in res_std.stdout
        assert "2 identified-only" in res_std.stdout
        assert "1 over-budget" in res_std.stdout
        assert "1 pending" in res_std.stdout
        assert "1 changed" in res_std.stdout
        assert "2 failed/unavailable" in res_std.stdout

        res_deep = subprocess.run(
            [str(PYTHON), "-m", "pubrun", "show", str(run_path), "--deep"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            env=env,
            timeout=30,
        )
        assert res_deep.returncode == 0, res_deep.stderr
        out = res_deep.stdout
        assert "\033[" not in out
        assert "[ Data Files ]" in out
        for badge in (
            "[verified]",
            "[asserted]",
            "[metadata-only]",
            "[path-only]",
            "[over-budget]",
            "[pending]",
            "[changed]",
            "[unavailable]",
            "[failed]",
        ):
            assert badge in out, f"missing badge {badge} in:\n{out}"

        # Non-SHA-256 verified digest and asserted caller_digest shown; anomaly hashes never shown.
        assert "sha512:1234567890ab" in out
        assert "sha256:fedcba987654" in out
        assert "aaaa1111bbbb" not in out
        assert "999988887777" not in out
        assert "deadbeef0000" not in out

        # Anomaly details are surfaced.
        assert "caller_digest_mismatch" in out
        assert "file changed during hashing" in out
        assert "file size exceeded max_hash_bytes" in out
        assert "file does not exist" in out

        # Labels and paths are sanitized to single line with ANSI stripped.
        assert "[label=ext injected label]" in out
        assert "data/name_only line2.csv" in out

    def test_print_report_color_uses_no_dim_and_handles_legacy_malformed_and_sections(
        self, tmp_path, monkeypatch, capsys
    ):
        from pubrun.report.diagnostics import SHOW_SECTIONS, print_report

        assert SHOW_SECTIONS == ("logs", "env", "packages")

        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(self._rich_manifest()), encoding="utf-8")

        # Color enabled: File Provenance lines must never use Colors.DIM (\033[2m).
        monkeypatch.delenv("NO_COLOR", raising=False)
        print_report(str(manifest_path), depth="deep")
        colored_out = capsys.readouterr().out
        df_section = colored_out.split("[ Data Files ]", 1)[1].split("[ Subprocesses ]", 1)[0]
        assert "\033[2m" not in df_section
        for line in colored_out.splitlines():
            if "Data Files" in line:
                assert "\033[2m" not in line

        # Legacy manifest omitting mixed and hash_status renders cleanly.
        monkeypatch.setenv("NO_COLOR", "1")
        legacy = {
            "run": {"run_id": "legacy01"},
            "timing": {"started_at_utc": 1780250000.0, "elapsed_seconds": 1.0},
            "status": {"outcome": "completed"},
            "invocation": {"script": {"basename": "old.py"}, "argv": []},
            "data_files": {
                "inputs": [
                    {"path": "old_hashed.csv", "sha256": "0123456789abcdef" * 4},
                    {"path": "old_stat.csv", "size_bytes": 100},
                ],
                "outputs": [],
            },
        }
        manifest_path.write_text(json.dumps(legacy), encoding="utf-8")
        print_report(str(manifest_path), depth="deep")
        leg_out = capsys.readouterr().out
        assert "\033[" not in leg_out
        assert "2 tracked (1 verified, 1 identified-only)" in leg_out
        assert "[verified] old_hashed.csv" in leg_out
        assert "sha256:0123456789ab" in leg_out
        assert "[metadata-only] old_stat.csv" in leg_out

        # Malformed data_files never raises and shows (None captured) in deep view.
        malformed = {
            "run": {"run_id": "bad01"},
            "timing": {"started_at_utc": 1780250000.0, "elapsed_seconds": 1.0},
            "status": {"outcome": "completed"},
            "invocation": {"script": {"basename": "bad.py"}, "argv": []},
            "data_files": {"inputs": "not-a-list", "outputs": [None, 42], "mixed": None},
        }
        manifest_path.write_text(json.dumps(malformed), encoding="utf-8")
        print_report(str(manifest_path), depth="deep")
        bad_out = capsys.readouterr().out
        assert "[ Data Files ]" in bad_out
        assert "(None captured)" in bad_out
        assert "Data Files  :" not in bad_out
