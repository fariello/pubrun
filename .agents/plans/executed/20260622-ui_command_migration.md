# Implementation Plan: UI Command Migration and Aliasing

This plan details the changes to migrate the primary terminal user interface (TUI) command from `tui` to `ui`, while maintaining backward-compatible aliases for both `tui` and `gui` in `pubrun`.

All changes will be implemented **locally** first. No commits will be pushed to the remote repository.

---

## 1. Codebase Modifications

### A. CLI Parser and Subcommand Dispatch

#### [MODIFY] [src/pubrun/__main__.py](file://~/VC/pubrun/src/pubrun/__main__.py)
1.  **Subcommands Set**:
    Update the `subcommands` check to include `"ui"`, `"tui"`, and `"gui"`:
    ```python
    subcommands = {"report", "methods", "rerun", "diff", "meta", "status", "clean", "combined", "cite", "run", "ui", "tui", "gui"}
    ```
2.  **Subparser Definition**:
    Rename the subparser command from `"tui"` to `"ui"`, add aliases `"tui"` and `"gui"`, and update descriptions:
    ```python
    ui_parser = subparsers.add_parser(
        "ui",
        aliases=["tui", "gui"],
        help="Launch the interactive pubrun dashboard.",
        description="Launch the interactive pubrun dashboard.",
        epilog=f"Examples:\n  {prog_name} ui\n  {prog_name} ui --dir /path/to/runs",
    )
    ui_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help="Override the output directory to scan (default: configured output_dir or ./runs).")
    ```
3.  **Subcommand Dispatching**:
    Modify the command dispatch branch to check for `"ui"`, `"tui"`, or `"gui"` and adjust the dependency missing warning message to refer to the UI:
    ```python
    elif args.command in {"ui", "tui", "gui"}:
        try:
            from pubrun.tui.app import PubrunTUIApp
            app = PubrunTUIApp(output_dir=getattr(args, "dir", None))
            app.run()
        except ImportError:
            _print_error(
                "pubrun is by default zero-dependency based and does not install the TUI dashboard.\n"
                "Run `pip install textual rich` (or `pip install \"pubrun[tui]\"`) to run the UI."
            )
            sys.exit(1)
    ```

---

## 2. Test Suite Modifications

### A. Subcommand Checklist Test

#### [MODIFY] [tests/test_cli.py](file://~/VC/pubrun/tests/test_cli.py)
Update the checked subcommands list to replace `"tui"` with `"ui"`, `"tui"`, `"gui"`.

### B. TUI Command Tests

#### [MODIFY] [tests/test_tui.py](file://~/VC/pubrun/tests/test_tui.py)
*   Update `test_tui_cli_parser_and_run()` to test parsing for all three invocations: `"ui"`, `"tui"`, and `"gui"`.
*   Update `test_tui_missing_dependencies_prints_notice()` to verify execution for `"ui"`.

---

## 3. Verification Plan

### Local Automated Tests
Run the entire pytest suite to ensure all unit tests pass, verifying both the new `ui` command and its aliases:
```bash
~/venv/p3.14/bin/pytest
```

### Manual CLI Checks
Verify that the help message lists `ui` (and its aliases) correctly, and that launching with each form attempts to load the app correctly:
```bash
~/venv/p3.14/bin/python -m pubrun --help
~/venv/p3.14/bin/python -m pubrun ui --help
~/venv/p3.14/bin/python -m pubrun tui --help
~/venv/p3.14/bin/python -m pubrun gui --help
```
