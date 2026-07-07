#!/usr/bin/env python3
"""pubrun benchmark harness (stdlib-only measurement core).

Runs each scenario (see ``scenarios.py``) in a FRESH subprocess N times and
records wall-clock timing statistics, then writes one JSON result file
containing the machine metadata (captured via pubrun itself) and every
scenario's stats. Import matplotlib/pytest-benchmark is intentionally avoided
here so the harness runs anywhere pubrun runs (including locked-down HPC nodes).

By default it runs the FULL scenario sweep TWICE (``--passes 2``) and records
both passes, so any startup / filesystem caching effect is visible (compare
pass 1 vs pass 2) rather than silently baked in. The top-level ``scenarios`` key
mirrors the last (warmest) pass for convenience and backward compatibility.

Usage:
    python benchmarks/harness.py                 # full run: 2 passes x 30 iterations
    python benchmarks/harness.py --quick         # smoke run: 2 passes x 8 iterations
    python benchmarks/harness.py --passes 1      # single pass (no cache-warming)
    python benchmarks/harness.py --iterations 50 # custom
    python benchmarks/harness.py --out results/my.json

Portability: pure standard library. Requires pubrun importable (``pip install
-e .`` from the repo root) so scenarios and machine metadata capture work.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent

# Make sibling modules importable when run as a script.
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import scenarios as _scenarios  # noqa: E402

FULL_ITERATIONS = 30
QUICK_ITERATIONS = 8


def _toml_dumps(data: dict) -> str:
    """Minimal TOML serializer for the nested config dicts we emit.

    Handles the small subset we use: nested tables, strings, bools, ints. Kept
    dependency-free (we must not require tomli-w). Section paths are dotted.
    """
    lines: list[str] = []

    def _emit_table(prefix: str, table: dict) -> None:
        scalars = {k: v for k, v in table.items() if not isinstance(v, dict)}
        tables = {k: v for k, v in table.items() if isinstance(v, dict)}
        if prefix and scalars:
            lines.append(f"[{prefix}]")
        for k, v in scalars.items():
            lines.append(f"{k} = {_fmt(v)}")
        if prefix and scalars:
            lines.append("")
        for k, v in tables.items():
            _emit_table(f"{prefix}.{k}" if prefix else k, v)

    def _fmt(v) -> str:
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        return '"' + str(v).replace('"', '\\"') + '"'

    _emit_table("", data)
    return "\n".join(lines) + "\n"


def _machine_metadata() -> dict:
    """Capture host/hardware/python metadata by reusing pubrun's own capture."""
    md: dict = {}
    try:
        from pubrun.config import resolve_config
        cfg = resolve_config()
        from pubrun.capture.host import get_host
        from pubrun.capture.hardware import get_hardware
        from pubrun.capture.python_runtime import get_python_runtime
        md["host"] = get_host(cfg)
        md["hardware"] = get_hardware(cfg)
        md["python"] = get_python_runtime(cfg)
    except Exception as e:  # never let metadata capture abort a benchmark run
        md["capture_error"] = f"{type(e).__name__}: {e}"
    try:
        import pubrun
        md["pubrun_version"] = getattr(pubrun, "__version__", None)
        md["pubrun_commit"] = getattr(pubrun, "__commit__", None)
    except Exception:
        md["pubrun_version"] = None
    md["python_executable"] = sys.executable
    md["platform"] = sys.platform
    return md


def _pass_env() -> dict:
    """Dynamic host state captured at the START OF EACH PASS.

    A node that gets loaded (or runs low on RAM) between passes would otherwise be
    invisible. Cheap /proc reads; reuses pubrun's own system-metrics capture.
    """
    env: dict = {}
    try:
        from pubrun.capture.system_metrics import get_system_memory, get_load_average, read_proc_stat_cpu_times, iowait_pct_between
        env["system_memory"] = get_system_memory()
        env["load_average"] = get_load_average()
        # Sample iowait over a short window so the per-pass value is meaningful.
        a = read_proc_stat_cpu_times()
        time.sleep(0.05)
        b = read_proc_stat_cpu_times()
        env["system_iowait_pct"] = iowait_pct_between(a, b)  # NODE-WIDE, indicative only
    except Exception as e:
        env["capture_error"] = f"{type(e).__name__}: {e}"
    return env


