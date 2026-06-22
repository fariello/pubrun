# Implementation Plan: Outstanding TODO.md Items

This plan details the implementation of the outstanding issues and test coverage gaps remaining in `TODO.md`.

## 1. Proposed Changes

### A. Test Coverage & Stability Gaps

#### [MODIFY] [test_status.py](file:///home/gfariello/VC/pubrun/tests/test_status.py)
- **P3-T10 (`clean` interactive prompting)**: Implement new test cases under `TestCleanRuns` that mock `builtins.input` using `monkeypatch` to verify:
  1. Interactive selection parsing (e.g. inputting `1-2`) and confirming deletion (`y`).
  2. Cancelling cleanup by entering an empty string or explicitly cancelling (`n`, `no`, `none`).
  3. Selecting `all` candidates but cancelling at the confirmation prompt.

#### [MODIFY] [test_events.py](file:///home/gfariello/VC/pubrun/tests/test_events.py)
- **P3-R4 (Critical Event Cap with `max_events=0`)**: Add `test_critical_event_cap_with_max_events_zero` under `TestEventStreamCriticalCap` to assert that when `max_tracked_events` is configured to `0`, `self._max_critical_events` resolves to the default minimum cap of `10,000`.

#### [MODIFY] [test_cli.py](file:///home/gfariello/VC/pubrun/tests/test_cli.py)
- **P3-T15 (Prevent Recursive Pytest)**: Update `test_run_tests_exits_zero` under `TestCliRunTests` to mock `subprocess.run` via monkeypatch. If a call matching `python -m pytest` is detected, mock a successful subprocess return without running the full test suite recursively, defusing the latent CI time bomb.

### B. CI / Infrastructure Coverage

#### [MODIFY] [pyproject.toml](file:///home/gfariello/VC/pubrun/pyproject.toml)
- Configure `pytest-cov` settings:
  1. Add `addopts = "--cov=src --cov-report=term-missing --cov-report=xml"` under `[tool.pytest.ini_options]`.
  2. Add `[tool.coverage.run]` setting the source to `src` and omitting `tests/*`.
  3. Add `[tool.coverage.report]` setting `show_missing = true`.

### C. Future Feature Considerations

#### [MODIFY] [__main__.py](file:///home/gfariello/VC/pubrun/src/pubrun/__main__.py)
- **Direct Bug Reporting command**:
  1. Implement `_run_bug_report()` to print environment diagnostics (pubrun version, python version, OS platform, machine, system time) and attempt to open `https://github.com/fariello/pubrun/issues/new` using Python's standard `webbrowser.open()`.
  2. Add `bug-report` subcommand parser to the subparsers dispatcher with aliases `feedback` and `issue`.
  3. Add dispatch logic for `args.command == "bug-report"`.

---

## 2. Verification Plan

### Automated Tests
- Run `PYTHONPATH=$(pwd)/src pytest` to verify the entire test suite passes, recursive pytest execution is avoided, and coverage reports are generated.

### Manual CLI Verification
- Run `pubrun bug-report` and verify environment context prints correctly and attempts to open the GitHub issue page.
- Run `pubrun clean` interactively with multiple test run folders to verify interactive prompts work as expected.
