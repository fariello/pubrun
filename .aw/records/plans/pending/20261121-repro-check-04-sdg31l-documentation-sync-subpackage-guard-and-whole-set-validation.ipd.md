# IPD: Documentation sync, subpackage guard, and whole-Set validation

- Date: 2026-11-21
- Kind: child
- Concern: Documentation accuracy, subpackage import-integrity regression guard, and whole-Set end-to-end validation
- Scope: Update `docs/cli.md`, `docs/hpc.md`, `docs/manifest.md`, and `docs/api.md` for reproducibility assessment and preflight, add `reproducibility` to `tests/test_report_subpackage_integrity.py`, add end-to-end tests in `tests/test_reproducibility_e2e.py` covering all eight `q3bll1` scenarios, and run the full repository test suite.
- Scope-Paths: docs/cli.md, docs/hpc.md, docs/manifest.md, docs/api.md, tests/test_report_subpackage_integrity.py, tests/test_reproducibility_e2e.py
- Item-Dependencies: executed:3lqtlt
- Status: to-review
- Work-Kind: feature
- Priority: medium
- From-Backlog: q3bll1
- Set: repro-check
- Order: 4
- Highest E allocated: 04
- Author: agent
- Id: sdg31l
- Short-Description: Update CLI/HPC/manifest/API docs, guard subpackage imports, and run whole-Set end-to-end validation

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-21 to-review (agent): created child plan 04 of Set `repro-check` graduating backlog item `q3bll1`.

## Goal

Synchronize user and developer documentation with the shipped reproducibility assessment and preflight behavior, guard the new `pubrun.report.reproducibility` submodule against import-mode shadowing regressions, verify all eight example scenarios from backlog item `q3bll1` end-to-end through the real command-line interface (CLI) and Python application programming interface (API), and validate the complete repository test suite.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Documentation synchronization

- [ ] E-01 Update `docs/cli.md` and `docs/hpc.md` to document `pubrun inspect --preflight`, `pubrun rerun --preflight`, `--strict` / `--fail-on`, the structured JavaScript Object Notation (`--json`) contract, evidence statuses (`observed`, `inferred`, `asserted`, `inherited`, `unavailable`, `not_checked`), non-guarantee disclaimer, and high-performance computing (HPC) parent `meta_ref` hydration diagnostics.
  - Depends on: none
  - Expected outcome: `docs/cli.md` and `docs/hpc.md` accurately describe all new flags, exit code contracts, stdout/stderr piping guarantees, evidence taxonomy, and HPC parent-snapshot inheritance limits with concrete examples and zero em or en dashes in user-facing prose added or edited.
  - Execution state: pending

- [ ] E-02 Update `docs/manifest.md` and `docs/api.md` to document parent `meta_ref` inheritance semantics, `pubrun.report.checks.assess_run` / `pubrun.report.utils.hydrate_manifest_with_report` (if surfaced as documented diagnostic helpers), and the read-only offline boundary of reproducibility assessment.
  - Depends on: E-01
  - Expected outcome: `docs/manifest.md` clarifies that hydrated sections are marked `is_hydrated` at report time and carry `inherited` evidence status rather than direct child observation (and that script `mtime` alone does not prove matching dependencies); `docs/api.md` accurately notes read-only diagnostic/preflight boundaries without altering the `import pubrun` one-import adoption story, with zero em or en dashes in added or edited user-facing prose.
  - Execution state: pending

### Task group 2: Subpackage regression guard and end-to-end scenario coverage

- [ ] E-03 Add `"reproducibility"` to `_REPORT_SUBMODULES` in `tests/test_report_subpackage_integrity.py` and create `tests/test_reproducibility_e2e.py` exercising all eight `q3bll1` acceptance scenarios end-to-end via real `pubrun` runs and CLI invocations.
  - Depends on: E-02
  - Expected outcome: `tests/test_report_subpackage_integrity.py` verifies `pubrun.report.reproducibility` remains importable alongside callable `pubrun.report()` under all six import modes (`auto`, `noauto`, `full`, `nopatch`, `noconsole`, `minimal`); `tests/test_reproducibility_e2e.py` passes all eight scenarios (adequate recorded evidence with non-guarantee disclaimer, dirty source without recorded diff, missing dependencies, package mismatch, missing or changed input, redacted arguments, unavailable parent snapshot, and partial or failed capture) plus offline/no-replay CLI proof.
  - Execution state: pending

### Task group 3: Whole-Set validation

