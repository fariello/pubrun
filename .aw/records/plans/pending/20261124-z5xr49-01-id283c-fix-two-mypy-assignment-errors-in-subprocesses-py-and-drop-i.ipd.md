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

- [ ] E-01 In `src/pubrun/capture/subprocesses.py`, replace the local variable `rec` inside both `pending_running` loops with a distinct `proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)` binding instead of reassigning `rec` (`Dict[str, Any]`):
  - In `src/pubrun/capture/subprocesses.py::SubprocessSpy.install._drain` (the `if rc is not None:` block inside the `pending_running` loop), rename `rec` to `proc_rec` on all 3 lines (`proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)`, `if proc_rec is not None:`, `_complete_record(proc_rec, rc, time.time(), time.perf_counter())`). Leave the earlier `pending_exits.popleft()` `rec` binding unchanged.
  - In `src/pubrun/capture/subprocesses.py::SubprocessSpy.finalize_all` Phase 2 (the `pending_running` loop after `for rec in list(cls._records):`), rename every occurrence of `rec` in that block (all 8 occurrences across the assignment, the 4 `if` conditions, `live_procs.append`, and `seen_rec_ids.add`) to `proc_rec` (`proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)`). Leave the earlier `for rec in list(cls._records):` loop and the later Phase 3 and Phase 4 loops unchanged.
  - Shadowing hazard: `rec` (`Dict[str, Any]`) remains bound in the enclosing function scope from the preceding loop in both methods, and no existing test enters the `finalize_all` Phase 2 `pending_running` loop. Leaving any unrenamed `rec` inside either `pending_running` block passes both `mypy` and `pytest` while referencing the wrong record; verify every line of both blocks in the diff.
  - Depends on: none
  - Expected outcome: Both `[assignment]` errors in `src/pubrun/capture/subprocesses.py` (`SubprocessSpy.install._drain` and `SubprocessSpy.finalize_all`) are resolved with identical runtime behavior, Python 3.8-compatible `typing` annotations (`Optional`, `Dict`, and `Any` are already imported), and zero stale `rec` references inside either `pending_running` block.
  - Execution state: pending

- [ ] E-02 In `pyproject.toml`, remove `"pubrun.capture.subprocesses",` from the `module = [...]` list of the `[[tool.mypy.overrides]]` block that sets `ignore_errors = true`, and update the adjacent comment from `# Remove each module as its existing errors are fixed (backlog items qqwebg and z5xr49).` to `# Remove each module as its existing errors are fixed (backlog item qqwebg).` (changing plural `items` to singular `item`).
  - Depends on: E-01
  - Expected outcome: `"pubrun.capture.subprocesses"` is no longer listed in the `[[tool.mypy.overrides]]` `ignore_errors = true` block in `pyproject.toml`, the comment reads `(backlog item qqwebg).`, and `python3 -m mypy --no-incremental` plus `python3 -m mypy --no-incremental src/pubrun` both exit 0 with no issues found.
  - Execution state: pending

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

- [ ] V-01 validates E-01
  - Required evidence: Paste `git diff src/pubrun/capture/subprocesses.py` showing only the two `pending_running` blocks in `SubprocessSpy.install._drain` (3 lines) and `SubprocessSpy.finalize_all` Phase 2 (9 lines) changed, with `proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)` and zero remaining `rec` references inside either `pending_running` block; plus actual output of `python3 -m pytest tests/test_capture.py tests/test_signals.py -v` showing all tests passing.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Paste `git diff pyproject.toml` confirming `"pubrun.capture.subprocesses"` is removed from `[[tool.mypy.overrides]]` (`ignore_errors = true`) and the comment reads `(backlog item qqwebg).`; paste actual output of `python3 -m mypy --no-incremental` and `python3 -m mypy --no-incremental src/pubrun` both exiting 0 with no issues found; and paste `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
  - Result: pending

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
