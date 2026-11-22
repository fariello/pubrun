#!/usr/bin/env python3
"""Local, non-publishing package-capture startup and finalization benchmark for pubrun.

Measures the two package-capture costs a tracked run pays, separately:

- **startup**: ``get_packages(cfg, stage="startup")``, the crash-safe snapshot taken
  while the run initializes;
- **finalization**: ``get_packages(cfg, stage="final", include_transitive=...)`` plus
  ``merge_package_snapshots(startup, final, config=cfg)``, the refresh that records
  late imports. This mirrors ``Run._refresh_packages_at_finalization()``, including
  ``include_transitive=False`` for ``imported-transitive`` (the closure is computed once
  inside the merge) and the early return for ``mode = "off"``.

It runs every mode (``off``, ``imported-only``, ``imported-transitive``,
``top-level-installed``, ``full-environment``) against three environment profiles:

- ``small`` and ``large``: deterministic synthetic ``site-packages`` trees (``.dist-info``
  metadata, ``Requires-Dist`` chains with PEP 508 markers and extras, import names that
  differ from distribution names) run under ``python -S`` so only the synthetic
  distributions are installed;
- ``ambient``: the interpreter running this script, with its real installed packages.

Cold samples come from a fresh child process per run (empty distribution cache).
Warm samples come from one child process per (profile, mode) that runs one discarded
warmup pass and then repeats the pass, so the environment-fingerprinted distribution
cache is reused.

Standard library only. Nothing is published and no scheduler job is submitted; the
optional ``--json-out`` file is written locally and is redacted (no hostname, username,
or machine-local path).

Usage:
    python benchmarks/package_capture_bench.py
    python benchmarks/package_capture_bench.py --small-count 10 --large-count 300 \\
        --repetitions 10 --cold-runs 3
    python benchmarks/package_capture_bench.py --workdir /path/to/shared/scratch \\
        --json-out results.json
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
_SRC_ROOT = _REPO_ROOT / "src"

if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

SCHEMA_VERSION = "pubrun-package-capture-bench/1"
MODES = (
    "off",
    "imported-only",
    "imported-transitive",
    "top-level-installed",
    "full-environment",
)
PROFILES = ("small", "large", "ambient")
_PROBE_MARKER = "__PUBRUN_PKG_BENCH_JSON__:"
_CHILD_TIMEOUT_S = 600.0
# Stdlib modules imported late in the ambient profile: they exercise the
# finalization refresh path (and its stdlib filtering) without importing
# arbitrary third-party packages that could have side effects.
_AMBIENT_LATE_IMPORTS = ("csv", "decimal", "fractions")


# ---------------------------------------------------------------------------
# Child process: one measured pass (or warmup plus repeated passes)
# ---------------------------------------------------------------------------

def _child_main(spec: Dict[str, Any]) -> int:
    """Run inside a fresh interpreter; print one marker line with JSON samples."""
    sys.dont_write_bytecode = True
    for entry in reversed(spec.get("extra_paths") or []):
        sys.path.insert(0, entry)
    if spec.get("site_dir"):
        sys.path.insert(0, spec["site_dir"])

    import pubrun.minimal  # noqa: F401  (selects no-auto-start mode before core loads)
    from pubrun.capture import packages as pkgs

    mode = spec["mode"]
    cfg = {"capture": {"packages": {"mode": mode}}}
    late = list(spec.get("late_modules") or [])
    for name in spec.get("startup_modules") or []:
        importlib.import_module(name)

    def one_pass() -> Dict[str, Any]:
        t0 = time.perf_counter()
        startup = pkgs.get_packages(cfg, stage="startup")
        t1 = time.perf_counter()
        for name in late:
            importlib.import_module(name)
        t2 = time.perf_counter()
        if mode == "off":
            merged: Dict[str, Any] = {"capture_state": {"status": "suppressed"}}
        else:
            final = pkgs.get_packages(
                cfg,
                stage="final",
                include_transitive=(mode != "imported-transitive"),
            )
            merged = pkgs.merge_package_snapshots(startup, final, config=cfg)
        t3 = time.perf_counter()
        return {
            "startup_ms": (t1 - t0) * 1000.0,
            "finalization_ms": (t3 - t2) * 1000.0,
            "records": len(merged.get("records") or []),
            "unresolved": len(merged.get("unresolved") or []),
            "status": (merged.get("capture_state") or {}).get("status"),
        }

    def unload_late() -> None:
        # Make the late imports late again for the next warm pass. Bytecode
        # writing is disabled, so re-importing does not touch directory mtimes
        # (which feed the distribution-cache fingerprint).
        for name in late:
            for key in [k for k in sys.modules if k == name or k.startswith(name + ".")]:
                sys.modules.pop(key, None)

    warm_reps = int(spec.get("warm_reps") or 0)
    out: Dict[str, Any] = {"cold": None, "warm": []}
    first = one_pass()
    if warm_reps == 0:
        out["cold"] = first
    else:
        # ``first`` is the discarded warmup pass.
        for _ in range(warm_reps):
            unload_late()
            out["warm"].append(one_pass())
    # Counted after timing; skipped for ``off`` so the baseline never builds the index.
    out["indexed_distributions"] = None
    if mode != "off":
        try:
            out["indexed_distributions"] = len(
                pkgs._get_distribution_index().by_normalized_name
            )
        except Exception:
            out["indexed_distributions"] = None
    sys.stdout.write(_PROBE_MARKER + json.dumps(out) + "\n")
    sys.stdout.flush()
    return 0


# ---------------------------------------------------------------------------
# Synthetic environment builder
# ---------------------------------------------------------------------------

def _dist_name(i: int) -> str:
    return f"pcbench-dist-{i:04d}"


def _import_name(i: int) -> str:
    # Every import name differs from its distribution name; every seventh
    # distribution uses a further-mismatched alias.
    return f"pcbench_alias_{i:04d}" if i % 7 == 3 else f"pcbench_mod_{i:04d}"


def _requires_for(i: int, count: int) -> List[str]:
    reqs: List[str] = []
    if (i + 1) % 5 != 0 and i + 1 < count:
        reqs.append(_dist_name(i + 1))
    if i % 10 == 0 and i + 2 < count:
        reqs.append(f'{_dist_name(i + 2)}; python_version >= "3"')
    if i % 10 == 5 and i + 3 < count:
        reqs.append(f'{_dist_name(i + 3)}; extra == "fast"')
    if i % 20 == 0 and i + 5 < count:
        reqs.append(f"{_dist_name(i + 5)}[fast]")
    return reqs


def build_synthetic_site(root: Path, count: int) -> Path:
    """Create ``root/site-packages`` with ``count`` synthetic distributions."""
    site_dir = root / "site-packages"
    site_dir.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        dist = _dist_name(i)
        mod = _import_name(i)
        version = f"1.0.{i}"
        pkg_dir = site_dir / mod
        pkg_dir.mkdir(exist_ok=True)
        (pkg_dir / "__init__.py").write_text(f"VALUE = {i}\n", encoding="utf-8")
        info_dir = site_dir / f"{dist.replace('-', '_')}-{version}.dist-info"
        info_dir.mkdir(exist_ok=True)
        meta_lines = ["Metadata-Version: 2.1", f"Name: {dist}", f"Version: {version}"]
        if i % 10 == 5:
            meta_lines.append("Provides-Extra: fast")
        meta_lines.extend(f"Requires-Dist: {r}" for r in _requires_for(i, count))
        (info_dir / "METADATA").write_text("\n".join(meta_lines) + "\n", encoding="utf-8")
        (info_dir / "top_level.txt").write_text(mod + "\n", encoding="utf-8")
        (info_dir / "INSTALLER").write_text("pcbench\n", encoding="utf-8")
        info_rel = info_dir.name
        record = [
            f"{mod}/__init__.py,,",
            f"{info_rel}/METADATA,,",
            f"{info_rel}/top_level.txt,,",
            f"{info_rel}/INSTALLER,,",
            f"{info_rel}/RECORD,,",
        ]
        (info_dir / "RECORD").write_text("\n".join(record) + "\n", encoding="utf-8")
    return site_dir


def synthetic_workload(count: int) -> Dict[str, List[str]]:
    """Return the fixed startup-imported and late-imported module subsets."""
    startup_n = max(1, count // 10)
    late_n = max(1, count // 20)
    startup = [_import_name(i) for i in range(0, count, 5)][:startup_n]
    late = [_import_name(i) for i in range(2, count, 5)][:late_n]
    return {"startup_modules": startup, "late_modules": late}


def _isolated_extra_paths(env_root: Path) -> List[str]:
    """Paths a ``python -S`` child needs besides the synthetic site and ``src``.

    On Python < 3.11 pubrun needs ``tomli``; copy just that package (no
    ``.dist-info``) so the synthetic environment still holds only synthetic
    distributions.
    """
    if sys.version_info >= (3, 11):
        return []
    try:
        import importlib.util as _iu
        spec = _iu.find_spec("tomli")
    except Exception:
        spec = None
    if spec is None or not spec.submodule_search_locations:
        return []
    deps = env_root / "deps"
    deps.mkdir(parents=True, exist_ok=True)
    src_dir = Path(list(spec.submodule_search_locations)[0])
    dest = deps / "tomli"
    if not dest.exists():
        shutil.copytree(str(src_dir), str(dest))
    return [str(deps)]


# ---------------------------------------------------------------------------
# Parent orchestration
# ---------------------------------------------------------------------------

def _load_breakdown_helpers():
    import startup_breakdown as sb  # type: ignore  # same directory, stdlib only
    return sb


def _stats(samples: Sequence[float], failures: int) -> Dict[str, Any]:
    sb = _load_breakdown_helpers()
    stats = sb.compute_stats(samples, failures=failures)
    stats["min_ms"] = round(min(samples), 3) if samples else None
    stats["max_ms"] = round(max(samples), 3) if samples else None
    return stats


def _run_child(spec: Dict[str, Any], isolated: bool, workdir: Path) -> Optional[Dict[str, Any]]:
    argv = [sys.executable]
    if isolated:
        argv.append("-S")
    argv.extend([str(Path(__file__).resolve()), "--_child", json.dumps(spec)])
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if isolated:
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONSTARTUP", None)
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            cwd=str(workdir),
            env=env,
            timeout=_CHILD_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        sys.stderr.write("package_capture_bench: child timed out\n")
        return None
    for line in proc.stdout.splitlines():
        if line.startswith(_PROBE_MARKER):
            try:
                return json.loads(line[len(_PROBE_MARKER):])
            except ValueError:
                break
    sb = _load_breakdown_helpers()
    tail = sb.scrub_text(proc.stderr[-800:], extra_needles=[str(workdir)])
    sys.stderr.write(
        f"package_capture_bench: child failed (exit {proc.returncode}): {tail}\n"
    )
    return None


def _measure_mode(
    profile_spec: Dict[str, Any],
    mode: str,
    repetitions: int,
    cold_runs: int,
    isolated: bool,
    workdir: Path,
) -> Dict[str, Any]:
    cold_start: List[float] = []
    cold_final: List[float] = []
    cold_fail = 0
    last_cold: Dict[str, Any] = {}
    indexed: Optional[int] = None
    for _ in range(cold_runs):
        res = _run_child(dict(profile_spec, mode=mode, warm_reps=0), isolated, workdir)
        if not res or not res.get("cold"):
            cold_fail += 1
            continue
        cold_start.append(res["cold"]["startup_ms"])
        cold_final.append(res["cold"]["finalization_ms"])
        last_cold = res["cold"]
        indexed = res.get("indexed_distributions")

    warm_start: List[float] = []
    warm_final: List[float] = []
    warm_fail = 0
    res = _run_child(dict(profile_spec, mode=mode, warm_reps=repetitions), isolated, workdir)
    if res and res.get("warm"):
        for sample in res["warm"]:
            warm_start.append(sample["startup_ms"])
            warm_final.append(sample["finalization_ms"])
        if indexed is None:
            indexed = res.get("indexed_distributions")
        if not last_cold:
            last_cold = res["warm"][-1]
    else:
        warm_fail = repetitions

    return {
        "startup_ms": {
            "cold": _stats(cold_start, cold_fail),
            "warm": _stats(warm_start, warm_fail),
        },
        "finalization_ms": {
            "cold": _stats(cold_final, cold_fail),
            "warm": _stats(warm_final, warm_fail),
        },
        "records": last_cold.get("records"),
        "unresolved": last_cold.get("unresolved"),
        "capture_status": last_cold.get("status"),
        "indexed_distributions": indexed,
        "failures": cold_fail + warm_fail,
    }


def _delta(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    return round(a - b, 3)


def _add_deltas(modes: Dict[str, Dict[str, Any]]) -> None:
    base = modes.get("off")
    if not base:
        return
    for data in modes.values():
        data["delta_vs_off_ms"] = {
            phase: {
                kind: _delta(
                    data[phase][kind]["median_ms"], base[phase][kind]["median_ms"]
                )
                for kind in ("cold", "warm")
            }
            for phase in ("startup_ms", "finalization_ms")
        }


def run_benchmark(
    small_count: int,
    large_count: int,
    repetitions: int,
    cold_runs: int,
    workdir: Optional[str],
) -> Dict[str, Any]:
    """Run all profiles and modes and return the (unredacted-free) result dict."""
    sb = _load_breakdown_helpers()
    if workdir:
        parent = Path(workdir)
        parent.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix="pcbench-", dir=str(parent)))
        workdir_kind = "user-supplied"
    else:
        work = Path(tempfile.mkdtemp(prefix="pcbench-"))
        workdir_kind = "temporary"

    started = datetime.now(timezone.utc)
    try:
        fs_summary = sb._capture_filesystem_summary(work)
        profiles: Dict[str, Any] = {}
        for profile in PROFILES:
            if profile == "ambient":
                spec: Dict[str, Any] = {
                    "site_dir": None,
                    "extra_paths": [],
                    "startup_modules": [],
                    "late_modules": list(_AMBIENT_LATE_IMPORTS),
                }
                isolated = False
                synthetic_count: Optional[int] = None
            else:
                synthetic_count = small_count if profile == "small" else large_count
                env_root = work / profile
                site_dir = build_synthetic_site(env_root, synthetic_count)
                spec = {
                    "site_dir": str(site_dir),
                    "extra_paths": _isolated_extra_paths(env_root),
                }
                spec.update(synthetic_workload(synthetic_count))
                isolated = True
            modes: Dict[str, Any] = {}
            for mode in MODES:
                modes[mode] = _measure_mode(spec, mode, repetitions, cold_runs, isolated, work)
            _add_deltas(modes)
            profiles[profile] = {
                "synthetic_distributions": synthetic_count,
                "startup_imports": len(spec["startup_modules"]),
                "late_imports": len(spec["late_modules"]),
                "isolated_interpreter": isolated,
                "modes": modes,
            }
    finally:
        shutil.rmtree(str(work), ignore_errors=True)
    finished = datetime.now(timezone.utc)

    sha = sb._git_head_sha(_REPO_ROOT)
    workdir_fs = fs_summary.get("workdir", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "environment": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": f"{platform.system()} {platform.release()}",
            "cpu": sb._capture_cpu_summary(),
            "pubrun_version": sb._capture_pubrun_version(),
        },
        "git_revision": sha[:12] if sha else None,
        "filesystem": fs_summary,
        "workdir_fstype": workdir_fs.get("fstype", "unknown"),
        "workdir_is_network": bool(workdir_fs.get("is_network", False)),
        "workdir_kind": workdir_kind,
        "parameters": {
            "small_count": small_count,
            "large_count": large_count,
            "repetitions": repetitions,
            "cold_runs": cold_runs,
            "warmup_passes": 1,
            "modes": list(MODES),
        },
        "profiles": profiles,
    }


def _fmt(val: Optional[float]) -> str:
    return "n/a" if val is None else f"{val:.2f}"


def format_markdown(result: Dict[str, Any]) -> str:
    env = result["environment"]
    params = result["parameters"]
    lines = [
        "# pubrun package-capture benchmark (local, single machine)",
        "",
        f"- Python: {env['python_implementation']} {env['python_version']}",
        f"- Platform: {env['platform']}",
        f"- CPU: {env['cpu'].get('model')} ({env['cpu'].get('logical_cores')} logical cores)",
        f"- Git revision: {result.get('git_revision') or 'unknown'}",
        f"- Workdir filesystem: {result['workdir_fstype']}"
        f" (network: {'yes' if result['workdir_is_network'] else 'no'},"
        f" {result['workdir_kind']})",
        f"- Cold runs: {params['cold_runs']} (fresh process each);"
        f" warm repetitions: {params['repetitions']} after {params['warmup_passes']} warmup pass",
        "",
        "Times are milliseconds. Warm cells show median (IQR).",
        "",
    ]
    for profile, pdata in result["profiles"].items():
        count = pdata.get("synthetic_distributions")
        label = f"{count} synthetic distributions" if count is not None else "ambient interpreter"
        lines.append(
            f"## {profile} ({label}; {pdata['startup_imports']} startup imports,"
            f" {pdata['late_imports']} late imports)"
        )
        lines.append("")
        lines.append(
            "| mode | indexed dists | records | startup cold | startup warm |"
            " final cold | final warm | final warm p95 | final warm delta vs off |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for mode, m in pdata["modes"].items():
            sc, sw = m["startup_ms"]["cold"], m["startup_ms"]["warm"]
            fc, fw = m["finalization_ms"]["cold"], m["finalization_ms"]["warm"]
            delta = (m.get("delta_vs_off_ms") or {}).get("finalization_ms", {}).get("warm")
            lines.append(
                f"| {mode} | {m.get('indexed_distributions')} | {m.get('records')} |"
                f" {_fmt(sc['median_ms'])} | {_fmt(sw['median_ms'])} ({_fmt(sw['iqr_ms'])}) |"
                f" {_fmt(fc['median_ms'])} | {_fmt(fw['median_ms'])} ({_fmt(fw['iqr_ms'])}) |"
                f" {_fmt(fw['p95_ms'])} | {_fmt(delta)} |"
            )
        lines.append("")
    return "\n".join(lines)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Local, non-publishing benchmark of pubrun package capture at startup "
            "and at finalization."
        )
    )
    ap.add_argument("--small-count", type=int, default=10,
                    help="Synthetic distributions in the small profile (default: 10).")
    ap.add_argument("--large-count", type=int, default=300,
                    help="Synthetic distributions in the large profile (default: 300).")
    ap.add_argument("--repetitions", type=int, default=10,
                    help="Warm measured passes per profile and mode (default: 10).")
    ap.add_argument("--cold-runs", type=int, default=3,
                    help="Fresh-process cold runs per profile and mode (default: 3).")
    ap.add_argument(
        "--workdir",
        type=str,
        default=None,
        help=(
            "Optional parent directory for the synthetic environments, for example "
            "a shared NFS or Lustre scratch path. Only a dedicated ephemeral "
            "subdirectory is created inside it, and it is removed on exit."
        ),
    )
    ap.add_argument("--json-out", type=str, default=None,
                    help="Optional local path for the redacted JSON result (never published).")
    ap.add_argument("--_child", type=str, default=None, help=argparse.SUPPRESS)
    return ap.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args._child is not None:
        return _child_main(json.loads(args._child))

    for flag, val, minimum in (
        ("--small-count", args.small_count, 1),
        ("--large-count", args.large_count, 1),
        ("--repetitions", args.repetitions, 1),
        ("--cold-runs", args.cold_runs, 1),
    ):
        if val < minimum:
            print(f"error: {flag} must be an integer >= {minimum}", file=sys.stderr)
            return 2

    try:
        result = run_benchmark(
            small_count=args.small_count,
            large_count=args.large_count,
            repetitions=args.repetitions,
            cold_runs=args.cold_runs,
            workdir=args.workdir,
        )
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    sb = _load_breakdown_helpers()
    extra_needles: List[str] = []
    if args.workdir:
        extra_needles.append(args.workdir)
        extra_needles.append(str(Path(args.workdir).resolve()))
    result = sb.redact_breakdown(result, extra_needles=extra_needles)
    md_text = sb.scrub_text(format_markdown(result), extra_needles=extra_needles)
    ok, reasons = sb.validate_redacted_output(
        result, markdown_text=md_text, extra_needles=extra_needles
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
        out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(md_text + "\n")
    total_failures = sum(
        m.get("failures", 0)
        for p in result["profiles"].values()
        for m in p["modes"].values()
    )
    return 1 if total_failures else 0


if __name__ == "__main__":
    sys.exit(main())
