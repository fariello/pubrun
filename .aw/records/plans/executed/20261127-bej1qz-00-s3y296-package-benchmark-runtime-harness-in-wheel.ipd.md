# IPD: Package benchmark runtime harness in wheel

- Date: 2026-11-27
- Kind: orchestrator
- Concern: Backlog item `bej1qz`: the `pubrun` wheel ships the `pubrun bench` command-line interface (CLI) subcommand in `src/pubrun/__main__.py`, but `pyproject.toml` excludes `benchmarks/` from the wheel. A `pip`-installed `pubrun` outside a Git source checkout exits with an error because `src/pubrun/__main__.py::_find_bench_harness` cannot find `benchmarks/harness.py`, and `src/pubrun/__main__.py` maintains a duplicated share-safety fallback (`_verify_redacted`) because `benchmarks/share_safety.py` is not packaged.
- Scope: Coordination of five child plans for Set `bej1qz`: `29nsim` (package core benchmark runtime modules and workloads under `src/pubrun/_bench/` with checkout shims), `c1zz3x` (package high-performance computing (HPC) submission scripts under `src/pubrun/_bench/scripts/` with checkout shims), `mfeptf` (wire `src/pubrun/__main__.py` to the packaged runtime, writable default output directory, and single-source share-safety validator, and migrate `tests/test_bench_command.py::TestSubmissionVerifier` to `_share_check` so tests stay green when `_verify_redacted` is deleted), `cuboum` (update documentation across `docs/`, `benchmarks/README.md`, and `README.md`), and `1r585o` (update remaining benchmark tests, add non-checkout, output-dir, HPC command-generation, and wheel tests, update Continuous Integration (CI) packaging checks, and execute whole-Set acceptance verification). This orchestrator modifies no product code, scripts, tests, CI configuration, or documentation.
- Scope-Paths: .aw/records/plans/pending/20261127-bej1qz-00-s3y296-package-benchmark-runtime-harness-in-wheel.ipd.md
- Item-Dependencies: executed:29nsim, executed:c1zz3x, executed:mfeptf, executed:cuboum, executed:1r585o
- Status: executed
- Readiness: go-pending-approval
- Review-Depth: orchestrator
- Coverage: pass
- Coverage-Fingerprint: d81c6ad612243a69fff0b27866910bd7a44f6ab5ab9fa8e69fb098b689827407
- Coverage-Checked: 2026-11-27 by uri/its_direct/pt3-claude-opus-5.5-1m-us
- Short-Description: Orchestrate packaging the benchmark runtime harness into the pubrun wheel so pip-installed pubrun bench works without a source checkout
- Work-Kind: bug
- Priority: high
- From-Backlog: bej1qz
- Blocks-Release: g2qtg5
- Set: bej1qz
- Order: 0
- Highest E allocated: 05
- Author: Antigravity
- Id: s3y296

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-27 executed (aw agy run model=Gemini-4-Neon-High): RETIRED as the orchestrator rollup step of a runner Set completion, not executed by an agent: every child of Set bej1qz reached executed, so the runner (run run-20261127T062324Z-2230927) retired this Order-0 plan as bookkeeping. Its own E-*/V-* items were NOT performed; the runner superseded them by enforcing the ordering, the isolation and the per-child merge gate. Justifying children: 29nsim, c1zz3x, mfeptf, cuboum, 1r585o.
- 2026-11-27 approved (aw set): status set to approved
- 2026-11-27 coverage pass (aw oc run): fingerprint d81c6ad61224, model uri/its_direct/pt3-claude-opus-5.5-1m-us
- 2026-11-27 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004; review record `.aw/records/reviews/20261127-bej1qz-00-s3y296-package-benchmark-runtime-harness-in-wheel.review.md`.
- 2026-11-27 to-review (aw set): demoted approved -> to-review: APPROVAL WITHDRAWN: Demote to to-review so /plan-review writes Readiness attestations before execution
- 2026-11-27 approved (aw set): status set to approved
- 2026-11-27 to-review (aw set): Authored review-ready orchestrator plan from backlog item bej1qz
- 2026-11-27 coverage pass (aw oc run): fingerprint 40208be506de, model uri/its_direct/pt3-claude-opus-5.5-1m-us
- 2026-11-27 draft (Antigravity): created.

## Goal

