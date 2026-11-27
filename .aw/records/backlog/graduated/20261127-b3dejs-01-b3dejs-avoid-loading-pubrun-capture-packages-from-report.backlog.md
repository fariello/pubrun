- Id: b3dejs
- Status: graduated
- Graduated-To: b3dejs
- Set: b3dejs
- Work-Kind: followup
- Priority: low
- Summary: Avoid loading pubrun.capture.packages from report/methods.py when capture.packages.mode is off
- Short-Description: Avoid loading pubrun.capture.packages from report/methods.py when capture.packages.mode is off

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-27 graduated (aw backlog): graduated by run run-20261127T230423Z-4084483: 3u1xgk
- 2026-11-27 created (aw backlog): Avoid loading pubrun.capture.packages from report/methods.py when capture.packages.mode is off

## Problem

`src/pubrun/report/methods.py` imports `normalize_package_name` from `src/pubrun/capture/packages.py` at module top level. Because `src/pubrun/writer.py::ArtifactWriter.write_artifacts` imports `pubrun.report.methods::generate_report` during every `pubrun.stop()`, stopping a run loads `pubrun.capture.packages` and `importlib.metadata` even when `[capture.packages].mode == "off"`.

## Bounded outcome and acceptance

Move the PEP 503 package-name normalization helper to a lightweight shared module (or inline the regex in `src/pubrun/report/methods.py` without importing `src/pubrun/capture/packages.py` at top level) so a full `pubrun.start()` + `pubrun.stop()` cycle with `[capture.packages].mode == "off"` keeps `pubrun.capture.packages` out of `sys.modules`. Verify with a fresh-subprocess regression test asserting `"pubrun.capture.packages" not in sys.modules` after `pubrun.stop()`.