- [ ] E-04 Run the complete test suite (`pytest tests/ -v`), manifest schema conformance tests (`tests/test_manifest_schema.py`), import-isolation checks, and record CI matrix readiness requirements.
  - Depends on: E-03
  - Expected outcome: `pytest tests/ -v` exits `0` with zero failures, `tests/test_manifest_schema.py` confirms real manifests still validate against `schemas/manifest.schema.json`, `import pubrun` import-isolation checks pass, and the execution report explicitly states that the GitHub Actions multi-OS/Python matrix (`.github/workflows/ci.yml`: Linux/Windows/macOS across Python 3.8 through 3.14) must pass on pull request or push before release.
  - Execution state: pending

## Project conventions discovered (Step 0)

- User-facing documentation (`docs/cli.md`, `docs/hpc.md`, `docs/manifest.md`, `docs/api.md`, `README.md`) must contain no em dashes or en dashes in newly authored or edited text (per `AGENTS.md` agent execution contract) and must follow `.aw/system/workflows/technical-writing/technical-writing.md`.
- `tests/test_report_subpackage_integrity.py` maintains `_REPORT_SUBMODULES = ["output", "checks", "diagnostics", "methods", "utils"]` and tests every import mode in a fresh subprocess so `pubrun.report` callable shadowing cannot break submodule imports.
- `tests/test_manifest_schema.py` validates real manifests against `schemas/manifest.schema.json` using `jsonschema`.
- `.github/workflows/ci.yml` defines the repository's supported OS and Python matrix (`ubuntu-latest`, `ubuntu-24.04`, `windows-latest`, `macos-latest` across Python `3.8` through `3.14`) running `pytest tests/ -v`.

## Findings

1. Adding a new submodule `pubrun.report.reproducibility` without adding `"reproducibility"` to `_REPORT_SUBMODULES` in `tests/test_report_subpackage_integrity.py` would leave the new module unguarded by the callable-subpackage shadowing regression suite.
2. `docs/cli.md` currently documents `pubrun inspect` without `--preflight` or `--fail-on`, documents `pubrun rerun` without `--preflight`/`--strict`/`--json`, and documents `Exit Codes` with only `0` and `1` (missing strict preflight details).
3. `docs/hpc.md` and `docs/manifest.md` describe `meta_ref` hydration without explaining inherited-vs-direct evidence status, parent age/identity checks, or why script `mtime` alone does not prove matching dependencies.

## Proposed changes (ordered, validatable)

1. **`docs/cli.md`**:
   - Update the `inspect` section with `--preflight`, `--fail-on {warn,mismatch,unknown}`, the structured JSON output fields (`findings`, `categories`, `next_action`, `next_actions`, `disclaimer`, `parent_metadata`, `preflight`), evidence statuses (`observed`, `inferred`, `asserted`, `inherited`, `unavailable`, `not_checked`), explicit non-guarantee note, and concrete examples.
   - Update the `rerun` section with opt-in `--preflight`, `--strict`, `--fail-on`, and `--json`, explicitly documenting that default `pubrun rerun | bash` piping is unchanged, that `--preflight` prints diagnostics to `stderr`, that `--preflight --strict` exits `1` without printing to `stdout` on failure, that redacted commands are not directly executable, and that `pubrun` never executes the recorded command automatically.
   - Update the `show` section to note the concise reproducibility summary line in `standard`/`deep` reports and update the `Exit Codes` table to document `--strict` / `--fail-on` behavior.
2. **`docs/hpc.md`**:
   - Update `Diagnosing a finished run` to cover `pubrun inspect --preflight` on clusters (explaining how cross-node inspection separates expected portability/hostname differences from material package/Python/input mismatches) and how `meta_ref` parent snapshots are assessed for age, availability, and inherited-vs-observed status.
3. **`docs/manifest.md` and `docs/api.md`**:
   - Update `Meta Snapshot` / `meta_ref` notes in `docs/manifest.md` to explain `is_hydrated`, `inherited` evidence classification, and why script `mtime` alone does not prove matching dependencies.
   - Update `docs/api.md` with a concise note pointing to read-only post-hoc inspection and preflight (`pubrun inspect --preflight` / `pubrun.report.checks.assess_run`), reinforcing that report modules are never loaded by `import pubrun`.
4. **`tests/test_report_subpackage_integrity.py`**:
   - Add `"reproducibility"` to `_REPORT_SUBMODULES`.
