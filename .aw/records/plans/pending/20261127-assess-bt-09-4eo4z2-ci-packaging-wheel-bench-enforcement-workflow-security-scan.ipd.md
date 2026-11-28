# IPD: CI packaging wheel bench enforcement workflow security scan and test hygiene

- Date: 2026-11-27
- Kind: child
- Concern: Close two High Continuous Integration (CI) and security testing gaps (`TEST-I1`, `TEST-I2`), fix a dead subprocess monkeypatch in Command-Line Interface (CLI) tests (`TEST-U3`), and close `tox.ini`, `examples/verify_all.py`, `.github/scripts/` import-state isolation, and test-pinning hygiene gaps (`TEST-I5` `.github/scripts/`, `TEST-I8`, `TEST-I9`).
- Scope: Update `.github/workflows/ci.yml`, `.github/scripts/test_benchmark_intake_workflow.py`, `.github/scripts/test_extract_attachment_url.py`, `.github/scripts/test_validate_benchmark_submission.py`, `tox.ini`, `examples/verify_all.py`, `tests/test_bench_command.py`, and `tests/test_cli.py`.
- Scope-Paths: .github/workflows/ci.yml, .github/scripts/test_benchmark_intake_workflow.py, .github/scripts/test_extract_attachment_url.py, .github/scripts/test_validate_benchmark_submission.py, tox.ini, examples/verify_all.py, tests/test_bench_command.py, tests/test_cli.py
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: complex
- Short-Description: Enforce TestWheelNonCheckoutBench and verify_all.py in CI, scan multi-line run/script blocks in benchmark-intake, isolate .github/scripts/ imports, update tox.ini, and fix CLI/bench test hygiene
- Work-Kind: followup
- Priority: high
- Set: assess-bt
- Order: 9
- Highest E allocated: 05
- Author: Antigravity
- Id: 4eo4z2
- Approval: 2026-11-28, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-28 approved (aw set): status set to approved
- 2026-11-27 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004
- 2026-11-27 to-review (Antigravity): Authored review-ready child IPD from `/assess testing` Slices 2 and 3 on HEAD `512ee68` / `8f2aacd`.
- 2026-11-27 draft (Antigravity): created.

## Goal

Ensure `tests/test_bench_command.py::TestWheelNonCheckoutBench` actually executes and fails closed if `build` is missing in Continuous Integration (CI) instead of silently skipping in every job. Extend `.github/scripts/test_benchmark_intake_workflow.py` to detect untrusted GitHub Actions expression interpolations inside multi-line `run:` and `script:` blocks, and remove collection-time `sys.path` and `sys.modules` leaks in `.github/scripts/test_extract_attachment_url.py` and `.github/scripts/test_validate_benchmark_submission.py`. Run `examples/verify_all.py` in CI with isolated user config and stripped `PUBRUN_*` environment variables, update `tox.ini` to include the `tui` extra and expose a shell-glob-free `[testenv:extra]` environment, and replace the dead monkeypatch in `tests/test_cli.py::TestCliRunTests.test_run_tests_exits_zero` and private or raw-text pins in `tests/test_bench_command.py` and `tests/test_cli.py`.

### CI, workflow security, and test hygiene scope

```mermaid
flowchart LR
    E1["E-01: ci.yml, tox.ini, examples/verify_all.py"]
    E2["E-02: .github/scripts/ workflow scan and import isolation"]
    E3["E-03: test_cli.py and test_bench_command.py hygiene"]
    E4["E-04: YAML, tox.ini, compat, and isolated verify_all.py checks"]
    E5["E-05: Randomized pytest and import-state check"]

    E1 --> E3
    E1 --> E4
    E2 --> E5
    E3 --> E5
    E4 --> E5
```

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Enforce wheel bench tests, workflow security scan, and example verification in CI

