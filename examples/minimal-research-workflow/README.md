# Minimal Research Workflow Example

This example demonstrates how to use `pubrun` to monitor and capture the metadata, lifecycle events, and outputs of a computational research workflow.

## Overview

The workflow in [`analysis.py`](analysis.py) performs a linear regression fit on synthetic 2D data. It uses `pubrun` to:
1. Divide the script execution into logical execution phases using `pubrun.phase()`.
2. Annotate progress milestones with custom metadata using `pubrun.annotate()`.
3. Save structured JSON/text reports using `pubrun.report()`.
4. Register raw CSV outputs using `pubrun.artifact()`.

## Running the Example

To run this example locally:

```bash
# Run the analysis script under pubrun tracking
python analysis.py
```

This will automatically create a run directory inside `./runs/` containing:
- `manifest.json`: The machine-readable execution manifest.
- `stdout.log`: A transcript of stdout/stderr logs.
- `raw_data.csv`: A CSV artifact of the generated synthetic data.
- `predictions.csv`: A CSV artifact containing predictions and targets.
- `evaluation_metrics.json`: The structured JSON report of the model metrics and coefficients.

To compile a methods section from this run:
```bash
# Generate the methods text
pubrun methods
```

To view a diagnostic report:
```bash
# View the run status and details
pubrun status
```

---

## Reviewer & Replication Notes

### Machine-Specific / Non-Deterministic Fields in the Manifest

When verifying or replicating this run on different machines, certain sections of `manifest.json` will naturally differ. These do not affect scientific correctness but reflect host environment variance:

1. **`host`**:
   - `hostname`: The local machine name.
   - `cpu_model` and `cpu_cores`: Host hardware specifications.
   - `total_ram_bytes`: Available physical memory.
2. **`environment`**:
   - Path-related variables (like `PATH`, `PWD`, `PYTHONPATH`, `VIRTUAL_ENV`) reflect local directory structures.
   - Usernames (e.g. `USER`, `HOME`, `LOGNAME`) contain host user details.
3. **`timing`**:
   - `started_at_utc`, `ended_at_utc`, and `elapsed_seconds` vary depending on system clock time and processor speed.
4. **`git`**:
   - The commit hash (`sha`) and status flag (`dirty`) reflect the local repository state.

### Redaction Policy

To prevent accidental leaks of secrets (such as cloud credentials, passwords, or API tokens), `pubrun` automatically redacts sensitive environment variables. In the generated manifest:
- Variables matching secret patterns (e.g. `*PASSWORD*`, `*KEY*`, `*TOKEN*`) are replaced with `{"representation": "redacted"}`.
- This redaction is destructive by default. Raw values are not hashed or stored.