Deliver all requirements and acceptance criteria of backlog item `bej1qz` (status `graduated`) through five right-sized child plans so a user who installs `pubrun` from a wheel can run `pubrun bench` from any working directory without a source checkout, while keeping non-runtime benchmark artifacts out of the wheel and keeping direct source-checkout invocations working.

### Set dependency architecture

```mermaid
flowchart TD
    C1["01 29nsim: Package core runtime and checkout shims"]
    C2["02 c1zz3x: Package HPC submit scripts and checkout shims"]
    C3["03 mfeptf: Wire pubrun bench CLI, single-source share safety, and verifier tests"]
    C4["04 cuboum: Update documentation for packaged runtime"]
    C5["05 1r585o: Update tests, CI wheel checks, and run whole-Set verification"]
    ORCH["00 s3y296: Orchestrator retirement"]

    C1 --> C2
    C1 --> C3
    C2 --> C3
    C1 --> C4
    C2 --> C4
    C3 --> C4
    C1 --> C5
    C2 --> C5
    C3 --> C5
    C4 --> C5
    C1 --> ORCH
    C2 --> ORCH
    C3 --> ORCH
    C4 --> ORCH
    C5 --> ORCH
```

## Detailed Implementation Checklist (TODO)


> Its own E-*/V-* items were NOT performed; the runner superseded them by enforcing the ordering, the isolation and the per-child merge gate.

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Child plan execution confirmation

- [ ] E-01 CONFIRM 29nsim REACHED executed
  - Depends on: none
  - Expected outcome: `.aw/records/plans/executed/20261127-bej1qz-01-29nsim-package-benchmark-core-runtime-and-checkout-shims.ipd.md` exists with `- Status: executed`, all `E-*` items `performed`, and all `V-*` items `pass`.
  - Execution state: pending

- [ ] E-02 CONFIRM c1zz3x REACHED executed
  - Depends on: E-01
  - Expected outcome: `.aw/records/plans/executed/20261127-bej1qz-02-c1zz3x-package-hpc-submission-scripts-and-checkout-shims.ipd.md` exists with `- Status: executed`, all `E-*` items `performed`, and all `V-*` items `pass`.
  - Execution state: pending

- [ ] E-03 CONFIRM mfeptf REACHED executed
  - Depends on: E-01, E-02
  - Expected outcome: `.aw/records/plans/executed/20261127-bej1qz-03-mfeptf-wire-pubrun-bench-cli-to-packaged-runtime-and-single-source.ipd.md` exists with `- Status: executed`, all `E-*` items `performed`, and all `V-*` items `pass`.
  - Execution state: pending

- [ ] E-04 CONFIRM cuboum REACHED executed
  - Depends on: E-01, E-02, E-03
  - Expected outcome: `.aw/records/plans/executed/20261127-bej1qz-04-cuboum-update-benchmark-documentation-for-packaged-wheel-runtime.ipd.md` exists with `- Status: executed`, all `E-*` items `performed`, and all `V-*` items `pass`.
  - Execution state: pending

- [ ] E-05 CONFIRM 1r585o REACHED executed
  - Depends on: E-01, E-02, E-03, E-04
  - Expected outcome: `.aw/records/plans/executed/20261127-bej1qz-05-1r585o-add-benchmark-packaging-tests-ci-checks-and-end-to-end-verif.ipd.md` exists with `- Status: executed`, all `E-*` items `performed`, and all `V-*` items `pass`.
  - Execution state: pending

## Child IPDs, sequence, and dependencies

