# IPD: Slow test markers and workflow or benchmark test isolation cleanup

- Date: 2026-11-27
- Kind: child
- Concern: Add missing `@pytest.mark.slow` markers (`TEST-I6`), replace brittle workflow/config substring pins in `tests/test_compatibility.py` (`TEST-I8`), and clean up global `sys.modules` mutations in `tests/test_package_benchmark.py` and `tests/test_startup_benchmark.py` (`TEST-I5`).
- Scope: Update `tests/test_compatibility.py`, `tests/test_package_benchmark.py`, and `tests/test_startup_benchmark.py` (test-only changes; no production source edits).
- Scope-Paths: tests/test_compatibility.py, tests/test_package_benchmark.py, tests/test_startup_benchmark.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Add @pytest.mark.slow markers, replace brittle workflow substring pins in test_compatibility.py, and clean up module-load isolation in benchmark tests
- Work-Kind: followup
- Priority: low
- Set: assess-bt
- Order: 10
- Highest E allocated: 04
- Author: Antigravity
- Id: 37sth0

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-27 to-review (Antigravity): Authored review-ready child IPD from `/assess testing` Slice 3 audit on HEAD `512ee68` / `8f2aacd`.
- 2026-11-27 draft (Antigravity): created.

## Goal

Make `pytest -m "not slow"` accurately deselect multi-subprocess benchmark and compatibility tests using the `slow` marker already registered in `pyproject.toml`, replace brittle raw-text workflow/config substring checks in `tests/test_compatibility.py` with structured YAML/TOML/behavioral assertions, and prevent `_load_module` helpers in `tests/test_package_benchmark.py` and `tests/test_startup_benchmark.py` from leaving synthetic modules registered in `sys.modules` across tests.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Mark slow tests and remove brittle substring/module-state coupling

- [ ] E-01 Update `tests/test_compatibility.py` (`TEST-I6`, `TEST-I8`):
  - Apply `@pytest.mark.slow` to multi-subprocess compatibility tests that spawn external Python processes or benchmark workloads so `pytest -m "not slow"` skips them cleanly.
  - Replace brittle raw substring checks against `.github/workflows/*.yml` or `pyproject.toml` with structured parsing (`tomllib.loads` / YAML parsing) or behavioral contract assertions so benign formatting changes do not cause false test failures.
  - Depends on: none
  - Expected outcome: Slow compatibility tests honor `-m "not slow"` and workflow/config assertions survive benign reformatting.
  - Execution state: pending

- [ ] E-02 Update `tests/test_package_benchmark.py` (`TEST-I5`, `TEST-I6`):
  - Apply `@pytest.mark.slow` to tests that invoke `benchmarks/package_capture_bench.py` via subprocess.
  - Ensure `_load_module` does not permanently pollute `sys.modules` (either restore prior `sys.modules` entry via a context manager/fixture or remove temporary entries after loading/testing) while keeping all tests deterministic under `-p randomly`.
  - Depends on: none
  - Expected outcome: Subprocess package-benchmark tests are selectable/deselectable via `-m slow` / `-m "not slow"` and do not leak synthetic entries into `sys.modules`.
  - Execution state: pending

- [ ] E-03 Update `tests/test_startup_benchmark.py` (`TEST-I5`, `TEST-I6`):
  - Apply `@pytest.mark.slow` to tests that invoke `benchmarks/startup_breakdown.py` via subprocess.
  - Ensure `_load_module` does not permanently pollute `sys.modules` across tests while keeping all tests deterministic under `-p randomly`.
  - Depends on: none
  - Expected outcome: Subprocess startup-benchmark tests are selectable/deselectable via `-m slow` / `-m "not slow"` and do not leak synthetic entries into `sys.modules`.
  - Execution state: pending

### Task group 2: Validate full execution and `-m "not slow"` selection

- [ ] E-04 Run targeted `pytest -p randomly` (both full and `-m "not slow"`) and record complete output:
  - Run both commands listed in `## Required tests / validation` and verify exit `0`, confirming `-m "not slow"` deselects the marked slow tests and runs only the fast unit subset.
  - Depends on: E-01, E-02, E-03
  - Expected outcome: All tests pass under `-p randomly` and `-m "not slow"` reports deselected slow tests with exit `0`.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `pyproject.toml` already registers the marker `slow: runs the benchmark harness or another multi-subprocess workload (deselect with -m 'not slow')` under `[tool.pytest.ini_options]`, so no `pyproject.toml` edit is required.
