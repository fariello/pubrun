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
- **hotpath** — the patched `open()`/`print()` path vs the unpatched builtin.

See [`benchmarks/README.md`](../benchmarks/README.md) to run it:

```bash
python benchmarks/harness.py          # collect (stdlib only)
python benchmarks/aggregate.py benchmarks/results/*.json
```

### Result files (schema `pubrun-benchmark/5`)

Each run writes a **compact** (no-indent) JSON. The full local copy is
`<host>-<UTC-timestamp>.unredacted.json`; a shareable, redacted copy is
`pubrun-bench-<hostname-hash>-<UTC-timestamp>.redacted.json` (the filename embeds a
non-identifying hostname hash, never the hostname). Neither is ever a bare `*.json`.

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
| patched `open()` read (8 MiB) | Per-byte hashing tax vs `builtins.open` | _TBD_ |
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
- **Revisions:** Pre-change baseline `d1ba84b55997d9d6cad99830570aadd9b8c41b00` (`fthyv5`) versus post-change `e9e694ca62c67a0a49e4df8f6e14c53382f2d6ba` (`ckc3vl`).
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

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