| Order | Id | File | What it does | Depends on |
|---|---|---|---|---|
| 01 | `29nsim` | `20261127-bej1qz-01-29nsim-package-benchmark-core-runtime-and-checkout-shims.ipd.md` | Package standard-library benchmark core (`__init__.py`, `harness.py`, `scenarios.py`, `share_safety.py`, `workloads/`) under `src/pubrun/_bench/` and keep auto-start-safe, monkeypatch-transparent `benchmarks/` shims and `benchmarks/startup_breakdown.py` working. | none |
| 02 | `c1zz3x` | `20261127-bej1qz-02-c1zz3x-package-hpc-submission-scripts-and-checkout-shims.ipd.md` | Package Slurm, PBS, LSF, and SGE benchmark submission scripts under `src/pubrun/_bench/scripts/` using `import pubrun.minimal, pubrun._bench.harness` preflight, `python -m pubrun._bench.harness`, and explicit absolute `PUBRUN_RESULTS_DIR`, and keep `benchmarks/` script shims (including Slurm-spooled `run_bench.sbatch`) working. | 01 |
| 03 | `mfeptf` | `20261127-bej1qz-03-mfeptf-wire-pubrun-bench-cli-to-packaged-runtime-and-single-source.ipd.md` | Wire `src/pubrun/__main__.py` (`pubrun bench`) to resolve `src/pubrun/_bench/` first, choose a writable default results directory outside a checkout, pass explicit `PUBRUN_RESULTS_DIR` and `PUBRUN_UNREDACTED` to HPC scripts, replace `_load_share_safety`/`_verify_redacted` with direct `pubrun._bench.share_safety.check_share_safe_text`, and migrate `tests/test_bench_command.py::TestSubmissionVerifier` to `_share_check`. | 01, 02 |
| 04 | `cuboum` | `20261127-bej1qz-04-cuboum-update-benchmark-documentation-for-packaged-wheel-runtime.ipd.md` | Update `docs/cli.md`, `docs/performance.md`, `benchmarks/README.md`, `docs/hpc.md`, `docs/functional_spec.md`, and `README.md` to remove source-checkout requirements for `pubrun bench` and document the packaged runtime, writable default output directory, `${ANON_ID}` filename pattern, and redacted-only HPC script defaults. | 01, 02, 03 |
| 05 | `1r585o` | `20261127-bej1qz-05-1r585o-add-benchmark-packaging-tests-ci-checks-and-end-to-end-verif.ipd.md` | Update remaining tests in `tests/test_bench_command.py` and `tests/test_benchmark_intake_bugs.py`, add wheel/non-checkout, writable-output, HPC-script, and single-source `share_safety` tests, update `.github/workflows/ci.yml` wheel checks (16 required files, 10 forbidden paths, `--no-deps`, per-label clean-venv smoke runs), and run the whole-Set end-to-end wheel and test verification suite. | 01, 02, 03, 04 |

## Completion criteria (the whole Set is done only when)

- The Python standard-library benchmark runtime (`__init__.py`, `harness.py`, `scenarios.py`, `share_safety.py`, and `workloads/`) is packaged under `src/pubrun/_bench/` with zero new runtime dependencies, and direct source-checkout invocations of `benchmarks/harness.py`, `benchmarks/share_safety.py`, `benchmarks/scenarios.py`, `benchmarks/workloads/`, and `benchmarks/startup_breakdown.py` continue to work without unintended `pubrun` auto-start. Owner: `29nsim`.
- All five HPC scheduler scripts (`run_bench.sbatch`, `submit_bench.sh`, `submit_bench_pbs.sh`, `submit_bench_lsf.sh`, `submit_bench_sge.sh`) plus `__init__.py` are packaged under `src/pubrun/_bench/scripts/`, invoke `python -m pubrun._bench.harness` with an explicit absolute writable `PUBRUN_RESULTS_DIR` instead of `$PUBRUN_REPO/benchmarks/harness.py`, and retain working checkout shims under `benchmarks/` (including spooled `benchmarks/run_bench.sbatch`). Owner: `c1zz3x`.
- `src/pubrun/__main__.py` resolves the packaged `pubrun._bench` runtime first without requiring a source checkout, defaults to a writable `./pubrun-bench-results/` directory outside a checkout (preserving `benchmarks/results/` inside a checkout), passes explicit `PUBRUN_RESULTS_DIR`, `PUBRUN_UNREDACTED`, and packaged script paths on HPC submission, and imports `pubrun._bench.share_safety.check_share_safe_text` directly with `_load_share_safety` and `_verify_redacted` removed (with `tests/test_bench_command.py::TestSubmissionVerifier` migrated to `_share_check`). Owner: `mfeptf`.
- `docs/cli.md`, `docs/performance.md`, `benchmarks/README.md`, `docs/hpc.md`, `docs/functional_spec.md`, and `README.md` accurately describe wheel-installed `pubrun bench` execution, the default writable output directory, and packaged HPC scripts with no stale "requires a source checkout" claim and no added em or en dashes. Owner: `cuboum`.
- Installing the built wheel (`dist/pubrun-*.whl`) into a clean temporary virtual environment (with `--no-deps` on Python 3.11+) and running `pubrun bench --quick --local` from a temporary directory outside any `pubrun` source checkout exits `0` and writes a share-safe redacted JavaScript Object Notation (JSON) file whose path is printed to the user; `python3 -m twine check --strict dist/*` passes; the wheel includes all 16 `pubrun/_bench/` runtime files and contains none of `benchmarks/results/`, `benchmarks/data/`, `.aw/`, or non-runtime benchmark scripts/tests (`test_benchmarks.py`, `test_share_safety.py`); `python benchmarks/harness.py --quick` passes inside a checkout; automated tests cover wheel/non-checkout execution, default writable output directory selection, HPC submit script command generation without a checkout, and single-source `share_safety` validation; `.github/workflows/ci.yml` guards both `direct` and `from-sdist` wheels in isolated per-label working directories; and `tests/test_bench_command.py`, `benchmarks/test_benchmarks.py`, full `pytest` with coverage, three-platform `mypy`, and path-leak sanitization all pass. Owner: `1r585o`.

