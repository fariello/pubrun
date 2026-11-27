# Review findings: ipd mfeptf

- Subject-Id: mfeptf
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-bej1qz-03-mfeptf-wire-pubrun-bench-cli-to-packaged-runtime-and-single-source.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `errors: 0`, `warnings: 0`, `info: 2` boilerplate `IPD-C802`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` with only the same two non-blocking advisories on line 167 boilerplate. Expanded `HPC`, `CLI`, `PII`, and `JSON` on first use.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `- Scope:`, `- Scope-Paths:`, `E-01`, `## Project conventions discovered`, `## Proposed changes`, `## Deferred / out of scope`, `## Scope check` | Deferred `TestSubmissionVerifier` migration in `tests/test_bench_command.py` to Order 05 (`1r585o`) while deleting `_verify_redacted` in Order 03 (`mfeptf`) | Added `tests/test_bench_command.py` to `- Scope-Paths:` and migrated the 4-test `TestSubmissionVerifier` class in `E-01` to test `_share_check` directly | Prevent `mfeptf` from breaking `pytest tests/` and failing the merge-and-revalidate gate before Order 05 lands (`PR-001`) |
| `E-02`, `E-03` | Omitted `spec.origin != "built-in"` guard, removal of `repo_root = harness.parents[1]` / unused `_tf`, `PUBRUN_UNREDACTED` for non-Slurm schedulers, cross-platform `Path` detection for packaged harness, and explicit no-em/en-dash rule for `bench_parser` | Specified cross-platform `Path` checks, `spec.origin` guard, `repo_root` cleanup, `PUBRUN_UNREDACTED` across all schedulers, updated `_find_bench_harness`/`_run_bench` docstrings, and no em/en dashes in `bench_parser` help text | Eliminate Windows path-separator fragility, stale docstrings, and ignored `--unredacted` on PBS/LSF/SGE (`PR-002`) |
| `E-04`, `## Required tests / validation`, `V-01..V-04` | Commands 2, 3, and 4 omitted `PYTHONPATH=src` (importing wrong checkout in worktrees), Command 4 never tested default non-checkout `./pubrun-bench-results/` or `_share_check` and leaked temp dirs, and no pytest regression command was run | Added `PYTHONPATH=src` to commands 2, 3, and 5; added command 4 covering fast `tests/test_bench_command.py` classes (including `TestSubmissionVerifier`) and `tests/test_cli_diff_bugs.py::TestBenchScheduler`; tested both default `./pubrun-bench-results/` and `PUBRUN_RESULTS_DIR` `--json` with `_share_check` and `TemporaryDirectory` cleanup | Ensure worktree-safe, deterministic, non-vacuous validation (`PR-003`) |
| `## Approval and execution gate` and acronyms (`HPC`, `CLI`, `PII`, `JSON`) | Single gate paragraph lacking preconditions, `--scope-reason`/`--scope-ack`, validation honesty, no-`git add -A`/raw `git commit`, and conditional finalize ownership; acronyms unexpanded | Replaced with complete five-clause execution contract with conditional `aw oc run`/`aw agy run` vs manual `aw ipd finalize mfeptf` ownership and expanded acronyms on first use | Satisfy execution-contract rules (`r2-executability.md`, `s7-finalize.md`) and technical writing requirement 1 (`PR-004`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: bej1qz`, `- Order: 3`, `- Item-Dependencies: executed:29nsim, executed:c1zz3x`, `- Scope-Paths:` (`src/pubrun/__main__.py, tests/test_bench_command.py`), 4 E-items in 4 task groups.

1. Yes: changes `pubrun bench` CLI runtime resolution, default output directory behavior, HPC submission environment (`PUBRUN_RESULTS_DIR`, optional `PUBRUN_REPO`), `--help` text, and `_share_check` internals depended upon by `cuboum` and `1r585o`.
2. Yes: deletes `_verify_redacted`, `_scan_for_pii`, `_pii_needles`, `_BENCH_SENSITIVE_KEYS`, `_BENCH_SENSITIVE_LIST_KEYS`, and `_load_share_safety`, and rewires `_share_check` (the privacy gate for all benchmark submission/attach/staging flows) directly to `pubrun._bench.share_safety.check_share_safe_text`.
3. Yes: 4 E-items across 4 task groups integrating `29nsim` and `c1zz3x` into `src/pubrun/__main__.py` and keeping `tests/test_bench_command.py` green.
4. Yes: `- Scope-Paths:` explicitly lists `src/pubrun/__main__.py, tests/test_bench_command.py`.
5. Yes: a defect in `_share_check` could allow unredacted PII to be staged or submitted publicly; deleting `_verify_redacted` without migrating `TestSubmissionVerifier` breaks `pytest tests/` at merge time; worktree validation without `PYTHONPATH=src` tests the wrong checkout.

AW-TIER: complex

### Step R1

- Checked: `src/pubrun/__main__.py` lines 1375-1600, 1960-2298, and 2955-3025 (`_find_bench_harness`, `_BENCH_SENSITIVE_KEYS`, `_BENCH_SENSITIVE_LIST_KEYS`, `_pii_needles`, `_scan_for_pii`, `_verify_redacted`, `_load_share_safety`, `_share_check`, `_print_safe_file_block`, `_slurm_wait_and_contribute`, `_run_bench`, `bench_parser`), `tests/test_bench_command.py` (all test classes including `TestSubmissionVerifier:425-462`), `tests/test_cli_diff_bugs.py::TestBenchScheduler:250-285`, `tests/conftest.py`, and graduated backlog item `bej1qz`.
- Verified: every cited symbol in `src/pubrun/__main__.py` exists at the expected location; checking `tests/` surfaced the breaking dependency of `tests/test_bench_command.py::TestSubmissionVerifier` on `_verify_redacted` (`PR-001`) and confirmed `tests/test_cli_diff_bugs.py::TestBenchScheduler` remains compatible.

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-04` <-> `V-01..V-04`), `- Scope-Paths:` completeness, `- Item-Dependencies: executed:29nsim, executed:c1zz3x`, runtime-demonstration reachability for every `V-*` item, worktree-safe validation commands, and the execution gate contract.
- Verified: `PR-003` fixed missing `PYTHONPATH=src` in Commands 2, 3, and 5 and aligned Command 5 with `E-04`'s non-checkout `./pubrun-bench-results/` requirement; `PR-004` completed the five-clause execution contract.

