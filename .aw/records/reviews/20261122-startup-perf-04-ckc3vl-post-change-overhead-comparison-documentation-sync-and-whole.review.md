# Review findings: ipd ckc3vl

- Subject-Id: ckc3vl
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Antigravity / Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text, front matter, `Workflow history`, Mermaid diagram, `E-01` through `E-05`, `V-01` through `V-05`, `Project conventions discovered`, `Findings`, `Proposed changes`, `Deferred / out of scope`, `Scope check`, `Required tests / validation`, `Spec / documentation sync`, `Open questions`, and `Approval and execution gate` of `.aw/records/plans/pending/20261121-startup-perf-04-ckc3vl-post-change-overhead-comparison-documentation-sync-and-whole.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Workflow history` | Listed `draft` above `to-review` (oldest-first) | Reordered newest-first and prepended `/plan-review` entry | `steps/s7-finalize.md` newest-first history contract. |
| `Goal`, `E-01`..`E-05`, `Proposed changes`, `Deferred` | Unexpanded acronyms (`OS`, `CPU`, `p95`, `POSIX`, `RPC`, `HPC`, `ms`, `PEP`), dense single-sentence Expected outcomes, and bare artifact IDs (`fthyv5`, `4il383`, `tkmm5p`, `t1xqpw`, `9ppa0r`, `3tvesf`) | Expanded acronyms on first use, split dense sentences, and attached descriptive labels to referenced IDs | Technical writing requirements 1, 2, and reference clarity rule. |
| `### Post-change measurement, documentation, and verification pipeline` Mermaid diagram | Omitted baseline target evaluation, temporary harness-file cleanup, and CI matrix gate | Updated Mermaid `flowchart TD` to align with normative text | Technical writing requirements 12(b), 12(d), and 12(e). |
| `Project conventions`, `Proposed changes`, `Deferred`, `OQ-01` | Informal doc section pointers; deferred items lacked `- Carrier:` / `- Carrier-Declined:` lines; `OQ-01` carried `- Owner: maintainer (confirmed upon plan approval)` | Standardized `path#Heading` citations, added `- Carrier:` / `- Carrier-Declined:` lines, and changed `OQ-01` owner to `plan author (binding upon plan approval)` | `steps/p-proofread.md` Section 11.1, `check.ipd-uncarried-obligation`, and `steps/s5-questions.md` rule 5. |
| `Validation and cross-check` boilerplate and dash references | Two em dashes (`—as distinct from ... by construction—`) causing two `IPD-C802` advisories, plus literal em/en dash glyphs in prose | Replaced the two em dashes with parentheses and referenced `U+2014` / `U+2013` code points | Zero `IPD-C802` advisories while preserving exact meaning. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: `.aw/records/plans/pending/20261121-startup-perf-04-ckc3vl-post-change-overhead-comparison-documentation-sync-and-whole.ipd.md` front matter, `- Scope-Paths:`, 5 E-items across 3 task groups, public specification and documentation files, and whole-Set verification role in Set `startup-perf`.

1. Yes: updates public reference docs and functional specification (`docs/performance.md`, `docs/configuration.md`, `docs/architecture.md`, `docs/functional_spec.md`, `docs/manifest.md`) and serves as the whole-Set verification gate for orchestrator `9ppa0r`.
2. No: does not modify production code guarding private data, commits, worktree isolation, merges to main, or the sandbox (runs local non-publishing benchmarks and `scripts/sanitize_paths.py --check --all` to verify zero leaked local paths).
3. No: 5 focused E-items across 5 documentation Scope-Paths, child 04 of 4 in Set `startup-perf`.
4. Yes: `- Scope-Paths:` explicitly lists all 5 modified documentation files.
5. No: edits documentation only and is easily reversible, though unverified performance claims or stray unredacted benchmark files would harm honesty and privacy if left unchecked.

AW-TIER: complex

### Step R1

