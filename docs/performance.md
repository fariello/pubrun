[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)

# Performance / Overhead

`pubrun` is designed to be cheap enough to leave enabled during real work. This
page reports the overhead it adds, measured by the reproducible harness under
[`benchmarks/`](../benchmarks/README.md). You can regenerate every number here
on your own machine.

## How overhead is measured

Each scenario launches a **fresh Python subprocess** N times (default 30, plus a
discarded warmup) and records the median wall-clock time. The whole sweep runs
**three times by default** (`--passes 3`, preceded by one uncaptured baseline
pass) and every pass is recorded, so startup/filesystem caching effects are
visible; the reported numbers use the last (warmest) pass. "Overhead" is the
median of a scenario minus its group baseline:

- **startup** — vs a bare `python noop.py` (no `pubrun` import).
- **feature** — vs `feature-baseline`; `feature-none` (pubrun active, everything
  off) isolates pubrun's fixed startup cost, so a single feature's *marginal*
  cost is its delta above `feature-none`.
- **hotpath**: explicit per-call paths vs their unwrapped builtin: file
  provenance through `pubrun.open()` and `pubrun.register_input()` at
  `[capture.file_io].level = "stat"` and `"hash"` vs `builtins.open()` (pubrun
  never patches `open()`), and the console tee vs plain `print()`.

See [`benchmarks/README.md`](../benchmarks/README.md) to run it:

```bash
python benchmarks/harness.py          # collect (stdlib only)
python benchmarks/aggregate.py benchmarks/results/*.json
```

### Result files (schema `pubrun-benchmark/5`)

