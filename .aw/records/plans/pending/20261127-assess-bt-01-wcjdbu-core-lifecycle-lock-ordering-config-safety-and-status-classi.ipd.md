# IPD: Core lifecycle lock ordering config safety and status classification

- Date: 2026-11-27
- Kind: child
- Concern: Fix core runtime, lock-finalization, config-safety, and status-classification bugs (`BUG-C1`, `BUG-C2`, `BUG-C3`, `BUG-C4`, `BUG-C6`, `BUG-C7`, `BUG-C8`, `BUG-C9`, `BUG-C10`) plus status crash-closeout and root-safe test gaps (`TEST-U11`).
- Scope: Harden `src/pubrun/tracker.py`, `src/pubrun/writer.py`, `src/pubrun/status.py`, `src/pubrun/config.py`, and `src/pubrun/__init__.py` against non-dict config sections, premature `.pubrun.lock` removal, lockless `outcome: "running"` misclassification, `SystemExit`/bool exit-code corruption, `find_run()` stripping/ambiguity, `_merge_and_migrate()` concurrency/notice bugs, shadowed `open`, aliased `_deep_merge`, and symlink/corrupt-JSON `status.py` edges, with behavioral regression tests in `tests/test_core_lifecycle_bugs.py`, `tests/test_status_bugs.py`, and `tests/test_status.py`.
- Scope-Paths: src/pubrun/tracker.py, src/pubrun/writer.py, src/pubrun/status.py, src/pubrun/config.py, src/pubrun/__init__.py, tests/test_core_lifecycle_bugs.py, tests/test_status_bugs.py, tests/test_status.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Fix non-dict config crashes, lock removal before manifest write, lockless running misclassification, SystemExit/bool codes, find_run, migration races, and status tests
- Work-Kind: bug
- Priority: high
- Set: assess-bt
- Order: 1
- Highest E allocated: 05
- Author: Antigravity
- Id: wcjdbu

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-27 to-review (Antigravity): Authored review-ready child IPD from parallel `/assess bugs` and `/assess testing` audits on HEAD `512ee68` / `8f2aacd`.
- 2026-11-27 draft (Antigravity): created.

## Goal

Eliminate three High core/status correctness and data-integrity defects (non-dict config crashes leaking hooks, premature `.pubrun.lock` removal before package refresh and finalized manifest persistence, and lockless `outcome: "running"` manifests misclassified as `completed`) alongside six Medium/Low lifecycle and status bugs and the `close_out_crashed_run` / root-safe status test gaps.

### Safe finalization and lock-removal order

```mermaid
flowchart TD
    STOP["Run.stop() / atexit"] --> FIN["Run._finalize_state()"]
    FIN --> HOOKS["Run._rollback_owned_hooks(stage='finalization') (keeps .pubrun.lock)"]
    HOOKS --> PKG["Run._refresh_packages_at_finalization()"]
    PKG --> WRITE["ArtifactWriter.write_artifacts() writes config.resolved.json + atomic manifest.json"]
    WRITE -->|"write succeeds"| UNLOCK["Remove .pubrun.lock"]
    WRITE -->|"write raises OSError"| KEEP["Preserve .pubrun.lock for dead-PID crash detection"]
```

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Harden tracker, writer, config, and package root