## Cross-IPD validation

- Scope-path serialization: `mfeptf` (Order 03) and `1r585o` (Order 05) both modify `tests/test_bench_command.py` (`mfeptf` migrates `TestSubmissionVerifier` immediately when deleting `_verify_redacted`; `1r585o` depends on `executed:mfeptf` and updates the remaining legacy classes and adds new test classes), so `pytest tests/` remains green at every commit with zero concurrent conflict; all other Scope-Paths across `29nsim`, `c1zz3x`, `mfeptf`, `cuboum`, and `1r585o` are pairwise disjoint or strictly serialized (`29nsim` -> `c1zz3x` for `src/pubrun/_bench/scripts`).
- `1r585o` verifies that the wheel built from the combined changes of `29nsim`, `c1zz3x`, `mfeptf`, and `cuboum` contains all 16 packaged runtime files (`pubrun/_bench/` modules, workloads, and HPC scripts) and excludes all 10 non-runtime benchmark artifacts (`benchmarks/results/`, `benchmarks/data/`, `plot.py`, `aggregate.py`, `pull_submissions.py`, `startup_breakdown.py`, `package_capture_bench.py`, `test_benchmarks.py`, `test_share_safety.py`, and `.aw/`), and that the sdist excludes `.aw/`.
- `1r585o` verifies end-to-end wheel installation in a clean temporary virtual environment with zero extra dependencies installed on Python 3.11+, confirming `pubrun bench --quick --local` exits `0` outside any checkout, prints `"SAFE TO SUBMIT"`, `"PASSED"`, and the output path, creates no `runs/` directory, and writes a share-safe redacted JSON file to `./pubrun-bench-results/`.
- `1r585o` verifies that checkout compatibility (`python benchmarks/harness.py --quick`, `.github/scripts/validate_benchmark_submission.py` via `benchmarks/share_safety.py`, `benchmarks/test_benchmarks.py`, `benchmarks/test_share_safety.py`, and `benchmarks/submit_bench*.sh`) stays green alongside the packaged runtime.
- `1r585o` verifies repository-wide quality gates across all modified modules: `pytest tests/ -p randomly --cov=src --cov-fail-under=78`, `mypy` on Linux, `win32`, and `darwin`, `tests/test_report_subpackage_integrity.py`, and `python3 scripts/sanitize_paths.py --check --all`.

## Deferred / out of scope (with reason)

- Packaging non-runtime analysis, plotting, archival, or micro-benchmark tooling (`benchmarks/results/`, `benchmarks/data/`, `benchmarks/plot.py`, `benchmarks/aggregate.py`, `benchmarks/pull_submissions.py`, `benchmarks/startup_breakdown.py`, `benchmarks/package_capture_bench.py`, `benchmarks/test_*.py`) into the wheel is explicitly excluded by backlog item `bej1qz` requirement 2 to keep the wheel lightweight and zero-dependency.
  - Carrier-Declined: Exclusion is an explicit requirement of backlog item `bej1qz`; no follow-up is wanted.
- Live execution of Portable Batch System (PBS), Load Sharing Facility (LSF), or Sun Grid Engine (SGE) submission scripts against real cluster schedulers is out of scope in CI because no live PBS/LSF/SGE scheduler exists in the test environment; `1r585o` validates script invocation and argument handling with stub scheduler binaries.
  - Carrier-Declined: Hardware/cluster environment boundary; stub-scheduler verification covers script contract behavior deterministically.

## Scope check

