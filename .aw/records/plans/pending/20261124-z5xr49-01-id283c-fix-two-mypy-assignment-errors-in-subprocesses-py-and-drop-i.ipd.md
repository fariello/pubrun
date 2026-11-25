# IPD: Fix two mypy assignment errors in subprocesses.py and drop it from ignore_errors

- Date: 2026-11-24
- Kind: child
- Concern: Static type safety and `[tool.mypy]` ratchet hygiene for `src/pubrun/capture/subprocesses.py`
- Scope: Resolve the two `[assignment]` mypy errors in `src/pubrun/capture/subprocesses.py` (`SubprocessSpy.install._drain` and `SubprocessSpy.finalize_all`) introduced by commit `edc6343` (`focjwv`), and remove `"pubrun.capture.subprocesses"` from the `[tool.mypy.overrides]` `ignore_errors = true` list in `pyproject.toml`.
- Scope-Paths: src/pubrun/capture/subprocesses.py, pyproject.toml
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: simple
- Short-Description: Fix 2 mypy assignment errors in subprocesses.py and remove it from pyproject.toml ignore_errors
- Work-Kind: bug
- Priority: medium
- From-Backlog: z5xr49
- Blocks-Release: next
- Set: z5xr49
- Order: 1
- Highest E allocated: 02
- Author: Antigravity
- Id: id283c
- Approval: 2026-11-25, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 approved (aw set): status set to approved
- 2026-11-25 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003
- 2026-11-25 to-review (Antigravity): graduated from backlog item `z5xr49` into a review-ready plan.
- 2026-11-25 draft (Antigravity): created.

## Goal

Clear the two `mypy` `[assignment]` errors introduced in `src/pubrun/capture/subprocesses.py` by executed plan `focjwv` (commit `edc6343`, unwaited `Popen` exit harvesting) and remove `"pubrun.capture.subprocesses"` from the legacy `ignore_errors = true` ratchet in `pyproject.toml` so CI type-checks `src/pubrun/capture/subprocesses.py` without changing runtime behavior.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix assignment narrowing and tighten mypy ratchet

- [x] E-01 In `src/pubrun/capture/subprocesses.py`, replace the local variable `rec` inside both `pending_running` loops with a distinct `proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)` binding instead of reassigning `rec` (`Dict[str, Any]`):
  - In `src/pubrun/capture/subprocesses.py::SubprocessSpy.install._drain` (the `if rc is not None:` block inside the `pending_running` loop), rename `rec` to `proc_rec` on all 3 lines (`proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)`, `if proc_rec is not None:`, `_complete_record(proc_rec, rc, time.time(), time.perf_counter())`). Leave the earlier `pending_exits.popleft()` `rec` binding unchanged.
  - In `src/pubrun/capture/subprocesses.py::SubprocessSpy.finalize_all` Phase 2 (the `pending_running` loop after `for rec in list(cls._records):`), rename every occurrence of `rec` in that block (all 8 occurrences across the assignment, the 4 `if` conditions, `live_procs.append`, and `seen_rec_ids.add`) to `proc_rec` (`proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)`). Leave the earlier `for rec in list(cls._records):` loop and the later Phase 3 and Phase 4 loops unchanged.
  - Shadowing hazard: `rec` (`Dict[str, Any]`) remains bound in the enclosing function scope from the preceding loop in both methods, and no existing test enters the `finalize_all` Phase 2 `pending_running` loop. Leaving any unrenamed `rec` inside either `pending_running` block passes both `mypy` and `pytest` while referencing the wrong record; verify every line of both blocks in the diff.
  - Depends on: none
  - Expected outcome: Both `[assignment]` errors in `src/pubrun/capture/subprocesses.py` (`SubprocessSpy.install._drain` and `SubprocessSpy.finalize_all`) are resolved with identical runtime behavior, Python 3.8-compatible `typing` annotations (`Optional`, `Dict`, and `Any` are already imported), and zero stale `rec` references inside either `pending_running` block.
  - Execution state: performed