- Checked: Every cited file, heading, script, and artifact against the repository: `docs/performance.md` (`## How overhead is measured`, `## Representative results`, `## Notes`), `docs/configuration.md` (`### [core]`, `### [capture.git]`, `### [capture.hardware]`), `docs/architecture.md` (`## 3. Run Lifecycle`, `## 14. Race Safety and Durability`, `## 21. System Components`), `docs/functional_spec.md` (`### 3.2 Lightweight Import Requirement`, `## 19. Writer and Finalization`), `docs/manifest.md` (`## run`, `## config`, `## git`, `## hardware`), `src/pubrun/tracker.py::Run.to_manifest_dict`, `schemas/manifest.schema.json`, `benchmarks/harness.py --help` (confirming `--redacted-out`, `--passes`, `--iterations`), `examples/verify_all.py`, `scripts/sanitize_paths.py --help` (confirming `--check --all`), `.aw/records/backlog/graduated/20261121-pubrun-improve-01-t1xqpw-startup-overhead.backlog.md`, orchestrator `9ppa0r`, and reviewed prerequisites `fthyv5`, `4il383`, and `tkmm5p`. Caught `docs/manifest.md## run` missing `library_version` as well as `library_commit`, `harness.py` omitted from `Required tests` and `V-01`, and updated `4il383`/`tkmm5p` details from their completed reviews (PR-002).

### Step R2

- Checked: E/V 1:1 bijection (`E-01`..`E-05` to `V-01`..`V-05`), Scope-Paths completeness, `- Item-Dependencies: executed:fthyv5, executed:4il383, executed:tkmm5p` matching orchestrator `9ppa0r`, runtime-demonstration reachability of all `V-*` items (all five run local commands/tests or inspect diffs, reachable by construction), and `## Approval and execution gate` compliance against `steps/r2-executability.md` and `steps/s7-finalize.md`. Caught and fixed forbidden `"STOP and report"` scope-fence clause and hand-rolled `git mv` lifecycle transition in gate (PR-001), plus missing `benchmarks/harness.py` in `Required tests`/`V-01` and missing concrete Python em/en-dash diff check in `V-02`..`V-04` (PR-002, PR-003).

### Step R3

- Checked: Non-publishing benchmark invariant (no `gh`, Gist, or HPC scheduler submission), temporary `--redacted-out` file cleanup so zero unredacted or stray files enter `benchmarks/results/`, and `scripts/sanitize_paths.py --check --all` path-hygiene verification in `E-05`/`V-05`. Strengthened `V-01` and `V-05` to confirm temporary harness output removal and clean `git status -s` (PR-002, PR-003).

### Step R4

- Checked: Engineering rubric A (honesty and accuracy of reported measurements), C (operability and additive doc reconciliation), D (anti-regression across full test suite, benchmarks, examples, and sibling `timing-acc` docs), E (concrete validation commands and evidence), F (KISS, principles, and zero em/en dashes in user-facing docs), right-sizing/conceptual density (5 E-items across 5 Scope-Paths), and `## Spec / documentation sync` (this plan IS the documentation sync plan for Set `startup-perf`). Synced all `4il383` and `tkmm5p` reviewed details into `E-03`/`E-04`/Proposed changes #3/#4 and added `benchmarks/harness.py` + `fthyv5` target evaluation to `V-01` (PR-002, PR-003).

### Step R5

