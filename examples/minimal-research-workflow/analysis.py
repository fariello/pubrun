#!/usr/bin/env python3
"""
Minimal research workflow example for pubrun.

This script performs a small deterministic synthetic analysis so that reviewers
can see how pubrun records execution provenance for an ordinary Python script.

Example:
    python analysis.py --seed 42 --n 1000
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path
from typing import Dict, List, Sequence

import pubrun


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """
    Parse command-line arguments for the example analysis.

    Args:
        argv:
            Optional argument sequence for testing. When None, argparse reads
            arguments from the command line.

    Returns:
        argparse.Namespace:
            Parsed arguments with ``seed``, ``n``, and ``effect`` fields.

    Example:
        args = parse_args(["--seed", "42", "--n", "1000"])
    """
    parser = argparse.ArgumentParser(
        description="Run a deterministic synthetic analysis with pubrun tracking."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed used to generate synthetic data.",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1000,
        help="Number of synthetic observations to generate.",
    )
    parser.add_argument(
        "--effect",
        type=float,
        default=0.35,
        help="Synthetic effect size added to the treatment group.",
    )

    return parser.parse_args(argv)


def generate_synthetic_data(seed: int, n: int, effect: float) -> List[Dict[str, float]]:
    """
    Generate a deterministic two-group synthetic dataset.

    Args:
        seed:
            Random seed used by Python's standard-library random module.
        n:
            Number of observations to generate.
        effect:
            Additive effect applied to the treatment group.

    Returns:
        list[dict[str, float]]:
            Synthetic observations with ``group`` and ``value`` fields.

    Example:
        rows = generate_synthetic_data(seed=42, n=100, effect=0.25)
    """
    rng = random.Random(seed)
    rows: List[Dict[str, float]] = []

    for index in range(n):
        group = index % 2
        baseline = rng.gauss(0.0, 1.0)
        value = baseline + (effect if group == 1 else 0.0)

        rows.append(
            {
                "id": float(index),
                "group": float(group),
                "value": value,
            }
        )
        pass # for auto-indentation

    return rows


def summarize(rows: List[Dict[str, float]]) -> Dict[str, float]:
    """
    Summarize the synthetic dataset.

    Args:
        rows:
            Synthetic observations produced by ``generate_synthetic_data``.

    Returns:
        dict[str, float]:
            Summary statistics for the control and treatment groups.

    Example:
        summary = summarize(rows)
    """
    control = [row["value"] for row in rows if int(row["group"]) == 0]
    treatment = [row["value"] for row in rows if int(row["group"]) == 1]

    control_mean = statistics.fmean(control)
    treatment_mean = statistics.fmean(treatment)
    observed_effect = treatment_mean - control_mean

    pooled_variance = (
        statistics.variance(control) * (len(control) - 1)
        + statistics.variance(treatment) * (len(treatment) - 1)
    ) / (len(control) + len(treatment) - 2)

    standard_error = math.sqrt(
        pooled_variance * ((1.0 / len(control)) + (1.0 / len(treatment)))
    )

    return {
        "n": float(len(rows)),
        "control_n": float(len(control)),
        "treatment_n": float(len(treatment)),
        "control_mean": control_mean,
        "treatment_mean": treatment_mean,
        "observed_effect": observed_effect,
        "standard_error": standard_error,
        "z_like_statistic": observed_effect / standard_error,
    }


def write_outputs(rows: List[Dict[str, float]], summary: Dict[str, float]) -> None:
    """
    Write ordinary analysis outputs to the local example output directory.

    Args:
        rows:
            Synthetic observations.
        summary:
            Summary statistics.

    Returns:
        None.

    Example:
        write_outputs(rows, summary)
    """
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    with (output_dir / "synthetic_data.csv").open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["id", "group", "value"])
        writer.writeheader()
        writer.writerows(rows)
        pass # for auto-indentation

    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    pass # for auto-indentation


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the example analysis.

    Args:
        argv:
            Optional argument sequence for testing. When None, arguments are read
            from the command line.

    Returns:
        int:
            Process exit code. Returns 0 on success.

    Example:
        raise SystemExit(main(["--seed", "42", "--n", "1000"]))
    """
    args = parse_args(argv)

    pubrun.annotate(
        "example_started",
        seed=args.seed,
        n=args.n,
        effect=args.effect,
    )

    with pubrun.phase("generate_synthetic_data"):
        rows = generate_synthetic_data(seed=args.seed, n=args.n, effect=args.effect)

    with pubrun.phase("summarize"):
        summary = summarize(rows)

    with pubrun.phase("write_outputs"):
        write_outputs(rows, summary)

    pubrun.report("summary", summary)
    pubrun.artifact(
        "example_summary.json",
        json.dumps(summary, indent=2, sort_keys=True),
    )

    pubrun.annotate(
        "example_completed",
        observed_effect=summary["observed_effect"],
        z_like_statistic=summary["z_like_statistic"],
    )

    print("Synthetic analysis complete.")
    print(f"Rows: {int(summary['n'])}")
    print(f"Observed effect: {summary['observed_effect']:.4f}")
    print("Outputs written to ./outputs/")
    print("Run provenance written to ./runs/")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