- [x] E-02 In `pyproject.toml`, remove `"pubrun.capture.subprocesses",` from the `module = [...]` list of the `[[tool.mypy.overrides]]` block that sets `ignore_errors = true`, and update the adjacent comment from `# Remove each module as its existing errors are fixed (backlog items qqwebg and z5xr49).` to `# Remove each module as its existing errors are fixed (backlog item qqwebg).` (changing plural `items` to singular `item`).
  - Depends on: E-01
  - Expected outcome: `"pubrun.capture.subprocesses"` is no longer listed in the `[[tool.mypy.overrides]]` `ignore_errors = true` block in `pyproject.toml`, the comment reads `(backlog item qqwebg).`, and `python3 -m mypy --no-incremental` plus `python3 -m mypy --no-incremental src/pubrun` both exit 0 with no issues found.
  - Execution state: performed

## Project conventions discovered (Step 0)

- Cite code by SYMBOL (`path::Name`) or by a quoted content string, with a line number only appended to one of those and never alone (`IPD-C801`).
- `pyproject.toml` declares `requires-python = ">=3.8"`. `src/pubrun/capture/subprocesses.py` already imports `Any`, `Dict`, and `Optional` from `typing`, so use `Optional[Dict[str, Any]]` rather than PEP 604 `|` union syntax.
- Verified directly with `MYPYPATH=src python3 -m mypy --config-file /dev/null --explicit-package-bases --follow-imports=silent src/pubrun/capture/subprocesses.py` (`mypy` 2.3.1 on Linux): `src/pubrun/capture/subprocesses.py` has exactly two mypy errors:
  1. `src/pubrun/capture/subprocesses.py::SubprocessSpy.install._drain`: `rec = getattr(proc, "_pubrun_rec", None)` -> `Incompatible types in assignment (expression has type "Any | None", variable has type "dict[str, Any]") [assignment]`.
  2. `src/pubrun/capture/subprocesses.py::SubprocessSpy.finalize_all`: `rec = getattr(proc, "_pubrun_rec", None)` -> same `[assignment]` error.
- `pyproject.toml` `[[tool.mypy.overrides]]` (`ignore_errors = true`) lists `"pubrun.capture.subprocesses"` under the comment `# Remove each module as its existing errors are fixed (backlog items qqwebg and z5xr49).`.
- Cross-plan note: non-blocking pending plan `k6fs5k` (`Set: rand-mypy`, Order 4, `reviewed`) also renames these two `subprocesses.py` locals to `proc_rec`, removes `"pubrun.capture.subprocesses"` alongside the other five `pubrun.capture.*` entries from `pyproject.toml`, and adds behavioral coverage (`test_finalize_harvests_exit_code_of_collected_unwaited_child` in `tests/test_capture_mypy_guarded_paths.py`) for the `finalize_all` Phase 2 `pending_running` branch. Because `id283c` carries `- Blocks-Release: next`, it clears `subprocesses.py` ahead of the next release; if `id283c` executes before `k6fs5k`, those two edits in `k6fs5k` will already be satisfied.
- Subprocess capture and signal tests live in `tests/test_capture.py` and `tests/test_signals.py` (there is no `tests/test_subprocesses.py` file). `tests/test_capture.py::TestUnwaitedPopenHarvesting.test_cleanup_reaped_child_records_exit_code` exercises `_drain`'s `pending_running` branch; no existing test enters `finalize_all` Phase 2's `pending_running` branch.

## Findings

