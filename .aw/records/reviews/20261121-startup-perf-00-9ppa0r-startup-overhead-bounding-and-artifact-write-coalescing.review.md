# Review findings: ipd 9ppa0r

- Subject-Id: 9ppa0r
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, Mermaid flowchart and entity-relationship diagrams, `E-01`..`E-04`, `Child IPDs, sequence, and dependencies`, `Completion criteria`, `Cross-IPD validation`, `Deferred / out of scope`, `Scope check`, `Required tests / validation`, `Open questions`, `V-01`..`V-04`, and `Approval and execution gate` of `.aw/records/plans/pending/20261121-startup-perf-00-9ppa0r-startup-overhead-bounding-and-artifact-write-coalescing.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `Goal` & `Completion criteria` | 70-95 word single-sentence blocks and unexpanded `PEP 562`/`OS` acronyms | Split into short, complete sentences while preserving every `Owner: <id6>` attribution and expanded acronyms on first use | Technical writing requirements 1 and 2 |
| `Child IPDs`, `Completion criteria`, `Cross-IPD validation`, `Required tests / validation` | Stale child test lists and summaries from before child reviews (`fthyv5`, `4il383`, `tkmm5p`, `ckc3vl`) | Synchronized test commands (`test_bench_command.py`, `test_api.py`, `test_config.py`, `TestDoubleStop`, `python3` benchmark flags) and reviewed child guarantees (`SubprocessSpy` isolation, lock order, `"finalize"` in-place `fsync`, hardware timeout states) | Cross-plan consistency (Check R7) and reference accuracy (Check R1) |
| `Deferred / out of scope`, `OQ-01`, `OQ-02` | Deferred items lacked `- Carrier:` / `- Carrier-Declined:` lines (`check.ipd-uncarried-obligation`), lumped runs-index with four unrelated backlog IDs, and `OQ-01`/`OQ-02` attributed `- Owner: maintainer` to author-resolved defaults | Added explicit `- Carrier:` / `- Carrier-Declined:` lines, labeled each backlog ID accurately (`w4hxkh`, `x21s6w`, `x6alw4`, `q3bll1`), standardized `src/pubrun/capture/filesystem.py::get_filesystem`, and changed `OQ-01`/`OQ-02` `- Owner:` to `plan author (binding upon plan approval)` | `steps/s5-questions.md` rule 5 and `check.ipd-uncarried-obligation` |
| `Validation and cross-check` boilerplate | Two em dashes triggering `IPD-C802` advisories | Replaced the two em dashes with parentheses | Zero `IPD-C802` advisories while preserving exact meaning |
| `Approval and execution gate` | Gate item 5 instructed a hand-rolled move to `executed/` and gate item 3 lacked pasted-output requirement | Updated gate item 5 to unconditional `aw ipd finalize` obligation with conditional runner-retirement vs standalone ownership, and required pasted `aw ipd lint --phase post-transition` output in gate item 3 | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step R1

- Checked: Verified every artifact, backlog ID, child plan filename, test suite path, and symbol citation against `.aw/records/backlog/graduated/20261121-pubrun-improve-01-t1xqpw-startup-overhead.backlog.md`, `.aw/records/backlog/graduated/` (`6hp1zu`, `w4hxkh`, `x21s6w`, `x6alw4`, `q3bll1`), and all four reviewed child plans (`fthyv5`, `4il383`, `tkmm5p`, `ckc3vl`). Verified that `q3bll1` is `repro-preflight` (not a runs-index item; no separate runs-index backlog item exists in `.aw/records/backlog/`), and caught stale test command lists and missing reviewed-child guarantees (PR-001, PR-003).

### Step R2

- Checked: Executed `aw ipd lint --phase author --agent` (exit 0), `aw ipd coverage 9ppa0r` (exit 0, ready for review), and verified typed child-tracking rows (`E-01`..`E-04` -> `CONFIRM <id6> REACHED executed`, `IPD-S407` clean), 1:1 `E-*`/`V-*` bijection (`V-01`..`V-04` each demanding executed file path, `- Status: executed`, all `E-*` `performed`, all `V-*` `pass`, and `aw ipd lint --phase post-transition` exit 0), `- Scope-Paths:` self-scope, `- Item-Dependencies: none`, and `## Approval and execution gate`. Caught and fixed hand-rolled lifecycle move instructions and missing pasted-output wording in the gate (PR-002), plus uncarried deferred items (PR-003). Check T skipped per `plan-review.md` step 3 (Order-00 orchestrators are not rated by T, per spec `k3yx72` Section 5.1).

