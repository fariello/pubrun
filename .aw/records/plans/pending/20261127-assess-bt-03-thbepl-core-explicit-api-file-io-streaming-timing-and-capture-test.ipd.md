# IPD: Core explicit API file IO streaming timing and capture test hardening

- Date: 2026-11-27
- Kind: child
- Concern: Fix `pubrun.popen()` POSIX signal exit decoding (`BUG-C5`) and `file_io` small-chunk streaming hash timing (`BUG-E3`), and close high/medium testing gaps across `tests/test_explicit_api.py`, `tests/test_runtime_safety.py`, `tests/test_file_io_provenance.py`, and `tests/test_file_registration.py` (`TEST-C1`/`TEST-I3`, `TEST-C2`, `TEST-C5`, `TEST-C6`, `TEST-C7` manual `Path.cwd`, `TEST-C9` file I/O pinning, `TEST-I7` fixed sleeps).
- Scope: Fix `src/pubrun/core.py::_PopenPipeProxy.close` and `src/pubrun/capture/file_io.py::ProvenanceFileProxy._update_stream_hash`, and harden `tests/test_explicit_api.py` (leaving `test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively` untouched for pending plan `8o6o83`), `tests/test_runtime_safety.py`, `tests/test_file_io_provenance.py`, and `tests/test_file_registration.py`.
- Scope-Paths: src/pubrun/core.py, src/pubrun/capture/file_io.py, tests/test_explicit_api.py, tests/test_runtime_safety.py, tests/test_file_io_provenance.py, tests/test_file_registration.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Fix pubrun.popen POSIX signal decoding and small-chunk stream hash timing; close explicit API, symlink-escape, and file_io coverage gaps
- Work-Kind: bug
- Priority: high
- Set: assess-bt
- Order: 3
- Highest E allocated: 05
- Author: Antigravity
- Id: thbepl

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-27 to-review (Antigravity): Authored review-ready child IPD from parallel `/assess bugs` and `/assess testing` audits on HEAD `512ee68` / `8f2aacd`.
- 2026-11-27 draft (Antigravity): created.

## Goal

Fix POSIX signal-terminated exit-code corruption in `pubrun.popen()` and small-chunk `max_total_hash_seconds` timing bypass in `ProvenanceFileProxy._update_stream_hash`, while eliminating background `pubrun-hw` thread races in `tests/test_explicit_api.py` and closing high-priority security (`artifact`/`report` symlink escapes), explicit-API error-path, and `file_io` concurrency/re-registration test gaps.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix core `popen` signal decoding and `file_io` streaming hash timing

- [ ] E-01 Fix POSIX signal-terminated exit decoding in `src/pubrun/core.py::popen` (`_PopenPipeProxy.close`) (`BUG-C5`):
  - On POSIX, when `isinstance(exit_status, int)`: if `exit_status < 0 and (exit_status & 0xff) == 0`, decode `rc = exit_status >> 8` (`-signum`); else if `os.WIFEXITED(exit_status)` use `os.WEXITSTATUS(exit_status)`; else if `os.WIFSIGNALED(exit_status)` use `-os.WTERMSIG(exit_status)`; else `exit_status`.
  - Depends on: none
  - Expected outcome: `pubrun.popen("kill -TERM $$")` and `pubrun.popen("kill -9 $$")` record `-15` and `-9` (matching `pubrun.subprocess.run` and `SubprocessSpy`) instead of `241` and `247`.
  - Execution state: pending

- [ ] E-02 Fix small-chunk streaming hash timing in `src/pubrun/capture/file_io.py::ProvenanceFileProxy._update_stream_hash` (`BUG-E3`):
  - When `budget.max_total_hash_seconds > 0.0`, time every `self._stream_hasher.update(data)` call into `self._stream_elapsed` while keeping the `DEFAULT_CHUNK_SIZE` throttle strictly for the locked `budget.check_stream_progress(...)` call. Keep the zero-timer fast path only when `budget.max_total_hash_seconds == 0.0`.
  - Depends on: none
  - Expected outcome: Small-chunk streaming I/O (<64 KiB reads/writes) enforces `max_total_hash_seconds` accurately and records realistic `hash_duration_seconds`.
  - Execution state: pending

### Task group 2: Harden explicit API, runtime safety, and file I/O test suites

