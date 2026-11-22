# Review findings: ipd zp2yyu

- Subject-Id: zp2yyu
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, `Workflow history`, Mermaid diagrams, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `Scope check`, `Required tests`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate` of `.aw/records/plans/pending/20261121-cap-isolation-04-zp2yyu-isolation-overhead-measurement-documentation-reconciliation.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Workflow history` | Listed `draft` above `to-review` (oldest-first) | Reordered newest-first and prepended `/plan-review` entry | `steps/s7-finalize.md` newest-first history contract |
| `Goal`, `Measurement, reconciliation, and whole-Set verification flow` | Dense single-sentence goal, bare prerequisite IDs, flowchart mentioning `"silently expanding scope"`, and no `erDiagram` across 5 reconciled docs | Split into concise sentences, labeled prerequisite IDs, aligned flowchart, and added `erDiagram` | Technical writing requirements 2, 12(a), 12(d), and 12(e) |
| `Project conventions`, `Proposed changes`, `Deferred`, `OQ-01` | Informal doc references, missing carrier lines on all three deferred items, and `OQ-01` `- Owner: maintainer (confirmed upon plan approval)` | Standardized `path#Heading` / `path::Symbol` citations, added `- Carrier: ed0yds` and `- Carrier-Declined:` lines, and changed `OQ-01` owner to `plan author (binding upon plan approval)` | `steps/p-proofread.md` Section 11.1, `check.ipd-uncarried-obligation`, and `steps/s5-questions.md` rule 5 |
| `Validation and cross-check` boilerplate | Two em dashes triggering `IPD-C802` advisories | Replaced both em dashes with parentheses and referenced `U+2014` / `U+2013` code points | Zero `IPD-C802` advisories while preserving exact meaning |
| `Approval and execution gate` | Prohibited `"Do not expand scope; if additional files seem required, STOP and report"` clause and hand-rolled manual move to `executed/` | Replaced with `--scope-reason`/`--scope-ack` scope declaration, HARD MUST honesty wording, and conditional runner-lane vs standalone `aw ipd finalize` ownership | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step T

- Checked: Front matter, `- Scope-Paths:`, `E-01`..`E-05`, and cross-plan/cross-Set contracts across `docs/architecture.md`, `docs/functional_spec.md`, `docs/manifest.md`, `docs/api.md`, `docs/performance.md`, `benchmarks/harness.py`, Set `cap-isolation` (`frzw20`, `p6pon8`, `ed0yds`, `26euz0`), and concurrent sibling Sets (`ckc3vl`, `3tvesf`, `iflqsl`, `sdg31l`, `4gpguy`).

1. Yes — reconciles five public specification and reference documents and serves as the whole-Set verification gate for release-blocking Set `cap-isolation` (`frzw20`).
2. No — local non-publishing benchmarking, documentation reconciliation, and hygiene verification only (runs `scripts/sanitize_paths.py --check --all` read-only).
3. No — 5 focused E-items across 2 task groups and 5 documentation Scope-Paths, child 04 of 4 in Set `cap-isolation`.
4. Yes — `- Scope-Paths:` explicitly lists all 5 modified documentation files.
5. Yes — invalid `--iters` flag breaks `benchmarks/harness.py` immediately, omitting `--redacted-out` drops untracked files into `benchmarks/results/`, overwriting `docs/performance.md#Representative results` violates its multi-machine placeholder policy, and uncoordinated edits could clobber sibling Sets on the same five docs.

AW-TIER: complex

### Step R1

- Checked: Verified every cited file, heading, CLI flag, and sibling plan against `benchmarks/harness.py --help`, `src/pubrun/capture/filesystem.py`, `docs/architecture.md`, `docs/functional_spec.md`, `docs/manifest.md`, `docs/api.md`, `docs/performance.md`, `examples/verify_all.py`, `scripts/sanitize_paths.py --help`, `.github/workflows/ci.yml`, backlog `x21s6w`, orchestrator `frzw20`, and reviewed prerequisites `p6pon8`, `ed0yds`, and `26euz0`. Caught non-existent `benchmarks/harness.py --iters` flag and missing `--redacted-out` temp-file cleanup, missing `get_filesystem({}, ...)` two-arg signature, missing post-review `p6pon8`/`ed0yds`/`26euz0` details (`MAX_CAPTURE_ERRORS = 50`, self-caught failed returns, consumer honesty, `faulthandler.is_enabled()`), and `docs/performance.md#Representative results` placeholder policy (PR-001, PR-002).

