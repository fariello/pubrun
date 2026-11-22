# Assessment run report — documentation

- Date / run ID: 20260707-150242
- Concern: documentation (accuracy-first lens)
- Scope: whole project docs; emphasis on `README.md`, `docs/cli.md`, `CHANGELOG.md` nav
- IPD written: `.agents/plans/pending/2026-07-07-assess-documentation.md`
- Verdict: **needs work** for documentation (accuracy)

## Top findings

| ID | Severity | Remediation Risk | Persona | Finding |
|----|----------|------------------|---------|---------|
| D3 | High | Low | novice/engineer | README documents `pubrun bug-report`, a command that no longer exists (now `report-bug` + `feedback`). |
| D1 | High | Low | novice/engineer | README says "fourteen commands"; there are 20. |
| D6 | High | Low | novice/engineer | Roadmap lists `pubrun combined` as "future" — it already ships (documented elsewhere in the same README). |
| D7 | High | Low | novice/engineer | Roadmap lists timestamped console capture as "future" — it ships. |
| D2 | High | Low | novice/engineer | `docs/cli.md` says "thirteen commands" — wrong and self-contradictory with its own body (20). |
| D4 | Medium | Low | novice/engineer | README documents `pubrun report`; canonical command is `show` (report is a hidden alias). |
| D5 | Medium | Low | novice/engineer | README documents `pubrun resources`; canonical are `res`/`cpu`/`mem`. |
| D9 | Medium | Low | novice | README CLI section omits `init`, `self-check`, `inspect`, `bench`, `report-bug`, `feedback`, `show`, `res`, `cpu`, `mem`. |
| D10 | Medium | Low | novice | Two License sections in README. |
| D11 | Medium | Low | novice | Two differing suggested-citation strings. |
| D12 | Medium | Low | engineer | CHANGELOG nav omits Performance & HPC links. |
| D8 | Medium | Low | engineer | Roadmap lists GitHub Actions CI as "future" — it ships. |
| D13 | Low | Low | novice | README footer nav placed mid-document. |
| D14 | Low | — | engineer | `docs/design/file-io-provenance-evaluation.md` not in nav (judged intentional; no change). |

(The complete findings list is in `findings.csv`.)

## Proposed plan (summary)

Documentation-only, fix-by-default (all Low Remediation Risk), inaccuracies first:
1. De-brittle the command count (README + `docs/cli.md`).
2. Replace `bug-report` section with `report-bug` + `feedback`.
3. Retitle `report` → `show`; `resources` → `res`/`cpu`/`mem` (note aliases).
4. Purge shipped items from the Roadmap "Future" (combined, timestamped capture, CI).
5. Add concise README CLI entries for `init`, `self-check`, `inspect`, `bench` (link to `docs/cli.md`).
6. Consolidate to one License section + one citation string (aligned to `CITATION.cff`).
7. Add Performance & HPC to the CHANGELOG nav; move README footer nav to the end.

## Deferred (with reason)

- None deferred on Remediation-Risk grounds — every fix is documentation-only and Low risk.
- D14 is a no-op by judgment (intentional internal design note), not a risk deferral.

## Out-of-repo / organizational notes (if any)

- None. All fixes are in-repo Markdown edits.

## Verified-accurate (no action)

- README nav links all resolve; `docs/cli.md` nav complete.
- Roadmap items 1/3/4/5 (Sphinx/MkDocs, plugin model, `register_artifact`, `register_metadata`)
  are genuinely unimplemented (grep found no such symbols) and correctly listed as future.
- `docs/configuration.md` correctly documents `[capture.file_io].level="stat"` default,
  `[capture.resources].system_metrics`, and correctly has NO `[capture.filesystem]` key (the
  live probe is CLI/diagnostic-only by design).

Next step: review the IPD (optionally run `plan-review`) and approve before execution. This
workflow does not execute the plan.
