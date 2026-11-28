# Review findings: ipd 37sth0

- Subject-Id: 37sth0
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-bt-10-37sth0-slow-test-markers-and-workflow-or-benchmark-test-isolation-c.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` (`conforming`). Expanded acronyms (`CI`, `CLI`) on first use, standardized full repo-relative `path::Symbol` citations, added a Mermaid `flowchart LR` summarizing the 3-file workflow (`E-01..E-03` -> `E-04`, Req 12), replaced `N/A.` with a substantiated `Not applicable.`, and completed all 5 execution-contract clauses in `## Approval and execution gate` (`PR-004`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `### Slow marker and test isolation workflow` | Plan had no Mermaid diagram despite updating 3 related test files with a multi-step validation flow | Added `flowchart LR` linking `E-01`, `E-02`, `E-03` to `E-04` | Satisfy technical writing standard Req 12(a)/(b) (`PR-004`) |
| `## Goal`, `E-01`, `## Project conventions discovered`, `## Findings`, `## Proposed changes`, `V-01` | Claimed `tests/test_compatibility.py` had `pyproject.toml` pins to replace with Python 3.11+ `tomllib`, and omitted PyYAML optionality in CI's `test` job | Removed erroneous `pyproject.toml`/`tomllib` claims; specified formatting-tolerant zero-dependency stdlib workflow checks plus structured `pytest.importorskip("yaml")` assertions | Fix false file reference and prevent breaking CI's 21-cell `test` matrix where `pyyaml` is not installed (`PR-001`) |
| `E-02`, `E-03`, `## Project conventions discovered`, `## Required tests / validation`, `V-02`, `V-03`, `V-04` | Addressed only `sys.modules[mod_name]` cleanup and lacked a runtime check of `sys.path`/`sys.modules` cleanliness | Specified snapshotting and restoring both `sys.path[:]` and `sys.modules` (covering `benchmarks/`, `src/`, `share_safety`, and `_pubrun_bench_scenarios_standalone`) plus Command 3 (`BENCH_TESTS_IMPORT_CLEAN_OK`) | Close transitive `sys.path` and `sys.modules` leaks (`PR-002`) |
| `E-01`, `E-02`, `E-03` | Left exact `@pytest.mark.slow` targets unnamed across the 3 files | Named exact slow targets (`test_scaling_benchmark_quick_smoke_and_share_safety`, `TestPackageCaptureBenchRun`, `TestBreakdownEndToEnd`, `TestBreakdownScrubBoundaries.test_cli_with_short_username_emits_intact_output`) and named fast tests to keep unmarked | Prevent partial class marking or missed slow tests under `-m "not slow"` (`PR-003`) |
| `## Required tests / validation`, `## Spec / documentation sync`, `V-01..V-04`, `## Approval and execution gate` | Used bare `pytest`, `N/A.`, omitted reachability/re-derivation wording in `V-*`, and omitted required execution-contract clauses | Switched to `python3 -m pytest`, replaced `N/A.` with substantiated `Not applicable.`, added reachability and execution-time re-derivation wording in `V-01..V-04`, and completed all 5 execution-contract clauses | Satisfy `technical-writing.md`, `r2-executability.md`, and `s7-finalize.md:31-46` (`PR-004`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-bt`, `- Order: 10`, `- Scope-Paths:` (`tests/test_compatibility.py, tests/test_package_benchmark.py, tests/test_startup_benchmark.py`), 4 E-items in 2 task groups, `- Priority: low`, no `.spec.md` file.

1. No: test-only plan modifying three test files using the existing `slow` marker already registered in `pyproject.toml`; changes no spec, public CLI, or production API.
2. No: touches only test files under `tests/`, not production security, commit, worktree, or sandbox code.
3. No: small, cohesive 4-E-item / 2-task-group / 3-file test hygiene plan (Order 10 of Set `assess-bt`).
4. Yes: `- Scope-Paths:` explicitly lists all 3 modified test files.
5. Yes: replacing the stdlib workflow checks in `tests/test_compatibility.py` with unconditional `import yaml` would break the 21-cell `test` matrix in `.github/workflows/ci.yml` where `pyyaml` is not installed, and incomplete `sys.path`/`sys.modules` cleanup or missed slow markers would defeat the plan's test-hygiene goals.

AW-TIER: standard

### Step R1

- Checked: every file, test class, helper, and workflow cited or exercised by `37sth0` against the repository:
  - `tests/test_compatibility.py` (L1-223): `_load_share_safety`, `_extract_job_block`, `test_scaling_benchmark_quick_smoke_and_share_safety` (L46-135), `test_ci_workflow_compatibility_matrix_structural` (L137-168), `test_dependency_audit_workflow_structural` (L170-178), `test_workflows_pyyaml_crosscheck_when_available` (L180-223). Confirmed `tests/test_compatibility.py` never reads `pyproject.toml`.
  - `.github/workflows/ci.yml` (`test` job L38 `pip install -e ".[dev,tui]"` without `pyyaml`; `extra-suites` job L55 `pip install -e ".[dev,bench]" pyyaml`) and `.github/workflows/dependency-audit.yml` (L1-29).
  - `tests/test_package_benchmark.py` (L1-197): `_load_module` (L22-29), `bench_run` module-scoped fixture (L32-53), `TestPackageCaptureBenchRun` (8 methods, L56-144), `TestPackageCaptureBenchCli` (1 fast argparse test, L146-156), `TestSyntheticEnvironmentBuilder` (2 unit tests, L159-186), `TestTransitiveScenario` (1 unit test, L188-197).
  - `tests/test_startup_benchmark.py` (L1-531): `_load_module` (L21-28), `TestStartupAutoDefaultScenario` (1 unit test, L31-53), `TestBreakdownStatisticsAndRedaction` (3 unit tests, L56-140), `TestBreakdownCLIValidation` (8 fast argparse/validation checks, L142-189), `TestBreakdownEndToEnd` (3 slow benchmark tests, L191-422), `TestBreakdownScrubBoundaries` (8 fast unit tests + 2 parametrized slow CLI benchmark tests at L498-531).
  - `benchmarks/package_capture_bench.py` (L59-62 `sys.path.insert` of `benchmarks/` and `src/`), `benchmarks/startup_breakdown.py` (L38-43 `sys.path.insert` of `benchmarks/` and `src/` plus `import share_safety`), `benchmarks/scenarios.py` (L22-31 `sys.modules["_pubrun_bench_scenarios_standalone"]`), and `pyproject.toml` (L15 `requires-python = ">=3.8"`, L106-108 `slow` marker registration).
- Verified: ran `python3 -m pytest --collect-only -q tests/test_compatibility.py tests/test_package_benchmark.py tests/test_startup_benchmark.py` (41 tests collected: 14 slow multi-subprocess benchmark items and 27 fast unit/structural/validation items). Uncovered and fixed `PR-001` through `PR-004`.

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-04` <-> `V-01..V-04`), `- Scope-Paths:` completeness (all 3 files mutually disjoint from sibling children in Set `assess-bt`, including `4eo4z2` which edits `.github/workflows/ci.yml` and runs `tests/test_compatibility.py -k workflow` read-only), `- Item-Dependencies: none`, runtime-demonstration reachability in `V-02`/`V-03`/`V-04`, execution-time re-derivation (`r2-executability.md:65`), and the 5-clause execution contract in `## Approval and execution gate`.
- Verified: `PR-001` through `PR-004` closed every structural, citation, reachability, and execution-contract gap.

