# Review findings: ipd nasg1q

- Subject-Id: nasg1q
- Subject-Type: ipd
- Reviewed-At: 2026-11-24
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, `Workflow history`, `Goal`, `E-01`..`E-05`, `Project conventions`, `Findings`, Mermaid `flowchart TD`, `Proposed changes`, `Deferred / out of scope`, `Scope check`, `Required tests / validation`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate` of `.aw/records/plans/pending/20261123-bjgca2-01-nasg1q-unify-file-provenance-and-capture-error-finding-codes-across.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`. Preserved all H2 headings, existing `E-01`..`E-04`/`V-01`..`V-04` structure (expanding cleanly to `E-01`..`E-05`/`V-01`..`V-05` for `PR-001`), checkbox states, and field names.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Workflow history` | Listed `draft` above `to-review` (oldest-first) | Reordered newest-first and prepended `/plan-review` entry | `steps/s7-finalize.md` newest-first history contract (`PR-004`) |
| `Scope`, `Scope-Paths`, `Goal`, `E-01`..`E-05`, `Findings`, Mermaid diagram, `Proposed changes` | Omitted `src/pubrun/__main__.py::_reconcile_cli_file_provenance`, conflated `packages_timeout` with `packages_capture_failed`, and omitted `_bound_detail`, `_normalize_error_section`, `(+N more)`, `errors_capture_partial`, and `_classify_file_record` details | Added `src/pubrun/__main__.py` (`E-04`/`V-04`, tests moved to `E-05`/`V-05`), enumerated all ported classification/bounding/deduplication/truncation mechanics, and updated the Findings table and Mermaid diagram to match | Reference accuracy (Check R1), engineering soundness (Check R4), and technical writing requirements 5, 6, 12(d), and 12(e) (`PR-001`, `PR-002`) |
| `V-01`..`V-05` and `## Approval and execution gate` | `V-03` used source `grep`, `V-04` lacked `_assess_cli_run` and `import pubrun` isolation checks and required bare "0 failures"; gate omitted the 5-part Execution contract | Strengthened `V-01`..`V-05` to demand behavioral pytest output across all four surfaces plus baseline-aware full-suite reporting, and replaced the gate with a compliant 5-part Execution contract | `steps/r2-executability.md` and `steps/s7-finalize.md` (`PR-003`, `PR-004`) |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step T

- Checked: front matter, `- Scope-Paths:`, E-items, all callers of `_apply_file_provenance_findings` and retired finding codes across `src/pubrun/` and `tests/`, and overlapping pending plans.

1. Yes: changes finding codes emitted in JSON outputs of `assess_manifest_reproducibility()`, `assess_run()`, `manifest_findings()`, `pubrun inspect --json`, and `pubrun rerun --preflight --json`.
2. No: does not touch private-data redaction, commit locks, worktree isolation, or sandbox guards.
3. Yes: spans three production modules (`src/pubrun/report/reproducibility.py`, `src/pubrun/report/checks.py`, `src/pubrun/__main__.py`) and four test suites across four assessment categories.
4. Yes: declares `- Scope-Paths:` (extended in this review to include `src/pubrun/__main__.py`).
5. Yes: deleting `checks._apply_file_provenance_findings` without removing its import in `src/pubrun/__main__.py::_reconcile_cli_file_provenance` breaks `pubrun inspect` and `pubrun rerun --preflight` with `ImportError`, and losing detail bounding or deduplication breaks existing CLI checks.

AW-TIER: complex

### Step R1

- Checked: every cited file, symbol, and test across `src/pubrun/report/reproducibility.py`, `src/pubrun/report/checks.py`, `src/pubrun/__main__.py`, `tests/test_reproducibility_assessment.py`, `tests/test_checks_commands.py`, `tests/test_report_checks_bugs.py`, `tests/test_reproducibility_e2e.py`, and `docs/`.
- Caught critical missing caller `src/pubrun/__main__.py::_reconcile_cli_file_provenance` importing `checks._apply_file_provenance_findings` (`PR-001`).
- Caught five subtle behavioral differences between `reproducibility.py` and `checks.py` (`packages` `timeout` vs `failed`, `_bound_detail` 160-char single-line truncation + `"errors.records"` suggestion, `_normalize_error_section` + `(+N more)` grouping, `errors_capture_partial` truncation wording, and `_classify_file_record` / `_is_caller_digest_mismatch` / `pending` vs `identified_only` breakdown) (`PR-002`).
- Confirmed via `grep` across `docs/` that none of the retired finding codes appear in user-facing documentation.

### Step R2

