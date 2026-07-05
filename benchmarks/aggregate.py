#!/usr/bin/env python3
"""Aggregate pubrun benchmark result JSONs into a CSV and a Markdown summary.

Stdlib-only. Merges one or more result files (see ``harness.py``) into:
  - a tidy CSV (one row per machine x scenario), and
  - a Markdown table of overhead relative to each group's baseline.

Overhead is computed within a group against that group's baseline scenario:
  startup  -> baseline-noop
  feature  -> feature-baseline
  hotpath  -> the matching *-baseline scenario (open/print)

Usage:
    python benchmarks/aggregate.py benchmarks/results/*.json
    python benchmarks/aggregate.py results/*.json --csv out.csv --md out.md
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

# Which baseline scenario each scenario is compared against.
_GROUP_BASELINE = {
    "startup": "baseline-noop",
    "feature": "feature-baseline",
}
# hotpath scenarios pair explicitly (scenario -> baseline)
_HOTPATH_BASELINE = {
    "hotpath-open-pubrun": "hotpath-open-baseline",
    "hotpath-print-tee": "hotpath-print-baseline",
}


def _load(paths: list[str]) -> list[dict]:
    runs = []
    for p in paths:
        try:
            runs.append(json.loads(Path(p).read_text(encoding="utf-8")))
        except Exception as e:
            print(f"warning: skipping {p}: {e}", file=sys.stderr)
    return runs


def _machine_label(run: dict) -> str:
    m = run.get("machine", {})
    cpu = (m.get("hardware", {}) or {}).get("cpu", {}) or {}
    os_name = (m.get("host", {}) or {}).get("os_name", "?")
    return f"{os_name}/{cpu.get('model', '?')}/{cpu.get('logical_cores', '?')}c"


def _baseline_for(name: str, group: str) -> str | None:
    if name in _HOTPATH_BASELINE:
        return _HOTPATH_BASELINE[name]
    return _GROUP_BASELINE.get(group)


def build_rows(runs: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for run in runs:
        label = _machine_label(run)
        pubrun_version = (run.get("machine", {}) or {}).get("pubrun_version")
        scns = run.get("scenarios", {})
        for name, s in scns.items():
            if s.get("skipped"):
                continue
            group = s.get("group", "?")
            base_name = _baseline_for(name, group)
            base = scns.get(base_name, {}) if base_name else {}
            med = s.get("median_s")
            base_med = base.get("median_s")
            overhead_ms = None
            overhead_pct = None
            if med is not None and base_med is not None and base_name != name:
                overhead_ms = (med - base_med) * 1000.0
                if base_med > 0:
                    overhead_pct = (med - base_med) / base_med * 100.0
            rows.append({
                "machine": label,
                "pubrun_version": pubrun_version,
                "group": group,
                "scenario": name,
                "mode": s.get("mode"),
                "workload": s.get("workload"),
                "median_ms": None if med is None else round(med * 1000, 2),
                "p95_ms": None if s.get("p95_s") is None else round(s["p95_s"] * 1000, 2),
                "stdev_ms": None if s.get("stdev_s") is None else round(s["stdev_s"] * 1000, 2),
                "n": s.get("n"),
                "vs_baseline": base_name if base_name != name else "",
                "overhead_ms": None if overhead_ms is None else round(overhead_ms, 2),
                "overhead_pct": None if overhead_pct is None else round(overhead_pct, 1),
            })
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    fields = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_markdown(rows: list[dict], path: Path) -> None:
    lines = ["# pubrun overhead summary", ""]
    machines = sorted({r["machine"] for r in rows})
    lines.append(f"Machines aggregated: {len(machines)}")
    for mlabel in machines:
        lines.append(f"- `{mlabel}`")
    lines.append("")
    lines.append("Overhead is median wall time relative to the group baseline "
                 "(a fresh Python process with no pubrun / no features).")
    lines.append("")
    lines.append("| Machine | Group | Scenario | Median (ms) | p95 (ms) | vs baseline | Overhead (ms) | Overhead (%) |")
    lines.append("|---|---|---|---:|---:|---|---:|---:|")
    for r in sorted(rows, key=lambda x: (x["machine"], x["group"], x["scenario"])):
        lines.append(
            f"| {r['machine']} | {r['group']} | {r['scenario']} | "
            f"{r['median_ms']} | {r['p95_ms']} | {r['vs_baseline'] or '-'} | "
            f"{'-' if r['overhead_ms'] is None else r['overhead_ms']} | "
            f"{'-' if r['overhead_pct'] is None else r['overhead_pct']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Aggregate pubrun benchmark results.")
    ap.add_argument("inputs", nargs="+", help="Result JSON files or globs.")
    ap.add_argument("--csv", default=str(_HERE / "results" / "summary.csv"))
    ap.add_argument("--md", default=str(_HERE / "results" / "summary.md"))
    args = ap.parse_args()

    paths: list[str] = []
    for pat in args.inputs:
        expanded = glob.glob(pat)
        paths.extend(expanded if expanded else [pat])
    runs = _load(paths)
    if not runs:
        print("No valid result files found.", file=sys.stderr)
        sys.exit(1)

    rows = build_rows(runs)
    write_csv(rows, Path(args.csv))
    write_markdown(rows, Path(args.md))
    print(f"Aggregated {len(runs)} run(s), {len(rows)} rows -> {args.csv}, {args.md}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