### Step R3

- Checked: full security and privacy rubric (`r3-security.md` B).
- Verified: test-only edits; preserves all share-safety and redaction assertions across `tests/test_compatibility.py`, `tests/test_package_benchmark.py`, and `tests/test_startup_benchmark.py`, and keeps all CI/dependency-audit security checks (`pip-audit`, `scaling_bench.py` wheel exclusion, `check_share_safe_text`) active without weakening them.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified:
  - A/C/D: preserving zero-dependency stdlib workflow tests ensures CI's `test` job never fails on missing `pyyaml`; snapshotting/restoring both `sys.path[:]` and `sys.modules` closes both direct and transitive import leaks (`benchmarks/`, `src/`, `share_safety`, `_pubrun_bench_scenarios_standalone`); marking `TestPackageCaptureBenchRun` at class level prevents the module-scoped `bench_run` fixture from running under `-m "not slow"`, and marking `TestBreakdownScrubBoundaries.test_cli_with_short_username_emits_intact_output` at method level keeps the 8 fast scrub unit tests active.
  - E: Commands 1, 2, and 3 validate full randomized execution, `-m "not slow"` deselection, and `sys.path`/`sys.modules` cleanliness (`BENCH_TESTS_IMPORT_CLEAN_OK`).
  - Right-sizing: 4 E-items in 2 task groups across 3 Scope-Paths; each E-item targets exactly one test file (plus `E-04` validation) and is executable in one focused pass.
  - `## Spec / documentation sync`: substantiated (`slow` marker already registered in `pyproject.toml`; test-only changes).

### Step S5