5. **`tests/test_reproducibility_e2e.py`** (new test file):
   - Exercise all eight scenarios required by `q3bll1` acceptance criteria using real `tmp_path` fixtures, real manifests (and real git repos created with `git init`), and real `python -m pubrun` subprocess calls:
     1. Adequate recorded evidence (verifying non-guarantee disclaimer is present and sparse/legacy manifests also avoid claiming reproduction is guaranteed).
     2. Dirty source without recorded diff/patch.
     3. Missing dependencies (`packages` suppressed or empty).
     4. Package version mismatch and missing package on preflight.
     5. Missing and content-changed input file on preflight (plus stat-only `not_checked` distinct from verified hash match).
     6. Redacted CLI arguments (`rerun_command` contains `[REDACTED]`, warned as not directly executable; `rerun --preflight --strict` refuses to emit to stdout).
     7. Unavailable / moved / policy-blocked parent `meta_ref` snapshot (and available stale/inherited snapshot distinct from direct observation).
     8. Partial or failed capture (`capture_state.status` = `partial`/`failed`/`timeout`, non-completed run outcome).
   - Verify CLI and Python `assess_run()` produce matching category statuses, finding codes, and `next_action`.

## Deferred / out of scope (with reason)

- Running the GitHub Actions Windows and macOS CI matrix locally: unavailable on a single Linux workstation; documented as a pre-merge CI gate using `.github/workflows/ci.yml`.
- Performance speedup benchmarks: N/A because this feature adds read-only diagnostic/preflight tooling off the `import pubrun` path and claims no speedup; import-path isolation (`import pubrun` never imports `pubrun.report.reproducibility`) is verified instead.

## Scope check

- Over-scope: none. Only updates affected docs, guards the new report submodule, adds the eight backlog acceptance scenarios, and runs the full test suite.
- Under-scope: none. Closes every documentation, cross-IPD consistency, and whole-Set validation requirement for Set `repro-check` and backlog item `q3bll1`.

## Required tests / validation

- Run `pytest tests/test_report_subpackage_integrity.py tests/test_reproducibility_e2e.py tests/test_manifest_schema.py -v`.
- Run the full repository test suite `pytest tests/ -v`.
- Run a fresh subprocess check confirming `import pubrun` does not import `pubrun.report.checks` or `pubrun.report.reproducibility`.

## Spec / documentation sync

- Updates `docs/cli.md`, `docs/hpc.md`, `docs/manifest.md`, and `docs/api.md` in `E-01` and `E-02`.
- `schemas/manifest.schema.json`: unchanged and validated by `tests/test_manifest_schema.py` in `E-04`.

## Open questions

### OQ-01: Multi-OS and multi-Python CI matrix execution

- Blocking: no
- Status: open
- Owner: none
- Resolution or deferral rationale: Per `q3bll1` shared validation requirements, CLI and platform-dependent changes require the repository's supported OS/Python CI matrix (`.github/workflows/ci.yml`: Linux, Windows, macOS across Python 3.8 through 3.14) before completion. Local validation runs on the current Linux Python version; full matrix verification occurs when pushed to GitHub Actions CI.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition)—as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction—name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Paste `git diff -- docs/cli.md docs/hpc.md` summary (or key section checks) and verify zero em/en dashes (`—`, `–`) were introduced in added lines of `docs/cli.md` and `docs/hpc.md` via a Python check command, confirming all new `inspect`/`rerun`/`show` flags, exit codes, JSON fields, evidence statuses, and HPC parent-hydration notes match the implemented CLI `--help` output.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Paste `git diff -- docs/manifest.md docs/api.md` summary and verify zero em/en dashes (`—`, `–`) were introduced in added lines of `docs/manifest.md` and `docs/api.md`, confirming `meta_ref` inheritance semantics and read-only diagnostic boundaries match `src/pubrun/report/utils.py` and `src/pubrun/report/reproducibility.py`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Paste actual runner output of `pytest tests/test_report_subpackage_integrity.py tests/test_reproducibility_e2e.py -v` showing exit code 0 and all six import-mode checks plus all eight `q3bll1` end-to-end scenarios passing.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Paste actual runner output of `pytest tests/ -v` (summary line and exit code 0), `pytest tests/test_manifest_schema.py -v` (exit code 0), and `python -c "import pubrun, sys; assert 'pubrun.report.checks' not in sys.modules and 'pubrun.report.reproducibility' not in sys.modules; print('ISOLATED')"` printing `ISOLATED` (exit code 0), plus an explicit note recording the pending GitHub Actions multi-OS/Python CI matrix gate.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution requires explicit human approval (`- Status: approved`) and completion of dependency `3lqtlt`. Commit only the scoped files through `aw commit sdg31l -- <paths>`, paste actual runner output into `Observed evidence`, and run the post-gate `aw ipd` lifecycle transition to `.aw/records/plans/executed/`.
