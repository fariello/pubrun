- Id: uatvzh
- Status: graduated
- Graduated-To: uatvzh
- Set: uatvzh
- Work-Kind: bug
- Priority: medium
- Summary: Coalesced hardware refresh holds _run_lock across an fsynced manifest write, so stop() during it inflates workload_seconds
- Short-Description: Coalesced hardware refresh holds _run_lock across an fsynced manifest write, so stop() during it inflates workload_seconds
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-23 graduated (aw backlog): graduated by run run-20261123T005542Z-1001883: 3aalwv
- 2026-11-22 created (aw backlog): Coalesced hardware refresh holds _run_lock across an fsynced manifest write, so stop() during it inflates workload_seconds

Observed while executing IPD 3tvesf (2026-11-22, git af36c85, Linux ext4, CPython 3.14.6). The pubrun-hw thread (src/pubrun/tracker.py, _collect_hardware, about lines 650-675) performs its coalesced refresh writer.write_startup_manifest(is_refresh=True) while holding _run_lock. With the default artifact_durability = "fsync" that write took a median of 180 ms (max 468 ms, n=16) when the run directory was on the repository disk, versus about 7 ms under a /tmp directory on another ext4 mount. Run._finalize_state() takes the workload-end anchor t2 only after acquiring _run_lock (about line 1109), so a stop() issued while the refresh is in flight blocks and the wait is counted as workload. Measured: time from the stop() call to t2 was median 47.3 ms, stdev 36.1, IQR 40.0, max 185.9 (n=30) for a 20 ms workload on the repository disk; 0.02 ms on /tmp; 0.03 ms for a 500 ms workload (refresh already finished). examples/05_execution_phases.py shows it: two 10 ms phases, workload_seconds 24 to 245 ms across runs. Expected: workload_seconds excludes pubrun's own capture work. Possible fixes (unverified): take t2 (perf_counter and time.time) before acquiring _run_lock in _finalize_state, or perform the refresh write outside _run_lock after re-checking the latch, preserving the _run_lock before _write_lock order. Needs a regression test that stalls the refresh write and asserts workload_seconds stays near the workload.
