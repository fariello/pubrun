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
python benchmarks/harness.py --quick     # fast smoke run (2 passes x 8 iterations)
python benchmarks/harness.py             # full run (2 passes x 30 iterations)
python benchmarks/harness.py --passes 1  # single pass (skip cache-warming)
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

## Running on a Slurm cluster

Two helper scripts submit the harness as a batch job:

- `run_bench.sbatch` — the job itself (single node, ~4 CPUs, few minutes). Writes
  a node-tagged result to `benchmarks/results/<node>-<timestamp>.json`.
- `submit_bench.sh` — picks a **random idle CPU node** (via `sinfo`) and submits
  the job to it; falls back to an unpinned submit if none are idle.

```bash
# random idle node, full 2-pass run:
benchmarks/submit_bench.sh

# forward harness args (e.g. a quick smoke run):
benchmarks/submit_bench.sh --quick

# choose a partition and exclude GPU nodes; use a venv python:
PUBRUN_PARTITION=compute PUBRUN_EXCLUDE='^gpu' \
  PUBRUN_PY="$HOME/venv/p3.14/bin/python" benchmarks/submit_bench.sh
```

Environment knobs (all optional): `PUBRUN_PARTITION`, `PUBRUN_PY` (default
`python3`), `PUBRUN_REPO`, `PUBRUN_EXCLUDE` (regex of node names to skip). The
job fails fast with a clear message if `pubrun` is not importable on the node —
`pip install -e .` into the venv the compute nodes share, if needed. To sample
several node types, submit repeatedly (each lands on a different random idle
node) or set `PUBRUN_PARTITION` per node class, then `aggregate.py` over all the
committed result JSONs.

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
  statistic is the **median** (plus p95 and stdev); the first iteration of each
  pass is a discarded warmup.
- The full sweep runs **twice by default** (`--passes 2`). Both passes are
  recorded under `pass_results` in the JSON so you can see whether startup /
  filesystem caching mattered (compare `pass 1` vs `pass 2`). The top-level
  `scenarios` key mirrors the **last (warmest) pass**, which `aggregate.py`/
  `plot.py` use.
- **Schema `pubrun-benchmark/3`** adds cross-machine context so results are
  comparable across systems and nodes:
  - `machine.filesystem` — the filesystem type of `$TMPDIR`, the results dir, and
    the `pubrun` install location (flags **network filesystems** like NFS/Lustre
    that can silently inflate I/O — the common HPC pitfall).
  - `machine.slurm` — Slurm allocation context (`job_id`, `cpus_per_task`,
    `partition`, `node`, …) when running under Slurm.
  - `pass_results[i].pass_env` — the dynamic host state (available RAM, load
    average, node iowait) captured at the **start of each pass**, so a node that
    got loaded between passes is visible rather than silently confounding results.
  Older `pubrun-benchmark/2` files remain readable by `aggregate.py`/`plot.py`.
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
