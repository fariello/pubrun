# IPD: Capture resource hardware reproducibility and snapshot test coverage

- Date: 2026-11-27
- Kind: child
- Concern: Close high/medium behavioral coverage gaps in `ResourceWatcher`, `src/pubrun/capture/hardware.py`, `src/pubrun/report/meta_snapshot.py`, `src/pubrun/report/reproducibility.py`, `src/pubrun/report/checks.py`, and `src/pubrun/report/methods.py` (`TEST-C3`, `TEST-C4`, `TEST-U6`, `TEST-U7`, `TEST-U10`).
- Scope: Add deterministic behavioral tests (no production code changes) in `tests/test_resources.py`, `tests/test_hardware.py`, `tests/test_hpc_hydration_e2e.py`, `tests/test_reproducibility_assessment.py`, `tests/test_checks_commands.py`, `tests/test_reports.py`, and `tests/test_methods_multi.py`.
- Scope-Paths: tests/test_resources.py, tests/test_hardware.py, tests/test_hpc_hydration_e2e.py, tests/test_reproducibility_assessment.py, tests/test_checks_commands.py, tests/test_reports.py, tests/test_methods_multi.py
- Scope-Exceeded: .aw/records/backlog/open/20261127-wvdr46-01-wvdr46-avoid-import-lock-deadlock-when-coverage-py-probes.backlog.md (Required defect-report backlog carrier filed for adjacent coverage.py + pubrun auto-start import-lock deadlock observed during validation)
- Item-Dependencies: none
- Status: executed
- Readiness: go-pending-approval
- Review-Depth: complex
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

- 2026-11-28 executed (aw agy run model=Gemini-4-Neon-High): aw agy run self-finalize: dqaj9a verified (set assess-bt, attempt 1). [Scope reconciliation - out-of-scope .aw/records/backlog/open/20261127-wvdr46-01-wvdr46-avoid-import-lock-deadlock-when-coverage-py-probes.backlog.md: Required defect-report backlog carrier filed for adjacent coverage.py + pubrun auto-start import-lock deadlock observed during validation]
- 2026-11-28 approved (aw set): status set to approved
- 2026-11-27 reviewed (Antigravity): /plan-review (complex tier, single pass); added tuple-via-list cycle case for `meta_snapshot.py:49`, `b'"annotation"'` pre-filter requirement for `reproducibility.py:1198-1199`, started-watcher abort precondition in `E-01`, exact hardware parser/budget isolation in `E-02`, deterministic `os.cpu_count`/local-import isolation and multi-run variance pairing in `E-04`, and hardened execution gate; readiness `go-pending-approval`.
- 2026-11-27 to-review (Antigravity): Authored review-ready child Implementation Plan Document (IPD) from `/assess testing` Slices 1 and 2 on HEAD `512ee68` / `8f2aacd`.
- 2026-11-27 draft (Antigravity): created.

## Goal

Close empirically verified 0%-coverage branches in failure-state reporting (`ResourceWatcher` `partial` vs `failed`), newly landed `assess-8l` parsers and containment logic (`src/pubrun/capture/hardware.py`, `src/pubrun/report/meta_snapshot.py`, `src/pubrun/report/reproducibility.py::_has_recorded_seed_annotation`), and live-check/methods-truncation paths (`src/pubrun/report/checks.py`, `src/pubrun/report/methods.py`), replacing hedged/weak assertions with exact contract checks.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Cover capture failure states and hardware parser boundaries

