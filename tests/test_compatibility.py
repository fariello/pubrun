"""Compatibility, workflow matrix, and local scaling-benchmark smoke tests."""
from __future__ import annotations

import importlib.util
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CI_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yml"
_AUDIT_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "dependency-audit.yml"
_SCALING_BENCH = _REPO_ROOT / "benchmarks" / "scaling_bench.py"
_SHARE_SAFETY = _REPO_ROOT / "benchmarks" / "share_safety.py"
_MODE_MODULES = (
    "pubrun.auto",
    "pubrun.full",
    "pubrun.noauto",
    "pubrun.nopatch",
    "pubrun.noconsole",
    "pubrun.minimal",
)
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_BLOCK_SCALAR_RE = re.compile(r"^([|>])([+-]?\d*|\d*[+-]?)\s*(?:#.*)?$")
_EXTRAS_TARGET_RE = re.compile(r"^\.\[([^\]]+)\]$")


def _load_share_safety():
    spec = importlib.util.spec_from_file_location("_test_compat_share_safety", _SHARE_SAFETY)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_yaml_comment(value: str) -> str:
    """Strip an unquoted trailing YAML ``# comment`` from a single-line value."""
    in_single = False
    in_double = False
    escaped = False
    for idx, ch in enumerate(value):
        if escaped:
            escaped = False
            continue
        if in_double and ch == "\\":
            escaped = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if idx == 0 or value[idx - 1].isspace():
                return value[:idx].rstrip()
    return value.rstrip()


def _unquote_yaml_scalar(value: str) -> str:
    text = _strip_yaml_comment(value).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text


def _extract_job_block(text: str, job_name: str) -> str:
    """Extract a job block under ``jobs:`` without PyYAML.

    Tolerates valid YAML indentation widths, quoted job keys, and trailing comments.
    """
    lines = text.splitlines()
    jobs_idx: Optional[int] = None
    for idx, line in enumerate(lines):
        if re.match(r"^jobs:\s*(?:#.*)?$", line):
            jobs_idx = idx
            break
    assert jobs_idx is not None, "top-level 'jobs:' section not found"

    key_pattern = re.compile(
        rf"""^\s*(?:{re.escape(job_name)}|"{re.escape(job_name)}"|'{re.escape(job_name)}'):\s*(?:#.*)?$"""
    )
    job_indent: Optional[int] = None
    start: Optional[int] = None
    for idx in range(jobs_idx + 1, len(lines)):
        line = lines[idx]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = _line_indent(line)
        if indent == 0:
            break
        if job_indent is None:
            job_indent = indent
        if indent == job_indent and key_pattern.match(line):
            start = idx
            break

    assert start is not None and job_indent is not None, f"job {job_name!r} not found"
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            collected.append(line)
            continue
        if _line_indent(line) <= job_indent:
            break
        collected.append(line)
    return "\n".join(collected)


def _extract_subblock(block: str, key: str) -> str:
    """Extract an indented mapping sub-block by key without PyYAML."""
    lines = block.splitlines()
    pattern = re.compile(
        rf"""^\s*(?:-\s+)?(?:{re.escape(key)}|"{re.escape(key)}"|'{re.escape(key)}'):\s*(?:#.*)?$"""
    )
    start: Optional[int] = None
    key_indent = 0
    for idx, line in enumerate(lines):
        if pattern.match(line):
            start = idx
            key_indent = _line_indent(line)
            break
    assert start is not None, f"mapping key {key!r} not found"
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            collected.append(line)
            continue
        if _line_indent(line) <= key_indent:
            break
        collected.append(line)
    return "\n".join(collected)