- [ ] E-03 Eliminate `pubrun-hw` thread races, add explicit-API failure/edge tests, and clean up manual `Path.cwd` mutation in `tests/test_explicit_api.py` (`TEST-C1`/`TEST-I3`, `TEST-C6`, `TEST-C7`, `BUG-C5`):
  - Pass `capture={"hardware": {"depth": "off"}, "resources": {"depth": "off"}}` in `test_explicit_subprocess_popen_wait_communicate_poll_timeout_and_failure`, `test_explicit_popen_monotonic_and_launch_failure_schema`, `test_explicit_subprocess_run_monotonic_and_schema`, and `test_manual_subprocess_provenance_isolation_cap_zero_bool_and_concurrency`. Do NOT edit `test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively` (owned by pending plan `8o6o83`).
  - Add behavioral tests covering: (a) POSIX `pubrun.popen` signal termination (`kill -TERM $$` -> `-15`), non-zero exit (`exit 5` -> `5`, `capture_state.status == "failed"`), and double-`close()` idempotency; (b) `pubrun.print` timestamped multi-line output (`console.capture_mode="standard"`), simulated write `OSError` recovery, and concurrent multi-threaded calls; (c) failing `cProfile.Profile.dump_stats` and fake `yappi` `save()` cleaning up the 0-byte sentinel `.prof` file with no `profile_saved` event.
  - Replace direct `Path.cwd = staticmethod(lambda: tmp_path)` assignments with `isolated_cwd` / `monkeypatch.chdir`.
  - Depends on: E-01
  - Expected outcome: `tests/test_explicit_api.py` has zero background `pubrun-hw` interference and covers all explicit `popen`/`print`/`phase` failure paths.
  - Execution state: pending

- [ ] E-04 Add symlink-escape security tests, replace fixed sleeps, and harden `file_io` tests in `tests/test_runtime_safety.py`, `tests/test_file_io_provenance.py`, and `tests/test_file_registration.py` (`TEST-C2`, `TEST-C5`, `TEST-C7`, `TEST-C9`, `TEST-I7`, `BUG-E3`):
  - In `tests/test_runtime_safety.py`: add symlink-escape and `"."` target tests for `pubrun.artifact()` / `pubrun.report()` (symlink to outside directory, symlink to `manifest.json`, and `"."`, skipping cleanly where symlinks cannot be created), and replace fixed-sleep thread handshakes (`time.sleep`) with `threading.Event` synchronization.
  - In `tests/test_file_io_provenance.py`: add a small-chunk streaming hash budget regression test for `BUG-E3` (asserting `over_budget` under a tight cap and non-zero `hash_duration_seconds` under a generous cap), add a multi-threaded `threading.Barrier` test racing `pubrun.open()`, `register_input()`, and `register_output(defer=True)` against `max_tracked_files`, drop private-attribute assertions (`fh._budget._has_caps`, `fh._stream_valid`, `fh._stream_over_budget`) in favor of observable assertions (`TEST-C9`), and remove redundant manual `Path.cwd = staticmethod(...)` mutations (`TEST-C7`).
  - In `tests/test_file_registration.py`: add a test for re-registering an existing pending deferred output with `digest`, `verify_digest=True`, and `level` overrides confirming index eviction/reindex and finalization behavior (`TEST-C5`), and remove redundant manual `Path.cwd = staticmethod(...)` mutations (`TEST-C7`).
  - Depends on: E-02
  - Expected outcome: Symlink-escape security guards, small-chunk stream hash timing, concurrent `max_tracked_files`, and pending-output re-registration are behaviorally verified with zero private-field pinning or sleep flakes.
  - Execution state: pending

### Task group 3: Validate

- [ ] E-05 Run targeted `pytest -p randomly` with coverage and 3-OS `mypy` and record complete output:
  - Run all commands listed in `## Required tests / validation` and verify exit `0`.
  - Depends on: E-03, E-04
  - Expected outcome: All targeted tests pass under `-p randomly`, targeted coverage lines are hit, and 3-OS `mypy` exits `0`.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `tests/test_explicit_api.py::test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively` is already assigned to pending plan `8o6o83` (graduated from backlog item `7jd8g1`); leave that function untouched here to avoid merge conflict with `8o6o83`.
- `tests/conftest.py::isolated_cwd` already isolates working directory per test via `monkeypatch.chdir`; direct `Path.cwd = staticmethod(...)` overwrites are unnecessary.
- `src/pubrun/core.py::_resolve_within_run_dir` is the containment gate used by both `pubrun.artifact()` and `pubrun.report()`.

## Findings