- [x] E-01 Cover `ResourceWatcher` failure-state manifest reporting, idempotency, and central processing unit (CPU) clamping in `tests/test_resources.py` (`TEST-C3`):
  - Add deterministic unit tests exercising `ResourceWatcher._update_metrics()` + `to_manifest_dict()` for `_successful_samples == 0` (`capture_state == {"status": "failed", "detail": "resource polling failed on every sample"}`) and `_successful_samples > 0` followed by `max_failures` unreadable (`-1`) polls (`capture_state == {"status": "partial", "detail": "resource polling stopped after consecutive failures"}`).
  - Verify `ResourceWatcher.stop()` skips the final measurement after self-abort on an actually started watcher (start the watcher with a mocked `-1` `_poll_rss`, wait for `_stop_event.is_set()`, reset call counter, call `stop()`, and assert `_poll_rss` is not called again and `to_manifest_dict()["end_rss_bytes"] is None`), and verify `stop()` is idempotent on double-stop and on an unstarted watcher.
  - Verify negative `os.times()` CPU delta clamps to `0.0` in `ResourceWatcher._poll_cpu()`.
  - Make `isinstance(res["peak_rss_bytes"], int) and res["peak_rss_bytes"] > 0` unconditional when `sys.platform != "win32"` in `tests/test_resources.py::test_resources_watcher_threads` (keeping the `is not None` fallback only on `win32`) and remove the unused `_get_rss_windows` import at line 6.
  - Depends on: none
  - Expected outcome: `src/pubrun/capture/resources.py` failure-state, stop-idempotency, and CPU-clamp branches are covered and `test_resources_watcher_threads` fails loudly on non-Windows sampling timeout.
  - Execution state: performed

- [x] E-02 Add boundary and negative tests for `src/pubrun/capture/hardware.py` parsers and timeouts in `tests/test_hardware.py` (`TEST-C4`):
  - Parametrize `_parse_windows_reg_vram` tests covering negative signed 32-bit `int` conversion (`raw & 0xFFFFFFFF`), `bool` rejection (`True`/`False -> None`), `0 -> None`, and empty `bytes` (`b"" -> None`).
  - Test `get_hardware` with `total_timeout=0` (monkeypatching `subprocess.check_output` to fail if called, verifying zero GPU subprocess spawns and `capture_state["status"]` in `{"partial", "timeout"}` with exact detail) and test `_parse_positive_timeout` / `_parse_nonnegative_timeout` plus `get_hardware` on invalid timeout values (`float("nan")`, `float("inf")`, `-1`, `True`, `"bad"`) with mocked subprocess probes, confirming fallback to `_DEFAULT_HW_TIMEOUT` without spawning real tools or raising.
  - Test `_parse_amd_smi_json` and `_parse_rocm_smi_json` on malformed JavaScript Object Notation (JSON) (direct parser calls raise `json.JSONDecodeError`; `_get_gpus` degrades safely to `[]`), non-dict/non-list top-level JSON (`"123"`, `"null"` -> `[]`), top-level list vs single-dict payloads, `[N/A]` sentinels, integer megabyte (MB) `vram_size` fallback (`vram_size * 1024 * 1024`), non-`(B)` Radeon Open Compute (ROCm) video random-access memory (VRAM) key fallback (e.g. `"VRAM Total Memory (MB)": "16384 MB"` when `"VRAM Total Memory (B)"` is absent), and `amd-smi`/`rocm-smi` `subprocess.TimeoutExpired` budget marking (`budget.timed_out is True` with `sys.platform` patched to `"linux"`).
  - Depends on: none
  - Expected outcome: Freshly landed `assess-8l` hardware parser and timeout paths in `src/pubrun/capture/hardware.py` are behaviorally verified.
  - Execution state: performed

### Task group 2: Cover snapshot containment, seed-scan caps, and checks/methods gaps

