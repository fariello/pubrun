# IPD: Capture Failure Isolation and Transactional Hook Rollback

- Date: 2026-11-21
- Kind: orchestrator
- Concern: Per-engine capture failure isolation, narrow ghost-mode boundary, transactional hook ownership and rollback, independent finalization cleanup, honest partial-manifest reporting, and measured isolation overhead.
- Scope: Full-Set coordination for backlog item `x21s6w` across capture-engine hook ownership and safe error redaction, tracker per-engine isolation and narrow ghost-mode rollback, partial-manifest diagnostics and consumer honesty, overhead measurement, documentation reconciliation, and whole-Set verification.
- Scope-Paths: .aw/records/plans/pending/20261121-cap-isolation-00-frzw20-capture-failure-isolation-and-transactional-hook-rollback.ipd.md
- Item-Dependencies: none
- Status: executed
- Readiness: go-pending-approval
- Review-Depth: orchestrator
- Coverage: pass
- Coverage-Fingerprint: 532708cecd6d2b0a5b2bde61ce6168cf653d7f530444431213c8763871a25a63
- Coverage-Checked: 2026-11-22 by uri/its_direct/pt3-claude-opus-5.5-1m-us
- Short-Description: Coordinate hook ownership rollback, tracker failure isolation, partial-manifest consumers, overhead measurement, and docs
- Work-Kind: bug
- Priority: high
- From-Backlog: x21s6w
- Blocks-Release: next
- Set: cap-isolation
- Order: 0
- Highest E allocated: 04
- Author: agent
- Id: frzw20

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-22 executed (aw agy run model=claude-opus-5-5-medium): RETIRED as the orchestrator rollup step of a runner Set completion, not executed by an agent: every child of Set cap-isolation reached executed, so the runner (run run-20261122T143534Z-3922406) retired this Order-0 plan as bookkeeping. Its own E-*/V-* items were NOT performed; the runner superseded them by enforcing the ordering, the isolation and the per-child merge gate. Justifying children: p6pon8, ed0yds, 26euz0, zp2yyu.
- 2026-11-22 approved (aw set): status set to approved
- 2026-11-22 /plan-review (Gemini 4 Neon (High)): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004
- 2026-11-22 coverage pass (aw oc run): fingerprint 532708cecd6d, model uri/its_direct/pt3-claude-opus-5.5-1m-us
- 2026-11-22 coverage pass (aw oc run): fingerprint 20cdcee01e70, model uri/its_direct/pt3-claude-opus-5.5-1m-us
- 2026-11-22 draft (agent): created.
- 2026-11-22 to-review (agent): authored review-ready orchestrator plan graduating backlog item `x21s6w` into Set `cap-isolation` with four child plans (`p6pon8`, `ed0yds`, `26euz0`, `zp2yyu`).

## Goal

Graduate open backlog item `x21s6w` (isolate capture failures and roll back partially installed hooks) into four bounded, verifiable child Implementation Plan Documents (IPDs). Together, the four child plans isolate individual capture-engine failures into honest partial manifests, restrict ghost mode to genuinely unusable run output, enforce transactional hook installation and ownership-guarded rollback across process-global hooks and background workers, and run finalization cleanup steps independently. They also surface partial capture honestly in diagnostic consumers and documentation, and measure isolation overhead with reproducible local benchmarks.

### Set structure and execution sequence

The child table and text below are normative. These diagrams summarize the execution sequence and entity relationships in Set `cap-isolation`.

```mermaid
flowchart TD
    A["p6pon8: Safe Diagnostic Redaction and Hook Ownership Rollback Across Capture Engines"] --> B["ed0yds: Tracker Per-Engine Failure Isolation Narrow Ghost Mode and Independent Finalization"]
    B --> C["26euz0: Partial Manifest Diagnostics Inspect Findings and Methods Honesty"]
    A --> D["zp2yyu: Isolation Overhead Measurement Documentation Reconciliation and Whole-Set Verification"]
    B --> D
    C --> D
```

```mermaid
erDiagram
    BACKLOG_X21S6W ||--|| ORCHESTRATOR_FRZW20 : graduates_to
    ORCHESTRATOR_FRZW20 ||--|| CHILD_P6PON8 : coordinates
    ORCHESTRATOR_FRZW20 ||--|| CHILD_ED0YDS : coordinates
    ORCHESTRATOR_FRZW20 ||--|| CHILD_26EUZ0 : coordinates
    ORCHESTRATOR_FRZW20 ||--|| CHILD_ZP2YYU : coordinates
```

## Detailed Implementation Checklist (TODO)


