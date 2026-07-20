# Assessment run report - documentation (whole project, accuracy-first)

- Date / run ID: 20260719-230705
- Concern: documentation
- Scope: whole project, accuracy-first; concentrated on the CLI/config/manifest surface the recent
  `show config` + schema work touched or exposed.
- IPD written: `.agents/plans/pending/20260719-2307-01-assess-documentation.md`
- Verdict: **adequate** for documentation (just-shipped docs accurate; 4 small, real inaccuracies on
  adjacent surfaces, all low-risk to fix).

## Top findings

| ID | Severity | Remediation Risk | Persona | Finding |
|----|----------|------------------|---------|---------|
| D1 | Medium | Low | Novice | README omits the `show config` family and its `--show-config` row is stale (no deprecation note). |
| D2 | Medium | Low | Engineer | `docs/manifest.md` types `config.source_files` as `list[string]`; schema emits array of `{path, hash}` objects. |
| D3 | Low | Low | Engineer | `docs/configuration.md` precedence table presents the two local config files as separate tiers; the resolver merges them into one `local` layer. |
| D4 | Medium | Low | Engineer/Operator | Schema `packages_section.mode` enum omits `imported-transitive`, which the code supports and docs document; a run using it would fail the schema conformance gate. (Contract bug surfaced by the doc sweep.) |

(Complete list in `findings.csv`.)

## Proposed plan (summary)

1. (D1) Add `show config` family to the README CLI section + mark `--show-config` deprecated.
2. (D2) Fix `config.source_files` type in `docs/manifest.md` to `list[object]` `{path, hash?}`.
3. (D3) Reword the configuration precedence table so the two local files are one tier.
4. (D4) Add `imported-transitive` to the schema `packages_section.mode` enum + complete the
   `default.toml` comment + a conformance test; validate on the CI matrix (contract change).

## Deferred (with reason)

- None. All four findings are Low remediation risk and proposed.

## Out-of-repo / organizational notes (if any)

- None. All fixes are in-repo.
- Intentionally NOT proposed (not findings): the README pub/research framing (owned by the pending
  README-reframe IPD; not pre-empted here); prose-style polish (the `prose` lens, not accuracy); the
  show-config docs (verified accurate this run).

## Next step

Review the IPD (optionally run `/plan-review`) and approve before execution. This workflow does not
execute the plan.