- Checked: `aw ipd lint --phase author --agent` (exit 0, `clean`, 0 findings) before edits. Verified 1:1 `E-*`/`V-*` bijection after expanding to `E-01`..`E-05` / `V-01`..`V-05`, accurate `- Scope-Paths:` (7 files), concrete behavioral validation demands without code-pinning source reads (`PR-003`), baseline-aware full-suite verification, and compliant 5-part Execution contract (`PR-004`). Re-verified `aw ipd lint --phase review-finalize --agent` cleanly after edits.

### Step R3

- Checked: security and robustness. Manifest fields (`capture_state.detail`, `errors.records[].message`) can contain long or multi-line strings (including redacted strings from fault injection, tested by `tests/test_checks_commands.py::test_real_fault_injected_manifest_propagates_redacted_detail`). Porting `_bound_detail` (160-character single-line cap) into `reproducibility.py` preserves output bounding and prevents terminal/log flooding when the `checks.py` post-pass is removed. Preserving `try/except Exception: return []` in `checks.manifest_findings` keeps `pubrun inspect` crash-safe on malformed manifests.

### Step R4

- Checked: engineering soundness. Removing both reconciliation bridges (`checks.py` and `__main__.py`) makes `reproducibility.py` the true single source of truth for all four assessment surfaces (`assess_manifest_reproducibility`, `assess_run`, `manifest_findings`, `_assess_cli_run`). Splitting `packages` `failed` (`packages_capture_failed`) from `timeout` (`packages_timeout`) aligns `packages` with `git` (`git_capture_failed` vs `git_timeout`) and prevents a timeout from masquerading as a failure. Preserving `import pubrun` import-isolation (checked by `tests/test_report_subpackage_integrity.py`) guarantees zero startup overhead regression.

### Step R5

- Checked: eight personas.
  - QA/QC and testing: added four-surface parity tests and `test_report_subpackage_integrity.py` to `Required tests / validation` and `V-03`/`V-05`.
  - Architect: single canonical emitter in `reproducibility.py`; zero post-pass translation layers in `checks.py` or `__main__.py`.
  - Software engineer: each E-item targets one focused module/concern (5 E-items, 7 Scope-Paths, well within `IPD-Z603`).
  - Power user and stakeholder: `pubrun inspect --json`, `pubrun rerun --preflight --json`, `assess_run()`, and `manifest_findings()` now agree on every finding code.
  - Novice and UI/UX: bounded single-line messages and clear `errors.records` / `pubrun.open()` suggestions are preserved verbatim.

### Step R6

- Checked: decomposition. 5 E-items and 7 Scope-Paths sit squarely within `IPD-Z603` right-sizing guidance; all steps deliver one cohesive contract and splitting into a Set would create artificial cross-plan coupling between removing the bridges and emitting the canonical codes.

### Step R7

- Checked: Set `bjgca2` (single child plan, no orchestrator) and pending reviewed plans sharing files: `gzc672` (`src/pubrun/report/reproducibility.py`, `src/pubrun/__main__.py`, `[tool.mypy]` ratchet) and `ic6z4s` (`src/pubrun/__main__.py`). Their edits touch disjoint functions (`__main__.py` duplicate import / `--create-config` EOF vs `_reconcile_cli_file_provenance`), so no dependency edge is required; added typing hygiene guidance so `nasg1q` stays compatible with `gzc672`'s `mypy` work (`PR-005`).

### Step S5