def _extract_yaml_list_values(block: str, key: str) -> List[str]:
    """Extract YAML sequence items for ``key`` in flow or block style without PyYAML."""
    lines = block.splitlines()
    pattern = re.compile(
        rf"""^(\s*)(?:{re.escape(key)}|"{re.escape(key)}"|'{re.escape(key)}'):\s*(.*)$"""
    )
    for idx, line in enumerate(lines):
        match = pattern.match(line)
        if not match:
            continue
        key_indent = len(match.group(1))
        rest = _strip_yaml_comment(match.group(2)).strip()
        if rest.startswith("["):
            parts = [rest]
            cursor = idx + 1
            while "]" not in parts[-1] and cursor < len(lines):
                parts.append(_strip_yaml_comment(lines[cursor]).strip())
                cursor += 1
            joined = " ".join(parts)
            close_pos = joined.find("]")
            inner = joined[1:close_pos] if close_pos != -1 else joined[1:]
            return [
                _unquote_yaml_scalar(item)
                for item in inner.split(",")
                if item.strip()
            ]
        if not rest:
            items: List[str] = []
            for next_line in lines[idx + 1 :]:
                stripped = next_line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                indent = _line_indent(next_line)
                if indent < key_indent:
                    break
                if stripped.startswith("- "):
                    items.append(_unquote_yaml_scalar(stripped[2:]))
                elif indent == key_indent:
                    break
                else:
                    break
            if items:
                return items
    raise AssertionError(f"YAML list key {key!r} not found")


def _extract_run_blocks(job_block: str) -> List[str]:
    """Extract every step ``run:`` command string from a job block without PyYAML."""
    lines = job_block.splitlines()
    runs: List[str] = []
    run_pattern = re.compile(r"^(\s*)(?:-\s+)?run:\s*(.*)$")
    idx = 0
    while idx < len(lines):
        match = run_pattern.match(lines[idx])
        if not match:
            idx += 1
            continue
        # For "- run:", the key column sits past the "- " sequence prefix.
        raw_prefix = lines[idx][: lines[idx].find("run:")]
        key_col = len(raw_prefix)
        rest = match.group(2).strip()
        scalar_match = _BLOCK_SCALAR_RE.match(rest)
        if scalar_match:
            style = scalar_match.group(1)
            body_lines: List[str] = []
            block_indent: Optional[int] = None
            idx += 1
            while idx < len(lines):
                line = lines[idx]
                if not line.strip():
                    body_lines.append("")
                    idx += 1
                    continue
                indent = _line_indent(line)
                if indent <= key_col:
                    break
                if block_indent is None:
                    block_indent = indent
                body_lines.append(line[min(indent, block_indent) :])
                idx += 1
            if style == ">":
                runs.append(" ".join(part.strip() for part in body_lines if part.strip()))
            else:
                runs.append("\n".join(body_lines))
        else:
            collected = [_unquote_yaml_scalar(rest)] if rest else []
            idx += 1
            while idx < len(lines):
                line = lines[idx]
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    idx += 1
                    continue
                if _line_indent(line) <= key_col:
                    break
                collected.append(_unquote_yaml_scalar(stripped))
                idx += 1
            runs.append(" ".join(part for part in collected if part))
    return runs


def _iter_shell_commands(run_scripts: Sequence[str]) -> List[List[str]]:
    """Parse logical shell lines from ``run:`` scripts into normalized token lists."""
    commands: List[List[str]] = []
    for script in run_scripts:
        unwrapped = re.sub(r"\\\r?\n[ \t]*", " ", script)
        for raw_line in unwrapped.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                raw_tokens = shlex.split(stripped, comments=True)
            except ValueError:
                raw_tokens = [tok.strip("'\"") for tok in stripped.split()]
            if not raw_tokens:
                continue
            segment: List[str] = []
            for tok in raw_tokens:
                if tok in ("&&", "||"):
                    if segment:
                        commands.append(segment)
                        segment = []
                    continue
                if tok.startswith("<") and len(tok) > 1 and not tok.startswith("<<"):
                    segment.extend(["<", tok[1:]])
                    continue
                segment.append(tok)
            if segment:
                commands.append(segment)
    return commands


