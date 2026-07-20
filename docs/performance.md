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

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
