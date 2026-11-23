# IPD: Timing Docs Examples Benchmark and Whole-Set Verification

- Date: 2026-11-21
- Kind: child
- Concern: Specification and documentation reconciliation, understandable timing examples, timing-instrumentation cost benchmarking, and whole-Set verification.
- Scope: Reconcile `docs/manifest.md`, `docs/architecture.md`, `docs/functional_spec.md`, `docs/api.md`, and `docs/performance.md`; update `examples/05_execution_phases.py`, `examples/minimal-research-workflow/manifest_excerpt.json`, and `examples/minimal-research-workflow/README.md`; measure timing instrumentation overhead locally and execute whole-Set regression checks.
- Scope-Paths: docs/manifest.md, docs/architecture.md, docs/functional_spec.md, docs/api.md, docs/performance.md, examples/05_execution_phases.py, examples/minimal-research-workflow/manifest_excerpt.json, examples/minimal-research-workflow/README.md
- Item-Dependencies: executed:e1fwy2, executed:8co0wy, executed:vrr1fv
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: complex
- Short-Description: Sync specs, docs, and examples, benchmark timing instrumentation cost, and run whole-Set verification
- Work-Kind: bug
- Priority: high
- From-Backlog: 6hp1zu
- Blocks-Release: next
- Set: timing-acc
- Order: 4
- Highest E allocated: 05
- Author: agent
- Id: 3tvesf
- Approval: 2026-11-22, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-22 approved (aw set): status set to approved
- 2026-11-22 /plan-review (Gemini 4 Neon (High)): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004, PR-005
- 2026-11-22 draft (agent): created.
- 2026-11-22 to-review (agent): authored review-ready child plan from backlog item `6hp1zu`.

## Goal

Reconcile all repository specifications, reference docs, and examples with the monotonic timing and overhead-separation contracts introduced by prerequisite child plans `e1fwy2` (manifest timing schema and tracker monotonic lifecycle), `8co0wy` (monotonic phase, subprocess, and resource timing), and `vrr1fv` (reports, status, diff, and TUI timing semantics). Measure and record the timing instrumentation cost itself under documented local conditions without publishing or leaving unredacted files. Run whole-Set verification across the full test suite, all examples, and the path sanitizer.

### Documentation, benchmark, and verification pipeline

The text in `## Proposed changes (ordered, validatable)` is normative. These diagrams summarize the execution sequence and artifact relationships in this plan after `e1fwy2`, `8co0wy`, and `vrr1fv` reach `executed`.

```mermaid
flowchart LR
    A["Sync schema & spec docs (manifest.md, architecture.md, functional_spec.md)"] --> B["Sync API & examples (api.md, 05_execution_phases.py, minimal-research-workflow)"]
    B --> C["Run local non-publishing harness + isolated microbenchmark; update performance.md"]
    C --> D["Run whole-Set checks (pytest tests/, examples/verify_all.py, sanitize_paths.py)"]
```

```mermaid
erDiagram
    PREREQ_E1FWY2 ||--o{ SPEC_DOCS : "defines timing schema and lifecycle"
    PREREQ_8CO0WY ||--o{ SPEC_DOCS : "defines phase and subprocess durations"
    PREREQ_VRR1FV ||--o{ SPEC_DOCS : "defines consumer and diff semantics"
    SPEC_DOCS ||--|| EXAMPLES_AND_BENCH : "illustrated and measured by"
    EXAMPLES_AND_BENCH ||--|| WHOLE_SET_CHECKS : "validated by"
```

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Specification and documentation reconciliation

- [x] E-01 Update `docs/manifest.md`, `docs/architecture.md`, and `docs/functional_spec.md` to document monotonic durations, disjoint versus overlapping intervals, tracked-interval scope (including late imports), `subprocess_record` durations, `phase_end` duration payloads, crashed-run estimates, and legacy v1.0 compatibility.
  - Depends on: none
  - Expected outcome: All three docs remove stale statements claiming `elapsed_seconds = ended_at_utc - started_at_utc` or "trivial elapsed-time arithmetic" via wall-clock subtraction. Every additive `timing` and `subprocesses` field matches `schemas/manifest.schema.json`. Docs distinguish Portable Operating System Interface (POSIX) Coordinated Universal Time (UTC) chronology from monotonic durations (never persisted as raw counter values), explain that overlapping background hardware capture must not be summed with `workload_seconds`, explain that `finalization_overhead_seconds` excludes the final atomic write of `manifest.json`, document legacy v1.0 and crashed-estimate classification (`vrr1fv`), preserve any additive `startup-perf` (`ckc3vl`) sections if already present, and introduce zero em dashes (U+2014) or en dashes (U+2013) in added or edited lines.
  - Execution state: performed

- [x] E-02 Update `docs/api.md` to document `start()`, `stop()`, `phase()`, `tracked_run()`, `audit_run()`, `diff()`, `pubrun.subprocess.*`, and `pubrun.popen()` timing behavior and late-import tracked-interval semantics.
  - Depends on: E-01
  - Expected outcome: `docs/api.md` explains what each timing interval measures, states clearly that importing `pubrun` midway through a script measures the tracked interval rather than full process lifetime, documents `phase()` monotonic `phase_end` duration payloads (excluding profiler setup and dump I/O), documents explicit subprocess wrapper monotonic durations and `capture_state`, documents legacy-versus-monotonic semantic notes in `pubrun.diff()`, and introduces zero em dashes (U+2014) or en dashes (U+2013) in added or edited lines.
  - Execution state: performed