def _strip_leading_env_assignments(tokens: Sequence[str]) -> List[str]:
    idx = 0
    while idx < len(tokens) and _ENV_ASSIGN_RE.match(tokens[idx]):
        idx += 1
    return list(tokens[idx:])


def _command_basename(token: str) -> str:
    clean = token.rstrip(";")
    return re.split(r"[/\\]", clean)[-1].lower()


def _expand_flag_tokens(tokens: Sequence[str]) -> List[str]:
    expanded: List[str] = []
    for tok in tokens:
        if tok.startswith("--") and "=" in tok:
            flag, val = tok.split("=", 1)
            expanded.extend([flag, val])
        else:
            expanded.append(tok)
    return expanded


def _find_flag_value(tokens: Sequence[str], flag: str) -> Optional[str]:
    expanded = _expand_flag_tokens(tokens)
    for idx, tok in enumerate(expanded):
        if tok == flag and idx + 1 < len(expanded):
            return expanded[idx + 1]
    return None


def _python_module_invocation(tokens: Sequence[str]) -> Tuple[Optional[str], List[str]]:
    """Return ``(tool_name, args)`` for direct or ``python -m <tool>`` invocations."""
    cmd = _strip_leading_env_assignments(tokens)
    if not cmd:
        return None, []
    head = _command_basename(cmd[0])
    if head in ("python", "python3") and len(cmd) >= 3 and cmd[1] == "-m":
        return cmd[2].lower(), cmd[3:]
    return head, cmd[1:]


def _has_python_import_check(run_scripts: Sequence[str], module_name: str) -> bool:
    import_re = re.compile(
        rf"\b(?:import\s+{re.escape(module_name)}|from\s+{re.escape(module_name)}\b)"
    )
    for tokens in _iter_shell_commands(run_scripts):
        cmd = _strip_leading_env_assignments(tokens)
        if not cmd or _command_basename(cmd[0]) not in ("python", "python3"):
            continue
        code = _find_flag_value(cmd[1:], "-c")
        if code and import_re.search(code):
            return True
    return False


def _has_venv_cross_platform_bin_paths(run_scripts: Sequence[str]) -> bool:
    combined = "\n".join(run_scripts)
    has_scripts = re.search(r"\$\{?venv_dir\}?/Scripts\b", combined) is not None
    has_bin = re.search(r"\$\{?venv_dir\}?/bin\b", combined) is not None
    return has_scripts and has_bin


def _has_pubrun_bench_smoke(run_scripts: Sequence[str]) -> bool:
    required_flags = {"--no-baseline", "--local", "--no-submit"}
    for tokens in _iter_shell_commands(run_scripts):
        tool, args = _python_module_invocation(tokens)
        if tool != "pubrun" or not args or args[0] != "bench":
            continue
        expanded = _expand_flag_tokens(args[1:])
        has_devnull_stdin = any(
            expanded[i] == "<" and i + 1 < len(expanded) and expanded[i + 1] == "/dev/null"
            for i in range(len(expanded))
        )
        if (
            _find_flag_value(expanded, "--iterations") == "1"
            and _find_flag_value(expanded, "--passes") == "1"
            and required_flags <= set(expanded)
            and has_devnull_stdin
        ):
            return True
    return False


def _has_forbidden_wheel_entry(run_scripts: Sequence[str], entry: str) -> bool:
    for tokens in _iter_shell_commands(run_scripts):
        cleaned = [tok.rstrip(";") for tok in tokens]
        if "forbidden" in cleaned and entry in cleaned:
            return True
    return False


