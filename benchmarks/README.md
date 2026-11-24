# pubrun benchmarks

A reproducible harness for measuring the startup and run-time overhead `pubrun`
adds to a host process, so overhead claims can be verified and aggregated across
machines.

## Design

- **`harness.py`** — stdlib-only measurement core. Runs each scenario in a fresh
  subprocess N times and writes one JSON result (timings + machine metadata).
  Runs anywhere `pubrun` runs, including locked-down HPC nodes. No third-party
  imports.
- **`startup_breakdown.py`** - stdlib-only, local, non-publishing startup and
  finalization breakdown benchmark. Separates import, startup capture, workload,
  and finalization timings, compares source-checkout against isolated installed
  and nested-repository layouts, and counts Git subprocess spawns, manifest and
  config atomic writes, `os.fsync` calls, and writer JSON serialization time.
- **`package_capture_bench.py`** - local, non-publishing package-capture
  benchmark that uses only the Python standard library. It times the startup
  package snapshot and the finalization refresh separately across all five
  package-capture modes, using two synthetic profiles and the ambient (real)
  interpreter profile.
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
python benchmarks/harness.py --quick     # baseline + 2 passes x 15 iterations
python benchmarks/harness.py             # default: baseline + 3 passes x 30 iterations
python benchmarks/harness.py --rigorous  # baseline + 5 passes x 50 iterations (long)
python benchmarks/harness.py --iterations 1 --passes 1   # tiny custom run
python benchmarks/harness.py --no-baseline               # skip the baseline pass
```

Each run writes `results/<hostname>-<UTC-timestamp>.unredacted.json` (the full result;
add `--redacted-out <path>` to also write a shareable, redacted copy). Files are written
**compact** (no indentation): the redacted copy must fit GitHub's ~65 KB issue-body cap, and
the local copy uses the same form (it parses identically). The timestamp in the filename is
UTC; the JSON also records `generated_utc` and `generated_local` (local time with its offset).

The result format is `pubrun-benchmark/5`, defined by a machine-readable JSON Schema at
[`schemas/benchmark.schema.json`](../schemas/benchmark.schema.json). Both the full and the
redacted forms validate against it (redaction masks string values but never changes the
structure); a conformance test in `benchmarks/test_benchmarks.py` enforces this.

Aggregate one or many machines' results:

```bash
python benchmarks/aggregate.py benchmarks/results/*.json
# -> benchmarks/results/summary.csv and summary.md
# (matches both *.unredacted.json and *.redacted.json; mixed /4 and /5 files aggregate together)
```

Optional figures and the micro-benchmark suite (needs the extra):

```bash
pip install -e .[bench]
python benchmarks/plot.py benchmarks/results/summary.csv
pytest benchmarks/ --benchmark-only
```

### Startup and finalization breakdown

Use `benchmarks/startup_breakdown.py` to measure fixed startup and finalization
overhead in detail before and after performance changes. The script uses Python
standard library modules only (compatible with Python 3.8 through 3.14). It is
strictly local and non-publishing: it never invokes GitHub CLI (`gh`), Gist
APIs, `git push`, or batch schedulers (`sbatch`, `qsub`, `bsub`).

```bash
python benchmarks/startup_breakdown.py
python benchmarks/startup_breakdown.py --passes 3 --iterations 15 --warmup 1
python benchmarks/startup_breakdown.py --workdir /path/to/shared/tmp --out /tmp/breakdown.redacted.json
python benchmarks/startup_breakdown.py --durability-policies fsync,finalize,atomic,strict
```

CLI flags:

- `--iterations`: measured iterations per scenario per pass (integer >= 1, default `15`).
- `--passes`: measured passes from Pass 1 (cold) through Pass N (warm) (integer >= 1, default `3`).
- `--warmup`: discarded warmup iterations before each pass (integer >= 0, default `1`).
- `--workdir`: optional parent directory for ephemeral benchmark files. Pass a path on a
  shared filesystem (such as Network File System (NFS) or Lustre) to compare shared storage
  against local storage. The script creates and deletes only a dedicated ephemeral
  subdirectory inside `--workdir`, leaving `--workdir` and pre-existing sibling files intact.
- `--durability-policies`: comma-separated subset of `default,fsync,finalize,atomic,strict`
  (default `default`). `default` measures built-in defaults without writing `.pubrun.toml`;
  explicit policies write `[core].artifact_durability` into each temporary scenario directory.
- `--out`: optional path for the redacted JSON report (`pubrun-startup-breakdown/1`). Standard
  output always prints a concise redacted Markdown summary.

What it measures and reports:

- **Isolated layouts:** compares `pubrun.minimal` and `pubrun.noauto` across a source checkout
  (`checkout`), an isolated installed package outside any Git tree (`installed`), and an
  installed package inside a nested user Git repository (`installed-nested`).
- **Phase separation and clean timing:** runs uninstrumented child processes for wall-clock
  timings (`bare-python-noop`, `bare-python-cpu-burn`, `auto-noop-*`, `auto-cpu-burn-*`, and
  phased `import` / `startup` / `workload` / `finalization` probes) so instrumentation never
  distorts wall-clock measurements.
- **Counters and serialization:** runs dedicated instrumented probes outside timed samples to
  count `git` subprocess spawns, `manifest.json` and `config.resolved.json` atomic writes,
  startup and finalization `os.fsync` calls, and `pubrun.writer` JSON serialization time.
- **Cold versus warm passes and dispersion:** records Pass 1 (cold) through Pass N (warm) with
  sample count (`n`), `failures`, `median_ms`, `mean_ms`, 95th percentile (`p95_ms`), standard
  deviation (`stdev_ms`), and Interquartile Range (`iqr_ms`), alongside absolute overhead (ms)
  and relative overhead (%) for short (`noop.py`) and long (`cpu_burn.py`) workloads.
- **Redaction and share-safety:** omits raw paths and mount points, scrubs hostname, username,
  home directory, `--workdir`, and repository root substrings, and validates output with
  `benchmarks/share_safety.py::check_share_safe` before writing or printing.

### Package capture benchmark

Use `benchmarks/package_capture_bench.py` to time `pubrun` package capture at
run startup and at finalization separately. The script uses only the Python
standard library and is local and non-publishing: it uploads nothing and submits
no batch scheduler job. When you pass `--json-out`, the script writes a redacted
JSON result file locally.

```bash
python benchmarks/package_capture_bench.py
python benchmarks/package_capture_bench.py --small-count 10 --large-count 300 \
  --repetitions 10 --cold-runs 3
python benchmarks/package_capture_bench.py --workdir /path/to/shared/scratch \
  --json-out /tmp/package-capture.json
```

CLI flags:

- `--small-count`: synthetic distributions in the `small` profile (integer >= 1,
  default `10`).
- `--large-count`: synthetic distributions in the `large` profile (integer >= 1,
  default `300`).
- `--repetitions`: warm measured passes per profile and mode (integer >= 1,
  default `10`).
- `--cold-runs`: fresh-process cold runs per profile and mode (integer >= 1,
  default `3`).
- `--workdir`: optional parent directory for the synthetic environments, for
  example a shared Network File System (NFS) or Lustre scratch path. The script
  creates only a dedicated temporary subdirectory inside `--workdir` and removes
  it on exit.
- `--json-out`: optional local path for the redacted JSON result (never
  published). Standard output always prints a redacted Markdown summary.

Passing a value below `1` for `--small-count`, `--large-count`, `--repetitions`,
or `--cold-runs` prints an error to standard error and exits with status `2`.

What it measures and reports:

- **Two timing points:** measures `startup` (the initial package snapshot) and
  `finalization` (the final package refresh plus its merge with the startup
  snapshot, matching `Run`) separately.
- **Five capture modes:** runs `off`, `imported-only`, `imported-transitive`,
  `top-level-installed`, and `full-environment`. The `off` mode is the baseline
  used to compute each mode's `delta_vs_off_ms` values.
- **Three environment profiles:** runs `small` and `large` (synthetic
  `site-packages` trees executed under `python -S` so only the synthetic
  distributions are installed) and `ambient` (the running interpreter's real
  installed packages).
- **Cold versus warm sampling:** cold samples run one fresh child process per
  run with an empty distribution cache. Warm samples run one child process per
  profile and mode, execute one discarded warmup pass, and then repeat measured
  passes that reuse the distribution cache.
- **Result format:** writes schema `pubrun-package-capture-bench/1`, which is
  not the `pubrun-benchmark/5` format and is not read by `aggregate.py`.
- **Redaction, share-safety, and exit status:** redacts hostname, username, and
  machine-local paths (including `--workdir`) and validates the result with a
  share-safety check before printing or writing any output. If that check fails,
  the script refuses to emit output and exits with status `1`. The script also
  exits with status `1` when any sample fails.

See the
[performance documentation](../docs/performance.md#package-capture-startup-and-finalization-overhead-single-machine-local-measurements)
for single-machine local measurements collected with this script.

## Running on an HPC cluster

The easiest way is `pubrun bench`, which auto-detects the batch scheduler (**Slurm,
PBS/Torque, LSF, or SGE/Grid Engine**) and offers to submit to a compute node.

For direct use, per-scheduler submit scripts live here:

- `submit_bench.sh` + `run_bench.sbatch` — **Slurm**. Picks a **random idle CPU node**
  (via `sinfo`) and submits to it; falls back to an unpinned submit if none are idle.
  Each job writes a node-tagged result to `benchmarks/results/<node>-<timestamp>.json`.
- `submit_bench_pbs.sh` — **PBS/Torque/OpenPBS** (`qsub`).
- `submit_bench_lsf.sh` — **LSF** (`bsub`).
- `submit_bench_sge.sh` — **SGE / Grid Engine** (`qsub`).

The PBS/LSF/SGE scripts submit to the default queue and let the scheduler place the job (no
site-specific idle-node query). They are **starting points** — real clusters usually need an
account/allocation and often a queue/walltime, set via env knobs (`PUBRUN_QUEUE`,
`PUBRUN_ACCOUNT`/`PUBRUN_PROJECT`, `PUBRUN_PE`) or by editing the directives. Only the Slurm
path is exercised in CI; the others are provided as adaptable templates. Note: PBS and SGE
both use `qsub` — if `pubrun bench` cannot tell them apart, pass `--scheduler pbs|sge`.

### Slurm details

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

By default `pubrun bench` writes only a redacted, share-safe file under `results/`:

- `pubrun-bench-<hash>-<UTC-timestamp>.redacted.json`: a **redacted** copy safe to share
  publicly. The filename embeds a stable, non-identifying hostname hash (never the hostname
  itself, matching the in-file hostname redaction). Inside, hostname, OS username, and every
  home-directory path are masked, while the analysis-relevant data (CPU/GPU model, core count,
  raw timings, versions, filesystem type, Slurm partition) is preserved.
- Pass `--unredacted` if you also want `<host>-<UTC-timestamp>.unredacted.json` (the full,
  identifying result for your own local analysis; do not share). Never a bare `*.json`.

After a run, `pubrun bench` runs the structural share-safety validator
(`benchmarks/share_safety.py`) and, on an interactive terminal, **offers to contribute** the
redacted result to `fariello/pubrun` (press Enter to accept, or pass `--contribute` /
`--no-contribute` to pre-decide). It uses the GitHub CLI (`gh`): it creates an unlisted Gist of
the redacted file and opens a GitHub issue linking it, falling back to embedding the JSON inline
when under GitHub's ~65 KB body cap, and finally to the browser Issue Form when `gh` is
unavailable.

If you decline, or if a Slurm wait is interrupted, submit later without re-running:

```bash
pubrun bench --submit-file results/pubrun-bench-<hash>-<timestamp>.redacted.json
```

Prefer to attach manually in a browser? Run `pubrun bench --prepare-submission` to copy only
the redacted file into a clean `pubrun-share/` folder, then attach it to the Issue Form at
<https://github.com/fariello/pubrun/issues/new?template=benchmark-result.yml>. A validate-only
GitHub Action checks the submission as data only and posts a pass/fail receipt; maintainers
collect accepted results locally into `benchmarks/data/` via `benchmarks/pull_submissions.py`
(see `benchmarks/data/README.md`).

**Privacy caveat (honest):** even redacted, a distinctive CPU/GPU model plus a
named Slurm partition can be re-identifying in a small group. Share only what you
are comfortable making public.

Advanced / manual:

- `python benchmarks/harness.py --redacted-out results/shareable.redacted.json` runs the
  harness directly and writes a compact redacted copy.
- `python benchmarks/pull_submissions.py` (dry-run; `--apply` to store/aggregate/re-tag)
  collects validated community submissions locally into `benchmarks/data/`.
- Re-run `aggregate.py` over results and, if helpful, `plot.py`.

## Interpreting the numbers

- Timings are **wall-clock**, measured by launching a fresh Python subprocess
  per iteration (so import/startup cost is real, not warm-cached). The reported
  statistic is the **median** (plus p95 and stdev); the first iteration of each
  pass is a discarded warmup.
- Every run starts with **one uncaptured baseline pass** (pubrun absent) that warms
  caches and records the cost floor. It is stored separately under `result["baseline"]`
  (with `uncaptured: true`) and is NEVER mixed into the pubrun-overhead stats.
- The measured sweep then runs **N times** per the tier (`--quick` = 2, default = 3,
  `--rigorous` = 5; `--passes` overrides). All measured passes are recorded under
  `pass_results` so you can see whether startup / filesystem caching mattered (compare
  `pass 1` vs `pass N`). `aggregate.py`/`plot.py` use the **last (warmest) pass**.
- `result["total_wall_time_s"]` is the whole-invocation wall time (harness start → end),
  distinct from the summed per-iteration timings. `result["mode"]` records the tier
  (`quick`/`default`/`rigorous`/`custom`).
- **Schema `pubrun-benchmark/5`** is a compact, non-redundant reshape of `/4` that keeps
  every raw timing while fitting the shared file under GitHub's issue-body cap:
  - **Static scenario descriptors are defined once**, in a top-level `scenario_defs` map
    (`{name: {group, mode, workload, config}}`). Passes reference scenarios by name and no
    longer repeat these descriptors. (There is **no** top-level `scenarios` key anymore — the
    old schema/1 last-pass alias was removed; readers use `scenario_defs` + per-pass timings.)
  - **Raw timings are grouped per pass**: each `pass_results[i]` carries only what *varies* —
    `pass`, `pass_env`, a `timings` map (`{name: [raw wall times in run order]}`), a
    `failures` map (`{name: int}`), and (if any) a `skipped` map (`{name: reason}`). Timings
    are stored rounded to **6 decimal places** (microsecond-ish; ample for wall-clock) — the
    one lossy step, and a deliberate one: it is the decisive size lever and far finer than any
    real signal. Every raw sample is retained, so you can still compute any statistic, inspect
    distribution shape, and **pool correctly across submissions** (you cannot average medians).
  - **Derived stats are NOT stored** (`n`/`min_s`/`median_s`/`mean_s`/`p95_s`/`max_s`/
    `stdev_s`). They are fully recomputable from the raw timings, so dropping them loses no
    analytical data; `aggregate.py` recomputes them from the last pass's timings.
  - The `baseline` block uses the **same compact shape** (`timings`/`failures`/`skipped` maps,
    no per-scenario descriptors, no stored stats).
  - Two timestamps are recorded: `generated_utc` (canonical) and `generated_local` (local ISO
    time **with** its UTC offset). The filename timestamp stays UTC.
  - `machine.python` gains non-identifying `environment_kind` (venv/conda/system/…),
    `in_venv`, and `sys_path_len` — these **survive share-redaction**, so a result
    stays interpretable after PII masking.
  - `machine.filesystem` — the filesystem type of `$TMPDIR`, the results dir, the
    `pubrun` install, the **Python install prefix**, `/dev/shm`, and the I/O-baseline
    target (flags **network filesystems** like NFS/Lustre that silently inflate I/O).
    On `pubrun bench` (a diagnostic context) each entry also gets a `live` sub-dict
    with capacity/inode/read-only data and a **hung/slow** status from a background
    `statvfs` probe.
  - `machine.slurm` — Slurm allocation context (`job_id`, `cpus_per_task`,
    `partition`, `node`, …) when running under Slurm.
  - `pass_results[i].pass_env` — the dynamic host state (available RAM, load
    average, node iowait) captured at the **start of each pass**, so a node that
    got loaded between passes is visible rather than silently confounding results.
  Older `pubrun-benchmark/2`/`3`/`4` files remain readable by `aggregate.py`/`plot.py`
  (version-gated: `/4` and earlier use their stored stats; `/5` recomputes from timings —
  the aggregate output is identical either way).
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
