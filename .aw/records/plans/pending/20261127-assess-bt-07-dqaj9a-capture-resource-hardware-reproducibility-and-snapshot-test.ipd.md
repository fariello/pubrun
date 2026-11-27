# IPD: Capture resource hardware reproducibility and snapshot test coverage

- Date: 2026-11-27
- Kind: child
- Concern: Close high/medium behavioral coverage gaps in `ResourceWatcher`, `hardware.py`, `meta_snapshot.py`, `reproducibility.py`, `checks.py`, and `methods.py` (`TEST-C3`, `TEST-C4`, `TEST-U6`, `TEST-U7`, `TEST-U10`).
- Scope: Add deterministic behavioral tests (no production code changes) in `tests/test_resources.py`, `tests/test_hardware.py`, `tests/test_hpc_hydration_e2e.py`, `tests/test_reproducibility_assessment.py`, `tests/test_checks_commands.py`, `tests/test_reports.py`, and `tests/test_methods_multi.py`.
- Scope-Paths: tests/test_resources.py, tests/test_hardware.py, tests/test_hpc_hydration_e2e.py, tests/test_reproducibility_assessment.py, tests/test_checks_commands.py, tests/test_reports.py, tests/test_methods_multi.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Add deterministic tests for ResourceWatcher partial/failed states, hardware parsers/timeouts, meta_snapshot containment, seed scan caps, and checks/methods
- Work-Kind: followup
- Priority: high
- Set: assess-bt
- Order: 7
- Highest E allocated: 05
- Author: Antigravity
- Id: dqaj9a

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-27 to-review (Antigravity): Authored review-ready child IPD from `/assess testing` Slices 1 and 2 on HEAD `512ee68` / `8f2aacd`.
- 2026-11-27 draft (Antigravity): created.

## Goal

Close empirically verified 0%-coverage branches in failure-state reporting (`ResourceWatcher` `partial` vs `failed`), newly landed `assess-8l` parsers and containment logic (`hardware.py`, `meta_snapshot.py`, `reproducibility.py::_has_recorded_seed_annotation`), and live-check/methods-truncation paths (`checks.py`, `methods.py`), replacing hedged/weak assertions with exact contract checks.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Cover capture failure states and hardware parser boundaries

- [ ] E-01 Cover `ResourceWatcher` failure-state manifest reporting, idempotency, and CPU clamping in `tests/test_resources.py` (`TEST-C3`):
  - Add deterministic unit tests exercising `ResourceWatcher._update_metrics()` + `to_manifest_dict()` for `successful_samples == 0` (`status == "failed"`, `"resource polling failed on every sample"`) and `successful_samples > 0` followed by `max_failures` (`status == "partial"`, `"resource polling stopped after consecutive failures"`).
  - Verify `ResourceWatcher.stop()` skips final measurement after abort and is idempotent on double-stop / unstarted watcher.
  - Verify negative `os.times()` CPU delta clamps to `0.0`.
  - Make `peak_rss_bytes > 0` unconditional on non-Windows in `test_resources_watcher_threads` (removing the silent `if res["peak_rss_bytes"] is not None:` guard) and remove the unused `_get_rss_windows` import.
  - Depends on: none
  - Expected outcome: `src/pubrun/capture/resources.py` failure-state, stop-idempotency, and CPU-clamp branches are covered and `test_resources_watcher_threads` fails loudly on sampling timeout.
  - Execution state: pending

- [ ] E-02 Add boundary and negative tests for `hardware.py` parsers and timeouts in `tests/test_hardware.py` (`TEST-C4`):
  - Parametrize `_parse_windows_reg_vram` tests covering negative signed 32-bit `int` conversion (`raw & 0xFFFFFFFF`), `bool` rejection (`True`/`False -> None`), `0 -> None`, and empty `bytes`.
  - Test `get_hardware` with `total_timeout=0` and invalid timeout values (`float("nan")`, `float("inf")`, `-1`, `True`, `"bad"`) confirming safe fallback without raising.
  - Test `_parse_amd_smi_json` and `_parse_rocm_smi_json` on malformed JSON, top-level list vs single-dict payloads, `[N/A]` sentinels, integer MB `vram_size` fallback, non-`(B)` ROCm VRAM key fallback, and `amd-smi`/`rocm-smi` `subprocess.TimeoutExpired` budget marking.
  - Depends on: none
  - Expected outcome: Freshly landed `assess-8l` hardware parser and timeout paths in `src/pubrun/capture/hardware.py` are behaviorally verified.
  - Execution state: pending

