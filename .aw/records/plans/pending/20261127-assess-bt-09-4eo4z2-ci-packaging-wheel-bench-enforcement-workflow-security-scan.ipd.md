# IPD: CI packaging wheel bench enforcement workflow security scan and test hygiene

- Date: 2026-11-27
- Kind: child
- Concern: Close two High CI/security testing gaps (`TEST-I1`, `TEST-I2`), fix a dead subprocess monkeypatch in CLI tests (`TEST-U3`), and close `tox.ini`, `examples/verify_all.py`, and test-pinning hygiene gaps (`TEST-I5` `.github/scripts/`, `TEST-I8`, `TEST-I9`).
- Scope: Update `.github/workflows/ci.yml`, `.github/scripts/test_benchmark_intake_workflow.py`, `tox.ini`, `examples/verify_all.py`, `tests/test_bench_command.py`, and `tests/test_cli.py`.
- Scope-Paths: .github/workflows/ci.yml, .github/scripts/test_benchmark_intake_workflow.py, tox.ini, examples/verify_all.py, tests/test_bench_command.py, tests/test_cli.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Run TestWheelNonCheckoutBench and verify_all.py in CI, scan multi-line run blocks in benchmark-intake, update tox.ini, and fix dead CLI test monkeypatch
- Work-Kind: followup
- Priority: high
- Set: assess-bt
- Order: 9
- Highest E allocated: 05
- Author: Antigravity
- Id: 4eo4z2

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-27 to-review (Antigravity): Authored review-ready child IPD from `/assess testing` Slices 2 and 3 on HEAD `512ee68` / `8f2aacd`.
- 2026-11-27 draft (Antigravity): created.

## Goal

Ensure `TestWheelNonCheckoutBench` actually executes in CI (rather than silently skipping in every job), extend `.github/scripts/test_benchmark_intake_workflow.py` to detect shell-injection expressions inside multi-line `run: |` workflow blocks, run `examples/verify_all.py` with isolated user config in CI, update `tox.ini` to cover `tui` and extra suites, and replace the dead monkeypatch in `test_run_tests_exits_zero` and private/config-pinning assertions in `test_bench_command.py` and `test_cli.py`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Enforce wheel bench tests, workflow security scan, and example verification in CI

- [ ] E-01 Update `.github/workflows/ci.yml`, `tox.ini`, and `examples/verify_all.py` (`TEST-I1`, `TEST-I9`):
  - In `.github/workflows/ci.yml`, add a step in the `packaging` job (where `build` is already installed) that runs `pytest tests/test_bench_command.py -k TestWheelNonCheckoutBench -v` (or fails if skipped via a `-rs` / non-zero check) so the wheel-based `pubrun bench` verification never silently skips in CI.
  - In `.github/workflows/ci.yml`, add a step running `python examples/verify_all.py` in a Linux test job so example scripts are continuously verified.
  - In `examples/verify_all.py`, isolate `XDG_CONFIG_HOME` and `APPDATA` to a temporary directory before running example scripts so host user config cannot break verification.
  - In `tox.ini`, include the `tui` extra and expose/run the extra suites (`benchmarks/test_*.py`, `.github/scripts/`) alongside `tests/`.
  - Depends on: none
  - Expected outcome: CI runs `TestWheelNonCheckoutBench` and `examples/verify_all.py`; `examples/verify_all.py` is immune to host config; `tox.ini` reflects the full supported test surface.
  - Execution state: pending

- [ ] E-02 Extend `.github/scripts/test_benchmark_intake_workflow.py` to scan multi-line `run: |` blocks and avoid collection-time `sys.path` leaks (`TEST-I2`, `TEST-I5`):
  - Parse multi-line `run: |` (and `run: >` / `run: |-`) YAML shell blocks in `.github/workflows/benchmark-intake.yml` (rather than only single-line `run:` entries) when checking for untrusted `${{ github.event.* }}` interpolation into shell commands.
  - Add a positive/negative synthetic test proving an untrusted `${{ github.event.issue.body }}` placed on line 2+ of a multi-line `run: |` block is caught by the scanner.
  - Replace collection-time `sys.path` / `sys.modules` mutation with scoped module loading so importing the test file does not mutate global Python import state (`TEST-I5`).
  - Depends on: none
  - Expected outcome: Multi-line shell injections in `benchmark-intake.yml` are reliably detected, and `.github/scripts/test_benchmark_intake_workflow.py` leaves `sys.path` clean at collection time.
  - Execution state: pending

