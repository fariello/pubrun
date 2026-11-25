# IPD: Fix two mypy assignment errors in subprocesses.py and drop it from ignore_errors

- Date: 2026-11-24
- Kind: child
- Concern: Static type safety and `[tool.mypy]` ratchet hygiene for `src/pubrun/capture/subprocesses.py`
- Scope: Resolve the two `[assignment]` mypy errors in `src/pubrun/capture/subprocesses.py` (`SubprocessSpy.install._drain` and `SubprocessSpy.finalize_all`) introduced by commit `edc6343` (`focjwv`), and remove `"pubrun.capture.subprocesses"` from the `[tool.mypy.overrides]` `ignore_errors = true` list in `pyproject.toml`.
- Scope-Paths: src/pubrun/capture/subprocesses.py, pyproject.toml
- Item-Dependencies: none
- Status: to-review
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

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 to-review (Antigravity): graduated from backlog item `z5xr49` into a review-ready plan.
- 2026-11-25 draft (Antigravity): created.

## Goal

Clear the two `mypy` `[assignment]` errors introduced in `src/pubrun/capture/subprocesses.py` by `focjwv` (`edc6343`) and remove `"pubrun.capture.subprocesses"` from the legacy `ignore_errors = true` ratchet in `pyproject.toml` so CI type-checks `subprocesses.py` strictly without changing runtime behavior.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix assignment narrowing and tighten mypy ratchet

- [ ] E-01 In `src/pubrun/capture/subprocesses.py`, use a distinct `Optional[Dict[str, Any]]` local variable (for example `proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)`) in `SubprocessSpy.install._drain` and `SubprocessSpy.finalize_all` instead of reassigning `rec` (`Dict[str, Any]`).
  - Depends on: none
  - Expected outcome: Both `[assignment]` errors in `src/pubrun/capture/subprocesses.py` (`_drain` and `finalize_all`) are resolved with identical runtime behavior and Python 3.8-compatible `typing` annotations.
  - Execution state: pending

- [ ] E-02 Remove `"pubrun.capture.subprocesses"` from the `[tool.mypy.overrides]` `ignore_errors = true` module list in `pyproject.toml` and update the adjacent comment (`# Remove each module as its existing errors are fixed (backlog items qqwebg and z5xr49).` -> remove `and z5xr49`).
  - Depends on: E-01
  - Expected outcome: `"pubrun.capture.subprocesses"` is no longer ignored by `[tool.mypy.overrides]` in `pyproject.toml`, and `python3 -m mypy` plus `python3 -m mypy src/pubrun` exit 0 with no issues found.
  - Execution state: pending

## Project conventions discovered (Step 0)

- Cite code by SYMBOL (`path::Name`) or by a quoted content string, with a line number only appended to one of those and never alone (`IPD-C801`).
- Verified directly with `MYPYPATH=src python3 -m mypy --config-file /dev/null --explicit-package-bases --follow-imports=silent src/pubrun/capture/subprocesses.py`: `src/pubrun/capture/subprocesses.py` has exactly two mypy errors on Linux:
  1. `SubprocessSpy.install._drain`: `rec = getattr(proc, "_pubrun_rec", None)` -> `Incompatible types in assignment (expression has type "Any | None", variable has type "dict[str, Any]") [assignment]`.
  2. `SubprocessSpy.finalize_all`: `rec = getattr(proc, "_pubrun_rec", None)` -> same `[assignment]` error.
- `pyproject.toml` `[tool.mypy.overrides]` lists `"pubrun.capture.subprocesses"` under `ignore_errors = true` with a comment naming `z5xr49`.
- Cross-plan note: non-blocking pending plan `k6fs5k` (`Set: rand-mypy`, Order 04) also mentions `subprocesses.py` and `pyproject.toml` for later capture-module mypy work; because `id283c` carries `- Blocks-Release: next`, it clears `subprocesses.py` ahead of `1.4.0` cleanly.
- Subprocess capture and signal tests live in `tests/test_capture.py` and `tests/test_signals.py` (there is no `tests/test_subprocesses.py` file).

## Findings

Commit `edc6343` (`focjwv`) reused local variable `rec` (already inferred as `Dict[str, Any]` from earlier loops) for `getattr(proc, "_pubrun_rec", None)` (`Any | None`) in two places inside `src/pubrun/capture/subprocesses.py`: `SubprocessSpy.install._drain` and `SubprocessSpy.finalize_all`. That caused `gzc672` to place `"pubrun.capture.subprocesses"` into the `pyproject.toml` `ignore_errors = true` ratchet. Giving the optional lookup its own `Optional[Dict[str, Any]]` variable clears both errors with zero runtime change and removes the module from the ratchet.

## Proposed changes (ordered, validatable)

1. **`src/pubrun/capture/subprocesses.py` (E-01):**
   - In `SubprocessSpy.install._drain`, replace `rec = getattr(proc, "_pubrun_rec", None)` and the immediately following `if rec is not None: _complete_record(rec, ...)` with `proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)` and `if proc_rec is not None: _complete_record(proc_rec, ...)`.
   - In `SubprocessSpy.finalize_all`, replace `rec = getattr(proc, "_pubrun_rec", None)` and its `if rec is not None ...` block with `proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)` and matching `proc_rec` references.
2. **`pyproject.toml` (E-02):**
   - Remove `"pubrun.capture.subprocesses",` from the `[tool.mypy.overrides]` `module = [...]` list (`ignore_errors = true`) and update the ratchet comment above it to drop `and z5xr49`.

## Deferred / out of scope (with reason)

- Windows-only `mypy --platform win32` guards in `subprocesses.py` (such as `os.WIFEXITED`): owned by pending plan `juoqy2` (`Set: rand-mypy`).
  - Carrier: juoqy2

## Scope check

- Over-scope: none. Only `src/pubrun/capture/subprocesses.py` and `pyproject.toml` are modified.
- Under-scope: none. Confirmed by running `mypy` without `ignore_errors` that only these two errors exist in `subprocesses.py`.

## Required tests / validation

- Run `python3 -m mypy` and `python3 -m mypy src/pubrun` and confirm both exit 0 with zero issues found.
- Run `python3 -m pytest tests/test_capture.py tests/test_signals.py -v` and confirm all tests pass.
- Run `python3 scripts/sanitize_paths.py --check --all` and confirm exit code 0.

## Spec / documentation sync

N/A. Internal type-annotation cleanup and `pyproject.toml` mypy configuration only; no runtime or user-facing documentation change.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Paste `git diff src/pubrun/capture/subprocesses.py` showing the two `Optional[Dict[str, Any]]` variable fixes in `_drain` and `finalize_all`, plus actual output of `python3 -m pytest tests/test_capture.py tests/test_signals.py -v` showing all tests passing.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Paste `git diff pyproject.toml` confirming `"pubrun.capture.subprocesses"` is removed from `[tool.mypy.overrides]`, paste actual output of `python3 -m mypy` and `python3 -m mypy src/pubrun` both exiting 0 with no issues found, and paste `python3 scripts/sanitize_paths.py --check --all` exiting 0.
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
4. **Path-scoped commit and never-push:** Commit only the modified paths through `aw commit id283c -- src/pubrun/capture/subprocesses.py pyproject.toml`; never use `git add -A` or `-a`, and never push without explicit human instruction.
5. **Lifecycle transition (conditional runner vs. standalone ownership):** When executed inside `aw oc run` / `aw agy run`, the runner owns the lifecycle move after the merge-and-revalidate gate; when executed standalone outside the runner, run `aw ipd finalize id283c` (never a hand-rolled `git mv` to `executed/`).
