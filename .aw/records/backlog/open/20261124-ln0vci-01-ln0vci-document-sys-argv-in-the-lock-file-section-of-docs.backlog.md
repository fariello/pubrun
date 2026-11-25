- Id: ln0vci
- Status: open
- Set: ln0vci
- Work-Kind: followup
- Priority: low
- Summary: Document sys_argv in the Lock File section of docs/manifest.md
- Short-Description: Document sys_argv in the Lock File section of docs/manifest.md

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-25 created (aw backlog): Document sys_argv in the Lock File section of docs/manifest.md

Run._write_lock_file in src/pubrun/tracker.py writes a redacted sys_argv list (from sys.argv) into .pubrun.lock, but the Lock File table and JSON example in docs/manifest.md omit sys_argv.
