# IPD: CLI, status, diagnostics, and render negative paths and assertion hardening

- Date: 2026-11-23
- Kind: child
- Concern: Testing rigor and completeness (strengthening weak CLI/status/report assertions, fixing subprocess executable/epoch/leak bugs in tests, removing Linux silent skips in `test_status.py`, and adding CLI/diagnostics/status/render negative-path tests).
- Scope: `tests/test_cli.py`, `tests/test_status.py`, `tests/test_reports.py`, `tests/test_render.py`, `tests/test_combined.py`, `tests/test_report_subpackage_integrity.py`, and new `tests/test_cli_negative_paths.py`.
- Scope-Paths: tests/test_cli.py, tests/test_status.py, tests/test_reports.py, tests/test_render.py, tests/test_combined.py, tests/test_report_subpackage_integrity.py, tests/test_cli_negative_paths.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Strengthen weak CLI/status/report assertions, fix epoch and subprocess helpers, and test corrupt-manifest and flag negative paths
- Work-Kind: chore
- Priority: high
- Set: test-audit
- Order: 7
- Highest E allocated: 05
- Author: Antigravity
- Id: ic6z4s

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-23 to-review (Antigravity): authored from `/assess-testing` findings T-08 (`test_status.py`), T-14, and T-15.
- 2026-11-23 draft (Antigravity): created.

## Goal

Eliminate exit-0-only, tautological, time-dependent, and leaky test patterns across CLI, status, report, and combined-output suites, and add thorough negative-path and flag coverage for corrupt JSON manifests, invalid durations, `status.py`, `render.py`, and untested CLI subcommand flags.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: each E-item addresses one concern executable in one focused pass. Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Harden weak assertions, fixtures, and leaks

- [ ] E-01 Harden `tests/test_cli.py` and `tests/test_reports.py`: (a) strengthen `TestCliDiff`, `TestCliReport`, and `TestCliMeta` to assert concrete output content (no ANSI codes for `--no-color`, created `.pubrun_diff_*` export files with valid JSON/text inside `cwd=str(tmp_path)`, distinct output across depth levels); (b) replace hardcoded `1782000000.0` epochs with relative `time.time()` offsets and fix lock key `"args"` -> `"argv"`; (c) replace manual `Path.cwd = staticmethod(...)` mutations with `monkeypatch` / `isolated_cwd`, and ensure every `subprocess.run` prepends `src/` to `PYTHONPATH`; and (d) replace loose `or` assertions in `tests/test_reports.py:TestPrintReportUnit` with exact value checks.
  - Depends on: none
  - Expected outcome: Every CLI diff/report/meta test validates real observable output and is immune to calendar drift or `Path.cwd` fixture collisions.
  - Execution state: pending

- [ ] E-02 Harden `tests/test_status.py`: (a) replace hardcoded `["python", "-m", "pubrun", ...]` in `TestStatusCli` and `TestCleanCli` with `[sys.executable, "-m", "pubrun", ...]` plus `PYTHONPATH=src`; (b) fail hard on Linux instead of `pytest.skip` in `test_scan_running_run` and `test_clean_does_not_delete_running`; (c) replace the tautological `exit_code is not None or exit_code is None` in `test_scan_broken_pipe_run` and add a `STATUS_RUNNING` precondition assertion in `test_clean_running_filter_stripped`; (d) use explicit distinct `started_at_utc` values in `test_clean_interactive_selection_and_confirm`; and (e) add unit tests for `filter_runs` invalid-regex literal fallback and `exit_code` filtering, `clean_runs` interactive `KeyboardInterrupt`/`EOFError`/`"n"`/invalid selection/`shutil.rmtree` `OSError`, and `find_run` ambiguous prefix returning `None` + dir-name substring fallback.
  - Depends on: none
  - Expected outcome: `tests/test_status.py` has zero tautological assertions, zero Linux silent skips, portable `sys.executable` invocations, and covers all `status.py` fallback/error paths.
  - Execution state: pending

- [ ] E-03 Clean up `tests/test_combined.py` (replace the fragile `pubrun.__main__.open` `side_effect=Exception("Stop execution here")` sentinel mocks with tiny 1-line real files and assert actual combined stdout output) and `tests/test_report_subpackage_integrity.py` (pass `tmp_path` as `cwd` and prepend `src/` to `PYTHONPATH` instead of leaking uncleaned `tempfile.mkdtemp()` directories in `/tmp`).
  - Depends on: none
  - Expected outcome: Both test files verify real observable output without leaking temp directories or depending on internal exception-swallowing accidents.
  - Execution state: pending

### Task group 2: Render and CLI/diagnostics negative paths

- [ ] E-04 Expand `tests/test_render.py` to test `_summarize_change` and `_render_table` for `list_diff` summaries in `--table` mode, `path_split`/`list_diff` truncation at `max_length`, long-key ellipsis (`len(k) > 48`), multiline detail flattening, and `_render_table(..., use_color=True)` ANSI formatting.
  - Depends on: none
  - Expected outcome: All previously uncovered branches in `src/pubrun/analysis/render.py` are verified.
  - Execution state: pending