### Task group 2: Examples, instrumentation benchmark, and whole-Set verification

- [x] E-03 Update `examples/05_execution_phases.py`, `examples/minimal-research-workflow/manifest_excerpt.json`, and `examples/minimal-research-workflow/README.md` with accurate timing fields and a plain-language explanation of what is measured.
  - Depends on: E-02
  - Expected outcome: `examples/05_execution_phases.py` verifies that each `phase_end` event carries a nonnegative numeric `elapsed_seconds` (not `bool`) and `duration_clock == "monotonic"`, verifies the finalized `manifest.json` carries monotonic tracked-workload timing metadata, prints a concise explanation of what was measured while preserving `[PASS] PASS: 05_execution_phases.py`, and exits 0. `examples/minimal-research-workflow/manifest_excerpt.json` remains valid JSON, adds the additive `timing` fields with internally consistent redacted/synthetic values, and its `"timing"` object validates against the `$defs.timing` subschema of `schemas/manifest.schema.json`. `examples/minimal-research-workflow/README.md` adds a concise plain-language section explaining tracked workload versus capture overhead, non-additive background hardware capture, and late-import scope, introducing zero em dashes (U+2014) or en dashes (U+2013) in added or edited lines.
  - Execution state: performed

- [x] E-04 Benchmark the timing instrumentation cost locally using non-publishing commands and document the scoped methodology and measurements in `docs/performance.md` without committing unredacted host-identifying artifacts.
  - Depends on: E-03
  - Expected outcome: Execute local non-publishing measurements without modifying `src/pubrun/`: (1) `python3 benchmarks/harness.py --passes 3 --iterations 30 --redacted-out /tmp/pubrun-timing-harness.redacted.json` (recording pass 1 cold vs pass 3 warm medians and dispersion, then deleting `/tmp/pubrun-timing-harness.redacted.json` so `benchmarks/results/` stays clean); and (2) an ephemeral in-memory Python microbenchmark (`N >= 30` repetitions across 3 passes: pass 1 cold vs pass 3 warm) measuring raw `time.perf_counter()` bookkeeping overhead versus an empty-loop baseline, active `pubrun.phase()` loop versus inactive no-op baseline, and `Run` `start()`/`stop()` breakdown (`startup_overhead_seconds`, `workload_seconds`, `finalization_overhead_seconds`, `writer_overhead_seconds`). Record environment (Operating System (OS), Python version, Central Processing Unit (CPU) model and logical cores, filesystem `fstype` and `is_network` via `src/pubrun/capture/filesystem.py::get_filesystem` with zero personal paths or hostnames), git commit SHA, workload, baseline, repetitions, cold versus warm passes, median, standard deviation (stdev), and Interquartile Range (IQR) in `V-04` and in a dedicated environment-scoped subsection of `docs/performance.md` (preserving `docs/performance.md#Representative results` intact, preserving any `startup-perf` (`ckc3vl`) subsection if present, making no unmeasured speedup claims, and introducing zero em or en dashes in added or edited lines).
  - Execution state: performed

- [x] E-05 Run whole-Set regression verification across the full test suite, all examples, and the path-sanitizer check, and record the remaining multi-OS and multi-Python Continuous Integration (CI) matrix gate.
  - Depends on: E-04
  - Expected outcome: `pytest tests/ -v`, `python3 examples/verify_all.py`, and `python3 scripts/sanitize_paths.py --check --all` all exit 0 with actual runner output pasted into `V-05`, `git status -s` shows no stray temporary or unredacted benchmark files, and `V-05` explicitly records that `.github/workflows/ci.yml` (Ubuntu, Windows, and macOS across Python 3.8 through 3.14) must pass in GitHub Actions before release closure.
  - Execution state: performed

## Project conventions discovered (Step 0)

