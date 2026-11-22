# IPD: Assess documentation - fix accuracy drift on the CLI/config/manifest surface

- Date: 2026-07-19
- Concern: documentation
- Scope: whole project, accuracy-first; concentrated on the CLI/config/manifest docs the recent
  `show config` + schema work touched or exposed (`README.md`, `docs/cli.md`, `docs/configuration.md`,
  `docs/manifest.md`, `schemas/manifest.schema.json`)
- Status: executed
- Approval: human-approved; executed as ab2d0bf (on origin/main)
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
| 1 | D1 | Add a short **`show config` subsection** to the README CLI section (the three forms - `show config` / `show run config [<id>]` / `show default config` - one line each, with a one-line example), matching `docs/cli.md`'s detail at a summary level. Separately, **hide `--show-config` from `--help`** (argparse `help=argparse.SUPPRESS` on the flag) so it no longer appears in the diagnostic-flags list; it keeps working but emits the existing stderr deprecation notice naming the alternative (`show default config`). Remove/replace the stale `--show-config` row in the README diagnostic-flags table (since it is now hidden). (Q2 decision.) | `README.md`, `src/pubrun/__main__.py` (the `--show-config` argparse `help`) | Low | README has a `show config` subsection; `pubrun -h` no longer lists `--show-config`; `pubrun --show-config` still prints defaults + a stderr deprecation notice naming `show default config` |
| 2 | D2 | Fix `docs/manifest.md` `config.source_files` type: `list[object]` with `{path, hash?}`, matching the schema. **Also note it is currently always empty** (`tracker.py:648-649` hardcodes `source_files: []` and `sources_path: null`), so the doc does not imply data that never appears (PR-002). | `docs/manifest.md` | Low | doc type matches `schemas/manifest.schema.json` field-for-field; doc notes the field is presently unpopulated |
| 3 | D3 | Reword the `docs/configuration.md` precedence table so the two local config files are one tier (e.g. merge rows 3-4 into "Local project config (`.pubrun.toml`, then `.config/pubrun/config.toml`; `.pubrun.toml` wins)"), matching the single merged `local` layer. | `docs/configuration.md` | Low | table tiers match `_resolve_layers` layers; `.pubrun.toml`-wins note preserved |
| 4 | D4 | **Reconcile the WHOLE `packages_section.mode` enum against every mode the code can emit** (PR-001), not just the one found: grep `capture/packages.py` for all accepted `mode` values (currently `imported-only`, `imported-transitive`, `top-level-installed`, `full-environment`) and ensure each is in the schema enum. `imported-transitive` is the confirmed-missing one. Complete the `default.toml` comment that enumerates the modes. Add a conformance test that produces a manifest with **`packages.mode="imported-transitive"`** (the previously-uncovered value) and validates it against the schema (PR-004). **Contract change -> validate on the full CI matrix per AGENTS.md matrix-validation discipline.** | `schemas/manifest.schema.json`, `src/pubrun/resources/default.toml`, `tests/test_manifest_schema.py` | Low | every mode `capture/packages.py` accepts is in the schema enum; a manifest with `packages.mode="imported-transitive"` passes the conformance test; full matrix green |

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

## Open questions (resolved interactively 2026-07-19 during /plan-review)

1. **D1 README prominence** -> RESOLVED (Q2): a short `show config` SUBSECTION in the README (the three
   forms + a one-line example), AND hide `--show-config` from `--help` (argparse `SUPPRESS`) while it
   keeps working with the stderr deprecation notice naming `show default config`. Step 1 updated.
2. **D4 here vs. split** -> RESOLVED (Q1): keep D4 in this IPD (one enum reconciliation + a test;
   shares the schema context; the CI-matrix run is cheap). The whole IPD's execution is therefore
   gated on the full CI matrix because of D4.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before execution, and it is NOT
auto-executed. Execution contract:

- Open questions: both resolved above (Q1 keep-D4-here, Q2 subsection + hide `--show-config`).
- Scope fence: only `README.md`, `docs/manifest.md`, `docs/configuration.md`,
  `schemas/manifest.schema.json`, `src/pubrun/resources/default.toml`, `src/pubrun/__main__.py`
  (the `--show-config` help only), `tests/test_manifest_schema.py`, and `CHANGELOG.md` (D4 entry).
  Do NOT touch the README pub/research framing (owned by the pending README-reframe IPD).
