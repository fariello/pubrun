# IPD: Performance/overhead benchmark suite

- Date: 2026-07-05
- Concern: performance measurement / reproducible benchmarking (net-new tooling)
- Scope: new `benchmarks/` tree in the public repo; a `[bench]` optional-dependency
  extra; no change to `src/pubrun/` runtime behavior.
- Status: EXECUTED (2026-07-05). All steps implemented; deferrals (CI perf-gating,
  Windows tree-scope) intact. `pytest tests/` unchanged (631 collected). `[bench]` extra
  does not leak into the base install. A quick sample result + aggregated summary are
  committed; representative docs numbers await multi-system collection by the maintainer.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)
- Plan-review: hardened 2026-07-05 (verdict APPROVE WITH REVISIONS APPLIED); see the
  "Plan-review revisions" section at the end.

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
   import mode. The actual modules are `import pubrun` (auto), `import pubrun.noauto`,
   `import pubrun.nopatch`, `import pubrun.noconsole`, `import pubrun.minimal` (verified
   against `src/pubrun/*.py` — there is NO `quiet` module; `noconsole` is the correct
   name, and `run --mode` accepts exactly `auto|noauto|nopatch|noconsole|minimal`).
   Isolate: background hardware thread on/off, startup-manifest write.
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
| 1 | Add the `bench` extra to `[project.optional-dependencies]` (alongside existing `dev`, `tui`): `pytest-benchmark`, `matplotlib`. Do NOT list `numpy` explicitly — matplotlib depends on it transitively, so pip resolves it; adding it would just duplicate. Keep `bench` OUT of `dev` (so the normal dev/test loop stays lean). | `pyproject.toml` | Low | `pip install -e .[bench]` resolves; `pip install -e .` still installs zero runtime deps (verify in a clean venv with `pip list`). |
| 2 | Create `benchmarks/harness.py`: a **stdlib-only** measurement core. Runs each scenario in a **fresh subprocess** (so import cost is real, not warm), N iterations (default 20, configurable), records min/median/p95/mean/stdev of wall time via `time.perf_counter`, plus the scenario's config. Emits one JSON per (machine × run). Never imports matplotlib/pytest-benchmark. | `benchmarks/harness.py` | Low–Medium (complexity: keep scenario list declarative) | `python benchmarks/harness.py --quick` runs in <60s and writes a JSON. |
| 3 | Define scenarios declaratively in `benchmarks/scenarios.py` (name, import mode, config overrides, workload). Workloads are tiny scripts under `benchmarks/workloads/` (e.g. `noop.py`, `cpu_burn.py`, `file_read.py`, `subprocess_spawn.py`, `print_loop.py`). | `benchmarks/scenarios.py`, `benchmarks/workloads/*.py` | Low | Each workload runs standalone; harness enumerates all scenarios. |
| 4 | Capture machine metadata into each result JSON by reusing pubrun's own capture — do not re-implement. Use the config-taking capture functions: `pubrun.capture.hardware.get_hardware(config)`, `pubrun.capture.host.get_host(config)`, `pubrun.capture.python_runtime.get_python_runtime(config)` (call `pubrun.config.resolve_config()` for `config`). Note `get_hostname()` takes NO args and `get_rss_bytes(pid)`/`get_cpu_percent(pid)` take a pid — do not pass `config` to those. Also record pubrun version (`pubrun.__version__`), git commit, UTC timestamp, and iteration count. | `benchmarks/harness.py` | Low | JSON contains a `machine` block with CPU model, cores, RAM, OS, Python, pubrun version; harness runs on a machine with no GPU (hardware capture returns gracefully). |
| 5 | `benchmarks/aggregate.py`: merge many result JSONs (`benchmarks/results/*.json`) into one tidy CSV + a summary table (Markdown) — overhead per feature, per machine. Stdlib-only. | `benchmarks/aggregate.py` | Low | Given 2 sample JSONs, produces a CSV and a Markdown table. |
| 6 | `benchmarks/plot.py`: OPTIONAL matplotlib figures from the aggregated CSV (bar charts of overhead per feature; startup-mode comparison). Imported lazily; prints a clear "install .[bench]" message if matplotlib is missing. Never required to collect data. | `benchmarks/plot.py` | Low | With `[bench]` installed, produces PNGs; without it, exits cleanly with guidance. |
| 7 | `benchmarks/test_benchmarks.py`: a **pytest-benchmark** micro-suite for the hot paths (open/print/subprocess wrappers, import cost). **Exclusion is already handled**: `pyproject.toml` sets `testpaths = ["tests"]`, so `benchmarks/` is NOT collected by a bare `pytest` — do NOT change `testpaths`. Two cautions to handle in the plan: (a) `addopts = "--cov=src --cov-report=..."` is global, so a raw `pytest benchmarks/` would still apply coverage (which conflicts with/《slows》pytest-benchmark timing) — the bench suite must be invoked as `pytest benchmarks/ -o addopts="" --benchmark-only` (or an equivalent no-cov invocation documented in Step 8); (b) requires the `[bench]` extra installed, else pytest-benchmark import fails — the file should `pytest.importorskip("pytest_benchmark")` so a plain checkout without `[bench]` does not error if someone points pytest at it. | `benchmarks/test_benchmarks.py` (no `pyproject.toml` testpaths change needed) | Low | `pytest tests/` unchanged (631 collected; 628 pass / 2 skip / 1 known flake); `pytest benchmarks/ -o addopts="" --benchmark-only` runs the bench suite; a checkout without `[bench]` skips it cleanly. |
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

