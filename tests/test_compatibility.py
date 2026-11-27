"""Compatibility, workflow matrix, and local scaling-benchmark smoke tests."""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CI_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yml"
_AUDIT_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "dependency-audit.yml"
_SCALING_BENCH = _REPO_ROOT / "benchmarks" / "scaling_bench.py"
_SHARE_SAFETY = _REPO_ROOT / "benchmarks" / "share_safety.py"


def _load_share_safety():
    spec = importlib.util.spec_from_file_location("_test_compat_share_safety", _SHARE_SAFETY)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _extract_job_block(text: str, job_name: str) -> str:
    """Extract a two-space-indented job block under ``jobs:`` without PyYAML."""
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if re.match(rf"^  {re.escape(job_name)}:\s*$", line):
            start = idx
            break
    assert start is not None, f"job {job_name!r} not found"
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        if re.match(r"^  [A-Za-z0-9_-]+:\s*$", line) or re.match(r"^[A-Za-z0-9_-]+:", line):
            break
        collected.append(line)
    return "\n".join(collected)


def test_scaling_benchmark_quick_smoke_and_share_safety(tmp_path: Path) -> None:
    """Run benchmarks/scaling_bench.py --quick and verify JSON schema, cleanup, and redaction."""
    workdir = tmp_path / "bench-workdir"
    workdir.mkdir()
    sibling = workdir / "keep-me.txt"
    sibling.write_text("preserve sibling\n", encoding="utf-8")
    json_out = tmp_path / "scaling.json"

    proc = subprocess.run(
        [
            sys.executable,
            str(_SCALING_BENCH),
            "--quick",
            "--workdir",
            str(workdir),
            "--json-out",
            str(json_out),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert json_out.is_file(), "scaling_bench.py did not create --json-out file"

    # Only the pre-existing sibling remains inside --workdir (no leftover ephemeral subdirs).
    remaining = sorted(p.name for p in workdir.iterdir())
    assert remaining == ["keep-me.txt"], f"unexpected leftovers in workdir: {remaining}"
    assert sibling.read_text(encoding="utf-8") == "preserve sibling\n"

    json_text = json_out.read_text(encoding="utf-8")
    data = json.loads(json_text)
    assert data["schema_version"] == "pubrun-scaling-bench/1"
    assert data["mode"] == "quick"

    scenarios = data["scenarios"]
    assert set(scenarios.keys()) == {
        "file_io",
        "run_scan_lookup",
        "inactive_hot_path",
        "large_manifest_diff",
    }

    fio = scenarios["file_io"]
    assert fio["file_count"] == 200
    assert fio["open_median_ms"] >= 0
    assert fio["register_input_median_ms"] >= 0
    assert fio["open_ms_per_1000"] >= 0
    assert fio["register_input_ms_per_1000"] >= 0

    rsl = scenarios["run_scan_lookup"]
    assert rsl["run_count"] == 100
    assert rsl["scanned_count"] == 100
    assert rsl["scan_median_ms"] >= 0
    assert rsl["find_exact_id_with_runs_median_ms"] >= 0
    assert rsl["find_recency_with_runs_median_ms"] >= 0
    assert rsl["scan_manifest_parses"] == 100
    assert rsl["find_with_runs_manifest_parses"] == 0
    assert rsl["find_direct_manifest_parses"] == 1

    ihp = scenarios["inactive_hot_path"]
    assert ihp["call_count"] == 1000
    assert ihp["annotate_median_ms"] >= 0
    assert ihp["annotate_us_per_call"] >= 0
    assert ihp["print_median_ms"] >= 0
    assert ihp["print_us_per_call"] >= 0

    lmd = scenarios["large_manifest_diff"]
    assert lmd["package_count"] == 100
    assert lmd["env_count"] == 100
    assert lmd["array_length"] == 200
    assert lmd["standard_diff_median_ms"] >= 0
    assert lmd["deep_diff_median_ms"] >= 0
    assert lmd["array_diff_median_ms"] >= 0

    share_safety = _load_share_safety()
    ok_json, reasons_json = share_safety.check_share_safe_text(json_text)
    assert ok_json and not reasons_json, reasons_json
    ok_stdout, reasons_stdout = share_safety.check_share_safe_text(
        json.dumps({"stdout": proc.stdout})
    )
    assert ok_stdout and not reasons_stdout, reasons_stdout

    assert str(workdir) not in json_text
    assert str(workdir) not in proc.stdout


def test_ci_workflow_compatibility_matrix_structural() -> None:
    """Always-on stdlib structural checks for .github/workflows/ci.yml."""
    text = _CI_WORKFLOW.read_text(encoding="utf-8")

    no_tui = _extract_job_block(text, "no-tui")
    assert '"3.10"' in no_tui and '"3.12"' in no_tui
    assert "import tomli" in no_tui

    packaging = _extract_job_block(text, "packaging")
    assert "ubuntu-latest" in packaging and "windows-latest" in packaging
    assert "$venv_dir/Scripts" in packaging and "$venv_dir/bin" in packaging
    assert '"$venv_bin/pubrun" bench --iterations 1 --passes 1 --no-baseline --local --no-submit < /dev/null' in packaging
    assert '"scaling_bench.py"' in packaging

    extra_suites = _extract_job_block(text, "extra-suites")
    assert '.[dev,bench]' in extra_suites
    assert "tests/test_compatibility.py" in extra_suites
    assert "benchmarks/plot.py --help" in extra_suites
    assert "matplotlib.use('Agg')" in extra_suites

    typecheck = _extract_job_block(text, "typecheck")
    assert "--strict --no-implicit-reexport" in typecheck
    for mod in (
        "pubrun.auto",
        "pubrun.full",
        "pubrun.noauto",
        "pubrun.nopatch",
        "pubrun.noconsole",
        "pubrun.minimal",
    ):
        assert mod in typecheck


def test_dependency_audit_workflow_structural() -> None:
    """Always-on stdlib structural checks for .github/workflows/dependency-audit.yml."""
    text = _AUDIT_WORKFLOW.read_text(encoding="utf-8")
    audit = _extract_job_block(text, "pip-audit")
    assert '"3.10"' in audit and '"3.12"' in audit
    assert "pip-audit ." in audit
    assert 'install -e ".[tui]"' in audit
    assert "pip-audit -r" in audit


def test_workflows_pyyaml_crosscheck_when_available() -> None:
    """Full PyYAML cross-check of CI and dependency-audit workflows when PyYAML is installed."""
    yaml = pytest.importorskip("yaml")

    ci_data: Dict[str, Any] = yaml.safe_load(_CI_WORKFLOW.read_text(encoding="utf-8"))
    jobs = ci_data["jobs"]

    # no-tui matrix + tomli check
    no_tui = jobs["no-tui"]
    assert no_tui["strategy"]["matrix"]["python-version"] == ["3.10", "3.12"]
    no_tui_runs: List[str] = [s.get("run", "") for s in no_tui["steps"]]
    assert any("import tomli" in r for r in no_tui_runs)

    # packaging Windows + Linux matrix + venv Scripts/bin + scaling_bench.py exclusion
    packaging = jobs["packaging"]
    assert packaging["strategy"]["fail-fast"] is False
    assert packaging["strategy"]["matrix"]["os"] == ["ubuntu-latest", "windows-latest"]
    pack_runs = "\n".join(s.get("run", "") for s in packaging["steps"])
    assert "$venv_dir/Scripts" in pack_runs
    assert '"scaling_bench.py"' in pack_runs
    assert "--iterations 1 --passes 1 --no-baseline --local --no-submit < /dev/null" in pack_runs

    # extra-suites [dev,bench] + compatibility tests + plot.py smoke
    extra = jobs["extra-suites"]
    extra_runs = "\n".join(s.get("run", "") for s in extra["steps"])
    assert '.[dev,bench]' in extra_runs
    assert "tests/test_compatibility.py" in extra_runs
    assert "benchmarks/plot.py --help" in extra_runs

    # typecheck downstream PEP 561 strict mode check
    typecheck = jobs["typecheck"]
    tc_runs = "\n".join(s.get("run", "") for s in typecheck["steps"])
    assert "--strict --no-implicit-reexport" in tc_runs
    assert "pubrun.minimal.__commit__" in tc_runs

    # dependency-audit matrix + [tui] clean-venv audit
    audit_data: Dict[str, Any] = yaml.safe_load(_AUDIT_WORKFLOW.read_text(encoding="utf-8"))
    audit_job = audit_data["jobs"]["pip-audit"]
    assert audit_job["strategy"]["fail-fast"] is False
    assert audit_job["strategy"]["matrix"]["python-version"] == ["3.10", "3.12"]
    audit_runs = "\n".join(s.get("run", "") for s in audit_job["steps"])
    assert "pip-audit ." in audit_runs
    assert '.[tui]' in audit_runs
    assert "pip-audit -r" in audit_runs
