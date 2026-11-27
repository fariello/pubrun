# IPD: Global test isolation assertion hardening and sleep or pinning cleanup

- Date: 2026-11-27
- Kind: child
- Concern: Close global test-isolation leaks (`TEST-C7`, `TEST-I4`), tighten vacuous/hedged/does-not-throw assertions (`TEST-C8`, `TEST-I10`), and eliminate fixed-sleep synchronization and private-slot pinning in `tests/test_signals.py` (`TEST-C9`, `TEST-I7`).
- Scope: Harden `tests/conftest.py` (user-config isolation + resetting 7 omitted module-level caches/latches), add real-file `load_user_config()` tests in `tests/test_config.py`, and tighten assertions / replace sleeps and private pinning across `tests/test_api.py`, `tests/test_edge_cases.py`, `tests/test_import_modes.py`, `tests/test_signals.py`, `tests/test_capture.py`, and `tests/test_events.py`.
- Scope-Paths: tests/conftest.py, tests/test_config.py, tests/test_api.py, tests/test_edge_cases.py, tests/test_import_modes.py, tests/test_signals.py, tests/test_capture.py, tests/test_events.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Isolate host user config and reset 7 module caches in conftest.py, tighten vacuous assertions, and replace fixed sleeps and private slot pins
- Work-Kind: followup
- Priority: medium
- Set: assess-bt
- Order: 8
- Highest E allocated: 05
- Author: Antigravity
- Id: kgoymu

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-27 to-review (Antigravity): Authored review-ready child IPD from `/assess testing` Slices 1 and 3 on HEAD `512ee68` / `8f2aacd`.
- 2026-11-27 draft (Antigravity): created.

## Goal

Ensure the test suite is hermetically isolated from host `~/.config/pubrun/config.toml` and cross-test module-level cache/latch state under arbitrary `pytest-randomly` orderings, replace vacuous or hedged assertions with exact behavioral contract checks, and remove fixed-sleep thread races and private `__slots__` pinning in `tests/test_signals.py`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Hermetic `conftest.py` isolation and user-config coverage

- [ ] E-01 Isolate host user config and reset all 7 omitted module-level caches/latches in `tests/conftest.py`, and add real-file `load_user_config()` tests in `tests/test_config.py` (`TEST-C7`, `TEST-I4`):
  - In `tests/conftest.py`, add an autouse fixture (or extend `pubrun_state_isolation`) that points `XDG_CONFIG_HOME` and `APPDATA` at a clean empty directory under `tmp_path_factory` so a developer's real `~/.config/pubrun/config.toml` cannot pollute tests.
  - In `tests/conftest.py::pubrun_state_isolation`, reset all 7 module-level caches/latches currently omitted between tests: `signals._timed_out_locks`, `file_io._warned_invalid_algorithms`, `events._warned_invalid_durability`, `core._debug_enabled` (or diagnostic debug latch), `__init__._cached_version`, `core._INACTIVE_POLICY_CACHE` / `_INACTIVE_POLICY_MEMO` (clearing via module helpers if present, without forcing eager imports of unloaded modules).
  - In `tests/test_config.py`, add real-file behavioral tests for `load_user_config()` covering valid TOML and malformed TOML under a temporary `XDG_CONFIG_HOME` (and `APPDATA` where applicable).
  - Depends on: none
  - Expected outcome: Running the suite with a hostile host `XDG_CONFIG_HOME/pubrun/config.toml` (`profile = "deep"`, `on_inactive_annotate = "error"`) stays 100% green, and cross-test cache/warning-latch leakage is eliminated.
  - Execution state: pending

### Task group 2: Tighten vacuous assertions and clean up sleeps and private pinning