- `docs/manifest.md## timing`, `docs/architecture.md### Timestamp Format`, `docs/architecture.md## 9. Observed vs Derived vs Inferred`, and `docs/functional_spec.md### 4.1 Timestamp Format` currently state `elapsed_seconds = ended_at_utc - started_at_utc` or "trivial elapsed-time arithmetic" from wall-clock timestamps, which conflicts with monotonic duration semantics after prerequisite `e1fwy2`.
- `docs/functional_spec.md### 7.1 Implemented Event Types`, `docs/functional_spec.md### 15.2 Recorded Fields`, and `docs/functional_spec.md### 19.2 Finalization Lifecycle` do not yet document `phase_end` monotonic durations, `subprocess_record` `elapsed_seconds`/`duration_clock`/`capture_state`, or the `t2` pre-teardown workload boundary and `config.resolved.json`-before-`manifest.json` write order.
- `examples/verify_all.py` executes every numbered script (`examples/00_*.py` through `examples/11_*.py`) plus `examples/minimal-research-workflow/analysis.py`, expects exit code 0, and highlights stdout lines containing `"PASS"` or `"TESTING"`; `tests/test_example_minimal_research_workflow.py` smoke-tests `examples/minimal-research-workflow/analysis.py`.
- `examples/minimal-research-workflow/manifest_excerpt.json` is an intentionally shortened redacted excerpt that omits `capture_state` on several sections (`run`, `invocation`, `capture`, `status`, `git`, `host`, `python`, `signals`), so JSON Schema validation must target the `$defs.timing` subschema of `schemas/manifest.schema.json` alongside full-file JSON parsing.
- `scripts/sanitize_paths.py --check --all` is enforced in `.github/workflows/secret-scan.yml` to block machine-local absolute home paths or hostnames from entering tracked files.
- `benchmarks/harness.py` writes a redacted JSON file under `benchmarks/results/` by default unless `--redacted-out <temp_path>` is passed (and writes an unredacted copy only when `--unredacted` or `--out` is passed); benchmark runs must never publish to GitHub Gists, open issues, or submit High-Performance Computing (HPC) scheduler jobs without explicit authorization.
- Sibling Set `startup-perf` (child `ckc3vl`, post-change overhead comparison and documentation sync) also edits `docs/manifest.md`, `docs/architecture.md`, `docs/functional_spec.md`, and `docs/performance.md`; edits here must remain additive to distinct subsections so either execution order composes cleanly.
- `AGENTS.md` prohibits em dashes (U+2014) and en dashes (U+2013) in newly authored or edited user-facing prose (`docs/`, `README.md`, examples).

## Findings

- **F-01 (Stale timing specifications):** `docs/manifest.md## timing`, `docs/architecture.md### Timestamp Format`, `docs/architecture.md## 9. Observed vs Derived vs Inferred`, and `docs/functional_spec.md### 4.1 Timestamp Format` explicitly state `elapsed_seconds = ended_at_utc - started_at_utc` and describe `timing` as having only `started_at_utc`, `ended_at_utc`, and `elapsed_seconds`.
- **F-02 (Missing late-import, overlap, subprocess, and diff semantics in docs and examples):** Neither `docs/api.md`, `docs/manifest.md`, `docs/functional_spec.md`, nor `examples/minimal-research-workflow/README.md` explains that importing `pubrun` late measures only the tracked interval, that background hardware capture overlaps with workload execution, that `phase_end` and `subprocesses` carry monotonic durations, or how legacy v1.0 manifests are labeled in reports and diffs.
- **F-03 (Unmeasured instrumentation cost):** `docs/performance.md` does not yet explain how `pubrun` separates its own startup and finalization overhead from workload timing or report measured timing-instrumentation cost with cold/warm passes and dispersion.

## Proposed changes (ordered, validatable)

1. **`docs/manifest.md`:**
   - Replace `docs/manifest.md## timing` (table and `[!NOTE]` block) to document `started_at_utc`, `workload_started_at_utc`, `ended_at_utc`, `finalized_at_utc`, `elapsed_seconds`, `workload_seconds`, `startup_overhead_seconds`, `finalization_overhead_seconds`, `session_seconds`, `hardware_wait_seconds`, `background_hardware_seconds`, `duration_clock`, `elapsed_basis`, `interval_scope`, and `capture_state`.
   - Document clearly which intervals are disjoint (`startup_overhead_seconds`, `workload_seconds`, `finalization_overhead_seconds`), which overlap (`background_hardware_seconds` overlaps workload; `hardware_wait_seconds` is a sub-interval of `finalization_overhead_seconds`), that `finalization_overhead_seconds` excludes the final atomic write of `manifest.json`, that raw monotonic counter values are never serialized, how legacy v1.0 manifests (lacking `duration_clock` and `elapsed_basis`) are classified and labeled, and how crashed-run closeouts record `duration_clock: "wall_clock_estimated"` and `elapsed_basis: "crashed_estimate"`.
   - Update `docs/manifest.md## subprocesses` to document optional `elapsed_seconds`, `duration_clock`, `pid`, and `error`.
2. **`docs/architecture.md` and `docs/functional_spec.md`:**
   - Reconcile `docs/architecture.md## 3. Run Lifecycle`, `docs/architecture.md### Timestamp Format`, and `docs/architecture.md## 9. Observed vs Derived vs Inferred`, plus `docs/functional_spec.md### 4.1 Timestamp Format`, `docs/functional_spec.md### 7.1 Implemented Event Types`, `docs/functional_spec.md### 15.2 Recorded Fields`, and `docs/functional_spec.md### 19.2 Finalization Lifecycle`: UTC epoch floats remain the format for absolute chronology; monotonic clocks (`time.perf_counter()`) produce nonnegative durations; raw monotonic counter readings are never serialized; `phase_end` carries `elapsed_seconds` and `duration_clock: "monotonic"` (excluding profiler setup and dump I/O); `t2` marks workload end before blocking hardware wait; and `config.resolved.json` is written before `manifest.json` freezes finalized timing.
   - Preserve any additive sections written by sibling plan `ckc3vl` (Set `startup-perf`) if already present on disk.
