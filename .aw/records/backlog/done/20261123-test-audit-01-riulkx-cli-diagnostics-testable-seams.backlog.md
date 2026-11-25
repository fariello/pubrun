- Id: riulkx
- Status: done
- Graduated-To: riulkx
- Set: test-audit
- Work-Kind: chore
- Priority: low
- Summary: Refactor monolithic CLI main() and diagnostics print_* into injectable testable seams (deferred from /assess-testing T-18)
- Short-Description: Refactor monolithic CLI main() and diagnostics print_* into injectable testable seams (deferred from /assess-testing T-18)

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-25 done (aw backlog): closed by aw agy run: IPD mvbbny executed (every IPD carrier is executed and this run executed .aw/records/plans/executed/20261124-riulkx-01-mvbbny-cli-main-and-diagnostics-report-testable-seams.ipd.md); evidence .aw/records/plans/executed/20261124-riulkx-01-mvbbny-cli-main-and-diagnostics-report-testable-seams.ipd.md
- 2026-11-25 graduated (aw backlog): graduated by run run-20261124T202433Z-1567679: mvbbny
- 2026-11-23 created (aw backlog): Refactor monolithic CLI main() and diagnostics print_* into injectable testable seams (deferred from /assess-testing T-18)

Deferred from /assess-testing (Set test-audit, T-18) due to Medium-High Remediation Risk on complexity and functionality: src/pubrun/__main__.py:main (~878 lines) mutates global sys.argv, NO_COLOR, and status._DISPLAY_UTC inline, and src/pubrun/report/diagnostics.py:print_report / print_resources_report write to sys.stdout and call sys.exit(1) directly. Safe behavioral coverage is executed first by ic6z4s.
