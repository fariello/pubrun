- Id: ln0vci
- Status: done
- Graduated-To: ln0vci
- Set: ln0vci
- Work-Kind: followup
- Priority: low
- Summary: Document sys_argv in the Lock File section of docs/manifest.md
- Short-Description: Document sys_argv in the Lock File section of docs/manifest.md

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-25 done (aw backlog): closed by aw agy run: IPD wg2l7b executed (every IPD carrier is executed and this run executed .aw/records/plans/executed/20261125-ln0vci-01-wg2l7b-document-sys-argv-in-the-lock-file-section-of-docs-manifest.ipd.md); evidence .aw/records/plans/executed/20261125-ln0vci-01-wg2l7b-document-sys-argv-in-the-lock-file-section-of-docs-manifest.ipd.md
- 2026-11-25 graduated (aw backlog): graduated by run run-20261125T053925Z-3065438: wg2l7b
- 2026-11-25 created (aw backlog): Document sys_argv in the Lock File section of docs/manifest.md

Run._write_lock_file in src/pubrun/tracker.py writes a redacted sys_argv list (from sys.argv) into .pubrun.lock, but the Lock File table and JSON example in docs/manifest.md omit sys_argv.