- [ ] E-02 Tighten vacuous and drifted assertions in `tests/test_api.py`, `tests/test_edge_cases.py`, and `tests/test_import_modes.py` (`TEST-C8`, `TEST-I10`):
  - In `tests/test_api.py`: in `TestDiff.test_diff_with_ignores`, assert ignored prefixes do not appear in `result["modified"] | result["added"] | result["removed"]`; in `TestPhase.test_phase_context_manager` and `test_phase_with_exception`, assert exact `"phase_start"` / `"phase_end"` and `payload["error"] == "ValueError"`; in `TestManifestSchema.test_capture_state_present_in_sections`, assert `isinstance(data, dict)` unconditionally before checking `"capture_state" in data`; add concrete post-condition assertions to any "does-not-throw" tests (`TEST-I10`).
  - In `tests/test_edge_cases.py`: in `TestDiffRobustness.test_unflatten_prefix_collision`, assert concrete collision preservation structure rather than bare `assert result`.
  - In `tests/test_import_modes.py`: align allowed-mode tuples in `test_manifest_imports_has_correct_mode` and `test_lock_file_contains_import_mode` with `VALID_MODES` (including `"full"`).
  - Depends on: E-01
  - Expected outcome: Every tightened test fails when its contract is broken rather than passing vacuously.
  - Execution state: pending

- [ ] E-03 Clean up `tests/test_signals.py` (`TEST-C9`, `TEST-I7`, `TEST-I10`):
  - Remove the private tuple-equality pin `finalization_lock.__slots__ == ("_lock", "_timeout", "_acquired")` in `test_finalization_lock_uses_slots_and_releases_on_exception` while keeping `assert not hasattr(ctx, "__dict__")` and behavioral exception-release checks (`TEST-C9`).
  - Replace fixed-sleep thread handshakes (`time.sleep` around `test_signals.py` lines 715 and 727) with deterministic `threading.Event` coordination (`TEST-I7`).
  - Add concrete post-condition assertions to any "does-not-throw" tests in `tests/test_signals.py` (`TEST-I10`).
  - Depends on: E-01
  - Expected outcome: `tests/test_signals.py` tests observable locking and signal outcomes without sleep races or private-slot coupling.
  - Execution state: pending

- [ ] E-04 Add post-condition assertions to "does-not-throw" tests in `tests/test_capture.py` and `tests/test_events.py` (`TEST-I10`):
  - Audit and tighten tests in `tests/test_capture.py` and `tests/test_events.py` that currently execute a call without asserting observable return values, manifest fields, logged warnings, or written event records.
  - Depends on: E-01
  - Expected outcome: Every test in `tests/test_capture.py` and `tests/test_events.py` asserts an observable post-condition.
  - Execution state: pending

### Task group 3: Validate under hostile host config and randomized ordering

- [ ] E-05 Run targeted `pytest -p randomly` both normally and under a hostile temporary `XDG_CONFIG_HOME` and record complete output:
  - Run both commands listed in `## Required tests / validation` and verify exit `0`.
  - Depends on: E-02, E-03, E-04
  - Expected outcome: All targeted test files pass under `-p randomly` even when host `XDG_CONFIG_HOME` contains hostile pubrun settings.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `tests/conftest.py::pubrun_state_isolation` must avoid importing optional or lazy submodules that were not yet loaded by the test (`sys.modules.get(...)` pattern) so lazy-import tests stay accurate.
- `tests/test_api.py::TestInactivePolicyCache` previously needed a local `empty_user_config_dir` fixture specifically because `tests/conftest.py` did not isolate `XDG_CONFIG_HOME` / `APPDATA`.

## Findings

| ID | Concerns | Severity | Remediation Risk | Persona | Summary |
|---|---|---|---|---|---|
| `TEST-C7` | testing | Medium | Low (`functionality`) | Testing Expert | `tests/conftest.py` does not isolate `XDG_CONFIG_HOME`/`APPDATA`, letting host `~/.config/pubrun/config.toml` break multiple tests. |
| `TEST-I4` | testing | Medium | Low (`functionality`) | Testing Expert | `tests/conftest.py` omits 7 module-level caches/latches (`_timed_out_locks`, `_warned_invalid_algorithms`, `_warned_invalid_durability`, `_debug_enabled`, `_cached_version`, `_INACTIVE_POLICY_CACHE`/`_MEMO`, `packages._CACHED_INDEX`) from per-test reset. |
| `TEST-C8` | testing | Medium | Low (`functionality`) | QA / Testing Expert | Vacuous, hedged, and drifted assertions in `test_api.py`, `test_edge_cases.py`, and `test_import_modes.py`. |
| `TEST-C9` (`test_signals.py`) | testing | Low | Low (`complexity`) | Testing Expert | Private `__slots__` tuple equality pin in `tests/test_signals.py::test_finalization_lock_uses_slots_and_releases_on_exception`. |
| `TEST-I7` (`test_signals.py`) | testing | Medium | Low (`functionality`) | Testing Expert | Fixed-sleep thread handshakes in `tests/test_signals.py`. |
| `TEST-I10` | testing | Low | Low (`functionality`) | QA Engineer | Eight "does-not-throw" tests lacking post-condition assertions across `test_api.py`, `test_capture.py`, `test_events.py`, and `test_signals.py`. |