> Its own E-*/V-* items were NOT performed; the runner superseded them by enforcing the ordering, the isolation and the per-child merge gate.

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Confirm child IPD completion

- [ ] E-01 CONFIRM p6pon8 REACHED executed
  - Depends on: none
  - Expected outcome: Child plan `p6pon8` is moved to `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` items marked `performed`, and all `V-*` items marked `pass`.
  - Execution state: pending

- [ ] E-02 CONFIRM ed0yds REACHED executed
  - Depends on: E-01
  - Expected outcome: Child plan `ed0yds` is moved to `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` items marked `performed`, and all `V-*` items marked `pass`.
  - Execution state: pending

- [ ] E-03 CONFIRM 26euz0 REACHED executed
  - Depends on: E-02
  - Expected outcome: Child plan `26euz0` is moved to `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` items marked `performed`, and all `V-*` items marked `pass`.
  - Execution state: pending

- [ ] E-04 CONFIRM zp2yyu REACHED executed
  - Depends on: E-01, E-02, E-03
  - Expected outcome: Child plan `zp2yyu` is moved to `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` items marked `performed`, and all `V-*` items marked `pass`.
  - Execution state: pending

## Child IPDs, sequence, and dependencies

| Order | Id | File | What it does | Depends on |
|---|---|---|---|---|
| 01 | `p6pon8` | `20261121-cap-isolation-01-p6pon8-safe-diagnostic-redaction-and-hook-ownership-rollback-across.ipd.md` | Adds bounded, redacted diagnostic formatting (`src/pubrun/capture/redaction.py::format_safe_error_detail`), implements transactional install, live pre-existing wrapper chaining, generation-tagged subprocess tracking, and ownership-guarded uninstall across `SubprocessSpy`, `ConsoleInterceptor` (including `faulthandler.is_enabled()` preservation), `SignalExitCapture` (including closure-captured `sys.excepthook` and redacted `_exit_exception`), and `ResourceWatcher`, hardens fallback redaction in `src/pubrun/capture/invocation.py::get_invocation`, and verifies third-party wrapper preservation and rollback in `tests/test_hook_ownership_rollback.py`. | none |
| 02 | `ed0yds` | `20261121-cap-isolation-02-ed0yds-tracker-per-engine-failure-isolation-narrow-ghost-mode-and-i.ipd.md` | Extends `$defs.error_record` additively in `schemas/manifest.schema.json`, isolates every capture engine call in `src/pubrun/tracker.py::Run` (including `resolve_console_mode()`, `set_poll_timeout()`, `_hardware_thread.start()`, and independent `hardware`, `host`, and `filesystem` blocks), narrows ghost mode to unusable output with `_run_lock`-latched transactional rollback of owned hooks, executes every pre-teardown and cleanup step independently in `Run._finalize_state()`, bounds runtime input/output (I/O) warnings in `EventStream` and `ArtifactWriter`, guards ghost-run and import-mode paths in `src/pubrun/core.py` and `Run._merge_and_migrate()`, populates `_errors_lock`-protected `errors.records` (capped at `MAX_CAPTURE_ERRORS = 50`) and honest `capture.capture_state`, updates `tests/test_tracker.py` and `tests/test_manifest_schema.py`, and adds fault-injection coverage in `tests/test_capture_isolation.py`. | 01 |
| 03 | `26euz0` | `20261121-cap-isolation-03-26euz0-partial-manifest-diagnostics-inspect-findings-and-methods-ho.ipd.md` | Makes `pubrun report` (`src/pubrun/report/diagnostics.py::print_report`, including `section="env"` and `section="packages"` extracts and `NO_COLOR`), `pubrun inspect` (`src/pubrun/report/checks.py::manifest_findings`, including deduplicated `capture-error` warnings and compatibility with sibling plan `0b8i7x`), and `pubrun methods` (`src/pubrun/report/methods.py::generate_report` and `generate_report_multi` across all runs with escaped LaTeX underscores) safe and honest on partial manifests, and verifies them in `tests/test_reports.py`, `tests/test_checks_commands.py`, and `tests/test_edge_cases.py`. | 02 |
| 04 | `zp2yyu` | `20261121-cap-isolation-04-zp2yyu-isolation-overhead-measurement-documentation-reconciliation.ipd.md` | Measures startup and hot-path overhead of capture isolation locally against a pre-`p6pon8` baseline (`benchmarks/harness.py --passes 2 --iterations 20 --redacted-out <temp_path>` plus an ephemeral micro-benchmark in a cleaned-up temporary Git worktree) with full environment, revision, workload, repetitions, cold/warm passes, and dispersion; reconciles `docs/architecture.md`, `docs/functional_spec.md`, `docs/manifest.md`, `docs/api.md`, and `docs/performance.md` (preserving `## Representative results` and adding zero em/en dashes); and runs whole-Set verification across tests, examples, and path sanitization. | 01, 02, 03 |

