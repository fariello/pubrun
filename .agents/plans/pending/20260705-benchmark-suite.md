# IPD: Performance/overhead benchmark suite

- Date: 2026-07-05
- Concern: performance measurement / reproducible benchmarking (net-new tooling)
- Scope: new `benchmarks/` tree in the public repo; a `[bench]` optional-dependency
  extra; no change to `src/pubrun/` runtime behavior.
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

Produce a **publishable, multi-system benchmark harness** that quantifies the startup
and run-time overhead pubrun adds to a host process, per feature, so we can (a) document
honest overhead numbers in the docs and (b) collect results across many machines to
support a JOSS paper. Results must be machine-readable (JSON + CSV), reproducible by a
third party, and portable enough to run on locked-down HPC nodes.

Design decisions already made with the maintainer:
- **Dependencies:** the *measurement/collection core is stdlib-only* (portable
  everywhere pubrun runs). Richer stats + figures use **pytest-benchmark** and
  **matplotlib**, gated behind a new **`[bench]` optional-dependency extra** so they
  never touch the runtime install. (Maintainer chose "allow pytest-benchmark /
  matplotlib, dev-only extra".)
- **Location:** harness **and** collected result JSONs live in the **public repo under
  `benchmarks/`** (reproducibility is a JOSS plus). (Maintainer chose "in the public
  repo under benchmarks/".)

## Project conventions discovered (Step 0)

- Guiding principles: `README.md`/`AGENTS.md` — zero *runtime* deps (tomli only <3.11),
  KISS, honest docs, never crash the host. A benchmark harness is separate tooling, so
  the `[bench]` extra is consistent (it is not a runtime dependency).
- Build: hatchling; extras under `[project.optional-dependencies]` (`dev`, `tui`
  exist). Add `bench` alongside.
- Plans: `.agents/plans/pending/` → `executed/`, `YYYYMMDD-<slug>.md`.
- Venv: `~/venv/p3.14/bin/python`.
- pubrun already captures machine metadata (CPU model, cores, RAM, OS, Python version)
  in its manifest — the harness should reuse that capture rather than re-implement it.

## What to measure (matched to pubrun's actual features)

1. **Import / startup overhead** — wall time of `python -c "pass"` (baseline) vs each
   import mode: `import pubrun` (auto), `import pubrun.noauto`, `import pubrun.nopatch`,
   `import pubrun.quiet`/`noconsole`, `import pubrun.minimal`. Isolate: background
   hardware thread on/off, startup-manifest write.
2. **Per-feature run-time deltas** (each toggled independently, everything else off):
   - console tee: `capture_mode` off / basic / standard
   - subprocess spy: `[capture.subprocesses].enabled` true/false
   - resource watcher: `sample_interval_seconds` sweep (e.g. 0.1/1/15) and
     `scope` process vs tree
   - packages: `imported-only` vs `imported-transitive` vs `full-environment`
   - git: `check_dirty` on/off; hardware depth off/basic
   - profiling: off vs cProfile (within a phase)
3. **Hot-path taxes** — throughput with pubrun active vs baseline:
   - patched `open()` read hashing: MB/s on a large temp file (e.g. 100 MB), read vs
     baseline `builtins.open`
   - `pubrun.print()` calls/sec vs builtin `print`
   - `pubrun.subprocess.run` overhead per call vs `subprocess.run`
4. **Shutdown/finalize cost** — manifest build + write, hash recompute, event flush.

## Proposed changes (ordered, validatable)

| Step | Change | Files | Remediation Risk | Validation |
|------|--------|-------|------------------|------------|
| 1 | Add the `bench` extra: `pytest-benchmark`, `matplotlib` (and `numpy` only if matplotlib needs it transitively — do not add otherwise). Keep it OUT of `dev`. | `pyproject.toml` | Low | `pip install -e .[bench]` resolves; `pip install -e .` still installs zero runtime deps. |
| 2 | Create `benchmarks/harness.py`: a **stdlib-only** measurement core. Runs each scenario in a **fresh subprocess** (so import cost is real, not warm), N iterations (default 20, configurable), records min/median/p95/mean/stdev of wall time via `time.perf_counter`, plus the scenario's config. Emits one JSON per (machine × run). Never imports matplotlib/pytest-benchmark. | `benchmarks/harness.py` | Low–Medium (complexity: keep scenario list declarative) | `python benchmarks/harness.py --quick` runs in <60s and writes a JSON. |
| 3 | Define scenarios declaratively in `benchmarks/scenarios.py` (name, import mode, config overrides, workload). Workloads are tiny scripts under `benchmarks/workloads/` (e.g. `noop.py`, `cpu_burn.py`, `file_read.py`, `subprocess_spawn.py`, `print_loop.py`). | `benchmarks/scenarios.py`, `benchmarks/workloads/*.py` | Low | Each workload runs standalone; harness enumerates all scenarios. |
| 4 | Capture machine metadata into each result JSON by reusing pubrun's own hardware/host/python capture (`from pubrun.capture import ...`) — do not re-implement. Include pubrun version, git commit, timestamp, iteration count. | `benchmarks/harness.py` | Low | JSON contains a `machine` block with CPU model, cores, RAM, OS, Python, pubrun version. |
| 5 | `benchmarks/aggregate.py`: merge many result JSONs (`benchmarks/results/*.json`) into one tidy CSV + a summary table (Markdown) — overhead per feature, per machine. Stdlib-only. | `benchmarks/aggregate.py` | Low | Given 2 sample JSONs, produces a CSV and a Markdown table. |
| 6 | `benchmarks/plot.py`: OPTIONAL matplotlib figures from the aggregated CSV (bar charts of overhead per feature; startup-mode comparison). Imported lazily; prints a clear "install .[bench]" message if matplotlib is missing. Never required to collect data. | `benchmarks/plot.py` | Low | With `[bench]` installed, produces PNGs; without it, exits cleanly with guidance. |
| 7 | `benchmarks/test_benchmarks.py`: a **pytest-benchmark** micro-suite for the hot paths (open/print/subprocess wrappers, import cost), marked so it is **excluded from the default `pytest tests/` run** (e.g. its own dir + `--benchmark-only`, or a `bench` marker deselected by default). This is the CI-friendly regression layer. | `benchmarks/test_benchmarks.py`, `pyproject.toml` (marker/testpaths) | Low–Medium (functionality: must NOT slow or break the normal suite) | `pytest tests/` unchanged (still 628±); `pytest benchmarks/ --benchmark-only` runs the bench suite. |
| 8 | `benchmarks/README.md`: how to run (`--quick` vs full), how to contribute a result JSON from a new machine, how to aggregate/plot, and a plain-English interpretation guide. Add a short "Performance / Overhead" section to `docs/` (or README) that cites representative numbers once collected (leave a placeholder table to fill from real data). | `benchmarks/README.md`, `docs/` | Low | Docs build/read cleanly; instructions are copy-pasteable. |
| 9 | `benchmarks/results/.gitkeep` + a committed sample result from THIS machine so the aggregate/plot scripts have real input and reviewers see the format. | `benchmarks/results/` | Low | `aggregate.py` runs on the committed sample. |

## Deferred / out of scope (with reason)

| Item | Reason |
|------|--------|
| Continuous performance-regression gating in CI (fail build on N% slowdown) | Remediation Risk Medium-High on Functionality: perf thresholds are noisy across runners and would cause flaky CI. Provide the bench suite + guidance now; wire a CI *reporting* job later if desired. |
| Windows tree-scope benchmark | Tree scope is unimplemented on Windows (falls back to process); nothing to measure. Scenario is skipped on Windows with a recorded reason. |

## Scope check

- Over-scope guard: keep the scenario list tied to real pubrun features; no speculative
  micro-optimizations, no new runtime deps, no `rich`. Matplotlib/pytest-benchmark are
  strictly in the `[bench]` extra and only imported by `plot.py`/`test_benchmarks.py`.
- Under-scope: the multi-machine aggregation (Step 5) is essential for the paper and is
  included, not deferred.

## Required tests / validation

- `pip install -e .` still pulls **zero** runtime deps (verify `pip show` / a clean venv).
- `pytest tests/ -q` is unchanged (628 passed, 2 skipped, 1 known flake) — the bench
  tests must not run in the default suite.
- `python benchmarks/harness.py --quick` produces a valid result JSON.
- `python benchmarks/aggregate.py benchmarks/results/*.json` produces CSV + Markdown.
- `benchmarks/plot.py` degrades gracefully without `[bench]` installed.

## Spec / documentation sync

- New `[bench]` extra → mention in `README`/install docs and `CHANGELOG [Unreleased]`.
- New "Performance / Overhead" doc section (placeholder numbers until real data lands).
- Run `/assess documentation` after execution.

## Open questions

1. Confirm the `[bench]` extra name (`bench`) and that `matplotlib` (+ `numpy` if pulled
   transitively) is acceptable as a dev-only extra. (Assumed yes per prior decision.)
2. Default iteration count for the full run (proposed 20; `--quick` uses 5). Confirm.
3. Should the representative overhead table in the docs be filled from the maintainer's
   machines before publishing, or is the committed sample from the dev machine enough
   to ship the harness? (Recommend: ship harness now, fill numbers as data arrives.)

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before execution and
is NOT auto-executed. On approval: implement the ordered steps, validate, sync docs, and
move this IPD to `.agents/plans/executed/`.
