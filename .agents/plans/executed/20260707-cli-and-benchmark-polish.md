# IPD: CLI & benchmark polish (report-bug/feedback rename, res all-resources, I/O ground-truth, bench help)

- Date: 2026-07-07
- Concern: usability / discoverability / measurement completeness. Four small, independent,
  already-decided changes bundled into one execution.
- Scope: `src/pubrun/__main__.py` (command rename, res dispatch help), `src/pubrun/report/
  diagnostics.py` (render all resources in `res`), `benchmarks/scenarios.py` +
  `benchmarks/workloads/` (I/O ground-truth baselines). No change to capture/runtime data
  model beyond rendering already-captured fields.
- Status: EXECUTED (2026-07-07). All four items implemented, tested (10 new/updated tests),
  documented. 757 passed / 2 skipped (only the known SIGPIPE flake fails, passes in
  isolation). See execution record at end.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Decisions (maintainer)

1. **Rename the bug/feedback commands.** `bug-report` (aliases `feedback`/`issue`) →
   **two separate commands**: `pubrun report-bug` (bug/feature reports) and `pubrun
   feedback`. **HARD RENAME** — old names removed, documented as a breaking change in the
   CHANGELOG. Chosen names: `report-bug` (verb-object; verified NOT to collide with the
   hidden `report` command — argparse requires exact subcommand matches; `report issue`
   WOULD have collided since `report` takes a positional `run_dir`), and `feedback` (matches
   pubrun's terse one-word command style; was an existing alias). Both call the existing
   `_run_bug_report` behavior (open the GitHub issues URL + print diagnostics) — bug reports
   and feedback both land as GitHub issues.
2. **`pubrun res` shows ALL monitored resources**, not just single-process CPU%+RSS. Add
   rendering of: process-tree peak RSS (`peak_tree_rss_bytes`, when scope=tree), system
   memory (`system_memory` free/available/cached), load average (`load_average`), node
   iowait (`system_iowait_pct`, labeled node-wide/indicative), and per-process I/O byte
   counters (`io_counters` delta). `cpu`/`mem` stay single-metric. Absent fields are omitted
   (honest) — older manifests just show less.
3. **Add ground-truth I/O baseline scenarios** to the benchmark suite: a `/dev/null` write
   sink (isolates pubrun's open/write-path tax from storage) and a `/dev/shm` tmpfs
   (RAM-backed I/O floor for cross-machine comparison). Cross-platform-honest: `/dev/null`
   → `NUL` on Windows; `/dev/shm` skipped (recorded as a `skipped` scenario) where
   unavailable (macOS/Windows).
4. **`pubrun bench` invocation stays flag-based** (`--quick`/`--iterations`/`--passes`); NO
   positional `quick`/`full` subcommand (avoids a second redundant way to set iterations —
   KISS). Only improve help text so quick-vs-full is obvious.

## Project conventions (Step 0)

- Principles: KISS, intuitive/self-documenting CLI, honest docs, never crash. Terse
  one-word command names are the norm (`cite`, `clean`, `diff`, `meta`, `bench`).
- `NO_COLOR`-respecting textual markers; non-DIM color only.
- Plans: `.agents/plans/pending/` → `executed/`, `YYYYMMDD-<slug>.md`.

## Verified current state (2026-07-06)

- `bug-report` at `__main__.py:1525-1531` (`aliases=["feedback","issue"]`), handler
  `_run_bug_report` (`:1357-1387`) opens `.../issues/new` + prints diagnostics; dispatch at
  `:2035-2036`; `_known_aliases` at `:1825`. `report` is a separate hidden command
  (`:1718-1733`, positional `run_dir`+`section`) — hence the `report issue` collision.
- `res`/`cpu`/`mem` (`__main__.py:1632-1758`) → `_run_resources` (`:499-533`) →
  `print_resources_report` (`report/diagnostics.py:592-798`). Today renders ONLY
  `peak_rss_bytes`/`end_rss_bytes` (mem/all), `peak_cpu_percent` (cpu/all), and the two
  time-series charts. Does NOT render `peak_tree_rss_bytes`, `system_memory`,
  `load_average`, `system_iowait_pct`, or `io_counters` (all now in the manifest via the
  prior IPDs).
- Benchmarks: `benchmarks/workloads/{noop,cpu_burn,print_loop,file_read}.py`;
  `file_read.py` writes 8 MiB to `tempfile.mkstemp()` ($TMPDIR) and reads it back — no
  `/dev/null` or `/dev/shm` baseline exists. Scenarios in `scenarios.py:75-112`;
  `hotpath-open-{baseline,pubrun}` are the only I/O scenarios.
- `bench` (`__main__.py:1578-1598`): `--quick` flag; `harness.py` `FULL_ITERATIONS=30`,
  `QUICK_ITERATIONS=8`, `--passes` default 2.

## Proposed changes

1. **Command rename (`__main__.py`):** register `report-bug` and `feedback` as two separate
   subparsers (no aliases); remove `bug-report`/`issue`. Update the dispatch set to
   `{"report-bug","feedback"}` and the `_known_aliases`/help-listing accordingly. Keep
   `_run_bug_report` as the shared handler. CHANGELOG breaking note.
2. **`print_resources_report` (`diagnostics.py`):** in the `metric == "all"` path, after the
   existing RSS/CPU lines, render the additional fields when present: tree RSS, system
   memory (free/available), load average, node iowait (with the "node-wide, indicative
   only" label), and io_counters read/write delta. Format with existing helpers; omit any
   absent field. Do NOT change the `cpu`/`mem` single-metric output.
3. **Benchmarks:** add `benchmarks/workloads/io_sink.py` parameterized (via env/argv) to
   write-and-read against a target path; add scenarios `hotpath-open-devnull` and
   `hotpath-open-devshm` (Linux; `devshm` recorded `skipped` where `/dev/shm` is absent;
   `devnull` uses `NUL` on Windows). These are baselines/reference floors, not pubrun-vs-
   baseline overhead pairs (document as ground-truth). Bump schema note only if fields
   change (they do not — new scenarios reuse the existing per-scenario shape).
4. **`bench` help:** clarify `--quick` (fast smoke, N iters) vs the default full run in the
   help/epilog; optionally add a `--full` flag as an explicit alias of the default for
   self-documentation. No positional subcommands.

## Anti-regression / invariants

- **Command rename is the intentional breaking change** (CHANGELOG). No OTHER command
  changes. A test asserts `report-bug` and `feedback` both parse and dispatch to the
  handler, and that `bug-report`/`issue` are gone (argparse error).
- **`res` rendering is additive** — `cpu` and `mem` output unchanged (characterization);
  `res` shows the new fields only when present; older manifests render without error.
- **Benchmark additions are additive** — existing scenarios/aggregation unchanged; new
  scenarios skip cleanly where the target path is unavailable; `/dev/null` writes must not
  attempt to read back (nothing to read) — the sink workload handles write-only correctly.
- Never crash / honest: absent resource fields omitted, not shown as null; `/dev/shm`
  absence → `skipped`, not an error.

## Required tests / validation

- CLI: `report-bug --help` and `feedback --help` exit 0; `bug-report`/`issue` no longer
  exist (nonzero/parse error). Both new commands dispatch to the handler (mock
  `webbrowser.open`).
- `res` rendering: given a manifest with the full resource set, output contains tree-RSS,
  system-memory, load, iowait, and io-counter lines; `cpu`/`mem` output unchanged; a
  minimal/old manifest renders without those lines and without error.
- Benchmark: `hotpath-open-devnull` runs; `hotpath-open-devshm` runs on Linux or is
  `skipped` where `/dev/shm` is absent.
- Full suite green (baseline 747 passed; known SIGPIPE flake excepted).

## Spec / documentation sync

`docs/cli.md` (rename `bug-report`→`report-bug`+`feedback`; expand `res` description),
`benchmarks/README.md` (new I/O baselines), `CHANGELOG.md` (breaking rename + res + bench).
Run `/assess documentation` after implementation.

## Approval and execution gate

All four decisions are already made by the maintainer; this IPD is the paper trail. Execute
this session, then move to `.agents/plans/executed/`.

## Execution record (2026-07-07)

All four items executed by opencode after the maintainer's interactive decisions.

1. **Rename (`__main__.py`):** `bug-report`/`issue` REMOVED; `report-bug` and `feedback`
   registered as two separate subparsers, both dispatching to `_run_bug_report`. `feedback`
   dropped from `_known_aliases`. Verified: both appear in `--help`; `bug-report`/`issue`
   now exit non-zero (argparse invalid-choice). CHANGELOG breaking note added.
2. **`res` comprehensive (`report/diagnostics.py`):** the `metric == "all"` path now renders
   process-tree RSS, system memory (available at start + lowest), load average, node iowait
   (labeled indicative-only), and per-process I/O byte volume (storage + logical), each only
   when present. `cpu`/`mem` unchanged (verified by test). Old manifests render without the
   new lines and without error.
3. **I/O ground-truth baselines:** new `benchmarks/workloads/io_sink.py` (target via
   `PUBRUN_BENCH_IO_TARGET`; write-only for null devices, write+read for dir targets);
   `Scenario` dataclass gained an additive `env` field; harness merges `scn.env` into the
   child env. Three new `io_baseline` scenarios: `io-baseline-devnull` (`/dev/null`, `NUL`
   on Windows), `io-baseline-devshm` (Linux; skipped where `/dev/shm` unavailable),
   `io-baseline-tmpdir`. Verified they run end-to-end and `aggregate.py` tolerates them.
4. **`bench` help (`__main__.py`):** added a `--full` flag (mutually exclusive with
   `--quick`; explicit alias of the default) and clarified iteration counts in help. No
   positional subcommand (KISS — flags remain the one way).

**Tests (10 new/updated):** report-bug + feedback dispatch (parametrized) + old-names-gone;
`TestResComprehensiveRender` (all-fields render, cpu stays focused, old-manifest clean);
`TestIoBaselineScenarios` (registered, devnull target, devshm skip logic, io_sink workload
for null + dir). NOTE: the scenarios-loader test registers the module in `sys.modules`
before `exec_module` so Python 3.12+ `@dataclass` can resolve `cls.__module__` (a testing
gotcha, not a scenarios.py bug). Full suite **757 passed**, 2 skipped; lone failure the
known SIGPIPE flake (passes in isolation).

**Docs:** `docs/cli.md` (`report-bug`/`feedback` rename + comprehensive `res`),
`benchmarks/README.md` (io_baseline floors), `CHANGELOG.md` (breaking rename + res + bench).