### Step R7

- Checked: Cross-plan consistency across the entire Set `startup-perf` (`9ppa0r`, `fthyv5`, `4il383`, `tkmm5p`, `ckc3vl`) and sibling Set `timing-acc` (`nr63qr`).
  - Child table filenames, Order numbers (`01`..`04`), and dependencies (`none`, `01`, `01`, `01, 02, 03`) match each child plan's `- Order:` and `- Item-Dependencies:` (`none`, `executed:fthyv5`, `executed:fthyv5`, `executed:fthyv5, executed:4il383, executed:tkmm5p`) and the Mermaid `flowchart TD` exactly.
  - All four child plans are already `- Status: reviewed` with `- Readiness: go-pending-approval` and zero blocking open questions.
  - Synchronized `Required tests / validation`, `Child IPDs`, `Completion criteria`, and `Cross-IPD validation` with the reviewed child plans so the orchestrator accurately rolls up every test command and deliverable (PR-001).
  - Verified full coverage of every requirement and acceptance criterion in backlog `t1xqpw` across `fthyv5`, `4il383`, `tkmm5p`, and `ckc3vl`.

### Step S5

- Checked: Audited `OQ-01`, `OQ-02`, all four deferred items, and all 4 review findings. Every finding had Low remediation risk and was fixed in place. Updated `OQ-01` and `OQ-02` `- Owner:` to `plan author (binding upon plan approval)` per `steps/s5-questions.md` rule 5, added `- Carrier:` / `- Carrier-Declined:` lines to every deferred item, and recorded reversible decisions `D-1` and `D-2` below. Zero blocking or uncarried questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R7/R1 | `.aw/records/plans/pending/20261121-startup-perf-00-9ppa0r-startup-overhead-bounding-and-artifact-write-coalescing.ipd.md:87-97,103,121-124`, `.aw/records/plans/pending/20261121-startup-perf-01-fthyv5-startup-and-finalization-overhead-baseline-measurement.ipd.md:168-170`, `.aw/records/plans/pending/20261121-startup-perf-02-4il383-build-stamped-and-deferred-commit-identity-resolution.ipd.md:187`, `.aw/records/plans/pending/20261121-startup-perf-03-tkmm5p-snapshot-write-coalescing-durability-policy-and-bounded-capt.ipd.md:245-246`, `.aw/records/plans/pending/20261121-startup-perf-04-ckc3vl-post-change-overhead-comparison-documentation-sync-and-whole.ipd.md:151-156` | `9ppa0r`'s `Required tests / validation`, `Child IPDs`, and `Completion criteria` drifted behind the four reviewed child plans: omitted `tests/test_bench_command.py` from `fthyv5`, `tests/test_api.py` from `4il383`, `tests/test_config.py` and `tests/test_quality.py -k TestDoubleStop` from `tkmm5p`, exact benchmark CLI flags from `fthyv5`/`ckc3vl`, and reviewed guarantees (`SubprocessSpy` isolation, deadlock-free lock ordering, `"finalize"` in-place `fsync` upgrade, hardware `"partial"`/`"timeout"` states). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Synchronized `Child IPDs`, `Completion criteria`, `Cross-IPD validation`, and `Required tests / validation` with the four reviewed child plans while keeping every `Owner: <id6>` attribution intact (recommendation strength: very strong). |
| PR-002 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261121-startup-perf-00-9ppa0r-startup-overhead-bounding-and-artifact-write-coalescing.ipd.md:175-178`, `.aw/system/workflows/plan-review/steps/r2-executability.md:59-60`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-36` | Gate item 5 instructed a hand-rolled move to `.aw/records/plans/executed/` instead of unconditional `aw ipd finalize` with conditional runner-retirement vs standalone ownership, and gate item 3 omitted the HARD MUST requirement to paste actual `aw ipd lint --phase post-transition` output and exit codes. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote gate item 5 with conditional runner-retirement vs standalone `aw ipd finalize 9ppa0r` ownership (forbidding raw `git mv`) and strengthened gate item 3 with the pasted-output honesty rule (recommendation strength: very strong). |
| PR-003 | MEDIUM | IN-SCOPE | S5/R2/R1 | `.aw/records/plans/pending/20261121-startup-perf-00-9ppa0r-startup-overhead-bounding-and-artifact-write-coalescing.ipd.md:107-110,132,139`, `.aw/system/workflows/plan-review/steps/s5-questions.md:21,79-91` | All four deferred items lacked `- Carrier:` / `- Carrier-Declined:` lines (`check.ipd-uncarried-obligation`), line 108 conflated runs-index optimization with four unrelated graduated backlog IDs (`w4hxkh`, `x21s6w`, `x6alw4`, `q3bll1`), and `OQ-01`/`OQ-02` claimed `- Owner: maintainer` on author-resolved defaults. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `- Carrier:` (`nr63qr`, `w4hxkh`) and `- Carrier-Declined:` lines to every deferred item, separated runs-index exclusion from labeled backlog IDs, and set `OQ-01`/`OQ-02` `- Owner:` to `plan author (binding upon plan approval)` with `D-1`/`D-2` recorded below (recommendation strength: very strong). |
| PR-004 | LOW | IN-SCOPE | Check P/R1 | `.aw/records/plans/pending/20261121-startup-perf-00-9ppa0r-startup-overhead-bounding-and-artifact-write-coalescing.ipd.md:33,94-97,140,144` | `Goal` and `Completion criteria` used 70-95 word run-on sentences, `PEP 562`/`OS` were unexpanded, `get_filesystem()` lacked a `path::Symbol` citation, and line 144 contained two em dashes (`IPD-C802`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Split run-on sentences while preserving every requirement and `Owner:` attribution, expanded acronyms, cited `src/pubrun/capture/filesystem.py::get_filesystem`, and replaced the two em dashes on line 144 with parentheses (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Proposed configuration key names (`[core].artifact_durability`, `[capture.git].total_timeout`, `[capture.hardware].total_timeout`) and `OQ-01` owner provenance | Keep `"fsync"` default and proposed key names (matching reviewed child `tkmm5p` `OQ-01`/`OQ-02`), attributed to `plan author (binding upon plan approval)` | Leave `- Owner: maintainer` (falsely claims maintainer already answered) or weaken default durability below `"fsync"` (violates `t1xqpw`) | `.aw/records/backlog/graduated/20261121-pubrun-improve-01-t1xqpw-startup-overhead.backlog.md:42`, reviewed child `tkmm5p:255-267`, `.aw/system/workflows/plan-review/steps/s5-questions.md:21` | yes |
| D-2 | Local vs shared filesystem measurement availability (`OQ-02`) and owner provenance | Keep author's resolution recording detected filesystem types via `src/pubrun/capture/filesystem.py::get_filesystem` with `--workdir` override and zero automatic scheduler submission, attributed to `plan author (binding upon plan approval)` | Attempt automatic HPC scheduler submission (prohibited by `t1xqpw` Acceptance Criterion 6) | `.aw/records/backlog/graduated/20261121-pubrun-improve-01-t1xqpw-startup-overhead.backlog.md:52`, reviewed children `fthyv5` and `ckc3vl`, `.aw/system/workflows/plan-review/steps/s5-questions.md:21` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, all sections were swept for cross-plan parity with reviewed children `fthyv5`, `4il383`, `tkmm5p`, and `ckc3vl`, and `aw ipd coverage --no-commit 9ppa0r` and `aw ipd lint --phase review-finalize --agent` were re-verified cleanly after edits.

AW-REVIEW: DONE
