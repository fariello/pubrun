# Review findings: ipd 4eo4z2

- Subject-Id: 4eo4z2
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-bt-09-4eo4z2-ci-packaging-wheel-bench-enforcement-workflow-security-scan.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` (`conforming`). Expanded acronyms (`CI`, `CLI`, `TUI`) on first use, standardized full repo-relative `path::Symbol` citations, added a Mermaid `flowchart LR` summarizing the 8-file multi-stage workflow/hygiene scope (Req 12), replaced `N/A.` with a substantiated `Not applicable.` in `## Spec / documentation sync`, and completed all 5 execution-contract clauses in `## Approval and execution gate` (`PR-004`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `### CI, workflow security, and test hygiene scope` | Plan had no Mermaid diagram despite modifying 8 related CI, workflow-script, tox, example, and test files across a multi-stage dependency flow | Added `flowchart LR` linking `E-01` through `E-05` | Satisfy technical writing standard Req 12(a)/(b) (`PR-004`) |
| `- Scope:`, `- Scope-Paths:`, `## Goal`, `E-02`, `## Findings` (`TEST-I5`), `## Proposed changes`, `V-02` | Assigned `TEST-I5` collection-time `sys.path`/`sys.modules` mutation to `.github/scripts/test_benchmark_intake_workflow.py` (which performs zero `sys.path`/`sys.modules` mutations) | Added `.github/scripts/test_extract_attachment_url.py` and `.github/scripts/test_validate_benchmark_submission.py` to `- Scope-Paths:` and scoped `TEST-I5` cleanup to those two files via module-scoped fixtures and `try/finally` snapshot/restore | Fix wrong target file for `TEST-I5` (`PR-001`) |
| `E-01`, `E-03`, `## Project conventions discovered`, `## Required tests / validation` | Ran bare `pytest` in `packaging` without installing `pytest`, relied on `-rs` (which still exits `0` on skip), passed unexpanded glob `benchmarks/test_*.py` in `tox.ini`, and left the CI job for `examples/verify_all.py` unnamed | Specified `pip install build twine pytest` and `PUBRUN_REQUIRE_WHEEL_TEST: "1"` with `python -m pytest` in `packaging` (paired with `pytest.fail` guard + fast unit test in `E-03`), assigned `examples/verify_all.py` to `extra-suites`, and specified `extras = dev, tui` plus shell-glob-free `[testenv:extra]` in `tox.ini` | Prevent CI/tox execution failures and silent wheel-test skips (`PR-002`) |
| `E-01`, `E-02`, `E-03`, `## Required tests / validation` | Omitted `PUBRUN_*` stripping in `examples/verify_all.py`, omitted `if:` exclusion and `script:` coverage for `benchmark-intake.yml`, omitted selective `subprocess.run` stubbing for `mock_training.py` in `_run_tests()`, suggested Python 3.11-only bare `tomllib`, and left `test_bench_command.py` `not hasattr` tests unnamed | Specified `PUBRUN_*` stripping and empty subdir config isolation inside `tmp_dir`, stdlib + PyYAML `run:`/`script:` scanning ignoring `if:`, selective `subprocess.run` stubbing in `_run_tests()`, `from pubrun.config import tomllib`, and behavioral replacements for `test_duplicate_verifier_helpers_removed` and `test_no_auto_post_helpers_remain` | Eliminate runtime, security, and Python 3.8–3.10 compatibility traps (`PR-003`) |
| `## Spec / documentation sync`, `V-01..V-05`, `## Approval and execution gate` | Used `N/A.`, bare `pytest`, lacked `tests/test_compatibility.py -k workflow` check, lacked reachability/re-derivation wording in `V-*`, and omitted `--scope-reason`/`--scope-ack`, no `git add -A`/raw `git commit`, and conditional runner vs manual `aw ipd finalize` clauses | Replaced `N/A.` with verified `Not applicable.` citing `README.md`/`docs/research-use.md`/`docs/functional_spec.md`, switched to `python3 -m pytest`, added `tests/test_compatibility.py -k workflow` and Command 3 collection-cleanliness check, added reachability/re-derivation wording in `V-01..V-05`, and completed all 5 execution-contract clauses | Satisfy `technical-writing.md`, `r2-executability.md`, and `s7-finalize.md:31-46` (`PR-004`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-bt`, `- Order: 9`, `- Scope-Paths:` (6 originally; corrected to 8 after adding `.github/scripts/test_extract_attachment_url.py` and `.github/scripts/test_validate_benchmark_submission.py`), 5 E-items in 3 task groups, `- Priority: high`, no `.spec.md` file.

1. Yes: updates `.github/workflows/ci.yml` (verified by `tests/test_compatibility.py`) and `tox.ini` (the contributor test runner contract), though no `.spec.md` or `src/pubrun/` public API changes.
2. Yes: updates `.github/scripts/test_benchmark_intake_workflow.py`, which enforces the security boundary against attacker-controlled GitHub issue shell-injection in `.github/workflows/benchmark-intake.yml`.
3. Yes: spans 8 files across CI workflows, workflow security/intake tests, `tox.ini`, example verification, and CLI/bench test suites in 3 task groups inside 10-child Set `assess-bt`.
4. Yes: `- Scope-Paths:` explicitly lists all 8 modified files.
5. Yes: a broken `packaging` step (calling uninstalled `pytest`) or broken `tox.ini` command (`benchmarks/test_*.py` literal glob) breaks CI/tox across all PRs, and an incomplete workflow scanner could miss shell injection in `benchmark-intake.yml`.

AW-TIER: complex

### Step R1

- Checked: every file, workflow, script, config, and test referenced by `4eo4z2` against the repository:
  - `.github/workflows/ci.yml`: `test` (L13-44), `extra-suites` (L46-61), `no-tui` (L63-81), `packaging` (L83-234; `pip install build twine` at L96, zero `pytest` installation or invocation), `typecheck` (L235-256).
  - `.github/workflows/benchmark-intake.yml`: job-level `if:` referencing `github.event.issue.body` (L29-31), single-line `run:` (L57), multi-line `run: |` blocks (L64-68, L73-76), and `actions/github-script` `script: |` blocks (L44-51, L84-158).
  - `.github/scripts/test_benchmark_intake_workflow.py` (L1-101; zero `sys.path`/`sys.modules` mutations; L66-78 checks only single lines starting with `python3` or `run:` for `github.event.issue.body`).
  - `.github/scripts/test_extract_attachment_url.py` (L10-17 module-level `sys.modules["extract_attachment_url"] = x`; L79-90 uncleaned `sys.modules["validate_benchmark_submission"] = v`), `.github/scripts/test_validate_benchmark_submission.py` (L19-25 module-level `sys.modules["validate_benchmark_submission"] = v`), and `.github/scripts/validate_benchmark_submission.py` (L60-62 `sys.path.insert(0, str(_REPO / "benchmarks"))` + `import share_safety`).
  - `tox.ini` (L1-8), `pyproject.toml` (L15 `requires-python = ">=3.8"`, L41 `tomli`, L50-51 `pubrun`/`pbr` scripts, L53-69 `dev`/`tui`/`bench` extras, L98-108 `pytest` options).
  - `examples/verify_all.py` (L17-103) and imports across `examples/*.py` and `examples/minimal-research-workflow/analysis.py` (100% stdlib + `pubrun`).
  - `src/pubrun/config.py::get_global_config_dir` (L62-77) and `tomllib` shim (L11-19); `src/pubrun/_config_boot.py::_global_config_dir` (L44-54) and `resolve_import_mode` (L158-192).
  - `src/pubrun/__main__.py::_share_check` (L1716-1730), `_run_bench` (L2211-2255), and `_run_tests` (L2836-2921).
  - `tests/test_bench_command.py`: `test_duplicate_verifier_helpers_removed` (L487-492), `test_no_auto_post_helpers_remain` (L637-642), `TestWheelNonCheckoutBench` (L1245-1387).
  - `tests/test_cli.py`: `TestCliRunTests.test_run_tests_exits_zero` (L668-681), `TestCliNewFeatures.test_pbr_alias_registered_in_pyproject` (L1338-1342).
  - `tests/test_compatibility.py` (L137-223, verifying `.github/workflows/ci.yml` structure and PyYAML parse).
  - `README.md`, `docs/research-use.md`, `docs/functional_spec.md` (verified zero documentation changes needed).
- Verified: empirically ran `python3 -m pytest --collect-only -q benchmarks/ .github/scripts/` (93 tests collected cleanly, confirming `benchmarks/` contains only `test_benchmarks.py`, `test_pull_submissions.py`, and `test_share_safety.py`). Uncovered and fixed all citation, scope, runtime, and compatibility defects (`PR-001` through `PR-004`).

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Scope-Paths:` completeness (updated to 8 files), `- Item-Dependencies: none`, runtime-demonstration reachability in `V-02`/`V-04`/`V-05`, execution-time re-derivation (`r2-executability.md:65`), and the 5-clause execution contract in `## Approval and execution gate`.
- Verified: `PR-001` through `PR-004` closed every structural, scope, reachability, and execution-contract gap.

### Step R3

- Checked: full security and privacy rubric (`r3-security.md` B).
- Verified: `E-02` closes a real CI workflow-injection detection blind spot (`TEST-I2`) by parsing multi-line `run:` and `script:` blocks (both stdlib and PyYAML) without false-positiving on `jobs.validate.if:` and by adding negative regression tests; `E-01` keeps `examples/verify_all.py` isolated from host `~/.config/pubrun/config.toml` and ambient `PUBRUN_*` variables; `E-03` preserves the fail-closed no-transmit privacy guarantee for `--submit-file` / `--prepare-submission` via behavioral assertions rather than fragile private-attribute checks.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified:
  - A/C/D: installing `pytest` in `packaging` without `pip install -e .` preserves clean wheel isolation; `PUBRUN_REQUIRE_WHEEL_TEST=1` makes CI fail closed on missing `build` without breaking local devs without `build`; `tox.ini` avoids shell-less glob breakage by passing `benchmarks/` and `.github/scripts/` in `[testenv:extra]`; `from pubrun.config import tomllib` preserves Python 3.8–3.10 compatibility; selective `subprocess.run` stubbing in `TestCliRunTests` keeps `mock_training.py` manifest validation intact.
  - E: Commands 1, 2, and 3 validate randomized tests, CI workflow compatibility (`tests/test_compatibility.py -k workflow`), `ci.yml` YAML parsing, `tox.ini` config parsing, hostile-config + hostile-`PUBRUN_*` `examples/verify_all.py` execution, and clean `.github/scripts/` collection import state.
  - Right-sizing: 5 E-items in 3 task groups across 8 Scope-Paths; each E-item is cohesive and executable in one focused pass.
  - `## Spec / documentation sync`: verified and substantiated against `README.md`, `docs/research-use.md`, and `docs/functional_spec.md`.

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught `TEST-I5` targeting the wrong `.github/scripts/` file (`PR-001`), missing `pytest` in `packaging` (`PR-002`), and blanket-stub pitfall in `_run_tests()` (`PR-003`).
  2. Testing and regression: replaced private `not hasattr` checks with real behavioral delegation and no-transmit tests (zero code-pinning), added `tests/test_compatibility.py -k workflow` and `SCRIPTS_COLLECTION_CLEAN_OK` checks, and noted offline `hatchling` isolation behavior honestly.
  3. UI / UX: verified `examples/verify_all.py` remains immune to developer `~/.config/pubrun/config.toml` and ambient `PUBRUN_*` env vars.
  4. Architect: verified clean separation between `[testenv]` (`dev, tui`) and `[testenv:extra]` (`dev, bench` + `pyyaml`) in `tox.ini` and zero editable-install pollution in `packaging`.
  5. Software engineer: caught Python 3.8–3.10 `tomllib` incompatibility (`from pubrun.config import tomllib`), shell-less glob failure in `tox.ini`, and `benchmark-intake.yml` `if:` exclusion (`PR-002`, `PR-003`).
  6. Power user: verified `tox -e extra` gives contributors a single command mirroring CI's `extra-suites`.
  7. Novice: added Mermaid overview diagram, expanded acronyms on first use, and named every concrete test/function target in `E-01..E-03`.
  8. Stakeholder: confirmed complete coverage of `TEST-I1`, `TEST-I2`, `TEST-I5` (`.github/scripts/`), `TEST-I8` (`test_bench_command.py`, `test_cli.py`), `TEST-I9`, and `TEST-U3` assigned by orchestrator `n6250e`.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-05` (5 E-items, 3 task groups, 8 Scope-Paths, already Order 09 of 10-child Set `assess-bt`).
- Confirmed: 8 Scope-Paths and 5 E-items sit cleanly within the right-sizing guideline (`<= 5` E-items, `<= 8` Scope-Paths), with each E-item grouping closely coupled deliverables (`E-01` CI/tox/examples, `E-02` `.github/scripts/`, `E-03` `test_cli.py`/`test_bench_command.py`, `E-04`/`E-05` validation). No split is warranted.

### Step R7

- Checked: cross-plan consistency across Set `assess-bt` (orchestrator `n6250e` and sibling children `wcjdbu`, `ndobra`, `thbepl`, `qum7gf`, `kk83rk`, `n39jh9`, `dqaj9a`, `kgoymu`, `37sth0`).
- Verified: adding `.github/scripts/test_extract_attachment_url.py` and `.github/scripts/test_validate_benchmark_submission.py` to `4eo4z2`'s `- Scope-Paths:` keeps all 10 children in Set `assess-bt` 100% file-disjoint; `n6250e`'s `## Child IPDs` row for `4eo4z2` already assigns `TEST-I5 (.github/scripts/)` to `4eo4z2` (note for `n6250e`'s own review: `n6250e` line 7 lists `.github/scripts/test_benchmark_intake_workflow.py` and can be widened to `.github/scripts/`); `E-01`'s edits to `.github/workflows/ci.yml` preserve every assertion in sibling `37sth0`'s `tests/test_compatibility.py`; `- Item-Dependencies: none` remains valid.

### Step S5

- Checked: `## Open questions` contains `None.`. All four findings (`PR-001` through `PR-004`) had `Low` overall Remediation Risk, were settled directly by repository evidence and documented workflow policy, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r1-references.md` / `r2-executability.md` | `.aw/records/plans/pending/20261127-assess-bt-09-4eo4z2-ci-packaging-wheel-bench-enforcement-workflow-security-scan.ipd.md:6-7,45,48,89` vs `.github/scripts/test_benchmark_intake_workflow.py:1-101`, `.github/scripts/test_extract_attachment_url.py:10-17,79-90`, `.github/scripts/test_validate_benchmark_submission.py:19-25`, `.github/scripts/validate_benchmark_submission.py:60-62` | `TEST-I5` targeted `.github/scripts/test_benchmark_intake_workflow.py`, which performs zero `sys.path`/`sys.modules` mutations; the actual `.github/scripts/` import-state leaks live in `.github/scripts/test_extract_attachment_url.py` and `.github/scripts/test_validate_benchmark_submission.py` (which were omitted from `- Scope-Paths:`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `.github/scripts/test_extract_attachment_url.py` and `.github/scripts/test_validate_benchmark_submission.py` to `- Scope-Paths:` and `- Scope:`, and updated `E-02`, `## Goal`, `## Findings`, `## Proposed changes`, `## Required tests / validation`, and `V-02` to isolate `sys.path`/`sys.modules` in those two files (recommendation strength: `very strong`). |
| PR-002 | HIGH | IN-SCOPE | `r2-executability.md` / `r4-engineering.md` A, C, E | `.aw/records/plans/pending/20261127-assess-bt-09-4eo4z2-ci-packaging-wheel-bench-enforcement-workflow-security-scan.ipd.md:36-40,58` vs `.github/workflows/ci.yml:83-101,46-61`, `tox.ini:1-8`, `tests/test_bench_command.py::TestWheelNonCheckoutBench:1245-1254`, `tests/test_compatibility.py:145-156,193-208` | `.github/workflows/ci.yml` `packaging` never installs `pytest` and `-rs` alone still exits `0` on skip; `tox.ini` does not expand shell globs (`benchmarks/test_*.py` would fail); and `E-01` left which CI job runs `examples/verify_all.py` unspecified. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified `pip install build twine pytest` and `PUBRUN_REQUIRE_WHEEL_TEST: "1"` + `python -m pytest` in `packaging` (with `pytest.fail` guard and fast unit test in `E-03`), assigned `examples/verify_all.py` to `extra-suites`, and specified `extras = dev, tui` plus shell-glob-free `[testenv:extra]` in `tox.ini` (recommendation strength: `very strong`). |
| PR-003 | HIGH | IN-SCOPE | `r2-executability.md` / `r3-security.md` / `r4-engineering.md` A, D, E | `.aw/records/plans/pending/20261127-assess-bt-09-4eo4z2-ci-packaging-wheel-bench-enforcement-workflow-security-scan.ipd.md:39,46-47,56-58` vs `examples/verify_all.py:33-48`, `.github/workflows/benchmark-intake.yml:29-31,53-78`, `src/pubrun/__main__.py::_run_tests:2836-2921`, `tests/test_cli.py:668-681,1338-1342`, `tests/test_bench_command.py:487-492,637-642`, `pyproject.toml:15,41` | `examples/verify_all.py` lacked `PUBRUN_*` env stripping; `E-02` omitted `if:` exclusion and `script:` block scanning; `E-03` omitted selective `subprocess.run` stubbing for `_run_tests()`'s `mock_training.py` subprocess, suggested Python 3.11-only bare `tomllib`, and left both `not hasattr` tests in `tests/test_bench_command.py` unnamed without behavioral replacements. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified `PUBRUN_*` stripping + temp config dir in `examples/verify_all.py`, stdlib + PyYAML `run:`/`script:` scanning ignoring `if:`, selective `subprocess.run` stubbing in `TestCliRunTests`, `from pubrun.config import tomllib` for Python 3.8–3.14 compatibility, and concrete behavioral replacements for both `not hasattr` tests (recommendation strength: `very strong`). |
| PR-004 | MEDIUM | IN-SCOPE | `p-proofread.md` / `r2-executability.md` / `s7-finalize.md` | `.aw/records/plans/pending/20261127-assess-bt-09-4eo4z2-ci-packaging-wheel-bench-enforcement-workflow-security-scan.ipd.md:26-29,113-139,148-182` vs `.aw/system/workflows/technical-writing/technical-writing.md:29,40-46`, `.aw/system/workflows/plan-review/steps/r2-executability.md:65,71`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46` | Plan lacked a Mermaid diagram for its 8-file multi-stage workflow scope (Req 12), used unsubstantiated `N/A.`, used bare `pytest` without `tests/test_compatibility.py -k workflow`, omitted reachability/re-derivation wording in `V-01..V-05`, and omitted required execution-contract clauses in `## Approval and execution gate`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added Mermaid `flowchart LR`, expanded acronyms, substantiated `Not applicable.` in `## Spec / documentation sync`, switched to `python3 -m pytest` + `tests/test_compatibility.py -k workflow` + Command 3, added reachability/re-derivation wording in `V-01..V-05`, and completed all 5 execution-contract clauses (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `4eo4z2` | `complex` | `standard` | Touches `.github/workflows/ci.yml`, `tox.ini`, and `.github/scripts/test_benchmark_intake_workflow.py` (CI security gate) across 8 Scope-Paths in 10-child Set `assess-bt`; answers Yes to tier questions 1, 2, 3, and 5 (`steps/t-tier.md`). | yes |
| D-2 | How to enforce non-skipping of `TestWheelNonCheckoutBench` in CI `packaging` (`PR-002`) | Add `pytest` to `packaging` (`pip install build twine pytest`) and fail closed in `TestWheelNonCheckoutBench` when `PUBRUN_REQUIRE_WHEEL_TEST == "1"` and `build` is missing, keeping `pytest.importorskip("build")` for local devs | Install `pip install -e ".[dev]"` in `packaging`, or parse `pytest -rs` stdout in bash | Installing `pytest` only avoids editable-install pollution of the runner Python in `packaging`; `PUBRUN_REQUIRE_WHEEL_TEST=1` works identically on `ubuntu-latest` and `windows-latest` and is unit-testable offline (`tests/test_bench_command.py:1245-1387`, `.github/workflows/ci.yml:83-101`). | yes |
| D-3 | Where to run `examples/verify_all.py` in `.github/workflows/ci.yml` and how to expose extra suites in `tox.ini` (`PR-002`) | Run `python examples/verify_all.py` in `jobs.extra-suites` (`ubuntu-latest`, Python 3.12), and in `tox.ini` add `tui` to `[testenv]` plus a dedicated `[testenv:extra]` using directory paths (`benchmarks/`, `.github/scripts/`) | Add `examples/verify_all.py` to the 21-cell `test` matrix or put `benchmarks/test_*.py` in `[testenv]` | All scripts in `examples/` are stdlib + `pubrun`; `extra-suites` is the dedicated single-runner Linux 3.12 verification job; `tox` does not expand shell globs and `benchmarks/` requires `[bench]` + `pyyaml` (`.github/workflows/ci.yml:46-61`, `tox.ini:1-8`). | yes |

### Step S6

- Checked: `- Scope-Paths:` changed during Round 1 (added `.github/scripts/test_extract_attachment_url.py` and `.github/scripts/test_validate_benchmark_submission.py` for `PR-001`). Per `steps/s6-rereview.md` Rule 1, a second re-review pass (Round 2) is required to verify the revised plan end-to-end.

AW-REVIEW: AGAIN

## Round 2

### Step P

- Checked: re-read the complete revised plan `.aw/records/plans/pending/20261127-assess-bt-09-4eo4z2-ci-packaging-wheel-bench-enforcement-workflow-security-scan.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Confirmed the Mermaid `flowchart LR` matches the text exactly, all acronyms are expanded on first use, all code citations use valid repo-relative `path::Symbol` anchors, and zero superseded wording from Round 1 remains (`benchmarks/test_*.py` is only mentioned explicitly as the anti-pattern to avoid).

### Step R1

- Checked: re-verified all 8 paths in `- Scope-Paths:` exist in the repository and all cited symbols (`examples/verify_all.py::main`, `.github/scripts/validate_benchmark_submission.py`, `src/pubrun/__main__.py::_run_tests`, `src/pubrun/__main__.py::_share_check`, `src/pubrun/__main__.py::_run_bench`, `src/pubrun/_bench/share_safety.py::check_share_safe_text`, `src/pubrun/config.py::tomllib`, `tests/test_cli.py::TestCliRunTests.test_run_tests_exits_zero`, `tests/test_cli.py::TestCliNewFeatures.test_pbr_alias_registered_in_pyproject`, `tests/test_bench_command.py::TestSubmissionVerifier.test_duplicate_verifier_helpers_removed`, `tests/test_bench_command.py::TestAttachFlowClient.test_no_auto_post_helpers_remain`, `tests/test_bench_command.py::TestWheelNonCheckoutBench`, `tests/test_compatibility.py::test_ci_workflow_compatibility_matrix_structural`, `tests/test_compatibility.py::test_workflows_pyyaml_crosscheck_when_available`) match current source.

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), 8-file `- Scope-Paths:` alignment across `- Scope:`, `## Scope check`, `E-01..E-03`, `V-01..V-03`, and `## Approval and execution gate` Clause 2, and full conformance with `aw ipd lint --phase review-finalize --agent` and `--citation-anchors`.

### Step R7

- Checked: re-verified the expanded 8-file `- Scope-Paths:` remains 100% file-disjoint from all nine sibling children in Set `assess-bt` (`wcjdbu`, `ndobra`, `thbepl`, `qum7gf`, `kk83rk`, `n39jh9`, `dqaj9a`, `kgoymu`, `37sth0`) and aligns cleanly with orchestrator `n6250e` (`E-09` and `## Child IPDs` row 09).

### Step S5

- Checked: `## Open questions` remains `None.`; zero new findings, zero unfixed or deferred findings, and zero human-decision questions exist after Round 1 revisions.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|

### Step S6

- Checked: Round 2 made zero edits to `E-*`/`V-*`, `- Scope-Paths:`, or `- Item-Dependencies:`, and found zero new issues, contradictions, or ambiguities. Ready to finalize (`Step S7`).

AW-REVIEW: DONE