### Task group 2: Replace dead CLI monkeypatch and remove private/config pinning

- [ ] E-03 Fix `tests/test_cli.py` (`TEST-U3`, `TEST-I8`) and `tests/test_bench_command.py` (`TEST-I1`, `TEST-I8`):
  - In `tests/test_cli.py`, replace `TestCliRunTests.test_run_tests_exits_zero` (whose `subprocess.run` monkeypatch is dead across a child subprocess) with an in-process test of `pubrun.__main__._run_tests()` inside a `tmp_path` containing fake `tests/` and `tox.ini` with `subprocess.run` stubbed in-process, asserting the pytest invocation executes (`call_count >= 1`) and propagates non-zero exit codes cleanly (`TEST-U3`).
  - In `tests/test_cli.py`, replace any raw `pyproject.toml` substring pin (`TEST-I8`) with a parsed `tomllib.loads` or behavioral CLI assertion.
  - In `tests/test_bench_command.py`, replace private `not hasattr(...)` pinning (`TEST-I8`) with observable behavioral assertions, and ensure `TestWheelNonCheckoutBench` asserts clean failure/behavior when `build` is installed (matching the CI `packaging` job step in `E-01`).
  - Depends on: E-01
  - Expected outcome: `test_run_tests_exits_zero` genuinely tests `_run_tests()`, and brittle config/private-attribute pins in `test_cli.py` and `test_bench_command.py` are replaced with behavioral checks.
  - Execution state: pending

### Task group 3: Validate YAML, examples, workflow security tests, and CLI/bench suites

- [ ] E-04 Validate `.github/workflows/ci.yml` YAML syntax and run `examples/verify_all.py` under hostile `XDG_CONFIG_HOME`:
  - Parse `.github/workflows/ci.yml` via `yaml.safe_load` (or Python check) and execute `examples/verify_all.py` with a temporary hostile `XDG_CONFIG_HOME` confirming exit `0`.
  - Depends on: E-01
  - Expected outcome: CI workflow YAML parses cleanly and `examples/verify_all.py` passes cleanly under hostile host config.
  - Execution state: pending

- [ ] E-05 Run targeted `pytest -p randomly` on `.github/scripts/`, `tests/test_bench_command.py`, and `tests/test_cli.py` and record complete output:
  - Run all commands listed in `## Required tests / validation` and verify exit `0`.
  - Depends on: E-02, E-03, E-04
  - Expected outcome: All workflow-security, bench, and CLI tests pass under `-p randomly` with zero failures.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `.github/workflows/ci.yml`'s `packaging` job already installs `build` and `twine` to build and inspect the wheel/sdist, making it the natural place to run `TestWheelNonCheckoutBench` without adding `build` to every matrix job.
- `.github/scripts/test_benchmark_intake_workflow.py` is run in CI alongside `tests/` and uses stdlib + PyYAML (or regex-over-YAML); ensuring multi-line block parsing handles YAML block scalars cleanly avoids false negatives without external dependencies.

## Findings

| ID | Concerns | Severity | Remediation Risk | Persona | Summary |
|---|---|---|---|---|---|
| `TEST-I1` | testing | High | Low (`functionality`) | Testing / CI Engineer | `TestWheelNonCheckoutBench` silently skips in every CI job because `build` is not in `[dev]` and the `packaging` job never runs pytest. |
| `TEST-I2` | testing | High | Low (`security`) | Security / CI Engineer | `.github/scripts/test_benchmark_intake_workflow.py` misses untrusted expressions inside multi-line `run: |` blocks in `benchmark-intake.yml`. |
| `TEST-U3` | testing | Medium | Low (`functionality`) | QA / CLI Maintainer | `tests/test_cli.py::TestCliRunTests.test_run_tests_exits_zero` has a dead `subprocess.run` monkeypatch that cannot cross into its child subprocess. |
| `TEST-I5` (`.github/scripts/`) | testing | Medium | Low (`complexity`) | Testing Expert | Collection-time `sys.path`/`sys.modules` mutation in `.github/scripts/test_benchmark_intake_workflow.py`. |
| `TEST-I8` (`test_bench_command.py`, `test_cli.py`) | testing | Low | Low (`complexity`) | Testing Expert | Private `not hasattr` checks in `test_bench_command.py` and raw substring check on `pyproject.toml` in `test_cli.py`. |
| `TEST-I9` | testing | Low | Low (`usability`) | CI Engineer | `examples/verify_all.py` is unrun in CI and lacks `XDG_CONFIG_HOME`/`APPDATA` isolation; `tox.ini` omits `tui` and extra suites. |

