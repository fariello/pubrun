- Id: ggaok0
- Status: done
- Graduated-To: ggaok0
- Set: ggaok0
- Work-Kind: bug
- Priority: medium
- Summary: benchmarks/startup_breakdown.py::_scrub_substrings uses unanchored str.replace of the username, so a short username (e.g. ed, pub) corrupts <redacted> markers and schema strings; port the boundary-safe scrub from benchmarks/harness.py (8k73qj BUG-20)
- Short-Description: benchmarks/startup_breakdown.py::_scrub_substrings uses unanchored str.replace of the username, so a short username (e.g. ed, pub) corrupts <redacted> markers and schema strings; port the boundary-safe scrub from benchmarks/harness.py (8k73qj BUG-20)
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-23 done (aw backlog): closed by aw oc run: IPD 0vwc5z executed (every IPD carrier is executed and this run executed .aw/records/plans/executed/20261122-ggaok0-01-0vwc5z-make-the-startup-breakdown-username-scrub-boundary-safe.ipd.md); evidence .aw/records/plans/executed/20261122-ggaok0-01-0vwc5z-make-the-startup-breakdown-username-scrub-boundary-safe.ipd.md
- 2026-11-23 graduated (aw backlog): graduated by run run-20261123T005542Z-1001883: 0vwc5z
- 2026-11-22 created (aw backlog): benchmarks/startup_breakdown.py::_scrub_substrings uses unanchored str.replace of the username, so a short username (e.g. ed, pub) corrupts <redacted> markers and schema strings; port the boundary-safe scrub from benchmarks/harness.py (8k73qj BUG-20)
