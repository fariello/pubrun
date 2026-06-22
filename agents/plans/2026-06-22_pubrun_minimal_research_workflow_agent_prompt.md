# Task prompt for Google Antigravity Gemini 3.5 Flash

## Goal

Add a reviewer-friendly minimal research workflow example to the `pubrun` repository.

This example is intended to support JOSS review and ordinary user adoption. It should be small, deterministic, runnable from a clean checkout, and based only on synthetic data. The example should demonstrate that `pubrun` can record execution provenance for an ordinary Python research script and that the command-line tools can inspect, describe, rerun, and compare recorded runs.

Do not make the README or documentation bland. Preserve the practical, approachable tone of the project. The example documentation should be clear, professional, and direct.

## Repository context

Repository: `https://github.com/fariello/pubrun`

Package purpose: `pubrun` provides low-friction execution provenance for ordinary Python research scripts.

The example should demonstrate:

1. `import pubrun` starts run tracking.
2. The script can record user events with `pubrun.annotate()`.
3. The script can record named analysis phases with `pubrun.phase()`.
4. Ordinary analysis outputs are written outside the run directory.
5. `pubrun` records run provenance under a local `runs/` directory.
6. `pubrun status` can inspect runs.
7. `pubrun methods` can generate methods-supporting text.
8. `pubrun rerun` can extract a rerun command.
9. `pubrun diff` can compare two runs.

## Required output files

Create the following directory and files:

```text
examples/minimal-research-workflow/
  README.md
  analysis.py
  expected_methods.md
  manifest_excerpt.json
```

Also add a smoke test:

```text
tests/test_example_minimal_research_workflow.py
```

Update `.gitignore` to ignore generated example output:

```gitignore
examples/minimal-research-workflow/runs/
examples/minimal-research-workflow/outputs/
```

## Coding style requirements

Follow the existing project style. For new Python code:

1. Include `#!/usr/bin/env python3`.
2. Include `from __future__ import annotations`.
3. Use type hints where practical.
4. Use clear, verbose docstrings.
5. Add helpful comments where they clarify purpose.
6. Do not add unnecessary dependencies.
7. Use only the Python standard library plus `pubrun` in the example script.
8. Keep the analysis deterministic.
9. Avoid private data, network calls, credentials, machine-specific paths, or large files.
10. End indented blocks with `pass # for auto-indentation` where appropriate, unless the block already ends with `return`, `raise`, `continue`, `break`, or another natural block-closing statement.

## File 1: `examples/minimal-research-workflow/analysis.py`

Create this file.

```python
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
```

## File 2: `examples/minimal-research-workflow/README.md`

Create this file.

```markdown
# Minimal research workflow example

This example demonstrates how `pubrun` records execution provenance for a small Python analysis. It uses synthetic data and is intended for documentation and review, not as a scientific result.

## What this example shows

This workflow demonstrates:

1. Running an ordinary Python script with `import pubrun`
2. Recording custom analysis events with `pubrun.annotate()`
3. Recording named phases with `pubrun.phase()`
4. Writing ordinary analysis outputs
5. Writing run-attached reports and artifacts
6. Inspecting runs with `pubrun status`
7. Generating methods text with `pubrun methods`
8. Extracting a rerun command with `pubrun rerun`
9. Comparing two runs with `pubrun diff`

## Files

- `analysis.py`: deterministic synthetic analysis using only the Python standard library and `pubrun`
- `README.md`: this guide
- `expected_methods.md`: representative methods output from a completed run
- `manifest_excerpt.json`: redacted excerpt showing the kind of manifest fields produced by `pubrun`

## Run the example

From the repository root:

```bash
cd examples/minimal-research-workflow
python -m pip install pubrun
python analysis.py --seed 42 --n 1000
```

For a local development checkout, use this instead from the repository root:

```bash
python -m pip install -e .
cd examples/minimal-research-workflow
python analysis.py --seed 42 --n 1000
```

After the script completes, `pubrun` writes a local run directory under:

```text
runs/
```

The script also writes ordinary analysis outputs under:

```text
outputs/
```

## Inspect recent runs

```bash
pubrun status
```

For more detail:

```bash
pubrun status -v
```

## Generate methods text

By default, this uses the most recent run in `./runs`:

```bash
pubrun methods --format markdown
```

You can also pass a specific run directory:

```bash
pubrun methods ./runs/<RUN_DIRECTORY> --format markdown
```

## Extract a rerun command

```bash
pubrun rerun ./runs/<RUN_DIRECTORY>
```

## Compare two runs

Create two runs with different seeds:

```bash
python analysis.py --seed 42 --n 1000
python analysis.py --seed 43 --n 1000
```

Then compare the two run directories:

```bash
pubrun diff ./runs/<FIRST_RUN_DIRECTORY> ./runs/<SECOND_RUN_DIRECTORY> --basic --same --wrap
```

Use `pubrun status -v` to identify the run directories.

## Notes for reviewers

This example intentionally uses synthetic data so that it can be run without private files, credentials, network access, or domain-specific dependencies.

Generated manifests include machine-specific values such as paths, hostnames, process IDs, timestamps, hardware details, and Python environment details. For that reason, `manifest_excerpt.json` is redacted and shortened rather than copied directly from one developer machine.

The exact output of `pubrun methods` will vary by machine and Python environment. `expected_methods.md` is a representative example, not a byte-for-byte test fixture.
```

## File 3: `examples/minimal-research-workflow/expected_methods.md`

Create this file.

