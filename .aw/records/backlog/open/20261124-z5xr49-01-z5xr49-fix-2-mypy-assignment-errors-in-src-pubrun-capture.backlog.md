- Id: z5xr49
- Status: open
- Set: z5xr49
- Work-Kind: bug
- Priority: medium
- Summary: Fix 2 mypy assignment errors in src/pubrun/capture/subprocesses.py introduced by focjwv and remove module from ignore_errors ratchet
- Short-Description: Fix 2 mypy assignment errors in src/pubrun/capture/subprocesses.py introduced by focjwv and remove module from ignore_errors ratchet
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-24 created (aw backlog): Fix 2 mypy assignment errors in src/pubrun/capture/subprocesses.py introduced by focjwv and remove module from ignore_errors ratchet

## Problem

Commit `edc6343` (IPD `focjwv`, merged after IPD `gzc672` was reviewed at `8ac3407`) introduced two `mypy` assignment errors in `src/pubrun/capture/subprocesses.py`:

- In `SubprocessSpy.install._drain`, local variable `rec` is bound to a `Dict[str, Any]` from `pending_exits.popleft()` and then reassigned to `getattr(proc, "_pubrun_rec", None)` (`Any | None`), producing `Incompatible types in assignment (expression has type "Any | None", variable has type "dict[str, Any]") [assignment]`.
- In `SubprocessSpy.finalize_all`, local variable `rec` is bound to a `Dict[str, Any]` in the `cls._records` loop and then reassigned to `getattr(proc, "_pubrun_rec", None)` (`Any | None`), producing the same `[assignment]` error.

Because `src/pubrun/capture/subprocesses.py` is outside the approved `- Scope-Paths:` of IPD `gzc672`, `gzc672` added `"pubrun.capture.subprocesses"` to the `[tool.mypy.overrides]` `ignore_errors = true` ratchet in `pyproject.toml` so the blocking CI `typecheck` job passes without modifying out-of-scope source files.

## Acceptance criteria

1. In `src/pubrun/capture/subprocesses.py`, resolve the two `[assignment]` errors in `SubprocessSpy.install._drain` and `SubprocessSpy.finalize_all` without changing runtime behavior (for example by using a distinct `Optional[Dict[str, Any]]` variable for `getattr(proc, "_pubrun_rec", None)`).
2. Remove `"pubrun.capture.subprocesses"` from the `ignore_errors = true` list in `pyproject.toml`.
3. `mypy` and `mypy src/pubrun` exit 0 with no issues found, and `tests/test_subprocesses.py` and `tests/test_signals.py` pass.
