- Id: tmngjn
- Status: open
- Set: tmngjn
- Work-Kind: bug
- Priority: high
- Summary: Mode modules (pubrun.auto etc.) start the background hardware thread before pubrun._run_lock is bound, so hardware capture can fail with ImportError
- Short-Description: Mode modules (pubrun.auto etc.) start the background hardware thread before pubrun._run_lock is bound, so hardware capture can fail with ImportError
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-23 created (aw backlog): Mode modules (pubrun.auto etc.) start the background hardware thread before pubrun._run_lock is bound, so hardware capture can fail with ImportError

## Problem

Observed while executing sdg31l (2026-11-22): running `python3 -c "import pubrun.auto"` (also `pubrun.full`) printed `Exception in thread pubrun-hw: ... ImportError: cannot import name '_run_lock' from 'pubrun'` from `src/pubrun/tracker.py` `_collect_hardware` (the `from pubrun import _run_lock` line before `self._collect_hardware_section()`).

Cause (from reading the code, not yet confirmed by a test): `src/pubrun/auto.py` (and the other explicit mode modules) call `_execute_boot_sequence(...)`, which starts the `pubrun-hw` background thread, before the later `_pkg._run_lock = _run_lock` assignment binds the attribute on the top-level package. If the thread runs first, the import fails, the thread dies, and the hardware and host/filesystem sections are not collected for that run. Plain `import pubrun` binds `_run_lock` through its own import list and is not affected.

## Acceptance

- A behavioral test that imports each explicit mode module in a fresh subprocess, runs a short tracked script, and asserts no `pubrun-hw` thread traceback on stderr and a captured `hardware` section in the manifest.
- Fix binds `_run_lock` (and any other attribute the background threads import from `pubrun`) before boot, or has threads import it from `pubrun.core`.
