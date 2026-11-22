# Review findings: ipd 26euz0

- Subject-Id: 26euz0
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Antigravity / Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text, front matter, both Mermaid diagrams, E-01 through E-05, V-01 through V-05, Project conventions, Findings, Proposed changes, Deferred, Scope check, Required tests, Spec/documentation sync, Open questions, and Approval and execution gate of `.aw/records/plans/pending/20261121-cap-isolation-03-26euz0-partial-manifest-diagnostics-inspect-findings-and-methods-ho.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal, E-01..E-05 | Dense multi-clause Expected outcome sentences and unexpanded `CLI` | Split into short, complete sentences and expanded `command-line interface (CLI)` on first use | Technical writing requirements 1 and 2. |
| Partial-manifest consumption flow diagrams | Omitted `env`/`packages` section extracts, `capture-error` deduplication, and multi-run methods aggregation | Updated Mermaid `flowchart TD` and `erDiagram` to match revised normative text | Technical writing requirements 12(d) and 12(e). |
| Project conventions, Findings, Deferred, Gate | Informal `file.py` (`func`) references, bare IDs, and missing `- Carrier:` lines on deferred rows | Standardized code citations to `path::Symbol`, attached descriptive labels to referenced IDs (`x21s6w`, `p6pon8`, `ed0yds`, `zp2yyu`, `osjxbz`, `vrr1fv`), and added `- Carrier:` lines (`p6pon8`, `ed0yds`, `zp2yyu`, `osjxbz`, `vrr1fv`) | `steps/p-proofread.md` Section 11.1, reference clarity rule, and `check.ipd-uncarried-obligation`. |
| OQ-01 | `- Owner: maintainer (confirmed upon plan approval)` on author-proposed resolved question | Changed to `- Owner: plan author (binding upon plan approval)` with decision `D-1` recorded below | `steps/s5-questions.md` rule 5 (accurate provenance). |
| Validation and cross-check boilerplate | Two em dashes (`—as distinct from ... by construction—`) causing two `IPD-C802` advisories | Replaced the two em dashes with parentheses | Zero `IPD-C802` advisories while preserving exact meaning. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: `.aw/records/plans/pending/20261121-cap-isolation-03-26euz0-partial-manifest-diagnostics-inspect-findings-and-methods-ho.ipd.md` front matter, `- Scope-Paths:`, E-items, and cross-module/cross-plan contracts across `src/pubrun/report/diagnostics.py`, `src/pubrun/report/checks.py`, `src/pubrun/report/methods.py`, Set `cap-isolation`, and sibling Sets `repro-check` (`0b8i7x`) and `file-prov` (`hm32d9`).

1. Yes: changes `pubrun report` / `pubrun show`, `pubrun inspect`, and `pubrun methods` (single and multi-run) output and finding codes relied on by CLI consumers, existing parity/example tests (`TestSingleRunParity`, `test_example_minimal_research_workflow.py`), and sibling Sets `repro-check` and `file-prov`.
2. No: read-only report, inspection, and methods consumers only (no private-data guarding, commit, worktree, or sandbox code).
3. No: 5 focused E-items across 2 task groups spanning 6 cohesive files (3 report modules + 3 test files), within a 4-child Set (`cap-isolation`).
4. Yes: `- Scope-Paths:` explicitly lists all 6 files modified.
5. Yes: changing `generate_report()` output for healthy manifests would break `tests/test_example_minimal_research_workflow.py` and `TestSingleRunParity`, and clobbering `manifest_findings()` delegation would conflict with sibling reviewed plan `0b8i7x`.

AW-TIER: complex

### Step R1

- Checked: Every cited file, symbol, and artifact against the repository: `src/pubrun/report/diagnostics.py` (`print_report`, `bytes_to_gb`, `Colors`, `_has_color`, `SHOW_SECTIONS`), `src/pubrun/report/checks.py` (`manifest_findings`, `_capture_state_status`), `src/pubrun/report/methods.py` (`bytes_to_gb`, `extract_highlighted_packages`, `generate_report`, `generate_report_multi`, `_VARIANCE_FIELDS`), `tests/test_reports.py` (`TestGenerateReportDegradedManifests`, `TestPrintReportUnit`), `tests/test_methods_multi.py` (`TestSingleRunParity`, `TestAggregateGenerator`), `tests/test_checks_commands.py`, `tests/test_edge_cases.py`, `tests/test_show_sections.py`, `tests/test_example_minimal_research_workflow.py`, `.aw/records/backlog/graduated/20261121-pubrun-improve-01-x21s6w-capture-isolation.backlog.md`, orchestrator `frzw20`, sibling plans `ed0yds` and `zp2yyu`, and cross-Set reviewed plan `0b8i7x`. Surfaced concrete unguarded crash sites in `diagnostics.py` and `methods.py` (`_packages_of`, `extract_highlighted_packages`, `section="env"`/`"packages"`, `argv`/`signals_received`/`started_at_utc`, and `generate_report_multi()` ignoring `manifests[1:]`).

### Step R2

- Checked: E/V 1:1 bijection (`E-01`..`E-05` to `V-01`..`V-05`), Scope-Paths completeness, `Item-Dependencies: executed:ed0yds` matching orchestrator `frzw20`, runtime-demonstration reachability of all `V-*` items (all five demand diffs and pytest outputs, reachable by construction), and `## Approval and execution gate` compliance against `steps/r2-executability.md` and `steps/s7-finalize.md`. Caught and fixed prohibited out-of-scope STOP wording and hand-rolled `git mv` lifecycle move (PR-005), and added `tests/test_methods_multi.py`, `tests/test_show_sections.py`, and `tests/test_example_minimal_research_workflow.py` to `E-05`, `Required tests / validation`, and `V-05` (PR-004).

