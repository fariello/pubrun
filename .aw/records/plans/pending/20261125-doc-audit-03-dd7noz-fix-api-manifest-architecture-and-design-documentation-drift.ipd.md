# IPD: Fix API, manifest, architecture, and design documentation drift

- Date: 2026-11-25
- Kind: child
- Concern: `docs/api.md`, `docs/manifest.md`, `docs/architecture.md`, and `docs/design/` contain high-impact contract errors including a phantom top-level `profiling` manifest section, a mismatched `redacted_value` hashed format, `python.virtual_env` documented as a path, deprecated `profile=` API examples, a false `pubrun inspect --json` vs `assess_run()` claim, and stale module trees and Phase-0 design status.
- Scope: `docs/api.md`, `docs/manifest.md`, `docs/architecture.md`, `docs/design/file-io-provenance-evaluation.md`, and `docs/design/tomli-dependency-decision.md`.
- Scope-Paths: docs/api.md, docs/manifest.md, docs/architecture.md, docs/design/file-io-provenance-evaluation.md, docs/design/tomli-dependency-decision.md
- Item-Dependencies: none
- Status: to-review
- Short-Description: Fix phantom manifest sections, deprecated profile examples, API behavioral errors, architecture layout, and design banners
- Work-Kind: chore
- Priority: high
- Set: doc-audit
- Order: 3
- Highest E allocated: 05
- Author: Antigravity
- Id: dd7noz

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 to-review (aw set): Authored from /assess-documentation
- 2026-11-25 /assess documentation (Antigravity): assessed; proposed 5 documentation fixes (23 verified findings across API, manifest, architecture, and design docs)
- 2026-11-25 draft (Antigravity): created.

## Goal

Align `docs/api.md`, `docs/manifest.md`, `docs/architecture.md`, and `docs/design/` with the live Python API (`src/pubrun/__init__.py`, `core.py`, `tracker.py`), capture modules, and `schemas/manifest.schema.json` (honestly noting schema/runtime divergences where runtime and schema disagree).

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix `docs/api.md`

- [ ] E-01 Fix all verified inaccuracies and omissions in `docs/api.md` (with no em or en dashes in added or edited lines):
  - Replace deprecated, inert `profile="deep"` / `profile="basic"` / `core={"profile": "deep"}` in primary examples with active overrides (`capture={"hardware": {"depth": "deep"}}`, `console={"capture_mode": "standard"}`, or `output_dir=...`), and mark `profile` in the flat-shortcuts list as deprecated/inert (emits `profile_deprecated` notice).
  - Rewrite the false claim that `pubrun inspect --json` merges `file_provenance_*` findings omitted by `assess_run()`: state that `assess_run()` itself emits all five canonical `file_provenance_*` codes in `inputs_outputs` (`src/pubrun/report/reproducibility.py::assess_manifest_reproducibility`), matching `pubrun inspect --json`.
  - Fix inactive-run behavior for `phase()`, `register_file()`, `register_input()`, and `register_output()`: all four obey `[events].on_inactive_annotate` (`"ignore"` default, `"warn"`, or `"error"` raising `RuntimeError`); update `## API Summary` rows to `Yes (configurable)`.
  - Fix `stop()`, `tracked_run()`, and `audit_run()` outcome rules (automatic unhandled-exception and non-zero `sys.exit()` detection in `tracker.py`; `_classify_exit_outcome()` maps `KeyboardInterrupt` to `"interrupted"`, `SystemExit(0)`/`None` to `"completed"`, and other exceptions / non-zero `SystemExit` to `"failed"`); document bare `@audit_run` (`audit_run(func=None, **overrides)`).
  - Add `__version__` and `__commit__` exports, add `paused()` to `## API Summary` and `## Threading Model`, add `subprocess.Popen(...)` to the subprocess summary row, add `sys.exit (SignalExitCapture)` to `Third-Party Hook Ownership Rules`, and fix `should_fail_strict(a, *, fail_on="warn")` keyword-only signature.
  - Depends on: none
  - Expected outcome: Every exported symbol, signature, example, hook rule, and behavioral claim in `docs/api.md` matches `src/pubrun/`.
  - Execution state: pending

### Task group 2: Fix `docs/manifest.md`

