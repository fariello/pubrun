#!/usr/bin/env python3
"""Local, non-publishing scaling benchmark for pubrun (standard library only).

Measures four high-volume scaling scenarios locally on Python 3.8+:

1. ``file_io``: ``pubrun.core.open`` and ``pubrun.core.register_input`` across
   1,000 distinct files (200 with ``--quick``) inside an ephemeral active run
   (``level="stat"``).
2. ``run_scan_lookup``: ``pubrun.status.scan_runs(..., keep_manifest=False)``
   and ``pubrun.status.find_run(..., runs=...)`` across 1,000 synthetic run
   directories (100 with ``--quick``), including manifest parse counts.
3. ``inactive_hot_path``: 10,000 calls each (1,000 with ``--quick``) to
   ``pubrun.core.annotate`` and ``pubrun.core.print`` (redirected to
   ``io.StringIO``) with no active run.
4. ``large_manifest_diff``: ``pubrun.analysis.diff.compare_manifests`` at
   ``"standard"`` and ``"deep"`` depth plus
   ``pubrun.analysis.render._format_array_diff`` on 500 packages, 500
   environment variables, and 1,000-element rearranged arrays (100 and 200 with
   ``--quick``).

Strictly local and non-publishing: never invokes ``gh``, ``git push``, or batch
schedulers. Scrubs hostname, username, home directory, ``--workdir``, and
repository root paths from Markdown stdout and optional ``--json-out`` output,
and validates emitted output with ``benchmarks/share_safety.py::check_share_safe_text``
before printing or writing.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import platform
import re
import shutil
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
_SRC_ROOT = _REPO_ROOT / "src"

if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

# Select minimal mode before importing pubrun.* so this benchmark script never
# auto-starts an implicit tracking session in the repo checkout.
import pubrun.minimal  # noqa: E402, F401
import share_safety as _share_safety  # noqa: E402
import startup_breakdown as _sb  # noqa: E402

SCHEMA_VERSION = "pubrun-scaling-bench/1"
_REDACTED = "<redacted>"
_PROTECTED_RE = re.compile(
    "(" + re.escape(_REDACTED) + "|" + re.escape(SCHEMA_VERSION) + ")"
)
_SCRUB_SKIP_KEYS = frozenset(
    {
        "schema_version",
        "started_at_utc",
        "finished_at_utc",
        "mode",
        "python_version",
        "python_implementation",
        "architecture",
        "pubrun_version",
        "git_revision",
        "workdir_kind",
        "workdir_fstype",
        "fstype",
        "status",
    }
)


def _median_ms(samples_ms: Sequence[float]) -> float:
    return round(float(statistics.median(samples_ms)), 3) if samples_ms else 0.0


def _total_ms(samples_ms: Sequence[float]) -> float:
    return round(float(sum(samples_ms)), 3)


def _bench_file_io(work_root: Path, file_count: int, rounds: int) -> Dict[str, Any]:
    """Measure pubrun.open and pubrun.register_input on distinct files."""
    from pubrun import core

    data_dir = work_root / "file_io_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    open_paths: List[Path] = []
    reg_paths: List[Path] = []
    for i in range(file_count):
        p_open = data_dir / f"open_{i:04d}.txt"
        p_open.write_text(f"open payload {i}\n", encoding="utf-8")
        open_paths.append(p_open)
        p_reg = data_dir / f"reg_{i:04d}.txt"
        p_reg.write_text(f"reg payload {i}\n", encoding="utf-8")
        reg_paths.append(p_reg)

    base_overrides: Dict[str, Any] = {
        "core": {"artifact_durability": "atomic"},
        "capture": {
            "file_io": {
                "level": "stat",
                "max_tracked_files": max(5000, file_count * 2),
            },
            "hardware": {"depth": "off"},
            "packages": {"mode": "off"},
            "git": {"depth": "off"},
            "environment": {"mode": "off"},
            "resources": {"depth": "off"},
            "subprocesses": {"enabled": False},
            "signals": {"enabled": False},
        },
        "console": {"capture_mode": "off"},
    }

    def _run_open_pass(paths: Sequence[Path], run_out: Path) -> Tuple[float, int]:
        overrides = dict(base_overrides)
        overrides["output_dir"] = str(run_out)
        run = core.start(**overrides)
        try:
            t0 = time.perf_counter()
            for p in paths:
                with core.open(p, "r", encoding="utf-8") as fh:
                    fh.read()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            tracked = len(getattr(run, "tracked_inputs", []))
            return elapsed_ms, tracked
        finally:
            core.stop()

    def _run_register_pass(paths: Sequence[Path], run_out: Path) -> Tuple[float, int]:
        overrides = dict(base_overrides)
        overrides["output_dir"] = str(run_out)
        run = core.start(**overrides)
        try:
            t0 = time.perf_counter()
            for p in paths:
                core.register_input(p, level="stat")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            tracked = len(getattr(run, "tracked_inputs", []))
            return elapsed_ms, tracked
        finally:
            core.stop()

    # Warm-up pass (small subset) to load lazy modules and warm OS page cache.
    warm_n = min(10, file_count)
    _run_open_pass(open_paths[:warm_n], work_root / "file_io_runs_warm_open")
    _run_register_pass(reg_paths[:warm_n], work_root / "file_io_runs_warm_reg")

    open_samples: List[float] = []
    reg_samples: List[float] = []
    open_tracked = 0
    reg_tracked = 0
    for r in range(rounds):
        o_ms, open_tracked = _run_open_pass(
            open_paths, work_root / f"file_io_runs_open_{r}"
        )
        open_samples.append(o_ms)
        r_ms, reg_tracked = _run_register_pass(
            reg_paths, work_root / f"file_io_runs_reg_{r}"
        )
        reg_samples.append(r_ms)

    open_med = _median_ms(open_samples)
    reg_med = _median_ms(reg_samples)
    scale = 1000.0 / float(file_count)
    return {
        "file_count": file_count,
        "rounds": rounds,
        "open_median_ms": open_med,
        "open_elapsed_ms": _total_ms(open_samples),
        "open_ms_per_1000": round(open_med * scale, 3),
        "open_tracked_records": open_tracked,
        "register_input_median_ms": reg_med,
        "register_input_elapsed_ms": _total_ms(reg_samples),
        "register_input_ms_per_1000": round(reg_med * scale, 3),
        "register_input_tracked_records": reg_tracked,
        "total_elapsed_ms": round(open_med + reg_med, 3),
    }


def _bench_run_scan_lookup(work_root: Path, run_count: int, rounds: int) -> Dict[str, Any]:
    """Measure scan_runs(keep_manifest=False) and find_run(..., runs=...)."""
    from pubrun import status as status_mod

    runs_dir = work_root / "synthetic_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    base_ts = 1790000000.0
    target_id = ""
    for i in range(run_count):
        run_id = f"ab{i:06x}"
        if i == run_count // 2:
            target_id = run_id
        rdir = runs_dir / f"pubrun-bench_script-20261127-120000-{run_id}"
        rdir.mkdir()
        manifest = {
            "schema_version": "1.0",
            "manifest_type": "pubrun-manifest",
            "run": {"run_id": run_id},
            "status": {"outcome": "completed"},
            "timing": {
                "started_at_utc": base_ts + float(i),
                "ended_at_utc": base_ts + float(i) + 1.25,
                "elapsed_seconds": 1.25,
                "workload_seconds": 1.25,
                "duration_clock": "monotonic",
                "elapsed_basis": "workload",
            },
            "invocation": {
                "script": {"basename": "bench_script.py"},
                "argv": ["bench_script.py", "--step", str(i)],
            },
            "signals": {"exit_code": 0, "signals_received": []},
            "git": {"commit": "abcdef1234567890"},
            "host": {"hostname": "bench-host"},
            "process": {"pid": 10000 + i},
        }
        (rdir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # Warm-up pass
    warm_runs = status_mod.scan_runs(str(runs_dir), keep_manifest=False)
    status_mod.find_run(target_id, str(runs_dir), runs=warm_runs)
    status_mod.find_run("1", str(runs_dir), runs=warm_runs)
    status_mod.find_run(target_id, str(runs_dir))

    scan_samples: List[float] = []
    find_id_samples: List[float] = []
    find_recency_samples: List[float] = []
    find_direct_samples: List[float] = []
    scanned_count = 0

    for _ in range(rounds):
        t0 = time.perf_counter()
        runs = status_mod.scan_runs(str(runs_dir), keep_manifest=False)
        scan_samples.append((time.perf_counter() - t0) * 1000.0)
        scanned_count = len(runs)

        t1 = time.perf_counter()
        hit_id = status_mod.find_run(target_id, str(runs_dir), runs=runs)
        find_id_samples.append((time.perf_counter() - t1) * 1000.0)
        if hit_id is None or hit_id.run_id != target_id:
            raise RuntimeError("find_run(exact_id, runs=...) failed to locate synthetic run")

        t2 = time.perf_counter()
        hit_rec = status_mod.find_run("1", str(runs_dir), runs=runs)
        find_recency_samples.append((time.perf_counter() - t2) * 1000.0)
        if hit_rec is None:
            raise RuntimeError("find_run('1', runs=...) failed to locate most recent run")

        t3 = time.perf_counter()
        hit_direct = status_mod.find_run(target_id, str(runs_dir))
        find_direct_samples.append((time.perf_counter() - t3) * 1000.0)
        if hit_direct is None or hit_direct.run_id != target_id:
            raise RuntimeError("find_run(exact_id) fast path failed to locate synthetic run")

    # Dedicated instrumented pass (outside timed loops) to count manifest parses.
    orig_json_load = status_mod.json.load
    parse_counter = [0]

    def _counting_load(*args: Any, **kwargs: Any) -> Any:
        parse_counter[0] += 1
        return orig_json_load(*args, **kwargs)

    status_mod.json.load = _counting_load  # type: ignore[assignment]
    try:
        parse_counter[0] = 0
        counted_runs = status_mod.scan_runs(str(runs_dir), keep_manifest=False)
        scan_parses = parse_counter[0]

        parse_counter[0] = 0
        status_mod.find_run(target_id, str(runs_dir), runs=counted_runs)
        status_mod.find_run("1", str(runs_dir), runs=counted_runs)
        find_with_runs_parses = parse_counter[0]

        parse_counter[0] = 0
        status_mod.find_run(target_id, str(runs_dir))
        find_direct_parses = parse_counter[0]
    finally:
        status_mod.json.load = orig_json_load  # type: ignore[assignment]

    scan_med = _median_ms(scan_samples)
    find_id_med = _median_ms(find_id_samples)
    find_rec_med = _median_ms(find_recency_samples)
    find_direct_med = _median_ms(find_direct_samples)
    return {
        "run_count": run_count,
        "scanned_count": scanned_count,
        "rounds": rounds,
        "scan_median_ms": scan_med,
        "scan_elapsed_ms": _total_ms(scan_samples),
        "scan_ms_per_1000": round(scan_med * (1000.0 / float(run_count)), 3),
        "find_exact_id_with_runs_median_ms": find_id_med,
        "find_recency_with_runs_median_ms": find_rec_med,
        "find_exact_id_direct_median_ms": find_direct_med,
        "scan_manifest_parses": scan_parses,
        "find_with_runs_manifest_parses": find_with_runs_parses,
        "find_direct_manifest_parses": find_direct_parses,
    }


def _bench_inactive_hot_path(call_count: int, rounds: int) -> Dict[str, Any]:
    """Measure inactive pubrun.annotate and pubrun.print calls with no active run."""
    from pubrun import core

    if core.get_current_run() is not None:
        core.stop()

    # Warm-up
    warm_buf = io.StringIO()
    for i in range(min(50, call_count)):
        core.annotate("warmup", step=i)
        core.print("warmup", i, file=warm_buf)

    annotate_samples: List[float] = []
    print_samples: List[float] = []

    for _ in range(rounds):
        t0 = time.perf_counter()
        for i in range(call_count):
            core.annotate("bench_step", step=i)
        annotate_samples.append((time.perf_counter() - t0) * 1000.0)

        buf = io.StringIO()
        t1 = time.perf_counter()
        for i in range(call_count):
            core.print("bench_line", i, file=buf)
        print_samples.append((time.perf_counter() - t1) * 1000.0)

    ann_med = _median_ms(annotate_samples)
    prt_med = _median_ms(print_samples)
    return {
        "call_count": call_count,
        "rounds": rounds,
        "annotate_median_ms": ann_med,
        "annotate_elapsed_ms": _total_ms(annotate_samples),
        "annotate_us_per_call": round((ann_med * 1000.0) / float(call_count), 3),
        "print_median_ms": prt_med,
        "print_elapsed_ms": _total_ms(print_samples),
        "print_us_per_call": round((prt_med * 1000.0) / float(call_count), 3),
    }


def _bench_large_manifest_diff(
    pkg_count: int, env_count: int, array_len: int, rounds: int
) -> Dict[str, Any]:
    """Measure compare_manifests (standard & deep) and _format_array_diff."""
    from pubrun.analysis.diff import compare_manifests
    from pubrun.analysis.render import _format_array_diff
    from pubrun.config import load_default_config

    defaults = load_default_config()
    standard_ignores = list((defaults.get("diff") or {}).get("ignore_standard") or [])

    pkgs_a = [
        {"name": f"pkg-{i:04d}", "version": f"1.{i % 20}.0"}
        for i in range(pkg_count)
    ]
    pkgs_b = [
        {
            "name": f"pkg-{i:04d}",
            "version": f"1.{i % 20}.{1 if i % 10 == 0 else 0}",
        }
        for i in range(pkg_count)
    ]
    pkgs_b.append({"name": "pkg-added-extra", "version": "2.0.0"})

    env_a = [
        {"name": f"BENCH_VAR_{i:04d}", "value": f"val-{i}"}
        for i in range(env_count)
    ]
    env_b = [
        {
            "name": f"BENCH_VAR_{i:04d}",
            "value": f"val-{i}-changed" if i % 15 == 0 else f"val-{i}",
        }
        for i in range(env_count)
    ]

    arr_a = [f"item-{i:04d}" for i in range(array_len)]
    # Rearrange blocks, remove a few, and add a few items.
    pivot = array_len // 2
    arr_b = arr_a[pivot:] + arr_a[:pivot]
    if len(arr_b) >= 4:
        arr_b = arr_b[2:] + ["item-added-1", "item-added-2"]

    manifest_a: Dict[str, Any] = {
        "schema_version": "1.0",
        "run": {"run_id": "aaaa0001"},
        "host": {"os_name": "Linux", "hostname": "bench-a"},
        "timing": {"started_at_utc": 1790000000.0, "elapsed_seconds": 12.3},
        "invocation": {
            "script": {"basename": "train.py"},
            "argv": ["train.py", "--epochs", "10"],
        },
        "packages": {"records": pkgs_a},
        "environment": {"variables": env_a},
        "custom": {"array": arr_a},
    }
    manifest_b: Dict[str, Any] = {
        "schema_version": "1.0",
        "run": {"run_id": "bbbb0002"},
        "host": {"os_name": "Linux", "hostname": "bench-b"},
        "timing": {"started_at_utc": 1790000100.0, "elapsed_seconds": 12.8},
        "invocation": {
            "script": {"basename": "train.py"},
            "argv": ["train.py", "--epochs", "20"],
        },
        "packages": {"records": pkgs_b},
        "environment": {"variables": env_b},
        "custom": {"array": arr_b},
    }

    set_a = set(arr_a)
    set_b = set(arr_b)
    added_items = [x for x in arr_b if x not in set_a]
    removed_items = [x for x in arr_a if x not in set_b]
    common_a = [x for x in arr_a if x in set_b]
    common_b = [x for x in arr_b if x in set_a]

    # Warm-up
    compare_manifests(manifest_a, manifest_b, ignores=standard_ignores, depth="standard")
    compare_manifests(manifest_a, manifest_b, ignores=[], depth="deep")
    _format_array_diff(arr_b, True, added_items, removed_items, common_a, common_b, False)

    std_samples: List[float] = []
    deep_samples: List[float] = []
    arr_samples: List[float] = []
    std_changes = 0
    deep_changes = 0

    for _ in range(rounds):
        t0 = time.perf_counter()
        diff_std = compare_manifests(
            manifest_a, manifest_b, ignores=standard_ignores, depth="standard"
        )
        std_samples.append((time.perf_counter() - t0) * 1000.0)
        std_changes = (
            len(diff_std["added"]) + len(diff_std["removed"]) + len(diff_std["modified"])
        )

        t1 = time.perf_counter()
        diff_deep = compare_manifests(manifest_a, manifest_b, ignores=[], depth="deep")
        deep_samples.append((time.perf_counter() - t1) * 1000.0)
        deep_changes = (
            len(diff_deep["added"]) + len(diff_deep["removed"]) + len(diff_deep["modified"])
        )

        t2 = time.perf_counter()
        _format_array_diff(arr_b, True, added_items, removed_items, common_a, common_b, False)
        arr_samples.append((time.perf_counter() - t2) * 1000.0)

    std_med = _median_ms(std_samples)
    deep_med = _median_ms(deep_samples)
    arr_med = _median_ms(arr_samples)
    return {
        "package_count": pkg_count,
        "env_count": env_count,
        "array_length": array_len,
        "rounds": rounds,
        "standard_diff_median_ms": std_med,
        "standard_diff_elapsed_ms": _total_ms(std_samples),
        "standard_diff_changes": std_changes,
        "deep_diff_median_ms": deep_med,
        "deep_diff_elapsed_ms": _total_ms(deep_samples),
        "deep_diff_changes": deep_changes,
        "array_diff_median_ms": arr_med,
        "array_diff_elapsed_ms": _total_ms(arr_samples),
        "array_diff_us_per_element": round((arr_med * 1000.0) / float(array_len), 3),
    }


def _scrub_string(text: str, needles: Sequence[str]) -> str:
    parts = _PROTECTED_RE.split(text)
    return "".join(
        part if idx % 2 else _sb._scrub_segment(part, needles)
        for idx, part in enumerate(parts)
    )


def _scrub_obj(obj: Any, needles: Sequence[str]) -> Any:
    if isinstance(obj, dict):
        return {
            k: (v if k in _SCRUB_SKIP_KEYS and isinstance(v, str) else _scrub_obj(v, needles))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_scrub_obj(x, needles) for x in obj]
    if isinstance(obj, str):
        return _scrub_string(obj, needles)
    return obj


def _needles_found(text: str, needles: Sequence[str]) -> bool:
    segments = _PROTECTED_RE.split(text)[::2]
    for needle in needles:
        pattern = _sb._needle_pattern(needle)
        if any(pattern.search(seg) for seg in segments):
            return True
    return False


def _validate_share_safety(
    result: Dict[str, Any],
    json_text: str,
    md_text: str,
    extra_needles: Sequence[str] = (),
) -> Tuple[bool, List[str]]:
    issues: List[str] = []

    ok_json, reasons_json = _share_safety.check_share_safe_text(json_text)
    if not ok_json:
        issues.extend(f"json: {r}" for r in reasons_json)

    ok_md, reasons_md = _share_safety.check_share_safe_text(json.dumps({"stdout": md_text}))
    if not ok_md:
        issues.extend(f"stdout: {r}" for r in reasons_md)

    needles = [
        n
        for n in _sb._collect_redaction_needles(extra_needles)
        if _sb._is_path_needle(n) or len(n) >= 3
    ]
    path_needles = [n for n in needles if _sb._is_path_needle(n)]
    if _sb._json_needle_leak(result, needles, path_needles):
        issues.append("identifying substring remains in JSON payload")
    if _needles_found(md_text, needles):
        issues.append("identifying substring remains in Markdown output")

    return (len(issues) == 0, issues)


def run_benchmark(quick: bool = False, workdir: Optional[str] = None) -> Dict[str, Any]:
    """Run all four scaling scenarios and return the structured result dict."""
    if quick:
        file_count = 200
        run_count = 100
        call_count = 1000
        pkg_count = 100
        env_count = 100
        array_len = 200
        rounds = 3
    else:
        file_count = 1000
        run_count = 1000
        call_count = 10000
        pkg_count = 500
        env_count = 500
        array_len = 1000
        rounds = 3

    if workdir:
        parent = Path(workdir)
        parent.mkdir(parents=True, exist_ok=True)
        ephemeral = Path(tempfile.mkdtemp(prefix="pubrun-scaling-", dir=str(parent)))
        workdir_kind = "user-supplied"
    else:
        ephemeral = Path(tempfile.mkdtemp(prefix="pubrun-scaling-"))
        workdir_kind = "temporary"

    started = datetime.now(timezone.utc)
    try:
        fs_summary = _sb._capture_filesystem_summary(ephemeral)
        scenarios = {
            "file_io": _bench_file_io(ephemeral, file_count=file_count, rounds=rounds),
            "run_scan_lookup": _bench_run_scan_lookup(
                ephemeral, run_count=run_count, rounds=rounds
            ),
            "inactive_hot_path": _bench_inactive_hot_path(
                call_count=call_count, rounds=rounds
            ),
            "large_manifest_diff": _bench_large_manifest_diff(
                pkg_count=pkg_count,
                env_count=env_count,
                array_len=array_len,
                rounds=rounds,
            ),
        }
    finally:
        shutil.rmtree(str(ephemeral), ignore_errors=True)

    finished = datetime.now(timezone.utc)
    sha = _sb._git_head_sha(_REPO_ROOT)
    workdir_fs = fs_summary.get("workdir", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "quick" if quick else "full",
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "environment": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": f"{platform.system()} {platform.release()}",
            "cpu": _sb._capture_cpu_summary(),
            "pubrun_version": _sb._capture_pubrun_version(),
        },
        "git_revision": sha[:12] if sha else None,
        "workdir_fstype": workdir_fs.get("fstype", "unknown"),
        "workdir_is_network": bool(workdir_fs.get("is_network", False)),
        "workdir_kind": workdir_kind,
        "scenarios": scenarios,
    }


def format_markdown(result: Dict[str, Any]) -> str:
    env = result["environment"]
    sc = result["scenarios"]
    fio = sc["file_io"]
    rsl = sc["run_scan_lookup"]
    ihp = sc["inactive_hot_path"]
    lmd = sc["large_manifest_diff"]
    lines = [
        f"# pubrun scaling benchmark ({result['mode']}, local, single machine)",
        "",
        f"- Schema: {result['schema_version']}",
        f"- Python: {env['python_implementation']} {env['python_version']}",
        f"- Platform: {env['platform']}",
        f"- CPU: {env['cpu'].get('model')} ({env['cpu'].get('logical_cores')} logical cores)",
        f"- Git revision: {result.get('git_revision') or 'unknown'}",
        f"- Workdir filesystem: {result['workdir_fstype']}"
        f" (network: {'yes' if result['workdir_is_network'] else 'no'},"
        f" {result['workdir_kind']})",
        "",
        "| scenario | scale | median (ms) | throughput / detail |",
        "|---|---|---|---|",
        (
            f"| file_io (open) | {fio['file_count']} files (stat) | "
            f"{fio['open_median_ms']:.3f} | {fio['open_ms_per_1000']:.3f} ms / 1,000 files |"
        ),
        (
            f"| file_io (register_input) | {fio['file_count']} files (stat) | "
            f"{fio['register_input_median_ms']:.3f} | "
            f"{fio['register_input_ms_per_1000']:.3f} ms / 1,000 files |"
        ),
        (
            f"| run_scan_lookup (scan_runs) | {rsl['run_count']} runs | "
            f"{rsl['scan_median_ms']:.3f} | "
            f"{rsl['scan_ms_per_1000']:.3f} ms / 1,000 runs "
            f"(parses: {rsl['scan_manifest_parses']}) |"
        ),
        (
            f"| run_scan_lookup (find_run) | {rsl['run_count']} runs | "
            f"{rsl['find_exact_id_with_runs_median_ms']:.3f} | "
            f"recency={rsl['find_recency_with_runs_median_ms']:.3f} ms, "
            f"direct={rsl['find_exact_id_direct_median_ms']:.3f} ms "
            f"(parses: cached={rsl['find_with_runs_manifest_parses']}, "
            f"direct={rsl['find_direct_manifest_parses']}) |"
        ),
        (
            f"| inactive_hot_path (annotate) | {ihp['call_count']} calls | "
            f"{ihp['annotate_median_ms']:.3f} | {ihp['annotate_us_per_call']:.3f} us / call |"
        ),
        (
            f"| inactive_hot_path (print) | {ihp['call_count']} calls | "
            f"{ihp['print_median_ms']:.3f} | {ihp['print_us_per_call']:.3f} us / call |"
        ),
        (
            f"| large_manifest_diff (standard) | {lmd['package_count']} pkgs, "
            f"{lmd['env_count']} env, {lmd['array_length']} array | "
            f"{lmd['standard_diff_median_ms']:.3f} | "
            f"changes={lmd['standard_diff_changes']} |"
        ),
        (
            f"| large_manifest_diff (deep) | {lmd['package_count']} pkgs, "
            f"{lmd['env_count']} env, {lmd['array_length']} array | "
            f"{lmd['deep_diff_median_ms']:.3f} | changes={lmd['deep_diff_changes']} |"
        ),
        (
            f"| large_manifest_diff (_format_array_diff) | {lmd['array_length']} elems | "
            f"{lmd['array_diff_median_ms']:.3f} | "
            f"{lmd['array_diff_us_per_element']:.3f} us / elem |"
        ),
    ]
    return "\n".join(lines)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Local, non-publishing scaling benchmark for pubrun "
            "(file_io, run scanning/lookup, inactive hot paths, large manifest diffs)."
        )
    )
    ap.add_argument(
        "--quick",
        action="store_true",
        help="Use scaled-down counts for a fast local smoke run.",
    )
    ap.add_argument(
        "--workdir",
        type=str,
        default=None,
        help=(
            "Optional parent directory for ephemeral benchmark files. Only a dedicated "
            "subdirectory is created and removed on exit; --workdir and siblings stay intact."
        ),
    )
    ap.add_argument(
        "--json-out",
        type=str,
        default=None,
        help="Optional local path for the redacted JSON result (schema pubrun-scaling-bench/1).",
    )
    return ap.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        result = run_benchmark(quick=args.quick, workdir=args.workdir)
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    extra_needles: List[str] = []
    if args.workdir:
        extra_needles.append(args.workdir)
        extra_needles.append(str(Path(args.workdir).resolve()))

    needles = _sb._collect_redaction_needles(extra_needles)
    redacted = _scrub_obj(_sb._redact_keys_recursive(result), needles)
    redacted["schema_version"] = SCHEMA_VERSION
    md_text = _scrub_string(format_markdown(redacted), needles)
    json_text = json.dumps(redacted, indent=2) + "\n"

    ok, reasons = _validate_share_safety(
        redacted, json_text, md_text, extra_needles=extra_needles
    )
    if not ok:
        print(
            "error: share-safety check failed; refusing to emit output: " + "; ".join(reasons),
            file=sys.stderr,
        )
        return 1

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_text, encoding="utf-8")

    sys.stdout.write(md_text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