```markdown
# Representative methods output

The exact methods text generated by `pubrun methods` depends on the local machine, Python environment, package state, operating system, and Git state. A completed run of this example should produce methods text similar in purpose to the following:

> Computational experiments were executed using Python in a local command-line environment. Execution provenance was recorded with `pubrun`, including the command-line invocation, Python runtime, dependency state, operating environment, Git state, logs, exit status, and user-recorded analysis events. The analysis used a deterministic synthetic dataset generated with a fixed random seed. The run record was written to a local `pubrun` run directory, and the resulting manifest can be used to inspect the execution context, generate methods-supporting text, compare runs, and extract a rerun command.

To generate current methods text from the latest local run:

```bash
pubrun methods --format markdown
```

To generate methods text from a specific run:

```bash
pubrun methods ./runs/<RUN_DIRECTORY> --format markdown
```
```

## File 4: `examples/minimal-research-workflow/manifest_excerpt.json`

Create this file.

```json
{
  "schema_version": "1.0",
  "manifest_type": "pubrun-manifest",
  "run": {
    "run_id": "a1b2c3d4"
  },
  "timing": {
    "started_at_utc": 1780250544.068,
    "ended_at_utc": 1780250544.412,
    "elapsed_seconds": 0.344
  },
  "invocation": {
    "argv": [
      "analysis.py",
      "--seed",
      "42",
      "--n",
      "1000"
    ],
    "command_line": "python analysis.py --seed 42 --n 1000",
    "rerun_command": "cd /REDACTED/examples/minimal-research-workflow && python analysis.py --seed 42 --n 1000",
    "entrypoint_type": "script",
    "script": {
      "path": "/REDACTED/examples/minimal-research-workflow/analysis.py",
      "basename": "analysis.py",
      "sha256": "REDACTED"
    },
    "working_directory": {
      "path": "/REDACTED/examples/minimal-research-workflow",
      "real_path": "/REDACTED/examples/minimal-research-workflow"
    }
  },
  "python": {
    "implementation": "cpython",
    "version": "REDACTED",
    "virtual_env": "REDACTED_OR_NULL"
  },
  "git": {
    "repo_root": "/REDACTED/pubrun",
    "commit": "REDACTED",
    "branch": "main",
    "dirty": false,
    "remote_url": {
      "representation": "redacted"
    }
  },
  "host": {
    "os_name": "REDACTED",
    "hostname": "REDACTED"
  },
  "signals": {
    "signals_received": [],
    "exit_code": 0,
    "exit_exception": null
  },
  "status": {
    "outcome": "completed"
  },
  "capture": {
    "output_base_dir": "./runs",
    "run_dir": "./runs/pubrun-analysis-REDACTED"
  }
}
```

## File 5: `tests/test_example_minimal_research_workflow.py`

Create this file.

```python
#!/usr/bin/env python3
"""
Smoke test for the minimal research workflow example.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_minimal_research_workflow_runs(tmp_path: Path) -> None:
    """
    Verify that the minimal research workflow example executes successfully.

    Args:
        tmp_path:
            Pytest-provided temporary directory.

    Returns:
        None.
    """
    repo_root = Path(__file__).resolve().parents[1]
    example_dir = repo_root / "examples" / "minimal-research-workflow"
    script_path = example_dir / "analysis.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--seed",
            "42",
            "--n",
            "100",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Synthetic analysis complete." in completed.stdout
    assert (tmp_path / "outputs" / "summary.json").exists()

    run_dirs = sorted((tmp_path / "runs").glob("pubrun-analysis-*"))
    assert run_dirs, "Expected pubrun to create at least one run directory."

    latest_run = run_dirs[-1]
    assert (latest_run / "manifest.json").exists()
    assert (latest_run / "config.resolved.json").exists()

    pass # for auto-indentation
```

## Update `.gitignore`

Add the following lines if equivalent ignores do not already exist:

```gitignore
# pubrun example outputs
examples/minimal-research-workflow/runs/
examples/minimal-research-workflow/outputs/
```

## Validation commands

Run these commands from the repository root.

```bash
python -m pytest tests/test_example_minimal_research_workflow.py -v
python -m pytest tests/ -v
```

Then manually run the example:

```bash
python -m pip install -e .
cd examples/minimal-research-workflow
python analysis.py --seed 42 --n 1000
pubrun status
pubrun methods --format markdown
python analysis.py --seed 43 --n 1000
pubrun status -v
```

Use the two run directories shown by `pubrun status -v` to run:

```bash
pubrun diff ./runs/<FIRST_RUN_DIRECTORY> ./runs/<SECOND_RUN_DIRECTORY> --basic --same --wrap
pubrun rerun ./runs/<SECOND_RUN_DIRECTORY>
```

## Acceptance criteria

The task is complete only when all of the following are true:

1. `examples/minimal-research-workflow/README.md` exists.
2. `examples/minimal-research-workflow/analysis.py` exists and runs successfully.
3. `examples/minimal-research-workflow/expected_methods.md` exists.
4. `examples/minimal-research-workflow/manifest_excerpt.json` exists and contains only redacted or non-sensitive values.
5. `tests/test_example_minimal_research_workflow.py` exists and passes.
6. Running the example creates `outputs/summary.json`.
7. Running the example creates at least one `runs/pubrun-analysis-*` directory.
8. The run directory contains `manifest.json`.
9. `pubrun status` can inspect the run.
10. `pubrun methods --format markdown` produces methods-supporting text.
11. Two runs with different seeds can be compared using `pubrun diff`.
12. A rerun command can be extracted using `pubrun rerun`.
13. Generated `runs/` and `outputs/` directories are ignored by git.
14. The full test suite still passes.

## Commit message

Use this commit message:

```text
Add minimal research workflow example
```