- [ ] E-02 Fix high-severity contract errors in `docs/manifest.md` (with no em or en dashes in added or edited lines):
  - Remove `## profiling` as a top-level `manifest.json` section (replace with a note explaining that phase profiling writes `profile-<phase>.prof` files in `run_dir` and emits `profile_saved` events in `events.jsonl`, and does not add a top-level key to `manifest.json`, which enforces `additionalProperties: false`).
  - Update `redacted_value` to document all five representations (`plain`, `redacted`, `hashed`, `suppressed`, `unavailable`), show the actual runtime hashed payload emitted by `src/pubrun/capture/redaction.py::redact_value` (`{"representation": "hashed", "hash_algorithm": "sha256", "hash_value": "<hex>"}`), and add a brief note flagging the known schema divergence in `schemas/manifest.schema.json` (`$defs.redacted_value` currently defines `hash: {algorithm, value}`).
  - Fix `python.virtual_env` to state it emits the literal string `"venv"` when inside a virtual environment or `null` otherwise (pointing to `prefix` for the path and `environment_kind`/`in_venv` for richer classification).
  - Add `"running"` (startup/in-progress manifests), `"crashed"` (written by `pubrun status` closeout, noting it is not yet in the schema enum), and `"partial"` to `status.outcome`.
  - Depends on: none
  - Expected outcome: `docs/manifest.md` contains no phantom top-level sections and truthfully describes `redacted_value`, `python.virtual_env`, and `status.outcome`.
  - Execution state: pending

- [ ] E-03 Fix medium- and low-severity field accuracy in `docs/manifest.md` (with no em or en dashes in added or edited lines):
  - Clarify `capture.console_capture_mode` records the configured `[console].capture_mode`, while `console.capture_mode` records the resolved effective mode.
  - Fix `invocation.script`: `path` is the path as invoked (not necessarily absolute), add `real_path` (`string | null`) and `ctime` (`float | null`), and note the 1 MiB `sha256` skip (`sha256_skipped`).
  - Fix `console` section: document required `captured` boolean and nullable `path`/`lines_captured` on `stdout`, `stderr`, and `combined`, and mention `"partial"` and `"failed"` finalized `capture_state.status` values.
  - Fix `Meta Snapshot`: clarify that meta snapshots include `timing.started_at_utc` for staleness checks (while omitting run-specific fields like `invocation`, `status`, `console`, `resources`), add `host` to hydrable sections (`HYDRABLE_SECTIONS`), and mention `diff` and legacy `report` alongside `inspect`/`show`/`methods`/TUI.
  - Fix `subprocesses[].cwd` type to `string | null` (populated only when `cwd=` was passed to `Popen`), add a `hardware.gpus[]` sub-table (`vendor`, `model`, `memory_total_bytes`, `driver_version`, optional `clock_speed_mhz`), add `| null` to nullable columns (`process.user.uid`/`gid`, `git.repo_root`/`commit`/`branch`/`dirty`, `resources.peak_rss_bytes`/`end_rss_bytes`/`peak_cpu_percent`), mention `register_file`/`register_input`/`register_output` under `capture.file_provenance_available`, and add a one-line note for reserved schema-only top-level keys (`artifacts`, `determinism`, `extensions`).
  - Depends on: E-02
  - Expected outcome: All manifest section tables in `docs/manifest.md` match live runtime output and `schemas/manifest.schema.json`.
  - Execution state: pending

### Task group 3: Fix `docs/architecture.md` and `docs/design/`

- [ ] E-04 Update `docs/architecture.md` to match the live package and manifest architecture (with no em or en dashes in added or edited lines):
  - Replace stale `Status: v1.0.0` header with `Status: Current (schema v1.0)`.
  - Add `"filesystem"`, `"pubrun_imports"`, and `"data_files"` to the Section 5 Manifest Design skeleton, and add `Filesystem`, `File I/O`, and `Profiling` rows (plus `"off"` mode notes for `Packages` and `Environment`) to Section 10 Capture Categories.
  - Update Section 6 Event Model to list all 9 emitted event types (`annotation`, `phase_start`, `phase_end`, `resource_sample`, `profile_saved`, `input_dataset`, `output_artifact`, `mixed_dataset`, `warning`), noting critical vs buffered flushing.
  - Fix run directory path template to `<output_dir>/pubrun-<script>-<timestamp>-<pid>-<run_id>/` (defaulting `<output_dir>` to `./runs`) and list `.pubrun.lock` (while active) and `profile-<phase>.prof` (when profiling enabled).
  - Update Section 16 Public API (align with `__all__` or frame as core lifecycle primitives linking `docs/api.md`), add `sys.exit` to Section 18 Failure Model, and update Section 21 System Components to reflect the current `src/pubrun/` layout (`capture/`, `analysis/`, `report/`, `tui/`, mode submodules, `status.py`, `__main__.py`) and primary CLI commands (`show`, `inspect`, `self-check`, `bench`, `ui`, `init`, `combined`, `res`/`cpu`/`mem`, `cite`, `report-bug`).
  - Depends on: none
  - Expected outcome: `docs/architecture.md` accurately reflects the current repository modules, manifest shape, event types, and CLI.
  - Execution state: pending