- `pip install -e .` (no extras) still pulls **zero** runtime deps on 3.11+ (verify in a
  clean venv with `pip list`: only pubrun + tomli-on-<3.11 present, NOT matplotlib/
  numpy/pytest-benchmark). This is the key anti-regression check — the `bench` extra
  must not leak into the base install (rubric D/G).
- `pytest tests/ -q` is unchanged: **631 collected → 628 passed, 2 skipped, 1
  known-flaky** (`test_real_sigpipe_via_pipe`, passes in isolation). The bench tests
  must not be collected by a bare `pytest` (guaranteed by the existing
  `testpaths = ["tests"]`).
- `python benchmarks/harness.py --quick` produces a valid result JSON on a machine with
  and without a GPU (hardware capture degrades gracefully).
- `python benchmarks/aggregate.py benchmarks/results/*.json` produces CSV + Markdown.
- `benchmarks/plot.py` degrades gracefully (clear "install .[bench]" message, non-zero
  handled) when matplotlib is absent.
- `pytest benchmarks/ -o addopts="" --benchmark-only` runs the bench suite when `[bench]` is
  installed, and skips cleanly (`importorskip`) when it is not.

## Spec / documentation sync

- New `[bench]` extra → mention in `README`/install docs and `CHANGELOG [Unreleased]`.
- New "Performance / Overhead" doc section (placeholder numbers until real data lands).
- Run `/assess documentation` after execution.

## Open questions

1. RESOLVED: extra name is `bench`; `pytest-benchmark` + `matplotlib` confirmed
   acceptable (numpy comes in transitively via matplotlib — not listed explicitly).
2. Default iteration count for the full run (proposed 20; `--quick` uses 5). Confirm.
3. Should the representative overhead table in the docs be filled from the maintainer's
   machines before publishing, or is the committed sample from the dev machine enough
   to ship the harness? (Recommend: ship harness now, fill numbers as data arrives.)

## Cross-repo note (harness location decision)

The maintainer confirmed the benchmark **harness lives in the public `pubrun` repo**
(this IPD), while the private `pubrun-paper` repo only *consumes/analyzes* the result
JSONs for the manuscript (figures/tables). Reproducibility of the paper's overhead
numbers requires the harness to be in the reviewed software repo (a JOSS expectation)
and it version-locks to the code it measures.

`~/VC/pubrun-paper/benchmarks/benchmark_capture.py` is an early **seed** of this idea
(it times each `get_*` capture engine but assumes a sibling `src/` and won't run
standalone in the paper repo). Fold its per-engine startup-timing approach into this
harness as one scenario group (the "startup metadata capture" timings in
"What to measure" §1/§4). After this IPD executes, retire that seed in the paper repo
(move it to `pubrun-paper/notes/`) so there is a single source of truth. That paper-repo
cleanup is tracked separately and is NOT part of this pubrun IPD's file changes.

Dependency note: this harness benchmarks `full-environment` package mode, which relies
on the EC-08 null-name fix (`packages.py:140`, present on HEAD). Confirmed present; no
action needed, but do not run this suite against a pre-EC-08 checkout.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before execution and
is NOT auto-executed. On approval: implement the ordered steps, validate, sync docs, and
move this IPD to `.agents/plans/executed/`.

## Plan-review revisions (2026-07-05)

Verdict: **APPROVE WITH REVISIONS APPLIED**. Verified the plan's technical claims
against the actual `src/pubrun/` source before approving. Approach is sound; no
re-plan. Changes:

- **PR-B1 (HIGH, accuracy):** the import-mode list named `import pubrun.quiet` — there
  is **no `quiet` module**. Corrected to the real set (`auto`, `noauto`, `nopatch`,
  `noconsole`, `minimal`), verified against `src/pubrun/*.py` and the `run --mode`
  choices.
- **PR-B2 (HIGH, functionality):** Step 4 "reuse pubrun's capture" was signature-
  ambiguous. Pinned the exact functions: `get_hardware/get_host/get_python_runtime`
  take `config`; `get_hostname()` takes none; `get_rss_bytes/get_cpu_percent` take a
  pid. Prevents an executor from passing `config` to the wrong function.
- **PR-B3 (MEDIUM, functionality):** Step 7 assumed a `testpaths` change was needed —
  it is **not** (`testpaths = ["tests"]` already excludes `benchmarks/`). Added the two
  real cautions: the global `--cov` `addopts` conflicts with pytest-benchmark (invoke
  as `pytest benchmarks/ -o addopts="" --benchmark-only`), and the bench test file must
  `importorskip("pytest_benchmark")` so a checkout without `[bench]` doesn't error.
- **PR-B4 (LOW, accuracy):** Step 1 said add numpy "only if needed" — matplotlib
  always pulls numpy transitively, so do not list it. Anchored `bench` alongside the
  existing `dev`/`tui` extras.
- **PR-B5 (MEDIUM, accuracy):** corrected the baseline test numbers throughout from
  "628±" to the verified "631 collected → 628 pass, 2 skip, 1 known flake".
- **PR-B6 (MEDIUM, anti-regression, rubric D/G):** strengthened the key guard — a
  clean-venv `pip list` must confirm the `bench` extra does NOT leak matplotlib/numpy/
  pytest-benchmark into the base `pip install -e .`.
- **PR-B7 (MEDIUM, scope/stakeholder):** recorded the maintainer's "harness in pubrun,
  analysis in pubrun-paper" decision and the plan to fold/retire the
  `pubrun-paper/benchmarks/benchmark_capture.py` seed; noted the `full-environment`
  scenario depends on the EC-08 fix (present on HEAD).

No plan-review finding was deferred; all were fixed in place. Deferrals in the plan
(CI perf-gating, Windows tree-scope) remain correctly justified on their named axes.