## Completion criteria (the whole Set is done only when)

- Every process-global hook and background worker (`SubprocessSpy`, `ConsoleInterceptor` including `faulthandler.is_enabled()` ownership preservation, `SignalExitCapture` including closure-captured `sys.excepthook` and redacted `_exit_exception`, and `ResourceWatcher`) installs transactionally and rolls back only resources owned by the failing run. Teardown restores prior handlers and wrappers without removing later third-party wrappers, flips remaining wrappers into passive passthrough, isolates cross-run `Popen` and concurrent `os.system` records, runs cleanup steps independently, and formats failure details through bounded, redacted diagnostics with no raw secrets or traceback spam. Owner: `p6pon8`.
- Fault injection into each individual capture engine (`invocation`, `git`, `process`, `python`, `packages`, `environment`, `hardware`, `host`, `filesystem`, `subprocesses`, `console`, `events`, `resources`, `signals`) preserves unrelated healthy sections and preserves the host script's normal result and exit code. Each failed section records `capture_state.status == "failed"` plus bounded, redacted `errors.records` entries (capped at `MAX_CAPTURE_ERRORS = 50`, protected by `_errors_lock`, without requiring the failed subsystem), sets `capture.capture_state.status == "partial"` (for both escaping exceptions and self-caught failed returns), and writes a schema-valid partial manifest when storage is writable. Genuine output failure at startup latches `_finalized` under `_run_lock`, rolls back all owned hooks without leaking threads or open file handles, and enters documented ghost mode. Owner: `ed0yds`.
- Behavioral tests verify cleanup isolation (including `SubprocessSpy.finalize_all()` separated from `uninstall(owner=...)`), idempotence, reference counting, concurrent stop and background writes, finalized-manifest race protection, second cleanup failures, output loss or read-only storage at startup and mid-run, nested runs (including ghost-run `_merge_and_migrate()` guards), multiple `stop()` calls, automatic `atexit` exit, slow background workers, and all six import modes (`auto`, `full`, `noauto`, `nopatch`, `noconsole`, `minimal`). Owner: `ed0yds`.
- Downstream consumers (`pubrun report`, `pubrun inspect`, `pubrun methods`, and `pubrun status`) tolerate partial manifests with failed, null, or non-dict section fields without crashing across single-run, multi-run (`manifests[1:]`), and `section="env"`/`"packages"` paths while respecting `NO_COLOR` and sibling plan `0b8i7x` compatibility. They surface failed sections and deduplicated `capture-error` records explicitly (distinct from `"suppressed"`), escape LaTeX underscores in disclosures, and do not claim complete capture or standard-library-only dependencies when a section failed. Owner: `26euz0`.
- Local startup and hot-path overhead from capture isolation is measured against a pre-`p6pon8` baseline with recorded environment, Git revisions, workloads, repetitions, cold and warm passes, and dispersion, leaving zero temporary worktrees or benchmark artifacts behind. Documentation (`docs/architecture.md`, `docs/functional_spec.md`, `docs/manifest.md`, `docs/api.md`, and `docs/performance.md`) matches the implemented behavior, preserves `## Representative results` as a multi-machine placeholder, and introduces zero em or en dashes in edited lines. Whole-Set verification (`pytest tests/ -v`, `python3 examples/verify_all.py`, and `python3 scripts/sanitize_paths.py --check --all`) passes with exit code 0. Owner: `zp2yyu`.

## Cross-IPD validation

- Hook ownership to tracker integration check: child `p6pon8` verifies per-engine transactional install, rollback, and third-party wrapper preservation in isolation; child `ed0yds` exercises those exact engine APIs through `Run.__init__()`, `Run._rollback_owned_hooks()`, `Run._finalize_state()`, and `Run.stop()` under fault injection and output-loss scenarios.
- Partial-manifest producer-to-consumer check: child `ed0yds` validates real partial manifests containing failed sections and `errors.records` against `schemas/manifest.schema.json` in `tests/test_manifest_schema.py`; child `26euz0` feeds real partial manifests produced by isolated engine failures into `pubrun report`, `pubrun inspect`, `pubrun methods`, and `pubrun status`.
- Whole-Set regression, documentation, and benchmark check: child `zp2yyu` runs the full test suite (`pytest tests/ -v`), `python3 examples/verify_all.py`, `python3 scripts/sanitize_paths.py --check --all`, `git status --short`, the diff-scoped em/en dash check, and the local isolation-overhead measurement against the pre-`p6pon8` baseline after `p6pon8`, `ed0yds`, and `26euz0` are executed.