- [x] E-03 Cover `src/pubrun/report/meta_snapshot.py` section-failure containment and `src/pubrun/report/reproducibility.py::_has_recorded_seed_annotation` scan caps in `tests/test_hpc_hydration_e2e.py` and `tests/test_reproducibility_assessment.py` (`TEST-U6`, `TEST-U7`):
  - In `tests/test_hpc_hydration_e2e.py`: monkeypatch `get_hardware` in `pubrun.report.meta_snapshot` to raise `RuntimeError("probe failed")`, call `generate_meta_snapshot(out, "basic")`, and assert the snapshot JSON is written with `hardware.capture_state == {"status": "failed", "detail": "probe failed"}` while sibling sections succeed; also test `_sanitize_json_value` on (a) self-referential dict, self-referential list, and tuple-via-list cycle (`lst = []; tup = (lst,); lst.append(tup)`) each raising `ValueError("Circular reference detected")` (covering lines `26`, `39`, and `49`), (b) tuples with not-a-number (`NaN`) / infinity (`Inf`) values returning sanitized tuples (lines `46-54`), and (c) non-finite float dict keys replaced by `"null"`.
  - In `tests/test_reproducibility_assessment.py`: test `_has_recorded_seed_annotation` on (a) a corrupt JSON line containing literal `"annotation"` (required to pass the `b'"annotation"'` pre-filter and hit `reproducibility.py:1198-1199`), a JSON array containing `"annotation"` (hitting line `1201`), and an annotation record with a non-dict `payload` (hitting line `1204`) followed by a valid seed annotation (returns `True`), (b) `{"type": "annotation", "payload": {"seed": null}}` (returns `False`), and (c) monkeypatched small `_SEED_SCAN_MAX_LINES` / `_SEED_SCAN_MAX_BYTES` caps with a valid seed line past either cap (returns `False`, hitting lines `1190` and `1193`).
  - Depends on: none
  - Expected outcome: Uncovered resilience and cap branches in `src/pubrun/report/meta_snapshot.py` and `src/pubrun/report/reproducibility.py` are covered.
  - Execution state: performed

- [x] E-04 Cover `src/pubrun/report/checks.py` `live_findings()`/`live_checks()` branches and `src/pubrun/report/methods.py` edge/truncation paths in `tests/test_checks_commands.py`, `tests/test_reports.py`, and `tests/test_methods_multi.py` (`TEST-U10`):
  - In `tests/test_checks_commands.py`: add deterministic monkeypatched tests (isolating `cwd` via `tmp_path`, `PUBRUN_OUTPUT_DIR`, `checks.os.cpu_count`, `checks.shutil.which`, `pubrun.capture.system_metrics.get_system_memory`, `pubrun.capture.system_metrics.get_load_average`, `pubrun.capture.filesystem.get_filesystem`, and `pubrun.capture.filesystem.probe_paths_live`) for `live_findings()` and `live_checks()` triggering `low_memory` (`"warn"`), `high_load` (`"warn"`), `git_missing` (`"info"`), `fs_hung_*` (`"warn"`), and `fs_slow_*` (`"warn"`), asserting exact finding codes, severities, and mapped `live_checks()` check statuses (`memory`, `load`, `git_available`, `filesystems`).
  - In `tests/test_reports.py`: tighten `test_empty_python_version` to assert `"Python unknown (Unknown)" in result`, and add a 12-package non-highlighted manifest test asserting `"and 2 additional packages (12 total)."` in `generate_report(...)` output.
  - In `tests/test_methods_multi.py`: add multi-run tests where contrasting manifests surface `_packages_of` variance in `generate_report_multi(...)`, asserting `"(+2 more; 12 recorded)"` for a 12-package non-highlighted run and `"(package capture disabled)"` for a `capture_state.status == "suppressed"` run.
  - Depends on: none
  - Expected outcome: Weak "does not throw" assertions are replaced and uncovered `src/pubrun/report/checks.py` and `src/pubrun/report/methods.py` branches are verified.
  - Execution state: performed

### Task group 3: Validate coverage and randomized execution

- [x] E-05 Run targeted `pytest -p randomly` with coverage across all six target production modules and record complete output:
  - Run the command in `## Required tests / validation` and verify exit `0` and coverage hits on every targeted branch.
  - Depends on: E-01, E-02, E-03, E-04
  - Expected outcome: All seven test files pass under `-p randomly` with targeted branches covered.
  - Execution state: performed

## Project conventions discovered (Step 0)