### Step R3

- Checked: Read-only consumer safety, `NO_COLOR` compliance, bounded output caps (preventing terminal spam from up to 50 `errors.records` entries), LaTeX underscore escaping, and CLI-only import isolation (`tests/test_checks_commands.py::test_import_pubrun_does_not_import_checks`). Added explicit output capping, `NO_COLOR` ANSI-free requirement, and LaTeX underscore escaping for disclosure lines (PR-001, PR-002).

### Step R4

- Checked: Engineering rubric A (correctness and data integrity), C (architecture and operability), D (anti-regression and domain invariants), E (testing and verification), F (KISS, principles, and UX), right-sizing/conceptual density (5 bounded E-items across 6 cohesive Scope-Paths), and `## Spec / documentation sync` (deferred honestly to `zp2yyu`). Caught and fixed `methods.py` multi-run gaps and null-field crashes (PR-001), `diagnostics.py` crash sites across section extracts and Basic/Standard/Deep sections + `errors.capture_state` truncation (PR-002), `checks.py` `capture-error` deduplication and `0b8i7x` compatibility (PR-003), and missing multi-run/section/example regression test suites (PR-004).

### Step R5

- Checked: All eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`:
  1. **QA / QC engineer:** Surfaced `_packages_of()` still emitting `"(standard library only)"` on failed packages in multi-run output, `generate_report_multi()` ignoring failures in `manifests[1:]`, `diagnostics.py` `section="env"`/`"packages"` printing `(None captured)` on failed capture, and `extract_highlighted_packages` crashing on `None` names (PR-001, PR-002).
  2. **Testing and regression expert:** Surfaced missing `tests/test_methods_multi.py`, `tests/test_show_sections.py`, and `tests/test_example_minimal_research_workflow.py` in `E-05`/`V-05`, and pinned preservation of `TestGenerateReportDegradedManifests` and `TestSingleRunParity` (PR-001, PR-004).
  3. **UI / UX expert:** Surfaced terminal-spam risk if 50 `errors.records` entries print uncapped in `print_report()` or produce 50 duplicate `WARN` findings in `manifest_findings()`, and ensured `NO_COLOR` emits zero ANSI escapes (PR-002, PR-003).
  4. **Systems and software architect:** Surfaced cross-Set compatibility with `0b8i7x` (`pubrun.report.checks.manifest_findings` delegating to `pubrun.report.reproducibility`) and exact alignment with `ed0yds`'s `errors.capture_state` truncation contract (PR-002, PR-003).
  5. **Software engineer:** Surfaced crash sites in `diagnostics.py` (`inv.argv` non-strings, `signals_received` non-dicts, invalid `started_at_utc`, whitespace-only `python.version`, `subprocesses` non-dicts) and `methods.py` (`bytes_to_gb` non-numeric, LaTeX underscore escaping) (PR-001, PR-002).
  6. **Sophisticated power user:** Confirmed `pubrun show <run> env` and `packages` honestly report capture failure rather than empty results and `pubrun methods --all` surfaces partial capture across aggregated run sets (PR-001, PR-002).
  7. **Complete novice:** Confirmed clear `[WARN ]` headers at `basic` depth and plain-language partial-provenance disclosure prevent misinterpreting missing data as "zero packages" or "no git repo".
  8. **Stakeholder:** Confirmed `x21s6w` consumer honesty goals are met without breaking byte-identical methods output for complete runs.

### Step R6

- Checked: Evaluated decomposition and conceptual density for `E-01` through `E-05`.
- Conclusion: No split recommended. `26euz0` is already child 03 of 4 in Set `cap-isolation`, with 5 small, single-concern E-items across 6 cohesive files (one E-item per consumer module plus two focused test items).

### Step R7

- Checked: Cross-plan consistency across Set `cap-isolation` (`frzw20`, `p6pon8`, `ed0yds`, `26euz0`, `zp2yyu`) and cross-Set compatibility with `repro-check` (`0b8i7x`) and `file-prov` (`hm32d9`).
  - Orchestrator `frzw20` and prerequisite `ed0yds`: `- Item-Dependencies: executed:ed0yds` matches; consumer handling aligns 1:1 with `ed0yds`'s `capture_state.status == "failed"`, `errors.records` (`kind="capture-error"`, `section`, `stage`), and `errors.capture_state` truncation contract.
  - Downstream `zp2yyu`: reconciles docs and runs full-suite validation after `26euz0` executes.
  - Cross-Set `0b8i7x`: added explicit preservation note in `checks.py::manifest_findings` if `0b8i7x` lands first (PR-003).

### Step S5

- Checked: Pre-existing `OQ-01` and all 6 review findings. All 6 findings had Low remediation risk and were fixed in place with zero remaining unresolved or deferred findings and zero blocking human questions. Updated `OQ-01` `- Owner:` to `plan author (binding upon plan approval)` per `steps/s5-questions.md` rule 5 and recorded reversible decisions `D-1` through `D-3` below.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R1 / R4.A (`methods.py` multi-run false `"standard library only"`, ignored `manifests[1:]` failures, `extract_highlighted_packages` crashes, and LaTeX escaping) | `.aw/records/plans/pending/20261121-cap-isolation-03-26euz0-partial-manifest-diagnostics-inspect-findings-and-methods-ho.ipd.md:73,117-123`; `src/pubrun/report/methods.py::extract_highlighted_packages:9-18`; `src/pubrun/report/methods.py::_packages_of:115-117`; `src/pubrun/report/methods.py::generate_report_multi:131-185`; `tests/test_reports.py::TestGenerateReportDegradedManifests:170-235` | Four defects in `methods.py` coverage: (1) `_packages_of()` still returns `"(standard library only)"` when `packages.capture_state.status == "failed"`; (2) `generate_report_multi()` generates its base paragraph only from `manifests[0]`, hiding failed sections in `manifests[1:]`; (3) `extract_highlighted_packages()`, `bytes_to_gb()`, and `_VARIANCE_FIELDS` crash on `None`/non-dict sections, non-numeric RAM, or `None` package names; (4) LaTeX disclosure lines did not specify escaping underscores. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Specified null/type guards across `bytes_to_gb`, `extract_highlighted_packages`, `generate_report`, `generate_report_multi`, and all `_VARIANCE_FIELDS`, updated `_packages_of()` for `"failed"`/`"suppressed"`, required multi-run failure aggregation across all manifests, required LaTeX underscore escaping, and preserved `TestGenerateReportDegradedManifests` defaults (recommendation strength: very strong). |
| PR-002 | high | IN-SCOPE | R1 / R4.A (`diagnostics.py` crash sites in `env`/`packages` extracts and Basic/Standard/Deep views, plus `errors.capture_state` truncation) | `.aw/records/plans/pending/20261121-cap-isolation-03-26euz0-partial-manifest-diagnostics-inspect-findings-and-methods-ho.ipd.md:63,104-108`; `src/pubrun/report/diagnostics.py::print_report:182-227,265-325,371-402,427-471`; `.aw/records/plans/pending/20261121-cap-isolation-02-ed0yds-tracker-per-engine-failure-isolation-narrow-ghost-mode-and-i.ipd.md:207` | `print_report()` has unguarded crash sites on `section="env"`/`"packages"` (which also falsely print `(None captured)` when capture failed), `config.notices`, `signals_received` non-dicts, non-numeric `started_at_utc`/`elapsed_seconds`, non-string `inv.argv`, whitespace-only `python.version`, redacted `host.hostname` dicts, and `subprocesses` non-dicts. It also did not specify an explicit error-line cap or surfacing `ed0yds`'s `errors.capture_state` truncation detail. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Specified `_as_dict`/`_section_status` guards across all sections and `env`/`packages` extracts (showing `(capture failed: <detail>)`), bounded `[WARN ]` display capped at 10 error lines + overflow + `errors.capture_state` truncation detail, and zero ANSI escapes under `NO_COLOR` (recommendation strength: very strong). |
| PR-003 | medium | IN-SCOPE | R4.A / R7 (`checks.py` `capture-error` deduplication and cross-Set `0b8i7x` delegation preservation) | `.aw/records/plans/pending/20261121-cap-isolation-03-26euz0-partial-manifest-diagnostics-inspect-findings-and-methods-ho.ipd.md:110-115`; `.aw/records/plans/pending/20261121-repro-check-01-0b8i7x-shared-reproducibility-evidence-model-and-recorded-gap-analy.ipd.md:128-131` | `manifest_findings()` did not deduplicate repeated `capture-error` records for the same unreported section (for example multiple `"writer"` or `"subprocesses"` errors), did not handle `section=None` or `errors.capture_state` truncation, and did not note preserving delegation to `pubrun.report.reproducibility` if sibling reviewed plan `0b8i7x` lands first. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Specified per-section deduplication (with count suffix and `"general"` fallback for missing section), `errors.capture_state` truncation surfacing, and preserving `0b8i7x` delegation if already present (recommendation strength: strong). |
| PR-004 | medium | UNDER-SCOPE | R2 / R4.E (Missing regression test suites for `methods_multi`, `show_sections`, and minimal-workflow example) | `.aw/records/plans/pending/20261121-cap-isolation-03-26euz0-partial-manifest-diagnostics-inspect-findings-and-methods-ho.ipd.md:85,146,187`; `tests/test_methods_multi.py`; `tests/test_show_sections.py`; `tests/test_example_minimal_research_workflow.py` | E-01 and E-03 modify `print_report()` (including section extracts) and `generate_report()` / `generate_report_multi()`, but `tests/test_methods_multi.py`, `tests/test_show_sections.py`, and `tests/test_example_minimal_research_workflow.py` were omitted from `E-05`, `Required tests / validation`, and `V-05`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Added `tests/test_methods_multi.py`, `tests/test_show_sections.py`, and `tests/test_example_minimal_research_workflow.py` to `E-05`, `Required tests / validation`, and `V-05` (recommendation strength: strong). |
| PR-005 | high | IN-SCOPE | R2 / S7 (Execution contract policy) | `.aw/records/plans/pending/20261121-cap-isolation-03-26euz0-partial-manifest-diagnostics-inspect-findings-and-methods-ho.ipd.md:198,201`; `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46`; `.aw/system/workflows/plan-review/steps/r2-executability.md:59-60` | Gate item 2 carried the prohibited `"if additional files seem required, STOP and report"` clause for out-of-scope edits, and gate item 5 instructed a hand-rolled `git mv` lifecycle move to `executed/` instead of unconditional `aw ipd finalize` obligation with conditional runner-vs-standalone ownership. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Rewrote gate item 2 as a scope declaration with `--scope-reason`/`--scope-ack` justification and gate item 5 with conditional runner-vs-standalone `aw ipd finalize` ownership (recommendation strength: very strong). |
| PR-006 | low | IN-SCOPE | Check P / S5 (Technical writing, OQ-01 owner provenance, deferred carriers, diagram parity, citations, and `IPD-C802` hygiene) | `.aw/records/plans/pending/20261121-cap-isolation-03-26euz0-partial-manifest-diagnostics-inspect-findings-and-methods-ho.ipd.md:36-53,63,73,80,85,90-94,132-134,159,164` | `OQ-01` claimed `- Owner: maintainer` on an author-proposed resolved question; deferred rows lacked `- Carrier:` lines; `CLI` was unexpanded; E-item Expected outcomes were dense multi-clause sentences; code references lacked `path::Symbol`; bare IDs lacked labels; Mermaid diagrams omitted updated scope; and line 164 carried two em dashes (`IPD-C802`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Updated `OQ-01` `- Owner:` to `plan author (binding upon plan approval)` with `D-1`, added `- Carrier:` lines (`p6pon8`, `ed0yds`, `zp2yyu`, `osjxbz`, `vrr1fv`), expanded `CLI`, split dense sentences, synced diagrams, standardized `path::Symbol` citations, labeled referenced IDs, and replaced the two em dashes on line 164 with parentheses (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Preserving byte-identical `methods` output for complete manifests (`OQ-01`) and owner provenance | Activate failed-packages wording and partial-provenance disclosure only when a section has `capture_state.status == "failed"` (or `"suppressed"` for packages) and record `- Owner: plan author (binding upon plan approval)` | Always append provenance completeness notes (breaks `TestSingleRunParity` and `test_example_minimal_research_workflow.py`) | `tests/test_methods_multi.py::TestSingleRunParity`; `tests/test_reports.py::TestGenerateReportDegradedManifests`; `.aw/system/workflows/plan-review/steps/s5-questions.md:21` | yes |
| D-2 | Bounding and deduplicating `errors.records` in `diagnostics.py` and `checks.py` | Cap `[WARN ]` error lines rendered in `print_report()` at 10 entries + overflow summary + `errors.capture_state` truncation detail, and deduplicate `capture_error_<section>` findings per unreported section in `manifest_findings()` | Print all 50 errors uncapped and emit 50 separate `WARN` findings (terminal spam) | `.aw/records/plans/pending/20261121-cap-isolation-02-ed0yds-tracker-per-engine-failure-isolation-narrow-ghost-mode-and-i.ipd.md:149,207`; `.aw/records/backlog/graduated/20261121-pubrun-improve-01-x21s6w-capture-isolation.backlog.md:44` | yes |
| D-3 | Handling partial capture across `manifests[1:]` in `methods.py::generate_report_multi` | Update `_packages_of()` to emit `"(package capture failed)"` / `"(package capture disabled)"` and aggregate failed sections across all manifests in the run set | Check only `manifests[0]` (silently hides capture failures in aggregated runs) | `src/pubrun/report/methods.py::_packages_of:115-117`; `src/pubrun/report/methods.py::generate_report_multi:131-185` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, and all revised sections (`Goal`, both Mermaid diagrams, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `Scope check`, `Required tests`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate`) were swept for internal consistency with zero residual contradictions or new open questions.

AW-REVIEW: DONE