def _has_pip_install_with_extras(
    run_scripts: Sequence[str],
    required_extras: Set[str],
    *,
    editable: Optional[bool] = None,
) -> bool:
    for tokens in _iter_shell_commands(run_scripts):
        tool, args = _python_module_invocation(tokens)
        if tool not in ("pip", "pip3") or not args or args[0] != "install":
            continue
        install_args = args[1:]
        is_editable = "-e" in install_args or "--editable" in install_args
        if editable is not None and is_editable != editable:
            continue
        for arg in install_args:
            match = _EXTRAS_TARGET_RE.match(arg)
            if match:
                extras = {part.strip() for part in match.group(1).split(",") if part.strip()}
                if required_extras <= extras:
                    return True
    return False


def _has_pytest_target(run_scripts: Sequence[str], target: str) -> bool:
    for tokens in _iter_shell_commands(run_scripts):
        tool, args = _python_module_invocation(tokens)
        if tool == "pytest" and target in args:
            return True
    return False


def _has_python_script_flag(run_scripts: Sequence[str], script: str, flag: str) -> bool:
    for tokens in _iter_shell_commands(run_scripts):
        cmd = _strip_leading_env_assignments(tokens)
        if not cmd or _command_basename(cmd[0]) not in ("python", "python3"):
            continue
        args = _expand_flag_tokens(cmd[1:])
        if script in args and flag in args:
            return True
    return False


def _has_headless_matplotlib_smoke(run_scripts: Sequence[str]) -> bool:
    agg_re = re.compile(r"""matplotlib\.use\(\s*['"]Agg['"]\s*\)""")
    for tokens in _iter_shell_commands(run_scripts):
        cmd = _strip_leading_env_assignments(tokens)
        if not cmd or _command_basename(cmd[0]) not in ("python", "python3"):
            continue
        code = _find_flag_value(cmd[1:], "-c")
        if code and "matplotlib" in code and agg_re.search(code):
            return True
    return False


def _has_strict_mypy_mode_check(
    run_scripts: Sequence[str],
    modules: Sequence[str],
    required_snippets: Sequence[str] = (),
) -> bool:
    for tokens in _iter_shell_commands(run_scripts):
        tool, args = _python_module_invocation(tokens)
        if tool != "mypy":
            continue
        expanded = _expand_flag_tokens(args)
        if not ({"--strict", "--no-implicit-reexport"} <= set(expanded)):
            continue
        code = _find_flag_value(expanded, "-c") or ""
        if all(re.search(rf"\b{re.escape(mod)}\b", code) for mod in modules) and all(
            snippet in code for snippet in required_snippets
        ):
            return True
    return False


def _has_pip_audit_with_arg(run_scripts: Sequence[str], *accepted_args: str) -> bool:
    accepted = set(accepted_args)
    for tokens in _iter_shell_commands(run_scripts):
        tool, args = _python_module_invocation(tokens)
        if tool not in ("pip-audit", "pip_audit"):
            continue
        expanded = _expand_flag_tokens(args)
        if accepted & set(expanded):
            return True
    return False


@pytest.mark.slow
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
    assert fio["open_tracked_records"] == 200
    assert fio["register_input_tracked_records"] == 200
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
    no_tui_pythons = _extract_yaml_list_values(_extract_subblock(no_tui, "matrix"), "python-version")
    assert {"3.10", "3.12"} <= set(no_tui_pythons)
    no_tui_runs = _extract_run_blocks(no_tui)
    assert _has_python_import_check(no_tui_runs, "tomli")

    packaging = _extract_job_block(text, "packaging")
    packaging_os = _extract_yaml_list_values(_extract_subblock(packaging, "matrix"), "os")
    assert {"ubuntu-latest", "windows-latest"} <= set(packaging_os)
    pack_runs = _extract_run_blocks(packaging)
    assert _has_venv_cross_platform_bin_paths(pack_runs)
    assert _has_pubrun_bench_smoke(pack_runs)
    assert _has_forbidden_wheel_entry(pack_runs, "scaling_bench.py")

    extra_suites = _extract_job_block(text, "extra-suites")
    extra_runs = _extract_run_blocks(extra_suites)
    assert _has_pip_install_with_extras(extra_runs, {"dev", "bench"})
    assert _has_pytest_target(extra_runs, "tests/test_compatibility.py")
    assert _has_python_script_flag(extra_runs, "benchmarks/plot.py", "--help")
    assert _has_headless_matplotlib_smoke(extra_runs)

    typecheck = _extract_job_block(text, "typecheck")
    tc_runs = _extract_run_blocks(typecheck)
    assert _has_strict_mypy_mode_check(
        tc_runs,
        _MODE_MODULES,
        required_snippets=("pubrun.minimal.__commit__",),
    )


