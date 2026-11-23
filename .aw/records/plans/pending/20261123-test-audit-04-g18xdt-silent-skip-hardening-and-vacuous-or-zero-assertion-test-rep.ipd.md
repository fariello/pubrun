# IPD: Silent-skip hardening and vacuous or zero-assertion test repair

- Date: 2026-11-23
- Kind: child
- Concern: Testing rigor and completeness (eliminating silent bug-masking `pytest.skip` calls, zero-assertion tests, vacuous loops, tautological `.tmp` checks, and teardown leaks).
- Scope: `tests/test_capture_engines.py`, `tests/test_tracker.py`, `tests/test_quality.py`, `tests/test_new_features.py`, `tests/test_capture.py`, `tests/test_api.py`, `tests/test_manifest_schema.py`, and `tests/test_methods_multi.py`.
- Scope-Paths: tests/test_capture_engines.py, tests/test_tracker.py, tests/test_quality.py, tests/test_new_features.py, tests/test_capture.py, tests/test_api.py, tests/test_manifest_schema.py, tests/test_methods_multi.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Remove bug-masking skips and repair zero-assertion, vacuous, and tautological tests across core and schema suites
- Work-Kind: bug
- Priority: high
- Set: test-audit
- Order: 4
- Highest E allocated: 05
- Author: Antigravity
- Id: g18xdt

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-23 to-review (Antigravity): authored from `/assess-testing` findings T-08 (schema/methods) and T-09.
- 2026-11-23 draft (Antigravity): created.

## Goal

Convert silent zero-assertion, vacuous, tautological, and bug-masking-skip tests across core lifecycle, capture engine, and schema test files into strict behavioral regression gates that fail when the underlying production behavior breaks.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: each E-item addresses one concern executable in one focused pass. Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Repair zero-assertion and tautological core tests

- [ ] E-01 Fix `tests/test_capture_engines.py` so `TestGit` (`test_has_commit_when_in_repo`, `test_has_branch`, `test_has_dirty`) creates a real temporary git repository inside `tmp_path` and asserts `result["capture_state"]["status"] == "complete"` unconditionally, and `TestEnvironment` (`test_redacts_secrets`, `test_redaction_disabled_via_config`) asserts `"TEST_API_TOKEN" in by_name` unconditionally instead of gating behind `if`.
  - Depends on: none
  - Expected outcome: All five tests execute real assertions on every run instead of silently passing with zero assertions.
  - Execution state: pending

- [ ] E-02 Fix `tests/test_tracker.py` (`test_atomic_manifest_write` and `test_atomic_write_cleans_temp_on_failure`) to assert `list(run_dir.glob("*.tmp")) == []` (and `list(target.parent.glob("*.tmp")) == []`) instead of checking obsolete `.json.tmp` filenames, and update `tests/test_api.py:test_ignore_policy_is_silent` to inject `caplog` and assert `caplog.records == []`.
  - Depends on: none
  - Expected outcome: Temp-file leak checks match `writer.py`'s actual `*.json.<pid>.<uuid8>.tmp` pattern and `test_ignore_policy_is_silent` proves silence via `caplog`.
  - Execution state: pending

### Task group 2: Repair vacuous assertions and unsafe teardown

- [ ] E-03 Fix `tests/test_quality.py`: (a) complete `TestDoubleStop.test_double_stop_preserves_manifest` by re-reading `manifest.json` after the second `tracker.stop(outcome="completed")` and asserting `data2 == data1` (including `elapsed_seconds == elapsed1`), and (b) wrap `sys.stdout = third_party` in `TestConsoleRestoreSafety.test_stop_preserves_third_party_wrapper` using `monkeypatch` or `try/finally`.
  - Depends on: none
  - Expected outcome: Double-stop preservation is genuinely asserted and `sys.stdout` is always restored even on test failure.
  - Execution state: pending

- [ ] E-04 Fix `tests/test_capture.py` (`TestSubprocessSpy.test_detached_subprocess_finalized` to spawn a child that stays alive until `stop()`, assert `len(unwatched) == 1`, and terminate/reap `p` in `finally:`) and `tests/test_new_features.py` (`TestResourceWatcherTreeScope.test_tree_scope_manifest_fields` to mock `_poll_tree_rss` cross-platform, replace `time.sleep(0.3)` with deadline polling, and assert `peak_tree_rss_bytes == 100_000_000`; and `TestConcurrentStart.test_only_one_run_created` to stop all 5 ref-counts cleanly).
  - Depends on: none
  - Expected outcome: Neither test passes vacuously, no child process or active ref-count is leaked, and tree RSS assertion is active on Linux, macOS, and Windows.
  - Execution state: pending

### Task group 3: Harden silent skips and expand schema contract coverage

