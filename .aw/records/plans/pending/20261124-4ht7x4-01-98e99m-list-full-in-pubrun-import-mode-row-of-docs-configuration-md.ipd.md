# IPD: List full in PUBRUN_IMPORT_MODE row of docs/configuration.md

- Date: 2026-11-24
- Kind: child
- Concern: Documentation accuracy for `PUBRUN_IMPORT_MODE` in `docs/configuration.md`
- Scope: Add `full` to the `PUBRUN_IMPORT_MODE` row of the `## Environment Variables` table in `docs/configuration.md` so all six valid import modes from `src/pubrun/_modes.py::VALID_MODES` are listed.
- Scope-Paths: docs/configuration.md
- Item-Dependencies: none
- Status: to-review
- Short-Description: Add missing full import mode to the PUBRUN_IMPORT_MODE row in docs/configuration.md
- Work-Kind: followup
- Priority: low
- From-Backlog: 4ht7x4
- Set: 4ht7x4
- Order: 1
- Highest E allocated: 01
- Author: Antigravity
- Id: 98e99m

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 to-review (Antigravity): graduated from backlog item `4ht7x4` into a review-ready plan.
- 2026-11-25 draft (Antigravity): created.

## Goal

Bring the `PUBRUN_IMPORT_MODE` row in `docs/configuration.md#Environment Variables` into parity with `src/pubrun/_modes.py::VALID_MODES` and `src/pubrun/_config_boot.py::resolve_import_mode` by listing all six supported import modes, including `full`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Update PUBRUN_IMPORT_MODE row in docs/configuration.md

- [ ] E-01 Update the `PUBRUN_IMPORT_MODE` row in `docs/configuration.md#Environment Variables` so it lists all six valid import modes (`auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, and `full`) without modifying any other row or introducing em or en dashes.
  - Depends on: none
  - Expected outcome: The `PUBRUN_IMPORT_MODE` row reads `| \`PUBRUN_IMPORT_MODE\` | Canonical import mode: \`auto\`, \`noauto\`, \`nopatch\`, \`noconsole\`, \`minimal\`, or \`full\`. Takes highest precedence. |` (no other row in `docs/configuration.md` changes, and the edited line contains zero em or en dashes).
  - Execution state: pending

## Project conventions discovered (Step 0)

- Cite code by SYMBOL (`path::Name`) or by a quoted content string, with a line number only appended to one of those and never alone (`IPD-C801`).
- `src/pubrun/_modes.py::VALID_MODES` defines six modes: `auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, `full`.
- `src/pubrun/_config_boot.py::resolve_import_mode` validates `PUBRUN_IMPORT_MODE` against `VALID_MODES` and accepts `full` (returning `('full', 'env:PUBRUN_IMPORT_MODE')`).
- `docs/configuration.md#Environment Variables` currently reads `| \`PUBRUN_IMPORT_MODE\` | Canonical import mode: \`auto\`, \`noauto\`, \`nopatch\`, \`noconsole\`, or \`minimal\`. Takes highest precedence. |`.
- Agent execution contract: user-facing documentation (`docs/configuration.md`) must contain zero em or en dashes in authored or edited prose.

## Findings

The `PUBRUN_IMPORT_MODE` row in `docs/configuration.md#Environment Variables` omits `full`, even though `src/pubrun/_modes.py::VALID_MODES` and `src/pubrun/_config_boot.py::resolve_import_mode` accept all six modes.

## Proposed changes (ordered, validatable)

1. **`docs/configuration.md` (E-01):** Add `` `full` `` to the mode list in the `PUBRUN_IMPORT_MODE` row of `## Environment Variables`, leaving every other row unchanged.

## Deferred / out of scope (with reason)

- Resolving whether `pubrun run --mode` overrides an in-code `import pubrun.<mode>` (the "Takes highest precedence" semantics): tracked separately by backlog item `oubh58`.
  - Carrier: oubh58

## Scope check

- Over-scope: none. Only one table row in `docs/configuration.md` is modified.
- Under-scope: none. Matches backlog item `4ht7x4` exactly.

## Required tests / validation

- Run a one-line runtime check confirming `PUBRUN_IMPORT_MODE=full` resolves via `pubrun._config_boot.resolve_import_mode` to `('full', 'env:PUBRUN_IMPORT_MODE')` and that every name in `pubrun._modes.VALID_MODES` appears in the `PUBRUN_IMPORT_MODE` row of `docs/configuration.md`.
- Confirm zero em or en dashes in the added diff line.
- Run `python3 scripts/sanitize_paths.py --check --all` and confirm exit code 0.

## Spec / documentation sync

This plan is the documentation sync for `PUBRUN_IMPORT_MODE` in `docs/configuration.md`.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Paste `git diff docs/configuration.md` showing only the `PUBRUN_IMPORT_MODE` row updated to include all six modes (`auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, `full`) with zero em or en dashes; paste output of a Python check confirming `PUBRUN_IMPORT_MODE=full` resolves to `('full', 'env:PUBRUN_IMPORT_MODE')` via `src/pubrun/_config_boot.py::resolve_import_mode` and every mode in `src/pubrun/_modes.py::VALID_MODES` appears in the row; and paste `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`).

Execution contract:
1. **Open-questions precondition:** Zero blocking open questions remain before execution (`## Open questions` is empty).
2. **Scope declaration:** `- Scope-Paths:` declares `docs/configuration.md`. If execution must edit another file or leave a declared file unchanged, make the change and justify it with `--scope-reason` or `--scope-ack` at finalize.
3. **Validation honesty (HARD MUST):** Paste the actual diff, Python parity output, and `sanitize_paths.py` output observed after the final edit into `V-01`.
4. **Path-scoped commit and never-push:** Commit only `docs/configuration.md` through `aw commit 98e99m -- docs/configuration.md`; never use `git add -A` or `-a`, and never push without explicit human instruction.
5. **Lifecycle transition (conditional runner vs. standalone ownership):** When executed inside `aw oc run` / `aw agy run`, the runner owns the lifecycle move after the merge-and-revalidate gate; when executed standalone outside the runner, run `aw ipd finalize 98e99m` (never a hand-rolled `git mv` to `executed/`).