3. **`docs/api.md`:**
   - Update `docs/api.md### pubrun.start(**overrides)`, `### pubrun.stop()`, `### pubrun.phase(name)`, `## 5. Lifecycle Wrappers` (`tracked_run()`, `audit_run()`), `### pubrun.diff(...)`, `### pubrun.subprocess.run(*args, **kwargs) / pubrun.subprocess.Popen(...)`, and `### pubrun.popen(cmd, mode="r", bufsize=-1)` to document monotonic timing guarantees, late-import tracked-interval scope, `phase()` profiler setup/dump exclusion, explicit subprocess monotonic durations and `capture_state`, and legacy-versus-monotonic diff notes when `timing` is included.
4. **`examples/05_execution_phases.py`, `examples/minimal-research-workflow/manifest_excerpt.json`, and `examples/minimal-research-workflow/README.md`:**
   - Extend `examples/05_execution_phases.py` to assert that each `phase_end` record carries numeric (non-`bool`), nonnegative `elapsed_seconds` and `duration_clock == "monotonic"`, assert that `manifest.json` carries monotonic tracked-workload timing metadata, and print a short explanation of what was measured while keeping `[PASS] PASS: 05_execution_phases.py` intact.
   - Update `examples/minimal-research-workflow/manifest_excerpt.json` to include the additive `timing` fields (`workload_started_at_utc`, `finalized_at_utc`, `workload_seconds`, `startup_overhead_seconds`, `finalization_overhead_seconds`, `session_seconds`, `hardware_wait_seconds`, `background_hardware_seconds`, `duration_clock`, `elapsed_basis`, `interval_scope`, `capture_state`) with internally consistent synthetic values that validate against `$defs.timing` in `schemas/manifest.schema.json`.
   - Add a concise "What timing metrics measure" section to `examples/minimal-research-workflow/README.md` explaining tracked workload versus capture overhead, non-additive overlapping background capture, and late-import tracked-interval scope.
5. **`docs/performance.md` and local non-publishing instrumentation benchmark:**
   - Without editing `src/pubrun/`, run:
     - `python3 benchmarks/harness.py --passes 3 --iterations 30 --redacted-out /tmp/pubrun-timing-harness.redacted.json` (and delete `/tmp/pubrun-timing-harness.redacted.json` immediately after reading its summary); and
     - An ephemeral in-memory Python microbenchmark (`N >= 30` repetitions across 3 passes: pass 1 cold vs pass 3 warm) measuring (a) raw `time.perf_counter()` bookkeeping call cost versus empty-loop baseline, (b) active `pubrun.phase()` loop versus inactive no-op baseline, and (c) `Run` `start()`/`stop()` timing breakdown (`startup_overhead_seconds`, `workload_seconds`, `finalization_overhead_seconds`, `writer_overhead_seconds`).
   - Capture environment (OS, Python version, CPU model/logical cores, filesystem `fstype`/`is_network` via `get_filesystem` with no personal paths or hostnames), git commit SHA, workload, baseline, repetitions (`N >= 30`), cold versus warm pass comparison (pass 1 vs pass 3), median, stdev, and IQR.
   - Add a dedicated, environment-scoped subsection (`### Timing instrumentation and overhead separation`) in `docs/performance.md` without modifying `docs/performance.md#Representative results` or clobbering any `ckc3vl` subsection, summarizing the measured results honestly with zero unmeasured speedup claims.
6. **Whole-Set verification and prose hygiene:**
   - Run `pytest tests/ -v`, `python3 examples/verify_all.py`, and `python3 scripts/sanitize_paths.py --check --all`, pasting actual runner outputs and exit codes into `V-05`.
   - Verify via a Python check over added lines (`git diff`) that zero em dashes (U+2014) or en dashes (U+2013) were introduced in any modified doc or example file, and verify `git status -s` contains only declared Scope-Paths.

## Deferred / out of scope (with reason)

- Running the GitHub Actions cross-OS/Python matrix (`ubuntu-latest`, `ubuntu-24.04`, `windows-latest`, `macos-latest` across Python 3.8 through 3.14 in `.github/workflows/ci.yml`) requires GitHub Actions runners after PR or push; local execution covers the host OS/Python and records the CI matrix gate explicitly.
  - Carrier-Declined: executed automatically by GitHub Actions CI (.github/workflows/ci.yml) on pull request or push; unavailable in a single local Linux worktree.
- Publishing benchmark results to GitHub Issues/Gists or running HPC scheduler scripts (`benchmarks/submit_bench*.sh`) is prohibited without explicit maintainer authorization.
  - Carrier-Declined: explicitly prohibited without explicit maintainer authorization.
- Optimizing startup cost (`_resolve_commit()` and config write coalescing) belongs to sibling backlog item `t1xqpw` (Set `startup-perf`, orchestrator `9ppa0r`).
  - Carrier: 9ppa0r

## Scope check

- Over-scope: none. Touches only the five docs files and three example files (8 Scope-Paths, 5 E-items).
- Under-scope: none. Covers documentation sync, example updates, instrumentation benchmarking, em/en-dash verification, and whole-Set verification required by backlog item `6hp1zu` and orchestrator `nr63qr`.

## Required tests / validation

Run inside the repository root and capture actual runner output and exit codes:

