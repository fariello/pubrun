# IPD: Assess documentation - fix accuracy drift on the CLI/config/manifest surface

- Date: 2026-07-19
- Concern: documentation
- Scope: whole project, accuracy-first; concentrated on the CLI/config/manifest docs the recent
  `show config` + schema work touched or exposed (`README.md`, `docs/cli.md`, `docs/configuration.md`,
  `docs/manifest.md`, `schemas/manifest.schema.json`)
- Status: to-review
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

Keep pubrun's docs honest: every doc claim should describe what the software does *today* (the
documentation lens's #1 rubric, and this repo's "honest docs over impressive docs" principle). This
run was triggered by the doc-sync discipline in `AGENTS.md` after the `show config` family shipped.
The just-shipped `show config`/`configuration.md`/`manifest.md` docs are accurate; the findings are a
small set of real inaccuracies on adjacent surfaces the work touched or exposed. Fixing inaccuracies
is highest-harm and low remediation risk, so all are proposed.

## Project conventions discovered (Step 0)

- Guiding principles: no `GUIDING_PRINCIPLES.md`; principles from README (zero-dep, honest docs,
  never-intrude), `AGENTS.md` (doc-sync + matrix-validation discipline), CONTRIBUTING. Applied the
  universal fallback (honest/self-documenting/KISS) where unstated.
- Plan lifecycle: five-state (`pending/ executed/ superseded/ not-executed/ reusable/`), filename
  `YYYYMMDD-HHMM-NN-<slug>.md`, `Status:` front-matter (born `to-review`). Followed.
- Contributor contract: `AGENTS.md` (doc-sync after user-visible change -> this run; matrix-validation
  for contract-shaped changes -> relevant to D4).
- Stack: pure-Python library + argparse CLI; docs in `docs/` + `README.md`; manifest contract in
  `schemas/manifest.schema.json` (enforced by a conformance test gate).

## Findings

Severity = impact if left alone; Remediation Risk = the Fix-Bar gate. Persona: **Novice** = new user
from the README; **Engineer/Operator** = uses/maintains from the docs.

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence (doc -> code) |
|----|----------|------------------|---------|------|---------|------------------------|
| D1 | Medium | Low | Novice | README completeness/accuracy | README omits the entire `show config` family AND its `--show-config` row is now stale (still "Print the default configuration to the terminal", no deprecation note). A README reader cannot discover `show config` and is misinformed that `--show-config` is current. | `README.md:250-254` (show, no config family), `README.md:301` (`--show-config` row) -> `__main__.py:2499-2507` (family), `:2808-2812` (`--show-config` soft-deprecated) |
| D2 | Medium | Low | Engineer | Manifest reference accuracy | `docs/manifest.md` types `config.source_files` as `list[string]`, but the schema/contract emits an array of objects `{path, hash}`. A consumer coding to the doc would mis-parse the field. | `docs/manifest.md:252` (`list[string]`) -> `schemas/manifest.schema.json` `config_section.source_files.items` = object `{path, hash?}` |
| D3 | Low | Low | Engineer | Configuration doc precedence table | `docs/configuration.md:18` presents `./.config/pubrun/config.toml` as a distinct, lower precedence *tier* than `.pubrun.toml` (row 4 vs row 3), but the resolver merges both local files into ONE `local` layer. The relative order (`.pubrun.toml` wins) is stated correctly at `:22`; the table over-implies two tiers. | `docs/configuration.md:15-20` -> `config.py:113-129` (single merged local layer) |
| D4 | Medium | Low | Engineer/Operator | Contract accuracy (schema vs code) | **Peripheral to docs, but a real contract bug the doc sweep exposed:** code supports `capture.packages.mode = "imported-transitive"` (documented correctly at `docs/configuration.md:135`), but the manifest schema `packages_section.mode` enum omits it. A run using that mode would FAIL the schema conformance gate. Same class as the schema drift previously reconciled. | `capture/packages.py:41` (supported) + `docs/configuration.md:135` (documented) -> `schemas/manifest.schema.json` `packages_section.mode.enum` (omits `imported-transitive`) |

