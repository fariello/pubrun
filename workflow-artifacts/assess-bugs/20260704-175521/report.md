# Assessment run report - bugs (whole project)

- Date / run ID: 20260704-175521
- Concern: bugs and correctness
- Scope: whole project (src/pubrun/)
- IPD written: plans/pending/20260704-assess-bugs.md
- Verdict: adequate for correctness (no blockers; several Medium-severity logic bugs)

## Top findings

| ID | Severity | Remediation Risk | Persona | Finding |
|----|----------|------------------|---------|---------|
| BUG-01 | High | Low | Engineer/QA | macOS `_get_rss_darwin()` returns peak RSS (`ru_maxrss`) not current RSS — metrics are wrong |
| BUG-02 | Medium | Low | Engineer | `_poll_cpu()` formula double-counts children CPU time between samples |
| BUG-03 | Medium | Low | Engineer/QA | ProvenanceFileProxy has no `write()` method — write-mode hash tracking is incomplete |
| BUG-04 | Medium | Low | Engineer | `start()` race: concurrent threads can both create a Run, second overwrites first |
| BUG-06 | Medium | Low | Engineer/QA | Hardware data never written to disk if process killed between thread completion and stop() |

(The complete findings list is in `findings.csv`.)

## Proposed plan (summary)

1. Fix macOS RSS to return current (not peak) via ctypes `task_info` or `ps`
2. Fix CPU% delta formula to correctly compute total CPU difference
3. Fix start() race condition by holding lock across Run() construction
4. Add write()/writelines() to ProvenanceFileProxy for write-mode hash accuracy
5. Re-write startup manifest after hardware thread completes
6. Improve event stream error reporting for non-serializable payloads
7. Reset SubprocessSpy records on uninstall to prevent cross-run leakage
8. Guard event stream emit after failed migration
9. Document flush-on-close assumption in ProvenanceFileProxy

## Deferred (with reason)

- None. All findings have Low remediation risk.

## Next step

Review the IPD (optionally run the `plan-review` workflow on it) and approve
before execution. This workflow does not execute the plan.