- Python 3.11+ standard library `tomllib` is available in the test environment for structured `pyproject.toml` assertions.

## Findings

| ID | Concerns | Severity | Remediation Risk | Persona | Summary |
|---|---|---|---|---|---|
| `TEST-I5` (`test_*_benchmark.py`) | testing | Medium | Low (`complexity`) | Testing Expert | `_load_module` helpers in `tests/test_package_benchmark.py` and `tests/test_startup_benchmark.py` insert synthetic modules into `sys.modules` without cleanup. |
| `TEST-I6` (`@pytest.mark.slow`) | testing | Medium | Low (`complexity`) | Testing / CI Engineer | Multi-subprocess tests in `test_compatibility.py`, `test_package_benchmark.py`, and `test_startup_benchmark.py` lack `@pytest.mark.slow` despite the marker being registered in `pyproject.toml`. |
| `TEST-I8` (`test_compatibility.py`) | testing | Low | Low (`complexity`) | Testing Expert | Brittle workflow/config raw substring pinning in `tests/test_compatibility.py`. |

## Proposed changes (ordered, validatable)

1. `E-01` (`tests/test_compatibility.py`): Add `@pytest.mark.slow` on multi-subprocess tests and replace brittle raw workflow/config substring checks with structured assertions.
2. `E-02` (`tests/test_package_benchmark.py`): Add `@pytest.mark.slow` on subprocess benchmark tests and clean up `sys.modules` registration in `_load_module`.
3. `E-03` (`tests/test_startup_benchmark.py`): Add `@pytest.mark.slow` on subprocess benchmark tests and clean up `sys.modules` registration in `_load_module`.
4. `E-04` (validation): Run randomized pytest both fully and with `-m "not slow"`.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none. Test-only plan modifying strictly three test files.
- Under-scope: none. All remaining `TEST-I5`, `TEST-I6`, and `TEST-I8` items are covered.

## Required tests / validation

1. Full randomized pytest run across all three files:
   ```sh
   pytest -p randomly tests/test_compatibility.py tests/test_package_benchmark.py tests/test_startup_benchmark.py -v
   ```
2. Fast-subset marker selection check:
   ```sh
   pytest -p randomly -m "not slow" tests/test_compatibility.py tests/test_package_benchmark.py tests/test_startup_benchmark.py -v
   ```

## Spec / documentation sync

N/A. Uses the existing `slow` marker already documented in `pyproject.toml`.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result (which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- tests/test_compatibility.py` confirming `@pytest.mark.slow` annotations and structured YAML/TOML/behavioral assertions, plus passing pytest output for `tests/test_compatibility.py`.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- tests/test_package_benchmark.py` confirming `@pytest.mark.slow` annotations and `sys.modules` cleanup in `_load_module`, plus passing pytest output for `tests/test_package_benchmark.py`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- tests/test_startup_benchmark.py` confirming `@pytest.mark.slow` annotations and `sys.modules` cleanup in `_load_module`, plus passing pytest output for `tests/test_startup_benchmark.py`.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted complete output of both commands in `## Required tests / validation`, confirming exit `0`, all tests passing in Command 1, and slow tests visibly deselected (`deselected`) in Command 2.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

1. **Open questions and approval:** Do not execute until explicit human approval is recorded (`aw ipd set approved 37sth0 --by-human` or `aw set approved assess-bt --by-human`).
2. **Scope declaration:** Modify only the three declared `Scope-Paths`.
3. **Validation honesty:** Paste actual command outputs from this workspace for every `V-*` item.
4. **Commits and push policy:** Commit only files modified for this plan through `aw commit 37sth0 -- <paths>`. Never push, tag, or publish.
5. **Lifecycle finalization:** Finalize via `aw ipd finalize 37sth0` (or let the runner finalize) only after every `E-*` is `performed` and every `V-*` is `pass`.
