# Assessment run report - UI/UX (CLI + API)

- Date / run ID: 20260704-212506
- Concern: UI/UX usability and intuitiveness
- Scope: CLI commands, Python API
- IPD written: .agents/plans/pending/20260704-assess-ui-ux.md
- Verdict: adequate for UI/UX (functional and clear for power users; novice onboarding gaps)

## Top findings

| ID | Severity | Remediation Risk | Persona | Finding |
|----|----------|------------------|---------|---------|
| UX-01 | Medium | Low | Novice | Unknown command error shows all aliases (noisy, confusing) |
| UX-03 | Low | Low | Novice | "No runs found" gives no guidance on how to start |
| UX-06 | Low | Low | Power-user | `clean -y` deletes without showing summary |
| UX-08 | Low | Low | Stakeholder | No `pubrun init` entry point for first-time CLI users |

## Proposed plan (summary)

1. Suppress aliases from argparse error messages
2. Add helpful hint when no runs found
3. Add guidance to `diff` with < 2 runs
4. Document useful Run attributes in start() docstring
5. Show summary before `-y` delete
6. Add `pubrun init` as getting-started entry point
7. Improve `--info` help text

## Deferred (with reason)

- UX-02: Remediation Risk Medium-High on complexity — argparse alias separation
  requires deep subclassing. Confusing but not broken.

## Next step

Review the IPD and approve before execution.