- [ ] E-05 Harden `tests/test_manifest_schema.py` and `tests/test_methods_multi.py`: (a) in `test_startup_manifest_conforms_to_schema`, never skip on `json.JSONDecodeError` or `FileNotFoundError` (tolerate retry only on `PermissionError` on `win32`); (b) fix the stale module docstring claiming whole-manifest drift uses `xfail`; (c) add live end-to-end schema validation for populated `meta_ref`, `determinism`, and `artifacts` fields; and (d) replace `pytest.importorskip("pubrun.report.methods")` in `tests/test_methods_multi.py:test_aggregate_of_one_equals_single` with a direct import.
  - Depends on: none
  - Expected outcome: Corrupt or missing startup manifests fail loudly on all platforms, internal imports cannot silently skip, and schema validation covers `meta_ref`, `determinism`, and `artifacts`.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `tests/conftest.py:isolated_cwd` is `autouse=True` and chdirs every test into `tmp_path`, which is outside any git repo; tests that require a git repo must initialize one inside `tmp_path`.
- `src/pubrun/writer.py:_atomic_json_write` writes unique temp files named `.json.<pid>.<uuid8>.tmp`, never `.json.tmp`.

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| T-08 (part) | High | Low | Testing expert / QA engineer | `tests/test_manifest_schema.py:test_startup_manifest_conforms_to_schema`; `tests/test_methods_multi.py:test_aggregate_of_one_equals_single` | Silent skips on `JSONDecodeError`/`FileNotFoundError` and internal `pubrun.report.methods` import mask real regressions. |
| T-09 | High | Low | Testing expert | `tests/test_capture_engines.py:TestGit`, `TestEnvironment`; `tests/test_tracker.py`; `tests/test_quality.py:TestDoubleStop`, `TestConsoleRestoreSafety`; `tests/test_new_features.py`; `tests/test_capture.py:TestSubprocessSpy`; `tests/test_api.py:test_ignore_policy_is_silent` | Zero-assertion git/env tests, vacuous double-stop and detached-subprocess tests, tautological `.json.tmp` checks, and unguarded `sys.stdout` mutation. |

## Proposed changes (ordered, validatable)

1. Repair `TestGit` and `TestEnvironment` in `tests/test_capture_engines.py` (Remediation Risk: Low).
2. Fix `.tmp` glob assertions in `tests/test_tracker.py` and `caplog` silence check in `tests/test_api.py` (Remediation Risk: Low).
3. Complete double-stop assertions and `sys.stdout` restore in `tests/test_quality.py` (Remediation Risk: Low).
4. Make `test_detached_subprocess_finalized`, `test_tree_scope_manifest_fields`, and `test_only_one_run_created` strict and leak-free in `tests/test_capture.py` and `tests/test_new_features.py` (Remediation Risk: Low).
5. Remove bug-masking skips and add `meta_ref`/`determinism`/`artifacts` schema coverage in `tests/test_manifest_schema.py` and `tests/test_methods_multi.py` (Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Silent skips in `tests/test_liveness.py` are owned by `7y0gmc`.
  - Carrier: 7y0gmc
- Silent skips in `tests/test_status.py` are owned by `ic6z4s`.
  - Carrier: ic6z4s
- Silent skips in `tests/test_sanitize_paths.py` are owned by `2mwjjw`.
  - Carrier: 2mwjjw

## Scope check

- Over-scope: none.
- Under-scope: none.

## Required tests / validation

- Run `pytest tests/test_capture_engines.py tests/test_tracker.py tests/test_quality.py tests/test_new_features.py tests/test_capture.py tests/test_api.py tests/test_manifest_schema.py tests/test_methods_multi.py -v`.
- Verify zero unexpected skips in the run output.
- Run `python3 scripts/sanitize_paths.py --check --all`.

## Spec / documentation sync

N/A with reason: test-only hardening; no production code or user-facing behavior changes.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'.

- [ ] V-01 validates E-01
  - Required evidence: Pasted output of `pytest tests/test_capture_engines.py -v` showing all `TestGit` and `TestEnvironment` tests passing and diff confirming unconditional assertions.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted output of `pytest tests/test_tracker.py tests/test_api.py -v` passing and diff showing `glob("*.tmp")` and `caplog.records == []`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted output of `pytest tests/test_quality.py -v` passing and diff confirming post-second-stop manifest comparison and `sys.stdout` cleanup guard.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted output of `pytest tests/test_capture.py tests/test_new_features.py -v` passing with `len(unwatched) == 1`, `peak_tree_rss_bytes == 100_000_000`, and balanced `pubrun.stop()` calls.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted output of `pytest tests/test_manifest_schema.py tests/test_methods_multi.py -v` showing 0 skipped tests and all new schema checks passing, plus `python3 scripts/sanitize_paths.py --check --all` exit 0.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

This plan must be reviewed and explicitly approved by a human (`- Status: approved`) before execution. During execution, commit only the scoped files through `aw commit`, never push without explicit human instruction, and move this plan to `.aw/records/plans/executed/` only after all `E-*` items are `performed`, all `V-*` items are `pass`, and `aw ipd lint` reports `conforming`.
