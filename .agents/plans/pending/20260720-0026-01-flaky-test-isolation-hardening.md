# IPD: Harden the flaky-test class - cross-test isolation + timing-sensitive assertions

- Date: 2026-07-20
- Concern: testing (reliability of the test suite)
- Scope: `tests/` (conftest fixtures + several order/timing-sensitive tests); no product behavior
  change intended (characterization: pin real behavior, fix only test isolation/robustness)
- Status: to-review
- Approval: (set when a human approves; omit until then)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

Stop the recurring "green locally, red on one CI job" whack-a-mole. Over recent CI runs, FIVE
distinct pre-existing tests have flaked - each passing in isolation, each failing intermittently on a
different matrix job. They are one CLASS: **assertions that depend on state a prior test can disturb,
or on a background thread / finalizer having completed within a very short run.** Fix the class at the
root (test isolation + tolerant-but-meaningful assertions) so the suite is reliably green and future
contract/feature work is not blocked by unrelated noise.

This is explicitly a TEST-quality effort, not a product change. Where a flake hints at a real product
isolation bug (see the provenance one below), investigate and, if confirmed, split that fix out.

## The observed flake roster (evidence)

All surfaced 2026-07-15..20 across CI runs; all pre-existing; all pass in isolation:

| Test | Job seen | Symptom | Root-cause class | Status |
|---|---|---|---|---|
| `test_full_mode.py::test_full_wraps_console_end_to_end` | ubuntu-3.8 | `KeyError 'capture_mode'` (console section un-finalized) | timing (console finalize) | FIXED `13f9beb` |
| `test_manifest_schema.py::test_startup_manifest_conforms_to_schema` | windows-3.14 | `PermissionError` reading a live run's manifest | platform file-lock | FIXED `13f9beb` |
| `test_resources.py` (peak RSS) | ubuntu-3.11 | `peak_rss_bytes is None` before sampler landed | timing (bg sampler) | FIXED `8e9978b` |
| `test_cli.py::test_run_tests_mock_run_manifest_is_wellformed` | ubuntu-3.14 | outcome `running` != `completed` (atexit finalize race) | timing (atexit finalize) | FIXED `753ee76` |
| `test_new_features.py::TestProvenanceWriteHash::test_write_hash_matches_file` | ubuntu-3.13 | empty `data_files.outputs` (pubrun.open did not wrap) | **cross-test global-state** (current-run/provenance inactive) | diagnostic guard `d836e22`; ROOT FIX PENDING (this IPD) |

The first four were hardened point-by-point. The fifth is the tell that this is a class, not four
coincidences, and it points at the deeper cause: **module-global state leaking across tests.**

## Root-cause hypothesis (to confirm in execution)

Current isolation (`tests/conftest.py`): two autouse fixtures - `isolated_cwd` (chdir + patch
`Path.cwd`) and `clean_active_run` (resets `pubrun.tracker._active_run` before/after each test). But
pubrun carries OTHER process-global state that is NOT reset between tests:

- **Import-mode / bootstrap selection** (`pubrun._bootstrap` - the "first import wins" mode latch),
  which governs whether hooks (subprocess spy, console tee, and the current-run wiring `pubrun.open`
  relies on) are active. A prior test that imported a mode module can leave this latched.
- **Background threads** (resource watcher `pubrun-hw`, sampler) that may still be running or may not
  have sampled yet when a short test asserts on their output.
- **Console tee / signal handlers** installed on the process.

`pubrun.open()` records provenance only when `get_current_run().is_active` (`core.py:725-730`); if the
global current-run wiring is disturbed by ordering, the file is not wrapped and `outputs` is empty -
exactly the 5th flake.

## Proposed changes (ordered, validatable)

