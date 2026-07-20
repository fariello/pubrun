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

# Tier presets: (iterations, measured passes). Every tier also runs one uncaptured baseline
# pass first. --iterations/--passes override the preset.
#   quick    = a fast smoke run       (2 x 15)
#   default  = the standard run       (3 x 30)
#   rigorous = tight-CI / overnight   (5 x 50)
_TIERS = {
    "quick": (15, 2),
    "default": (30, 3),
    "rigorous": (50, 5),
}


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
            # Python install (stdlib/interpreter) — a startup-I/O source; on NFS it
            # dominates import time independent of where the run writes.
            "python_prefix": sys.base_prefix,
        }
        try:
            import pubrun
            pkg_file = getattr(pubrun, "__file__", None)
            if pkg_file:
                paths["pubrun_install"] = str(Path(pkg_file).resolve().parent)
        except Exception:
            pass
        # /dev/shm (RAM-backed tmpfs) — a devshm I/O-baseline target when present.
        if os.path.isdir("/dev/shm"):
            paths["devshm"] = "/dev/shm"
        # The actual I/O-baseline target, if the scenarios point PUBRUN_BENCH_IO_TARGET
        # somewhere non-obvious (e.g. an NFS $TMPDIR) — so a slow baseline is interpretable.
        io_target = os.environ.get("PUBRUN_BENCH_IO_TARGET")
        if io_target and io_target not in ("/dev/null", "NUL") and os.path.exists(io_target):
            paths["io_target"] = io_target
        fs_data = get_filesystem({}, paths)
        # Live capacity/health probe (bench is an explicit diagnostic context — NOT the
        # import path). Deduped by mount; a wedged mount is recorded as pending/hung rather
        # than hanging the harness. Never raises.
        try:
            from pubrun.capture.filesystem import probe_paths_live
            probe_paths_live(fs_data)
        except Exception:
            pass
        return fs_data
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


# Timings are rounded to this many decimal places in the STORED file (schema/5). Six places
# is microsecond-ish on a wall-clock second, far finer than any real signal, and it is the
# decisive size lever: rounding + de-duplication lands the shared file well under the GitHub
# issue-body cap with NO analytical data loss (every raw sample is retained, only rounded).
_TIMING_DECIMALS = 6


def _round_timings(samples: list[float]) -> list[float]:
    return [round(s, _TIMING_DECIMALS) for s in samples]


def _run_pass(pass_no: int, iterations: int, warmup: int, workdir: Path) -> dict:
    """Run the whole scenario sweep once (schema/5 compact shape).

    Returns ``{"defs": {name: {group, mode, workload, config}}, "timings": {name: [..6dp..]},
    "failures": {name: int}, "skipped": {name: reason}}``. Static scenario descriptors live in
    ``defs`` (hoisted to the top-level ``scenario_defs`` map by :func:`run`, defined ONCE);
    per pass we keep only what VARIES (timings, failures, skips)."""
    scns = _scenarios.all_scenarios()
    defs: dict = {}
    timings: dict = {}
    failures_map: dict = {}
    skipped: dict = {}
    for scn in scns:
        defs[scn.name] = {"group": scn.group, "mode": scn.mode,
                          "workload": scn.workload, "config": scn.config or {}}
        skip = scn.skip_if() if scn.skip_if else None
        if skip:
            skipped[scn.name] = skip
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

        # Raw per-iteration wall times IN RUN ORDER (schema/5), rounded to 6 dp: the source of
        # truth. Derived stats are NOT stored (they are recomputable from these samples);
        # readers recompute them. Only the raw samples allow later re-analysis (any statistic,
        # distribution shape, order/warmup drift) and CORRECT pooling across submissions.
        timings[scn.name] = _round_timings(samples)
        failures_map[scn.name] = failures
        st = _stats(samples)
        med = st.get("median_s")
        print(f"  [pass {pass_no}] {scn.name}: median={med*1000:.1f} ms "
              f"(n={st['n']}, fail={failures})" if med else
              f"  [pass {pass_no}] {scn.name}: NO DATA (fail={failures})", file=sys.stderr)
    return {"defs": defs, "timings": timings, "failures": failures_map, "skipped": skipped}


def _run_baseline_pass(iterations: int, warmup: int, workdir: Path) -> dict:
    """Run every scenario's workload WITHOUT pubrun active (a cache-warming + pubrun-absent
    reference sweep). Recorded as the baseline pass (pass 0), in the same schema/5 compact
    shape as a measured pass (timings/failures/skipped maps keyed by scenario name; no
    per-scenario static descriptors, no stored stats)."""
    scns = _scenarios.all_scenarios()
    timings: dict = {}
    failures_map: dict = {}
    skipped: dict = {}
    for scn in scns:
        skip = scn.skip_if() if scn.skip_if else None
        if skip:
            skipped[scn.name] = skip
            continue
        scn_cwd = workdir / "pass0" / scn.name
        scn_cwd.mkdir(parents=True, exist_ok=True)
        (scn_cwd / "runs").mkdir(exist_ok=True)
        # Run the workload directly (no pubrun import), regardless of the scenario's mode.
        workload_path = _HERE / "workloads" / scn.workload
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(_REPO_ROOT / "src")] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        for k, v in getattr(scn, "env", {}).items():
            env[k] = v
        argv = [sys.executable, str(workload_path)]
        samples: list[float] = []
        failures = 0
        for i in range(iterations + warmup):
            dt = _time_once(argv, env, scn_cwd)
            if dt is None:
                failures += 1
                continue
            if i >= warmup:
                samples.append(dt)
        timings[scn.name] = _round_timings(samples)
        failures_map[scn.name] = failures
    return {"timings": timings, "failures": failures_map, "skipped": skipped}


