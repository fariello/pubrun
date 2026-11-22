# Review findings: ipd 3tvesf

- Subject-Id: 3tvesf
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, Mermaid diagram, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `Scope check`, `Required tests`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate` of `.aw/records/plans/pending/20261121-timing-acc-04-3tvesf-timing-docs-examples-benchmark-and-whole-set-verification.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `Goal`, `E-01`..`E-05` | Dense multi-clause sentences and unexpanded `OS`/`CPU`/`CI`/`HPC`/`IQR`/`POSIX`/`UTC` acronyms | Split into short, complete sentences and expanded acronyms on first use | Technical writing requirements 1 and 2 |
| `Documentation, benchmark, and verification pipeline` | Linear `flowchart LR` only; no entity/component diagram across 8 target files | Aligned `flowchart LR` with revised steps and added `erDiagram` connecting prerequisites, docs, examples/benchmarks, and verification | Technical writing requirements 12(a), 12(d), and 12(e) |
| `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `OQ-01` | Informal doc references, bare IDs, inaccurate `benchmarks/harness.py` output description, missing `- Carrier:` lines, and `OQ-01` `- Owner: maintainer` | Standardized `path#Heading` and `path::Symbol` citations, labeled referenced IDs, corrected `harness.py` `--redacted-out` behavior, added `- Carrier:`/`- Carrier-Declined:` lines, and changed `OQ-01` `- Owner:` to `plan author (binding upon plan approval)` | `steps/p-proofread.md` Section 11.1, `steps/s5-questions.md` rule 5, and `check.ipd-uncarried-obligation` |
| `Validation and cross-check` boilerplate | Two em dashes triggering `IPD-C802` advisories | Replaced the two em dashes with parentheses | Zero `IPD-C802` advisories while preserving exact meaning |
| `Approval and execution gate` | Prohibited `"if additional files seem required, STOP and report"` scope-fence clause and hand-rolled move to `executed/` | Replaced with `--scope-reason`/`--scope-ack` declaration and conditional runner/standalone `aw ipd finalize` ownership | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step T

- Checked: Front matter, `- Scope-Paths:`, `E-01`..`E-05`, and cross-plan/cross-Set contracts across five reference/spec docs (`docs/manifest.md`, `docs/architecture.md`, `docs/functional_spec.md`, `docs/api.md`, `docs/performance.md`), three example files, `benchmarks/harness.py`, Set `timing-acc`, and sibling Set `startup-perf` (`ckc3vl`).

1. Yes — updates five public reference and specification documents and two runnable examples verified by `examples/verify_all.py` and shared with sibling Set `startup-perf` (`ckc3vl`).
2. No — documentation, examples, and local non-publishing benchmark execution only (does not edit redaction, commit, worktree, or sandbox code, while running `scripts/sanitize_paths.py --check --all` as a hygiene check).
3. No — 5 cohesive E-items across 2 task groups spanning 8 Scope-Paths within a 4-child Set (`timing-acc`).
4. Yes — `- Scope-Paths:` explicitly lists all 8 modified files.
5. Yes — whole-schema validation on `manifest_excerpt.json` would fail on intentionally omitted sections, default `benchmarks/harness.py` writes into `benchmarks/results/`, overwriting `docs/performance.md#Representative results` violates its placeholder policy, and uncoordinated edits to shared docs could clobber sibling `ckc3vl`.

AW-TIER: complex

### Step R1

- Checked: Verified every cited file, heading, example, test, benchmark CLI flag, and sibling plan against `docs/manifest.md`, `docs/architecture.md`, `docs/functional_spec.md`, `docs/api.md`, `docs/performance.md`, `examples/05_execution_phases.py`, `examples/minimal-research-workflow/manifest_excerpt.json`, `examples/minimal-research-workflow/README.md`, `examples/minimal-research-workflow/analysis.py`, `examples/verify_all.py`, `tests/test_example_minimal_research_workflow.py`, `schemas/manifest.schema.json`, `benchmarks/harness.py --help`, backlog `6hp1zu`, orchestrator `nr63qr`, reviewed prerequisites `e1fwy2`, `8co0wy`, and `vrr1fv`, and concurrent plan `ckc3vl`. Surfaced inaccurate `harness.py` output behavior, unsatisfiable full-schema validation on `manifest_excerpt.json`, and missing concrete doc anchors (PR-001, PR-002, PR-003).

