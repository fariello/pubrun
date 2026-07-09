# Assessment run report - use-cases (whole project)

- Date / run ID: 20260708-231828
- Concern: use-cases (use-case / scenario coverage)
- Scope: whole project (pubrun library + CLI + docs + tests)
- IPD written: .agents/plans/pending/2026-07-08-assess-use-cases.md
- Verdict: **strong** for use-case coverage (narrow, specific gaps only)

## Top findings

| ID | Severity | Remediation Risk | Persona | Finding |
|----|----------|------------------|---------|---------|
| U1 | High | Low | Power, Stakeholder | Documented `resources` alias of `res` errors ("unknown command"); dispatch handles it but no argparse subparser is registered. |
| U3 | Medium | Low | Novice, QA | `pubrun init` (primary first-use path) has no test. |
| U4 | Medium | Low | QA, Stakeholder | SIGHUP interrupted-classification untested; SIGKILL->crashed only tested via `run` exit code, not the real lock-file crashed path. |
| U5 | Medium | Low-Medium | Stakeholder, QA | HPC parent-child hydration only unit-tested; no end-to-end child-with-META_REF test; `tests/scripts/hpc_node.py` fixture is unreferenced/dead. |
| U6 | Low | Low-Medium | Power, QA | No test for two live tracked runs in separate processes against one `./runs/` dir (normal HPC array reality). |
| U2 | Low | Low | Power | Dead dispatch strings `monitor`/`chart`/`stats` (unreachable, undocumented). |
| U7 | Low | Medium | Stakeholder | docs/research-use.md says the public example "should be added"; it already exists (`examples/minimal-research-workflow/`). Stale future tense. |

(The complete findings list is in `findings.csv`.)

## Proposed plan (summary)

1. Make `resources` a real argparse alias of `res` (or remove the doc promise; recommend making
   it work) and drop the dead `monitor`/`chart`/`stats` dispatch strings. (U1, U2)
2. Add a `pubrun init` test incl. the pre-existing-config safety case. (U3)
3. Add a SIGHUP interrupted test + a real SIGKILL'd-child crashed-classification test
   (`skipif win32`). (U4)
4. Add one end-to-end HPC-hydration test (child with `PUBRUN_META_REF`, assert heavy-capture skip
   + parent-context stitching); wire in or replace the dead `hpc_node.py` fixture. (U5)
5. Add a two-concurrent-live-runs test against one output dir. (U6)
6. Update docs/research-use.md to present-tense, pointing at the existing example. (U7)

## Deferred (with reason)

- None. All findings clear the Fix-Bar (Remediation Risk Low to Low-Medium); nothing reaches
  Medium-High, so nothing is deferred.

## Out-of-repo / organizational notes (if any)

- None. All proposed work is in-repo (code, tests, docs).
- Legitimately out of scope (not findings): real Jupyter-kernel / real Textual-TUI integration
  tests (high Complexity Remediation-Risk vs. the simplicity principle; guard logic already
  unit-tested); the four declared Roadmap items; Windows positive-path tests (owned by the
  compatibility lens).

## Next step

Review the IPD (optionally run the `plan-review` workflow on it) and approve before execution.
This workflow does not execute the plan.
