# Assessment run report - documentation (scoped: this session's user-visible changes)

- Date / run ID: 20260709-210203
- Concern: documentation (accuracy-first)
- Scope: the user-visible changes shipped this session — the `core.profile` deprecation
  (+ new `manifest.config.notices` field and its CLI surfacing) and the `resources` alias.
  Not a full-repo documentation sweep.
- IPD written: `.agents/plans/pending/2026-07-09-manifest-schema-reconciliation.md` (for the
  larger pre-existing finding only; the scoped findings were fixed in place).
- Verdict: **needs work → fixed** for the scoped surface (one BLOCKER I introduced, now fixed;
  a larger pre-existing schema-drift defect filed as an IPD + guarded by a new test).

## Top findings

| ID | Severity | Remediation Risk | Persona | Finding |
|----|----------|------------------|---------|---------|
| D1 | BLOCKER | Low | engineer | New `manifest.config.notices` field violated the shipped JSON schema (`config_section` has `additionalProperties:false`) — every profile-notice manifest failed validation. |
| D2 | Medium | Low | engineer/novice | `config.notices` was undocumented in `docs/manifest.md`. |
| D3 | Low | Low | novice | `docs/manifest.md` `suppressed` state still said "disabled by configuration or profile" — residual false `profile` claim. |
| D4 | High | Low | engineer | No jsonschema conformance test existed, so schema drift was silent (root cause of D1 going unnoticed and of D5). |
| D5 | High | (see IPD) | engineer | **Pre-existing:** the manifest schema is broadly stale — 7 conformance errors on a default manifest (filesystem, capture flags, host.os_release + hostname-type disagreement, packages.source, python fields, resources fields). |

## Fixed in place (this session's scope)

- **D1** — added `notices` to `config_section` in `schemas/manifest.schema.json` (with item shape).
- **D2** — documented `config.notices` in `docs/manifest.md` `config` table.
- **D3** — corrected the `suppressed` capture-state description (removed "or profile").
- **D4** — added `tests/test_manifest_schema.py`: the `config` section (incl. a real `notices`
  manifest) validates now; the schema document is checked as valid JSON Schema; and a
  `strict=False` `xfail` full-manifest test is the tripwire for D5. Added `jsonschema>=4.0` to the
  `dev` extra (test-only; pubrun stays zero-runtime-dependency).
- **Self-test coverage** (maintainer request) — `tests/test_cli.py::TestCliRunTests` now asserts the
  `--run-tests` end-to-end mock actually runs a tracked script and validates a well-formed manifest
  (previously the self-test swallowed manifest errors silently).

## Proposed plan (summary) — D5 only

Full manifest-schema reconciliation across the 7 drifted sections + flip the xfail conformance test
to a hard CI gate. See the IPD. Not executed.

## Deferred (with reason)

- None from the scoped set (D1-D4 fixed). D5 is not deferred — it is filed as an approved-pending IPD
  because it is a larger, pre-existing, cross-section change that warrants its own reconciliation pass
  and per-section verification (maintainer directed: fix my field now, IPD the rest, add drift tests).

## Next step

Approve/execute the schema-reconciliation IPD when prioritized. This session's scoped doc fixes are
committed; full suite green.