- [ ] E-05 Create `tests/test_cli_negative_paths.py` testing: (a) corrupt JSON `manifest.json` across `show`, `diff`, `methods`, `rerun`, `res`, and `inspect` (verifying non-zero exit and clear error output); (b) invalid `--last` values (`bogus`, empty string) and zero-sample `events.jsonl` for `res`/`cpu`/`mem`; (c) `methods --all <run_dir>` mutual-exclusion error and `methods --all` with 0/corrupt runs; (d) CLI `diff` flags (`--table`, `--same`/`--no-same`, `--max-length`, bare `--export`, `--basic`), `status <id>` / `-v` / `--utc` / ambiguous selector / crashed auto-closeout, `--create-config` prompt branches (mocking `builtins.input` for `"1"`, `""`, `"2"`, invalid choice, `KeyboardInterrupt`), unknown-command stderr text excluding aliases (`tui`/`gui`), and `pbr --help` showing `pbr` usage.
  - Depends on: none
  - Expected outcome: High-traffic CLI subcommands and diagnostics error paths are covered end-to-end with deterministic assertions.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `tests/test_cli.py:run_pubrun` and `tests/test_cli_diff_bugs.py:run_pubrun` demonstrate the canonical pattern: `[sys.executable, "-m", "pubrun", ...]` with `src/` prepended to `PYTHONPATH`.
- Pending approved plan `4cy3ft` also addresses `PYTHONPATH=src` for specific test subprocess helpers; keep `ic6z4s` strictly within its own `Scope-Paths` (do not touch files outside `Scope-Paths`).
- Pending approved plan `6bgkyj` owns missing host OS fields in `print_report`; excluded here.

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| T-08 (part) | High | Low | Testing expert / QA engineer | `tests/test_status.py:test_scan_running_run`, `test_clean_does_not_delete_running` | Unconditional `pytest.skip` masks `STATUS_RUNNING` regressions on Linux. |
| T-14 | High | Low | QA engineer / Testing expert | `tests/test_cli.py:TestCliDiff`, `TestCliReport`, `TestCliMeta`; `tests/test_status.py`; `tests/test_reports.py`; `tests/test_combined.py`; `tests/test_report_subpackage_integrity.py` | Exit-0-only assertions, tautological `exit_code` check, hardcoded `"python"` & `1782000000.0` epochs, `"args"` lock typo, leaked `/tmp` dirs, and `open()` sentinel mocks. |
| T-15 | High | Low | QA engineer / Testing expert | `src/pubrun/__main__.py`; `src/pubrun/report/diagnostics.py`; `src/pubrun/status.py`; `src/pubrun/analysis/render.py` | Corrupt JSON manifests, invalid `--last`, `methods --all` errors, CLI `diff`/`status`/`--create-config`/`pbr`/unknown-command flags, `status.py` regex/cancel/ambiguous paths, and `render.py` table/color branches lack tests. |

## Proposed changes (ordered, validatable)

1. Strengthen `tests/test_cli.py` and `tests/test_reports.py` assertions, relative timestamps, and `Path.cwd`/`PYTHONPATH` hygiene (Remediation Risk: Low).
2. Fix `tests/test_status.py` executable/skips/tautologies and add `filter_runs`/`clean_runs`/`find_run` negative tests (Remediation Risk: Low).
3. Clean up `tests/test_combined.py` and `tests/test_report_subpackage_integrity.py` (Remediation Risk: Low).
4. Expand `tests/test_render.py` for `_render_table` and truncation/color paths (Remediation Risk: Low).
5. Add `tests/test_cli_negative_paths.py` covering corrupt JSON, `--last`, `methods --all`, CLI flags, `--create-config`, unknown commands, and `pbr --help` (Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Refactoring monolithic `src/pubrun/__main__.py:main` and `diagnostics.py:print_*` (T-18): Remediation Risk **Medium-High** on **complexity** and **functionality**; deferred.
  - Carrier: riulkx

## Scope check

- Over-scope: none.
- Under-scope: none.

## Required tests / validation

- Run `pytest tests/test_cli.py tests/test_status.py tests/test_reports.py tests/test_render.py tests/test_combined.py tests/test_report_subpackage_integrity.py tests/test_cli_negative_paths.py -v`.
- Run `python3 scripts/sanitize_paths.py --check --all`.

## Spec / documentation sync

N/A with reason: test-only hardening and coverage expansion.

## Open questions

### OQ-01: Behavior of `pubrun show <run> <unknown_section>`

- Blocking: no
- Status: resolved
- Owner: none
- Resolution or deferral rationale: Resolved to characterization-only in this test plan: `src/pubrun/report/diagnostics.py:print_report` currently falls through to printing the full report with exit 0 when passed an unrecognized section name, so `ic6z4s` characterizes that existing behavior without changing production CLI exit semantics.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'.

- [ ] V-01 validates E-01
  - Required evidence: Pasted output of `pytest tests/test_cli.py tests/test_reports.py -v` passing and `grep -n "1782000000" tests/test_cli.py` returning zero matches.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted output of `pytest tests/test_status.py -v` passing with 0 skips on Linux and `grep -n '"python"' tests/test_status.py` returning zero subprocess matches.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted output of `pytest tests/test_combined.py tests/test_report_subpackage_integrity.py -v` passing and `grep -n "Stop execution here\|mkdtemp" tests/test_combined.py tests/test_report_subpackage_integrity.py` returning zero matches.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted output of `pytest tests/test_render.py -v` showing all new table, truncation, ellipsis, and color tests passing.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted output of `pytest tests/test_cli_negative_paths.py -v` showing all corrupt-JSON, `--last`, `methods --all`, CLI flag, `--create-config`, unknown-command, and `pbr` tests passing, plus `python3 scripts/sanitize_paths.py --check --all` exit 0.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

This plan must be reviewed and explicitly approved by a human (`- Status: approved`) before execution. During execution, commit only the scoped files through `aw commit`, never push without explicit human instruction, and move this plan to `.aw/records/plans/executed/` only after all `E-*` items are `performed`, all `V-*` items are `pass`, and `aw ipd lint` reports `conforming`.