### Step R2

- Checked: Verified 1:1 `E-*`/`V-*` bijection (`E-01`..`E-05` to `V-01`..`V-05`), 5-file `- Scope-Paths:`, `- Item-Dependencies: executed:p6pon8, executed:ed0yds, executed:26euz0` matching orchestrator `frzw20`, concrete per-item validation evidence, runtime-demonstration reachability (all `V-*` demand local benchmark output, `git diff`, Python checks, `pytest`, `examples/verify_all.py`, or `sanitize_paths.py`, reachable by construction), carrier obligations on deferred items, and `## Approval and execution gate`. Fixed prohibited `"STOP and report"` scope-fence wording and hand-rolled lifecycle move (PR-003), mixed `python`/`python3` commands and missing `git status --short` / Set test-file checks in `V-05` (PR-004), and uncarried deferred items (PR-005).

### Step R3

- Checked: Verified strict non-publishing and non-HPC-submission invariants on benchmarks, temporary worktree and `--redacted-out` JSON cleanup so zero unredacted or stray files enter `benchmarks/results/` or the repo, zero raw hostnames or local paths in `docs/performance.md` or `V-01`, and `python3 scripts/sanitize_paths.py --check --all` plus `git status --short` enforcement in `E-05`/`V-05` (PR-001, PR-004).

### Step R4

- Checked: Evaluated engineering rubric sections A (benchmark CLI accuracy and documentation parity with reviewed `p6pon8`/`ed0yds`/`26euz0`), C (cross-Set additive coexistence across all five shared docs), D (anti-regression across full `pytest tests/ -v`, `examples/verify_all.py`, and `Representative results` placeholder), E (concrete diff-scoped Python `U+2014`/`U+2013` checks, `python3` standardization, temp cleanup verification, and Set test-file confirmation), F (KISS, clear user docs), right-sizing (5 focused E-items across 5 doc Scope-Paths), and `## Spec / documentation sync` (this plan IS the documentation/spec reconciliation plan for Set `cap-isolation`).

### Step R5

- Checked: Evaluated through all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`:
  1. **QA / QC engineer:** Caught non-existent `benchmarks/harness.py --iters` flag, missing `--redacted-out` temp-file cleanup, and missing `git worktree remove --force` cleanup (PR-001).
  2. **Testing and regression expert:** Added diff-scoped Python `U+2014`/`U+2013` checks in `V-02`..`V-04`, `python3` consistency, `git status --short` cleanliness, and explicit confirmation of `test_hook_ownership_rollback.py`, `test_capture_isolation.py`, `test_reports.py`, `test_checks_commands.py`, `test_edge_cases.py`, and `test_manifest_schema.py` in `V-05` (PR-002, PR-004).
  3. **UI / UX expert:** Verified `docs/performance.md#Representative results` placeholder integrity and clear single-machine labeling with zero em/en dashes (PR-002).
  4. **Systems and software architect:** Synced `MAX_CAPTURE_ERRORS = 50`, self-caught failed returns, `faulthandler.is_enabled()`, passive passthrough, and `26euz0` consumer honesty into `docs/architecture.md`, `docs/functional_spec.md`, `docs/manifest.md`, and `docs/api.md`, and added cross-Set additive coexistence rules (PR-002).
  5. **Software engineer:** Fixed prohibited `"STOP and report"` scope-fence wording and hand-rolled lifecycle move in `## Approval and execution gate` (PR-003).
  6. **Sophisticated power user:** Confirmed reproducible local harness + ephemeral micro-benchmark design with `>= 20` warm iterations plus explicit cold pass, median, IQR, and stdev without polluting `benchmarks/results/` (PR-001).
  7. **Complete novice:** Added `erDiagram`, split dense sentences, and labeled referenced artifact IDs (`p6pon8`, `ed0yds`, `26euz0`, `frzw20`, `x21s6w`) (PR-005).
  8. **Stakeholder:** Confirmed every overhead-measurement, documentation/spec-reconciliation, example, sanitizer, and CI-matrix requirement in backlog `x21s6w` and orchestrator `frzw20` is covered honestly.

### Step R6

