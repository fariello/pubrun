# IPD: List full in PUBRUN_IMPORT_MODE row of docs/configuration.md

- Date: 2026-11-24
- Kind: child
- Concern: Documentation accuracy for `PUBRUN_IMPORT_MODE` in `docs/configuration.md`
- Scope: Add `full` to the `PUBRUN_IMPORT_MODE` row of the `## Environment Variables` table in `docs/configuration.md` so all six valid import modes from `src/pubrun/_modes.py::VALID_MODES` are listed.
- Scope-Paths: docs/configuration.md
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: simple
- Short-Description: Add missing full import mode to the PUBRUN_IMPORT_MODE row in docs/configuration.md
- Work-Kind: followup
- Priority: low
- From-Backlog: 4ht7x4
- Set: 4ht7x4
- Order: 1
- Highest E allocated: 01
- Author: Antigravity
- Id: 98e99m
- Approval: 2026-11-25, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 approved (aw set): status set to approved
- 2026-11-25 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003
- 2026-11-25 to-review (Antigravity): graduated from backlog item `4ht7x4` into a review-ready plan.
- 2026-11-25 draft (Antigravity): created.

## Goal

Bring the `PUBRUN_IMPORT_MODE` row in `docs/configuration.md#Environment Variables` into parity with `src/pubrun/_modes.py::VALID_MODES` and `src/pubrun/_config_boot.py::resolve_import_mode` by listing all six supported import modes, including `full`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Update PUBRUN_IMPORT_MODE row in docs/configuration.md