- [ ] E-01 Harden `src/pubrun/tracker.py` and `src/pubrun/writer.py` for config safety, lock ordering, `SystemExit` handling, and migration races (`BUG-C1`, `BUG-C2`, `BUG-C4`, `BUG-C7`):
  - In `src/pubrun/tracker.py`, replace every unguarded `.get(...)` chain on config sections in `Run._bootstrap_engines`, `_call_get_packages`, and `Run._refresh_packages_at_finalization` with `pubrun.config._section(...)`. Guard `self._bootstrap_engines()` in `Run.__init__()` so any unexpected exception rolls back owned hooks cleanly rather than leaking `SubprocessSpy` or `.pubrun.lock`.
  - In `src/pubrun/tracker.py::Run._rollback_owned_hooks`, call `self._remove_lock_file()` only when `stage == "rollback"` (ghost rollback). In `src/pubrun/writer.py::ArtifactWriter.write_artifacts`, remove `.pubrun.lock` only *after* `manifest.json` is atomically written (and in `Run.stop()`'s `finally` only when `writer is None`), so `.pubrun.lock` stays intact during package refresh and on `manifest.json` write failure.
  - In `src/pubrun/tracker.py::Run._finalize_state`, use `pubrun.core._classify_exit_outcome(sys.exc_info()[1])` instead of treating all non-`KeyboardInterrupt` exceptions (including `SystemExit(0)` / `SystemExit(None)`) as `"failed"`, and coerce `bool` `SystemExit.code` via `int(code)` (`True -> 1`, `False -> 0`) before `record_exit_code`.
  - In `src/pubrun/tracker.py::Run._merge_and_migrate`, serialize `_api_overrides` read-merge-commit under `_run_lock`, recompute `self.config_notices` via `profile_deprecation_notice(merged)`, and ensure `SubprocessSpy.install(owner=self._spy_owner_token)` is immediately rolled back if `self._finalized` became `True` before committing.
  - Depends on: none
  - Expected outcome: Non-dict config overrides never raise `AttributeError` or leak hooks; `.pubrun.lock` persists until after atomic `manifest.json` write; `SystemExit(0)`/`None`/`bool` record accurate outcomes and `int` exit codes; concurrent `_merge_and_migrate` updates never drop overrides, leak `SubprocessSpy`, or leave `config_notices` stale.
  - Execution state: pending

- [ ] E-02 Fix `src/pubrun/config.py` and `src/pubrun/__init__.py` (`BUG-C8`, `BUG-C9`):
  - In `src/pubrun/config.py::_deep_merge`, replace `result[key] = value` with `result[key] = copy.deepcopy(value)` so nested lists/dicts from `dict2` are never aliased into the merged result.
  - In `src/pubrun/__init__.py::_read_pyproject_project_meta`, call `builtins.open` instead of unqualified `open` (which is shadowed by `pubrun.core.open`), preventing `__commit__` resolution during an active run from recording `pyproject.toml` into `run.data_files["inputs"]`.
  - Depends on: none
  - Expected outcome: Mutating `_deep_merge(d1, d2)` never mutates `d2`; accessing `pubrun.__commit__` during an active run never pollutes `data_files["inputs"]`.
  - Execution state: pending

### Task group 2: Harden `status.py` classification, selector matching, and directory sizing

- [ ] E-03 Harden `src/pubrun/status.py` (`BUG-C1`, `BUG-C3`, `BUG-C6`, `BUG-C10`, plus `~`/`$VAR` expansion in `_resolve_output_dir` supporting `BUG-U5`):
  - In `_resolve_output_dir`, look up `core` via `pubrun.config._section(config, "core")`, validate `isinstance(base_str, str)`, and expand `~` and `$VAR` (`os.path.expanduser(os.path.expandvars(...))`) on both explicit `output_dir` arguments and config-derived strings.
  - In `RunInfo._load_from_manifest`, add an explicit `elif self.outcome == "running":` branch: classify as `STATUS_RUNNING` when local liveness (`is_same_process(self.pid, self.started_at_utc, expected_script=self.script)`) confirms the process is alive, and `STATUS_CRASHED` otherwise (never falling through to `STATUS_COMPLETED`).
  - In `RunInfo._load_from_manifest` and `RunInfo._load_from_lock`, treat valid-JSON non-dict payloads (e.g., `[]`, `null`) as corrupt (`_parse_dir_name()` + `STATUS_CRASHED`) and coerce non-dict sub-sections (`run`, `status`, `git`, `invocation`, `signals`, `process`) to `{}`.
  - In `find_run`, use stripped `sel` in prefix and substring matching (steps 2 and 3), and raise `AmbiguousRunSelectorError` whenever `by_recency is not None` and `other_exact = [r for r in exact_id if r is not by_recency]` is non-empty (even when `len(other_exact) >= 2`).
  - In `_dir_size`, skip symlinks (`not f.is_symlink() and f.is_file()`) and handle `OSError` per entry so one unreadable/disappearing entry does not abort sizing.
  - Depends on: none
  - Expected outcome: Lockless startup manifests with dead PIDs classify as `STATUS_CRASHED`; non-dict config/JSON degrades safely; `find_run` honors whitespace stripping and multi-collision ambiguity; `_dir_size` excludes symlinks and tolerates per-entry `OSError`.
  - Execution state: pending

### Task group 3: Add behavioral regression tests and validate

- [ ] E-04 Add behavioral regression tests in `tests/test_core_lifecycle_bugs.py`, `tests/test_status_bugs.py`, and `tests/test_status.py` (`BUG-C1`..`C4`, `BUG-C6`..`C10`, `TEST-U11`):
  - In `tests/test_core_lifecycle_bugs.py`, add tests for: (a) non-dict `events`/`capture` section overrides in `pubrun.start()` leaving `SubprocessSpy._installed == False` after `stop()`; (b) `.pubrun.lock` remaining present during `merge_package_snapshots` and `_atomic_json_write`, removed after success, and preserved when `manifest.json` write raises `OSError`; (c) `_finalize_state()` on `SystemExit(0)`, `SystemExit(None)`, `SystemExit(True)`, `SystemExit(False)` checking outcomes and `type(exit_code) is int`; (d) `_merge_and_migrate()` refreshing `config_notices` on `start(profile="deep")`, racing `SubprocessSpy.install` against `stop()`, and concurrent `start()` override retention; (e) `pubrun.__commit__` during an active run not adding `pyproject.toml` to `data_files["inputs"]`; (f) `_deep_merge()` not aliasing mutable values from `dict2`.
  - In `tests/test_status_bugs.py`, add tests for: (a) `scan_runs()` with `core = "bad"` / `[core]\noutput_dir = 123` and `$VAR` expansion; (b) lockless startup `manifest.json` (`outcome="running"`) classifying as `STATUS_CRASHED` for dead PID and `STATUS_RUNNING` for live PID; (c) `find_run(" abcd ", d)`, `find_run(" train ", d)`, and `find_run("1", d)` with two runs sharing `run_id="1"` plus a newer run raising `AmbiguousRunSelectorError`; (d) `_dir_size()` excluding symlinks and tolerating `OSError`; (e) `RunInfo(run_dir)` degrading to `STATUS_CRASHED` on `[]` or `{"run": null}`; (f) `close_out_crashed_run` TOCTOU refusal on live `os.getpid()` and fallback `run_id`/`mtime` reconstruction on empty `lock_data={}` (`TEST-U11`).
  - In `tests/test_status.py`, add `hasattr(os, "geteuid") and os.geteuid() == 0` to `TestLockFile.test_ghost_mode_no_lock_file`'s skip guard (`TEST-U11`).
  - Depends on: E-01, E-02, E-03
  - Expected outcome: Every defect and test gap in this child has a failing-before/passing-after behavioral regression test.
  - Execution state: pending

- [ ] E-05 Run targeted `pytest -p randomly` and 3-OS `mypy` validation and record complete output:
  - Run all commands listed in `## Required tests / validation` and verify exit code `0` with zero failures.
  - Depends on: E-04
  - Expected outcome: All targeted pytest suites pass under `-p randomly` and 3-OS `mypy` reports zero errors.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `src/pubrun/config.py::_section(cfg, key)` is the house helper introduced in `1o1cua` to coerce non-dict TOML/override sections safely to `{}`.
- `src/pubrun/core.py::_classify_exit_outcome(exc)` defines the authoritative mapping from exception / `SystemExit` values to `("completed" | "failed" | "interrupted")`.
- `tests/test_report_checks_bugs.py` already uses `hasattr(os, "geteuid") and os.geteuid() == 0` alongside `sys.platform == "win32"` for read-only permission tests.
- All tests must exercise observable behavior and outcomes (no AST/source inspection or private-slot pinning).

## Findings

| ID | Concerns | Severity | Remediation Risk | Persona | Summary |
|---|---|---|---|---|---|
| `BUG-C1` | bugs | High | Low (`functionality`) | Software Engineer | Non-dict config sections crash `Run._bootstrap_engines()` mid-startup (leaking hooks/lock) and `status._resolve_output_dir()`. |
| `BUG-C2` | bugs | High | Medium (`functionality`) | Data Integrity | `.pubrun.lock` is removed in `_rollback_owned_hooks` before package refresh and atomic `manifest.json` persistence. |
| `BUG-C3` | bugs | High | Low (`functionality`) | Data Integrity | `RunInfo._load_from_manifest` misclassifies lockless `outcome: "running"` manifests as `STATUS_COMPLETED`. |
| `BUG-C4` | bugs | Medium | Low (`functionality`) | Software Engineer | `Run._finalize_state` maps active `SystemExit(0)`/`None` to `"failed"` and stores `bool` exit codes. |
| `BUG-C6` | bugs | Medium | Low (`usability`) | QA Engineer | `find_run` ignores stripped `sel` in prefix/substring branches and misses multi-run recency collisions. |
| `BUG-C7` | bugs | Medium | Low (`functionality`) | Concurrency Reviewer | `Run._merge_and_migrate` has a `SubprocessSpy` post-finalization leak race, stale `config_notices`, and concurrent override lost-update. |
| `BUG-C8` | bugs | Low | Low (`functionality`) | Software Engineer | `pubrun/__init__.py::_read_pyproject_project_meta` calls shadowed `pubrun.core.open` instead of `builtins.open`. |
| `BUG-C9` | bugs | Low | Low (`functionality`) | Software Engineer | `config._deep_merge` aliases mutable values from `dict2`. |
| `BUG-C10` | bugs | Low | Low (`usability`) | QA Engineer | `status._dir_size` follows symlinks and aborts on `OSError`; `RunInfo` crashes directly on valid-JSON non-dict files. |
| `TEST-U11` | testing | Low | Low (`complexity`) | QA / CI Engineer | `test_status.py::test_ghost_mode_no_lock_file` lacks root skip guard; `close_out_crashed_run` TOCTOU and empty-lock fallback paths are untested. |

## Proposed changes (ordered, validatable)

1. `E-01` (`src/pubrun/tracker.py`, `src/pubrun/writer.py`): Guard config section lookups with `_section()`, defer `.pubrun.lock` removal until after atomic `manifest.json` write, fix `SystemExit`/bool handling in `_finalize_state()`, and harden `_merge_and_migrate()`.
2. `E-02` (`src/pubrun/config.py`, `src/pubrun/__init__.py`): Deep-copy `dict2` values in `_deep_merge()` and use `builtins.open` in `_read_pyproject_project_meta()`.
3. `E-03` (`src/pubrun/status.py`): Guard/expand `_resolve_output_dir()`, classify lockless `outcome: "running"` via liveness, harden non-dict JSON handling, fix `find_run()` stripping/ambiguity, and harden `_dir_size()`.
4. `E-04` (`tests/test_core_lifecycle_bugs.py`, `tests/test_status_bugs.py`, `tests/test_status.py`): Add behavioral regression tests and root-safe skip guard.
5. `E-05` (validation): Run randomized pytest suites and 3-OS `mypy`.

## Deferred / out of scope (with reason)

None. All core lifecycle, lock-ordering, config-safety, and status findings assigned to Order 01 are covered in this plan.

## Scope check

- Over-scope: none. Only the five directly affected runtime modules and three paired test files are in `Scope-Paths`.
- Under-scope: none. Every finding (`BUG-C1`..`C4`, `BUG-C6`..`C10`, `TEST-U11`) has a dedicated code change and behavioral regression test.

## Required tests / validation

1. Targeted randomized pytest run:
   ```sh
   pytest -p randomly tests/test_core_lifecycle_bugs.py tests/test_status_bugs.py tests/test_status.py tests/test_config.py tests/test_tracker.py tests/test_runtime_safety.py tests/test_hook_ownership_rollback.py -v
   ```
2. Three-OS static type check:
   ```sh
   mypy && mypy --platform win32 && mypy --platform darwin
   ```

## Spec / documentation sync

N/A. Fixes align runtime behavior with existing documented contracts (non-interference golden rule, lock-based crash detection, non-mutating `_deep_merge`, and `find_run` ambiguity handling).

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result (which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- src/pubrun/tracker.py src/pubrun/writer.py` confirming `_section()` guards, post-manifest `.pubrun.lock` removal, `_classify_exit_outcome()` + `int(code)` coercion, and `_merge_and_migrate()` lock/notice hardening, plus passing output for the new `tests/test_core_lifecycle_bugs.py` tests exercising `Run._bootstrap_engines`, `ArtifactWriter.write_artifacts`, `Run._finalize_state`, and `Run._merge_and_migrate`.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- src/pubrun/config.py src/pubrun/__init__.py` confirming `copy.deepcopy(value)` in `_deep_merge` and `builtins.open` in `_read_pyproject_project_meta`, plus passing output for the corresponding `tests/test_core_lifecycle_bugs.py` tests.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- src/pubrun/status.py` confirming `_resolve_output_dir`, `outcome == "running"` classification, non-dict JSON resilience, `find_run` `sel`/ambiguity fixes, and `_dir_size` symlink/OSError handling, plus passing output for the corresponding `tests/test_status_bugs.py` tests.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `pytest -v` output naming every newly added test function in `tests/test_core_lifecycle_bugs.py` and `tests/test_status_bugs.py` and confirming `test_ghost_mode_no_lock_file` in `tests/test_status.py` passes (and includes the `geteuid() == 0` guard in `git diff -- tests/test_status.py`).
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted complete output of both commands in `## Required tests / validation` (`pytest -p randomly ...` and 3-OS `mypy`), all exiting `0` with zero failures.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

1. **Open questions and approval:** Do not execute until explicit human approval is recorded (`aw ipd set approved wcjdbu --by-human` or `aw set approved assess-bt --by-human`).
2. **Scope declaration:** Modify only the eight declared `Scope-Paths`.
3. **Validation honesty:** Paste actual command outputs from this workspace for every `V-*` item.
4. **Commits and push policy:** Commit only files modified for this plan through `aw commit wcjdbu -- <paths>`. Never push, tag, or publish.
5. **Lifecycle finalization:** Finalize via `aw ipd finalize wcjdbu` (or let the runner finalize) only after every `E-*` is `performed` and every `V-*` is `pass`.