- Full-suite baseline coverage at `512ee68` confirmed exact 0%-hit lines matching these findings: `src/pubrun/capture/resources.py` (`_poll_cpu` clamp L499-500, `to_manifest_dict` partial/failed L732-742), `src/pubrun/report/meta_snapshot.py` (83%, missing `26, 39, 46-54, 114-116`, where line `49` requires a tuple-through-mutable-container cycle), `src/pubrun/report/reproducibility.py` (`_has_recorded_seed_annotation` missing `1190, 1193, 1198-1199, 1201, 1204`, where lines `1198-1199` require a corrupt line containing literal `"annotation"`), `src/pubrun/report/checks.py` (live finding branches at `105, 112, 208, 240, 248`), and `src/pubrun/report/methods.py` (95%, missing `302-308, 422, 430`).
- Zero production source edits are needed for this plan; every test exercises real functions with deterministic inputs/mocks.

## Findings

| ID | Concerns | Severity | Remediation Risk | Persona | Summary |
|---|---|---|---|---|---|
| `TEST-C3` | testing | High | Low (`functionality`) | Testing / Quality Assurance (QA) Engineer | `ResourceWatcher` `partial` vs `failed` manifest reporting, `stop()` idempotency, and CPU wrap clamping are uncovered; resident set size (`peak_rss_bytes`) check silently masks timeout. |
| `TEST-C4` | testing | Medium | Low (`functionality`) | Testing / QA Engineer | Freshly landed `src/pubrun/capture/hardware.py` VRAM/Advanced Micro Devices (AMD)/ROCm parsers and timeout validation lack negative and boundary tests. |
| `TEST-U6` | testing | Medium | Low (`functionality`) | Reliability / High-Performance Computing (HPC) Engineer | `src/pubrun/report/meta_snapshot.py::_gather` section-failure containment and `_sanitize_json_value` circular-ref/tuple/NaN guards have 0% coverage. |
| `TEST-U7` | testing | Medium | Low (`functionality`) | Reproducibility / QA Engineer | `src/pubrun/report/reproducibility.py::_has_recorded_seed_annotation` line/byte scan caps, corrupt-line skipping, and `seed: null` handling have 0% coverage. |
| `TEST-U10` | testing | Low | Low (`functionality`) | QA Engineer | Weak assertions in `tests/test_checks_commands.py` and `tests/test_reports.py` leave `live_findings()` branches and >10 package truncation / suppressed packages untested. |

## Proposed changes (ordered, validatable)

1. `E-01` (`tests/test_resources.py`): Add `ResourceWatcher` failure-state, started-abort/double-stop/unstarted `stop()`, and CPU-clamp tests; tighten `peak_rss_bytes` assertion on non-Windows and drop unused import.
2. `E-02` (`tests/test_hardware.py`): Add `_parse_windows_reg_vram`, mocked timeout validation, and AMD/ROCm edge/timeout tests.
3. `E-03` (`tests/test_hpc_hydration_e2e.py`, `tests/test_reproducibility_assessment.py`): Add `meta_snapshot` containment/sanitization tests (including tuple-via-list cycle) and `_has_recorded_seed_annotation` cap/corrupt-with-`"annotation"`/null tests.
4. `E-04` (`tests/test_checks_commands.py`, `tests/test_reports.py`, `tests/test_methods_multi.py`): Add deterministic `live_findings()`/`live_checks()` tests, tighten `test_empty_python_version`, and cover >10 package truncation and suppressed-package variance.
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