### Step R2

- Checked: Verified 1:1 `E-*`/`V-*` bijection (`E-01`..`E-05` to `V-01`..`V-05`), 8-file `- Scope-Paths:`, `- Item-Dependencies: executed:e1fwy2, executed:8co0wy, executed:vrr1fv` matching orchestrator `nr63qr`, concrete diff/output evidence in every `V-*`, runtime-demonstration reachability (all V-items demand diffs, `pytest`, `examples/verify_all.py`, `sanitize_paths.py`, or local benchmark output, reachable by construction), absence of hardcoded mutable record-tree counts, and `## Approval and execution gate`. Fixed unsatisfiable `V-03` schema check (PR-002), vague `E-04` microbenchmark baseline and uncleaned `harness.py` output (PR-001), and prohibited gate wording (PR-004).

### Step R3

- Checked: Verified strict non-publishing and non-scheduler-submission invariants on benchmarks, redaction of hostnames/usernames/paths before recording results in `docs/performance.md` or `V-04`, removal of temporary `/tmp/pubrun-timing-harness.redacted.json`, and enforcement of `python3 scripts/sanitize_paths.py --check --all` in `E-05`/`V-05`.

### Step R4

- Checked: Evaluated engineering rubric sections A (correctness and accuracy), C (architecture and operability), D (anti-regression and domain invariants), E (testing and verification), F (KISS, fallback principles, and UX), right-sizing/conceptual density (5 bounded E-items across 8 Scope-Paths), and `## Spec / documentation sync` (this plan IS the sync plan for Set `timing-acc`). Caught and fixed: `harness.py --redacted-out` temp-file handling and zero-`src/`-edit microbenchmark design (PR-001), `$defs.timing` subschema validation for `manifest_excerpt.json` and `examples/verify_all.py` `[PASS]` compatibility (PR-002), exact doc section anchors (`manifest.md` `[!NOTE]`, `architecture.md`, `functional_spec.md`, `api.md#diff`), cross-Set coordination with `ckc3vl`, and diff-scoped em/en-dash verification (PR-003).

### Step R5