- Checked: `## Open questions` (`None`) and all 5 findings (`PR-001`..`PR-005`). Every finding had Low remediation risk and was fixed in place with recorded reversible decisions (`D-1`, `D-2`). Zero unresolved or blocking human questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | UNDER-SCOPE | R1/R4 | `src/pubrun/__main__.py::_reconcile_cli_file_provenance` (line 329 `from pubrun.report.checks import _apply_file_provenance_findings`), `src/pubrun/__main__.py::_assess_cli_run` (line 425); plan original `- Scope-Paths:` and `E-03` | E-03 deletes `_apply_file_provenance_findings` from `src/pubrun/report/checks.py`, but `src/pubrun/__main__.py::_reconcile_cli_file_provenance` imports and calls it. Executing E-03 without updating `src/pubrun/__main__.py` would crash `pubrun inspect` and `pubrun rerun --preflight` with `ImportError`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `src/pubrun/__main__.py` to `- Scope-Paths:` and added `E-04`/`V-04` (shifting tests to `E-05`/`V-05`) to remove `_reconcile_cli_file_provenance` and return `assess_run(...)` directly from `_assess_cli_run` (recommendation strength: very strong). |
| PR-002 | HIGH | IN-SCOPE | R1/R4 | `src/pubrun/report/reproducibility.py` (`packages_failed` line 626-639, `_evaluate_inputs_outputs` lines 900-981, `_evaluate_capture_completeness` lines 1170-1225); `src/pubrun/report/checks.py` (`_bound_detail`, `_normalize_error_section`, `_classify_file_record`, `_is_caller_digest_mismatch`, `manifest_findings` lines 682-780); `tests/test_checks_commands.py` lines 208-280 | Plan omitted five behavioral details currently performed by `checks.py` that `reproducibility.py` lacks: splitting `packages` `timeout` (`packages_timeout`) from `failed` (`packages_capture_failed`), 160-character single-line `_bound_detail` + `"errors.records"` suggestion on failed sections, `_normalize_error_section` + `(+N more)` grouping + deduplication against all failed sections, `errors_capture_partial` truncation wording, and `_classify_file_record`/`_is_caller_digest_mismatch`/`pending` breakdown. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified all five concrete behaviors explicitly in `E-01`, `E-02`, `E-03`, `Findings`, Mermaid diagram, and `Proposed changes` (`D-1`, recommendation strength: very strong). |
| PR-003 | HIGH | IN-SCOPE | R2/R4 | Plan original `V-01`..`V-04`; `src/pubrun/report/checks.py` module docstring ("import pubrun does not import pubrun.report.checks") | Original `V-03` used `grep` on source text, `V-04` omitted `_assess_cli_run` parity and `import pubrun` import-isolation verification (`test_report_subpackage_integrity.py`), and required bare "0 failures" on full `pytest` without baseline comparison. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote `V-01`..`V-05` to demand behavioral pytest output across all four surfaces (`assess_manifest_reproducibility`, `assess_run`, `manifest_findings`, `_assess_cli_run`), added `tests/test_report_subpackage_integrity.py`, removed the source `grep` requirement, and added baseline-aware full-suite reporting (recommendation strength: very strong). |
| PR-004 | MEDIUM | IN-SCOPE | R2/S7 | Plan original `## Workflow history` and `## Approval and execution gate`; `.aw/system/workflows/plan-review/steps/s7-finalize.md` | `## Workflow history` was oldest-first and `## Approval and execution gate` omitted the required 5-part Execution contract (open-questions precondition, scope declaration with `--scope-reason`/`--scope-ack`, HARD MUST pasted validation output, path-scoped `aw commit` + never-push, and conditional runner vs standalone `aw ipd finalize`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Reordered `## Workflow history` newest-first and replaced `## Approval and execution gate` with the full compliant 5-part Execution contract naming `aw commit nasg1q` and `aw ipd finalize nasg1q` (recommendation strength: very strong). |
| PR-005 | MEDIUM | UNDER-SCOPE | R7/R4 | Reviewed pending plans `gzc672` (`src/pubrun/report/reproducibility.py`, `src/pubrun/__main__.py`) and `ic6z4s` (`src/pubrun/__main__.py`) | Plan did not note overlapping file edits with reviewed pending plans `gzc672` (which adds a `[tool.mypy]` ratchet) and `ic6z4s`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Documented cross-plan coordination in `## Project conventions discovered (Step 0)` and required clean type annotations on ported helpers in `E-01`/`E-02` (`D-2`, recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | What finding code should `packages` with `capture_state.status == "timeout"` emit once `packages_failed` is replaced by `packages_capture_failed`? | Emit `packages_timeout` for `status == "timeout"` and `packages_capture_failed` for `status == "failed"`. | Map both `failed` and `timeout` to `packages_capture_failed`. | Mirrors `git_timeout` vs `git_capture_failed` in `reproducibility.py` and preserves `checks.py`'s existing distinction where only `status == "failed"` maps to `*_capture_failed`. | yes |
| D-2 | Should `nasg1q` declare `- Item-Dependencies:` on `gzc672` or `ic6z4s`? | Keep `- Item-Dependencies: none` and require clean type annotations on ported helpers. | Serialize `nasg1q` after `gzc672`. | Edits target disjoint functions in `reproducibility.py` and `__main__.py`, isolated worktrees and the merge-and-revalidate gate handle disjoint edits safely, and `nasg1q` has no runtime dependency on `gzc672`. | yes |

### Step S6

- Checked: Round 1 edits expanded `E-01`..`E-04` to `E-01`..`E-05` (`V-01`..`V-05`) and added `src/pubrun/__main__.py` to `- Scope-Paths:`, triggering a Step S6 re-check in this round: verified `Highest E allocated: 05`, 1:1 `E-01`..`E-05` / `V-01`..`V-05` bijection, full token sweep removing stale references to `_apply_file_provenance_findings` callers and 4-item counts, and clean `aw ipd lint --phase review-finalize --agent` (0 errors, 0 warnings). Finalized with `- Status: reviewed`, `- Readiness: go-pending-approval`, `- Review-Depth: complex`.

AW-REVIEW: DONE