- [ ] E-01 Update `.github/workflows/ci.yml`, `tox.ini`, and `examples/verify_all.py` (`TEST-I1`, `TEST-I9`):
  - In `.github/workflows/ci.yml` (`jobs.packaging`), install `pytest` alongside `build` and `twine` (`pip install build twine pytest`) so pytest is available on both `ubuntu-latest` and `windows-latest` without installing editable `pubrun` into the runner's base Python. Add a dedicated step after `Verify sdist cleanliness, wheel contents, and commit stamp in clean environments` with `env: PUBRUN_REQUIRE_WHEEL_TEST: "1"` running `python -m pytest tests/test_bench_command.py -k TestWheelNonCheckoutBench -v -rs` (cross-platform across bash and PowerShell, preserving every existing check asserted by `tests/test_compatibility.py`).
  - In `.github/workflows/ci.yml` (`jobs.extra-suites` on `ubuntu-latest`, Python `3.12`), add a step running `python examples/verify_all.py` so every example script is verified continuously without altering existing `extra-suites` assertions in `tests/test_compatibility.py`.
  - In `examples/verify_all.py::main`, strip ambient `PUBRUN_*` variables (`for key in list(env): if key.startswith("PUBRUN_"): del env[key]`) and, inside the `tempfile.TemporaryDirectory` block, create an empty config directory (for example `os.path.join(tmp_dir, "config_home")`) and set both `env["XDG_CONFIG_HOME"]` and `env["APPDATA"]` to that directory before invoking each example script.
  - In `tox.ini`, add `tui` to `[testenv]` (`extras = dev, tui`) so default Python 3.8 through 3.14 test runs cover the Terminal User Interface (TUI) suite, and add `[testenv:extra]` (`extras = dev, bench`, `deps = pyyaml`, `commands = pytest .github/scripts/ benchmarks/ tests/test_compatibility.py -v`) using explicit directory paths rather than an unexpanded shell glob (`benchmarks/test_*.py`), because `tox` invokes commands directly without a shell.
  - Depends on: none
  - Expected outcome: CI `packaging` runs `TestWheelNonCheckoutBench` with `pytest` installed and fail-closed enforcement; CI `extra-suites` runs `examples/verify_all.py`; `examples/verify_all.py` is isolated from host config and `PUBRUN_*` environment variables; `tox.ini` covers `tui` in `[testenv]` and exposes shell-glob-free `[testenv:extra]`.
  - Execution state: pending