- Over-scope: none. Every child plan maps directly to requirements 1 through 8 and the five acceptance criteria of backlog item `bej1qz`, plus consistency updates in `docs/hpc.md`, `docs/functional_spec.md`, `README.md`, and `.github/workflows/ci.yml` so no stale checkout-only claim or unguarded wheel packaging regression remains.
- Under-scope: none. Every requirement and acceptance criterion in backlog item `bej1qz` is assigned to an explicit child plan in `## Child IPDs, sequence, and dependencies`.

## Required tests / validation

This orchestrator executes no commands directly. Each child runs its own targeted checks during execution (`29nsim`, `c1zz3x`, `mfeptf`, `cuboum`), and child `1r585o` executes the whole-Set acceptance and regression suite: wheel and sdist build, `twine check --strict`, sdist/wheel content inspection (16 required `_bench` files, 10 forbidden paths, `.aw/` excluded), clean virtual-environment non-checkout `pubrun bench --quick --local` (`--no-deps` on Python 3.11+), source-checkout `python benchmarks/harness.py --quick`, `pytest` (including `tests/test_bench_command.py`, `tests/test_benchmark_intake_bugs.py`, `benchmarks/test_benchmarks.py`, `benchmarks/test_share_safety.py`, `.github/scripts/`, and `--cov=src --cov-fail-under=78`), three-platform `mypy`, and `scripts/sanitize_paths.py --check --all`.

## Open questions

None. All design choices (internal package location `src/pubrun/_bench/`, non-checkout default directory `./pubrun-bench-results/`, checkout shim preservation, and single-source `share_safety`) are established by backlog item `bej1qz` and verified repository conventions.

## Validation and cross-check (verify before reporting the Set complete)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition)—as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction—name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-bej1qz-01-29nsim-package-benchmark-core-runtime-and-checkout-shims.ipd.md` exists, carries `- Status: executed`, has all `E-*` performed and all `V-*` passed, and passes `aw ipd lint --phase post-transition`.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-bej1qz-02-c1zz3x-package-hpc-submission-scripts-and-checkout-shims.ipd.md` exists, carries `- Status: executed`, has all `E-*` performed and all `V-*` passed, and passes `aw ipd lint --phase post-transition`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-bej1qz-03-mfeptf-wire-pubrun-bench-cli-to-packaged-runtime-and-single-source.ipd.md` exists, carries `- Status: executed`, has all `E-*` performed and all `V-*` passed, and passes `aw ipd lint --phase post-transition`.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-bej1qz-04-cuboum-update-benchmark-documentation-for-packaged-wheel-runtime.ipd.md` exists, carries `- Status: executed`, has all `E-*` performed and all `V-*` passed, and passes `aw ipd lint --phase post-transition`.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-bej1qz-05-1r585o-add-benchmark-packaging-tests-ci-checks-and-end-to-end-verif.ipd.md` exists, carries `- Status: executed`, has all `E-*` performed and all `V-*` passed, and passes `aw ipd lint --phase post-transition`.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

1. **Preconditions:** Retire this orchestrator only after it carries `- Status: approved`, all blocking open questions are resolved, and all five child plans (`29nsim`, `c1zz3x`, `mfeptf`, `cuboum`, `1r585o`) have reached `executed` on disk and pass `aw ipd lint`.
2. **Scope declaration:** `- Scope-Paths:` declares only this orchestrator file (`.aw/records/plans/pending/20261127-bej1qz-00-s3y296-package-benchmark-runtime-harness-in-wheel.ipd.md`); this orchestrator modifies no product code, scripts, tests, CI configuration, or documentation. Any scope deviation at manual finalization must be justified explicitly with `--scope-reason` or `--scope-ack`.
3. **Validation honesty:** Every `V-*` item MUST record actual pasted verification output (`aw ipd lint --phase post-transition` and executed-child status confirmation) before marking `pass` in a manual retirement; never claim completion from memory.
4. **Commit and push discipline:** Commit only explicit orchestrator paths through `aw commit`. Never use `git add -A`, bare `git add .`, or raw `git commit`, and never push, tag, or publish a release without explicit human authorization.
5. **Lifecycle transition:** After all five child plans reach `executed` on disk, this orchestrator MUST complete the post-gate transition to `.aw/records/plans/executed/`. When executing under an automated runner (`aw oc run` or `aw agy run`), leave orchestrator retirement to the runner's automated retirement step (after the coverage and lint gates clear); in a manual retirement outside a runner, run `aw ipd lint --phase pre-transition` and `aw ipd finalize s3y296` (never hand-roll `git mv` to `executed/`).