| ID | Concerns | Severity | Remediation Risk | Persona | Summary |
|---|---|---|---|---|---|
| `BUG-C5` | bugs | Medium | Low (`functionality`) | Software / QA Engineer | `pubrun.popen()` corrupts POSIX signal-terminated exit codes (`-9 -> 247`, `-15 -> 241`). |
| `BUG-E3` | bugs | Medium | Low (`functionality`) | QA Engineer | `ProvenanceFileProxy._update_stream_hash` leaves small-chunk (<64 KiB) updates untimed, bypassing `max_total_hash_seconds`. |
| `TEST-C1` / `TEST-I3` | testing | High | Low (`functionality`) | Testing Expert | Four tests in `tests/test_explicit_api.py` monkeypatch `time`/`Popen.__init__` while background `pubrun-hw` is running. |
| `TEST-C2` | testing | High | Low (`security`) | QA Engineer | Missing symlink-escape and `"."` target security tests for `pubrun.artifact()` / `pubrun.report()`. |
| `TEST-C5` | testing | Medium | Low (`functionality`) | Testing Expert | Pending-output re-registration index eviction and multi-threaded `max_tracked_files` cap are untested. |
| `TEST-C6` | testing | Medium | Low (`functionality`) | QA Engineer | Untested `pubrun.popen` non-zero/double-close, `pubrun.print` timestamped/error/concurrency, and `phase.__exit__` 0-byte `.prof` rollback. |
| `TEST-C7` (partial) | testing | Medium | Low (`functionality`) | Testing Expert | Manual `Path.cwd = staticmethod(...)` overwrites in `test_explicit_api.py`, `test_file_io_provenance.py`, and `test_file_registration.py`. |
| `TEST-C9` (partial) | testing | Low | Low (`complexity`) | Testing Expert | Private attribute assertions (`fh._budget._has_caps`, `fh._stream_valid`, `fh._stream_over_budget`) in `tests/test_file_io_provenance.py`. |
| `TEST-I7` (partial) | testing | Medium | Low (`functionality`) | Testing Expert | Fixed-sleep thread handshakes in `tests/test_runtime_safety.py`. |

## Proposed changes (ordered, validatable)

1. `E-01` (`src/pubrun/core.py`): Fix POSIX signal exit-code decoding in `_PopenPipeProxy.close`.
2. `E-02` (`src/pubrun/capture/file_io.py`): Time every `update()` call when `max_total_hash_seconds > 0.0` while keeping the 64 KiB lock-check throttle.
3. `E-03` (`tests/test_explicit_api.py`): Disable background hardware/resources in the 4 racy tests, add explicit `popen`/`print`/`phase` failure tests, and clean up `Path.cwd`.
4. `E-04` (`tests/test_runtime_safety.py`, `tests/test_file_io_provenance.py`, `tests/test_file_registration.py`): Add symlink-escape, small-chunk budget, concurrent cap, and pending-digest re-registration tests; replace fixed sleeps and private field pins.
5. `E-05` (validation): Run randomized pytest with coverage and 3-OS `mypy`.

## Deferred / out of scope (with reason)

- Fixing the `pubrun-hw` race in `tests/test_explicit_api.py::test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively`: already owned by pending plan `8o6o83` (graduated from `7jd8g1`).
  - Carrier: 8o6o83

## Scope check

- Over-scope: none. Only the two affected production modules and four directly paired test files are modified.
- Under-scope: none. All findings listed in `## Findings` are covered with explicit behavioral tests.

## Required tests / validation

1. Targeted randomized pytest with coverage on `core` and `file_io`:
   ```sh
   pytest -p randomly tests/test_explicit_api.py tests/test_runtime_safety.py tests/test_file_io_provenance.py tests/test_file_registration.py --cov=pubrun.core --cov=pubrun.capture.file_io --cov-report=term-missing -v
   ```
2. Three-OS static type check:
   ```sh
   mypy && mypy --platform win32 && mypy --platform darwin
   ```

## Spec / documentation sync

N/A. Restores documented POSIX signal return-code parity (`-signum`) and `max_total_hash_seconds` budget enforcement without altering public configuration keys.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result (which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- src/pubrun/core.py` and passing pytest output from `tests/test_explicit_api.py` exercising `pubrun.popen` with `kill -TERM $$` (`-15`), `exit 5`, and double-`close()`.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- src/pubrun/capture/file_io.py` and passing pytest output from `tests/test_file_io_provenance.py` verifying small-chunk streaming enforces `max_total_hash_seconds` (`over_budget`) and reports non-zero `hash_duration_seconds`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- tests/test_explicit_api.py` confirming the 4 racy tests pass `hardware.depth="off"` (while leaving `test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively` untouched), no manual `Path.cwd = staticmethod(...)` remains, and passing pytest output for all newly added `popen`/`print`/`phase` tests.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `git diff -- tests/test_runtime_safety.py tests/test_file_io_provenance.py tests/test_file_registration.py` and passing pytest output confirming symlink-escape, concurrent `max_tracked_files`, and pending-digest re-registration tests pass and private `_budget._has_caps`/`_stream_valid`/`_stream_over_budget` assertions are removed.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted complete output of both commands in `## Required tests / validation`, both exiting `0` with coverage confirming the targeted branches in `src/pubrun/core.py` and `src/pubrun/capture/file_io.py` are hit.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

1. **Open questions and approval:** Do not execute until explicit human approval is recorded (`aw ipd set approved thbepl --by-human` or `aw set approved assess-bt --by-human`).
2. **Scope declaration:** Modify only the six declared `Scope-Paths`.
3. **Validation honesty:** Paste actual command outputs from this workspace for every `V-*` item.
4. **Commits and push policy:** Commit only files modified for this plan through `aw commit thbepl -- <paths>`. Never push, tag, or publish.
5. **Lifecycle finalization:** Finalize via `aw ipd finalize thbepl` (or let the runner finalize) only after every `E-*` is `performed` and every `V-*` is `pass`.