def _filesystem_context() -> dict:
    """Filesystem type of the harness workdir/$TMPDIR and the results dir.

    Surfaces the "installed/running over NFS" case that confounds cross-machine results.
    Non-blocking (parses /proc/mounts; never statvfs/df on the target).
    """
    try:
        from pubrun.capture.filesystem import get_filesystem
        paths = {
            "tmpdir": tempfile.gettempdir(),
            "results_dir": str(Path(__file__).resolve().parent / "results"),
        }
        try:
            import pubrun
            pkg_file = getattr(pubrun, "__file__", None)
            if pkg_file:
                paths["pubrun_install"] = str(Path(pkg_file).resolve().parent)
        except Exception:
            pass
        return get_filesystem({}, paths)
    except Exception as e:
        return {"capture_error": f"{type(e).__name__}: {e}"}


def _slurm_context() -> dict | None:
    """Slurm allocation context (when running under Slurm), for interpreting cross-node results."""
    keys = {
        "SLURM_JOB_ID": "job_id",
        "SLURM_CPUS_PER_TASK": "cpus_per_task",
        "SLURM_MEM_PER_NODE": "mem_per_node",
        "SLURM_JOB_PARTITION": "partition",
        "SLURMD_NODENAME": "node",
        "SLURM_JOB_NUM_NODES": "num_nodes",
    }
    ctx = {dest: os.environ[src] for src, dest in keys.items() if os.environ.get(src)}
    return ctx or None


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def _build_child_command(scn: "_scenarios.Scenario", workdir: Path) -> tuple[list[str], dict]:
    """Return (argv, env) to run one iteration of the scenario in a fresh process."""
    workload_path = _HERE / "workloads" / scn.workload
    env = dict(os.environ)
    # Ensure the child can import pubrun from the repo (editable or installed).
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_REPO_ROOT / "src")] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    # Scenario-specific env (e.g. a workload's I/O target path).
    for k, v in getattr(scn, "env", {}).items():
        env[k] = v

    if scn.is_baseline:
        # No pubrun import at all: run the workload directly.
        return [sys.executable, str(workload_path)], env

    # pubrun-active: import pubrun in the requested mode, then exec the workload.
    env["PUBRUN_IMPORT_MODE"] = scn.mode
    module = {
        "auto": "pubrun",
        "noauto": "pubrun.noauto",
        "nopatch": "pubrun.nopatch",
        "noconsole": "pubrun.noconsole",
        "minimal": "pubrun.minimal",
    }[scn.mode]
    # runpy executes the workload as __main__ so its `if __name__ == "__main__"` runs.
    preamble = (
        f"import {module}  # noqa\n"
        f"import runpy; runpy.run_path({str(workload_path)!r}, run_name='__main__')\n"
    )
    return [sys.executable, "-c", preamble], env


def _time_once(argv: list[str], env: dict, cwd: Path) -> float | None:
    """Run one child process; return elapsed wall seconds, or None on failure."""
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            argv, env=env, cwd=str(cwd),
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120,
        )
    except Exception:
        return None
    elapsed = time.perf_counter() - t0
    if proc.returncode != 0:
        return None
    return elapsed


def _stats(samples: list[float]) -> dict:
    s = sorted(samples)
    n = len(s)
    def _pct(p: float) -> float:
        if not s:
            return 0.0
        idx = min(n - 1, int(round(p * (n - 1))))
        return s[idx]
    return {
        "n": n,
        "min_s": s[0] if s else None,
        "median_s": statistics.median(s) if s else None,
        "mean_s": statistics.fmean(s) if s else None,
        "p95_s": _pct(0.95) if s else None,
        "max_s": s[-1] if s else None,
        "stdev_s": statistics.pstdev(s) if n > 1 else 0.0,
    }