## Proposed changes (ordered, validatable)

Ordered inaccuracies-first (highest harm), all Low remediation risk.

| Step | Source | Change | Files | Remediation Risk | Validation |
|------|--------|--------|-------|------------------|------------|
| 1 | D1 | Add a short `show config` mention to the README CLI section (the three forms, one line each) and update the `--show-config` diagnostic-flags row to note it is deprecated in favor of `show default config`. Keep it concise (no bloat). | `README.md` | Low | README lists `show config`/`show run config`/`show default config`; `--show-config` row says deprecated |
| 2 | D2 | Fix `docs/manifest.md` `config.source_files` type: `list[object]` with `{path, hash?}`, matching the schema. | `docs/manifest.md` | Low | doc type matches `schemas/manifest.schema.json` field-for-field |
| 3 | D3 | Reword the `docs/configuration.md` precedence table so the two local config files are one tier (e.g. merge rows 3-4 into "Local project config (`.pubrun.toml`, then `.config/pubrun/config.toml`; `.pubrun.toml` wins)"), matching the single merged `local` layer. | `docs/configuration.md` | Low | table tiers match `_resolve_layers` layers; `.pubrun.toml`-wins note preserved |
| 4 | D4 | Add `"imported-transitive"` to the schema `packages_section.mode` enum (code supports it; doc documents it; only the schema is stale). Also complete the `default.toml` comment that enumerates the modes. **Contract change -> validate on the full CI matrix per AGENTS.md matrix-validation discipline.** Consider a conformance test that runs with `mode="imported-transitive"` so the gate covers it. | `schemas/manifest.schema.json`, `src/pubrun/resources/default.toml`, `tests/` | Low | a manifest produced with `packages.mode="imported-transitive"` passes the schema conformance test; full matrix green |

## Deferred / out of scope (with reason)

- Nothing deferred. All four findings are Low remediation risk and proposed.
- Explicitly OUT of scope (not findings): the README's pub/research framing (a separate, already-drafted
  decision - see the pending README-reframe IPD; do not pre-empt it here); prose-style polish (that is
  the `prose` lens, not accuracy); the show-config docs themselves (verified accurate this run).

## Scope check

- Over-scope: none. D4 is adjacent (schema, not prose) but is a genuine accuracy defect the doc lens
  surfaced and matches this repo's contract-honesty discipline; included rather than dropped.
- Under-scope: none identified; the show-config/config/manifest surface was swept and the accurate
  parts recorded (see run record `evidence.md`).

## Required tests / validation

- Steps 1-3 are prose/doc changes: verify each claim against the cited code line; check links; no code
  test needed.
- Step 4 is a **contract change** (schema enum): add/extend a conformance test and validate on the full
  CI matrix (3 OS x Python 3.8-3.14) before considering it done, per `AGENTS.md`.
- Re-run `/assess documentation` (or spot-verify) after to confirm the four discrepancies are closed.

## Spec / documentation sync

This IPD *is* documentation sync. D4 additionally touches the manifest contract (schema + a test) and
warrants a CHANGELOG entry ("schema: accept `imported-transitive` packages mode"). Steps 1-3 are
doc-only (no CHANGELOG needed unless the maintainer prefers one).

## Open questions

1. D1 README wording: how prominent should `show config` be - a one-line addition under the existing
   `show` entry, or its own short subsection? Recommend: one line under `show` + fix the flag row
   (KISS; the full detail already lives in `docs/cli.md`).
2. D4: fix the schema enum now (recommended - it is a latent gate failure), or split it to its own
   tiny contract IPD since it is not strictly "documentation"? Recommend fixing here; it is one line
   + a test and shares the reconciliation context.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before execution, and it is NOT
auto-executed. On approval: apply steps in order; for D4 validate on the CI matrix; commit path-scoped;
never push without explicit approval; then move this IPD to `.agents/plans/executed/` (Status ->
`executed`).

## Workflow history
- 2026-07-19 /assess documentation (opencode / its_direct/pt3-claude-opus-4.8-1m-us): assessed;
  proposed 4 changes.