- [x] V-01 validates E-01
  - Required evidence: Pasted `pytest -v` and coverage output for `tests/test_resources.py` showing `partial`/`failed` manifest state, started-abort/double-stop/unstarted `stop()`, CPU clamp, and unconditional non-Windows `peak_rss_bytes > 0` tests passing and hitting `src/pubrun/capture/resources.py` lines `499-500` and `732-742`.
  - Observed evidence: Ran `PYTHONPATH=src PUBRUN_IMPORT_MODE=minimal pytest -p randomly tests/test_resources.py --cov=pubrun.capture.resources --cov-report=term-missing -v` (seed `3616371313`; `PUBRUN_IMPORT_MODE=minimal` isolates pytest-cov dotted-module `find_spec` from triggering auto-start import-lock deadlock on Python 3.14): `12 passed in 1.53s` including `test_resources_watcher_threads`, `test_resource_watcher_failed_manifest_state_when_no_successful_samples`, `test_resource_watcher_partial_manifest_state_after_successful_then_failures`, `test_resource_watcher_stop_skips_final_poll_after_self_abort`, `test_resource_watcher_stop_idempotent_double_stop_and_unstarted`, and `test_cpu_poll_clamps_negative_delta_to_zero`. Coverage: `src/pubrun/capture/resources.py 513 251 51%` with `Missing` ending `..., 459-461, 506-508, ..., 714-718, 754-758` (confirming lines `499-500` and `732-742` are covered).
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: Pasted `pytest -v` and coverage output for `tests/test_hardware.py` showing `_parse_windows_reg_vram`, invalid/zero timeout, and AMD/ROCm edge/timeout tests passing and hitting `src/pubrun/capture/hardware.py`.
  - Observed evidence: Ran `PYTHONPATH=src PUBRUN_IMPORT_MODE=minimal pytest -p randomly tests/test_hardware.py --cov=pubrun.capture.hardware --cov-report=term-missing -v` (seed `1268542361`): `42 passed in 0.81s` including all 12 `test_parse_windows_reg_vram_boundaries` cases, `test_get_hardware_zero_total_timeout_spawns_no_subprocesses`, `test_timeout_parsers_reject_invalid_values` (8 cases), `test_timeout_parsers_zero_and_valid_values`, `test_get_hardware_invalid_timeouts_fall_back_to_default` (5 cases), `test_parse_amd_smi_and_rocm_smi_boundaries_and_malformed_json`, and `test_amd_and_rocm_smi_timeout_marks_capture_budget` (`amd-smi`, `rocm-smi`). Coverage: `src/pubrun/capture/hardware.py 524 106 80%` with zero missing lines across `_parse_windows_reg_vram` (116-127), `_parse_amd_smi_json` (263-325), `_parse_rocm_smi_json` (328-385), `_parse_positive_timeout`/`_parse_nonnegative_timeout` (388-411), `amd-smi`/`rocm-smi` timeout paths (656-705), and `get_hardware` (786-849).
  - Result: pass

- [x] V-03 validates E-03
  - Required evidence: Pasted `pytest -v` and coverage output for `tests/test_hpc_hydration_e2e.py` and `tests/test_reproducibility_assessment.py` confirming `src/pubrun/report/meta_snapshot.py` (`26, 39, 46-54, 114-116`) and `src/pubrun/report/reproducibility.py` (`1190, 1193, 1198-1199, 1201, 1204`) are covered.
  - Observed evidence: Ran `PYTHONPATH=src PUBRUN_IMPORT_MODE=minimal pytest -p randomly tests/test_hpc_hydration_e2e.py tests/test_reproducibility_assessment.py --cov=pubrun.report.meta_snapshot --cov=pubrun.report.reproducibility --cov-report=term-missing -v` (seed `407848441`): `30 passed in 1.09s` including `test_generate_meta_snapshot_contains_section_failure`, `test_sanitize_json_value_cycles_tuples_and_non_finite_keys`, `TestHasRecordedSeedAnnotation::test_skips_corrupt_non_dict_and_non_dict_payload_before_valid_seed`, `test_seed_null_returns_false`, and `test_scan_stops_at_line_and_byte_caps`. Coverage: `src/pubrun/report/meta_snapshot.py 113 7 94%` (`Missing: 101, 171-174, 178-179`; confirming `26, 39, 46-54, 114-116` are covered) and `src/pubrun/report/reproducibility.py 1569 785 50%` (`Missing` skips `1170-1207`; confirming `1190, 1193, 1198-1199, 1201, 1204` are covered).
  - Result: pass

