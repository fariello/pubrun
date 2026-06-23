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