### Task group 2: Cover snapshot containment, seed-scan caps, and checks/methods gaps

- [ ] E-03 Cover `meta_snapshot.py` section-failure containment and `_has_recorded_seed_annotation` scan caps in `tests/test_hpc_hydration_e2e.py` and `tests/test_reproducibility_assessment.py` (`TEST-U6`, `TEST-U7`):
  - In `tests/test_hpc_hydration_e2e.py`: monkeypatch `get_hardware` in `pubrun.report.meta_snapshot` to raise `RuntimeError("probe failed")`, call `generate_meta_snapshot(out, "basic")`, and assert the snapshot JSON is written with `hardware.capture_state == {"status": "failed", "detail": "probe failed"}` while sibling sections succeed; also test `_sanitize_json_value` on self-referential dict/list (raises `ValueError("Circular reference detected")`), tuples with `NaN`/`Inf`, and non-finite float dict keys.
  - In `tests/test_reproducibility_assessment.py`: test `_has_recorded_seed_annotation` on (a) corrupt JSON lines, JSON arrays containing `"annotation"`, and non-dict payloads followed by a valid seed annotation (returns `True`), (b) `{"type": "annotation", "payload": {"seed": null}}` (returns `False`), and (c) monkeypatched small `_SEED_SCAN_MAX_LINES` / `_SEED_SCAN_MAX_BYTES` caps with a seed past either cap (returns `False`).
  - Depends on: none
  - Expected outcome: Uncovered resilience and cap branches in `src/pubrun/report/meta_snapshot.py` and `src/pubrun/report/reproducibility.py` are covered.
  - Execution state: pending

- [ ] E-04 Cover `checks.live_findings()`/`live_checks()` branches and `methods.py` edge/truncation paths in `tests/test_checks_commands.py`, `tests/test_reports.py`, and `tests/test_methods_multi.py` (`TEST-U10`):
  - In `tests/test_checks_commands.py`: add deterministic monkeypatched tests for `live_findings()`/`live_checks()` triggering `low_memory`, `high_load`, `git_missing`, `fs_hung_*`, and `fs_slow_*` and asserting exact finding codes and severities.
  - In `tests/test_reports.py`: tighten `test_empty_python_version` to assert `"Python unknown (Unknown)" in result`, and add a 12-package non-highlighted manifest test asserting the truncation summary branch.
  - In `tests/test_methods_multi.py`: add a >10 non-highlighted packages multi-run test and a suppressed-package variance test covering `_packages_of`.
  - Depends on: none
  - Expected outcome: Weak "does not throw" assertions are replaced and uncovered `checks.py` / `methods.py` branches are verified.
  - Execution state: pending

### Task group 3: Validate coverage and randomized execution

- [ ] E-05 Run targeted `pytest -p randomly` with coverage across all six target production modules and record complete output:
  - Run the command in `## Required tests / validation` and verify exit `0` and increased line coverage on every targeted branch.
  - Depends on: E-01, E-02, E-03, E-04
  - Expected outcome: All seven test files pass under `-p randomly` with targeted branches covered.
  - Execution state: pending

## Project conventions discovered (Step 0)

- Full-suite baseline coverage at `512ee68` confirmed exact 0%-hit lines matching these findings: `resources.py` (`_poll_cpu` clamp, `to_manifest_dict` partial/failed), `meta_snapshot.py` (83%, missing `26, 39, 46-54, 114-116`), `reproducibility.py` (`_has_recorded_seed_annotation` missing `1190, 1193, 1198-1199, 1201, 1204`), `checks.py` (82%, missing `132-133, 138-139, 156, 170-171, 182, 187, 203-204, 228-231, 240, 248-254`), and `methods.py` (95%, missing `302-304, 422, 430`).
- Zero production source edits are needed for this plan; every test exercises real functions with deterministic inputs/mocks.

## Findings

