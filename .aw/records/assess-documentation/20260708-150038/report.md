# Assessment run report — documentation

- Date / run ID: 20260708-150038
- Concern: documentation (accuracy-first lens)
- Scope: whole project docs; emphasis on `README.md` CLI section, `docs/cli.md`,
  `docs/configuration.md`, `CHANGELOG.md` — triggered by the 7-IPD CLI/UX batch
- IPD written: `.agents/plans/pending/2026-07-08-assess-documentation.md`
- Verdict: **adequate, with fixes needed** for documentation (2 genuine accuracy defects +
  README lag)

## Top findings

| ID | Severity | Remediation Risk | Persona | Finding |
|----|----------|------------------|---------|---------|
| D3 | High | Low | novice/engineer | README `self-check` missing `--quiet`/`--json`/`-v` and the new itemized-by-default behavior. |
| D1 | Medium | Low | engineer | `bench --passes` help says "(default 2)" but the effective default tier is 3 passes — stale, contradicts the tier docs. |
| D2 | Medium | Low | engineer | CHANGELOG claims `pubrun bench --no-baseline`; that flag exists only on the harness, not the front-end. |
| D4 | Medium | Low | novice/engineer | README `diff` omits `--table` and the concise `--basic`/`--standard` behavior. |
| D5 | Medium | Low | novice/engineer | README `bench` omits `--rigorous` tier + baseline pass. |
| D6 | Medium | Low | novice/engineer | Recency-index run selector not documented in README. |
| D7 | Medium | Low | engineer | `cli.md` `res`/`cpu`/`mem` omit `--average` (+ `-l/--last`, run filters). |
| D8 | Low | Low | engineer | `configuration.md` `[diff]` ignore lists shown as stale `...` placeholders. |
| D9 | Low | Low | novice | README `res` predates peak/avg/min + tree CPU. |
| D10 | Low | Low | novice | README omits the output-prefix scheme. |
| D11 | Low | Low | engineer | `cli.md` `status` column list omits the new `#` recency column. |

(Full list = these 11; there is no larger `findings.csv` tail beyond them.)

## Proposed plan (summary)

Documentation-first, fix-by-default (all Low remediation risk), inaccuracies first:
1. Fix `bench --passes` "(default 2)" help (D1).
2. Resolve `--no-baseline`: expose on `pubrun bench` or correct the CHANGELOG (D2, Open Q1).
3. README: update `self-check` (D3), `diff` (D4), `bench` (D5), add recency selector (D6),
   refresh `res` + note output prefixes (D9/D10).
4. `cli.md`: document `res`/`cpu`/`mem` `--average`/`-l`/filters (D7); add `#` column to
   `status` (D11).
5. `configuration.md`: real `[diff]` ignore-list defaults (D8).

## Deferred (with reason)

- None deferred on Remediation-Risk grounds — every fix is Low risk.
- Noted out-of-scope: a pre-existing duplicate `## pubrun_imports` heading in `manifest.md`
  (structural nit, predates the batch) — for a future general docs cleanup.

## Verified clean (no action)

- `docs/manifest.md` fully covers the batch's new fields (`peak_tree_cpu_percent`,
  `python.environment_kind`/`in_venv`/`sys_path_len`).
- Nav-link integrity (README + CHANGELOG) — all resolve.
- CHANGELOG covers the whole batch (except the D2 `--no-baseline` line).
- Roadmap "Future" items genuinely unshipped; README has no stale command-count number.

Next step: review the IPD (optionally run `plan-review`) and approve before execution. This
workflow does not execute the plan.
