# Assessment run report - performance (whole project)

- Date / run ID: 20260704-143134
- Concern: performance
- Scope: whole project (src/pubrun/)
- IPD written: .agents/plans/pending/20260704-assess-performance.md
- Verdict: adequate for performance (with targeted improvements available)

## Top findings

| ID | Severity | Remediation Risk | Persona | Finding |
|----|----------|------------------|---------|---------|
| PERF-01 | Medium | Low | Engineer/Architect | `get_packages()` iterates all installed distributions on every import (~50-200ms in large venvs) |
| PERF-02 | Medium | Low | Engineer/Power-user | `get_hardware()` spawns GPU/CPU detection subprocesses synchronously during import (~200-500ms) |
| PERF-03 | Medium | Low | Engineer | `get_git()` runs 4 sequential git subprocess calls during import |
| PERF-07 | Medium | Low | Power-user/Architect | `ProvenanceFileProxy` re-reads entire file on close despite having an incremental hash |
| PERF-09 | Medium | Low | Power-user/Architect | `scan_runs()` does O(n) sequential JSON parses with no caching for status display |

(The complete findings list is in `findings.csv`.)

## Proposed plan (summary)

1. Cache default config and compiled regex patterns (eliminate redundant work)
2. Fix ProvenanceFileProxy to use incremental hash for reads (eliminate redundant I/O)
3. Change default packages mode to `imported-only` (reduce import-time iteration)
4. Defer hardware detection to background thread (unblock import)
5. Parallelize or reduce git subprocess calls
6. Optimize timestamp formatting in console tee hot path
7. Buffer event stream writes (reduce lock contention and flush overhead)
8. Add runs directory index for faster status queries (conditional on benchmarks)
9. Gate script hashing behind a size threshold
10. Optimize event count in status (avoid full file read)
11. Use native APIs for RSS polling on macOS/Windows (eliminate subprocess spawns)
12. Optimize ProvenanceFileProxy mode detection at construction time

## Deferred (with reason)

- PERF-08 (full class split): Remediation Risk Medium-High on complexity because
  splitting ProvenanceFileProxy into binary/text subclasses doubles class surface
  area for marginal per-call savings. The simple branch-at-construction (Step 12)
  captures most benefit without the complexity cost.

## Out-of-repo / organizational notes (if any)

- None. All proposed changes are in-repo code optimizations.

## Next step

Review the IPD (optionally run the `plan-review` workflow on it) and approve
before execution. This workflow does not execute the plan.
