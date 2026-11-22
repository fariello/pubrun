# Review findings: ipd frzw20

- Subject-Id: frzw20
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, Mermaid flowchart and entity-relationship diagrams, `E-01`..`E-04`, `Child IPDs, sequence, and dependencies`, `Completion criteria`, `Cross-IPD validation`, `Deferred / out of scope`, `Scope check`, `Required tests / validation`, `Open questions`, `V-01`..`V-04`, and `Approval and execution gate` of `.aw/records/plans/pending/20261121-cap-isolation-00-frzw20-capture-failure-isolation-and-transactional-hook-rollback.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `Goal` & `Completion criteria` | 55-87 word multi-clause sentences and unexpanded `I/O` acronym | Split into short, complete sentences while preserving every requirement and `Owner: <id6>` attribution; expanded `input/output (I/O)` on first use | Technical writing requirements 1 and 2 |
| `Child IPDs`, `Completion criteria`, `Cross-IPD validation`, `Required tests / validation` | Stale child test lists (`p6pon8`, `26euz0`, `zp2yyu`) and pre-review child summaries | Synchronized test commands (`test_edge_cases.py`, `test_pause_resume.py`, `test_cli.py -k "faulthandler or excepthook"`, `test_methods_multi.py`, `test_show_sections.py`, `test_example_minimal_research_workflow.py`, `python3 examples/verify_all.py`, `git status --short`, dash check, local harness flags) and reviewed child guarantees | Cross-plan consistency (Check R7) and reference accuracy (Check R1) |
| `Deferred / out of scope`, `OQ-01`, `OQ-02` | Deferred items lacked `- Carrier:` / `- Carrier-Declined:` lines; orchestrator IDs `6s7k9e` and `osjxbz` were mislabeled as backlog items alongside backlog `x6alw4`; `OQ-01`/`OQ-02` claimed `- Owner: maintainer` on author defaults; bare `(EC-15)` lacked symbol citations | Added explicit `- Carrier:` (`nr63qr`, `9ppa0r`, `6s7k9e`, `osjxbz`, `vtkkn1`) and `- Carrier-Declined:` lines; paired each sibling Set with its backlog and orchestrator IDs; set `OQ-01`/`OQ-02` `- Owner:` to `plan author (binding upon plan approval)`; cited `src/pubrun/capture/signals.py::SignalExitCapture._restore_excepthook`, `tests/test_edge_cases.py::TestExcepthookRestore`, and `tests/test_quality.py::TestConsoleRestoreSafety.test_stop_preserves_third_party_wrapper` | `steps/s5-questions.md` rule 5, `check.ipd-uncarried-obligation`, and `steps/p-proofread.md` Section 11.1 |
| `Validation and cross-check` boilerplate | Two em dashes triggering `IPD-C802` advisories | Replaced the two em dashes with parentheses | Zero `IPD-C802` advisories while preserving exact meaning |
| `Approval and execution gate` | Gate item 5 instructed a hand-rolled move to `.aw/records/plans/executed/` and gate item 3 omitted the pasted-output honesty rule | Updated gate item 5 to unconditional `aw ipd finalize` with conditional runner-retirement vs standalone `aw ipd finalize frzw20` ownership (forbidding raw `git mv`) and strengthened gate item 3 with the HARD MUST pasted-output requirement | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step R1

- Checked: Verified every artifact, backlog ID, child plan filename, test suite path, schema reference, CI workflow matrix, and code symbol citation against `.aw/records/backlog/graduated/20261121-pubrun-improve-01-x21s6w-capture-isolation.backlog.md`, `.aw/records/backlog/graduated/` (`6hp1zu`, `t1xqpw`, `w4hxkh`, `q3bll1`, `x6alw4`), sibling pending orchestrators (`nr63qr`, `9ppa0r`, `6s7k9e`, `osjxbz`, `vtkkn1`), all four reviewed child plans (`p6pon8`, `ed0yds`, `26euz0`, `zp2yyu`), `.github/workflows/ci.yml`, `schemas/manifest.schema.json` (`$defs.error_record`), `src/pubrun/capture/signals.py` (EC-15), `tests/test_edge_cases.py::TestExcepthookRestore`, and `src/pubrun/tracker.py` / `writer.py` / `events.py` / `capture/*.py`. Caught mislabeled sibling IDs (`6s7k9e` and `osjxbz` are orchestrator IPDs, not backlog items; `x6alw4` is a backlog item whose orchestrator is `vtkkn1`), bare `(EC-15)` reference, and drifted child test commands (PR-001, PR-003, PR-004).

### Step R2

- Checked: Executed `aw ipd lint --phase author --agent` (exit 0, 0 errors, 0 warnings, 2 `IPD-C802` advisories cleared by PR-004), `aw ipd coverage frzw20` (exit 0, ready for review), and verified typed child-tracking rows (`E-01`..`E-04` -> `CONFIRM <id6> REACHED executed`, `IPD-S407` clean), 1:1 `E-*`/`V-*` bijection (`V-01`..`V-04` each demanding executed file path, `- Status: executed`, all `E-*` `performed`, all `V-*` `pass`, and `aw ipd lint --phase post-transition` exit 0), `- Scope-Paths:` self-scope, `- Item-Dependencies: none`, and `## Approval and execution gate`. Caught and fixed hand-rolled lifecycle move instructions and missing pasted-output wording in the gate (PR-002), plus uncarried deferred items (PR-003). Check T skipped per `plan-review.md` step 3 (Order-00 orchestrators are not rated by T, per spec `k3yx72` Section 5.1).

### Step R7

- Checked: Cross-plan consistency across the entire Set `cap-isolation` (`frzw20`, `p6pon8`, `ed0yds`, `26euz0`, `zp2yyu`), backlog item `x21s6w`, and sibling Sets (`timing-acc`/`nr63qr`, `startup-perf`/`9ppa0r`, `dep-capture`/`6s7k9e`, `repro-check`/`osjxbz`, `file-prov`/`vtkkn1`).
  - Child table filenames, Order numbers (`01`..`04`), and dependencies (`none`, `01`, `02`, `01, 02, 03`) match each child plan's `- Order:`, `- Item-Dependencies:` (`none`, `executed:p6pon8`, `executed:ed0yds`, `executed:p6pon8, executed:ed0yds, executed:26euz0`), `E-01`..`E-04` dependencies, and the Mermaid `flowchart TD` exactly.
  - All four child plans are already `- Status: reviewed` with `- Readiness: go-pending-approval` and zero blocking open questions.
  - Synchronized `Child IPDs`, `Completion criteria`, `Cross-IPD validation`, and `Required tests / validation` with the four reviewed child plans so the orchestrator accurately rolls up every test command and deliverable (PR-001).
  - Verified full coverage of every implementation guidance point, acceptance criterion, and shared validation/documentation requirement in backlog `x21s6w` across `p6pon8`, `ed0yds`, `26euz0`, and `zp2yyu`.

### Step S5

- Checked: Audited `OQ-01`, `OQ-02`, all deferred items, and all 4 review findings. Every finding had Low remediation risk and was fixed in place. Updated `OQ-01` and `OQ-02` `- Owner:` to `plan author (binding upon plan approval)` per `steps/s5-questions.md` rule 5, added explicit `- Carrier:` / `- Carrier-Declined:` lines to every deferred item, and recorded reversible decisions `D-1` and `D-2` below. Zero blocking or uncarried questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R7/R1 | `.aw/records/plans/pending/20261121-cap-isolation-00-frzw20-capture-failure-isolation-and-transactional-hook-rollback.ipd.md:88-99,105,124-127`, `.aw/records/plans/pending/20261121-cap-isolation-01-p6pon8-safe-diagnostic-redaction-and-hook-ownership-rollback-across.ipd.md:94,258-259`, `.aw/records/plans/pending/20261121-cap-isolation-02-ed0yds-tracker-per-engine-failure-isolation-narrow-ghost-mode-and-i.ipd.md:87,242`, `.aw/records/plans/pending/20261121-cap-isolation-03-26euz0-partial-manifest-diagnostics-inspect-findings-and-methods-ho.ipd.md:88,163`, `.aw/records/plans/pending/20261121-cap-isolation-04-zp2yyu-isolation-overhead-measurement-documentation-reconciliation.ipd.md:88,156-162` | `frzw20`'s `Required tests / validation`, `Child IPDs`, `Completion criteria`, and `Cross-IPD validation` drifted behind the four reviewed child plans: omitted `tests/test_edge_cases.py`, `tests/test_pause_resume.py`, and `pytest tests/test_cli.py -k "faulthandler or excepthook" -v` from `p6pon8`; omitted `tests/test_methods_multi.py`, `tests/test_show_sections.py`, and `tests/test_example_minimal_research_workflow.py` from `26euz0`; used `python` instead of `python3` for `examples/verify_all.py` and omitted `git status --short`, the diff-scoped dash check, and exact `benchmarks/harness.py` flags from `zp2yyu`; and omitted reviewed guarantees (`faulthandler.is_enabled()`, generation-tagged `Popen`, closure-captured `prev_hook`, `MAX_CAPTURE_ERRORS = 50`, `_errors_lock`, self-caught failed returns, `NO_COLOR`, `manifests[1:]` disclosure, `0b8i7x` compatibility, and `## Representative results` preservation). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Synchronized `Child IPDs`, `Completion criteria`, `Cross-IPD validation`, and `Required tests / validation` with the four reviewed child plans while keeping every `Owner: <id6>` attribution intact (recommendation strength: very strong). |
| PR-002 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261121-cap-isolation-00-frzw20-capture-failure-isolation-and-transactional-hook-rollback.ipd.md:176-181`, `.aw/system/workflows/plan-review/steps/r2-executability.md:58-60`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-36` | Gate item 5 instructed a hand-rolled move to `.aw/records/plans/executed/` instead of unconditional `aw ipd finalize` with conditional runner-retirement vs standalone ownership, and gate item 3 omitted the HARD MUST requirement to paste actual `aw ipd lint --phase post-transition` output and exit codes into each `V-*` `Observed evidence:` field. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote gate item 5 with conditional runner-retirement vs standalone `aw ipd finalize frzw20` ownership (forbidding raw `git mv`) and strengthened gate item 3 with the HARD MUST pasted-output honesty rule (recommendation strength: very strong). |
| PR-003 | MEDIUM | IN-SCOPE | S5/R1/R2 | `.aw/records/plans/pending/20261121-cap-isolation-00-frzw20-capture-failure-isolation-and-transactional-hook-rollback.ipd.md:107-113,135,142`, `.aw/system/workflows/plan-review/steps/s5-questions.md:21,79-91` | All five deferred items lacked `- Carrier:` / `- Carrier-Declined:` lines (`check.ipd-uncarried-obligation`), line 111 mislabeled orchestrator IPDs `6s7k9e` (backlog `w4hxkh`) and `osjxbz` (backlog `q3bll1`) as "unrelated backlog items" alongside backlog `x6alw4` (orchestrator `vtkkn1`), and `OQ-01`/`OQ-02` claimed `- Owner: maintainer (confirmed upon plan approval)` on author-resolved defaults. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `- Carrier:` (`nr63qr`, `9ppa0r`, `6s7k9e`, `osjxbz`, `vtkkn1`) and `- Carrier-Declined:` lines to every deferred item, paired each sibling Set accurately with its backlog and orchestrator IDs, and set `OQ-01`/`OQ-02` `- Owner:` to `plan author (binding upon plan approval)` with `D-1`/`D-2` recorded below (recommendation strength: very strong). |
| PR-004 | LOW | IN-SCOPE | Check P/R1 | `.aw/records/plans/pending/20261121-cap-isolation-00-frzw20-capture-failure-isolation-and-transactional-hook-rollback.ipd.md:34,89,95-99,143,147` | `Goal` and `Completion criteria` used 55-87 word run-on sentences, `I/O` on line 89 was unexpanded, bare `(EC-15)` on line 143 lacked symbol citations, and line 147 contained two em dashes triggering `IPD-C802` advisories. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Split run-on sentences while preserving every requirement and `Owner:` attribution, expanded `input/output (I/O)`, cited `src/pubrun/capture/signals.py::SignalExitCapture._restore_excepthook`, `tests/test_edge_cases.py::TestExcepthookRestore`, and `tests/test_quality.py::TestConsoleRestoreSafety.test_stop_preserves_third_party_wrapper`, and replaced the two em dashes on line 147 with parentheses (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Additive optional `section` and `stage` fields on `$defs.error_record` in `schemas/manifest.schema.json` and `OQ-01` owner provenance | Keep optional additive `section` and `stage` fields alongside existing section `capture_state` and `errors.records` (capped at `MAX_CAPTURE_ERRORS = 50`, matching reviewed child `ed0yds`), attributed to `plan author (binding upon plan approval)` | Leave `- Owner: maintainer` (falsely claims maintainer already answered) or omit `section`/`stage` before review (weakens per-section deduplication in `26euz0`) | `.aw/records/backlog/graduated/20261121-pubrun-improve-01-x21s6w-capture-isolation.backlog.md:22,57`, `schemas/manifest.schema.json:1805-1825`, reviewed children `ed0yds` and `26euz0`, `.aw/system/workflows/plan-review/steps/s5-questions.md:21` | yes |
| D-2 | Post-install third-party hook ownership rule (`OQ-02`) and owner provenance | Keep identity-guarded restore with passive passthrough when a third-party wrapper sits outside `pubrun`'s hook (extending existing `sys.stdout`/`sys.stderr` and `sys.excepthook` EC-15 behavior across all hook engines, matching reviewed child `p6pon8`), attributed to `plan author (binding upon plan approval)` | Blindly restore pre-existing global targets on uninstall (breaks post-install third-party wrappers, violating `x21s6w` Acceptance Criterion 4) | `.aw/records/backlog/graduated/20261121-pubrun-improve-01-x21s6w-capture-isolation.backlog.md:42,51`, `src/pubrun/capture/signals.py:251`, `tests/test_edge_cases.py:172`, reviewed child `p6pon8`, `.aw/system/workflows/plan-review/steps/s5-questions.md:21` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, all sections were swept for cross-plan parity with reviewed children `p6pon8`, `ed0yds`, `26euz0`, and `zp2yyu`, and `aw ipd coverage --no-commit frzw20` and `aw ipd lint --phase review-finalize --agent` were re-verified cleanly after edits.

AW-REVIEW: DONE
