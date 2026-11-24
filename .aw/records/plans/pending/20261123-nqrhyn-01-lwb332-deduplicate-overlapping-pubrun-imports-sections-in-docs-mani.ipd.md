# IPD: Deduplicate overlapping pubrun_imports sections in docs/manifest.md

- Date: 2026-11-23
- Kind: child
- Concern: Manifest documentation accuracy and deduplication
- Scope: Remove the stale duplicate `## pubrun_imports` section in `docs/manifest.md` and reconcile the single remaining `## pubrun_imports` and `### pubrun_imports.requests[]` section against `src/pubrun/_bootstrap.py::get_import_metadata`, `src/pubrun/_modes.py::MODES`, and `schemas/manifest.schema.json`.
- Scope-Paths: docs/manifest.md
- Item-Dependencies: none
- Status: to-review
- Work-Kind: chore
- Priority: low
- From-Backlog: nqrhyn
- Set: nqrhyn
- Order: 1
- Highest E allocated: 02
- Author: Antigravity
- Id: lwb332

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-24 draft (Antigravity): created.
- 2026-11-24 to-review (Antigravity): graduated from backlog item `nqrhyn` into a review-ready plan.

## Goal

Eliminate the duplicate `## pubrun_imports` section in `docs/manifest.md` so the manifest reference documents `pubrun_imports` once, with exact parity against `src/pubrun/_bootstrap.py::get_import_metadata`, `src/pubrun/_modes.py::MODES`, and `schemas/manifest.schema.json`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Deduplicate and reconcile pubrun_imports in docs/manifest.md

- [ ] E-01 Remove the first, stale `## pubrun_imports` section in `docs/manifest.md` (the version that lists `capture_state` and omits `core_loaded`, `requests`, and `### pubrun_imports.requests[]`).
  - Depends on: none
  - Expected outcome: `docs/manifest.md` contains exactly one `## pubrun_imports` heading, and any internal TOC or cross-reference anchor pointing to `#pubrun_imports` resolves unambiguously to that single section.
  - Execution state: pending

- [ ] E-02 Reconcile the remaining `## pubrun_imports` and `### pubrun_imports.requests[]` tables in `docs/manifest.md` against `src/pubrun/_bootstrap.py::get_import_metadata`, `src/pubrun/_modes.py::MODES`, and `schemas/manifest.schema.json`, and remove any em or en dashes in edited lines.
  - Depends on: E-01
  - Expected outcome: The single `## pubrun_imports` table documents the exact nine schema and runtime fields (`selected_mode`, `selected_behavior`, `selected_by`, `selected_source`, `selected_at_utc`, `core_loaded`, `conflict_policy`, `conflicts_detected`, `requests`) and does not claim a nonexistent `capture_state` field; `selected_mode` lists all six valid modes (`"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, `"full"`); `selected_behavior` lists the emitted boolean keys (`auto_start`, `global_hooks`, `patch_subprocesses`, `patch_console`, `signal_hooks`, and optional `force_console` for `"full"`); `### pubrun_imports.requests[]` matches `schemas/manifest.schema.json`; and all edited lines contain zero em or en dashes.
  - Execution state: pending

## Project conventions discovered (Step 0)

- Cite code by SYMBOL (`module.function`) or by a quoted content string, with a line number only appended to one of those and never alone (`IPD-C801`).
- `src/pubrun/_bootstrap.py::get_import_metadata` emits exactly nine keys: `selected_mode`, `selected_behavior`, `selected_by`, `selected_source`, `selected_at_utc`, `core_loaded`, `conflict_policy`, `conflicts_detected`, and `requests`. It does not emit `capture_state`.
- `schemas/manifest.schema.json` (`properties.pubrun_imports`) defines those exact nine properties and no `capture_state`.
- `src/pubrun/_modes.py::MODES` defines six modes: `"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, and `"full"` (which adds `"force_console": True`).
- Agent execution contract: user-facing documentation (`docs/manifest.md`) must contain zero em or en dashes in authored or edited prose.

## Findings

`docs/manifest.md` currently contains two separate `## pubrun_imports` sections that disagree with each other:

1. The first occurrence documents only seven fields plus a nonexistent `capture_state` field, omitting `core_loaded`, `requests`, and `### pubrun_imports.requests[]`.
2. The second occurrence documents all nine fields plus `### pubrun_imports.requests[]` (matching `get_import_metadata` and `schemas/manifest.schema.json`), but needs verification against the six modes in `src/pubrun/_modes.py::MODES` (including `"full"` and `force_console`) and contains an em dash in the `selected_behavior` description.

## Proposed changes (ordered, validatable)

1. **`docs/manifest.md` (E-01):** Delete the stale first `## pubrun_imports` section and its separator so only one `## pubrun_imports` section remains. Check the top-level Table of Contents (if present) so it has a single entry for `pubrun_imports`.
2. **`docs/manifest.md` (E-02):** Verify every row in `## pubrun_imports` and `### pubrun_imports.requests[]` against `src/pubrun/_bootstrap.py::get_import_metadata`, `src/pubrun/_modes.py::MODES`, and `schemas/manifest.schema.json`. Ensure all six modes (`"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, `"full"`) and the `selected_behavior` keys are accurately documented, and replace any em or en dashes in edited rows with plain punctuation.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none. Only `docs/manifest.md` is modified; schema and runtime code are read-only sources of truth.
- Under-scope: none. Both the duplication and the field/mode parity check are covered.

## Required tests / validation

- Confirm `grep -c '^## `pubrun_imports`' docs/manifest.md` returns `1`.
- Inspect `git diff docs/manifest.md` against `src/pubrun/_bootstrap.py::get_import_metadata`, `src/pubrun/_modes.py::MODES`, and `schemas/manifest.schema.json`.
- Confirm zero em or en dashes in added or edited lines.
- Run `python3 scripts/sanitize_paths.py --check --all` and confirm exit code 0.

## Spec / documentation sync

This plan fixes duplication and drift in `docs/manifest.md`.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Paste the output of `grep -n '^## .*pubrun_imports' docs/manifest.md` showing exactly one matching heading and `git diff docs/manifest.md` showing removal of the stale duplicate section.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Paste the remaining `## pubrun_imports` and `### pubrun_imports.requests[]` section from `docs/manifest.md` (or `git diff docs/manifest.md`), confirming exact parity with the nine keys in `schemas/manifest.schema.json` and six modes in `src/pubrun/_modes.py::MODES` and zero em or en dashes in edited lines, plus the output of `python3 scripts/sanitize_paths.py --check --all`.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after this plan reaches `approved`. Execute `E-01` and `E-02`, verify `V-01` and `V-02` with pasted evidence, commit only `docs/manifest.md` through `aw commit`, and complete the post-gate lifecycle transition under `ipd-lifecycle`.
