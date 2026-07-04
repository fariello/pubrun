# Assessment run report - testing

- Date / run ID: 20260704-234714
- Concern: testing rigor and completeness
- Scope: new features added today (no tests for them)
- IPD written: .agents/plans/pending/20260704-assess-testing.md
- Verdict: needs work (10 untested critical paths in new code)

## Evidence

Test suite run: 582 passed, 1 flake, 2 skipped, 59% coverage.
Key coverage gaps: packages.py 49%, resources.py 50%, core.py profiling 0%.

## Top findings

| ID | Severity | Remediation Risk | Persona | Finding |
|----|----------|------------------|---------|---------|
| TST-01 | High | Low | Testing | imported-transitive mode entirely untested |
| TST-02 | High | Low | Testing | Linux tree RSS (/proc walk) untested |
| TST-03 | High | Low | Testing | macOS tree RSS (ps parse + tree walk) untested |
| TST-04 | Medium | Low | Testing | Phase profiling hooks untested |
| TST-05 | Medium | Low | Testing | Jupyter/non-TTY console resolution untested |

## Proposed plan (summary)

1. Test imported-transitive mode (parser, dedup, required_by)
2. Test Linux tree RSS with mocked /proc
3. Test macOS tree RSS with mocked ps output
4. Test phase profiling (cProfile, orphan cleanup)
5. Test resolve_console_mode (Jupyter, non-TTY)
6. Test non-serializable event payload handling
7. Test tree scope integration in ResourceWatcher
8. Test status summary line rendering
9. Test concurrent start() race protection
10. Test write-mode provenance hash accuracy

## Deferred

- None.

## Next step

Review IPD and approve before execution.
