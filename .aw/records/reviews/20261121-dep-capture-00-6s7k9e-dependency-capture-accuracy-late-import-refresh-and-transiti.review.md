# Review findings: ipd 6s7k9e

- Subject-Id: 6s7k9e
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, Mermaid flowchart and entity-relationship diagrams, `E-01`..`E-04`, `Child IPDs, sequence, and dependencies`, `Completion criteria`, `Cross-IPD validation`, `Deferred / out of scope`, `Scope check`, `Required tests / validation`, `Open questions`, `V-01`..`V-04`, and `Approval and execution gate` of `.aw/records/plans/pending/20261121-dep-capture-00-6s7k9e-dependency-capture-accuracy-late-import-refresh-and-transiti.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `Goal` & `Completion criteria` | Cited moved backlog path `.aw/records/backlog/open/...`, used 58-71 word multi-clause sentences, and left `TUI` unexpanded | Updated backlog path to `.aw/records/backlog/graduated/...`, split long sentences while preserving every requirement and `Owner: <id6>` attribution, and expanded `Terminal User Interface (TUI)` | Reference accuracy (Check R1) and technical writing requirements 1 and 2 |
| `Child IPDs`, `Completion criteria`, `Cross-IPD validation`, `Required tests / validation` | Stale child test lists (`uil22c`, `fdqkrz`, `ijipnx`, `iflqsl`) and pre-review child summaries | Synchronized exact test commands (`test_new_features.py`, `test_manifest_schema.py`, full `ijipnx` regression suite, `python3 benchmarks/package_capture_bench.py --small-count 10 --large-count 300 --repetitions 10 --cold-runs 3`, `python3 examples/verify_all.py`, `git status --short`, dash check) and reviewed child guarantees | Cross-plan consistency (Check R7) and reference accuracy (Check R1) |
| `Deferred / out of scope`, `OQ-01`, `OQ-02` | All five deferred items lacked `- Carrier:` / `- Carrier-Declined:` lines (`check.ipd-uncarried-obligation`), `OQ-01`/`OQ-02` claimed `- Owner: maintainer (confirmed upon plan approval)` on author defaults, and `OQ-02` used non-canonical `pubrun.capture.filesystem.get_filesystem()` | Added `- Carrier: osjxbz` and `- Carrier-Declined:` lines to every deferred item, set `OQ-01`/`OQ-02` `- Owner:` to `plan author (binding upon plan approval)`, and cited `src/pubrun/capture/filesystem.py::get_filesystem` | `steps/s5-questions.md` rule 5, `check.ipd-uncarried-obligation`, and `steps/p-proofread.md` Section 11.1 |
| `Validation and cross-check` boilerplate | Two em dashes triggering `IPD-C802` advisories | Replaced the two em dashes with parentheses | Zero `IPD-C802` advisories while preserving exact meaning |
| `Approval and execution gate` | Gate item 5 instructed a hand-rolled move to `.aw/records/plans/executed/` and gate item 3 omitted the pasted-output honesty rule | Updated gate item 5 to unconditional `aw ipd finalize` with conditional runner-retirement vs standalone `aw ipd finalize 6s7k9e` ownership (forbidding raw `git mv`) and strengthened gate item 3 with the HARD MUST pasted-output requirement | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step R1

- Checked: Verified every artifact, backlog path, child plan filename, test suite path, CI workflow matrix, and code symbol citation against `.aw/records/backlog/graduated/20261121-pubrun-improve-01-w4hxkh-dependency-capture.backlog.md`, sibling orchestrator `osjxbz` (backlog `q3bll1`), all four reviewed child plans (`uil22c`, `fdqkrz`, `ijipnx`, `iflqsl`), `.github/workflows/ci.yml`, and `src/pubrun/capture/filesystem.py::get_filesystem`. Caught moved backlog path (`.aw/records/backlog/open/...` -> `.aw/records/backlog/graduated/...`), non-canonical `get_filesystem` citation, and drifted child test commands (PR-001, PR-003).

### Step R2

- Checked: Executed `aw ipd lint --phase author --agent` (exit 0, 0 errors, 0 warnings, 2 `IPD-C802` advisories cleared by PR-004), `aw ipd coverage --no-commit 6s7k9e` (exit 0, ready for review), and verified typed child-tracking rows (`E-01`..`E-04` -> `CONFIRM <id6> REACHED executed`, `IPD-S407` clean), 1:1 `E-*`/`V-*` bijection (`V-01`..`V-04` each demanding executed file path, `- Status: executed`, all `E-*` `performed`, all `V-*` `pass`, and `aw ipd lint --phase post-transition` exit 0), `- Scope-Paths:` self-scope, `- Item-Dependencies: executed:uil22c, executed:fdqkrz, executed:ijipnx, executed:iflqsl`, and `## Approval and execution gate`. Caught and fixed hand-rolled lifecycle move instructions and missing pasted-output wording in the gate (PR-002), plus uncarried deferred items flagged by `check.ipd-uncarried-obligation` (PR-003). Check T skipped per `plan-review.md` step 3 (Order-00 orchestrators are not rated by T, per spec `k3yx72` Section 5.1).

