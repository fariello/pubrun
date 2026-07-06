#!/usr/bin/env python3
"""pubrun benchmark harness (stdlib-only measurement core).

Runs each scenario (see ``scenarios.py``) in a FRESH subprocess N times and
records wall-clock timing statistics, then writes one JSON result file
containing the machine metadata (captured via pubrun itself) and every
scenario's stats. Import matplotlib/pytest-benchmark is intentionally avoided
here so the harness runs anywhere pubrun runs (including locked-down HPC nodes).

Usage:
    python benchmarks/harness.py                 # full run (30 iterations)
    python benchmarks/harness.py --quick         # smoke run (8 iterations)
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


def run(iterations: int, out_path: Path, warmup: int = 1) -> dict:
    result = {
        "schema": "pubrun-benchmark/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "iterations": iterations,
        "warmup": warmup,
        "git_commit": _git_commit(),
        "machine": _machine_metadata(),
        "scenarios": {},
    }

    scns = _scenarios.all_scenarios()
    print(f"Running {len(scns)} scenarios x {iterations} iterations "
          f"(+{warmup} warmup) ...", file=sys.stderr)

    with tempfile.TemporaryDirectory(prefix="pubrun-bench-") as td:
        workdir = Path(td)
        # Send any pubrun run output away from the benchmark cwd tree.
        for scn in scns:
            skip = scn.skip_if() if scn.skip_if else None
            if skip:
                result["scenarios"][scn.name] = {"group": scn.group, "mode": scn.mode,
                                                 "workload": scn.workload, "skipped": skip}
                print(f"  - {scn.name}: SKIPPED ({skip})", file=sys.stderr)
                continue

            # Fresh cwd per scenario so a stale .pubrun.toml never leaks across scenarios.
            scn_cwd = workdir / scn.name
            scn_cwd.mkdir(parents=True, exist_ok=True)
            (scn_cwd / "runs").mkdir(exist_ok=True)
            if scn.config:
                (scn_cwd / ".pubrun.toml").write_text(_toml_dumps(scn.config), encoding="utf-8")

            argv, env = _build_child_command(scn, scn_cwd)
            # Point pubrun output_dir into the throwaway cwd.
            env["PUBRUN_PROFILE"] = env.get("PUBRUN_PROFILE", "default")

            samples: list[float] = []
            failures = 0
            for i in range(iterations + warmup):
                dt = _time_once(argv, env, scn_cwd)
                if dt is None:
                    failures += 1
                    continue
                if i >= warmup:  # discard warmup iterations
                    samples.append(dt)

            entry = {"group": scn.group, "mode": scn.mode, "workload": scn.workload,
                     "config": scn.config or {}, "failures": failures, **_stats(samples)}
            result["scenarios"][scn.name] = entry
            med = entry.get("median_s")
            print(f"  - {scn.name}: median={med*1000:.1f} ms "
                  f"(n={entry['n']}, fail={failures})" if med else
                  f"  - {scn.name}: NO DATA (fail={failures})", file=sys.stderr)

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


def main() -> None:
    ap = argparse.ArgumentParser(description="pubrun overhead benchmark harness")
    ap.add_argument("--quick", action="store_true", help=f"Fast smoke run ({QUICK_ITERATIONS} iters).")
    ap.add_argument("--iterations", type=int, default=None, help="Iterations per scenario.")
    ap.add_argument("--out", type=str, default=None, help="Output JSON path.")
    args = ap.parse_args()

    iterations = args.iterations if args.iterations else (QUICK_ITERATIONS if args.quick else FULL_ITERATIONS)
    out_path = Path(args.out) if args.out else _default_out()
    run(iterations, out_path)


if __name__ == "__main__":
    main()
