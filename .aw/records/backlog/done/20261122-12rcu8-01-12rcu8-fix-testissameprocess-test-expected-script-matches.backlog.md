- Id: 12rcu8
- Status: done
- Graduated-To: 4h2qwz
- Set: 12rcu8
- Work-Kind: bug
- Priority: low
- Summary: Fix TestIsSameProcess.test_expected_script_matches failure under pytest-xdist workers in tests/test_liveness.py
- Short-Description: Fix TestIsSameProcess.test_expected_script_matches failure under pytest-xdist workers in tests/test_liveness.py

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-23 done (aw set): Duplicate of ivpkar (carried by plan vv4vdd)
- 2026-11-23 graduated (aw set): salvaged plan 4h2qwz from aw/lane/12rcu8 (3fd18c2)
- 2026-11-22 created (aw backlog): Fix TestIsSameProcess.test_expected_script_matches failure under pytest-xdist workers in tests/test_liveness.py

## Problem

`tests/test_liveness.py::TestIsSameProcess::test_expected_script_matches` fails when run under `pytest-xdist` parallel workers (including `aw suite`, which runs 6 workers), while passing in a single-process `pytest` run.

In a `pytest-xdist` worker subprocess on Linux, `/proc/<pid>/cmdline` invokes the Python interpreter with an inline `execnet` bootstrap command (`python -c ...`) rather than a `pytest` script token. Because `test_expected_script_matches` checks `_check_command_linux(os.getpid(), "pytest") is not None` (which returns `False`, not `None`, so the skip condition does not trigger) and then asserts `is_same_process(os.getpid(), time.time(), expected_script="pytest") is True`, the assertion fails under xdist.

## Acceptance criteria

- `tests/test_liveness.py::TestIsSameProcess::test_expected_script_matches` passes under both standalone `python3 -m pytest tests/test_liveness.py -v` and parallel `pytest-xdist` execution (`aw suite`).
- The test verifies `is_same_process(..., expected_script=...)` against a real process whose command line contains the expected script token (or spawns a short-lived child script) rather than assuming the current pytest worker process command line contains `"pytest"`.
