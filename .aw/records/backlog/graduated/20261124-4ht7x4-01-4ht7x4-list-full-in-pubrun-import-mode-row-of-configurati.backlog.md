- Id: 4ht7x4
- Status: graduated
- Graduated-To: 4ht7x4
- Set: 4ht7x4
- Work-Kind: followup
- Priority: low
- Summary: List full in the PUBRUN_IMPORT_MODE row of the docs/configuration.md Environment Variables table
- Short-Description: List full in the PUBRUN_IMPORT_MODE row of the docs/configuration.md Environment Variables table

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-25 graduated (aw set): Graduated to review-ready IPD 98e99m (Set: 4ht7x4)
- 2026-11-25 created (aw backlog): List full in the PUBRUN_IMPORT_MODE row of the docs/configuration.md Environment Variables table

The `PUBRUN_IMPORT_MODE` row of `docs/configuration.md#Environment Variables` lists five import modes (`auto`, `noauto`, `nopatch`, `noconsole`, `minimal`) and omits `full`. `src/pubrun/_config_boot.py::resolve_import_mode` accepts every name in `src/pubrun/_modes.py::VALID_MODES`, which has six entries; with `PUBRUN_IMPORT_MODE=full` it returns `('full', 'env:PUBRUN_IMPORT_MODE')`. Acceptance: the row lists all six modes, including `full`, and no other row changes. Found while authoring plan q4f9wi (backlog mv1g3x), which is scoped to `docs/functional_spec.md` only.