- [ ] E-05 Update the two design records under `docs/design/` (with no em or en dashes in added or edited lines):
  - In `docs/design/file-io-provenance-evaluation.md`, add a top-of-file historical outcome banner noting that Recommendations 1 (`/proc/self/io` totals) and 2 (`pubrun.open()`, `ProvenanceFileProxy`, `register_file`/`register_input`/`register_output`) have since shipped with level order `none < name < stat < realpath < hash` and default `level = "stat"` (cross-linking `docs/api.md`, `docs/manifest.md`, `docs/configuration.md`), while Recommendation 3 (`sys.addaudithook`) remains deferred; correct `pause()` reference to `pubrun.paused()`.
  - In `docs/design/tomli-dependency-decision.md`, refresh the TOML call-site summary using module/function names (`config.py`, `_config_boot.py`, `__init__.py::_pyproject_declares_pubrun`, `report/checks.py::_config_file_findings`) and update the `README.md` reference to its current Installation / footnote location.
  - Depends on: none
  - Expected outcome: Readers of `docs/design/` immediately understand what shipped vs what remains deferred, with accurate symbol references.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `AGENTS.md` forbids em and en dashes (`\u2013`, `\u2014`) in user-facing Markdown prose (`docs/*.md`, `docs/design/*.md`).
- `schemas/manifest.schema.json` enforces `"additionalProperties": false` at the top level and has no `profiling` property.
- `src/pubrun/__init__.py::__all__` exports 20 public symbols including `__version__`, `__commit__`, `paused`, `register_file`, `register_input`, `register_output`, `subprocess`, `popen`.
- `src/pubrun/report/utils.py::HYDRABLE_SECTIONS` includes `"host"`.

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| A-01 | High | Low | Operator | `docs/manifest.md` `## profiling` vs `src/pubrun/tracker.py::Run.to_manifest_dict` & `schemas/manifest.schema.json` | Documents phantom top-level `profiling` manifest section that is never emitted and violates `additionalProperties: false`. |
| A-02 | High | Low (doc part) | Operator | `docs/manifest.md` `redacted_value` vs `src/pubrun/capture/redaction.py::redact_value` & `schemas/manifest.schema.json` | Hashed representation disagrees with both live code (`hash_algorithm`/`hash_value`) and JSON Schema (`hash: {algorithm, value}`); omits `unavailable`/`suppressed`. |
| A-03 | High | Low | Novice / Operator | `docs/manifest.md` `python.virtual_env` vs `src/pubrun/capture/python_runtime.py` | Documented as a path, but emits literal `"venv"` or `null`. |
| A-04 | High | Low | Novice | `docs/api.md` primary examples vs `src/pubrun/config.py` & `default.toml` | Teaches deprecated, inert `profile="deep"` / `profile="basic"` without warning. |
| A-05 | High | Low | Operator | `docs/api.md` `assess_run()` vs `src/pubrun/report/reproducibility.py::assess_manifest_reproducibility` & `__main__.py::_assess_cli_run` | Falsely claims `pubrun inspect --json` merges `file_provenance_*` findings omitted by `assess_run()`. |
| A-06 | Medium | Low | Operator / Novice | `docs/manifest.md` (`console_capture_mode`, `invocation.script`, `console`, `Meta Snapshot`, `status.outcome`) vs `src/pubrun/` | Multiple field-level inaccuracies and missing enums (`running`, `crashed`, `partial`, `host`, `real_path`, `ctime`, `captured`, `combined`). |
| A-07 | Medium | Low | Novice / Operator | `docs/api.md` (`phase`, `register_*`, `stop`, `tracked_run`, `audit_run`, `__all__`, `should_fail_strict`) vs `src/pubrun/core.py` & `reproducibility.py` | Misstates inactive-run policy and exception-to-outcome rules; omits bare `@audit_run`, `__version__`/`__commit__`, `paused()` summary, and keyword-only `*` in `should_fail_strict`. |
| A-08 | Medium | Low | Operator | `docs/architecture.md` Sections 5, 10, 12, 16, 21 & `docs/design/file-io-provenance-evaluation.md` | Omits live manifest sections/categories/modules/CLI commands, misstates `<output_dir>/runs/` path, and lacks shipped-outcome banner on Phase-0 file-I/O design doc. |
| A-09 | Low | Low | Operator / Novice | `docs/manifest.md` (`subprocesses[].cwd`, `gpus[]`, nullability), `docs/api.md` & `docs/architecture.md` (`sys.exit`, events, header status), `docs/design/tomli-dependency-decision.md` | Minor field typing/nullability omissions, missing `sys.exit` hook entry, stale header `v1.0.0`, and stale TOML line citations. |