- Checked: Evaluated decomposition and conceptual density across `E-01`..`E-05` and 5 Scope-Paths. `zp2yyu` is child 04 of 4 in Set `cap-isolation` with 5 cohesive E-items partitioned cleanly into measurement (`E-01`), architecture+spec docs (`E-02`), manifest+API docs (`E-03`), performance docs (`E-04`), and whole-Set verification (`E-05`). No split recommended.

### Step R7

- Checked: Cross-plan consistency across Set `cap-isolation` (`frzw20`, `p6pon8`, `ed0yds`, `26euz0`, `zp2yyu`) and concurrent sibling Sets (`ckc3vl`, `3tvesf`, `iflqsl`, `sdg31l`, `4gpguy`). Confirmed `- Item-Dependencies: executed:p6pon8, executed:ed0yds, executed:26euz0` matches `frzw20`; reconciled all reviewed `p6pon8`, `ed0yds`, and `26euz0` details into `zp2yyu`'s doc sync; and required additive doc coexistence across shared files.

### Step S5

- Checked: Audited `OQ-01` (changed `- Owner: maintainer (confirmed upon plan approval)` to `- Owner: plan author (binding upon plan approval)` per `steps/s5-questions.md` rule 5), all three deferred items (added `- Carrier: ed0yds` and `- Carrier-Declined:` lines), and all 5 review findings. All 5 findings had Low remediation risk and were fixed in place. Recorded reversible decisions `D-1`..`D-3` below. Zero blocking or uncarried questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R1/R2/R4.A | `.aw/records/plans/pending/20261121-cap-isolation-04-zp2yyu-isolation-overhead-measurement-documentation-reconciliation.ipd.md:52-55,94-100`, `benchmarks/harness.py --help`, `src/pubrun/capture/filesystem.py:207` | Proposed changes #1 invoked `benchmarks/harness.py --passes 2 --iters 20` on `"startup and hotpath groups"`: `--iters` does not exist (`--iterations` is the real flag), there is no group filter flag, and omitting `--redacted-out <temp_path>` drops an untracked JSON into `benchmarks/results/`. It also omitted temporary worktree/file cleanup commands and the two-argument `get_filesystem({}, {"workdir": ...})` signature. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected command to `python3 benchmarks/harness.py --passes 2 --iterations 20 --redacted-out /tmp/pubrun-cap-isolation-harness.redacted.json` with explicit temp-file and `git worktree remove --force` cleanup, specified `get_filesystem({}, {"workdir": ...})`, and required verifying cleanup in `V-01` (`D-1`, recommendation strength: very strong). |
| PR-002 | HIGH | UNDER-SCOPE | R1/R4.A/R7 | `.aw/records/plans/pending/20261121-cap-isolation-04-zp2yyu-isolation-overhead-measurement-documentation-reconciliation.ipd.md:57-70,102-108`, `.aw/records/plans/pending/20261121-cap-isolation-02-ed0yds-tracker-per-engine-failure-isolation-narrow-ghost-mode-and-i.ipd.md:149,207-208`, `.aw/records/plans/pending/20261121-cap-isolation-03-26euz0-partial-manifest-diagnostics-inspect-findings-and-methods-ho.ipd.md:109-133`, `docs/performance.md:50-73` | Doc sync omitted post-review `p6pon8`/`ed0yds`/`26euz0` details (`MAX_CAPTURE_ERRORS = 50` truncation, self-caught failed returns setting `capture.capture_state.status = "partial"`, `faulthandler.is_enabled()` preservation, passive passthrough, and `26euz0` consumer honesty), did not guard `docs/performance.md## Representative results` placeholder policy or cross-Set additive doc coexistence (`ckc3vl`, `3tvesf`, `iflqsl`, `sdg31l`, `4gpguy`), and lacked diff-scoped Python `U+2014`/`U+2013` checks in `V-02`..`V-04`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Reconciled all post-review `p6pon8`/`ed0yds`/`26euz0` contracts into `E-02`/`E-03`/Proposed changes #2, guarded `docs/performance.md## Representative results` as untouched placeholder, added cross-Set additive coexistence rules, and required diff-scoped Python `U+2014`/`U+2013` checks in `V-02`..`V-04` (`D-2`, recommendation strength: very strong). |
| PR-003 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261121-cap-isolation-04-zp2yyu-isolation-overhead-measurement-documentation-reconciliation.ipd.md:43,188,191`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46`, `.aw/system/workflows/plan-review/steps/r2-executability.md:57-60` | Gate item 2 carried the prohibited `"Do not expand scope; if additional files seem required, STOP and report"` scope-fence clause, and gate item 5 instructed a hand-rolled manual move to `.aw/records/plans/executed/` instead of conditional runner-lane vs standalone `aw ipd finalize` ownership. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced `## Approval and execution gate` with a compliant 5-item Execution contract using `--scope-reason`/`--scope-ack`, HARD MUST honesty wording, and conditional runner/standalone `aw ipd finalize` ownership (forbidding raw `git mv`) (recommendation strength: very strong). |
| PR-004 | MEDIUM | IN-SCOPE | R1/R2/R4.E | `.aw/records/plans/pending/20261121-cap-isolation-04-zp2yyu-isolation-overhead-measurement-documentation-reconciliation.ipd.md:76,113,135,177` | Commands mixed `python` and `python3`; `V-05` did not confirm `git status --short` cleanliness or explicitly verify the Set's new test files (`test_hook_ownership_rollback.py`, `test_capture_isolation.py`, `test_tracker.py`, `test_reports.py`, `test_checks_commands.py`, `test_edge_cases.py`, `test_manifest_schema.py`) passed inside `pytest tests/ -v`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Standardized all Python commands on `python3` and added `git status --short` cleanliness and explicit Set test-file confirmation to `E-05`/`V-05` (recommendation strength: strong). |
| PR-005 | MEDIUM | IN-SCOPE | Check P/S5/R2 | `.aw/records/plans/pending/20261121-cap-isolation-04-zp2yyu-isolation-overhead-measurement-documentation-reconciliation.ipd.md:25-26,30,36-44,118-123,149,154` | `Workflow history` was oldest-first; `OQ-01` carried `- Owner: maintainer (confirmed upon plan approval)` for an author resolution; all three deferred items lacked `- Carrier:` / `- Carrier-Declined:` lines (`check.ipd-uncarried-obligation`); line 154 had two em dashes (`IPD-C802`); an `erDiagram` was missing; and prose had dense sentences and unlabeled IDs. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Reordered `Workflow history` newest-first, updated `OQ-01` owner to `plan author (binding upon plan approval)` (`D-3`), added `- Carrier: ed0yds` and `- Carrier-Declined:` lines, replaced line 154 em dashes with parentheses, added `erDiagram`, split dense sentences, and labeled artifact IDs (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | How to invoke `benchmarks/harness.py` locally without failing on `--iters` or polluting `benchmarks/results/` | Run `python3 benchmarks/harness.py --passes 2 --iterations 20 --redacted-out /tmp/pubrun-cap-isolation-harness.redacted.json` alongside the ephemeral micro-benchmark and remove temp files and temporary baseline worktree before finalizing | Keep `--iters 20` (fails with argparse error) or omit `--redacted-out` (pollutes `benchmarks/results/` with untracked JSON) | `benchmarks/harness.py --help`, reviewed siblings `3tvesf` and `ckc3vl` | yes |
| D-2 | Where to record single-machine isolation-overhead results in `docs/performance.md` and how to verify em/en dashes | Keep `## Representative results` untouched as a multi-machine placeholder, add a clearly labeled single-machine subsection additive with sibling Sets, and verify added (`+`) diff lines via Python for zero `U+2014`/`U+2013` | Overwrite `## Representative results` (violates `docs/performance.md:50-58`) or scan whole files (false-fails on untouched pre-existing em dashes) | `docs/performance.md:50-58`, reviewed siblings `ckc3vl`, `3tvesf`, and `iflqsl` | yes |
| D-3 | Ownership label for `OQ-01` and carrier tags for the three deferred items | Set `OQ-01` `- Owner: plan author (binding upon plan approval)` per `steps/s5-questions.md` rule 5 and add `- Carrier: ed0yds` plus two `- Carrier-Declined:` lines (CI matrix and external benchmark publication) | Retain `- Owner: maintainer` (violates `s5-questions.md` rule 5) or leave deferred items uncarried (triggers `check.ipd-uncarried-obligation`) | `.aw/system/workflows/plan-review/steps/s5-questions.md:21,79-91`, `.github/workflows/ci.yml:1-37` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, and all revised sections (`Workflow history`, `Goal`, diagrams, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `Required tests`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate`) were swept for internal consistency (zero remaining `--iters` references, consistent `python3` commands, consistent `MAX_CAPTURE_ERRORS = 50` and `Representative results` policy, zero new open questions).

AW-REVIEW: DONE
