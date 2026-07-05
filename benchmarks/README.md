# pubrun benchmarks

A reproducible harness for measuring the startup and run-time overhead `pubrun`
adds to a host process, so overhead claims can be verified and aggregated across
machines.

## Design

- **`harness.py`** — stdlib-only measurement core. Runs each scenario in a fresh
  subprocess N times and writes one JSON result (timings + machine metadata).
  Runs anywhere `pubrun` runs, including locked-down HPC nodes. No third-party
  imports.
- **`scenarios.py`** — declarative scenario list (import mode, config overrides,
  workload) grouped into `startup`, `feature`, and `hotpath`.
- **`workloads/`** — tiny scripts the scenarios execute (`noop`, `cpu_burn`,
  `file_read`, `print_loop`).
- **`aggregate.py`** — stdlib-only; merges result JSONs into a CSV + a Markdown
  overhead table (overhead computed vs each group's baseline).
- **`plot.py`** — optional matplotlib figures (requires `pip install -e .[bench]`).
- **`test_benchmarks.py`** — optional `pytest-benchmark` micro-suite for hot
  paths. Not collected by the default `pytest` run.
- **`results/`** — collected result JSONs (committed for reproducibility) plus
  the generated `summary.csv`/`summary.md`.

## Running

Collect data (no extra dependencies needed):

```bash
pip install -e .                 # pubrun itself (zero runtime deps on 3.11+)
python benchmarks/harness.py --quick     # fast smoke run (8 iterations)
python benchmarks/harness.py             # full run (30 iterations)
```

Each run writes `results/<hostname>-<timestamp>.json`.

Aggregate one or many machines' results:

```bash
python benchmarks/aggregate.py benchmarks/results/*.json
# -> benchmarks/results/summary.csv and summary.md
```

Optional figures and the micro-benchmark suite (needs the extra):

```bash
pip install -e .[bench]
python benchmarks/plot.py benchmarks/results/summary.csv
pytest benchmarks/ -o addopts="" --benchmark-only
```

`-o addopts=""` clears the repo's global `--cov` options, which would otherwise
distort pytest-benchmark timings.

## Contributing a result from a new machine

1. `pip install -e .` in a clean environment.
2. `python benchmarks/harness.py` (full run).
3. Commit the produced `results/<hostname>-<timestamp>.json` (raw timings and
   machine metadata are not sensitive; `pubrun`'s own capture is used, which
   redacts secrets).
4. Re-run `aggregate.py` over all results and, if helpful, `plot.py`.

## Interpreting the numbers

- Timings are **wall-clock**, measured by launching a fresh Python subprocess
  per iteration (so import/startup cost is real, not warm-cached). The reported
  statistic is the **median** (plus p95 and stdev); the first iteration is a
  discarded warmup.
- **Overhead** is the median of a scenario minus its group baseline:
  - `startup` scenarios compare against `baseline-noop` (a bare `python noop.py`).
  - `feature` scenarios compare against `feature-baseline`; note `feature-none`
    (pubrun active with everything off) captures pubrun's fixed startup cost —
    the *marginal* cost of a single feature is its delta above `feature-none`.
  - `hotpath` scenarios pair with their `*-baseline` (e.g. patched `open()` vs
    `builtins.open`).
- Numbers vary by machine, filesystem, and Python version; that is why results
  carry full machine metadata and are aggregated across systems before any
  representative figure is published.