def run(iterations: int, out_path: Path, warmup: int = 1, passes: int = 2,
        mode: str = "default", baseline_pass: bool = True) -> dict:
    scns = _scenarios.all_scenarios()
    machine = _machine_metadata()
    # Enrich the machine block with filesystem type (the NFS signal) and Slurm context
    # so cross-machine / cross-node results are interpretable.
    machine["filesystem"] = _filesystem_context()
    slurm = _slurm_context()
    if slurm:
        machine["slurm"] = slurm
    _wall_start = time.perf_counter()
    result = {
        "schema": "pubrun-benchmark/5",
        # UTC timestamp (canonical) AND local time WITH its UTC offset. Storing local+offset
        # explicitly is more reliable than reconstructing local time from UTC after the fact;
        # the offset lives in the data.
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generated_local": datetime.now().astimezone().isoformat(),
        "mode": mode,               # quick | default | rigorous | custom
        "iterations": iterations,   # iterations per pass (fixed for the run)
        "warmup": warmup,           # discarded warmup iterations per pass (fixed for the run)
        "passes": passes,
        "baseline_pass": baseline_pass,
        "git_commit": _git_commit(),
        "machine": machine,
        # Static per-scenario descriptors, defined ONCE (identical across passes): the
        # decisive de-duplication lever for the shared file size. Passes reference scenarios
        # by name. NOTE: intentionally NOT named "scenarios" (schema/1's removed last-pass
        # alias used that key); readers key off scenario_defs + per-pass timings.
        "scenario_defs": {},
        # Each pass is the FULL scenario sweep, run in order. Recording every
        # pass (rather than discarding a warmup pass) makes startup / filesystem
        # caching effects VISIBLE: compare pass 1 vs pass N. Aggregation/reporting
        # can prefer the last pass (warmest) or show the spread. Each pass also
        # records the dynamic host state (RAM/load/iowait) at its start, so a node
        # loaded between passes is visible. Per pass we store only what VARIES:
        # {pass, pass_env, timings:{name:[..6dp..]}, failures:{name:int}, skipped:{name:reason}}.
        "pass_results": [],
    }

    print(f"Running {'baseline (uncaptured) + ' if baseline_pass else ''}{passes} pass(es) x "
          f"{len(scns)} scenarios x {iterations} iterations (+{warmup} warmup each) ...",
          file=sys.stderr)

    with tempfile.TemporaryDirectory(prefix="pubrun-bench-") as td:
        workdir = Path(td)
        # Pass 0: an uncaptured baseline sweep (pubrun absent) — warms caches and records the
        # "cost floor" without pubrun. Kept SEPARATE from the measured passes so aggregation
        # never mixes it into pubrun-overhead stats.
        if baseline_pass:
            print("--- pass 0/baseline (uncaptured) ---", file=sys.stderr)
            b_env = _pass_env()
            b = _run_baseline_pass(iterations, warmup, workdir)
            baseline = {"pass": 0, "uncaptured": True, "pass_env": b_env,
                        "timings": b["timings"], "failures": b["failures"]}
            if b.get("skipped"):
                baseline["skipped"] = b["skipped"]
            result["baseline"] = baseline
        for pass_no in range(1, passes + 1):
            print(f"--- pass {pass_no}/{passes} ---", file=sys.stderr)
            pass_env = _pass_env()
            p = _run_pass(pass_no, iterations, warmup, workdir)
            # Static scenario descriptors are identical across passes: define them ONCE
            # in the top-level scenario_defs map (fixed per run; nothing mutates a def
            # mid-run). Later passes update in place with identical values (a no-op).
            result["scenario_defs"].update(p["defs"])
            entry = {"pass": pass_no, "pass_env": pass_env,
                     "timings": p["timings"], "failures": p["failures"]}
            if p.get("skipped"):
                entry["skipped"] = p["skipped"]
            result["pass_results"].append(entry)

    # Total wall-time for the WHOLE benchmark invocation (harness start -> now), distinct from
    # the summed per-iteration timings.
    result["total_wall_time_s"] = round(time.perf_counter() - _wall_start, 3)

    # Write COMPACT (no indentation): the shared/redacted copy must fit GitHub's issue-body
    # cap; the local unredacted copy uses the same compact form (parses identically).
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    print(f"\nWrote {out_path}", file=sys.stderr)
    return result


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _hostname() -> str:
    try:
        import platform
        return platform.node() or "unknown"
    except Exception:
        return "unknown"