| Step | Change | Files | Remediation Risk | Validation |
|------|--------|-------|------------------|------------|
| 1 | **Reproduce the class deterministically.** Run the suite under randomized order (`pytest -p randomly` if available, else a fixed adverse order) and/or run suspect predecessor files immediately before each flaky test, until at least the 5th flake reproduces locally. Record the reproducing order. | (none; investigation) | Low | the flake reproduces locally on demand |
| 2 | **Confirm the leaked-global root cause** for the provenance flake: is `get_current_run()` stale, or is the mode latch suppressing hooks? Decide whether it is purely a TEST isolation gap or also a PRODUCT isolation bug. If product, split a separate finding. | `tests/`, `src/pubrun/_bootstrap.py`/`core.py` (read-only) | Low | documented cause with evidence |
| 3 | **Strengthen the autouse isolation fixture** in `conftest.py` to reset ALL relevant process-global state between tests (current-run - already done; plus mode-latch/bootstrap, and joining/stopping any lingering watcher threads), so tests start from a clean pubrun state regardless of order. Keep it minimal and documented. | `tests/conftest.py` | Medium (complexity - must reset the right globals without hiding real bugs; verify by the repro from step 1 going green) | the step-1 repro order now passes; full suite passes under randomized order |
| 4 | **Make the remaining timing assertions self-contained** (finalize/stop explicitly rather than relying on atexit or a bg thread having run; already done for 4/5) and confirm the 5th's diagnostic guard becomes a real pass under the hardened fixture. Remove the diagnostic-only scaffolding if the root fix makes it moot. | `tests/test_new_features.py` and any others step 1 surfaces | Low | flaky tests pass under adverse ordering |
| 5 | (Optional, if `pytest-randomly` is acceptable as a dev dep) add randomized test ordering to CI so this class cannot silently regress. Otherwise document the adverse-order check as a manual gate. | `pyproject.toml` (dev extra), `.github/workflows/ci.yml` | Low-Medium (adds a dev dep + surfaces latent order-dependence, which is the point) | CI runs randomized order; suite green across the matrix |

## Scope check

- Over-scope: do NOT change product behavior to make a test pass. If step 2 finds a real product
  isolation bug, that is a separate IPD (cross-referenced), not folded in here.
- Under-scope: fixing only the 5th test (leaving the class) - that is the mistake this IPD exists to
  avoid. Steps 1-3 target the class.

## Required tests / validation

- The reproducing order from step 1 must go from red to green after step 3.
- Full suite green under randomized ordering locally, then on the **full CI matrix** (these flakes are
  matrix/timing-specific; local single-platform green is not sufficient - AGENTS.md matrix discipline).
- No product-behavior test is weakened (assertions still fail on a genuine regression; they only stop
  being order/timing-dependent).

## Spec / documentation sync

None (test-only). If step 5 adds `pytest-randomly` to the dev extra, note it in CONTRIBUTING/dev docs.

## Open questions

1. Is adding `pytest-randomly` (dev-only) acceptable to institutionalize order-independence in CI, or
   keep order-randomization as a manual/periodic check? (Recommend: add it - cheap, dev-only, and it
   is the durable guard against this whole class.)
2. If step 2 finds a genuine PRODUCT isolation bug (e.g. `get_current_run()` returning a stale run
   after another run finalized), fix here or split to its own IPD? (Recommend: split; keep this IPD
   test-only.)

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Execution contract:
- Honesty rule (hard MUST): paste ACTUAL runner output when reporting passes; never claim an unrun pass.
- Matrix rule: these are matrix/timing flakes; validate on the full CI matrix, and prefer a randomized
  order, before considering done.
- Commit path-scoped (tests/ + conftest, and pyproject/CI only if step 5 is taken); never push without
  explicit human approval.
- On completion, `git mv` this IPD to `.agents/plans/executed/` (Status -> executed).

## Workflow history
- 2026-07-20 /assess-adjacent (opencode / its_direct/pt3-claude-opus-4.8-1m-us): drafted from the
  flake cluster surfaced during the show-config + assess-documentation executions; proposed 5 steps.
