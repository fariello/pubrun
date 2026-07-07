[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)

# Performance / Overhead

`pubrun` is designed to be cheap enough to leave enabled during real work. This
page reports the overhead it adds, measured by the reproducible harness under
[`benchmarks/`](../benchmarks/README.md). You can regenerate every number here
on your own machine.

## How overhead is measured

Each scenario launches a **fresh Python subprocess** N times (default 30, plus a
discarded warmup) and records the median wall-clock time. The whole sweep runs
twice by default (`--passes 2`) and both passes are recorded, so
startup/filesystem caching effects are visible; the reported numbers use the
last (warmest) pass. "Overhead" is the median of a scenario minus its group
baseline:

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