## Proposed changes (ordered, validatable)

1. `E-01` (`.github/workflows/ci.yml`, `tox.ini`, `examples/verify_all.py`): Run `TestWheelNonCheckoutBench` and `examples/verify_all.py` in CI, isolate host config in `examples/verify_all.py`, and update `tox.ini`.
2. `E-02` (`.github/scripts/test_benchmark_intake_workflow.py`): Scan multi-line `run: |` blocks with synthetic regression test and clean up collection-time `sys.path`.
3. `E-03` (`tests/test_cli.py`, `tests/test_bench_command.py`): Replace dead monkeypatch in `test_run_tests_exits_zero` and replace raw/private pins with behavioral checks.
4. `E-04` (validation): Validate CI YAML syntax and `examples/verify_all.py` under hostile host config.
5. `E-05` (validation): Run randomized pytest across `.github/scripts/`, `tests/test_bench_command.py`, and `tests/test_cli.py`.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none. Strictly scoped to the six CI, example, tox, and test files listed in `Scope-Paths`.
- Under-scope: none. Both High CI/security testing gaps and all paired hygiene gaps are covered.

## Required tests / validation

1. Workflow security, bench, and CLI randomized pytest run:
   ```sh
   pytest -p randomly .github/scripts/ tests/test_bench_command.py tests/test_cli.py -v
   ```
2. CI YAML syntax + isolated `examples/verify_all.py` run under hostile host config:
   ```sh
   python3 -c 'import os, subprocess, sys, tempfile
   from pathlib import Path
   try:
       import yaml
       yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
       print("CI_YAML_OK")
   except ImportError:
       print("PYYAML_NOT_INSTALLED_SKIPPED_YAML_PARSE")
   with tempfile.TemporaryDirectory() as td:
       cfg = Path(td) / "pubrun" / "config.toml"
       cfg.parent.mkdir(parents=True)
       cfg.write_text("[core]\nprofile = \"deep\"\n[events]\non_inactive_annotate = \"error\"\n", encoding="utf-8")
       env = dict(os.environ, XDG_CONFIG_HOME=td, APPDATA=td)
       rc = subprocess.call([sys.executable, "examples/verify_all.py"], env=env)
       assert rc == 0, f"verify_all.py failed: rc={rc}"
       print("VERIFY_ALL_ISOLATED_OK")'
   ```

## Spec / documentation sync

N/A. CI, tox, example verification, and test-hygiene updates only.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result (which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- .github/workflows/ci.yml tox.ini examples/verify_all.py` confirming `TestWheelNonCheckoutBench` in `packaging`, `examples/verify_all.py` in CI with isolated `XDG_CONFIG_HOME`/`APPDATA`, and `tox.ini` updates.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- .github/scripts/test_benchmark_intake_workflow.py` and passing pytest output from `.github/scripts/` confirming multi-line `run: |` injection detection (including the synthetic negative test) and clean collection-time `sys.path`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- tests/test_cli.py tests/test_bench_command.py` confirming the in-process `_run_tests()` test and removal of raw/private pins, plus passing pytest output for `TestCliRunTests` and `tests/test_bench_command.py`.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted output of Command 2 from `## Required tests / validation` showing `VERIFY_ALL_ISOLATED_OK` (and `CI_YAML_OK` if PyYAML is present) with exit `0`.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted complete output of Command 1 from `## Required tests / validation` (`pytest -p randomly .github/scripts/ tests/test_bench_command.py tests/test_cli.py -v`), exiting `0` with zero failures.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

1. **Open questions and approval:** Do not execute until explicit human approval is recorded (`aw ipd set approved 4eo4z2 --by-human` or `aw set approved assess-bt --by-human`).
2. **Scope declaration:** Modify only the six declared `Scope-Paths`.
3. **Validation honesty:** Paste actual command outputs from this workspace for every `V-*` item.
4. **Commits and push policy:** Commit only files modified for this plan through `aw commit 4eo4z2 -- <paths>`. Never push, tag, or publish.
5. **Lifecycle finalization:** Finalize via `aw ipd finalize 4eo4z2` (or let the runner finalize) only after every `E-*` is `performed` and every `V-*` is `pass`.