Executed plan `focjwv` (commit `edc6343`, unwaited `Popen` exit harvesting) reused local variable `rec` (already inferred as `Dict[str, Any]` from earlier loops) for `getattr(proc, "_pubrun_rec", None)` (`Any | None`) in two places inside `src/pubrun/capture/subprocesses.py`: `src/pubrun/capture/subprocesses.py::SubprocessSpy.install._drain` and `src/pubrun/capture/subprocesses.py::SubprocessSpy.finalize_all`. That caused executed plan `gzc672` (`mypy` CI type-check setup) to add `"pubrun.capture.subprocesses"` to the `[[tool.mypy.overrides]]` `ignore_errors = true` ratchet in `pyproject.toml`. Giving the optional lookup its own `Optional[Dict[str, Any]]` local variable (`proc_rec`) clears both errors with zero runtime change and lets `pyproject.toml` remove the module from the ratchet.

## Proposed changes (ordered, validatable)

1. **`src/pubrun/capture/subprocesses.py` (E-01):**
   - In `src/pubrun/capture/subprocesses.py::SubprocessSpy.install._drain`, replace the 3 lines in the `pending_running` `if rc is not None:` block:
     ```python
     proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)
     if proc_rec is not None:
         _complete_record(proc_rec, rc, time.time(), time.perf_counter())
     ```
   - In `src/pubrun/capture/subprocesses.py::SubprocessSpy.finalize_all` Phase 2, replace the 9 lines in the `pending_running` loop (all 8 `rec` occurrences):
     ```python
     proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)
     if (
         proc_rec is not None
         and proc_rec.get("exit_code") is None
         and "ended_at_utc" not in proc_rec
         and id(proc_rec) not in seen_rec_ids
     ):
         live_procs.append((proc_rec, proc))
         seen_rec_ids.add(id(proc_rec))
     ```
2. **`pyproject.toml` (E-02):**
   - Remove `"pubrun.capture.subprocesses",` from the `[[tool.mypy.overrides]]` (`ignore_errors = true`) `module = [...]` list and update the ratchet comment above it to `# Remove each module as its existing errors are fixed (backlog item qqwebg).`.

## Deferred / out of scope (with reason)

- Windows-only `mypy --platform win32` guards in `src/pubrun/capture/subprocesses.py::_decode_wait_status` (such as `os.WIFEXITED`): owned by pending plan `juoqy2` (`Set: rand-mypy`, Order 6).
  - Carrier: juoqy2
- Dedicated behavioral test for the `src/pubrun/capture/subprocesses.py::SubprocessSpy.finalize_all` Phase 2 `pending_running` branch (not reached by `tests/test_capture.py` or `tests/test_signals.py`): owned by sibling pending plan `k6fs5k` (`Set: rand-mypy`, Order 4, `E-04`).
  - Carrier: k6fs5k

## Scope check

- Over-scope: none. Only `src/pubrun/capture/subprocesses.py` and `pyproject.toml` are modified.
- Under-scope: none. Verified with `mypy` without `ignore_errors` that only these two errors exist in `src/pubrun/capture/subprocesses.py` on Linux; Windows-only guards and new `finalize_all` Phase 2 test coverage are carried by `juoqy2` and `k6fs5k`.

## Required tests / validation

- Run `python3 -m mypy --no-incremental` and `python3 -m mypy --no-incremental src/pubrun` and confirm both exit 0 with `Success: no issues found in <N> source files` (re-derived at execution time).
- Run `python3 -m pytest tests/test_capture.py tests/test_signals.py -v` and confirm all tests pass.
- Run `python3 scripts/sanitize_paths.py --check --all` and confirm exit code 0.

## Spec / documentation sync