## Deferred / out of scope (with reason)

- Monotonic timing intervals belong to sibling Set `timing-acc` (orchestrator `nr63qr`, backlog item `6hp1zu`). Child `ed0yds` preserves any monotonic timing anchor calls (`_mark_finalization_end()`) if present, keeping both Sets independently executable.
  - Carrier: nr63qr
- Startup commit-identity optimization and snapshot durability/write coalescing belong to sibling Set `startup-perf` (orchestrator `9ppa0r`, backlog item `t1xqpw`). Child `ed0yds` preserves any `_write_lock`, `durability`, `is_refresh`, or `hardware.depth == "off"` fast path if present, keeping both Sets independently executable.
  - Carrier: 9ppa0r
- Dependency capture accuracy (backlog item `w4hxkh`, Set `dep-capture`, orchestrator `6s7k9e`) is unrelated and remains out of scope.
  - Carrier: 6s7k9e
- Reproducibility preflight (backlog item `q3bll1`, Set `repro-check`, orchestrator `osjxbz`) is unrelated and remains out of scope; child `26euz0` preserves compatibility if sibling plan `0b8i7x` lands first.
  - Carrier: osjxbz
- File provenance (backlog item `x6alw4`, Set `file-prov`, orchestrator `vtkkn1`) is unrelated and remains out of scope.
  - Carrier: vtkkn1
- Multi-operating-system and multi-Python Continuous Integration (CI) matrix execution (`ubuntu-latest`, `ubuntu-24.04`, `windows-latest`, `macos-latest` across Python 3.8 through 3.14 in `.github/workflows/ci.yml`) runs in GitHub Actions after local work lands and is recorded by child `zp2yyu` as a required post-merge release gate.
  - Carrier-Declined: executed automatically by GitHub Actions CI (.github/workflows/ci.yml) on pull request or push; unavailable in a single local Linux worktree.
- External benchmark submission, GitHub Gist creation, and High-Performance Computing (HPC) scheduler job submission are out of scope and prohibited without explicit maintainer authorization.
  - Carrier-Declined: prohibited by policy without explicit maintainer authorization.

## Scope check

- Over-scope: none. Every child plan maps directly to the capture-isolation, transactional rollback, independent cleanup, bounded-warning, consumer-honesty, documentation, and overhead-measurement requirements of backlog item `x21s6w`.
- Under-scope: none. Every requirement and acceptance criterion in `x21s6w` is assigned to a named child plan (`p6pon8`, `ed0yds`, `26euz0`, or `zp2yyu`).

## Required tests / validation

This orchestrator plan runs no tests directly. Whole-Set validation is performed by its child plans:

- Child `p6pon8` runs `pytest tests/test_hook_ownership_rollback.py tests/test_signals.py tests/test_capture.py tests/test_resources.py tests/test_redaction.py tests/test_quality.py tests/test_edge_cases.py tests/test_pause_resume.py -v` and `pytest tests/test_cli.py -k "faulthandler or excepthook" -v`.
- Child `ed0yds` runs `pytest tests/test_capture_isolation.py tests/test_tracker.py tests/test_writer.py tests/test_events.py tests/test_import_modes.py tests/test_manifest_schema.py tests/test_quality.py -v`.
- Child `26euz0` runs `pytest tests/test_reports.py tests/test_methods_multi.py tests/test_show_sections.py tests/test_example_minimal_research_workflow.py tests/test_checks_commands.py tests/test_edge_cases.py tests/test_status.py -v`.
- Child `zp2yyu` runs `pytest tests/ -v`, `python3 examples/verify_all.py`, `python3 scripts/sanitize_paths.py --check --all`, `git status --short`, the diff-scoped em/en dash check over the five updated docs, and the local isolation-overhead measurement (`python3 benchmarks/harness.py --passes 2 --iterations 20 --redacted-out <temp_path>` plus an ephemeral micro-benchmark comparing against a cleaned-up pre-`p6pon8` baseline worktree).

## Open questions

### OQ-01: Additive manifest fields for structured capture-error records

