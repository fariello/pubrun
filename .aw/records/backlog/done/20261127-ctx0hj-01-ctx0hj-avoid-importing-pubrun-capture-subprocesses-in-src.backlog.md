- Id: ctx0hj
- Status: done
- Graduated-To: ctx0hj
- Set: ctx0hj
- Work-Kind: followup
- Priority: low
- Summary: Avoid importing pubrun.capture.subprocesses in src/pubrun/capture/git.py::_run_git_raw when SubprocessSpy is not loaded
- Short-Description: Avoid importing pubrun.capture.subprocesses in src/pubrun/capture/git.py::_run_git_raw when SubprocessSpy is not loaded

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-28 done (aw backlog): closed by aw agy run: IPD 7a4bvr executed (every IPD carrier is executed and this run executed .aw/records/plans/executed/20261127-ctx0hj-01-7a4bvr-avoid-importing-pubrun-capture-subprocesses-in-git-capture-w.ipd.md); evidence .aw/records/plans/executed/20261127-ctx0hj-01-7a4bvr-avoid-importing-pubrun-capture-subprocesses-in-git-capture-w.ipd.md
- 2026-11-28 graduated (aw backlog): graduated by run run-20261128T043704Z-1009291: 7a4bvr
- 2026-11-28 created (aw backlog): Avoid importing pubrun.capture.subprocesses in src/pubrun/capture/git.py::_run_git_raw when SubprocessSpy is not loaded

During import pubrun.nopatch (when [capture.git].enabled is true), src/pubrun/capture/git.py::_run_git_raw unconditionally executes 'from pubrun.capture.subprocesses import disable_spy' on the main thread during Step 2 of Run._bootstrap_engines() before SubprocessSpy is installed. Use a sys.modules-based _disable_spy_if_loaded() helper (matching src/pubrun/capture/hardware.py, filesystem.py, and resources.py from IPD 3ed2o4) so nopatch runs keep pubrun.capture.subprocesses unloaded even with git capture enabled.
