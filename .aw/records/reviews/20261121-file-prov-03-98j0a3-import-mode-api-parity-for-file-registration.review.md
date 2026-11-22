# Review findings: ipd 98j0a3

- Subject-Id: 98j0a3
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, Mermaid `erDiagram`, `E-01`..`E-03`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `Scope check`, `Required tests`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-03`, and `Approval and execution gate` of `.aw/records/plans/pending/20261121-file-prov-03-98j0a3-import-mode-api-parity-for-file-registration.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `Goal`, `E-01`..`E-03` | Long single-sentence goal/outcomes without parent-package or lazy-import precision | Split into short, complete sentences naming alias parity, parent-package `_pkg` binding, `pubrun.report` preservation, and lazy `pubrun.capture.file_io` isolation | Technical writing requirements 2, 5, and 6 |
| `Project conventions`, `Findings`, `Deferred`, `Spec / documentation sync` | Informal citations, bare IDs (`x6alw4`, `4gpguy`), and missing `- Carrier-Declined:` line on deferred item | Standardized citations to `path::Symbol`, labeled referenced IDs (`x6alw4`, `52dl55`, `4gpguy`, `vtkkn1`), and added `- Carrier-Declined:` to deferred refactor | `steps/p-proofread.md` Section 11.1 and `check.ipd-uncarried-obligation` |
| `Validation and cross-check` boilerplate | Two em dashes triggering `IPD-C802` advisories | Replaced the two em dashes with parentheses | Zero `IPD-C802` advisories while preserving exact meaning |
| `Approval and execution gate` | One-line paragraph missing prerequisite gate, `--scope-reason`/`--scope-ack` fence, `never push`/`git add -A`, and giving an unconditional lifecycle-transition instruction | Replaced with complete 5-item execution contract including prerequisite `52dl55`, compliant scope declaration, HARD MUST honesty rule, path-scoped commit/never-push, and conditional runner/standalone `aw ipd finalize` ownership | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step T

- Checked: Front matter, `- Scope-Paths:`, `E-01`..`E-03`, and contracts across `src/pubrun/{auto,full,noauto,nopatch,noconsole,minimal}.py`, `tests/test_import_modes.py`, `tests/test_report_subpackage_integrity.py`, prerequisite `52dl55`, and orchestrator `vtkkn1`.

1. Yes — extends public module exports of all six `pubrun.<mode>` submodules and parent-package `pubrun` rebinding relied on by callers, `tests/test_import_modes.py`, `tests/test_report_subpackage_integrity.py`, and downstream plan `4gpguy`.
2. No — import-mode re-exports and tests only (no private-data guarding, commit, worktree, or sandbox code).
3. No — small, single-concern plan (3 E-items across 7 cohesive files: 6 nearly identical mode modules + 1 test file).
4. Yes — `- Scope-Paths:` explicitly lists all 7 modified files.
5. Yes — mistakes in import-mode submodules can shadow `pubrun.report` CallableModule subpackage or trigger unintended side effects on import.

AW-TIER: standard

### Step R1

- Checked: Verified every cited file, symbol, and artifact against `src/pubrun/__init__.py`, `src/pubrun/_bootstrap.py`, `src/pubrun/auto.py`, `src/pubrun/full.py`, `src/pubrun/noauto.py`, `src/pubrun/nopatch.py`, `src/pubrun/noconsole.py`, `src/pubrun/minimal.py`, `tests/test_import_modes.py`, `tests/test_report_subpackage_integrity.py`, backlog `x6alw4`, orchestrator `vtkkn1`, and reviewed prerequisite `52dl55`. Confirmed `TestModeAliasApiParity.test_mode_alias_exposes_full_api` currently checks only `hasattr(pubrun_alias, n)` and does not test `_pkg.<name>` parent-package rebinding (PR-001).

### Step R2

- Checked: Verified 1:1 `E-*`/`V-*` bijection (`E-01`..`E-03` to `V-01`..`V-03`), 7-file `- Scope-Paths:`, `- Item-Dependencies: executed:52dl55` matching orchestrator `vtkkn1`, concrete evidence demands, runtime-demonstration reachability (diffs and `pytest` runs, reachable by construction), deferred carrier compliance, and `## Approval and execution gate`. Caught and fixed: `V-01`/`V-02` missing diffs, omitting `tests/test_report_subpackage_integrity.py` while claiming to verify `pubrun.report`, and ordering dependency on `E-03` (PR-002); missing required execution-contract elements and unconditional finalize instruction in the gate (PR-003); and uncarried deferred item (PR-004).

### Step R3

- Checked: Verified no secrets, auth paths, or global I/O monkeypatching (`builtins.open` remains unpatched, `pubrun.capture.file_io` remains lazily imported, and subprocess tests isolate `cwd=str(tmp_path)` and env vars).

### Step R4