- Checked: Evaluated through all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`:
  1. **QA / QC engineer:** Caught `manifest_excerpt.json` lacking `capture_state` on unrelated sections (breaking whole-schema validation in `V-03`), `benchmarks/harness.py` dropping untracked files into `benchmarks/results/` without `--redacted-out`, and `python` vs `python3` mismatch (PR-001, PR-002).
  2. **Testing and regression expert:** Caught `examples/05_execution_phases.py` needing `not isinstance(..., bool)` check and `[PASS]` stdout preservation for `examples/verify_all.py`, plus diff-scoped Python em/en-dash check instead of ambiguous whole-file claims on docs with pre-existing dashes (PR-002, PR-003).
  3. **UI / UX expert:** Verified plain-language timing explanations in `examples/minimal-research-workflow/README.md` and `docs/api.md`, and confirmed zero introduced em/en dashes across user-facing prose.
  4. **Systems and software architect:** Added symmetric cross-Set coordination note with `ckc3vl` (`startup-perf`) on shared docs (`docs/manifest.md`, `docs/architecture.md`, `docs/functional_spec.md`, `docs/performance.md`) and aligned `docs/api.md` with `vrr1fv`'s diff semantic notes (PR-003).
  5. **Software engineer:** Caught the infeasible "baseline without timing bookkeeping" microbenchmark wording (which would have tempted editing `src/pubrun/` out of scope) and replaced it with a concrete, reproducible, zero-`src/`-edit microbenchmark design (PR-001).
  6. **Sophisticated power user:** Confirmed reproducible local benchmark commands with `N >= 30`, pass 1 cold vs pass 3 warm, median, stdev, and IQR, without polluting `benchmarks/results/`.
  7. **Complete novice:** Confirmed `examples/minimal-research-workflow/README.md` and `examples/05_execution_phases.py` clearly explain tracked workload, capture overheads, overlapping background hardware, and late-import scope.
  8. **Stakeholder:** Confirmed every documentation, example, instrumentation-benchmarking, and whole-Set validation requirement in backlog `6hp1zu` and orchestrator `nr63qr` is met honestly.

### Step R6

- Checked: Evaluated decomposition and conceptual density across `E-01`..`E-05`.
- Conclusion: No split recommended. `3tvesf` is child 04 of 4 in Set `timing-acc` with 5 cohesive E-items across 8 Scope-Paths, right at right-sizing bounds.

### Step R7

- Checked: Cross-plan consistency across Set `timing-acc` (`nr63qr`, `e1fwy2`, `8co0wy`, `vrr1fv`, `3tvesf`) and concurrent Set `startup-perf` (`ckc3vl`, `9ppa0r`).
  - Prerequisites `e1fwy2`, `8co0wy`, and `vrr1fv` are all `Status: reviewed` (`go-pending-approval`); `- Item-Dependencies: executed:e1fwy2, executed:8co0wy, executed:vrr1fv` matches orchestrator `nr63qr`.
  - Documented fields, enums, `phase_end` payloads, subprocess records, legacy/crashed classification, and `diff` notes match `e1fwy2`, `8co0wy`, and `vrr1fv` 1:1.
  - Added symmetric coordination note with `ckc3vl` on shared docs (`docs/manifest.md`, `docs/architecture.md`, `docs/functional_spec.md`, `docs/performance.md`).

### Step S5

- Checked: Audited `OQ-01`, all three deferred items, and all 5 review findings. Every finding had Low remediation risk and was fixed in place. Updated `OQ-01` `- Owner:` to `plan author (binding upon plan approval)` per `steps/s5-questions.md` rule 5, added `- Carrier:` / `- Carrier-Declined:` lines to every deferred item, and recorded reversible decisions `D-1` through `D-3` below. Zero blocking or uncarried questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R1/R4.A/R4.E | `benchmarks/harness.py --help`, `.aw/records/plans/pending/20261121-timing-acc-04-3tvesf-timing-docs-examples-benchmark-and-whole-set-verification.ipd.md:68,73,81,105-107,133,168` | Three defects in benchmark plan: (1) `benchmarks/harness.py` writes a redacted file into `benchmarks/results/` by default unless `--redacted-out <temp_path>` is passed (and line 81 misstated default unredacted output); (2) "baseline without timing bookkeeping" inside `Run`/`phase()`/`SubprocessSpy` was unspecified and could tempt out-of-scope edits to `src/pubrun/`; (3) commands mixed `python` and `python3`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified `python3 benchmarks/harness.py --passes 3 --iterations 30 --redacted-out /tmp/pubrun-timing-harness.redacted.json` with cleanup, defined a concrete zero-`src/`-edit ephemeral microbenchmark (raw `perf_counter()` vs empty loop, active vs inactive `phase()`, and `Run` interval breakdown with `N >= 30`, pass 1 cold vs pass 3 warm, median/stdev/IQR), and standardized on `python3` (`D-2`). Recommendation strength: very strong. |
| PR-002 | HIGH | IN-SCOPE | R1/R2/R4.A | `examples/minimal-research-workflow/manifest_excerpt.json:1-63`, `examples/05_execution_phases.py:13-41`, `examples/verify_all.py:57`, `schemas/manifest.schema.json:377-416` | `V-03` demanded a "schema/JSON parse check on `manifest_excerpt.json`", which fails whole-manifest validation because the intentionally shortened excerpt omits `capture_state` on `run`, `invocation`, `capture`, `status`, `git`, `host`, `python`, and `signals`; `examples/05_execution_phases.py` also needed `not isinstance(..., bool)` check, manifest timing check, and `[PASS]` line preservation for `examples/verify_all.py`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Scoped `V-03` schema validation on `manifest_excerpt.json` to full-file JSON parsing plus `$defs.timing` subschema validation against `schemas/manifest.schema.json`, and sharpened `examples/05_execution_phases.py` assertions (`D-3`). Recommendation strength: very strong. |
| PR-003 | HIGH | IN-SCOPE | R1/R4.F/R7 | `docs/manifest.md:32-45,94-106`, `docs/architecture.md:29-42,104-122`, `docs/functional_spec.md:152-163,242-248,631-635,755-767`, `docs/api.md:68-247,329-341`, `.aw/records/plans/pending/20261121-startup-perf-04-ckc3vl-post-change-overhead-comparison-documentation-sync-and-whole.ipd.md:89,165-170` | Proposed doc edits missed exact stale anchors (`docs/manifest.md` `[!NOTE]`, `docs/architecture.md## 3. Run Lifecycle`, `docs/functional_spec.md### 4.1`/`7.1`/`15.2`/`19.2`, `docs/api.md### pubrun.diff`), omitted `vrr1fv`'s crashed-estimate and `diff` semantic-note docs, lacked a symmetric coordination note for concurrent plan `ckc3vl` on shared docs, and did not scope em/en-dash checks to added/edited diff lines (existing docs already have pre-existing em dashes). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Named exact target headings across all five docs, added crashed-estimate and `diff` note coverage, added symmetric additive-merge coordination with `ckc3vl`, and specified diff-scoped Python em/en-dash checks in `V-01`..`V-04`. Recommendation strength: very strong. |
| PR-004 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261121-timing-acc-04-3tvesf-timing-docs-examples-benchmark-and-whole-set-verification.ipd.md:184,187`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46`, `.aw/system/workflows/plan-review/steps/r2-executability.md:59-60` | Gate item 2 carried the prohibited `"if additional files seem required, STOP and report"` clause for out-of-scope edits, and gate item 5 instructed a hand-rolled lifecycle move to `executed/` instead of conditional runner/standalone `aw ipd finalize`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced gate item 2 with `--scope-reason`/`--scope-ack` declaration and gate item 5 with conditional runner/standalone `aw ipd finalize` ownership (forbidding raw `git mv`). Recommendation strength: very strong. |
| PR-005 | MEDIUM | IN-SCOPE | Check P/S5/R2 | `.aw/records/plans/pending/20261121-timing-acc-04-3tvesf-timing-docs-examples-benchmark-and-whole-set-verification.ipd.md:30,51-73,112-116,145,150` | `OQ-01` attributed `- Owner: maintainer` to an author-resolved default; deferred items lacked `- Carrier:` / `- Carrier-Declined:` lines (`check.ipd-uncarried-obligation`); dense run-on sentences and unexpanded acronyms (`OS`, `CPU`, `CI`, `HPC`, `IQR`, `POSIX`, `UTC`); missing `erDiagram`; two em dashes on line 150 triggered `IPD-C802`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Changed `OQ-01` `- Owner:` to `plan author (binding upon plan approval)` (`D-1`), added `- Carrier:`/`- Carrier-Declined:` lines (`9ppa0r` + two declined gates), split run-on sentences, expanded acronyms, added `erDiagram`, standardized citations, and replaced line 150 em dashes with parentheses. Recommendation strength: strong. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Where to record single-machine instrumentation benchmark numbers (`OQ-01`) and owner provenance | Record in `V-04` and a dedicated environment-scoped subsection of `docs/performance.md` without modifying `docs/performance.md#Representative results`, attributed to `plan author (binding upon plan approval)` | Overwrite `docs/performance.md#Representative results` with single-machine numbers (violates placeholder policy in `docs/performance.md:50-58`) | `docs/performance.md:50-58`, reviewed sibling `ckc3vl`, `.aw/system/workflows/plan-review/steps/s5-questions.md:21` | yes |
| D-2 | How to measure timing-instrumentation cost locally without modifying `src/pubrun/` or polluting `benchmarks/results/` | Run `python3 benchmarks/harness.py --passes 3 --iterations 30 --redacted-out /tmp/pubrun-timing-harness.redacted.json` (cleaned up afterward) plus an ephemeral in-memory Python microbenchmark (raw `perf_counter()` vs empty loop, active vs inactive `phase()`, and `Run` breakdown) | Temporarily edit `src/pubrun/` to strip `perf_counter()` (violates scope fence) or run `harness.py` with default output path (pollutes `benchmarks/results/`) | `benchmarks/harness.py --help`, backlog `6hp1zu`, `3tvesf` `- Scope-Paths:` | yes |
| D-3 | How to schema-validate `examples/minimal-research-workflow/manifest_excerpt.json` in `V-03` | Parse the whole file as valid JSON and validate `excerpt["timing"]` against `$defs.timing` in `schemas/manifest.schema.json` | Validate the whole excerpt against the full schema (fails on intentionally omitted `capture_state` in unrelated sections) | `examples/minimal-research-workflow/manifest_excerpt.json:1-63`, `schemas/manifest.schema.json:377-416`, reviewed `e1fwy2` `D-3` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, and all revised sections (`Goal`, diagrams, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `Scope check`, `Required tests`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate`) were swept for internal consistency with zero residual contradictions or new open questions.

AW-REVIEW: DONE