- Blocking: no
- Status: resolved
- Owner: plan author (binding upon plan approval)
- Resolution or deferral rationale: Backlog item `x21s6w` states that new API or schema names are proposals rather than pre-approved contracts and directs reusing existing section `capture_state` fields. Child `ed0yds` reuses existing `capture_state` (`status = "failed"`, bounded redacted `detail`) on each section, sets `capture.capture_state.status = "partial"` when any section fails, and populates the existing `errors.records` array (`kind = "capture-error"`, `traceback = null`, capped at `MAX_CAPTURE_ERRORS = 50`) with two optional additive fields (`section`, `stage`) on `$defs.error_record` in `schemas/manifest.schema.json`. Existing manifests remain valid, and the maintainer may rename or omit `section`/`stage` during review before approving `ed0yds`.

### OQ-02: Ownership rule when a third-party library wraps a global hook after `pubrun`

- Blocking: no
- Status: resolved
- Owner: plan author (binding upon plan approval)
- Resolution or deferral rationale: When a third-party wrapper sits outside `pubrun`'s installed hook (`sys.stdout`, `sys.stderr`, `sys.excepthook`, a signal handler, `subprocess.Popen.__init__`, `subprocess.Popen.wait`, or `os.system`), restoring the earlier target blindly would break the third-party wrapper. Child `p6pon8` follows the existing identity-guarded restoration rule already established for `sys.stdout`/`sys.stderr` (`tests/test_quality.py::TestConsoleRestoreSafety.test_stop_preserves_third_party_wrapper`) and `sys.excepthook` (`src/pubrun/capture/signals.py::SignalExitCapture._restore_excepthook`, edge case EC-15, verified by `tests/test_edge_cases.py::TestExcepthookRestore`): restore only when the current global target is still `pubrun`'s own installed wrapper; otherwise leave the third-party wrapper intact and flip `pubrun`'s wrapper into passive passthrough mode so it stops recording and leaks no state.

## Validation and cross-check (verify before reporting the Set complete)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition) (as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Path `.aw/records/plans/executed/20261121-cap-isolation-01-p6pon8-safe-diagnostic-redaction-and-hook-ownership-rollback-across.ipd.md` exists, shows `- Status: executed`, has all `E-*` items `performed` and all `V-*` items `pass`, and `aw ipd lint --phase post-transition` exits 0 on it.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Path `.aw/records/plans/executed/20261121-cap-isolation-02-ed0yds-tracker-per-engine-failure-isolation-narrow-ghost-mode-and-i.ipd.md` exists, shows `- Status: executed`, has all `E-*` items `performed` and all `V-*` items `pass`, and `aw ipd lint --phase post-transition` exits 0 on it.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Path `.aw/records/plans/executed/20261121-cap-isolation-03-26euz0-partial-manifest-diagnostics-inspect-findings-and-methods-ho.ipd.md` exists, shows `- Status: executed`, has all `E-*` items `performed` and all `V-*` items `pass`, and `aw ipd lint --phase post-transition` exits 0 on it.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Path `.aw/records/plans/executed/20261121-cap-isolation-04-zp2yyu-isolation-overhead-measurement-documentation-reconciliation.ipd.md` exists, shows `- Status: executed`, has all `E-*` items `performed` and all `V-*` items `pass`, and `aw ipd lint --phase post-transition` exits 0 on it.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

This orchestrator plan coordinates Set `cap-isolation` (`p6pon8`, `ed0yds`, `26euz0`, `zp2yyu`) and executes no application code directly.

Execution contract:
1. Open questions: all open questions (`OQ-01`, `OQ-02`) are resolved for review and become binding upon human approval of this Set (`- Status: approved`).
2. Scope declaration: this orchestrator declares only its own plan file as `- Scope-Paths:` for lifecycle retirement; it executes no application code and adds no non-confirmation checklist items.
3. Honesty rule (HARD MUST): confirm child completion only by inspecting the executed child plan files on disk and running `aw ipd lint --phase post-transition`, pasting actual runner output and exit codes into each `V-*` `Observed evidence:` field; never claim a child reached `executed` without verifying its file state.
4. Commit and push discipline: retire this orchestrator via `aw commit` path-scoped to its moved plan file (or let the `aw` runner retire it); never use `git add -A`, `git add .`, or `git commit -a`; never push without explicit human instruction.
5. Lifecycle transition on completion: once all four child plans (`p6pon8`, `ed0yds`, `26euz0`, `zp2yyu`) reach `executed` on disk, this orchestrator must reach `.aw/records/plans/executed/` with `- Status: executed` through `aw ipd finalize`. Under an `aw` runner, the runner automatically retires the orchestrator once every child is `executed` and coverage passes; in standalone execution, run `aw ipd finalize frzw20` directly. Never hand-roll a raw `git mv` to `.aw/records/plans/executed/`.
