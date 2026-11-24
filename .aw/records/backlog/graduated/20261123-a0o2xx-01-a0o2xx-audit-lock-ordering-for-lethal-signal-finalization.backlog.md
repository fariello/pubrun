- Id: a0o2xx
- Status: graduated
- Graduated-To: a0o2xx
- Set: a0o2xx
- Work-Kind: followup
- Priority: medium
- Summary: Audit lock ordering for lethal-signal finalization: the SIGTERM/SIGHUP shim finalizes on the main thread (taking _run_lock and _write_lock) while the interrupted code may hold any pubrun lock; get_records() was one such deadlock (fixed in 94e504a), others may exist
- Short-Description: Audit lock ordering for lethal-signal finalization: the SIGTERM/SIGHUP shim finalizes on the main thread (taking _run_lock and _write_lock) while the interrupted code may hold any pubrun lock; get_records() was one such deadlock (fixed in 94e504a), others may exist

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-24 graduated (aw set): Graduated to review-ready IPD zcuoll (Set: a0o2xx)
- 2026-11-23 created (aw backlog): Audit lock ordering for lethal-signal finalization: the SIGTERM/SIGHUP shim finalizes on the main thread (taking _run_lock and _write_lock) while the interrupted code may hold any pubrun lock; get_records() was one such deadlock (fixed in 94e504a), others may exist