No spec or documentation update is required. Verified by searching `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/`, and `.aw/records/specs/` for `z5xr49`, `capture.subprocesses`, and `ignore_errors`: `CONTRIBUTING.md` (`CONTRIBUTING.md#Development setup`) describes the `ignore_errors` override generically without naming individual modules, and no spec or user doc lists `pubrun.capture.subprocesses` or `z5xr49`.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [x] V-01 validates E-01
  - Required evidence: Paste `git diff src/pubrun/capture/subprocesses.py` showing only the two `pending_running` blocks in `SubprocessSpy.install._drain` (3 lines) and `SubprocessSpy.finalize_all` Phase 2 (9 lines) changed, with `proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)` and zero remaining `rec` references inside either `pending_running` block; plus actual output of `python3 -m pytest tests/test_capture.py tests/test_signals.py -v` showing all tests passing.
  - Observed evidence:
    1. `git diff src/pubrun/capture/subprocesses.py` (only the two `pending_running` blocks changed; zero remaining `rec` references inside either block):
    ```diff
    diff --git a/src/pubrun/capture/subprocesses.py b/src/pubrun/capture/subprocesses.py
    index eda6bb3..d3564e7 100644
    --- a/src/pubrun/capture/subprocesses.py
    +++ b/src/pubrun/capture/subprocesses.py
    @@ -221,9 +221,9 @@ class SubprocessSpy:
                             break
                         rc = getattr(proc, "returncode", None)
                         if rc is not None:
    -                        rec = getattr(proc, "_pubrun_rec", None)
    -                        if rec is not None:
    -                            _complete_record(rec, rc, time.time(), time.perf_counter())
    +                        proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)
    +                        if proc_rec is not None:
    +                            _complete_record(proc_rec, rc, time.time(), time.perf_counter())
                         else:
                             still_running.append(proc)
                     if still_running and state["active"]:
    @@ -625,15 +625,15 @@ class SubprocessSpy:
                             proc = pending_running.popleft()
                         except IndexError:
                             break
    -                    rec = getattr(proc, "_pubrun_rec", None)
    +                    proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)
                         if (
    -                        rec is not None
    -                        and rec.get("exit_code") is None
    -                        and "ended_at_utc" not in rec
    -                        and id(rec) not in seen_rec_ids
    +                        proc_rec is not None
    +                        and proc_rec.get("exit_code") is None
    +                        and "ended_at_utc" not in proc_rec
    +                        and id(proc_rec) not in seen_rec_ids
                         ):
    -                        live_procs.append((rec, proc))
    -                        seen_rec_ids.add(id(rec))
    +                        live_procs.append((proc_rec, proc))
    +                        seen_rec_ids.add(id(proc_rec))

                 # Phase 3: Poll each live Popen once outside _lock.
                 prev_poll = state["prev_popen_poll"]
    ```
    2. `python3 -m pytest tests/test_capture.py tests/test_signals.py -v` (exit code `0`; local interpreter and worktree paths redacted in header):
    ```text
    ============================= test session starts ==============================
    platform linux -- Python 3.14.6, pytest-8.2.2, pluggy-1.6.0 -- ~/venv/p3.14/bin/python3
    cachedir: .pytest_cache
    rootdir: <worktree-root>
    configfile: pyproject.toml
    plugins: anyio-4.14.1, cov-7.1.0, xdist-3.8.0
    collected 78 items

    tests/test_capture.py::TestInvocationCapture::test_rerun_command_present PASSED [  1%]
    tests/test_capture.py::TestInvocationCapture::test_argv_is_list PASSED   [  2%]
    tests/test_capture.py::TestInvocationCapture::test_working_directory_captured PASSED [  3%]
    tests/test_capture.py::TestSubprocessInterceptor::test_waited_subprocess_captured PASSED [  5%]
    tests/test_capture.py::TestSubprocessInterceptor::test_detached_subprocess_finalized PASSED [  6%]
    tests/test_capture.py::TestSubprocessInterceptor::test_os_system_captured PASSED [  7%]
    tests/test_capture.py::TestSubprocessInterceptor::test_disable_spy_context_manager PASSED [  8%]
    tests/test_capture.py::TestSubprocessInterceptor::test_shlex_fallback_on_bad_quotes PASSED [ 10%]
    tests/test_capture.py::TestSubprocessInterceptor::test_shlex_split_normal_string PASSED [ 11%]
    tests/test_capture.py::TestSubprocessInterceptor::test_shlex_split_list_input PASSED [ 12%]
    tests/test_capture.py::TestConsoleInterceptor::test_tqdm_compression PASSED [ 14%]
    tests/test_capture.py::TestConsoleInterceptor::test_console_manifest_structure PASSED [ 15%]
    tests/test_capture.py::TestConsoleInterceptor::test_console_off_mode PASSED [ 16%]
    tests/test_capture.py::TestConsoleInterceptor::test_multi_line_write PASSED [ 17%]
    tests/test_capture.py::TestFinalizeAll::test_marks_unwaited_records_partial PASSED [ 19%]
    tests/test_capture.py::TestFinalizeAll::test_does_not_modify_completed_records PASSED [ 20%]
    tests/test_capture.py::TestFinalizeAll::test_does_not_modify_failed_records_with_exit_code PASSED [ 21%]
    tests/test_capture.py::TestSubprocessSpyOverflow::test_max_records_limits_capture PASSED [ 23%]
    tests/test_capture.py::TestDisableSpyNesting::test_nested_disable_spy PASSED [ 24%]
    tests/test_capture.py::TestTqdmSafeTeeAdvanced::test_multiple_cr_in_single_write PASSED [ 25%]
    tests/test_capture.py::TestTqdmSafeTeeAdvanced::test_line_count_after_flush PASSED [ 26%]
    tests/test_capture.py::TestTqdmSafeTeeAdvanced::test_line_count_accuracy_with_newlines PASSED [ 28%]
    tests/test_capture.py::TestTqdmSafeTeeAdvanced::test_getattr_delegation PASSED [ 29%]
    tests/test_capture.py::TestTqdmSafeTeeAdvanced::test_write_to_closed_log_file PASSED [ 30%]
    tests/test_capture.py::TestTqdmSafeTeeBrokenPipe::test_write_catches_broken_pipe PASSED [ 32%]
    tests/test_capture.py::TestTqdmSafeTeeBrokenPipe::test_flush_catches_broken_pipe PASSED [ 33%]
    tests/test_capture.py::TestSubprocessSpyMonotonicTiming::test_popen_forward_and_backward_wall_jumps PASSED [ 34%]
    tests/test_capture.py::TestSubprocessSpyMonotonicTiming::test_os_system_backward_wall_jump_and_exception PASSED [ 35%]
    tests/test_capture.py::TestSubprocessSpyMonotonicTiming::test_popen_launch_failure_records_monotonic_duration PASSED [ 37%]
    tests/test_capture.py::TestSubprocessSpyMonotonicTiming::test_finalize_all_monotonic_non_collision_and_post_finalize_wait PASSED [ 38%]
    tests/test_capture.py::TestSubprocessSpyMonotonicTiming::test_subprocess_spy_manifest_validates_against_schema PASSED [ 39%]
    tests/test_capture.py::TestResourceWatcherMonotonicSampling::test_poll_cpu_unaffected_by_backward_wall_clock_jump PASSED [ 41%]
    tests/test_capture.py::TestResourceWatcherMonotonicSampling::test_poll_tree_cpu_unaffected_by_backward_wall_clock_jump_linux PASSED [ 42%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_unwaited_exited_child_exit_code_harvested_at_finalize[0-complete] PASSED [ 43%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_unwaited_exited_child_exit_code_harvested_at_finalize[7-failed] PASSED [ 44%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_unwaited_uncollected_child_polled_at_finalize PASSED [ 46%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_gc_after_exit_records_exit_code PASSED [ 47%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_cleanup_reaped_child_records_exit_code PASSED [ 48%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_externally_reaped_child_is_partial_not_sentinel PASSED [ 50%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_popen_del_hook_does_not_take_spy_lock PASSED [ 51%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_uninstall_restores_popen_del PASSED [ 52%]
    tests/test_signals.py::TestSignalExitCaptureBasic::test_install_and_uninstall PASSED [ 53%]
    tests/test_signals.py::TestSignalExitCaptureBasic::test_double_install_is_safe PASSED [ 55%]
    tests/test_signals.py::TestSignalExitCaptureBasic::test_double_uninstall_is_safe PASSED [ 56%]
    tests/test_signals.py::TestSignalExitCaptureBasic::test_get_records_empty_initially PASSED [ 57%]
    tests/test_signals.py::TestSignalExitCaptureBasic::test_record_exit_code PASSED [ 58%]
    tests/test_signals.py::TestSignalExitCaptureBasic::test_record_exit_code_only_first PASSED [ 60%]
    tests/test_signals.py::TestSignalCapture::test_captures_sigusr1 PASSED   [ 61%]
    tests/test_signals.py::TestSignalCapture::test_captures_sigint_as_keyboard_interrupt PASSED [ 62%]
    tests/test_signals.py::TestSignalCapture::test_multiple_signals_recorded PASSED [ 64%]
    tests/test_signals.py::TestSignalCapture::test_restores_original_handlers PASSED [ 65%]
    tests/test_signals.py::TestSignalCapture::test_chains_to_sig_ign PASSED  [ 66%]
    tests/test_signals.py::TestExcepthookCapture::test_excepthook_captures_system_exit_code PASSED [ 67%]
    tests/test_signals.py::TestExcepthookCapture::test_excepthook_captures_generic_exception PASSED [ 69%]
    tests/test_signals.py::TestExcepthookCapture::test_excepthook_restores_on_uninstall PASSED [ 70%]
    tests/test_signals.py::TestSignalOutcomeDetermination::test_sigint_sets_outcome_interrupted PASSED [ 71%]
    tests/test_signals.py::TestSignalOutcomeDetermination::test_no_signal_stays_completed PASSED [ 73%]
    tests/test_signals.py::TestSignalCaptureConfig::test_disabled_via_config PASSED [ 74%]
    tests/test_signals.py::TestSignalCaptureConfig::test_enabled_via_config PASSED [ 75%]
    tests/test_signals.py::TestSignalHandlerReinstallation::test_handler_reinstalled_after_sigint_caught PASSED [ 76%]
    tests/test_signals.py::TestSignalNonMainThread::test_warns_on_non_main_thread PASSED [ 78%]
    tests/test_signals.py::TestFinalizeActiveRun::test_finalize_active_run_calls_write_artifacts PASSED [ 79%]
    tests/test_signals.py::TestFinalizeActiveRun::test_finalize_active_run_no_crash_without_active_run PASSED [ 80%]
    tests/test_signals.py::TestMacosHardwareSpying::test_macos_hardware_calls_wrapped_in_disable_spy PASSED [ 82%]
    tests/test_signals.py::TestLethalSignalFinalization::test_lethal_signal_finalization_sigterm PASSED [ 83%]
    tests/test_signals.py::TestGetRecordsDoesNotBlock::test_get_records_from_other_thread_while_lock_held PASSED [ 84%]
    tests/test_signals.py::TestFinalizationLock::test_blocks_normally_outside_signal_finalization PASSED [ 85%]
    tests/test_signals.py::TestFinalizationLock::test_gives_up_within_bound_during_signal_finalization PASSED [ 87%]
    tests/test_signals.py::TestFinalizationLock::test_skips_wait_for_lock_that_already_timed_out PASSED [ 88%]
    tests/test_signals.py::TestFinalizationLock::test_finalize_active_run_clears_timed_out_locks PASSED [ 89%]
    tests/test_signals.py::TestLethalSignalWhileLockHeld::test_sigterm_finalizes_while_lock_held[errors_lock] PASSED [ 91%]
    tests/test_signals.py::TestLethalSignalWhileLockHeld::test_sigterm_finalizes_while_lock_held[data_files_lock] PASSED [ 92%]
    tests/test_signals.py::TestLethalSignalWhileLockHeld::test_sigterm_finalizes_while_lock_held[file_io_budget_lock] PASSED [ 93%]
    tests/test_signals.py::TestLethalSignalWhileLockHeld::test_sigterm_finalizes_while_lock_held[event_stream_lock] PASSED [ 94%]
    tests/test_signals.py::TestLethalSignalWhileLockHeld::test_sigterm_finalizes_while_lock_held[subprocess_spy_lock] PASSED [ 96%]
    tests/test_signals.py::TestLethalSignalWhileLockHeld::test_sigterm_finalizes_while_lock_held[resource_watcher_lock] PASSED [ 97%]
    tests/test_signals.py::TestLethalSignalWhileLockHeld::test_sigterm_finalizes_while_lock_held[write_lock_vs_hw_refresh] PASSED [ 98%]
    tests/test_signals.py::TestLethalSignalWhileLockHeld::test_sigterm_finalizes_while_lock_held[errors_lock_vs_hw_refresh] PASSED [100%]

    ============================= 78 passed in 13.64s ==============================
    ```
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: Paste `git diff pyproject.toml` confirming `"pubrun.capture.subprocesses"` is removed from `[[tool.mypy.overrides]]` (`ignore_errors = true`) and the comment reads `(backlog item qqwebg).`; paste actual output of `python3 -m mypy --no-incremental` and `python3 -m mypy --no-incremental src/pubrun` both exiting 0 with no issues found; and paste `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
    1. `git diff pyproject.toml`:
    ```diff
    diff --git a/pyproject.toml b/pyproject.toml
    index 2144170..6499a7f 100644
    --- a/pyproject.toml
    +++ b/pyproject.toml
    @@ -114,7 +114,7 @@ ignore_missing_imports = true

     [[tool.mypy.overrides]]
     # Legacy type-check ratchet: this list may only shrink, never grow.
    -# Remove each module as its existing errors are fixed (backlog items qqwebg and z5xr49).
    +# Remove each module as its existing errors are fixed (backlog item qqwebg).
     module = [
         "pubrun._bootstrap",
         "pubrun.analysis.diff",
    @@ -125,7 +125,6 @@ module = [
         "pubrun.capture.filesystem",
         "pubrun.capture.packages",
         "pubrun.capture.resources",
    -    "pubrun.capture.subprocesses",
         "pubrun.config",
         "pubrun.core",
         "pubrun.events",
    ```
    2. `python3 -m mypy --no-incremental` (exit code `0`):
    ```text
    Success: no issues found in 58 source files
    ```
    3. `python3 -m mypy --no-incremental src/pubrun` (exit code `0`):
    ```text
    Success: no issues found in 58 source files
    ```
    4. `python3 scripts/sanitize_paths.py --check --all`: exit code `0` (zero findings).
  - Result: pass

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`).

Execution contract:
1. **Open-questions precondition:** Zero blocking open questions remain before execution (`## Open questions` is empty).
2. **Scope declaration:** `- Scope-Paths:` declares `src/pubrun/capture/subprocesses.py` and `pyproject.toml`. If execution must edit another file or leave a declared file unchanged, make the change and justify it with `--scope-reason` or `--scope-ack` at finalize.
3. **Validation honesty (HARD MUST):** Paste the actual `mypy`, `pytest`, and `sanitize_paths.py` output observed after the final edit into `V-01` and `V-02`; never claim checks pass without running them.
4. **Path-scoped commit and never-push:** Commit only the modified paths through `aw commit id283c -- src/pubrun/capture/subprocesses.py pyproject.toml`; never use `git add -A`, `-a`, or raw `git commit`, and never push without explicit human instruction.
5. **Lifecycle transition (conditional runner vs. standalone ownership):** When executed inside `aw oc run` / `aw agy run`, the runner owns the lifecycle move after the merge-and-revalidate gate; when executed standalone outside the runner, after every `E-*` item is `performed`, every `V-*` item is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`, run `aw ipd finalize id283c` (never a hand-rolled `git mv` to `executed/`).
