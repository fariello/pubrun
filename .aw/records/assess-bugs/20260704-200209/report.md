# Assessment run report - bugs round 2 (new code)

- Date / run ID: 20260704-200209
- Concern: bugs and correctness
- Scope: newly-added code (console resolve, tree RSS, profiling, transitive packages)
- IPD written: .agents/plans/pending/20260704-assess-bugs-2.md
- Verdict: adequate (no blockers; 2 Medium-severity issues in tree RSS macOS)

## Top findings

| ID | Severity | Remediation Risk | Persona | Finding |
|----|----------|------------------|---------|---------|
| BUG2-01 | Medium | Low | QA/Engineer | macOS `pgrep -P` only finds direct children, misses grandchildren |
| BUG2-06 | Medium | Low | QA/Engineer | macOS tree RSS returns 0 when no children (loses self RSS) |
| BUG2-03 | Low | Low | Engineer | yappi global state conflicts with concurrent phases |
| BUG2-04 | Low | Low | QA | Orphaned cProfile profiler if phase entered without context manager |

## Proposed plan (summary)

1. Fix macOS tree walk to discover grandchildren (iterative pgrep or ps -eo pid,ppid)
2. Always include self RSS in tree total (even when no children found)
3. Guard yappi against concurrent phase starts
4. Disable orphaned profilers during run finalization

## Deferred (with reason)

- None.

## Next step

Review the IPD and approve before execution.
