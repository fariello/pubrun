# Review findings: ipd n39jh9

- Subject-Id: n39jh9
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-bt-06-n39jh9-bench-env-isolation-filesystem-live-probing-scaling-scrub-an.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` (`conforming`). Added a Mermaid `flowchart LR` matching all 8 Scope-Paths (`PR-004`), required local `_json_needle_leak` with `scaling_bench._SCRUB_SKIP_KEYS` and `_needles_found` plus fail-closed negative test coverage (`PR-001`), made `current_labels` explicitly optional on `pull_submissions._retag` to preserve backward compatibility with existing tests (`PR-002`), clarified per-file `sys.path`/`sys.modules` cleanup and cross-platform `probe_paths_live` entry ordering (`PR-003`), replaced `N/A.` with `Not applicable.`, switched validation commands to `python3 -m pytest` / `python3 -m mypy` (adding `tests/test_bench_command.py` and `tests/test_benchmark_intake_bugs.py`), and completed the five-clause execution contract (`PR-004`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `### Bench, filesystem, and submission hardening scope` | Plan had no Mermaid diagram despite modifying 8 related files across 4 components | Added `flowchart LR` mapping `E-01..E-04` files to `E-05` validation | Satisfy technical writing standard Req 12(a) (`PR-004`) |
| `E-02` bullet 1, `E-03` bullet 2, `## Findings` (`BUG-E6`) | Specified `_SCRUB_SKIP_KEYS` swap without requiring local `_json_needle_leak` / `scaling_bench._needles_found` (`_PROTECTED_RE`), omitted workdir-guard test and negative fail-closed test in `test_share_safety.py` | Required local `_json_needle_leak` using `scaling_bench._SCRUB_SKIP_KEYS` and `scaling_bench._needles_found`, plus positive skip-key, workdir-guard, and fail-closed leak-rejection tests | Ensure `"pubrun-scaling-bench/1"` stays protected and privacy check stays fail-closed (`PR-001`) |
| `E-02` bullet 2, `E-03` bullet 3, `## Project conventions discovered` | Left `_retag` signature vague (`and/or filter ... against current_labels`) without protecting existing 4-arg `_retag` callers | Specified optional `current_labels: Optional[Sequence[str]] = None` with backward-compatible 4-attempt fallback when `None` and exact filtered removals when passed from `_process_issue`, testing both paths | Preserve existing `_retag` unit tests in `benchmarks/test_pull_submissions.py` (`PR-002`) |
| `E-01`, `E-03`, `E-04` | Described all three benchmark test files as having collection-time `sys.path` mutations, omitted `TestSchema5Validation` from module-fixture caching, and left `probe_paths_live` test path ordering/portability unspecified | Clarified per-file `sys.path`/`sys.modules` restoration, shared module-scoped harness fixture across both `TestSchema5Shape` and `TestSchema5Validation`, noted `_run_baseline_pass` isolation via `_child_env_with_checkout_src`, and specified `results_dir` first + `mount_point=str(tmp_path)` in `E-04` | Ensure all 10 redundant runs collapse to 1 and `BUG-E7` test reproduces bug portably across Linux/macOS/Windows (`PR-003`) |
| `## Required tests / validation`, `## Spec / documentation sync`, `V-01..V-05`, `## Approval and execution gate` | Used bare `pytest`/`mypy`, omitted `test_bench_command.py`/`test_benchmark_intake_bugs.py`, used `N/A.`, and omitted full execution-contract clauses | Switched to `python3 -m pytest` (including `tests/test_bench_command.py` and `tests/test_benchmark_intake_bugs.py`) and `python3 -m mypy`, expanded `N/A.` to `Not applicable.`, added reachability/re-derivation wording to `V-01..V-05`, and completed the 5-clause execution contract | Satisfy `technical-writing.md` Req 1, `r2-executability.md`, and `s7-finalize.md:31-46` (`PR-004`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-bt`, `- Order: 6`, `- Scope-Paths:` (`src/pubrun/_bench/harness.py, src/pubrun/capture/filesystem.py, benchmarks/scaling_bench.py, benchmarks/pull_submissions.py, benchmarks/test_benchmarks.py, benchmarks/test_share_safety.py, benchmarks/test_pull_submissions.py, tests/test_capture_engines.py`), 5 E-items in 3 task groups, no `.spec.md` file.

1. Yes: modifies packaged benchmark child-env construction (`src/pubrun/_bench/harness.py`), live filesystem probing (`src/pubrun/capture/filesystem.py`), scaling-bench share-safety validation (`benchmarks/scaling_bench.py`), and GitHub submission re-tagging (`benchmarks/pull_submissions.py`).
2. Yes: modifies `src/pubrun/_bench/harness.py` and `benchmarks/scaling_bench.py::_validate_share_safety` (which guard against leaking private hostnames, usernames, and paths in shared benchmark artifacts).
3. Yes: 5 E-items across 3 task groups spanning 8 files (4 production/script modules and 4 test files) in the 10-child Set `assess-bt`.
4. Yes: `- Scope-Paths:` explicitly lists all 8 files.
5. Yes: an error in `benchmarks/scaling_bench.py::_validate_share_safety` could weaken PII redaction checks, and an error in `benchmarks/pull_submissions.py::_retag` could mislabel live GitHub submission issues.

AW-TIER: complex

### Step R1

- Checked: every file and symbol cited in `n39jh9` against the repository: `src/pubrun/_bench/harness.py` (`_filesystem_context:165-194`, `_child_env_with_checkout_src:226-236`, `_build_child_command:239-266`, `_run_pass:317-377`, `_run_baseline_pass:380-414`), `src/pubrun/_bench/scenarios.py` (`all_scenarios`, `PUBRUN_BENCH_IO_TARGET`, `PUBRUN_BENCH_FILE_MODE`), `src/pubrun/_bench/workloads/io_sink.py`, `src/pubrun/capture/filesystem.py` (`probe_paths_live:417-444`), `benchmarks/scaling_bench.py` (`_PROTECTED_RE:61-63`, `_SCRUB_SKIP_KEYS:64-80`, `_scrub_obj:491-501`, `_needles_found:504-510`, `_validate_share_safety:513-540`, `main:717-752`), `benchmarks/startup_breakdown.py` (`_SCRUB_SKIP_KEYS:74-80`, `_PROTECTED_RE:82`, `_json_needle_leak:381-395`), `benchmarks/pull_submissions.py` (lines 46-50 `sys.path.insert`, `list_issues:102-119`, `_retag:253-289`, `_process_issue:292-315`), `benchmarks/test_benchmarks.py` (`_load:21-28`, `TestSchema5Shape:33-106`, `TestSchema5Validation:180-233`), `benchmarks/test_share_safety.py`, `benchmarks/test_pull_submissions.py` (`_load_pull:22-32`, `_retag` tests:168-198), and `tests/test_capture_engines.py`.
- Verified: all cited files and symbols exist; caught three subtle behavioral details missed by the draft (`_sb._json_needle_leak` also uses `_sb._PROTECTED_RE` in `PR-001`, existing `_retag` tests omit `current_labels` in `PR-002`, and exact per-file `sys.path`/`sys.modules` behavior across the 3 benchmark test files in `PR-003`).

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Scope-Paths:` completeness, `- Item-Dependencies: none`, runtime-demonstration reachability, re-derivation convention (`r2-executability.md:65`), and the 5-clause execution contract in `## Approval and execution gate`.
- Verified: `PR-001` through `PR-004` aligned every `E-*`/`V-*` pair, added missing `test_bench_command.py` and `test_benchmark_intake_bugs.py` coverage, and completed the execution gate contract.

### Step R3

- Checked: full security and privacy rubric (`r3-security.md` B) across `src/pubrun/_bench/harness.py`, `benchmarks/scaling_bench.py`, and `benchmarks/pull_submissions.py`.
- Verified:
  - Privacy / PII scrubbing (`scaling_bench.py`): defining local `_json_needle_leak` with `scaling_bench._SCRUB_SKIP_KEYS` (strictly fixed-vocabulary keys, deliberately excluding `release`, paths, hostnames, usernames) and `scaling_bench._needles_found` preserves fail-closed detection of real leaks while avoiding false failures on fixed-vocabulary keys; guarding bare relative `args.workdir` still includes `str(Path(args.workdir).resolve())` as a path needle; `PR-001` adds an explicit negative fail-closed leak-rejection test.
  - Subprocess / GitHub CLI safety (`pull_submissions.py`): `_retag` continues to invoke `gh` strictly via argv lists (`shell=False`) with fixed label constants (`_LABEL_ACCEPTED`, `_LABEL_NEEDS_FIX`, `_LABEL_PENDING`) and `str(int(issue_number))`.
  - Environment isolation (`harness.py`): stripping ambient `PUBRUN_*` keys prevents external env vars (e.g. `PUBRUN_OUTPUT_DIR`) from redirecting benchmark child writes outside the isolated `scn_cwd`.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified:
  - A/C/D: stripping `PUBRUN_*` in `_child_env_with_checkout_src()` isolates both `_build_child_command` and `_run_baseline_pass` while preserving explicit `scn.env` (`PUBRUN_BENCH_IO_TARGET` on `io-baseline-devnull`/`io-baseline-devshm`, `PUBRUN_BENCH_FILE_MODE` on `file_read.py`); `probe_paths_live` probing `mp` (`mount_point`) eliminates mount-poisoning by uncreated child paths; optional `current_labels` on `_retag` preserves all existing tests while fixing dual-label bugs; module-scoped fixture caching across both `TestSchema5Shape` and `TestSchema5Validation` cuts 10 harness runs to 1 (~10x faster).
  - E: Command 1 runs all 6 affected pytest files under `-p randomly` and Command 2 runs 3-OS `mypy` (Linux, `win32`, `darwin`).
  - Right-sizing: 5 E-items in 3 task groups across 8 Scope-Paths; each E-item is concise and focused.
  - `## Spec / documentation sync`: substantiated (bug fixes align with existing documented behavior).

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught `_sb._PROTECTED_RE` mismatch in `scaling_bench.py` (`PR-001`) and `results_dir` dict-order dependency in `E-04` (`PR-003`).
  2. Testing and regression: caught backward-compatibility risk on `_retag` tests (`PR-002`), added `TestSchema5Validation` to fixture caching (`PR-003`), and added `test_bench_command.py`/`test_benchmark_intake_bugs.py` to Command 1 (`PR-004`).
  3. UI / UX: verified `pubrun bench` child runs are unaffected by user shell `PUBRUN_*` exports and `scaling_bench.py` no longer false-fails on `--mode quick` / `--workdir quick`.
  4. Architect: verified clean reuse of `_child_env_with_checkout_src` across measured and baseline passes and clean `sys.path`/`sys.modules` fixture teardown.
  5. Software engineer: verified cross-platform `isinstance(mp, str)` guard in `probe_paths_live` and `str(tmp_path)` mount-point test portability on Linux/macOS/Windows.
  6. Power user: verified `PUBRUN_BENCH_IO_TARGET` in `scn.env` stays intact while ambient shell `PUBRUN_BENCH_IO_TARGET` cannot corrupt `io-baseline-tmpdir`.
  7. Novice: added Mermaid diagram and explicit per-file instructions in `E-01..E-04`.
  8. Stakeholder: confirmed full coverage of `BUG-E5..E8` and `TEST-I5`/`TEST-I6` (benchmarks) assigned by orchestrator `n6250e`.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-05` (5 E-items, 3 task groups, 8 Scope-Paths, already Order 06 of 10-child Set `assess-bt`).
- Confirmed: each E-item targets one bounded group of small fixes or paired tests. No further split is warranted.

### Step R7

- Checked: cross-plan consistency across Set `assess-bt` (orchestrator `n6250e` and sibling children `wcjdbu`, `ndobra`, `thbepl`, `qum7gf`, `kk83rk`, `dqaj9a`, `kgoymu`, `4eo4z2`, `37sth0`).
- Verified: strictly disjoint `Scope-Paths` across all 10 children (`n39jh9` owns `benchmarks/test_benchmarks.py`, `benchmarks/test_share_safety.py`, `benchmarks/test_pull_submissions.py`, and `tests/test_capture_engines.py`, whereas `4eo4z2` owns `tests/test_bench_command.py` and `37sth0` owns `tests/test_package_benchmark.py`/`tests/test_startup_benchmark.py`); `n39jh9` deliverables and `Item-Dependencies: none` align with `n6250e` E-06.

### Step S5

- Checked: `## Open questions` contains `None.`. All four findings (`PR-001` through `PR-004`) had `Low` overall Remediation Risk, were settled by repository code and documented workflow policy, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r1-references.md` / `r2-executability.md` / `r3-security.md` / `r4-engineering.md` A | `.aw/records/plans/pending/20261127-assess-bt-06-n39jh9-bench-env-isolation-filesystem-live-probing-scaling-scrub-an.ipd.md:46,56` vs `benchmarks/scaling_bench.py:61-80,491-540,725-738`, `benchmarks/startup_breakdown.py:74-82,371-395` | `scaling_bench.py::_validate_share_safety` delegating to `_sb._json_needle_leak` mismatches both `_SCRUB_SKIP_KEYS` and `_PROTECTED_RE` (`pubrun-startup-breakdown/1` vs `pubrun-scaling-bench/1`), and `E-03` bullet 2 omitted testing the `main()` workdir needle guard and a negative fail-closed leak-rejection case. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified local `_json_needle_leak` in `benchmarks/scaling_bench.py` using `scaling_bench._SCRUB_SKIP_KEYS` and `scaling_bench._needles_found`, and updated `E-03` bullet 2 to test positive skip-key preservation, bare relative workdir guard, and fail-closed leak rejection (recommendation strength: `very strong`). |
| PR-002 | HIGH | IN-SCOPE | `r2-executability.md` / `r4-engineering.md` A, D | `.aw/records/plans/pending/20261127-assess-bt-06-n39jh9-bench-env-isolation-filesystem-live-probing-scaling-scrub-an.ipd.md:47,57` vs `benchmarks/pull_submissions.py:117,253-275,292-315`, `benchmarks/test_pull_submissions.py:168-198` | `E-02` bullet 2 left `_retag`'s `current_labels` contract vague, risking breaking the three existing `_retag` unit tests in `benchmarks/test_pull_submissions.py` that omit `current_labels` and assert `--remove-label status:pending` on the first attempt. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified optional keyword-only `current_labels: Optional[Sequence[str]] = None` on `_retag` with backward-compatible 4-attempt fallback `(add+remove+pending, add+pending, add+remove, add)` when `None` and exact present-label filtering when passed by `_process_issue`, testing both paths in `E-03` (recommendation strength: `very strong`). |
| PR-003 | MEDIUM | IN-SCOPE | `r1-references.md` / `r2-executability.md` / `r4-engineering.md` E | `.aw/records/plans/pending/20261127-assess-bt-06-n39jh9-bench-env-isolation-filesystem-live-probing-scaling-scrub-an.ipd.md:55-57,63` vs `benchmarks/test_benchmarks.py:21-28,33-106,204-233`, `benchmarks/test_share_safety.py:13-18`, `benchmarks/test_pull_submissions.py:22-32` | `E-03` conflated `sys.path` and `sys.modules` leaks across the three benchmark test files and omitted `TestSchema5Validation` from module-fixture reuse (leaving 2 of 10 redundant runs uncached); `E-04` did not specify putting `results_dir` first and using `str(tmp_path)` as shared `mount_point` for cross-platform portability. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Clarified per-file `sys.path`/`sys.modules` fixture teardown, extended module-scoped harness fixture reuse to both `TestSchema5Shape` and `TestSchema5Validation` (using `copy.deepcopy`), noted `_run_baseline_pass` isolation in `E-01`, and specified `results_dir` first with `mount_point=str(tmp_path)` in `E-04` (recommendation strength: `strong`). |
| PR-004 | MEDIUM | IN-SCOPE | `p-proofread.md` / `r2-executability.md` / `s7-finalize.md` | `.aw/records/plans/pending/20261127-assess-bt-06-n39jh9-bench-env-isolation-filesystem-live-probing-scaling-scrub-an.ipd.md:26-29,111-120,130-164` vs `.aw/system/workflows/technical-writing/technical-writing.md:29,40-46`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46`, `.aw/system/workflows/plan-review/steps/r2-executability.md:65` | Plan lacked a Mermaid diagram for its 8-file multi-component scope (Req 12), used bare `pytest`/`mypy`, omitted `tests/test_bench_command.py` and `tests/test_benchmark_intake_bugs.py`, used `N/A.`, and omitted required execution-contract clauses in `## Approval and execution gate`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added a Mermaid `flowchart LR`, switched to `python3 -m pytest` (adding `tests/test_bench_command.py` and `tests/test_benchmark_intake_bugs.py`) and `python3 -m mypy`, expanded `N/A.` to `Not applicable.`, tightened `V-01..V-05`, and completed the 5-clause execution contract (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `n39jh9` | `complex` | `standard` | Touches privacy/share-safety validation (`src/pubrun/_bench/harness.py`, `benchmarks/scaling_bench.py`) and GitHub issue re-tagging (`benchmarks/pull_submissions.py`) across 8 files in 10-child Set `assess-bt`; answers Yes to tier questions 1, 2, 3, and 5 (`steps/t-tier.md`). | yes |
| D-2 | Signature of `benchmarks/pull_submissions.py::_retag` for `BUG-E8` | Add optional keyword-only `current_labels: Optional[Sequence[str]] = None` (keeping 4-attempt fallback when `None` and exact present-label filtering when passed from `_process_issue`) | Require `current_labels` on all `_retag` callers, or only add the 4th fallback without passing `issue["labels"]` | `benchmarks/pull_submissions.py:117,253-275,292-315` already fetches `issue["labels"]` in `list_issues`, while `benchmarks/test_pull_submissions.py:168-198` calls `_retag` without `current_labels`; supporting both avoids breaking existing callers and eliminates unnecessary failed `gh` calls during `_process_issue`. | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` and `- Item-Dependencies:` are unchanged; every revision (`PR-001` through `PR-004`) was swept across `## Goal`, the Mermaid diagram, `E-01..E-05`, `## Project conventions discovered`, `## Findings`, `## Proposed changes`, `## Required tests / validation`, `## Spec / documentation sync`, `V-01..V-05`, and `## Approval and execution gate` with no remaining contradictions, open questions, or structural ambiguities. No second pass is needed.

AW-REVIEW: DONE
