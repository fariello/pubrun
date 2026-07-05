#!/usr/bin/env python3
"""Render overhead figures from aggregated pubrun benchmark results.

Requires the optional plotting extra:  pip install -e .[bench]

This is NOT needed to collect or aggregate data (harness.py and aggregate.py are
stdlib-only). It only turns an aggregated CSV into PNG figures for the paper.

Usage:
    python benchmarks/plot.py benchmarks/results/summary.csv --out benchmarks/results/
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _need_matplotlib():
    try:
        import matplotlib  # noqa: F401
        matplotlib.use("Agg")  # headless
        import matplotlib.pyplot as plt
        return plt
    except Exception:
        print(
            "matplotlib is required for plotting but is not installed.\n"
            "Install the optional extra:\n\n"
            "    pip install -e .[bench]\n\n"
            "Data collection (harness.py) and aggregation (aggregate.py) do NOT "
            "require it.",
            file=sys.stderr,
        )
        sys.exit(2)


def _read_rows(csv_path: Path) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def plot_group(plt, rows: list[dict], group: str, out_dir: Path) -> Path | None:
    grp = [r for r in rows if r.get("group") == group and _fnum(r.get("overhead_ms")) is not None]
    if not grp:
        return None
    # Average across machines per scenario (usually one machine per CSV).
    by_scn: dict[str, list[float]] = {}
    for r in grp:
        by_scn.setdefault(r["scenario"], []).append(_fnum(r["overhead_ms"]))
    names = sorted(by_scn)
    vals = [sum(by_scn[n]) / len(by_scn[n]) for n in names]

    fig, ax = plt.subplots(figsize=(9, max(3, 0.5 * len(names))))
    ax.barh(names, vals, color="#3b7dd8")
    ax.set_xlabel("Overhead vs baseline (ms, median)")
    ax.set_title(f"pubrun overhead — {group}")
    ax.invert_yaxis()
    fig.tight_layout()
    out = out_dir / f"overhead-{group}.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Plot pubrun overhead figures.")
    ap.add_argument("csv", nargs="?", default=str(_HERE / "results" / "summary.csv"))
    ap.add_argument("--out", default=str(_HERE / "results"))
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print(f"No such CSV: {csv_path}. Run aggregate.py first.", file=sys.stderr)
        sys.exit(1)

    plt = _need_matplotlib()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = _read_rows(csv_path)

    produced = []
    for group in ("startup", "feature", "hotpath"):
        p = plot_group(plt, rows, group, out_dir)
        if p:
            produced.append(p)
    if produced:
        print("Wrote:\n  " + "\n  ".join(str(p) for p in produced), file=sys.stderr)
    else:
        print("No plottable rows found in the CSV.", file=sys.stderr)


if __name__ == "__main__":
    main()