## Proposed changes (ordered, validatable)

1. Fix `docs/api.md` examples, `assess_run()`, inactive-run policies, outcomes, exports, and signatures (E-01; Remediation Risk: Low).
2. Fix `docs/manifest.md` top-level `profiling`, `redacted_value`, `python.virtual_env`, and `status.outcome` (E-02; Remediation Risk: Low).
3. Fix `docs/manifest.md` `console`, `invocation.script`, `Meta Snapshot`, `subprocesses[].cwd`, `gpus[]`, and nullability (E-03; Remediation Risk: Low).
4. Update `docs/architecture.md` manifest, categories, events, run path, hooks, module tree, and header (E-04; Remediation Risk: Low).
5. Add outcome banner to `docs/design/file-io-provenance-evaluation.md` and refresh call-site references in `docs/design/tomli-dependency-decision.md` (E-05; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Reconciling `redacted_value` hashed schema vs `src/pubrun/capture/redaction.py`, adding `"crashed"` to `status.outcome` in `schemas/manifest.schema.json`, and adding `sha256_skipped` to `invocation.script` in `schemas/manifest.schema.json` are deferred in orchestrator `86cd17` (Medium-High Remediation Risk on Functionality).
  - Carrier-Declined: Schema/runtime contract changes outside documentation-only scope; recorded in orchestrator `86cd17`.

## Scope check

- Over-scope: none. Only the five documentation files in `- Scope-Paths:` are modified.
- Under-scope: none.

## Required tests / validation

- Diff inspection across all five files.
- Zero em/en dashes (`\u2013`, `\u2014`) in added lines of all five files.
- Link and anchor verification across all five files.
- `python3 scripts/sanitize_paths.py --check --all` exits 0.

## Spec / documentation sync

- Pure documentation synchronization with live code and schema; no runtime or schema files changed.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- docs/api.md` confirming removal of `profile=` primary examples, corrected `assess_run()` / `file_provenance_*` prose, configurable inactive-run policy for `phase()`/`register_*()`, exact outcome rules and bare `@audit_run`, `__version__`/`__commit__`/`paused()`/`subprocess.Popen`/`sys.exit`, and `should_fail_strict(a, *, fail_on="warn")`; plus pasted zero-dash check on added lines exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- docs/manifest.md` confirming removal of top-level `## profiling`, updated `redacted_value` (with live `hash_algorithm`/`hash_value` and schema-mismatch note + `unavailable`/`suppressed`), corrected `python.virtual_env`, and updated `status.outcome` (`running`, `crashed`, `partial`).
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- docs/manifest.md` covering `console_capture_mode`, `invocation.script`, `console`, `Meta Snapshot`, `subprocesses[].cwd`, `hardware.gpus[]`, nullable columns, `register_*()` note, and reserved sections; plus pasted zero-dash check on added lines of `docs/manifest.md` exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `git diff -- docs/architecture.md` covering header status, Manifest Design, Capture Categories, Event Model (9 types), run directory path, Public API, `sys.exit`, and System Components; plus pasted zero-dash check on added lines exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted `git diff -- docs/design/file-io-provenance-evaluation.md docs/design/tomli-dependency-decision.md`, pasted zero-dash check on added lines of both files exiting 0, pasted link/anchor check across all five files exiting 0, and pasted `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`). This assessment workflow does not execute the plan.

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`).
2. Scope declaration: modify only the five paths in `- Scope-Paths:`.
3. Validation honesty: run every required validation command and paste actual output into each `V-*` item.
4. Commit discipline: commit through `aw commit dd7noz -- <paths>`. Never use `git add -A` or raw `git commit`, and never push without explicit human instruction.
5. Lifecycle transition: finalize through `aw ipd finalize dd7noz` (or the runner) once every `E-*` is `performed`, every `V-*` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