- Checked: Evaluated engineering rubric sections A (correctness and data integrity), C (architecture and operability), D (anti-regression and domain invariants: `pubrun.report` CallableModule integrity, lazy `pubrun.capture.file_io`, unpatched `builtins.open`), E (testing and verification: added parent-package `_pkg` parity check, `cwd=str(tmp_path)` isolation, and lazy-import check in `E-03`), F (KISS, fallback principles), right-sizing (3 small E-items across 7 Scope-Paths), and `## Spec / documentation sync` (deferred honestly to `4gpguy`).

### Step S5

- Checked: Verified zero open questions (`vtkkn1` `OQ-01` already recorded human approval of `register_file`, `register_input`, and `register_output` on 2026-11-21) and added `- Carrier-Declined:` to the sole deferred item (`check.ipd-uncarried-obligation`). All 4 review findings had Low remediation risk and were fixed in place. Zero blocking or uncarried questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | UNDER-SCOPE | R1/R4.E | `tests/test_import_modes.py::TestModeAliasApiParity.test_mode_alias_exposes_full_api:821-843`, `.aw/records/plans/pending/20261121-file-prov-03-98j0a3-import-mode-api-parity-for-file-registration.ipd.md:58,65,72,92-93`, `.aw/records/plans/pending/20261121-file-prov-02-52dl55-explicit-external-file-registration-api-and-lifecycle-semant.ipd.md:80` | `TestModeAliasApiParity.test_mode_alias_exposes_full_api` checks only `hasattr(pubrun_alias, n)` and never verifies parent-package `_pkg.register_*` rebinding (`from pubrun import register_input`), so missing `_pkg` assignments in any mode module would pass unnoticed. In addition, the new `nopatch`/`minimal` subprocess tests did not specify `cwd=str(tmp_path)`, cleared `PUBRUN_IMPORT_MODE`/`PUBRUN_AUTO_START` env vars, or verifying `'pubrun.capture.file_io' not in sys.modules` after import (`52dl55` cold-import invariant). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Extended `E-03`, Proposed changes #3, and `V-03` to assert parent-package `import pubrun as base` parity across all six modes, isolate new subprocess tests with `cwd=str(tmp_path)` and cleared env vars, and verify lazy `pubrun.capture.file_io` isolation (recommendation strength: very strong). |
| PR-002 | MEDIUM | IN-SCOPE | R2/R4.E | `.aw/records/plans/pending/20261121-file-prov-03-98j0a3-import-mode-api-parity-for-file-registration.ipd.md:120-128`, `tests/test_report_subpackage_integrity.py:33-97` | `V-01` and `V-02` omitted diffs of the modified mode modules, claimed to verify `pubrun.report` integrity without invoking `tests/test_report_subpackage_integrity.py`, and did not note that running `test_import_modes.py` parity checks requires `E-03`'s `_PUBLIC` update. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Required diffs of the three respective mode modules plus `pytest tests/test_import_modes.py tests/test_report_subpackage_integrity.py -k ... -v` (after `E-03` updates `_PUBLIC`) in `V-01` and `V-02`, and diff + full suite output in `V-03` (recommendation strength: very strong). |
| PR-003 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261121-file-prov-03-98j0a3-import-mode-api-parity-for-file-registration.ipd.md:140`, `.aw/system/workflows/plan-review/steps/r2-executability.md:57-60`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46` | The execution gate was a single sentence missing prerequisite `52dl55` gating, compliant `--scope-reason`/`--scope-ack` scope declaration, `never git add -A/-a` / `never push`, and giving an unconditional lifecycle-transition instruction rather than conditional runner-lane vs standalone `aw ipd finalize` ownership. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced gate prose with a complete 5-item execution contract satisfying every requirement in `steps/r2-executability.md` and `steps/s7-finalize.md` (recommendation strength: very strong). |
| PR-004 | MEDIUM | IN-SCOPE | Check P/S5/R2 | `.aw/records/plans/pending/20261121-file-prov-03-98j0a3-import-mode-api-parity-for-file-registration.ipd.md:28,97,118` | Deferred refactor lacked a `- Carrier-Declined:` line (`check.ipd-uncarried-obligation`), line 118 carried two em dashes (`IPD-C802`), and references used informal citations and bare artifact IDs. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `- Carrier-Declined:` to the deferred item, replaced line 118 em dashes with parentheses, split long sentences, standardized `path::Symbol` citations, and labeled referenced IDs (`x6alw4`, `52dl55`, `4gpguy`, `vtkkn1`) (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | How to close the deferred helper-refactor item (`check.ipd-uncarried-obligation`) | Keep the six explicit per-mode re-export files untouched structurally and mark the deferred refactor `- Carrier-Declined:` as an intentional scope boundary | Refactor all six mode modules into a shared dynamic re-export helper during `x6alw4` (unnecessary bootstrap churn for 3 symbols) | `src/pubrun/{auto,full,noauto,nopatch,noconsole,minimal}.py`, `tests/test_report_subpackage_integrity.py`, `.aw/records/plans/pending/20261121-file-prov-03-98j0a3-import-mode-api-parity-for-file-registration.ipd.md:97` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, and all sections were swept for internal consistency with zero residual contradictions or new open questions.

AW-REVIEW: DONE