def _host_token(host: str) -> str:
    """A stable, NON-identifying token for the redacted filename: the first 8 hex of the
    SHA-256 of the hostname. Deterministic per host (so a host's redacted files sort/group)
    yet does not embed the hostname itself, matching the in-file hostname redaction."""
    import hashlib
    return hashlib.sha256(host.encode("utf-8", "replace")).hexdigest()[:8]


def _default_out() -> Path:
    """The FULL (unredacted) result path. Always a ``*.unredacted.json`` name (never a bare
    ``*.json``); embeds the real hostname (this local copy is for your own analysis)."""
    safe_host = "".join(c if c.isalnum() or c in "-_" else "_" for c in _hostname())
    return _HERE / "results" / f"{safe_host}-{_utc_stamp()}.unredacted.json"


def _default_redacted_out(unredacted: Path) -> Path:
    """The shareable (redacted) result path derived from an unredacted path. The filename must
    NOT embed the hostname: use ``pubrun-bench-<8hexOfSHA256(hostname)>-<utcstamp>.redacted.json``.
    The UTC stamp is taken from the unredacted name when present so the pair is correlatable."""
    host = _hostname()
    stamp = None
    # Reuse the stamp from the unredacted filename (…-YYYYMMDD-HHMMSS.unredacted.json).
    name = unredacted.name
    for suffix in (".unredacted.json", ".json"):
        if name.endswith(suffix):
            stem = name[: -len(suffix)]
            parts = stem.rsplit("-", 2)
            if len(parts) == 3 and len(parts[1]) == 8 and len(parts[2]) == 6:
                stamp = f"{parts[1]}-{parts[2]}"
            break
    if stamp is None:
        stamp = _utc_stamp()
    return unredacted.parent / f"pubrun-bench-{_host_token(host)}-{stamp}.redacted.json"


_REDACTED = "<redacted>"

# GitHub caps an issue body at 65,536 bytes; the submission path embeds the redacted JSON in
# the body. Warn (never fail) a bit under the hard cap so the fenced-block wrapper still fits.
_GH_ISSUE_BODY_LIMIT = 65000


def _warn_if_over_gh_cap(path: Path) -> None:
    """Warn (non-fatal) if a redacted result exceeds the GitHub issue-body budget, pointing at
    the attach-file alternative. Shared with the ``pubrun bench`` submit path."""
    try:
        size = path.stat().st_size
    except OSError:
        return
    if size > _GH_ISSUE_BODY_LIMIT:
        print(
            f"WARNING: {path.name} is {size} bytes, over GitHub's ~65 KB issue-body limit "
            f"({_GH_ISSUE_BODY_LIMIT} byte guard). The in-body submission path will be "
            "rejected; ATTACH the file to the issue instead of pasting it.",
            file=sys.stderr,
        )

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
    tier = ap.add_mutually_exclusive_group()
    tier.add_argument("--quick", action="store_true", help="Fast smoke run (2 passes x 15 iters).")
    tier.add_argument("--rigorous", action="store_true", help="Tight-CI run (5 passes x 50 iters); long.")
    ap.add_argument("--iterations", type=int, default=None, help="Override iterations per scenario.")
    ap.add_argument("--passes", type=int, default=None,
                    help="Override the number of measured scenario sweeps.")
    ap.add_argument("--no-baseline", action="store_true",
                    help="Skip the initial uncaptured baseline pass.")
    ap.add_argument("--out", type=str, default=None, help="Output JSON path.")
    ap.add_argument("--redacted-out", type=str, default=None,
                    help="Also write a redacted copy (safe to share publicly) to this path.")
    args = ap.parse_args()

    # Tier selection: quick / default / rigorous. Every tier runs 1 uncaptured baseline pass
    # first (unless --no-baseline), then N measured passes of M iterations. --iterations /
    # --passes override the tier's preset.
    mode = "quick" if args.quick else ("rigorous" if args.rigorous else "default")
    tier_iters, tier_passes = _TIERS[mode]
    iterations = args.iterations if args.iterations else tier_iters
    passes = max(1, args.passes) if args.passes else tier_passes
    if args.iterations or args.passes:
        mode = "custom"
    out_path = Path(args.out) if args.out else _default_out()
    result = run(iterations, out_path, passes=passes, mode=mode,
                 baseline_pass=not args.no_baseline)
    if args.redacted_out:
        red_path = Path(args.redacted_out)
        red_path.parent.mkdir(parents=True, exist_ok=True)
        # Compact (no indent): the redacted copy must fit GitHub's issue-body cap.
        red_path.write_text(json.dumps(redact_result(result), separators=(",", ":")),
                            encoding="utf-8")
        print(f"Wrote redacted copy {red_path}", file=sys.stderr)
        # Non-fatal size guard: warn if the shareable file is too big for the GitHub
        # issue-body submission path (~65 KB); suggest attaching the file instead.
        _warn_if_over_gh_cap(red_path)


if __name__ == "__main__":
    main()