- [x] V-04 validates E-04
  - Required evidence: Pasted `pytest -v` and coverage output for `tests/test_checks_commands.py`, `tests/test_reports.py`, and `tests/test_methods_multi.py` confirming `src/pubrun/report/checks.py` `live_findings()`/`live_checks()` branches (`105, 112, 208, 240, 248`) and `src/pubrun/report/methods.py` truncation/suppressed branches (`302-308, 422, 430`) are covered.
  - Observed evidence: Ran `PYTHONPATH=src PUBRUN_IMPORT_MODE=minimal pytest -p randomly tests/test_checks_commands.py tests/test_reports.py tests/test_methods_multi.py --cov=pubrun.report.checks --cov=pubrun.report.methods --cov-report=term-missing -v` (seed `3442242138`): `192 passed in 6.87s` including `TestLiveChecksModel::test_live_findings_and_checks_deterministic_branches`, `TestGenerateReportDegradedManifests::test_empty_python_version`, `TestGenerateReportDegradedManifests::test_twelve_non_highlighted_packages_truncation`, `TestAggregateGenerator::test_non_highlighted_twelve_packages_truncation_variance`, and `TestAggregateGenerator::test_suppressed_packages_variance`. Coverage: `src/pubrun/report/checks.py 191 52 73%` (`Missing: 52-53, 58-59, 80-83, 99, 132-133, 138-143, 156, 170-171, 182, 187, 193-197, 199-204, 228-231, 253-254, 327, 329-337, 346-347, 368-370, 378-380`; confirming `105, 112, 208, 240, 248` are covered) and `src/pubrun/report/methods.py 342 16 95%` (`Missing: 16, 29, 89, 95, 98, 121, 149, 220, 226, 229, 281, 325, 365, 431, 479-480`; confirming `302-308, 422, 430` are covered).
  - Result: pass

- [x] V-05 validates E-05
  - Required evidence: Pasted complete output of the command in `## Required tests / validation`, exiting `0` with zero failures and confirming coverage gains across all six target modules.
  - Observed evidence: Ran `PYTHONPATH=src PUBRUN_IMPORT_MODE=minimal pytest -p randomly tests/test_resources.py tests/test_hardware.py tests/test_hpc_hydration_e2e.py tests/test_reproducibility_assessment.py tests/test_checks_commands.py tests/test_reports.py tests/test_methods_multi.py --cov=pubrun.capture.resources --cov=pubrun.capture.hardware --cov=pubrun.report.meta_snapshot --cov=pubrun.report.reproducibility --cov=pubrun.report.checks --cov=pubrun.report.methods --cov-report=term-missing -v` (seed `2624802708`): exit `0`, `276 passed in 8.83s`. Coverage summary: `src/pubrun/capture/hardware.py 524 106 80%`, `src/pubrun/capture/resources.py 513 251 51%`, `src/pubrun/report/checks.py 191 52 73%`, `src/pubrun/report/meta_snapshot.py 113 7 94%`, `src/pubrun/report/methods.py 342 16 95%`, `src/pubrun/report/reproducibility.py 1569 761 51%`, `TOTAL 3252 1193 63%`. Also ran randomized 7-file check without `--cov` (`pytest -p randomly -n 0 ...`: `276 passed in 13.37s`) and full repository suite via `aw suite` (`2570 passed in 103.20s`, exit `0`).
  - Result: pass

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

1. **Open questions and approval:** Do not execute until explicit human approval is recorded (`aw ipd set approved dqaj9a --by-human` or `aw set approved assess-bt --by-human`).
2. **Scope declaration:** Modify only the seven declared `Scope-Paths`. Any additional path requires an explicit `--scope-reason` / `--scope-ack` justification recorded in the plan before editing.
3. **Validation honesty:** Paste actual command outputs from this workspace for every `V-*` item.
4. **Commits and push policy:** Commit only files modified for this plan through `aw commit dqaj9a -- <paths>`. Never use `git add -A`, bare `git add .`, `git commit -a`, or raw `git commit`. Never push, tag, or publish.
5. **Lifecycle finalization:** When executed under a runner (`aw oc run` / `aw agy run`), leave finalization to the runner and do not call `aw ipd finalize`. When executed standalone by hand, finalize via `aw ipd finalize dqaj9a` only after every `E-*` is `performed` and every `V-*` is `pass`; never hand-roll `git mv`.