- [x] E-01 Update the `PUBRUN_IMPORT_MODE` row in `docs/configuration.md#Environment Variables` so it lists all six valid import modes (`auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, and `full`) without modifying any other row or introducing em or en dashes.
  - Depends on: none
  - Expected outcome: The `PUBRUN_IMPORT_MODE` row reads ``| `PUBRUN_IMPORT_MODE` | Canonical import mode: `auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, or `full`. Takes highest precedence. |`` (no other row in `docs/configuration.md` changes, and the edited line contains zero em or en dashes).
  - Execution state: performed

## Project conventions discovered (Step 0)

- Cite code by SYMBOL (`path::Name`) or by a quoted content string, with a line number only appended to one of those and never alone (`IPD-C801`).
- `src/pubrun/_modes.py::VALID_MODES` defines six modes: `auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, `full`.
- `src/pubrun/_config_boot.py::resolve_import_mode` validates `PUBRUN_IMPORT_MODE` against `VALID_MODES` and accepts `full` (returning `('full', 'env:PUBRUN_IMPORT_MODE')`).
- Importing `pubrun._config_boot` executes `src/pubrun/__init__.py`, which runs `_execute_boot_sequence()` because `pubrun._config_boot` is not in `src/pubrun/_bootstrap.py::is_mode_submodule_import_in_progress`'s `_MODE_SUBMODULES`. Set `PUBRUN_AUTO_START=false` before importing `pubrun._config_boot` and set `os.environ["PUBRUN_IMPORT_MODE"] = "full"` afterward so validation creates no `runs/` directory in the working tree.
- `docs/configuration.md#Environment Variables` currently reads ``| `PUBRUN_IMPORT_MODE` | Canonical import mode: `auto`, `noauto`, `nopatch`, `noconsole`, or `minimal`. Takes highest precedence. |``.
- Agent execution contract: user-facing documentation (`docs/configuration.md`) must contain zero em or en dashes in authored or edited prose.

## Findings

The `PUBRUN_IMPORT_MODE` row in `docs/configuration.md#Environment Variables` omits `full`, even though `src/pubrun/_modes.py::VALID_MODES` and `src/pubrun/_config_boot.py::resolve_import_mode` accept all six modes.

## Proposed changes (ordered, validatable)

1. **`docs/configuration.md` (E-01):** Add `` `full` `` to the mode list in the `PUBRUN_IMPORT_MODE` row of `## Environment Variables`, leaving every other row unchanged.

## Deferred / out of scope (with reason)

- Precedence between launch-time `pubrun run --mode` and explicit in-code `import pubrun.<mode>` (and any change to the `"Takes highest precedence."` phrasing): tracked separately by backlog item `oubh58` (graduated to plan `lhwy0t`); backlog item `4ht7x4` is scoped strictly to adding `full` to the mode list in the `PUBRUN_IMPORT_MODE` row.
  - Carrier: oubh58

## Scope check

- Over-scope: none. Only one table row in `docs/configuration.md` is modified.
- Under-scope: none. Matches backlog item `4ht7x4` exactly.

## Required tests / validation

- Run a side-effect-free runtime and documentation parity check confirming `src/pubrun/_config_boot.py::resolve_import_mode` resolves `PUBRUN_IMPORT_MODE=full` to `('full', 'env:PUBRUN_IMPORT_MODE')`, the `PUBRUN_IMPORT_MODE` row in `docs/configuration.md` matches uniquely and lists every backticked mode in `src/pubrun/_modes.py::VALID_MODES`, and the edited row contains zero em or en dashes (without creating a `runs/` directory):

  ```sh
  PUBRUN_AUTO_START=false PYTHONPATH=src python3 -c 'import os, pathlib; from pubrun._config_boot import resolve_import_mode; from pubrun._modes import VALID_MODES; os.environ["PUBRUN_IMPORT_MODE"] = "full"; res = resolve_import_mode(); assert res == ("full", "env:PUBRUN_IMPORT_MODE"), res; rows = [l for l in pathlib.Path("docs/configuration.md").read_text(encoding="utf-8").splitlines() if l.startswith("| `PUBRUN_IMPORT_MODE` |")]; assert len(rows) == 1, rows; missing = [m for m in sorted(VALID_MODES) if f"`{m}`" not in rows[0]]; assert not missing, missing; assert not any(c in rows[0] for c in "\u2014\u2013"), rows[0]; print("OK:", res, sorted(VALID_MODES))'
  ```
- Run `python3 scripts/sanitize_paths.py --check --all` and confirm exit code 0.

## Spec / documentation sync

This plan is the documentation sync for `PUBRUN_IMPORT_MODE` in `docs/configuration.md`.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [x] V-01 validates E-01
  - Required evidence: Paste `git diff docs/configuration.md` showing only the `PUBRUN_IMPORT_MODE` row updated to include all six modes (`auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, `full`) with zero em or en dashes; paste output of the side-effect-free `PUBRUN_AUTO_START=false PYTHONPATH=src python3 -c ...` check from `Required tests / validation` confirming `src/pubrun/_config_boot.py::resolve_import_mode` returns `('full', 'env:PUBRUN_IMPORT_MODE')`, every mode in `src/pubrun/_modes.py::VALID_MODES` appears in the `PUBRUN_IMPORT_MODE` row, and zero em or en dashes appear in the row (printing `OK: ...` with exit 0 and leaving no untracked `runs/` files); and paste `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
    1. `git diff docs/configuration.md`:
    ```diff
    diff --git a/docs/configuration.md b/docs/configuration.md
    index f16789b..929e83f 100644
    --- a/docs/configuration.md
    +++ b/docs/configuration.md
    @@ -358,7 +358,7 @@ long); override any of them in your `.pubrun.toml`.

     | Variable | Description |
     |---|---|
    -| `PUBRUN_IMPORT_MODE` | Canonical import mode: `auto`, `noauto`, `nopatch`, `noconsole`, or `minimal`. Takes highest precedence. |
    +| `PUBRUN_IMPORT_MODE` | Canonical import mode: `auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, or `full`. Takes highest precedence. |
     | `PUBRUN_PROFILE` | **Deprecated and inert.** Sets `[core].profile`, which has no effect on capture (see the `[core]` table). Use the `capture.*` keys instead. |
     | `PUBRUN_AUTO_START` | Legacy alias for import mode. `"1"`, `"true"`, `"yes"`, or `"on"` maps to `auto`; `"0"`, `"false"`, `"no"`, or `"off"` maps to `noauto` (case-insensitive). Other values are ignored. |
     | `PUBRUN_META_REF` | Path to a parent `meta.json` for HPC hydration. Child runs will reference this. |
    ```
    2. Side-effect-free runtime and documentation parity check (`PUBRUN_AUTO_START=false PYTHONPATH=src python3 -c ...`):
    `OK: ('full', 'env:PUBRUN_IMPORT_MODE') ['auto', 'full', 'minimal', 'noauto', 'noconsole', 'nopatch']` (exit code `0`; `git status -sb` showed `M docs/configuration.md` with no untracked `runs/` directory or files).
    3. `python3 scripts/sanitize_paths.py --check --all`: exit code `0` (zero findings).
  - Result: pass

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