- [ ] E-02 Extend `.github/scripts/test_benchmark_intake_workflow.py` (`TEST-I2`) and remove collection-time import-state leaks in `.github/scripts/test_extract_attachment_url.py` and `.github/scripts/test_validate_benchmark_submission.py` (`TEST-I5`):
  - In `.github/scripts/test_benchmark_intake_workflow.py`, extract a standard-library helper (requiring zero third-party packages, preserving PyYAML optionality) that collects every `run:` shell value (single-line entries, multi-line YAML block scalars `|`, `|-`, `|+`, `>`, `>-`, `>+`, optional indentation indicators such as `|2`, and indented multi-line continuations) as well as `actions/github-script` `script:` blocks, while ignoring non-shell keys such as `jobs.validate.if:` (where `.github/workflows/benchmark-intake.yml` legitimately checks `github.event.issue.body`). Assert that no extracted `run:` or `script:` block interpolates untrusted `${{ ... github.event. ... }}` expressions. Extend `test_pyyaml_crosscheck_when_available` to walk `jobs[*].steps[*]` (`run` and `with.script`) with the same assertion.
  - In `.github/scripts/test_benchmark_intake_workflow.py`, add synthetic unit tests proving: (a) a clean multi-line `run: |` block passing data via `env:` produces zero findings, (b) an untrusted `${{ github.event.issue.body }}` or `${{ github.event.issue.title }}` on line 2 or later of `run: |`, `run: |-`, and `run: >` blocks is caught, and (c) `github.event.issue.body` inside a job-level `if:` condition is not falsely flagged.
  - In `.github/scripts/test_extract_attachment_url.py`, replace module-level collection-time `sys.modules["extract_attachment_url"] = x` registration with a module-scoped pytest fixture (or helper context manager) that snapshots and restores `sys.path` and `sys.modules` on teardown; update `test_host_allowlist_matches_validator` to load `.github/scripts/validate_benchmark_submission.py` inside a `try/finally` block that restores `sys.path[:]` and any added or modified `sys.modules` keys (`validate_benchmark_submission`, `share_safety`) mutated by `.github/scripts/validate_benchmark_submission.py`.
  - In `.github/scripts/test_validate_benchmark_submission.py`, replace module-level collection-time `sys.modules["validate_benchmark_submission"] = v` registration (which triggers `.github/scripts/validate_benchmark_submission.py`'s `sys.path.insert(0, str(_REPO / "benchmarks"))` and `import share_safety` at pytest collection time) with a module-scoped pytest fixture that runs `pytest.importorskip("jsonschema")`, snapshots `sys.path` and `sys.modules`, loads the module, yields it to tests, and restores `sys.path[:]` and `sys.modules` on teardown.
  - Depends on: none
  - Expected outcome: Multi-line shell and script injections in `.github/workflows/benchmark-intake.yml` are detected by both stdlib and PyYAML checks with regression tests, and collecting or running `.github/scripts/` leaves `sys.path` and `sys.modules` unchanged.
  - Execution state: pending

### Task group 2: Replace dead CLI monkeypatch and remove private/config pinning

- [ ] E-03 Fix `tests/test_cli.py` (`TEST-U3`, `TEST-I8`) and `tests/test_bench_command.py` (`TEST-I1`, `TEST-I8`):
  - In `tests/test_cli.py::TestCliRunTests.test_run_tests_exits_zero`, replace the dead child-subprocess `subprocess.run` monkeypatch with an in-process test calling `src/pubrun/__main__.py::_run_tests` inside `tmp_path` containing a fake `tests/` directory and `tox.ini` file. Selectively stub `subprocess.run` only when `isinstance(cmd, list) and len(cmd) >= 3 and cmd[1:3] == ["-m", "pytest"]`, delegating the subsequent `mock_training.py` subprocess call in `src/pubrun/__main__.py::_run_tests` to `original_run` so the mock script still generates `runs/<run>/manifest.json`. Assert both: (a) when stubbed pytest returns `0`, `pytest_calls` records `[sys.executable, "-m", "pytest", "tests/", "-q"]` (`len(pytest_calls) == 1`) and `_run_tests()` completes with `"Validation complete."` on stdout; and (b) when stubbed pytest returns `1`, `_run_tests()` raises `SystemExit` with `code == 1` and emits `"PyTest exited with code 1."` on stdout.
  - In `tests/test_cli.py::TestCliNewFeatures.test_pbr_alias_registered_in_pyproject`, replace the raw substring assertion (`'pbr = "pubrun.__main__:main"' in content`) with structured TOML parsing via `from pubrun.config import tomllib` (preserving Python 3.8 through 3.10 compatibility via `tomli` instead of bare `import tomllib`), asserting `data["project"]["scripts"]["pbr"] == "pubrun.__main__:main"` and `data["project"]["scripts"]["pubrun"] == "pubrun.__main__:main"`.
  - In `tests/test_bench_command.py`:
    - Replace `TestSubmissionVerifier.test_duplicate_verifier_helpers_removed` (private `not hasattr` checks) with a behavioral delegation test proving `src/pubrun/__main__.py::_share_check` delegates directly to `src/pubrun/_bench/share_safety.py::check_share_safe_text` (monkeypatching `check_share_safe_text` to record the call and return a sentinel `(False, ["sentinel reason"])`, asserting `_share_check` returns that exact tuple).
    - Replace `TestAttachFlowClient.test_no_auto_post_helpers_remain` (private `not hasattr` checks) with a behavioral no-transmit test calling `src/pubrun/__main__.py::_run_bench` for both `--submit-file` with `prepare_submission=True` (expecting `SystemExit(0)` and staged `pubrun-share/<file>`) and `--submit-file` with `prepare_submission=False, contribute=False` (expecting the safe-file attach block on stderr), with `subprocess.run` and `urllib.request.urlopen` monkeypatched to raise `AssertionError` so no external command or network request can occur.
    - Update `TestWheelNonCheckoutBench.test_wheel_install_runs_pubrun_bench_outside_checkout` so that when `os.environ.get("PUBRUN_REQUIRE_WHEEL_TEST") == "1"` and `importlib.util.find_spec("build") is None`, it fails closed via `pytest.fail(...)` instead of calling `pytest.importorskip("build")` (matching `E-01`'s `packaging` CI step). Add a fast (non-`slow`) unit test verifying via `monkeypatch` that missing `build` triggers `pytest.fail.Exception` when `PUBRUN_REQUIRE_WHEEL_TEST=1` and `pytest.skip.Exception` when unset.
  - Depends on: E-01
  - Expected outcome: `TestCliRunTests` exercises `src/pubrun/__main__.py::_run_tests` in-process for both zero and non-zero pytest outcomes; `pyproject.toml` script registration uses cross-version TOML parsing; private `not hasattr` pins are replaced by behavioral delegation and no-transmit tests; and `TestWheelNonCheckoutBench` enforces fail-closed execution when `PUBRUN_REQUIRE_WHEEL_TEST=1`.
  - Execution state: pending

### Task group 3: Validate YAML, tox.ini, examples, workflow security tests, and CLI/bench suites

- [ ] E-04 Validate `.github/workflows/ci.yml` YAML syntax, `tox.ini` configuration, workflow compatibility tests, and `examples/verify_all.py` under hostile host config and `PUBRUN_*` environment variables:
  - Run Command 2 from `## Required tests / validation` and confirm `CI_YAML_OK` (when PyYAML is installed), `TOX_INI_OK`, and `VERIFY_ALL_ISOLATED_OK` with exit `0`.
  - Depends on: E-01
  - Expected outcome: CI workflow YAML and `tox.ini` parse cleanly without unexpanded globs, and `examples/verify_all.py` exits `0` under hostile `XDG_CONFIG_HOME`, `APPDATA`, and `PUBRUN_*` values.
  - Execution state: pending

- [ ] E-05 Run targeted `python3 -m pytest -p randomly` across `.github/scripts/`, `tests/test_bench_command.py`, `tests/test_cli.py`, and `tests/test_compatibility.py -k workflow`, verify clean `.github/scripts/` import state, and record complete output:
  - Run Commands 1 and 3 from `## Required tests / validation` and verify exit `0`.
  - Depends on: E-02, E-03, E-04
  - Expected outcome: All workflow-security, bench, CLI, and CI-workflow compatibility tests pass under `-p randomly` with zero failures, and collecting `.github/scripts/` leaves `sys.path` and `sys.modules` clean.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `.github/workflows/ci.yml`'s `packaging` job runs on `[ubuntu-latest, windows-latest]` with Python 3.12 and currently installs only `build` and `twine` (not `pytest`), so adding `pytest` to `Install build frontend` lets `TestWheelNonCheckoutBench` run via `python -m pytest` without installing editable `pubrun` into the runner's base environment (`pyproject.toml` sets `pythonpath = ["src"]` and `addopts = "-p no:randomly"`).
- `.github/workflows/ci.yml`'s `extra-suites` job runs on `ubuntu-latest` Python `3.12` and is checked structurally by `tests/test_compatibility.py::test_ci_workflow_compatibility_matrix_structural` and `test_workflows_pyyaml_crosscheck_when_available`; all scripts in `examples/` use only the Python standard library plus `pubrun`.
- `.github/scripts/test_benchmark_intake_workflow.py` intentionally avoids a hard PyYAML dependency (`test_pyyaml_crosscheck_when_available` uses `pytest.importorskip("yaml")`), and `.github/workflows/benchmark-intake.yml` legitimately references `github.event.issue.body` inside `jobs.validate.if:` (not inside any `run:` or `script:` block).
- The actual `.github/scripts/` collection-time import leaks live in `.github/scripts/test_extract_attachment_url.py` and `.github/scripts/test_validate_benchmark_submission.py` (which loads `.github/scripts/validate_benchmark_submission.py`, executing `sys.path.insert(0, str(_REPO / "benchmarks"))` and `import share_safety`).
- `src/pubrun/config.py::tomllib` provides cross-version TOML parsing across Python 3.8 through 3.14 (`tomllib` on 3.11+, `tomli` on <3.11), matching `pyproject.toml` `requires-python = ">=3.8"`.
- `src/pubrun/__main__.py::_run_tests` runs two subprocesses when `tests/` and `tox.ini` exist (`pytest` and `mock_training.py`, which must create `runs/<run>/manifest.json`).

## Findings

| ID | Concerns | Severity | Remediation Risk | Persona | Summary |
|---|---|---|---|---|---|
| `TEST-I1` | testing | High | Low (`functionality`) | Testing / CI Engineer | `tests/test_bench_command.py::TestWheelNonCheckoutBench` silently skips in every CI job because `build` is not in `[dev]` and the `packaging` job never installs or runs `pytest`. |
| `TEST-I2` | testing | High | Low (`security`) | Security / CI Engineer | `.github/scripts/test_benchmark_intake_workflow.py` checks only single lines starting with `python3` or `run:` for `github.event.issue.body`, missing untrusted `${{ github.event.* }}` expressions inside multi-line `run: \|` and `script: \|` blocks. |
| `TEST-U3` | testing | Medium | Low (`functionality`) | QA / CLI Maintainer | `tests/test_cli.py::TestCliRunTests.test_run_tests_exits_zero` monkeypatches `subprocess.run` in the parent pytest process before spawning a child `pubrun --run-tests` subprocess in an empty `tmp_path`, so the monkeypatch is dead and the pytest branch never runs. |
| `TEST-I5` (`.github/scripts/`) | testing | Medium | Low (`complexity`) | Testing Expert | Collection-time and test-time `sys.modules` and `sys.path` mutations in `.github/scripts/test_extract_attachment_url.py` and `.github/scripts/test_validate_benchmark_submission.py` (including `validate_benchmark_submission.py`'s `sys.path.insert` and `share_safety` import). |
| `TEST-I8` (`test_bench_command.py`, `test_cli.py`) | testing | Low | Low (`complexity`) | Testing Expert | Private `not hasattr` checks in `tests/test_bench_command.py::TestSubmissionVerifier.test_duplicate_verifier_helpers_removed` and `TestAttachFlowClient.test_no_auto_post_helpers_remain`, and raw substring check on `pyproject.toml` in `tests/test_cli.py::TestCliNewFeatures.test_pbr_alias_registered_in_pyproject`. |
| `TEST-I9` | testing | Low | Low (`usability`) | CI Engineer | `examples/verify_all.py` is unrun in CI and lacks `XDG_CONFIG_HOME`, `APPDATA`, and `PUBRUN_*` isolation; `tox.ini` omits `tui` and extra suites. |

## Proposed changes (ordered, validatable)

1. `E-01` (`.github/workflows/ci.yml`, `tox.ini`, `examples/verify_all.py`): Install `pytest` and run `TestWheelNonCheckoutBench` with `PUBRUN_REQUIRE_WHEEL_TEST=1` in `packaging`, run `examples/verify_all.py` in `extra-suites`, isolate `XDG_CONFIG_HOME`/`APPDATA`/`PUBRUN_*` in `examples/verify_all.py`, and update `tox.ini` (`extras = dev, tui` plus shell-glob-free `[testenv:extra]`).
2. `E-02` (`.github/scripts/test_benchmark_intake_workflow.py`, `.github/scripts/test_extract_attachment_url.py`, `.github/scripts/test_validate_benchmark_submission.py`): Scan multi-line `run:` and `script:` blocks (stdlib + PyYAML cross-check) with synthetic regression tests, and isolate `sys.path`/`sys.modules` in `test_extract_attachment_url.py` and `test_validate_benchmark_submission.py`.
3. `E-03` (`tests/test_cli.py`, `tests/test_bench_command.py`): Replace dead monkeypatch in `test_run_tests_exits_zero` with in-process `_run_tests()` tests, parse `pyproject.toml` with `pubrun.config.tomllib`, replace both `not hasattr` tests with behavioral delegation/no-transmit assertions, and enforce `PUBRUN_REQUIRE_WHEEL_TEST=1` fail-closed behavior with a fast unit test.
4. `E-04` (validation): Validate CI YAML syntax, `tox.ini` config structure, and `examples/verify_all.py` under hostile host config and `PUBRUN_*` variables.
5. `E-05` (validation): Run randomized pytest across `.github/scripts/`, `tests/test_bench_command.py`, `tests/test_cli.py`, and `tests/test_compatibility.py -k workflow`, plus verify clean `.github/scripts/` collection import state.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none. Strictly scoped to the eight CI, script-test, tox, example, and unit-test files listed in `- Scope-Paths:` (mutually disjoint from all other children in Set `assess-bt`).
- Under-scope: none. Both High CI/security testing gaps and all paired hygiene and import-isolation gaps are covered.

## Required tests / validation

1. Workflow security, bench, CLI, and CI-workflow compatibility randomized pytest run:
   ```sh
   python3 -m pytest -p randomly .github/scripts/ tests/test_bench_command.py tests/test_cli.py -v && python3 -m pytest -p randomly tests/test_compatibility.py -k workflow -v
   ```
   (Note: if the execution environment lacks `hatchling` and offline isolation prevents `TestWheelNonCheckoutBench` from fetching `hatchling`, record that environment limit honestly, run the fast suite with `-m "not slow"` plus the new `PUBRUN_REQUIRE_WHEEL_TEST=1` unit guard test, and do not weaken the slow wheel test.)
2. CI YAML syntax, `tox.ini` validation, and isolated `examples/verify_all.py` run under hostile host config and `PUBRUN_*` env:
   ```sh
   python3 -c 'import configparser, os, subprocess, sys, tempfile
   from pathlib import Path
   try:
       import yaml
       ci = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
       assert "packaging" in ci["jobs"] and "extra-suites" in ci["jobs"]
       print("CI_YAML_OK")
   except ImportError:
       print("PYYAML_NOT_INSTALLED_SKIPPED_YAML_PARSE")
   cp = configparser.ConfigParser()
   cp.read("tox.ini", encoding="utf-8")
   assert "tui" in cp["testenv"]["extras"]
   assert "testenv:extra" in cp
   assert "*" not in cp["testenv:extra"]["commands"], cp["testenv:extra"]["commands"]
   print("TOX_INI_OK")
   with tempfile.TemporaryDirectory() as td:
       cfg = Path(td) / "pubrun" / "config.toml"
       cfg.parent.mkdir(parents=True)
       cfg.write_text("[core]\nprofile = \"deep\"\n[events]\non_inactive_annotate = \"error\"\n", encoding="utf-8")
       env = dict(os.environ, XDG_CONFIG_HOME=td, APPDATA=td, PUBRUN_AUTO_START="false", PUBRUN_OUTPUT_DIR=str(Path(td) / "hostile_runs"))
       rc = subprocess.call([sys.executable, "examples/verify_all.py"], env=env)
       assert rc == 0, f"verify_all.py failed: rc={rc}"
       assert not (Path(td) / "hostile_runs").exists(), "PUBRUN_OUTPUT_DIR leaked into examples"
       print("VERIFY_ALL_ISOLATED_OK")'
   ```
3. Verify collecting `.github/scripts/` does not mutate `sys.path` or leak script modules into `sys.modules`:
   ```sh
   python3 -c 'import sys, pytest
   before_path = list(sys.path)
   rc = pytest.main(["--collect-only", "-q", ".github/scripts/"])
   assert rc == 0, rc
   assert list(sys.path) == before_path, ("sys.path mutated during collection", set(sys.path) - set(before_path))
   leaked = [m for m in ("extract_attachment_url", "validate_benchmark_submission", "share_safety") if m in sys.modules]
   assert not leaked, f"sys.modules leaked during collection: {leaked}"
   print("SCRIPTS_COLLECTION_CLEAN_OK")'
   ```

## Spec / documentation sync

Not applicable. Verified `README.md`, `docs/research-use.md`, and `docs/functional_spec.md`: `README.md` and `docs/research-use.md` only name `examples/verify_all.py` generically, and `docs/functional_spec.md` describes `--run-tests` (`src/pubrun/__main__.py::_run_tests`) behavior that this plan preserves without production code or CLI contract changes.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result (which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- .github/workflows/ci.yml tox.ini examples/verify_all.py` confirming `pytest` installation and `PUBRUN_REQUIRE_WHEEL_TEST: "1"` `TestWheelNonCheckoutBench` step in `packaging`, `examples/verify_all.py` step in `extra-suites`, `XDG_CONFIG_HOME`/`APPDATA`/`PUBRUN_*` isolation inside `examples/verify_all.py::main`, and `tui` plus shell-glob-free `[testenv:extra]` in `tox.ini`.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- .github/scripts/test_benchmark_intake_workflow.py .github/scripts/test_extract_attachment_url.py .github/scripts/test_validate_benchmark_submission.py` confirming stdlib + PyYAML multi-line `run:`/`script:` injection scanning (ignoring `if:`) with synthetic regression tests and scoped `sys.path`/`sys.modules` fixtures, plus pasted output of Command 3 (`SCRIPTS_COLLECTION_CLEAN_OK`, exercising pytest collection via `pytest.main(["--collect-only", "-q", ".github/scripts/"])`) re-derived at execution time.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- tests/test_cli.py tests/test_bench_command.py` confirming in-process `src/pubrun/__main__.py::_run_tests` tests (zero and non-zero pytest exit with selective stubbing), `pubrun.config.tomllib` parsing for `pyproject.toml`, behavioral replacements for both `not hasattr` tests, and `PUBRUN_REQUIRE_WHEEL_TEST=1` fail-closed guard plus fast unit test, along with passing execution-time pytest output for `TestCliRunTests`, `TestCliNewFeatures.test_pbr_alias_registered_in_pyproject`, and `tests/test_bench_command.py`.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted complete output of Command 2 from `## Required tests / validation` (exercising `yaml.safe_load`, `configparser.ConfigParser`, and `examples/verify_all.py::main` under hostile `XDG_CONFIG_HOME`, `APPDATA`, `PUBRUN_AUTO_START`, and `PUBRUN_OUTPUT_DIR`) showing `CI_YAML_OK` (when PyYAML is installed), `TOX_INI_OK`, and `VERIFY_ALL_ISOLATED_OK` with exit `0`, re-derived at execution time.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted complete output of Command 1 from `## Required tests / validation` (`python3 -m pytest -p randomly` across `.github/scripts/`, `tests/test_bench_command.py`, `tests/test_cli.py`, and `tests/test_compatibility.py -k workflow`) and Command 3 (`SCRIPTS_COLLECTION_CLEAN_OK`), exiting `0` with zero failures, re-derived at execution time.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

1. **Open questions and approval:** Do not execute until explicit human approval is recorded (`aw ipd set approved 4eo4z2 --by-human` or `aw set approved assess-bt --by-human`).
2. **Scope declaration:** `- Scope-Paths:` declares the expected eight files this plan modifies (`.github/workflows/ci.yml`, `.github/scripts/test_benchmark_intake_workflow.py`, `.github/scripts/test_extract_attachment_url.py`, `.github/scripts/test_validate_benchmark_submission.py`, `tox.ini`, `examples/verify_all.py`, `tests/test_bench_command.py`, `tests/test_cli.py`). Keep changes within this scope; if execution genuinely requires editing an additional file or leaving a declared file untouched, make the necessary change and justify the delta at finalization with `--scope-reason` (per out-of-scope path) or `--scope-ack` (per declared-but-unmodified path) rather than stopping mid-run. Stop and report only on a genuinely unsafe condition (such as an unresolvable concurrent-edit conflict or missing prerequisite symbols).
3. **Validation honesty:** You MUST run every validation command listed in `## Required tests / validation` in this workspace and paste the actual runner output verbatim into each corresponding `V-*` item. Never claim tests passed without running them.
4. **Commits and push policy:** Commit only files modified for this plan through `aw commit 4eo4z2 -- <paths>` (never `git add -A`, `git commit -a`, or raw `git commit`). Never push, tag, or publish without explicit human instruction.
5. **Lifecycle finalization:** Mark each `E-*` item `performed` only after completing the work, and mark each `V-*` item `pass` only after inspecting actual pasted evidence in a separate pass. When executed by a runner (`aw oc run` or `aw agy run`), leave finalization to the runner's post-execution lifecycle transition; when executed manually by an agent outside a runner, finalize via `aw ipd finalize 4eo4z2` (never a hand-rolled `git mv` to `executed/`).
