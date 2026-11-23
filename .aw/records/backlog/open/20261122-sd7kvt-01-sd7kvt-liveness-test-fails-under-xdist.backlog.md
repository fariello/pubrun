- Id: sd7kvt
- Status: open
- Set: sd7kvt
- Work-Kind: bug
- Priority: low
- Summary: tests/test_liveness.py::TestIsSameProcess::test_expected_script_matches fails under pytest-xdist (aw suite)
- Short-Description: tests/test_liveness.py::TestIsSameProcess::test_expected_script_matches fails under pytest-xdist (aw suite)
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-22 created (aw backlog): tests/test_liveness.py::TestIsSameProcess::test_expected_script_matches fails under pytest-xdist (aw suite)

Observed while executing IPD 3tvesf (2026-11-22, git af36c85, Linux, CPython 3.14.6). aw suite reported 1 failed, 1493 passed; the failure was tests/test_liveness.py::TestIsSameProcess::test_expected_script_matches with 'assert is_same_process(os.getpid(), time.time(), expected_script="pytest") is True' returning False. Reproduced deterministically with 'python3 -m pytest tests/test_liveness.py -n 2' and never with serial runs (15/15 passes; full serial 'pytest tests/ -v' gave 1492 passed, 2 skipped). Cause: an xdist worker's /proc/<pid>/cmdline is '<python> -u -c import sys;exec(eval(sys.stdin.readline()))', which contains no 'pytest'. The functional-skip probe _check_command_linux(os.getpid(), "pytest") returns a non-None False (the command check works but does not match), so the test does not skip. Fix direction (unverified): derive expected_script from the actual /proc cmdline of the current process, or skip when PYTEST_XDIST_WORKER is set.