- Checked: All eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`:
  1. **QA / QC engineer:** Surfaced `benchmarks/harness.py` missing from `Required tests` and `V-01`, `fthyv5` target pass/fail evaluation missing from `V-01`, and `docs/manifest.md` missing `run.library_version` alongside `run.library_commit` (PR-002, PR-003).
  2. **Testing and regression expert:** Surfaced concrete Python em/en-dash diff checks for `V-02`..`V-04` (preventing false positives from pre-existing dashes in untouched lines) and explicit confirmation of `test_startup_benchmark.py`, `test_commit_identity.py`, and `test_startup_overhead_writes.py` inside `V-05` (PR-003).
  3. **UI / UX expert:** Confirmed `docs/configuration.md` clearly documents invalid `artifact_durability` single-warning fallback, `"finalize"` in-place `fsync` upgrade, and platform `fsync` / `F_FULLFSYNC` / `FlushFileBuffers` / NFS limits so users understand every setting without reading source code (PR-002).
  4. **Systems and software architect:** Confirmed alignment of `docs/architecture.md` and `docs/functional_spec.md` with reviewed `4il383` (lazy PEP 562 `__commit__`, single-read boot config) and `tkmm5p` (atomic visibility vs durability policy, `hardware.depth == "off"` synchronous collection, `_artifacts_written` idempotency, combined `git rev-parse`, and monotonic capture budgets) (PR-002).
  5. **Software engineer:** Surfaced forbidden `"STOP and report"` scope-fence wording and hand-rolled `git mv` gate instructions that violate `aw ipd finalize` and runner lane ownership (PR-001).
  6. **Sophisticated power user:** Confirmed local vs shared storage guidance (`benchmarks/startup_breakdown.py --workdir`), separate default `fsync` vs opt-in durability rows, and explicit cold/warm dispersion statistics (median, mean, p95, stdev, IQR).
  7. **Complete novice:** Surfaced unexpanded acronyms (`OS`, `CPU`, `p95`, `POSIX`, `RPC`, `HPC`, `PEP`) and dense single-sentence Expected outcomes (PR-004).
  8. **Stakeholder:** Confirmed every `t1xqpw` and `9ppa0r` acceptance criterion owned by `ckc3vl` is satisfied: honest apples-to-apples before/after measurements without conflating default durability with opt-in relaxation, zero unauthorized benchmark submission, synchronized specs/docs, full regression suite, and explicit CI matrix gate recording.

### Step R6

- Checked: Evaluated decomposition and conceptual density for `E-01` through `E-05`.
- Conclusion: No split recommended. `ckc3vl` is child 04 of 4 in Set `startup-perf` with 5 focused E-items across 5 documentation Scope-Paths, cleanly partitioned into post-change measurement (`E-01`), performance/config docs (`E-02`, `E-03`), spec/architecture/manifest sync (`E-04`), and whole-Set verification (`E-05`).

### Step R7

- Checked: Cross-plan consistency across Set `startup-perf` (`9ppa0r`, `fthyv5`, `4il383`, `tkmm5p`, `ckc3vl`) and concurrent sibling Set `timing-acc` (`3tvesf`):
  - Orchestrator `9ppa0r`: `- Item-Dependencies: executed:fthyv5, executed:4il383, executed:tkmm5p` matches; all four Cross-IPD verification commands match `9ppa0r` line 103 and line 124.
  - Prerequisite `fthyv5` (reviewed): `benchmarks/startup_breakdown.py` CLI flags (`--passes 3 --iterations 15 --warmup 1 --durability-policies fsync,finalize,atomic,strict`), `startup-auto-default` in `benchmarks/harness.py`, and baseline-derived target comparison match `fthyv5` `V-05` (PR-002, PR-003).
  - Prerequisite `4il383` (reviewed): reconciled exact lazy PEP 562 `__commit__`, `_build_meta.json` version check with legacy `COMMIT` fallback only when absent, `1.0`s bounded ownership-verified checkout Git lookup, and single-read `_config_boot.py` details into `E-04` and Proposed changes #4 (PR-002).
  - Prerequisite `tkmm5p` (reviewed): reconciled exact `[core].artifact_durability` (`"fsync"` default, invalid-value warning fallback, `"finalize"` in-place `fsync` upgrade, `"strict"` POSIX directory sync), `[capture.git].total_timeout = 5` (combined `rev-parse`, `"partial"`/`"timeout"`), `[capture.hardware].total_timeout = 10` (`"partial"`/`"timeout"`), and `hardware.depth == "off"` synchronous collection into `E-03`/`E-04` and Proposed changes #3/#4 (PR-002).
  - Sibling Set `timing-acc` (`3tvesf`): `OQ-01` keeps `ckc3vl`'s edits strictly additive in distinct subsections, preserving any `timing-acc` documentation present on disk.

### Step S5

- Checked: Pre-existing `OQ-01` (changed `- Owner: maintainer (confirmed upon plan approval)` to `- Owner: plan author (binding upon plan approval)` per `steps/s5-questions.md` rule 5) and all 4 review findings. All 4 findings had Low remediation risk and were fixed in place with zero remaining unresolved or deferred findings and zero blocking human questions. Recorded three reversible design decisions (`D-1` through `D-3`) below.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R2 / S7 (Forbidden `"STOP and report"` scope-fence wording and hand-rolled `git mv` lifecycle instruction) | `.aw/records/plans/pending/20261121-startup-perf-04-ckc3vl-post-change-overhead-comparison-documentation-sync-and-whole.ipd.md:190-195`; `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46`; `.aw/system/workflows/plan-review/steps/r2-executability.md:57-60` | Gate item 2 instructed `"Do not expand scope; if additional files seem required, STOP and report"` (violating the 2026-09-01 scope-fence ruling), and gate item 5 instructed a hand-rolled manual move to `executed/` instead of conditional runner-vs-standalone `aw ipd finalize`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Replaced `## Approval and execution gate` with the complete 5-part execution contract using `--scope-reason`/`--scope-ack` and conditional `aw ipd finalize` ownership matching `tkmm5p` and `4il383` (recommendation strength: very strong). |
| PR-002 | high | IN-SCOPE | R1 / R4.A / R7 (Missing `benchmarks/harness.py` in `Required tests`/`V-01`, `docs/manifest.md` `run.library_version` omission, and post-review sync with `4il383` and `tkmm5p`) | `.aw/records/plans/pending/20261121-startup-perf-04-ckc3vl-post-change-overhead-comparison-documentation-sync-and-whole.ipd.md:49-70,94-115,135-141,160-178`; `docs/manifest.md:21-29`; `src/pubrun/tracker.py::Run.to_manifest_dict:655-660`; `.aw/records/plans/pending/20261121-startup-perf-02-4il383-build-stamped-and-deferred-commit-identity-resolution.ipd.md:137-153`; `.aw/records/plans/pending/20261121-startup-perf-03-tkmm5p-snapshot-write-coalescing-durability-policy-and-bounded-capt.ipd.md:131-148,163-166` | `E-01` and Proposed changes #1 required running `benchmarks/harness.py --redacted-out <temp_path>`, but `Required tests` and `V-01` omitted it; `docs/manifest.md## run` lacked `library_version` alongside `library_commit`; and `E-03`/`E-04`/Proposed changes #3/#4 missed post-review details landed in `4il383` (PEP 562, legacy `COMMIT` only when `_build_meta.json` absent, single-read boot config) and `tkmm5p` (invalid-durability warning fallback, `"finalize"` in-place `fsync` upgrade, `hardware.depth == "off"` synchronous collection, combined `rev-parse`, and `git`/`hardware` `"partial"`/`"timeout"` statuses). | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Added `benchmarks/harness.py` with temp-file cleanup to `Required tests` and `V-01`, added `run.library_version` and `git`/`hardware` budget statuses to `docs/manifest.md` sync, and reconciled all reviewed `4il383` and `tkmm5p` details into `E-03`, `E-04`, Proposed changes #3/#4, and `V-03`/`V-04` (recommendation strength: very strong). |
| PR-003 | medium | UNDER-SCOPE | R2 / R4.E (Missing `fthyv5` target evaluation in `V-01`, missing concrete Python em/en-dash diff check in `V-02`..`V-04`, and `V-05` cleanliness/test confirmation) | `.aw/records/plans/pending/20261121-startup-perf-04-ckc3vl-post-change-overhead-comparison-documentation-sync-and-whole.ipd.md:49-76,160-183`; `.aw/records/plans/pending/20261121-startup-perf-01-fthyv5-startup-and-finalization-overhead-baseline-measurement.ipd.md:81,150` | `V-01` did not explicitly demand evaluating each baseline-derived target recorded in `fthyv5` `V-05`; `V-02`..`V-04` did not require a concrete Python check over added diff lines for em/en dashes (important because untouched lines in `docs/` contain pre-existing em dashes); and `V-05` did not confirm `git status -s` cleanliness or call out the three new Set test files inside `pytest tests/ -v`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Strengthened `V-01` with `fthyv5` target evaluation, added concrete Python added-line em/en-dash checks to `V-02`, `V-03`, and `V-04`, and added `git status -s` cleanliness and Set test-file confirmation to `V-05` (recommendation strength: strong). |
| PR-004 | low | IN-SCOPE | Check P / S5 (Technical writing, `Workflow history` ordering, `OQ-01` owner provenance, deferred carriers, diagram parity, citations, and `IPD-C802` hygiene) | `.aw/records/plans/pending/20261121-startup-perf-04-ckc3vl-post-change-overhead-comparison-documentation-sync-and-whole.ipd.md:22-26,35-41,51,68,120-125,149-155,158` | `Workflow history` was oldest-first; deferred items lacked `- Carrier:` / `- Carrier-Declined:` lines; `OQ-01` carried `- Owner: maintainer (...)` for a plan-author resolution; acronyms (`OS`, `CPU`, `p95`, `POSIX`, `RPC`, `HPC`, `PEP`, `ms`) were unexpanded; Expected outcomes were dense run-on sentences; doc references lacked `path#Heading`; Mermaid diagram omitted target evaluation and CI gate; and line 158 carried two em dashes (`IPD-C802`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Reordered `Workflow history` newest-first, set `OQ-01` `- Owner: plan author (binding upon plan approval)`, added `- Carrier:` / `- Carrier-Declined:` lines, expanded acronyms, split dense sentences, aligned the Mermaid diagram, standardized `path#Heading` citations, and removed all literal em/en dashes (`U+2014`/`U+2013` references only) (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | How to verify zero em/en dashes in edited `docs/` files that already have pre-existing em dashes on untouched lines | Require a concrete Python check over added (`+`) lines of `git diff -- <docs>` in `V-02`, `V-03`, and `V-04` | Scan whole files (false-fails on untouched pre-existing lines) or rely on manual eyeball inspection (error-prone) | `docs/performance.md:19,42`; `docs/configuration.md:5,52`; `.aw/records/plans/pending/20261121-repro-check-04-sdg31l-documentation-sync-subpackage-guard-and-whole-set-validation.ipd.md:133,138` | yes |
| D-2 | How to reflect post-review changes from `4il383` and `tkmm5p` in `ckc3vl` without expanding `- Scope-Paths:` | Sync all reviewed behavioral details (`run.library_version`/`library_commit`, single-read boot config, invalid durability warning fallback, `"finalize"` in-place sync, `hardware.depth == "off"` sync collection, combined `rev-parse`, `"partial"`/`"timeout"` capture states) across the existing 5 documentation Scope-Paths | Leave `ckc3vl` with pre-review summaries (would cause documentation drift on execution) or add `CONTRIBUTING.md` to scope (explicitly kept out of scope by `4il383`) | `.aw/records/plans/pending/20261121-startup-perf-02-4il383-build-stamped-and-deferred-commit-identity-resolution.ipd.md:192`; `.aw/records/plans/pending/20261121-startup-perf-03-tkmm5p-snapshot-write-coalescing-durability-policy-and-bounded-capt.ipd.md:131-209`; `docs/manifest.md:21-29` | yes |
| D-3 | Ownership label for `OQ-01` (self-resolved by plan author) | Change `- Owner: maintainer (confirmed upon plan approval)` to `- Owner: plan author (binding upon plan approval)` | Keep `- Owner: maintainer` (violates `steps/s5-questions.md` rule 5 distinguishing human-answered questions from author/reviewer resolutions) | `.aw/system/workflows/plan-review/steps/s5-questions.md:21`; `.aw/records/plans/pending/20261121-startup-perf-03-tkmm5p-snapshot-write-coalescing-durability-policy-and-bounded-capt.ipd.md:259` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, and all revised sections (`Workflow history`, `Goal`, Mermaid diagram, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `Scope check`, `Required tests`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate`) were swept for internal consistency with zero residual contradictions or new open questions.

AW-REVIEW: DONE