```bash
python3 benchmarks/harness.py --passes 3 --iterations 30 --redacted-out /tmp/pubrun-timing-harness.redacted.json && rm -f /tmp/pubrun-timing-harness.redacted.json
pytest tests/ -v
python3 examples/verify_all.py
python3 scripts/sanitize_paths.py --check --all
```

Also run the ephemeral in-memory timing-instrumentation microbenchmark (non-publishing, stdout only, zero `src/pubrun/` edits) and paste the measured summary table (environment, git revision, workload, baseline, repetitions, pass 1 cold vs pass 3 warm, median, stdev, and IQR) into `V-04`.

## Spec / documentation sync

This plan is the specification, documentation, and example synchronization plan for Set `timing-acc`.

## Open questions

### OQ-01: Where to record single-machine instrumentation benchmark numbers

- Blocking: no
- Status: resolved
- Owner: plan author (binding upon plan approval)
- Resolution or deferral rationale: `docs/performance.md#Representative results` keeps its cross-machine table as a placeholder until multi-machine collection occurs, while single-machine measurements must be labeled with their exact environment, revision, workload, baseline, repetitions, cold/warm passes, and dispersion. Record the local timing-instrumentation measurement both in `V-04` of this plan and in a clearly scoped, environment-labeled subsection of `docs/performance.md` without overwriting `docs/performance.md#Representative results` or committing host-identifying files. Human approval of this plan confirms this placement before execution.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition) (as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [x] V-01 validates E-01
  - Required evidence: Diff of `docs/manifest.md`, `docs/architecture.md`, and `docs/functional_spec.md` showing reconciled monotonic timing semantics, disjoint versus overlapping interval definitions, legacy and crashed-estimate classification rules, no stale `ended_at_utc - started_at_utc` claims, and pasted output of a Python check over added lines of `git diff -- docs/manifest.md docs/architecture.md docs/functional_spec.md` confirming zero em dashes (U+2014) or en dashes (U+2013).
  - Observed evidence:
    - Diff (`git diff --stat`): docs/manifest.md +55/-, docs/architecture.md +22/-, docs/functional_spec.md +26/- (248 insertions, 25 deletions across all 8 scope files).
    - docs/manifest.md `## timing`: replaced the 4-row table (which said `elapsed_seconds` = `ended_at_utc - started_at_utc`) with all 16 `$defs.timing` fields from schemas/manifest.schema.json; added chronology-vs-duration explanation (raw monotonic counters never persisted), a disjoint-vs-overlapping paragraph and ASCII diagram (background_hardware overlaps workload; hardware_wait inside finalization), tracked-interval / late-import paragraph, finalization excludes the final atomic `manifest.json` write, and legacy (`wall_clock`/`wall_clock_legacy`) plus crashed-estimate (`wall_clock_estimated`/`crashed_estimate`, partial) classification. `## subprocesses`: added `elapsed_seconds`, `duration_clock`, `pid`, `error` rows and capture_state semantics (checked against src/pubrun/capture/subprocesses.py and core.py wrappers).
    - docs/architecture.md: new `### Timing anchors` (t0..t3 with code locations, to_manifest_dict freeze, writer_overhead_seconds in memory only); `### Timestamp Format` bullet "Arithmetic simplicity: Elapsed time is `ended_at - started_at`" replaced by "Chronology only"; new `### Duration Format`; `phase_end` payload paragraph; subprocess capture description; §9 "Derived" example no longer `elapsed_seconds = ended_at - started_at`.
    - docs/functional_spec.md: §4.1 dropped "Trivial elapsed-time arithmetic (`ended_at - started_at`)", added MUST NOT subtract timestamps and new §4.1.1 Duration Format (incl. legacy v1.0, crashed, ghost); §7.1 `phase_end` payload; API table `phase()` row; subprocess record fields; §19.2 t2 before hardware wait and t3 + timing freeze.
    - Stale-claim grep `grep -rn "ended_at_utc - started_at_utc\|ended_at - started_at\|trivial elapsed\|Trivial elapsed" docs/ examples/ README.md` returns only docs/manifest.md:47 ("Durations are therefore **not** recomputed as `ended_at_utc - started_at_utc`") and :82 (describing what legacy manifests did): both intentional.
    - ckc3vl: no startup-perf content exists in these three files (grep), nothing to preserve there.
    - Dash check (Python over `+` lines of `git diff -U0 -- <file>`):
      ```
      docs/manifest.md: added=44 dash_lines=0
      docs/architecture.md: added=19 dash_lines=0
      docs/functional_spec.md: added=20 dash_lines=0
      ```
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: Diff of `docs/api.md` showing documented timing behavior for `start()`, `stop()`, `phase()`, `tracked_run()`, `audit_run()`, `diff()`, `pubrun.subprocess.*`, and `pubrun.popen()`, late-import tracked-interval scope, and pasted output of a Python check over added lines of `git diff -- docs/api.md` confirming zero em dashes (U+2014) or en dashes (U+2013).
  - Observed evidence:
    - docs/api.md diff (+44 lines): `start()` Timing paragraph + IMPORTANT callout on tracked interval vs process lifetime / late import; `stop()` Timing paragraph (t2 before 2 s hardware wait, finalization reported separately, manifest write after freeze, elapsed=workload, nested stop does not end workload) + example; `phase()` monotonic `phase_end` payload, profiler setup/dump excluded, `error`, JSON example; `tracked_run()`/`audit_run()` Timing paragraph; `diff()` legacy normalization and "timing definition changed" note + example; `pubrun.subprocess.*` timing/pid/capture_state/failed-launch; `pubrun.popen()` record on close.
    - Empirical check of every documented claim (script run with PYTHONPATH=<worktree>/src in /tmp/opencode/apichk): finalized timing had duration_clock=monotonic, elapsed_basis=workload, interval_scope=tracked_interval, capture_state complete, elapsed_seconds == workload_seconds (0.10425901506096125); startup+workload+finalization equals session_seconds; subprocess records: run pid=None complete, Popen pid=149470 complete, popen pid=None complete, missing executable raised FileNotFoundError and recorded failed with exit_code None; legacy-manifest diff produced the timing-definition-changed note; nested tracked_run shared the outer run and left it active ("nested ok").
    - Dash check: `docs/api.md: added=42 dash_lines=0`.
  - Result: pass

- [x] V-03 validates E-03
  - Required evidence: Diff of `examples/05_execution_phases.py`, `examples/minimal-research-workflow/manifest_excerpt.json`, and `examples/minimal-research-workflow/README.md`, pasted `python3 examples/05_execution_phases.py` output (exit code 0), pasted Python check confirming `manifest_excerpt.json` parses as valid JSON and its `"timing"` object validates against `$defs.timing` of `schemas/manifest.schema.json`, and pasted check confirming zero em/en dashes added to `examples/minimal-research-workflow/README.md`.
  - Observed evidence:
    - examples/05_execution_phases.py: asserts each phase_end payload `elapsed_seconds` is a nonnegative non-bool number and `duration_clock == "monotonic"`; asserts manifest timing duration_clock/elapsed_basis/interval_scope, nonnegative workload/startup/finalization/session, elapsed == workload, phases fit in workload; prints a plain-language explanation; keeps `[PASS] PASS: 05_execution_phases.py`.
    - Run (`cd examples && PYTHONPATH=../src python3 05_execution_phases.py; echo exit=$?`):
      ```
      Testing 05_execution_phases...
        What was measured (monotonic clock, so wall-clock changes cannot distort it):
          phase 'Dataset Initialization': 10.1 ms of your code
          phase 'Epoch Optimization': 13.0 ms of your code
          tracked workload (start() returned to stop() called): 24.2 ms
          pubrun startup capture, not part of the workload: 611.1 ms
          pubrun finalization before manifest.json, not part of the workload: 3.1 ms
        Time before pubrun.start() is outside the tracked interval and is not measured.
      [PASS] PASS: 05_execution_phases.py
      exit=0
      ```
      (Repeated runs reported workload 45 to 245 ms for 20 ms of phases; root-caused to defect backlog `uatvzh`, see V-04. The example's assertions hold regardless.)
    - manifest_excerpt.json validation (jsonschema 4.26.0, Draft202012Validator over `$defs.timing` with `$defs` attached):
      ```
      valid JSON; timing validates against $defs.timing
      disjoint sum 0.717 session 0.717
      ```
      UTC differences t1-t0=0.352, t2-t1=0.344, t3-t2=0.021 match the stated intervals.
    - Dash check: `examples/05_execution_phases.py: added=35 dash_lines=0`, `manifest_excerpt.json: added=16 dash_lines=0`, `examples/minimal-research-workflow/README.md: added=12 dash_lines=0`.
  - Result: pass

- [x] V-04 validates E-04
  - Required evidence: Pasted local non-publishing `benchmarks/harness.py` summary (with temp `--redacted-out` deleted afterward) and ephemeral timing-instrumentation microbenchmark output showing environment (without personal paths or hostnames), git revision, workload, baseline, repetitions (`N >= 30`), pass 1 cold versus pass 3 warm results, median, stdev, and IQR, plus diff of `docs/performance.md` preserving `#Representative results`, zero added em/en dashes, and `git status -s` confirming no stray or unredacted benchmark files remain.
  - Observed evidence:
    - Machine and environment were Linux 6.8.0-149-generic x86_64, CPython 3.14.6, Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz, 12 logical cores; get_filesystem: fstype=ext4 is_network=False; git af36c852546aafa843cf4838ff7071d7477cf439; pubrun 1.3.1; host shared and busy (load average 7 to 11).
    - Harness run `time python3 benchmarks/harness.py --passes 3 --iterations 30 --redacted-out /tmp/pubrun-timing-harness.redacted.json` -> exit=0, real 15m47.381s, "Running baseline (uncaptured) + 3 pass(es) x 29 scenarios x 30 iterations (+1 warmup each)". Summary from the redacted file (schema=pubrun-benchmark/5 git=af36c85 passes=3 iterations=30 warmup=1 total_wall_s=946.447), ms median/stdev/IQR, P1 cold | P3 warm, n=30:
      ```
      baseline-noop 17.42/2.18/2.52 | 19.15/2.01/3.55
      import-minimal 131.35/23.69/24.95 | 127.87/6.04/7.41
      import-auto 180.62/18.87/22.40 | 161.92/8.71/13.35
      startup-auto-default 554.11/55.61/46.92 | 528.14/17.82/21.78
      feature-baseline 235.85/15.15/10.71 | 236.14/11.74/16.26
      feature-none 382.23/11.83/14.95 | 369.95/33.39/21.38
      feature-hardware 388.08/19.08/19.33 | 415.96/46.46/49.91
      feature-packages-imported 713.94/26.79/31.61 | 749.90/38.33/54.29
      ```
      Then `rm -f /tmp/pubrun-timing-harness.redacted.json; ls ...` -> "No such file or directory"; `git status -s benchmarks/` empty.
    - Microbenchmark (/tmp/opencode/timing_microbench.py, uncommitted, REPS=30 PASSES=3 CALLS=100000 PHASES=1000 SLEEP=0.02, temp workdir removed: True), final run, median/stdev/IQR P1 cold | P3 warm:
      ```
      empty loop 100k (ms) 2.261/0.778/1.666 | 2.063/0.059/0.053
      perf_counter loop 100k (ms) 10.559/3.170/4.525 | 8.721/0.202/0.181
      perf_counter per call (ns) 82.5/25.4/40.8 | 66.6/2.0/1.8
      nullcontext 1k (ms) 0.266/0.091/0.014 | 0.273/0.065/0.011
      inactive phase 1k (ms) 108.618/16.503/14.305 | 106.176/27.167/10.964
      active phase 1k (ms) 38.401/7.553/11.343 | 18.592/2.659/0.423
      active minus nullcontext per phase (us) 38.14/7.53/11.33 | 18.32/2.66/0.44
      inactive minus nullcontext per phase (us) 108.35/16.47/14.29 | 105.91/27.12/10.97
      startup_overhead (ms) 22.287/3.802/6.300 | 21.321/8.829/4.683
      workload sleep(0.02) (ms) 20.091/0.738/0.017 | 20.099/0.534/0.028
      finalization_overhead (ms) 2.832/0.618/0.312 | 2.811/0.911/0.871
      hardware_wait (ms) 0.004/0.001/0.001 | 0.004/0.001/0.001
      background_hardware (ms) 22.092/1.834/2.369 | 21.449/1.438/2.717
      session (ms) 45.554/4.013/6.092 | 45.129/8.803/5.100
      writer_overhead (ms) 8.121/1.936/1.652 | 8.356/2.494/2.929
      ```
      Two earlier runs differed by up to ~2x in some warm medians (host load); disclosed in the doc.
    - Defects found and filed (no src/pubrun edits): `uatvzh` (pubrun-hw coalesced refresh holds `_run_lock` across an fsynced manifest write; stop() then blocks before t2: stop()-call-to-t2 on repo disk median 47.31 ms stdev 36.11 IQR 39.96 max 185.9 n=30 for a 20 ms workload, 0.02 ms under /tmp, 0.03 ms for a 500 ms workload; refresh write median 180.2 ms vs 7.4 ms under /tmp) and `oh0que` (inactive phase() resolves config per call, cProfile 0.207 of 0.215 s in resolve_config).
    - docs/performance.md: new `### Timing instrumentation and overhead separation` after the ckc3vl subsection (`### Startup, finalization, and artifact durability overhead` still at line 90, unchanged); `## Representative results` untouched (`git diff -U0 -- docs/performance.md` has no removed lines); no speedup claimed; known-exception note cites `uatvzh`. Dash check `docs/performance.md: added=58 dash_lines=0`.
    - `git status -s` after benchmarks: only the 8 scope files modified, plus the filed backlog items; no benchmark files.
    - Attempt 2 re-confirmation on base `c050886cba9f88d11d59b71158b6c1206cb48ae1` (same microbenchmark, same machine, 23.4 s, temporary workdir removed: True), warm Pass 3 median / stdev / IQR: perf_counter per call 70.4 / 30.1 / 59.4 ns; active phase minus nullcontext 22.33 / 5.44 / 3.47 us; inactive phase minus nullcontext 117.10 / 28.39 / 5.14 us; startup_overhead 22.894 / 3.669 / 4.130 ms; workload sleep(0.02) 20.097 / 0.024 / 0.009 ms; finalization_overhead 3.081 / 0.187 / 0.240 ms; session 46.310 / 3.650 / 4.009 ms. These fall within the run-to-run spread the doc already discloses, so `docs/performance.md` keeps its numbers, which are labeled with the revision they were measured at (`af36c85`). The 16-minute harness was not re-run.
  - Result: pass

- [x] V-05 validates E-05
  - Required evidence: Pasted actual runner output and exit code 0 for `pytest tests/ -v`, `python3 examples/verify_all.py`, and `python3 scripts/sanitize_paths.py --check --all`, `git status -s` confirming no stray benchmark files, plus an explicit note recording the GitHub Actions `.github/workflows/ci.yml` OS/Python CI matrix gate required before release closure.
  - Observed evidence:
    - `python3 -m pytest tests/ -v -p no:cacheprovider` (serial, worktree; pyproject pythonpath=src) -> exit=0:
      ```
      platform linux -- Python 3.14.6, pytest-8.2.2, pluggy-1.6.0
      TOTAL                                  15558   3642    77%
      ================= 1492 passed, 2 skipped in 513.46s (0:08:33) ==================
      ```
      Skipped: tests/test_status.py::TestStatusScan::test_scan_running_run, tests/test_status.py::TestCleanRuns::test_clean_does_not_delete_running.
    - `aw suite` (xdist) earlier: `FAILED tests/test_liveness.py::TestIsSameProcess::test_expected_script_matches` / `1 failed, 1493 passed in 176.16s`. Reproduced only with `-n 2` (serial 15/15 pass): an xdist worker's /proc cmdline is `python3 -u -c import sys;exec(eval(sys.stdin.readline()))` with no "pytest". Pre-existing test-environment defect unrelated to this plan's doc/example edits; filed backlog `sd7kvt`.
    - `PYTHONPATH=../src python3 verify_all.py` (in examples/) -> exit=0, 13 `[PASS] PASS:` lines (00 through 12) and `[SUCCESS] All examples passed.` (also ran minimal-research-workflow/analysis.py).
    - verify_all left an untracked `examples/outputs/` (analysis.py writes ./outputs relative to cwd; .gitignore covers only examples/minimal-research-workflow/outputs/). Removed it; filed backlog `g2434y`.
    - `python3 scripts/sanitize_paths.py --check --all` -> no output, `sanitize-exit=0`.
    - `git status -s` final: only the 8 Scope-Paths files (M) and the 4 new backlog items (uatvzh, oh0que, sd7kvt, g2434y); no stray benchmark or temp files.
    - CI matrix gate: `.github/workflows/ci.yml` (Ubuntu, Windows, macOS x Python 3.8 through 3.14) has NOT been run for this change (lane never pushes); it must pass in GitHub Actions before release closure of Set timing-acc.
    - Attempt 2 re-validation (2026-11-22, lane `aw/lane/3tvesf_attempt2`, base `c050886cba9f88d11d59b71158b6c1206cb48ae1`, which adds `m780uj` and `kqzd15` on top of attempt 1's base; attempt 1's diff applied cleanly):
      - `python3 -m pytest tests/ -v -p no:cacheprovider` -> exit=0:
        ```
        platform linux -- Python 3.14.6, pytest-8.2.2, pluggy-1.6.0
        TOTAL                                  15675   3612    77%
        ================= 1569 passed, 2 skipped in 490.68s (0:08:10) ==================
        ```
        Skipped: the same two tests in tests/test_status.py as in attempt 1.
      - `aw suite` (xdist): `FAILED tests/test_liveness.py::TestIsSameProcess::test_expected_script_matches` / `1 failed, 1570 passed in 170.34s (0:02:50)`; `python3 -m pytest tests/test_liveness.py -n 2 -q` reproduces it (`1 failed, 26 passed in 6.10s`). Same pre-existing defect `sd7kvt`; this plan changes no `src/` or `tests/` file.
      - `PYTHONPATH=../src python3 verify_all.py` (in examples/) -> exit=0, 13 `[PASS] PASS:` lines, `[SUCCESS] All examples passed.`; it again left `examples/outputs/` (defect `g2434y`), which was removed.
      - `python3 scripts/sanitize_paths.py --check --all` -> no output, `sanitize-exit=0`.
      - `git status -s` before commit: the 8 Scope-Paths files and this plan (M), the 4 backlog items (new); no benchmark or temporary files.
  - Result: pass

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Open questions: all open questions (`OQ-01`) are resolved for review; do not execute until prerequisites `e1fwy2` (manifest timing schema and tracker monotonic lifecycle), `8co0wy` (monotonic phase, subprocess, and resource timing), and `vrr1fv` (reports, status, diff, and TUI timing semantics) are `executed` and a human approves this plan (`- Status: approved`).
2. Scope declaration: expected modified files are `- Scope-Paths:` (`docs/manifest.md`, `docs/architecture.md`, `docs/functional_spec.md`, `docs/api.md`, `docs/performance.md`, `examples/05_execution_phases.py`, `examples/minimal-research-workflow/manifest_excerpt.json`, `examples/minimal-research-workflow/README.md`). If execution genuinely requires editing an out-of-scope file, justify it with `--scope-reason` at finalization; if a declared file requires no edit, acknowledge it with `--scope-ack`. Stop only for a genuinely unsafe condition such as an unresolvable concurrent-edit conflict or missing prerequisite behavior.
3. Honesty rule (HARD MUST): paste actual runner output and exit codes for `pytest`, `examples/verify_all.py`, `scripts/sanitize_paths.py`, `benchmarks/harness.py`, and the local timing microbenchmark into each `V-*` `Observed evidence:` field; never claim results you did not measure or run.
4. Commit and push discipline: commit only the files changed for this plan using `aw commit 3tvesf -- <paths>`; never use `git add -A`, `git add .`, or `git commit -a`; never push or publish benchmark results without explicit human instruction.
5. Lifecycle transition on completion: this plan must reach `.aw/records/plans/executed/` with `- Status: executed` through `aw ipd finalize` once all `E-*` items are `performed` and all `V-*` items are `pass`. In a runner-managed lane with `self_finalize=True`, leave lifecycle finalization to the runner's post-turn finalize step; in standalone execution, run `aw ipd finalize 3tvesf` directly. Never hand-roll a raw `git mv` to `.aw/records/plans/executed/`.
