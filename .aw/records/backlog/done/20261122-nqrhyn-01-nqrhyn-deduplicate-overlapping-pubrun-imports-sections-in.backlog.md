- Id: nqrhyn
- Status: done
- Graduated-To: nqrhyn
- Set: nqrhyn
- Work-Kind: chore
- Priority: low
- Summary: Deduplicate overlapping pubrun_imports sections in docs/manifest.md
- Short-Description: Deduplicate overlapping pubrun_imports sections in docs/manifest.md

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-24 done (aw backlog): closed by aw agy run: IPD lwb332 executed (every IPD carrier is executed and this run executed .aw/records/plans/executed/20261123-nqrhyn-01-lwb332-deduplicate-overlapping-pubrun-imports-sections-in-docs-mani.ipd.md); evidence .aw/records/plans/executed/20261123-nqrhyn-01-lwb332-deduplicate-overlapping-pubrun-imports-sections-in-docs-mani.ipd.md
- 2026-11-24 graduated (aw set): Graduated to review-ready IPD lwb332 (Set: nqrhyn)
- 2026-11-22 created (aw backlog): Deduplicate overlapping pubrun_imports sections in docs/manifest.md

## Context
`docs/manifest.md` contains two separate `## pubrun_imports` top-level sections with overlapping but diverging field tables: the first section lists 7 fields including `capture_state` (without `core_loaded` or `requests`), while the second section lists 9 fields including `core_loaded`, `requests`, and `### pubrun_imports.requests[]` (without `capture_state`).

## Acceptance criteria
- `docs/manifest.md` contains a single authoritative `## pubrun_imports` section reconciled against `src/pubrun/_bootstrap.py::get_import_metadata` and `schemas/manifest.schema.json`.
- Zero em dashes (U+2014) or en dashes (U+2013) appear in edited lines.
