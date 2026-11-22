# Evidence - assess-testing 20260704-234714

## Test suite execution (real evidence, not self-report)

Command: `pytest tests/ -q --cov=src/pubrun --cov-report=term-missing`
Result: 582 passed, 1 failed (ordering flake), 2 skipped
Duration: 86.94s
Coverage: 59% overall

## Coverage gaps identified (lines uncovered in new code)

| File | Overall % | Untested new-code lines |
|------|-----------|------------------------|
| capture/packages.py | 49% | 62-107 (imported-transitive mode) |
| capture/resources.py | 50% | 65-94 (tree Linux), 104-148 (tree macOS), 176-181 (tree poll) |
| core.py | 67% | 264-288 (profiling enter), 296-324 (profiling exit) |
| capture/console.py | 80% | 14-21 (Jupyter detect), 42-43, 50-52 (non-TTY) |
| events.py | 79% | 83-88 (serialization error) |

## Existing test files reviewed

- tests/test_api.py
- tests/test_capture.py
- tests/test_resources.py
- tests/test_status.py
- tests/test_import_modes.py
- tests/test_cli.py
- tests/test_tracker.py

None of these contain tests for the features added today (transitive packages,
tree RSS, profiling, console mode resolution, event buffering error path).