### Step R3

- Checked: privacy/PII gating across `_share_check`, `_print_safe_file_block`, `_prepare_submission`, `_submit_benchmark_result`, `_run_bench --submit-file`, and `PUBRUN_UNREDACTED` opt-in handling.
- Verified: removing `_verify_redacted` and `_load_share_safety` eliminates the stale fallback verifier so every local and server-side check uses the single canonical `pubrun._bench.share_safety.check_share_safe_text` without echoing raw leaked values; `PUBRUN_UNREDACTED` remains strictly opt-in.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified: `PR-001` preserves test-suite greenness on `main` across Orders 03 to 05; `PR-002` ensures cross-platform `Path` detection, `PUBRUN_UNREDACTED` parity across all schedulers, and clean removal of `harness.parents[1]`; `PR-003` closes validation determinism and coverage gaps; `## Spec / documentation sync` truthfully defers documentation updates to `cuboum` (Order 04).

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught `PYTHONPATH=src` omission in worktree validation commands and missing default-dir smoke check (`PR-003`).
  2. Testing and regression: caught `TestSubmissionVerifier` breakage on `_verify_redacted` removal (`PR-001`) and verified `tests/test_cli_diff_bugs.py::TestBenchScheduler` compatibility.
  3. UI / UX: checked `bench_parser` help text, non-Slurm `"Submitted. Results will be written under {results_dir}..."` message, and no em/en dashes (`PR-002`, `PR-004`).
  4. Architect: verified clean consumption of `pubrun._bench` (`default_results_dir`, `find_checkout_root`, `get_submit_script_path`, `share_safety.check_share_safe_text`) with zero duplicated verifier code.
  5. Software engineer: caught Windows path-separator hazard for packaged harness detection and `PUBRUN_UNREDACTED` omission on PBS/LSF/SGE (`PR-002`).
  6. Power user: verified `PUBRUN_RESULTS_DIR`, `--json`, `--no-submit`, `--submit-file`, `--unredacted`, and `--scheduler` all remain intact.
  7. Novice: verified `pubrun bench` works out of the box after `pip install pubrun` and prints clear output locations.
  8. Stakeholder: confirmed full alignment with backlog item `bej1qz` requirements 4, 5, 6, and 7.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-04` (4 E-items, 4 task groups, 2 Scope-Paths, Order 03 of 5-child Set `bej1qz`).
- Confirmed: each E-item is focused and right-sized; no splitting warranted.

### Step R7

- Checked: cross-plan consistency across Set `bej1qz` (`s3y296`, `29nsim`, `c1zz3x`, `cuboum`, `1r585o`).
- Verified: `mfeptf` depends on `executed:29nsim, executed:c1zz3x` and consumes their exact helpers (`find_checkout_root`, `default_results_dir`, `get_submit_script_path`, `share_safety.check_share_safe_text`, `-m pubrun._bench.harness`, `src/pubrun/_bench/scripts/*`). Adding `tests/test_bench_command.py` to `mfeptf` has zero concurrency conflict with `1r585o` because `1r585o` depends on `executed:mfeptf` (Order 05 runs strictly after Order 03), and keeps `pytest tests/` passing at Order 03 merge time.

### Step S5

- Checked: `## Open questions` contains `None.`. All four findings (`PR-001` through `PR-004`) had `Low` overall Remediation Risk and were fixed in place from repository evidence, leaving zero open or deferred findings and zero unresolved human decisions.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r4-engineering.md` D (Anti-regression) / `r7-cross-plan.md` | `.aw/records/plans/pending/20261127-bej1qz-03-mfeptf-wire-pubrun-bench-cli-to-packaged-runtime-and-single-source.ipd.md:56,121-122` vs `tests/test_bench_command.py::TestSubmissionVerifier:425-462` | Deleting `_verify_redacted` in `mfeptf` (Order 03) while deferring `tests/test_bench_command.py` updates to `1r585o` (Order 05) immediately breaks all four tests in `TestSubmissionVerifier` (`AttributeError`), causing the merge-and-revalidate gate to reject `mfeptf` and halt Set `bej1qz`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `tests/test_bench_command.py` to `- Scope-Paths:` (strictly serialized before `1r585o` via `executed:mfeptf`), migrated the 4-test `TestSubmissionVerifier` class to `_share_check` in `E-01`, updated `## Deferred / out of scope` and `## Scope check`, and verified it in Validation Command 4 (recommendation strength: `very strong`). |
| PR-002 | MEDIUM | IN-SCOPE | `r4-engineering.md` A, F (Cross-platform correctness & scheduler parity) | `.aw/records/plans/pending/20261127-bej1qz-03-mfeptf-wire-pubrun-bench-cli-to-packaged-runtime-and-single-source.ipd.md:65-71,78-83` vs `src/pubrun/__main__.py::_run_bench:2116,2194-2202,2239` | `E-02` did not specify cross-platform `Path` detection for packaged vs checkout harness (risking `/` vs `\` bugs on Windows), did not explicitly remove stale `repo_root = harness.parents[1]` and unused `_tf` or update `_find_bench_harness`/`_run_bench` docstrings, left `PUBRUN_UNREDACTED` wired only for Slurm instead of all schedulers, and `E-03` did not specify no em/en dashes in user-facing help prose. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-02` and `E-03` to require cross-platform `Path` checks, `spec.origin` guards, removal of `repo_root = harness.parents[1]` / unused `_tf`, `PUBRUN_UNREDACTED` forwarding for all schedulers, updated docstrings, and no em/en dashes in `bench_parser` help text (recommendation strength: `strong`). |
| PR-003 | HIGH | IN-SCOPE | `r4-engineering.md` E / `r2-executability.md` (Worktree-safe and complete validation) | `.aw/records/plans/pending/20261127-bej1qz-03-mfeptf-wire-pubrun-bench-cli-to-packaged-runtime-and-single-source.ipd.md:88-95,139-156` vs `tests/conftest.py::_subprocess_pythonpath:19-39` | Validation Commands 2, 3, and 4 omitted `PYTHONPATH=src` (importing the main checkout's editable install instead of the worktree's `src/`), Command 4 contradicted `E-04` by never testing default non-checkout `./pubrun-bench-results/` or `_share_check` and leaked temp dirs, and no pytest command verified existing CLI tests (`TestSubmissionVerifier`, `TestBenchNoBaselineFlag`, `TestBenchScheduler`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `PYTHONPATH=src` to Commands 2, 3, and 5; added Command 4 running fast `tests/test_bench_command.py` classes and `tests/test_cli_diff_bugs.py::TestBenchScheduler`; updated Command 5 to test both default `./pubrun-bench-results/` (`--no-submit`, `runs/` absent) and `PUBRUN_RESULTS_DIR` `--json` with `_share_check` and `TemporaryDirectory` cleanup; reconciled `V-01..V-04` (recommendation strength: `very strong`). |
| PR-004 | MEDIUM | IN-SCOPE | `r2-executability.md` / `s7-finalize.md` / `p-proofread.md` (Execution contract and technical writing) | `.aw/records/plans/pending/20261127-bej1qz-03-mfeptf-wire-pubrun-bench-cli-to-packaged-runtime-and-single-source.ipd.md:6,59,90,189-194` | `## Approval and execution gate` omitted the open-question precondition, `--scope-reason`/`--scope-ack` scope declaration, hard-MUST validation honesty rule, explicit no-`git add -A`/raw `git commit` prohibition, and conditional runner vs manual `aw ipd finalize mfeptf` ownership; `HPC`, `CLI`, `PII`, and `JSON` were not expanded on first use. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced the gate paragraph with the complete five-clause execution contract (including conditional `aw oc run`/`aw agy run` vs manual `aw ipd finalize mfeptf` ownership) and expanded acronyms on first use (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `mfeptf` | `complex` | `standard` | Order 03 of 5-child Set `bej1qz`, rewires `_share_check` privacy gate and `pubrun bench` CLI behavior, and integrates `29nsim` and `c1zz3x`; answers Yes to tier questions 1, 2, 3, and 5. | yes |
| D-2 | How to avoid breaking `tests/test_bench_command.py::TestSubmissionVerifier` when `mfeptf` deletes `_verify_redacted` | Add `tests/test_bench_command.py` to `mfeptf` `- Scope-Paths:` and migrate `TestSubmissionVerifier` to `_share_check` in `E-01` | Keep a temporary `_verify_redacted` shim until Order 05 (violates `mfeptf` E-01/V-01 and `bej1qz` req 7) or accept broken `pytest tests/` on `main` across Orders 03 to 04 | `tests/test_bench_command.py::TestSubmissionVerifier:425-462`, backlog `bej1qz` requirement 7, and strict serialization `1r585o -> executed:mfeptf`. | yes |

### Step S6

- Checked: Round 1 added `tests/test_bench_command.py` to `- Scope-Paths:` (`PR-001`), which triggers a Pass 2 re-review per `steps/s6-rereview.md` rule 1 to verify scope-fence alignment, cross-plan consistency with `1r585o`, and structural cleanliness after the scope change.

AW-REVIEW: AGAIN

## Round 2

### Step P

- Checked: re-read the complete revised `.aw/records/plans/pending/20261127-bej1qz-03-mfeptf-wire-pubrun-bench-cli-to-packaged-runtime-and-single-source.ipd.md` after Round 1's `- Scope-Paths:` expansion (`src/pubrun/__main__.py, tests/test_bench_command.py`). All headings, `E-01..E-04`/`V-01..V-04` bijection, technical writing requirements 1 to 12, and Mermaid diagram consistency hold with zero new defects.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step R1

- Checked: verified that every reference introduced by Round 1 (`tests/test_bench_command.py::TestSubmissionVerifier`, `tests/test_cli_diff_bugs.py::TestBenchScheduler`, `tests/conftest.py::_subprocess_pythonpath`, and all 12 pytest node IDs in Validation Command 4) matches exact class and method names in the repository.

### Step R2

- Checked: confirmed `- Scope-Paths: src/pubrun/__main__.py, tests/test_bench_command.py` matches `E-01..E-04`, `## Scope check`, `## Deferred / out of scope`, and clause 2 of `## Approval and execution gate`; confirmed every `V-01..V-04` demand is reachable and reconciled with the five commands in `## Required tests / validation`.

### Step R7

- Checked: confirmed `tests/test_bench_command.py` scope partition between `mfeptf` (Order 03, migrates `TestSubmissionVerifier` only) and `1r585o` (Order 05, depends on `executed:mfeptf`, updates remaining legacy classes and adds new test classes) has zero overlap conflict and keeps `main` green at every commit.

### Step S5

- Checked: zero open questions, zero unresolved findings, zero deferred findings. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|

### Step S6

- Checked: Round 2 required no edits to `E-*`, `V-*`, `- Scope-Paths:`, or `- Item-Dependencies:`, introduced zero new questions or findings, and verified full cross-section consistency. No further pass is needed.

AW-REVIEW: DONE