Each run writes a **compact** (no-indent) JSON file. By default, `benchmarks/harness.py`
writes only the shareable, redacted copy:
`benchmarks/results/pubrun-bench-<hostname-hash>-<UTC-timestamp>.redacted.json` (the filename
embeds a non-identifying hostname hash, never the hostname; pass `--redacted-out <path>` to
override its path). The identifying local copy
(`benchmarks/results/<host>-<UTC-timestamp>.unredacted.json`) is written only when you pass
`--unredacted` or `--out <path>`. Neither `benchmarks/harness.py` default output,
`pubrun bench`, nor Slurm (`benchmarks/run_bench.sbatch`) ever writes a bare `*.json` (the
PBS/LSF/SGE template scripts `benchmarks/submit_bench_{pbs,lsf,sge}.sh` currently pass
`--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`, which writes a gitignored unredacted bare
`.json` file alongside the default `.redacted.json` file; see
[`benchmarks/README.md`](../benchmarks/README.md#running-on-an-hpc-cluster)).

Schema `/5` is a compact, non-redundant reshape of `/4` with **zero analytical data loss**:
static per-scenario descriptors live once in a top-level `scenario_defs` map; each pass keeps
only what varies (`timings`/`failures`/`skipped` maps keyed by scenario name); raw per-iteration
timings are retained (rounded to 6 decimal places — the one deliberate, sub-signal lossy step)
grouped by pass; and the derived stats (`median_s`/`p95_s`/`stdev_s`/…) are **not stored** but
recomputed on read from the raw timings. Both `generated_utc` and `generated_local` (local time
with UTC offset) are recorded. The redacted copy is written small enough to fit GitHub's ~65 KB
issue-body submission cap (a full default run is well under it); a non-fatal warning prints if it
ever exceeds the cap, suggesting you attach the file instead of pasting it. `aggregate.py` reads
both `/4` (stored stats) and `/5` (recomputed) files, producing identical output either way.

## Representative results

> **Placeholder.** The table below is a template. Representative numbers will be
> filled in once results have been collected and aggregated across several
> machines/OSes/Python versions (they vary by hardware, filesystem, and Python
> version, so single-machine figures are not published as representative). A
> sample single-machine result is committed under `benchmarks/results/` so the
> aggregation and plotting scripts have real input. Run the harness locally for
> numbers specific to your environment.

| Scenario | What it measures | Overhead (median) |
|---|---|---:|
| `import pubrun` (auto) startup | Import + auto-start + finalize vs bare Python | _TBD_ |
| `import pubrun.minimal` startup | API-only import cost | _TBD_ |
| pubrun active, all features off | Fixed run overhead (create dir, manifest write) | _TBD_ |
| + resource watcher (15s) | Background sampling thread | _TBD_ |
| + subprocess spy | `subprocess`/`os.system` interception | _TBD_ |
| + git capture | `git` metadata subprocess calls | _TBD_ |
| + hardware capture | CPU/RAM/GPU inspection | _TBD_ |
| packages `imported-only` | Scan `sys.modules` | _TBD_ |
| packages `full-environment` | Enumerate all distributions | _TBD_ |
| `pubrun.open()` read, `level = "stat"` (8 MiB) | Open-fd `fstat` provenance vs `builtins.open` | _TBD_ |
| `pubrun.open()` read, `level = "hash"`, streamed (8 MiB) | Hashing the bytes as they are read | _TBD_ |
| `pubrun.open()` read, `level = "hash"`, fallback (8 MiB) | Re-reading the file at close to hash it | _TBD_ |
| `register_input()`, `level = "stat"` / `"hash"` (8 MiB) | Registering a file a library read | _TBD_ |
| console tee (`capture_mode="standard"`) | Per-write tee/log tax | _TBD_ |

## Notes

- Console wrapping is **off by default** (`[console].capture_mode = "off"`), so
  the default `import pubrun` pays no per-write console tax unless you opt in.
- The background resource watcher samples on an interval
  (`[capture.resources].sample_interval_seconds`, default 15s); shorter
  intervals increase overhead and `events.jsonl` size.
- The heaviest optional capture is usually `packages = "full-environment"` and
  hardware/GPU inspection; both are configurable and can be reduced or disabled.

### Startup, finalization, and artifact durability overhead

The measurements below come from a single local machine and are scoped strictly to that environment rather than published as cross-machine representative numbers:

- **Machine and runtime:** `Linux 6.8.0-149-generic` (`x86_64`), Python `3.14.6`, `Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz` (12 logical cores), `pubrun 1.3.1`.
- **Storage:** Local `ext4` (`is_network = false` for `workdir`, `tmpdir`, and `pubrun_install`).
- **Revisions:** Pre-change baseline `d1ba84b55997d9d6cad99830570aadd9b8c41b00` versus post-change `e9e694ca62c67a0a49e4df8f6e14c53382f2d6ba`.
- **Method:** `python3 benchmarks/startup_breakdown.py --passes 3 --iterations 15 --warmup 1` (with `--durability-policies fsync,finalize,atomic,strict` post-change) and local non-publishing `python3 benchmarks/harness.py --passes 3 --iterations 15`. Workloads are short (`benchmarks/workloads/noop.py`, baseline `bare-python-noop`) and long (`benchmarks/workloads/cpu_burn.py`, baseline `bare-python-cpu-burn`). Pass 1 is cold and Pass 3 is warm.

#### Before and after comparison under default durability (`fsync`)

Default durability (`[core].artifact_durability = "fsync"`) preserves per-write file `os.fsync()` crash durability and is reported separately from opt-in durability policies.

| Scenario / Metric | Pre-change (`d1ba84b5`) Pass 1 / Pass 3 | Post-change (`e9e694ca`) Pass 1 / Pass 3 | Post-change Pass 3 Dispersion (mean / p95 / stdev / IQR ms) | Notes |
|---|---|---|---|---|
| `bare-python-noop` (short baseline) | 15.58 / 17.34 ms | 19.70 / 20.22 ms | 20.04 / 23.82 / 2.86 / 1.86 | Host baseline shifted +2.88 ms |
| `bare-python-cpu-burn` (long baseline) | 227.57 / 227.82 ms | 230.96 / 221.23 ms | 224.32 / 231.63 / 5.41 / 9.51 | CPU-bound workload floor |
| `import-minimal-installed` | 112.19 / 116.59 ms (`git`: 1) | 119.16 / 117.39 ms (`git`: 0) | 117.50 / 122.80 / 3.56 / 4.73 | Zero `git` spawns (checkout, installed, nested) |
| `import-noauto-installed` | 112.14 / 111.54 ms (`git`: 1) | 117.55 / 115.12 ms (`git`: 0) | 116.20 / 123.16 / 4.65 / 5.85 | Zero `git` spawns (checkout, installed, nested) |
| `auto-noop` (default `fsync`) | 495.17 / 490.10 ms (+479.59 / +472.77 ms; 3078% / 2727%) | 505.90 / 509.44 ms (+486.20 / +489.22 ms; 2468% / 2419%) | 510.86 / 528.04 / 11.99 / 13.71 | `git`: 6 to 4; `config` writes: 2 to 1; `fsync`: 4 to 3 |
| `auto-cpu-burn` (default `fsync`) | 707.40 / 705.09 ms (+479.83 / +477.26 ms; 210.8% / 209.5%) | 706.51 / 703.33 ms (+475.55 / +482.10 ms; 205.9% / 217.9%) | 706.52 / 734.50 / 14.66 / 11.47 | `git`: 6 to 4; `config` writes: 3 to 1; `fsync`: 6 to 4 |
| Phased `noop`: Import / Startup / Finalize | 84.27 / 350.32 / 21.61 ms (P1); 83.69 / 352.56 / 20.03 ms (P3) | 83.75 / 351.92 / 15.97 ms (P1); 85.93 / 352.14 / 15.10 ms (P3) | P3 IQR: 5.41 / 5.41 / 5.30 | Finalization median -24.6% (P3) |
| Phased `cpu_burn`: Import / Startup / Finalize | 82.62 / 351.37 / 15.09 ms (P1); 80.89 / 350.69 / 17.09 ms (P3) | 81.74 / 353.42 / 9.14 ms (P1); 81.58 / 356.42 / 8.92 ms (P3) | P3 IQR: 1.29 / 12.71 / 1.76 | Finalization median -47.8% (P3) |

Key observations on this Linux `ext4` host:

- **Structural reductions:** Import-only scenarios (`pubrun.minimal` and `pubrun.noauto`, across checkout, installed, and nested-repository layouts) dropped from `1` to `0` `git` spawns. Tracked checkout runs dropped from `6` to `4` `git` spawns (3 in `get_git()` via combined `rev-parse` plus 1 lazy `pubrun.__commit__` lookup; installed wheels run `3`). Unchanged `config.resolved.json` writes dropped from `2` (`noop`) and `3` (`cpu_burn`) to `1` (`1` startup, `0` refresh/finalization) across every policy. Default `fsync` calls dropped from `4` to `3` (`-25.0%`, `24.44 ms` to `16.14 ms`) on `auto-noop` and from `6` to `4` (`-33.3%`, `34.47 ms` to `26.60 ms`) on `auto-cpu-burn`.
- **Why local wall-clock totals stayed near baseline under default `fsync`:** Finalization dropped by `24.6%` (`noop`) and `47.8%` (`cpu_burn`), and `phased-noop-fsync` wall time dropped from `512.10 ms` to `489.91 ms`. End-to-end `auto-*` wall time remained near baseline because host `bare-python-noop` latency was `+2.88 ms` higher during the post-change run and parallel feature sets merged between `d1ba84b5` and `e9e694ca` (including startup-to-finalization package snapshot merging, per-engine failure isolation, monotonic timing, and file-registration re-exports across all six import modes). In the matching local `benchmarks/harness.py` run (`--passes 3 --iterations 15`), `startup-auto-default` had Pass 3 median `497.95 ms` (`477.26 ms` above `20.69 ms` `baseline-noop`), and `feature-packages-imported` (`+319.8 ms` above `feature-none`) remained the largest component of fixed startup cost (compared with `+3.6 ms` for `feature-git` and `+10.8 ms` for `feature-hardware`).

#### Durability policy comparison (post-change `e9e694ca`, Pass 1 cold / Pass 3 warm)

| Policy | Workload | Auto Median P1 / P3 (ms) | Abs Overhead P1 / P3 (ms) | Rel Overhead P1 / P3 (%) | Startup / Finalize P3 (ms) | `config` writes (S/F) | `fsync` total (S/F) & instrumented ms |
|---|---|---|---|---|---|---|---|
| `fsync` (default) | `noop.py` (short) | 505.90 / 509.44 | 486.20 / 489.22 | 2468.4% / 2419.1% | 352.14 / 15.10 | 1 (1/0) | 3 (2/1), 16.14 ms |
| `fsync` (default) | `cpu_burn.py` (long) | 706.51 / 703.33 | 475.55 / 482.10 | 205.9% / 217.9% | 356.42 / 8.92 | 1 (1/0) | 4 (3/1), 26.60 ms |
| `finalize` (opt-in) | `noop.py` (short) | 505.02 / 497.78 | 485.32 / 477.56 | 2463.9% / 2361.5% | 337.60 / 31.07 | 1 (1/0) | 2 (0/2), 11.26 ms |
| `finalize` (opt-in) | `cpu_burn.py` (long) | 691.42 / 685.52 | 460.46 / 464.30 | 199.4% / 209.9% | 339.64 / 15.09 | 1 (1/0) | 2 (0/2), 9.83 ms |
| `atomic` (opt-in) | `noop.py` (short) | 485.10 / 485.56 | 465.40 / 465.34 | 2362.8% / 2301.0% | 339.75 / 19.50 | 1 (1/0) | 0 (0/0), 0.00 ms |
| `atomic` (opt-in) | `cpu_burn.py` (long) | 678.17 / 670.08 | 447.21 / 448.85 | 193.6% / 202.9% | 339.74 / 4.11 | 1 (1/0) | 0 (0/0), 0.00 ms |
| `strict` (opt-in) | `noop.py` (short) | 524.74 / 526.30 | 505.04 / 506.08 | 2564.1% / 2502.5% | 358.31 / 24.68 | 1 (1/0) | 6 (4/2), 32.79 ms |
| `strict` (opt-in) | `cpu_burn.py` (long) | 710.70 / 704.12 | 479.75 / 482.89 | 207.7% / 218.3% | 360.96 / 15.70 | 1 (1/0) | 6 (4/2), 27.45 ms |

#### Durability trade-offs and local versus shared storage (NFS / Lustre)

All four `[core].artifact_durability` policies preserve atomic visibility through unique temporary files and `os.replace()`. The trade-off is strictly crash durability versus `fsync` latency:

- `"fsync"` (default) synchronizes each written snapshot file before replacement without synchronizing the parent directory.
- `"finalize"` avoids `fsync` during startup and hardware refresh while synchronizing finalized artifacts at run end (upgrading an unchanged startup `config.resolved.json` in place without rewriting it). On local `ext4`, this shifts `fsync` cost from startup (`~352 ms` to `~338 ms`) into finalization (`2` total `fsync` calls instead of `3` to `4`).
- `"atomic"` eliminates `os.fsync()` completely (`0` calls, `0.00 ms` sync time, cutting `cpu_burn` finalization to `4.11 ms` on this host) while keeping concurrent readers safe, at the cost of delegating disk flush timing to the operating system.
- `"strict"` adds best-effort Portable Operating System Interface (POSIX) parent-directory `os.fsync()` after `os.replace()`, doubling `fsync` calls (`6` to `8`) and adding `+15` to `+20 ms` on local `ext4`.

Local `ext4` measurements understate synchronization costs on shared cluster storage. On Network File System (NFS) or Lustre mounts, each `fsync` triggers synchronous network writeback and remote procedure call (RPC) round trips, so removing redundant `config.resolved.json` writes or opting into `"finalize"` or `"atomic"` saves substantially more wall-clock time than on local disk. To measure your own shared filesystem locally without external submission or scheduler jobs, pass `--workdir` to the breakdown script:

```bash
python3 benchmarks/startup_breakdown.py --workdir /path/to/shared/tmp --durability-policies fsync,finalize,atomic,strict
```

See [Configuration](configuration.md#artifact-durability-policy) for full platform durability limits (Linux `fsync(2)`, macOS `fsync(2)` versus `F_FULLFSYNC`, Windows `FlushFileBuffers`, and shared-filesystem directory sync fallback).

### Timing instrumentation and overhead separation

Every manifest splits a run into three back-to-back intervals measured with the monotonic clock `time.perf_counter()`: `startup_overhead_seconds` (pubrun's startup capture), `workload_seconds` (your code), and `finalization_overhead_seconds` (pubrun's teardown and `config.resolved.json` write, before `manifest.json` is written). See [Manifest Reference](manifest.md#timing). This subsection measures what that timing instrumentation itself costs and checks that pubrun's overhead stays out of `workload_seconds`. The numbers come from one local machine and are not representative results; `## Representative results` above remains a multi-machine placeholder.

- **Machine and runtime:** Operating System (OS) `Linux 6.8.0-149-generic` (`x86_64`), Central Processing Unit (CPU) `Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz` (12 logical cores), CPython `3.14.6`, `pubrun 1.3.1`. The host was shared and busy: the 1-minute load average was between about 9 and 11 during the measurements, so absolute numbers are noisier than on an idle machine.
- **Storage:** local `ext4` (`is_network = false`), detected with `pubrun.capture.filesystem.get_filesystem()` for the temporary work directory.
- **Git revision:** `af36c852546aafa843cf4838ff7071d7477cf439`.
- **Methods (local, non-publishing):**
  1. An in-process microbenchmark (not committed) that ran 3 passes of 30 repetitions per measurement; Pass 1 is cold and Pass 3 is warm. It timed (a) 100,000 `time.perf_counter()` calls against an empty loop of the same length; (b) 1,000 `with pubrun.phase(...)` blocks with an active run and with no run, against `contextlib.nullcontext()`; and (c) 30 `pubrun.start()` / `time.sleep(0.020)` / `pubrun.stop()` runs per pass (default profile), reading the finalized `timing` section and the in-memory `Run.writer_overhead_seconds`. Its temporary directory was removed afterwards. The microbenchmark was run three times; the table reports the last run, and the earlier runs differed by up to about 2x in some warm medians because of host load.
  2. `python3 benchmarks/harness.py --passes 3 --iterations 30 --redacted-out <temp_path>` (1 uncaptured baseline pass, then 3 measured passes of 30 iterations plus 1 discarded warmup per scenario; total wall time `946.4` s). The temporary result file was deleted after reading.

#### In-process timing cost (Pass 1 cold / Pass 3 warm)

Values are median / standard deviation (stdev) / interquartile range (IQR).

| Measurement | Pass 1 cold | Pass 3 warm | Unit |
|---|---|---|---|
| Empty loop baseline (100,000 iterations) | 2.261 / 0.778 / 1.666 | 2.063 / 0.059 / 0.053 | ms |
| `time.perf_counter()` loop (100,000 calls) | 10.559 / 3.170 / 4.525 | 8.721 / 0.202 / 0.181 | ms |
| Cost per `perf_counter()` call (loop minus baseline) | 82.5 / 25.4 / 40.8 | 66.6 / 2.0 / 1.8 | ns |
| `contextlib.nullcontext()` baseline (1,000 blocks) | 0.266 / 0.091 / 0.014 | 0.273 / 0.065 / 0.011 | ms |
| Active `pubrun.phase()` (1,000 phases, 2 events each) | 38.401 / 7.553 / 11.343 | 18.592 / 2.659 / 0.423 | ms |
| Active `pubrun.phase()` minus `nullcontext`, per phase | 38.14 / 7.53 / 11.33 | 18.32 / 2.66 / 0.44 | us |
| Inactive `pubrun.phase()` (no run), per phase, minus `nullcontext` | 108.35 / 16.47 / 14.29 | 105.91 / 27.12 / 10.97 | us |
| `startup_overhead_seconds` | 22.287 / 3.802 / 6.300 | 21.321 / 8.829 / 4.683 | ms |
| `workload_seconds` (`time.sleep(0.020)`) | 20.091 / 0.738 / 0.017 | 20.099 / 0.534 / 0.028 | ms |
| `finalization_overhead_seconds` | 2.832 / 0.618 / 0.312 | 2.811 / 0.911 / 0.871 | ms |
| `hardware_wait_seconds` (part of finalization) | 0.004 / 0.001 / 0.001 | 0.004 / 0.001 / 0.001 | ms |
| `background_hardware_seconds` (overlaps the workload) | 22.092 / 1.834 / 2.369 | 21.449 / 1.438 / 2.717 | ms |
| `session_seconds` | 45.554 / 4.013 / 6.092 | 45.129 / 8.803 / 5.100 | ms |
| `Run.writer_overhead_seconds` (in memory only; includes the `manifest.json` write) | 8.121 / 1.936 / 1.652 | 8.356 / 2.494 / 2.929 | ms |

#### Whole-process harness context (`af36c852`, Pass 1 cold / Pass 3 warm)

Values are median / stdev / IQR in milliseconds over 30 fresh processes.

| Scenario | Pass 1 cold | Pass 3 warm |
|---|---|---|
| `baseline-noop` | 17.42 / 2.18 / 2.52 | 19.15 / 2.01 / 3.55 |
| `import-minimal` | 131.35 / 23.69 / 24.95 | 127.87 / 6.04 / 7.41 |
| `import-auto` (all features off) | 180.62 / 18.87 / 22.40 | 161.92 / 8.71 / 13.35 |
| `startup-auto-default` | 554.11 / 55.61 / 46.92 | 528.14 / 17.82 / 21.78 |
| `feature-baseline` | 235.85 / 15.15 / 10.71 | 236.14 / 11.74 / 16.26 |
| `feature-none` | 382.23 / 11.83 / 14.95 | 369.95 / 33.39 / 21.38 |
| `feature-hardware` | 388.08 / 19.08 / 19.33 | 415.96 / 46.46 / 49.91 |
| `feature-packages-imported` | 713.94 / 26.79 / 31.61 | 749.90 / 38.33 / 54.29 |

What these measurements show on this machine:

- **The timing instrumentation itself is negligible.** A run takes a handful of `perf_counter()` readings, each about 67 ns warm, so the clock reads add well under a microsecond per run.
- **pubrun's overhead stays out of `workload_seconds`.** A `time.sleep(0.020)` workload measured `20.099` ms warm median (`20.091` ms cold), about 0.1 ms above the requested sleep, while pubrun's own startup (about 21 to 22 ms in process) and finalization (about 2.8 ms) were reported separately. The three disjoint intervals add up to `session_seconds`. **Historical exception at `af36c852` (fixed in commit `cb1b6d1`):** these `af36c852` runs wrote to a temporary directory where the background hardware refresh write took about 7 ms. At that revision, with the run directory on the repository disk, that refresh write (an `fsync`ed `manifest.json` rewrite, made while holding the run lock) took a median of 180 ms, and a `stop()` issued during it waited for the lock before recording `ended_at_utc`. For a 20 ms workload this added a median of 47.3 ms (stdev 36.1, IQR 40.0, maximum 185.9, n=30) to `workload_seconds`; for a 500 ms workload, which ended after the refresh, it added 0.03 ms. That exception has since been fixed in commit `cb1b6d1`: `src/pubrun/tracker.py::Run._finalize_state` now records `end_mono` and `end_utc` before acquiring `_run_lock`, so wait time for an in-flight background hardware refresh is attributed to `finalization_overhead_seconds` rather than `workload_seconds`.
- **Background hardware capture overlaps the workload.** `background_hardware_seconds` (about 21 to 22 ms) is close to the 20 ms workload because the two ran concurrently; adding it to `workload_seconds` would double-count. The finalization wait for it was about 4 us because it had already finished.
- **The `manifest.json` write is not in any persisted duration.** `Run.writer_overhead_seconds` (about 8 ms, held in memory only) is larger than `finalization_overhead_seconds` (about 2.8 ms) because it also covers building and atomically writing `manifest.json` and `methods.md`.
- **An active `pubrun.phase()` costs about 18 us warm** (38 us cold) per block, mostly writing the `phase_start` and `phase_end` events. A later measurement of the inactive-policy cache change (built on commit `7f8af7c`, CPython 3.14.6, Intel Core i7-6800K, same machine) put a `pubrun.phase()` with **no** active run at about 22 us per block and an active one at about 19 us per block, down from about 114 us inactive on the unchanged tree in the same session. The inactive path caches `[events].on_inactive_annotate` and resolves the configuration again only when the user or local configuration file, the working directory, or the user configuration directory changes.
- **In-process versus whole-process numbers differ.** The in-process `startup_overhead_seconds` (about 21 ms) excludes importing pubrun and reuses the installed-distribution index cached by earlier runs in the same process, so it is much smaller than the whole-process `feature-none` and `startup-auto-default` harness scenarios, which include interpreter start, import, and the first package scan.

Limits: one busy machine, local `ext4`, and one Python version only. Other OSes, Python 3.8 through 3.13, and network filesystems were not measured, and the earlier microbenchmark runs show that warm medians on this host varied by up to about 2x between runs.

## Capture-isolation startup and hot-path overhead (single-machine local measurements)

The measurements below come from one local machine and are scoped strictly to that environment; they are not cross-machine representative numbers (`## Representative results` above remains a multi-machine placeholder):

- **Machine and runtime:** Operating System (OS) `Linux 6.8.0-149-generic` (`x86_64`), Central Processing Unit (CPU) `Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz` (12 logical cores), Python `3.14.6`.
- **Storage:** Local `ext4` detected via `pubrun.capture.filesystem.get_filesystem()` (`is_network = false` for both `workdir` and `tmpdir`).
- **Git revisions:** Pre-isolation baseline `9703da77e41fb27fd19e8f0b081ac0fccdc0547f` versus post-isolation HEAD `114d243d1e82739172d45a4d842303f7281882c5`.
- **Workloads and repetitions:**
  1. Ephemeral Python micro-benchmark run against both revisions (baseline checked out in a temporary detached Git worktree that was removed after measurement), with 1 explicit cold pass plus 25 warm iterations per workload. `SubprocessSpy` micro-benchmarks monkeypatch `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` to no-op stubs before importing `pubrun.capture.subprocesses` so both import-time (`9703da77`) and install-time (`114d243d`) hooks measure pure Python wrapper overhead without OS fork jitter.
  2. Local non-publishing harness sweep (`python3 benchmarks/harness.py --passes 2 --iterations 20 --redacted-out <temp_path>`) on `114d243d` (1 uncaptured baseline pass, Pass 1 cold, Pass 2 warm, 20 measured iterations plus 1 discarded warmup per scenario; total wall time `303.579` s; temporary output deleted after reading).

### Micro-benchmark comparison (pre-isolation `9703da77` vs. post-isolation `114d243d`)

| Workload | Pre-isolation (`9703da77`) Cold / Warm Median (ms) | Pre-isolation IQR / Stdev (ms) | Post-isolation (`114d243d`) Cold / Warm Median (ms) | Post-isolation IQR / Stdev (ms) | Warm Median Delta |
|---|---:|---:|---:|---:|---:|
| `Run` start/stop (all-off, 1 run) | 46.427 / 47.739 | 8.278 / 6.055 | 31.479 / 34.871 | 3.962 / 4.199 | -12.868 ms (-26.95%) |
| `Run` start/stop (default, 1 run) | 200.246 / 93.500 | 16.926 / 15.714 | 427.441 / 62.941 | 10.906 / 6.390 | -30.559 ms (-32.68%) |
| `TqdmSafeTee.write` (plain, 10,000 lines) | 17.712 / 16.839 | 0.791 / 0.779 | 43.011 / 16.313 | 3.636 / 6.095 | -0.526 ms (-3.12%) |
| `TqdmSafeTee.write` (timestamped, 10,000 lines) | 77.323 / 61.099 | 4.265 / 4.005 | 94.460 / 60.504 | 0.398 / 3.050 | -0.595 ms (-0.97%) |
| `SubprocessSpy` bypassed (`disable_spy`, 10,000 stub triplets) | 15.654 / 13.944 | 0.310 / 0.849 | 50.934 / 19.150 | 2.940 / 7.896 | +5.206 ms (+37.34%) |
| `SubprocessSpy` active (recording, 2,000 stub triplets) | 79.770 / 48.003 | 0.666 / 2.193 | 68.957 / 55.973 | 2.105 / 2.403 | +7.969 ms (+16.60%) |
| `EventStream.emit` (buffered, 10,000 events) | 53.301 / 45.642 | 0.460 / 2.029 | 110.423 / 46.871 | 0.677 / 4.961 | +1.229 ms (+2.69%) |

### Local `benchmarks/harness.py` startup and hot-path summary (`114d243d`, 2 passes x 20 iterations)

| Scenario | Group | Pass 1 Cold Median (ms) | Pass 1 IQR / Stdev (ms) | Pass 2 Warm Median (ms) | Pass 2 IQR / Stdev (ms) |
|---|---|---:|---:|---:|---:|
| `baseline-noop` | `startup` | 20.58 | 2.23 / 1.42 | 19.70 | 2.19 / 1.79 |
| `import-auto` (all-off) | `startup` | 154.76 | 18.16 / 9.89 | 154.71 | 13.11 / 8.85 |
| `import-noauto` | `startup` | 116.53 | 3.74 / 4.19 | 119.01 | 5.04 / 2.95 |
| `import-nopatch` | `startup` | 121.71 | 4.43 / 4.92 | 120.60 | 7.90 / 9.73 |
| `import-noconsole` | `startup` | 121.44 | 13.12 / 8.70 | 124.44 | 5.73 / 4.29 |
| `import-minimal` | `startup` | 115.90 | 8.59 / 7.14 | 114.16 | 4.08 / 3.85 |
| `startup-auto-default` | `startup` | 505.22 | 14.41 / 12.26 | 503.69 | 11.79 / 9.86 |
| `feature-baseline` | `feature` | 227.00 | 8.53 / 6.98 | 223.44 | 6.59 / 7.74 |
| `feature-none` | `feature` | 358.57 | 19.55 / 12.26 | 347.53 | 11.89 / 8.52 |
| `feature-subprocesses` | `feature` | 357.64 | 7.36 / 8.90 | 353.44 | 10.10 / 6.05 |
| `hotpath-open-baseline` | `hotpath` | 49.60 | 4.65 / 2.73 | 46.56 | 6.31 / 3.29 |
| `hotpath-open-pubrun` | `hotpath` | 158.26 | 8.01 / 7.08 | 163.71 | 8.91 / 6.72 |
| `hotpath-print-baseline` | `hotpath` | 21.61 | 3.15 / 1.51 | 20.46 | 3.08 / 2.14 |
| `hotpath-print-tee` | `hotpath` | 218.32 | 11.90 / 8.33 | 212.01 | 10.06 / 10.58 |

Key takeaways from these local measurements:

- **Startup and finalization (`Run` start/stop):** Warm `Run` start/stop latency decreased between `9703da77` and `114d243d` (`-12.87 ms` all-off, `-30.56 ms` default) because sibling optimizations merged in the same window (config-write coalescing, synchronous `hardware.depth = "off"`, and cached package identity resolution) outweighed the per-engine `try/except` isolation guards. The higher cold `Run` default pass (`427.44 ms` versus `200.25 ms`) reflects one-time package-distribution index caching on the first run.
- **Console tee (`TqdmSafeTee.write`):** Warm medians over 10,000 lines stayed within host jitter (`-0.53 ms` plain, `-0.60 ms` timestamped, about `-0.05` to `-0.06` microseconds per line).
- **Subprocess spy (`SubprocessSpy`):** Generation-scoped closure checks (`state["active"]`), direct record tagging, and monotonic `time.perf_counter()` duration tracking added `+5.21 ms` across 10,000 bypassed stub triplets (`+0.52` microseconds per triplet, or `+0.17` microseconds per wrapper call) and `+7.97 ms` across 2,000 active stub triplets (`+3.98` microseconds per recorded triplet). Compared with real OS process spawn latency (milliseconds per process), this wrapper delta is negligible; in the full subprocess harness, `feature-subprocesses` measured `+5.91 ms` over `feature-none` on Pass 2 (`353.44 ms` versus `347.53 ms`).
- **Event stream (`EventStream.emit`):** Re-checking `self._file is None` inside `self._lock` and tracking failure state added `+1.23 ms` across 10,000 buffered events (`+0.12` microseconds per event).

## Package capture startup and finalization overhead (single-machine local measurements)

These numbers come from one local machine, measured on 2026-11-22. They are not cross-machine representative numbers; `## Representative results` above remains a multi-machine placeholder.

A tracked run pays for package capture twice when `[capture.packages].mode` is not `"off"`: once for the startup snapshot, and once at finalization for the refresh that records late imports and merges them with the startup snapshot. [`benchmarks/package_capture_bench.py`](../benchmarks/package_capture_bench.py) times the two separately by calling the same functions `Run` calls (`get_packages(cfg, stage="startup")`, then `get_packages(cfg, stage="final", include_transitive=...)` plus `merge_package_snapshots()`), so the figures below are package-capture time only, not whole-run wall time.

- **Machine and runtime:** Operating System (OS) `Linux 6.8.0-149-generic` (`x86_64`), Central Processing Unit (CPU) `Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz` (12 logical cores), CPython `3.14.6`.
- **Storage:** local storage only. The benchmark's temporary work directory was on `ext4` (`is_network = false`), detected through `pubrun.capture.filesystem.get_filesystem()`. No network or parallel filesystem was measured.
- **Git revision:** `ff2516476876`.
- **Command:** `python3 benchmarks/package_capture_bench.py --small-count 10 --large-count 300 --repetitions 10 --cold-runs 3` (total wall time about 16 s).
- **Workloads:**
  - `small`: 10 synthetic distributions run under `python -S`, so only they are installed; 1 module imported before the startup snapshot and 1 imported afterwards (a late import).
  - `large`: 300 synthetic distributions under `python -S`; 30 startup imports and 15 late imports. The synthetic metadata has `Requires-Dist` chains, PEP 508 markers, an optional extra, a parent-requested `pkg[extra]`, and import names that differ from distribution names.
  - `ambient`: the interpreter's real environment (215 installed distributions); no extra startup imports and 3 late standard-library imports.
- **Repetitions:** each cold sample is a fresh child process (empty distribution cache), 3 per mode. Warm samples are 10 passes in one child process after 1 discarded warmup pass, so the cached distribution index is reused. `mode = "off"` is the baseline; for `off`, finalization does no package work, matching `Run`.

Times are milliseconds, shown as median (interquartile range (IQR) / standard deviation). "Indexed distributions" is the size of the installed-distribution index the capture built; "Records" is the number of records in the merged snapshot.

`small` (10 synthetic distributions):

| Mode | Indexed distributions | Records | Startup cold | Startup warm | Finalization cold | Finalization warm | Finalization warm p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `off` | n/a | 0 | 0.00 (0.00 / 0.00) | 0.00 (0.00 / 0.00) | 0.00 (0.00 / 0.00) | 0.00 (0.00 / 0.00) | 0.00 |
| `imported-only` | 10 | 2 | 15.00 (0.07 / 0.08) | 2.32 (0.07 / 0.11) | 2.20 (0.02 / 0.02) | 2.34 (0.13 / 0.10) | 2.43 |
| `imported-transitive` | 10 | 10 | 15.75 (0.95 / 1.03) | 2.54 (0.07 / 0.14) | 2.54 (0.06 / 0.06) | 2.66 (0.18 / 0.12) | 2.70 |
| `top-level-installed` | 10 | 1 | 11.96 (0.04 / 0.04) | 0.09 (0.00 / 0.00) | 0.13 (0.00 / 0.00) | 0.11 (0.01 / 0.00) | 0.12 |
| `full-environment` | 10 | 10 | 13.87 (1.10 / 1.10) | 0.05 (0.00 / 0.00) | 0.10 (0.01 / 0.01) | 0.08 (0.00 / 0.00) | 0.09 |

`large` (300 synthetic distributions):

| Mode | Indexed distributions | Records | Startup cold | Startup warm | Finalization cold | Finalization warm | Finalization warm p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `off` | n/a | 0 | 0.00 (0.00 / 0.00) | 0.00 (0.00 / 0.00) | 0.00 (0.00 / 0.00) | 0.00 (0.00 / 0.00) | 0.00 |
| `imported-only` | 300 | 45 | 127.46 (4.70 / 4.79) | 2.51 (0.21 / 0.13) | 3.08 (0.68 / 0.73) | 2.98 (0.15 / 0.26) | 3.45 |
| `imported-transitive` | 300 | 150 | 124.31 (1.36 / 1.42) | 4.74 (0.41 / 0.20) | 5.03 (0.08 / 0.08) | 5.15 (0.35 / 0.36) | 5.73 |
| `top-level-installed` | 300 | 45 | 122.43 (1.79 / 1.83) | 1.58 (0.18 / 0.11) | 1.51 (0.14 / 0.16) | 1.68 (0.16 / 0.20) | 2.01 |
| `full-environment` | 300 | 300 | 119.74 (0.51 / 0.51) | 0.49 (0.01 / 0.00) | 0.93 (0.11 / 0.13) | 0.86 (0.01 / 0.04) | 0.93 |

`ambient` (215 installed distributions):

| Mode | Indexed distributions | Records | Startup cold | Startup warm | Finalization cold | Finalization warm | Finalization warm p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `off` | n/a | 0 | 0.00 (0.00 / 0.00) | 0.00 (0.00 / 0.00) | 0.00 (0.00 / 0.00) | 0.00 (0.00 / 0.00) | 0.00 |
| `imported-only` | 215 | 2 | 317.54 (1.48 / 1.55) | 0.99 (0.03 / 0.04) | 1.09 (0.03 / 0.04) | 1.04 (0.04 / 0.08) | 1.16 |
| `imported-transitive` | 215 | 2 | 321.36 (10.12 / 11.29) | 2.41 (0.22 / 0.15) | 2.79 (0.04 / 0.05) | 2.54 (0.09 / 0.13) | 2.80 |
| `top-level-installed` | 215 | 58 | 320.76 (1.50 / 1.54) | 2.92 (0.16 / 0.18) | 3.21 (0.09 / 0.09) | 3.09 (0.13 / 0.09) | 3.20 |
| `full-environment` | 215 | 215 | 323.64 (16.32 / 17.11) | 0.40 (0.02 / 0.02) | 0.71 (0.01 / 0.01) | 0.71 (0.32 / 0.44) | 1.77 |

What these measurements show on this machine:

- **The first startup snapshot in a process carries almost all of the cost.** It builds the installed-distribution index: about 12 to 16 ms for 10 synthetic distributions, about 120 to 127 ms for 300, and about 318 to 324 ms for the 215 real distributions in the ambient environment. The cost is similar across modes because every mode builds the same index. Why the real environment costs more per distribution than the synthetic one was not isolated.
- **The finalization refresh is cheap when the environment has not changed.** It reuses the index cached at startup, so cold finalization stayed at or below 5.03 ms median in every profile and mode, and warm finalization at or below 5.15 ms. `imported-transitive` on the 300-distribution profile was the most expensive refresh (5.15 ms warm median, 5.73 ms p95) because it recomputes the recursive closure over the merged imports.
- **`off` costs nothing measurable** at either stage, so each mode's delta over the baseline equals its own median.

Remaining overhead and limits:

- One machine, local `ext4` storage, and one Python version only. Behavior on other OSes, Python 3.8 through 3.13, and network filesystems was not measured.
- The index cache is keyed on a fingerprint of `sys.path` and the modification times of its directories. If either changes during a run (for example a package is installed mid-run), the finalization refresh rebuilds the index and should then cost about as much as the cold startup column; that case was not benchmarked.
- Synthetic distributions carry minimal metadata, so the `small` and `large` rows understate the per-distribution cost of real packages, as the `ambient` rows show.
- The ambient workload imports only standard-library modules late, so it does not exercise late third-party imports.
- These are package-capture function timings, not whole-run wall time. The standard harness (`benchmarks/harness.py`) measures whole runs through the `feature-packages-imported`, `feature-packages-transitive`, and `feature-packages-full` scenarios.

To measure a shared filesystem such as Network File System (NFS) or Lustre, pass a directory on it as `--workdir`, for example `python3 benchmarks/package_capture_bench.py --workdir /path/to/shared/scratch --json-out results.json`. The synthetic `site-packages` trees are then created and read on that filesystem (the `ambient` profile still reads the interpreter's own installation), the detected filesystem type is reported, and only a dedicated temporary subdirectory is created inside `--workdir` and removed on exit. The JSON output is written locally, has hostnames, usernames, and machine-local paths redacted, and is never uploaded; the script submits no scheduler jobs.

## File provenance: stat-only versus full hashing (single-machine local measurements)

These numbers come from one machine and are **not** representative results; the
multi-machine table above stays a placeholder. They show what each
`[capture.file_io].level` costs when reading one file, and how many extra bytes pubrun
reads to produce a digest.

How they were collected: `benchmarks/workloads/file_read.py --measure-detail` was run
once per fresh Python process for each mode, selected with `PUBRUN_BENCH_FILE_MODE`.
Each process writes an 8 MiB temporary file (8,388,608 bytes), reads it in 64 KiB
chunks inside a temporary `pubrun.tracked_run()`, reads the finalized manifest record,
and removes every temporary file and run directory. Sequence: one cold pass (the first
process for each mode), then 3 warm passes of 10 processes per mode (30 samples per
mode). The baseline reads with `builtins.open()` and never imports pubrun. Nothing was
uploaded or written under `benchmarks/results/`.

Environment: Linux 6.8 (x86_64), Intel Core i7-6800K (12 logical CPUs), CPython 3.14.6,
temporary directory on local `ext4` (file contents in the page cache), Git revision
`7164b15` plus uncommitted workload and documentation changes (no `src/pubrun/` changes).

Columns: **Read total** is the time from the first read to the end of close (or of the
registration call), which also includes the one-time lazy import of
`pubrun.capture.file_io` in that process. **Close/register** is the time spent in
`close()` for `pubrun.open()` modes, or in the `register_input()` call. Values are
milliseconds: warm median (interquartile range) and warm p95; cold is the single first
process. `extra_read_bytes` is the manifest's `hash_stats.extra_read_bytes`, confirmed
by the Linux `/proc/self/io` `rchar` delta (about 8.4 MB for one read, about 17.0 MB
when pubrun re-reads the file).

| Mode | Level | Read total, warm median (IQR) | Read total, warm p95 | Read total, cold | Close/register, warm median (IQR) | Close/register, warm p95 | `extra_read_bytes` | `hash_status` / `observation_time` |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `baseline` (`builtins.open`) | n/a | 1.51 (0.43) | 2.07 | 1.46 | n/a | n/a | 0 | n/a |
| `open-stat` | `stat` | 3.36 (2.29) | 7.43 | 27.07 | 0.11 (0.04) | 0.22 | 0 | `disabled` / `at_close` |
| `open-hash-stream` | `hash` | 24.86 (1.37) | 31.65 | 24.11 | 0.15 (0.02) | 0.20 | 0 | `completed` / `during_stream` |
| `open-hash-fallback` | `hash` | 26.78 (2.76) | 33.66 | 27.64 | 22.59 (2.89) | 29.85 | 8,388,608 | `completed` / `at_close` |
| `register-stat` | `stat` | 3.61 (2.78) | 8.56 | 2.71 | 1.08 (0.36) | 4.22 | 0 | `disabled` / `at_registration` |
| `register-hash` | `hash` | 26.37 (2.86) | 42.84 | 26.39 | 23.98 (2.58) | 40.45 | 8,388,608 | `completed` / `at_registration` |

What these measurements show on this machine:

- **`stat` reads no file content.** Its close cost was about 0.1 ms and its
  `register_input()` cost about 1 ms (which includes the first-call module import),
  with zero extra bytes read.
- **Hashing costs about 23 ms per 8 MiB here, whichever path computes it.** SHA-256
  throughput, not I/O, dominates while the file is in the page cache.
- **A streamed digest moves the cost into the reads and adds no I/O.** `open-hash-stream`
  closed in about 0.15 ms and read zero extra bytes. The fallback and `register_input()`
  at `hash` re-read the whole file (8,388,608 extra bytes), which roughly doubles the
  bytes read.
- The `open-stat` cold value (27 ms) includes first-time costs in that process that
  were not isolated; the warm passes did not repeat it.

Limits: one machine, one Python version, a page-cached local `ext4` file, and one file
size. On a cold cache or a network filesystem such as NFS or Lustre the extra re-read
of the fallback and of `register_input()` at `hash` costs real I/O, which these numbers
do not show. To reproduce, run
`PUBRUN_BENCH_FILE_MODE=<mode> python3 benchmarks/workloads/file_read.py --measure-detail`
for each mode, or the `hotpath-open-*` and `hotpath-register-*` scenarios of
`benchmarks/harness.py`, which report whole-process overhead against
`hotpath-open-baseline`.

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
