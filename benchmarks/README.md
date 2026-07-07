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

The easy way (from a source checkout):

```bash
pip install -e .
python -m pubrun bench            # runs locally; on an HPC login node, offers to submit to Slurm
```

`pubrun bench` writes two files under `results/`:

- `<host>-<timestamp>.json` — the **full** result, for your own analysis.
- `<host>-<timestamp>.redacted.json` — a **redacted** copy safe to share publicly:
  hostname, OS username, and every home-directory path are masked, while the
  analysis-relevant data (CPU/GPU model, core count, timings, versions, filesystem
  type, Slurm partition) is preserved.

After a local run, `pubrun bench` **offers to contribute** the redacted result for
you (`Contribute this redacted result…? [y/N]` — Enter never transmits). If you say
yes, it tries the GitHub CLI (`gh`) → the GitHub Issues API → printing a
ready-to-paste submission, in that order. Every automated path files a **GitHub
issue**, so it needs a GitHub account (GitHub has no anonymous-issue mechanism);
opening it from your own account lets us follow up without any personal data in the
file. Fully anonymous submission (a throwaway account, or a manual paste) is fine too.

If you decline, submit later without re-running:

```bash
pubrun bench --submit-file results/<host>-<timestamp>.redacted.json
```

This is also the HPC path: run on a compute node, then submit the redacted file from
a login node. pubrun **never auto-transmits an un-redacted result** — the submit path
verifies the file looks redacted and refuses otherwise. You can always submit fully
manually instead: attach the redacted file to a new issue at
<https://github.com/fariello/pubrun-benchmarks/issues/new>.

**Privacy caveat (honest):** even redacted, a distinctive CPU/GPU model plus a
named Slurm partition can be re-identifying in a small group. Share only what you
are comfortable making public.

Advanced / manual:

- `python benchmarks/harness.py --redacted-out results/shareable.json` runs the
  harness directly and also writes a redacted copy.
- Re-run `aggregate.py` over all results and, if helpful, `plot.py`.

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
  - `io_baseline` scenarios are **ground-truth reference floors** (not overhead pairs):
    `io-baseline-devnull` (write-only sink — isolates the open()/write path from any
    storage), `io-baseline-devshm` (RAM-backed tmpfs, Linux; skipped where `/dev/shm` is
    unavailable), and `io-baseline-tmpdir` (the default temp filesystem). Comparing these
    tells you how much of a run's I/O time is storage vs. the write path itself, and lets
    the storage-dependent `hotpath-open` numbers be interpreted against a known floor.
- Numbers vary by machine, filesystem, and Python version; that is why results
  carry full machine metadata and are aggregated across systems before any
  representative figure is published.