def test_dependency_audit_workflow_structural() -> None:
    """Always-on stdlib structural checks for .github/workflows/dependency-audit.yml."""
    text = _AUDIT_WORKFLOW.read_text(encoding="utf-8")
    audit = _extract_job_block(text, "pip-audit")
    audit_pythons = _extract_yaml_list_values(_extract_subblock(audit, "matrix"), "python-version")
    assert {"3.10", "3.12"} <= set(audit_pythons)
    audit_runs = _extract_run_blocks(audit)
    assert _has_pip_audit_with_arg(audit_runs, ".")
    assert _has_pip_install_with_extras(audit_runs, {"tui"}, editable=True)
    assert _has_pip_audit_with_arg(audit_runs, "-r", "--requirement")


def test_workflow_structural_helpers_tolerate_reformatting() -> None:
    """Verify stdlib workflow helpers survive valid YAML/shell reformatting without false failures."""
    reformatted_ci = """\
name: CI
jobs:  # top-level comment
    no-tui:  # 4-space indent with trailing comment
        strategy:
            matrix:
                python-version:
                  - '3.12'
                  - "3.10"
        steps:
            - run: python3 -c 'import tomli'
    packaging:  # wheel checks
        strategy:
            matrix:
                os: [
                    'windows-latest',
                    "ubuntu-latest",
                ]
        steps:
            - run: |
                if [ -d "${venv_dir}/Scripts" ]; then
                  venv_bin="${venv_dir}/Scripts"
                else
                  venv_bin="${venv_dir}/bin"
                fi
                for forbidden in 'plot.py' scaling_bench.py; do
                  echo "$forbidden"
                done
                "$venv_bin/pubrun" bench --no-submit --local --passes=1 --no-baseline --iterations=1 </dev/null
    extra-suites:
        steps:
            - run: pip install --editable '.[bench, dev]' pyyaml
            - run: python3 -m pytest -p randomly tests/test_compatibility.py -v
            - run: |
                python3 --help benchmarks/plot.py
                python3 -c 'import matplotlib; matplotlib.use("Agg")'
    typecheck:
        steps:
            - run: >-
                MYPYPATH=src python3 -m mypy --no-implicit-reexport --strict -c
                "import pubrun.auto, pubrun.full, pubrun.noauto, pubrun.nopatch, pubrun.noconsole, pubrun.minimal; pubrun.minimal.__commit__"
"""
    no_tui = _extract_job_block(reformatted_ci, "no-tui")
    assert set(_extract_yaml_list_values(_extract_subblock(no_tui, "matrix"), "python-version")) == {
        "3.10",
        "3.12",
    }
    assert _has_python_import_check(_extract_run_blocks(no_tui), "tomli")

    packaging = _extract_job_block(reformatted_ci, "packaging")
    assert set(_extract_yaml_list_values(_extract_subblock(packaging, "matrix"), "os")) == {
        "ubuntu-latest",
        "windows-latest",
    }
    pack_runs = _extract_run_blocks(packaging)
    assert _has_venv_cross_platform_bin_paths(pack_runs)
    assert _has_pubrun_bench_smoke(pack_runs)
    assert _has_forbidden_wheel_entry(pack_runs, "scaling_bench.py")
    assert not _has_forbidden_wheel_entry(pack_runs, "missing_script.py")

    extra_runs = _extract_run_blocks(_extract_job_block(reformatted_ci, "extra-suites"))
    assert _has_pip_install_with_extras(extra_runs, {"dev", "bench"}, editable=True)
    assert not _has_pip_install_with_extras(extra_runs, {"dev", "tui"})
    assert _has_pytest_target(extra_runs, "tests/test_compatibility.py")
    assert _has_python_script_flag(extra_runs, "benchmarks/plot.py", "--help")
    assert _has_headless_matplotlib_smoke(extra_runs)

    tc_runs = _extract_run_blocks(_extract_job_block(reformatted_ci, "typecheck"))
    assert _has_strict_mypy_mode_check(
        tc_runs,
        _MODE_MODULES,
        required_snippets=("pubrun.minimal.__commit__",),
    )
    assert not _has_strict_mypy_mode_check(["mypy --strict -c 'import pubrun.auto'"], _MODE_MODULES)