### Step R7

- Checked: Cross-plan consistency across the entire Set `dep-capture` (`6s7k9e`, `uil22c`, `fdqkrz`, `ijipnx`, `iflqsl`), backlog item `w4hxkh`, and sibling Set `repro-check` (`osjxbz`, `0b8i7x`, `tusvtd`).
  - Child table filenames, Order numbers (`01`..`04`), and dependencies (`none`, `01`, `02`, `03`) match each child plan's `- Order:`, `- Item-Dependencies:` (`none`, `executed:uil22c`, `executed:fdqkrz`, `executed:ijipnx`), `E-01`..`E-04` dependencies, and the Mermaid `flowchart TD` exactly.
  - All four child plans are already `- Status: reviewed` with `- Readiness: go-pending-approval` and zero blocking open questions.
  - Synchronized `Child IPDs`, `Completion criteria`, `Cross-IPD validation`, and `Required tests / validation` with the four reviewed child plans so the orchestrator accurately rolls up every test command and deliverable (PR-001).
  - Verified full coverage of every implementation guidance item, acceptance criterion, and shared validation/documentation requirement in backlog `w4hxkh` across `uil22c`, `fdqkrz`, `ijipnx`, and `iflqsl`.

### Step S5

- Checked: Audited `OQ-01`, `OQ-02`, all five deferred items, and all 4 review findings. Every finding had Low remediation risk and was fixed in place. Updated `OQ-01` and `OQ-02` `- Owner:` to `plan author (binding upon plan approval)` per `steps/s5-questions.md` rule 5, added explicit `- Carrier:` / `- Carrier-Declined:` lines to every deferred item (clearing `check.ipd-uncarried-obligation`), and recorded reversible decisions `D-1` and `D-2` below. Zero blocking or uncarried questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R7/R1 | `.aw/records/plans/pending/20261121-dep-capture-00-6s7k9e-dependency-capture-accuracy-late-import-refresh-and-transiti.ipd.md:34,87-97,103,122-125`, `.aw/records/plans/pending/20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md:204`, `.aw/records/plans/pending/20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md:187`, `.aw/records/plans/pending/20261121-dep-capture-03-ijipnx-startup-to-finalization-package-merge-manifest-schema-and-re.ipd.md:242`, `.aw/records/plans/pending/20261121-dep-capture-04-iflqsl-package-capture-benchmarking-documentation-sync-and-whole-se.ipd.md:169-173` | Line 34 cited the pre-graduation path `.aw/records/backlog/open/...` (moved to `graduated/`), and `Required tests / validation`, `Child IPDs`, `Completion criteria`, and `Cross-IPD validation` drifted behind the four reviewed child plans: omitted `tests/test_new_features.py` and `tests/test_manifest_schema.py` from `uil22c`, omitted `tests/test_manifest_schema.py` from `fdqkrz`, omitted five regression test files from `ijipnx`, used `python` instead of `python3` and omitted exact benchmark flags, `git status --short`, and the dash check from `iflqsl`, and omitted reviewed child guarantees (schema-compatibility boundary until `ijipnx`, `direct_url.json` URL non-leakage, `top-level-installed` root filtering, `include_transitive=False` single-pass merge, `_filter_package_rows`, and `## Representative results` placeholder preservation). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated backlog path to `graduated/` and synchronized `Child IPDs`, `Completion criteria`, `Cross-IPD validation`, and `Required tests / validation` with the four reviewed child plans while preserving every `Owner: <id6>` attribution (recommendation strength: very strong). |
| PR-002 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261121-dep-capture-00-6s7k9e-dependency-capture-accuracy-late-import-refresh-and-transiti.ipd.md:174-179`, `.aw/system/workflows/plan-review/steps/r2-executability.md:58-60`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-36` | Gate item 5 instructed a hand-rolled move to `.aw/records/plans/executed/` instead of unconditional `aw ipd finalize` with conditional runner-retirement vs standalone ownership, and gate item 3 omitted the HARD MUST requirement to paste actual `aw ipd lint --phase post-transition` output and exit codes into each `V-*` `Observed evidence:` field. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote gate item 5 with conditional runner-retirement vs standalone `aw ipd finalize 6s7k9e` ownership (forbidding raw `git mv`) and strengthened gate item 3 with the HARD MUST pasted-output honesty rule (recommendation strength: very strong). |
| PR-003 | MEDIUM | IN-SCOPE | S5/R1/R2 | `.aw/records/plans/pending/20261121-dep-capture-00-6s7k9e-dependency-capture-accuracy-late-import-refresh-and-transiti.ipd.md:105-111,133,140-141`, `.aw/system/workflows/plan-review/steps/s5-questions.md:21,79-91` | All five deferred items lacked `- Carrier:` / `- Carrier-Declined:` lines (flagged by `check.ipd-uncarried-obligation`), `OQ-01` and `OQ-02` claimed `- Owner: maintainer (confirmed upon plan approval)` on author-resolved defaults, and `OQ-02` used non-canonical `pubrun.capture.filesystem.get_filesystem()`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `- Carrier: osjxbz` and `- Carrier-Declined:` lines to every deferred item, standardized `src/pubrun/capture/filesystem.py::get_filesystem`, and set `OQ-01`/`OQ-02` `- Owner:` to `plan author (binding upon plan approval)` with `D-1`/`D-2` recorded below (recommendation strength: very strong). |
| PR-004 | LOW | IN-SCOPE | Check P/R1 | `.aw/records/plans/pending/20261121-dep-capture-00-6s7k9e-dependency-capture-accuracy-late-import-refresh-and-transiti.ipd.md:34,94-97,145` | `Goal` and `Completion criteria` used 58-71 word run-on sentences, `TUI` on line 96 was unexpanded, and line 145 contained two em dashes triggering `IPD-C802` advisories. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Split run-on sentences while preserving every requirement and `Owner:` attribution, expanded `Terminal User Interface (TUI)`, and replaced the two em dashes on line 145 with parentheses (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Additive manifest field names under `packages` (`OQ-01`) and owner provenance | Keep additive optional fields (`snapshot_stage`, `unresolved`, `local_modules`, `coverage_notes`, `import_names`, `observed_at`, and `$defs.unresolved_package_record`, matching reviewed child `ijipnx` and sibling `repro-check` `0b8i7x`), attributed to `plan author (binding upon plan approval)` | Leave `- Owner: maintainer` (falsely claims maintainer already answered) or omit additive metadata fields (leaves late-import stage and unresolved reasons unrepresentable) | `.aw/records/backlog/graduated/20261121-pubrun-improve-01-w4hxkh-dependency-capture.backlog.md:22,44`, reviewed child `ijipnx` (`OQ-01`), sibling plan `0b8i7x`, `.aw/system/workflows/plan-review/steps/s5-questions.md:21` | yes |
| D-2 | Shared-storage benchmark availability during local execution (`OQ-02`) and owner provenance | Record detected local filesystem type via `src/pubrun/capture/filesystem.py::get_filesystem`, document local-storage scope honestly, and provide `--workdir` on `benchmarks/package_capture_bench.py` without automated HPC submission (matching reviewed child `iflqsl`), attributed to `plan author (binding upon plan approval)` | Attempt unattended HPC scheduler submission (prohibited by policy without explicit maintainer authorization) | `.aw/records/backlog/graduated/20261121-pubrun-improve-01-w4hxkh-dependency-capture.backlog.md:28,53`, reviewed child `iflqsl`, `.aw/system/workflows/plan-review/steps/s5-questions.md:21` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, all sections were swept for cross-plan parity with reviewed children `uil22c`, `fdqkrz`, `ijipnx`, and `iflqsl`, and `aw ipd coverage --no-commit 6s7k9e` and `aw ipd lint --phase review-finalize --agent` were re-verified cleanly after edits.

AW-REVIEW: DONE
