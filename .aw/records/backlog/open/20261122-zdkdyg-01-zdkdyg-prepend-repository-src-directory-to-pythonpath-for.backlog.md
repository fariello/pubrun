- Id: zdkdyg
- Status: open
- Set: zdkdyg
- Work-Kind: bug
- Priority: medium
- Blocks-Release: next
- Summary: Prepend repository src directory to PYTHONPATH for subprocess tests in tests/conftest.py
- Short-Description: Prepend repository src directory to PYTHONPATH for subprocess tests in tests/conftest.py

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-22 created (aw backlog): Prepend repository src directory to PYTHONPATH for subprocess tests in tests/conftest.py

## Problem

`pyproject.toml` sets `pythonpath = ["src"]`, which adds the repository `src` directory to `sys.path` in the `pytest` process only. It does not update `os.environ["PYTHONPATH"]`.

When `pytest` runs inside an isolated git worktree whose active Python environment has an editable install pointing to another checkout, tests that spawn child Python processes via `subprocess.run([sys.executable, ...])` without setting `PYTHONPATH` (for example in `tests/test_report_subpackage_integrity.py`, `tests/test_import_modes.py`, `tests/test_checks_commands.py`, `tests/test_bench_command.py`, and `tests/test_show_sections.py`) import `pubrun` from the editable-installed checkout instead of the worktree under test. That causes false failures or false passes during worktree validation.

## Acceptance criteria

- Session-level test setup in `tests/conftest.py` prepends the repository's local `src` directory (when present) to `os.environ["PYTHONPATH"]` for the test session, or all subprocess test helpers prepend it consistently.
- Running `python3 -m pytest tests/test_import_modes.py tests/test_report_subpackage_integrity.py` inside a git worktree without setting `PYTHONPATH` manually imports `pubrun` from that worktree's `src` directory in every spawned subprocess.