def test_workflows_pyyaml_crosscheck_when_available() -> None:
    """Full PyYAML cross-check of CI and dependency-audit workflows when PyYAML is installed."""
    yaml = pytest.importorskip("yaml")

    ci_data: Dict[str, Any] = yaml.safe_load(_CI_WORKFLOW.read_text(encoding="utf-8"))
    jobs = ci_data["jobs"]

    # no-tui matrix + tomli check
    no_tui = jobs["no-tui"]
    assert set(no_tui["strategy"]["matrix"]["python-version"]) == {"3.10", "3.12"}
    no_tui_runs: List[str] = [s.get("run", "") for s in no_tui["steps"] if s.get("run")]
    assert _has_python_import_check(no_tui_runs, "tomli")

    # packaging Windows + Linux matrix + venv Scripts/bin + scaling_bench.py exclusion
    packaging = jobs["packaging"]
    assert packaging["strategy"]["fail-fast"] is False
    assert set(packaging["strategy"]["matrix"]["os"]) == {"ubuntu-latest", "windows-latest"}
    pack_runs: List[str] = [s.get("run", "") for s in packaging["steps"] if s.get("run")]
    assert _has_venv_cross_platform_bin_paths(pack_runs)
    assert _has_forbidden_wheel_entry(pack_runs, "scaling_bench.py")
    assert _has_pubrun_bench_smoke(pack_runs)

    # extra-suites [dev,bench] + compatibility tests + plot.py smoke
    extra = jobs["extra-suites"]
    extra_runs: List[str] = [s.get("run", "") for s in extra["steps"] if s.get("run")]
    assert _has_pip_install_with_extras(extra_runs, {"dev", "bench"})
    assert _has_pytest_target(extra_runs, "tests/test_compatibility.py")
    assert _has_python_script_flag(extra_runs, "benchmarks/plot.py", "--help")
    assert _has_headless_matplotlib_smoke(extra_runs)

    # typecheck downstream PEP 561 strict mode check
    typecheck = jobs["typecheck"]
    tc_runs: List[str] = [s.get("run", "") for s in typecheck["steps"] if s.get("run")]
    assert _has_strict_mypy_mode_check(
        tc_runs,
        _MODE_MODULES,
        required_snippets=("pubrun.minimal.__commit__",),
    )

    # dependency-audit matrix + [tui] clean-venv audit
    audit_data: Dict[str, Any] = yaml.safe_load(_AUDIT_WORKFLOW.read_text(encoding="utf-8"))
    audit_job = audit_data["jobs"]["pip-audit"]
    assert audit_job["strategy"]["fail-fast"] is False
    assert set(audit_job["strategy"]["matrix"]["python-version"]) == {"3.10", "3.12"}
    audit_runs: List[str] = [s.get("run", "") for s in audit_job["steps"] if s.get("run")]
    assert _has_pip_audit_with_arg(audit_runs, ".")
    assert _has_pip_install_with_extras(audit_runs, {"tui"}, editable=True)
    assert _has_pip_audit_with_arg(audit_runs, "-r", "--requirement")
