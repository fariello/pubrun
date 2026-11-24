- Id: o9c3gr
- Status: open
- Set: o9c3gr
- Work-Kind: bug
- Priority: low
- Summary: Use monkeypatch in tests/test_tui.py::test_tui_missing_dependencies_prints_notice instead of permanently deleting sys.modules['pubrun.tui.app']
- Short-Description: Use monkeypatch in tests/test_tui.py::test_tui_missing_dependencies_prints_notice instead of permanently deleting sys.modules['pubrun.tui.app']
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-24 created (aw backlog): Use monkeypatch in tests/test_tui.py::test_tui_missing_dependencies_prints_notice instead of permanently deleting sys.modules['pubrun.tui.app']

## Problem

`tests/test_tui.py::test_tui_missing_dependencies_prints_notice` deletes `sys.modules["pubrun.tui.app"]` directly (`del sys.modules["pubrun.tui.app"]`) without restoring the original module entry when the test finishes. Later tests in the same pytest process re-import `pubrun.tui.app` and create a new `PubrunTUIApp` class object (and nested `PubrunTUIApp.RefreshSidebar` message class), while sibling test modules such as `tests/test_tui_widgets.py` still hold references to the `PubrunTUIApp` class imported at collection time. Any code that imports `PubrunTUIApp.RefreshSidebar` from `sys.modules["pubrun.tui.app"]` then posts a message class that does not match the `@on(RefreshSidebar)` handler bound to the earlier `PubrunTUIApp` instance.

## Acceptance criteria

1. Update `tests/test_tui.py::test_tui_missing_dependencies_prints_notice` to use `monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)` (or equivalent `mock.patch.dict`) so the original module entry is restored after the test completes.
2. Verify `python3 -m pytest tests/test_tui.py tests/test_tui_widgets.py` leaves `sys.modules["pubrun.tui.app"]` identical before and after `test_tui_missing_dependencies_prints_notice` and passes with 0 failures.