def _run_pass(pass_no: int, iterations: int, warmup: int, workdir: Path) -> dict:
    """Run the whole scenario sweep once, returning {scenario_name: entry}."""
    scns = _scenarios.all_scenarios()
    scenarios: dict = {}
    for scn in scns:
        skip = scn.skip_if() if scn.skip_if else None
        if skip:
            scenarios[scn.name] = {"group": scn.group, "mode": scn.mode,
                                   "workload": scn.workload, "skipped": skip}
            print(f"  [pass {pass_no}] {scn.name}: SKIPPED ({skip})", file=sys.stderr)
            continue

        # Fresh cwd per (pass, scenario) so a stale .pubrun.toml never leaks.
        scn_cwd = workdir / f"pass{pass_no}" / scn.name
        scn_cwd.mkdir(parents=True, exist_ok=True)
        (scn_cwd / "runs").mkdir(exist_ok=True)
        if scn.config:
            (scn_cwd / ".pubrun.toml").write_text(_toml_dumps(scn.config), encoding="utf-8")

        argv, env = _build_child_command(scn, scn_cwd)
        env["PUBRUN_PROFILE"] = env.get("PUBRUN_PROFILE", "default")

        samples: list[float] = []
        failures = 0
        for i in range(iterations + warmup):
            dt = _time_once(argv, env, scn_cwd)
            if dt is None:
                failures += 1
                continue
            if i >= warmup:
                samples.append(dt)

        entry = {"group": scn.group, "mode": scn.mode, "workload": scn.workload,
                 "config": scn.config or {}, "failures": failures, **_stats(samples)}
        scenarios[scn.name] = entry
        med = entry.get("median_s")
        print(f"  [pass {pass_no}] {scn.name}: median={med*1000:.1f} ms "
              f"(n={entry['n']}, fail={failures})" if med else
              f"  [pass {pass_no}] {scn.name}: NO DATA (fail={failures})", file=sys.stderr)
    return scenarios


def run(iterations: int, out_path: Path, warmup: int = 1, passes: int = 2) -> dict:
    scns = _scenarios.all_scenarios()
    machine = _machine_metadata()
    # Enrich the machine block with filesystem type (the NFS signal) and Slurm context
    # so cross-machine / cross-node results are interpretable.
    machine["filesystem"] = _filesystem_context()
    slurm = _slurm_context()
    if slurm:
        machine["slurm"] = slurm
    result = {
        "schema": "pubrun-benchmark/3",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "iterations": iterations,
        "warmup": warmup,
        "passes": passes,
        "git_commit": _git_commit(),
        "machine": machine,
        # Each pass is the FULL scenario sweep, run in order. Recording every
        # pass (rather than discarding a warmup pass) makes startup / filesystem
        # caching effects VISIBLE: compare pass 1 vs pass N. Aggregation/reporting
        # can prefer the last pass (warmest) or show the spread. Each pass also
        # records the dynamic host state (RAM/load/iowait) at its start, so a node
        # loaded between passes is visible.
        "pass_results": [],
    }

    print(f"Running {passes} pass(es) x {len(scns)} scenarios x {iterations} "
          f"iterations (+{warmup} warmup each) ...", file=sys.stderr)

    with tempfile.TemporaryDirectory(prefix="pubrun-bench-") as td:
        workdir = Path(td)
        for pass_no in range(1, passes + 1):
            print(f"--- pass {pass_no}/{passes} ---", file=sys.stderr)
            pass_env = _pass_env()
            scenarios = _run_pass(pass_no, iterations, warmup, workdir)
            result["pass_results"].append({"pass": pass_no, "pass_env": pass_env, "scenarios": scenarios})

    # Convenience: expose the LAST pass as top-level "scenarios" (warmest, and
    # backward-compatible with schema/1 consumers that read result["scenarios"]).
    if result["pass_results"]:
        result["scenarios"] = result["pass_results"][-1]["scenarios"]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}", file=sys.stderr)
    return result


