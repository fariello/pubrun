- Id: 7jd8g1
- Status: done
- Graduated-To: 7jd8g1
- Set: 7jd8g1
- Work-Kind: bug
- Priority: low
- Summary: Fix background pubrun-hw manifest refresh race in test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively
- Short-Description: Fix background pubrun-hw manifest refresh race in test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-28 done (aw backlog): closed by aw agy run: IPD 8o6o83 executed (every IPD carrier is executed and this run executed .aw/records/plans/executed/20261127-7jd8g1-01-8o6o83-fix-background-pubrun-hw-manifest-refresh-race-in-test-repor.ipd.md); evidence .aw/records/plans/executed/20261127-7jd8g1-01-8o6o83-fix-background-pubrun-hw-manifest-refresh-race-in-test-repor.ipd.md
- 2026-11-27 graduated (aw backlog): graduated by run run-20261127T230423Z-4084483: 8o6o83
- 2026-11-27 created (aw backlog): Fix background pubrun-hw manifest refresh race in test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively

In tests/test_explicit_api.py::test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively, active_run() leaves capture.hardware.depth at default basic. The background pubrun-hw thread can finish between reading orig_manifest and asserting manifest equality, calling write_startup_manifest(is_refresh=True) and causing an intermittent assertion failure. Wait for _hardware_future_done or pass hardware depth=off before snapshotting orig_manifest.
