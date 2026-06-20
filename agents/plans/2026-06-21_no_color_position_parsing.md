# Implementation Plan - Support --no-color Flag globally in Any Position

This plan details the design and implementation changes to fix the CLI parsing error when `--no-color` is passed after subcommands (e.g., `pubrun report <run_id> --no-color`).

## User Review Required

> [!NOTE]
> This change modifies how arguments are preprocessed in `sys.argv` before parsing. It is designed to be completely transparent and backward-compatible.

---

## Proposed Changes

### [Component] CLI Argument Parsing

#### [MODIFY] [__main__.py](file://~/VC/pubrun/src/pubrun/__main__.py)
- Preprocess `sys.argv` at the beginning of `main()` to look for `--no-color`.
- If `--no-color` is found:
  - If the subcommand is `run` and `--no-color` appears at or after `run`, do not remove it (to preserve it for the subprocess command).
  - Otherwise, set `os.environ["NO_COLOR"] = "1"`, record that it was present, and filter it out of `sys.argv`.
- After parsing arguments, if `--no-color` was present in the command line, manually set `args.no_color = True` to ensure downstream logic functions correctly.

---

### [Component] Tests

#### [MODIFY] [test_cli.py](file://~/VC/pubrun/tests/test_cli.py)
- Add a new test case `test_report_no_color_any_position` under `TestCliColorControl` to verify that `pubrun report <run_id> --no-color` runs successfully with exit code 0 and suppresses color output.
- Add a test verifying `pubrun run --mode minimal -- python -c "import sys; print(sys.argv)" --no-color` preserves the `--no-color` flag for the subprocess.

---

## Verification Plan

### Automated Tests
- Run `pytest` to execute all tests.

### Manual Verification
- Execute `pubrun report --no-color` and `pubrun report <run_id> --no-color` to ensure they execute successfully without color.
