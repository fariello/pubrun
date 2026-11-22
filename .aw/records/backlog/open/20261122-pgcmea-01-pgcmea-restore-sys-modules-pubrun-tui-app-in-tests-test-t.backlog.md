- Id: pgcmea
- Status: open
- Set: pgcmea
- Work-Kind: bug
- Priority: low
- Summary: Restore sys.modules['pubrun.tui.app'] in tests/test_tui.py::test_tui_cli_parser_and_run to prevent order-dependent TUI test failure
- Short-Description: Restore sys.modules['pubrun.tui.app'] in tests/test_tui.py::test_tui_cli_parser_and_run to prevent order-dependent TUI test failure
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-22 created (aw backlog): Restore sys.modules['pubrun.tui.app'] in tests/test_tui.py::test_tui_cli_parser_and_run to prevent order-dependent TUI test failure

tests/test_tui.py::test_tui_cli_parser_and_run overwrites sys.modules['pubrun.tui.app'] with a unittest.mock.Mock without restoring or removing it on teardown. When tests run out of file order (for example under pytest -p randomly), TestTuiResourceView.test_resource_view_populates_and_degrades imports the leaked Mock instead of the real PubrunTUIApp and fails. Use monkeypatch.setitem(sys.modules, 'pubrun.tui.app', mock_module) or a try/finally restore.