def _default_out() -> Path:
    host = "unknown"
    try:
        import platform
        host = platform.node() or "unknown"
    except Exception:
        pass
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_host = "".join(c if c.isalnum() or c in "-_" else "_" for c in host)
    return _HERE / "results" / f"{safe_host}-{stamp}.json"


_REDACTED = "<redacted>"

# Keys whose *entire value* is an identifier or a path that can embed the home dir /
# username. Matched by key name anywhere in the nested structure.
_REDACT_KEYS = {
    "hostname", "username", "executable", "prefix", "base_prefix", "virtual_env",
    "python_executable", "path", "mount_point", "run_dir", "output_base_dir",
    "results_dir", "pubrun_install", "tmpdir",
}
# Keys whose value is a LIST of paths.
_REDACT_LIST_KEYS = {"sys_path", "source_files"}


def _redact_secrets(obj):
    """Field-level redaction of identifiers/paths, applied recursively."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in _REDACT_LIST_KEYS and isinstance(v, list):
                out[k] = [_REDACTED for _ in v]
            elif k in _REDACT_KEYS and isinstance(v, str):
                out[k] = _REDACTED
            else:
                out[k] = _redact_secrets(v)
        return out
    if isinstance(obj, list):
        return [_redact_secrets(x) for x in obj]
    return obj


def _scrub_pii_substrings(obj, needles):
    """Belt-and-suspenders: replace any home-dir prefix / username substring that leaked
    into an un-enumerated string value, anywhere in the structure."""
    if isinstance(obj, dict):
        return {k: _scrub_pii_substrings(v, needles) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub_pii_substrings(x, needles) for x in obj]
    if isinstance(obj, str):
        s = obj
        for n in needles:
            if n:
                s = s.replace(n, _REDACTED)
        return s
    return obj


def redact_result(result: dict):
    """Return a redacted copy of a benchmark result safe to share to a PUBLIC repo.

    Masks hostname, OS username, and every path field that can embed the home directory,
    then does a deep substring scrub of the home-dir prefix and username as a safety net.
    Preserves the analysis-relevant, non-identifying data (CPU model, timings, versions,
    fstype classification, Slurm partition).
    """
    import copy
    import getpass
    redacted = _redact_secrets(copy.deepcopy(result))
    needles = []
    try:
        home = os.path.expanduser("~")
        if home and home != "~":
            needles.append(home)
    except Exception:
        pass
    try:
        needles.append(getpass.getuser())
    except Exception:
        pass
    # Longest first so a home path containing the username is scrubbed whole.
    needles = sorted({n for n in needles if n}, key=len, reverse=True)
    scrubbed = _scrub_pii_substrings(redacted, needles)
    return scrubbed if isinstance(scrubbed, dict) else redacted


def main() -> None:
    ap = argparse.ArgumentParser(description="pubrun overhead benchmark harness")
    ap.add_argument("--quick", action="store_true", help=f"Fast smoke run ({QUICK_ITERATIONS} iters).")
    ap.add_argument("--iterations", type=int, default=None, help="Iterations per scenario.")
    ap.add_argument("--passes", type=int, default=2,
                    help="Number of full scenario sweeps to run (default 2, so "
                         "startup/filesystem caching effects can level out; each "
                         "pass is recorded so the difference is visible).")
    ap.add_argument("--out", type=str, default=None, help="Output JSON path.")
    ap.add_argument("--redacted-out", type=str, default=None,
                    help="Also write a redacted copy (safe to share publicly) to this path.")
    args = ap.parse_args()

    iterations = args.iterations if args.iterations else (QUICK_ITERATIONS if args.quick else FULL_ITERATIONS)
    passes = max(1, args.passes)
    out_path = Path(args.out) if args.out else _default_out()
    result = run(iterations, out_path, passes=passes)
    if args.redacted_out:
        red_path = Path(args.redacted_out)
        red_path.parent.mkdir(parents=True, exist_ok=True)
        red_path.write_text(json.dumps(redact_result(result), indent=2), encoding="utf-8")
        print(f"Wrote redacted copy {red_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