- **Honesty rule (hard MUST):** when reporting that tests pass, paste the ACTUAL runner output; never
  claim a pass that was not run.
- **Matrix rule:** D4 is a contract change; validate on the full CI matrix (3 OS x Python 3.8-3.14)
  before considering execution complete - local green is not done.
- Commit **path-scoped** (only the files above); **never push** without explicit human approval.
- Only after CI-green + approval, `git mv` this IPD to `.agents/plans/executed/` and set
  `Status: executed`.

## Execution notes (2026-07-19)

Executed after human approval; local suite 906 passed, 2 skipped. Commit-scoped to the fence.

- **D1:** README `show config` subsection added; `--show-config` hidden from `--help`
  (`argparse.SUPPRESS`, `__main__.py`) - still functional, still prints the stderr deprecation
  notice; stale README flag row replaced with a deprecation note. Verified: `pubrun -h` no longer
  lists `--show-config`; `pubrun --show-config` prints defaults + notice.
- **D2:** `docs/manifest.md` `source_files` -> `list[object]` `{path, hash?}` + "currently always
  empty" note.
- **D3:** `docs/configuration.md` precedence table collapsed the two local files into one tier.
- **D4:** added `imported-transitive` to the schema `packages_section.mode` enum + completed the
  `default.toml` comment + a `packages-transitive` conformance variant. **The new conformance test
  immediately surfaced a SECOND, deeper gap (as PR-001's full-reconciliation mandate anticipated):**
  transitive package records carry a `required_by` (list[str]) field the schema's `package_record`
  rejected (`additionalProperties:false`). Added `required_by` to `package_record` and documented it
  in `docs/manifest.md`. So D4 reconciled BOTH the mode enum and the record shape. CHANGELOG updated.
- **Status: implemented + pushed (`ab2d0bf`), green on every CI job that ran the D1-D4 work; NOT yet
  moved to `executed/`.** The last CI run went red only on an UNRELATED pre-existing order/timing
  flake (`test_new_features.py::TestProvenanceWriteHash`, ubuntu-3.13) - not touched by D1-D4. Per the
  maintainer's decision, this IPD is HELD in `pending/` until the suite is reliably green, which is
  gated on the flaky-test-hardening IPD (`.agents/plans/pending/20260720-0026-01-flaky-test-isolation-hardening.md`).
  Once that lands and a full matrix run is green, move this to `executed/`. The D1-D4 changes
  themselves are complete and correct.

## Plan-review findings (2026-07-19)

Independent re-verification confirmed all four findings (D1-D4) against current code. Review findings
on the PLAN itself (all FIXED in-plan; none deferred):

- **PR-001 (Medium, under-scope):** D4 patched only the one missing mode; widened it to reconcile the
  WHOLE `packages_section.mode` enum against every mode `capture/packages.py` accepts.
- **PR-002 (Low, under-scope):** D2 did not note that `source_files`/`sources_path` are hardcoded
  empty (`tracker.py:648-649`); added the note so the doc does not imply data that never appears.
- **PR-003 (Low, gate):** execution gate lacked the hard-MUST honesty rule (paste actual runner
  output); added, plus a scope fence and path-scoped/never-push/lifecycle contract.
- **PR-004 (Low, in-scope):** D4's test target was vague; specified a conformance test that produces a
  manifest with `packages.mode="imported-transitive"` (the previously-uncovered value).

## Workflow history
- 2026-07-19 /assess documentation (opencode / its_direct/pt3-claude-opus-4.8-1m-us): assessed;
  proposed 4 changes.
- 2026-07-19 /plan-review (opencode / its_direct/pt3-claude-opus-4.8-1m-us): APPROVE WITH REVISIONS
  APPLIED; PR-001..PR-004 all FIXED; 2 open questions resolved interactively. Readiness: GO (pending
  human approval to execute).
- 2026-07-20 executed: D1-D4 implemented + pushed as ab2d0bf (confirmed on origin/main). Held in
  pending/ only until the suite was reliably green, gated on the flaky-test-hardening IPD
  (20260720-0026-01). That gate cleared: 20260720-0026-01 executed and the full CI matrix ran green
  (run 29779910507). Gate satisfied -> Status: executed; git mv pending/ -> executed/.