- Checked: `## Open questions` contains `None.`. All four findings (`PR-001` through `PR-004`) had `Low` overall Remediation Risk, were settled directly by repository source and CI workflow configuration, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r1-references.md` / `r2-executability.md` / `r4-engineering.md` D, E | `.aw/records/plans/pending/20261127-assess-bt-10-37sth0-slow-test-markers-and-workflow-or-benchmark-test-isolation-c.ipd.md:28,38,68,76,80,118` vs `tests/test_compatibility.py:1-223`, `.github/workflows/ci.yml:38,55`, `pyproject.toml:15,41` | `37sth0` falsely claimed `tests/test_compatibility.py` had `pyproject.toml` pins to parse with Python 3.11+ `tomllib` (`test_compatibility.py` never reads `pyproject.toml`, and bare `tomllib` breaks Python 3.8–3.10), and omitted PyYAML optionality needed by CI's 21-cell `test` job. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Removed erroneous `pyproject.toml`/`tomllib` claims across the plan; specified formatting-tolerant zero-dependency stdlib workflow checks plus structured `pytest.importorskip("yaml")` assertions in `E-01` and `V-01` (recommendation strength: `very strong`). |
| PR-002 | HIGH | IN-SCOPE | `r1-references.md` / `r2-executability.md` / `r4-engineering.md` A, D | `.aw/records/plans/pending/20261127-assess-bt-10-37sth0-slow-test-markers-and-workflow-or-benchmark-test-isolation-c.ipd.md:45,52,74,81-82` vs `tests/test_package_benchmark.py::_load_module:22-29`, `tests/test_startup_benchmark.py::_load_module:21-28`, `benchmarks/package_capture_bench.py:59-62`, `benchmarks/startup_breakdown.py:38-43`, `benchmarks/scenarios.py:22-31` | `E-02` and `E-03` addressed only `sys.modules[mod_name]` cleanup, missing permanent `sys.path` insertions (`benchmarks/`, `src/`) and transitive `sys.modules` entries (`share_safety`, `_pubrun_bench_scenarios_standalone`), and `## Required tests / validation` lacked an import-cleanliness check. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified snapshotting and restoring both `sys.path[:]` and `sys.modules` in a context manager/fixture in `E-02` and `E-03`, and added Command 3 (`BENCH_TESTS_IMPORT_CLEAN_OK`) to `## Required tests / validation`, `E-04`, and `V-02`/`V-03`/`V-04` (recommendation strength: `very strong`). |
| PR-003 | MEDIUM | IN-SCOPE | `r1-references.md` / `r2-executability.md` / `r4-engineering.md` E | `.aw/records/plans/pending/20261127-assess-bt-10-37sth0-slow-test-markers-and-workflow-or-benchmark-test-isolation-c.ipd.md:37,44,51` vs `tests/test_compatibility.py:46-135`, `tests/test_package_benchmark.py:32-197`, `tests/test_startup_benchmark.py:31-531` | `E-01`..`E-03` left exact `@pytest.mark.slow` targets unnamed, risking partial class marking of `TestPackageCaptureBenchRun` (still invoking `bench_run`) or missing `TestBreakdownScrubBoundaries.test_cli_with_short_username_emits_intact_output`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Enumerated every exact `@pytest.mark.slow` class/method target and named the fast unit, structural, and argparse-validation tests to keep unmarked across `E-01`..`E-03` (recommendation strength: `strong`). |
| PR-004 | MEDIUM | IN-SCOPE | `p-proofread.md` / `r2-executability.md` / `s7-finalize.md` | `.aw/records/plans/pending/20261127-assess-bt-10-37sth0-slow-test-markers-and-workflow-or-benchmark-test-isolation-c.ipd.md:26-29,96-108,117-146` vs `.aw/system/workflows/technical-writing/technical-writing.md:29,40-46`, `.aw/system/workflows/plan-review/steps/r2-executability.md:65,71`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46` | Plan lacked a Mermaid diagram (Req 12), used `N/A.` and bare `pytest`, omitted reachability/re-derivation wording in `V-01..V-04`, and omitted required execution-contract clauses in `## Approval and execution gate`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added Mermaid `flowchart LR`, expanded acronyms, substantiated `Not applicable.`, switched to `python3 -m pytest`, added reachability/re-derivation wording in `V-01..V-04`, and completed all 5 execution-contract clauses (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `37sth0` | `standard` | `simple`, `complex` | Low-priority test-only plan with 4 E-items in 2 task groups across 3 Scope-Paths, no spec/API or security-guard edits, and bounded CI regression risk (PyYAML optionality); matches `steps/t-tier.md` guidance for `standard`. | yes |
| D-2 | Whether fast CLI argparse-validation tests (`TestPackageCaptureBenchCli`, `TestBreakdownCLIValidation`) should be marked `@pytest.mark.slow` (`PR-003`) | Keep fast single-subprocess argparse/validation tests unmarked; mark only multi-subprocess benchmark workloads (`test_scaling_benchmark_quick_smoke_and_share_safety`, `TestPackageCaptureBenchRun`, `TestBreakdownEndToEnd`, `TestBreakdownScrubBoundaries.test_cli_with_short_username_emits_intact_output`) | Mark every test that invokes `subprocess.run` as `slow` | `pyproject.toml:107` defines `slow` as "runs the benchmark harness or another multi-subprocess workload"; argparse flag validation exits in <0.2s without running benchmark workloads. | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` (3 test files) and `- Item-Dependencies: none` are unchanged; every revision (`PR-001` through `PR-004`) was swept across `## Goal`, the Mermaid diagram, `E-01..E-04`, `## Project conventions discovered`, `## Findings`, `## Proposed changes`, `## Required tests / validation`, `## Spec / documentation sync`, `V-01..V-04`, and `## Approval and execution gate` with zero remaining contradictions, open questions, or structural ambiguities. No second pass is needed.

AW-REVIEW: DONE