## Proposed changes (ordered, validatable)

1. `E-01` (`tests/conftest.py`, `tests/test_config.py`): Isolate `XDG_CONFIG_HOME`/`APPDATA`, reset the 7 omitted caches/latches via `sys.modules.get(...)`, and add real-file `load_user_config()` tests.
2. `E-02` (`tests/test_api.py`, `tests/test_edge_cases.py`, `tests/test_import_modes.py`): Tighten vacuous/hedged/drifted assertions.
3. `E-03` (`tests/test_signals.py`): Remove private `__slots__` tuple equality, replace fixed sleeps with `threading.Event`, and add post-conditions.
4. `E-04` (`tests/test_capture.py`, `tests/test_events.py`): Add observable post-condition assertions to does-not-throw tests.
5. `E-05` (validation): Run randomized pytest normally and under a hostile temporary `XDG_CONFIG_HOME`.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none. Test-only changes strictly limited to the eight declared files.
- Under-scope: none. All global isolation, cache-reset, assertion-hardening, and signal-sleep/pinning findings are covered.

## Required tests / validation

1. Randomized pytest run across all modified suites:
   ```sh
   pytest -p randomly tests/test_config.py tests/test_api.py tests/test_edge_cases.py tests/test_import_modes.py tests/test_signals.py tests/test_capture.py tests/test_events.py -v
   ```
2. Hostile host user-config isolation verification:
   ```sh
   python3 -c 'import os, subprocess, sys, tempfile
   from pathlib import Path
   with tempfile.TemporaryDirectory() as td:
       cfg = Path(td) / "pubrun" / "config.toml"
       cfg.parent.mkdir(parents=True)
       cfg.write_text("[core]\nprofile = \"deep\"\n[events]\non_inactive_annotate = \"error\"\n", encoding="utf-8")
       env = dict(os.environ, XDG_CONFIG_HOME=td, APPDATA=td)
       rc = subprocess.call([sys.executable, "-m", "pytest", "-p", "randomly", "-q", "tests/test_config.py", "tests/test_api.py", "tests/test_edge_cases.py"], env=env)
       assert rc == 0, f"failed with hostile user config: rc={rc}"
       print("HOSTILE_USER_CONFIG_ISOLATION_OK")'
   ```

## Spec / documentation sync

N/A. Test-only isolation and assertion hardening.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result (which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- tests/conftest.py tests/test_config.py` confirming `XDG_CONFIG_HOME`/`APPDATA` isolation and all 7 module cache/latch resets (via `sys.modules.get`), plus passing output from Command 2 (`HOSTILE_USER_CONFIG_ISOLATION_OK`) and `tests/test_config.py` `load_user_config()` tests.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- tests/test_api.py tests/test_edge_cases.py tests/test_import_modes.py` confirming tightened assertions and `VALID_MODES` alignment, plus passing pytest output for those three files.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- tests/test_signals.py` confirming removal of private `__slots__` tuple equality and replacement of fixed sleeps with `threading.Event`, plus passing pytest output for `tests/test_signals.py`.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `git diff -- tests/test_capture.py tests/test_events.py` confirming added post-condition assertions, plus passing pytest output for both files.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted complete output of both commands in `## Required tests / validation`, exiting `0` with `HOSTILE_USER_CONFIG_ISOLATION_OK`.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

1. **Open questions and approval:** Do not execute until explicit human approval is recorded (`aw ipd set approved kgoymu --by-human` or `aw set approved assess-bt --by-human`).
2. **Scope declaration:** Modify only the eight declared `Scope-Paths`.
3. **Validation honesty:** Paste actual command outputs from this workspace for every `V-*` item.
4. **Commits and push policy:** Commit only files modified for this plan through `aw commit kgoymu -- <paths>`. Never push, tag, or publish.
5. **Lifecycle finalization:** Finalize via `aw ipd finalize kgoymu` (or let the runner finalize) only after every `E-*` is `performed` and every `V-*` is `pass`.