| ID | Concerns | Severity | Remediation Risk | Persona | Summary |
|---|---|---|---|---|---|
| `TEST-C3` | testing | High | Low (`functionality`) | Testing / QA Engineer | `ResourceWatcher` `partial` vs `failed` manifest reporting, `stop()` idempotency, and CPU wrap clamping are uncovered; `peak_rss_bytes` check silently masks timeout. |
| `TEST-C4` | testing | Medium | Low (`functionality`) | Testing / QA Engineer | Freshly landed `hardware.py` VRAM/AMD/ROCm parsers and timeout validation lack negative and boundary tests. |
| `TEST-U6` | testing | Medium | Low (`functionality`) | Reliability / HPC Engineer | `meta_snapshot._gather` section-failure containment and `_sanitize_json_value` circular-ref/tuple/NaN guards have 0% coverage. |
| `TEST-U7` | testing | Medium | Low (`functionality`) | Reproducibility / QA Engineer | `_has_recorded_seed_annotation` line/byte scan caps, corrupt-line skipping, and `seed: null` handling have 0% coverage. |
| `TEST-U10` | testing | Low | Low (`functionality`) | QA Engineer | Weak assertions in `test_checks_commands.py` and `test_reports.py` leave `live_findings()` branches and >10 package truncation / suppressed packages untested. |

## Proposed changes (ordered, validatable)

1. `E-01` (`tests/test_resources.py`): Add `ResourceWatcher` failure-state, double-stop, and CPU-clamp tests; tighten `peak_rss_bytes` assertion.
2. `E-02` (`tests/test_hardware.py`): Add `_parse_windows_reg_vram`, timeout validation, and AMD/ROCm edge/timeout tests.
3. `E-03` (`tests/test_hpc_hydration_e2e.py`, `tests/test_reproducibility_assessment.py`): Add `meta_snapshot` containment/sanitization tests and `_has_recorded_seed_annotation` cap/corrupt/null tests.
4. `E-04` (`tests/test_checks_commands.py`, `tests/test_reports.py`, `tests/test_methods_multi.py`): Add deterministic `live_findings()` tests, tighten `test_empty_python_version`, and cover >10 package truncation and suppressed packages.
5. `E-05` (validation): Run randomized pytest with coverage report.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none. Test-only plan modifying strictly the seven declared test files.
- Under-scope: none. All five coverage findings (`TEST-C3`, `TEST-C4`, `TEST-U6`, `TEST-U7`, `TEST-U10`) are covered with deterministic behavioral assertions.

## Required tests / validation

1. Targeted randomized pytest run with coverage:
   ```sh
   pytest -p randomly tests/test_resources.py tests/test_hardware.py tests/test_hpc_hydration_e2e.py tests/test_reproducibility_assessment.py tests/test_checks_commands.py tests/test_reports.py tests/test_methods_multi.py --cov=pubrun.capture.resources --cov=pubrun.capture.hardware --cov=pubrun.report.meta_snapshot --cov=pubrun.report.reproducibility --cov=pubrun.report.checks --cov=pubrun.report.methods --cov-report=term-missing -v
   ```

## Spec / documentation sync

N/A. Test-only additions verifying existing production contracts.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result (which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `pytest -v` and coverage output for `tests/test_resources.py` showing `partial`/`failed` manifest state, `stop()` idempotency, CPU clamp, and unconditional `peak_rss_bytes > 0` tests passing and hitting `src/pubrun/capture/resources.py`.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `pytest -v` and coverage output for `tests/test_hardware.py` showing `_parse_windows_reg_vram`, invalid/zero timeout, and AMD/ROCm edge/timeout tests passing and hitting `src/pubrun/capture/hardware.py`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `pytest -v` and coverage output for `tests/test_hpc_hydration_e2e.py` and `tests/test_reproducibility_assessment.py` confirming `meta_snapshot.py` (`26, 39, 46-54, 114-116`) and `reproducibility.py` (`_has_recorded_seed_annotation` cap/corrupt/null lines) are covered.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `pytest -v` and coverage output for `tests/test_checks_commands.py`, `tests/test_reports.py`, and `tests/test_methods_multi.py` confirming `checks.py` `live_findings()` branches and `methods.py` truncation/suppressed branches are covered.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted complete output of the command in `## Required tests / validation`, exiting `0` with zero failures and confirming coverage gains across all six target modules.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

1. **Open questions and approval:** Do not execute until explicit human approval is recorded (`aw ipd set approved dqaj9a --by-human` or `aw set approved assess-bt --by-human`).
2. **Scope declaration:** Modify only the seven declared `Scope-Paths`.
3. **Validation honesty:** Paste actual command outputs from this workspace for every `V-*` item.
4. **Commits and push policy:** Commit only files modified for this plan through `aw commit dqaj9a -- <paths>`. Never push, tag, or publish.
5. **Lifecycle finalization:** Finalize via `aw ipd finalize dqaj9a` (or let the runner finalize) only after every `E-*` is `performed` and every `V-*` is `pass`.
