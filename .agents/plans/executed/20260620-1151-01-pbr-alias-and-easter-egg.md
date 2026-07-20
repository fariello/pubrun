# Implementation Plan - Revert pr alias to pbr and Restore Easter Egg

This plan details the design and implementation changes to:
1. Replace the problematic `pr` alias with `pbr` in `pyproject.toml` to avoid conflicts with standard Unix coreutils `pr`.
2. Restore and implement the undocumented `pbr me` easter egg:
   - If someone runs `pbr me`, print `ASAP` and exit with `0`.
3. Update dynamic CLI program name resolution to recognize `pbr` instead of `pr`.
4. When `pubrun` or `pbr` is run without subcommands or execution flags:
   - Display the help menu.
   - Scan for and count runs in the output directory (e.g. `runs/`), printing a helpful summary of how many runs exist and prompting the user how to list them (e.g., `Found 3 run(s) in the output directory. Run 'pbr status' to view them.`).
5. Update unit tests to reflect the transition and verify help outputs, run scanning on help, and alias registration.

## User Review Required

> [!NOTE]
> The `pr` command is a standard utility on Unix (`/usr/bin/pr` for paginating files), which causes terminal hangs and shell collisions. Moving to `pbr` resolves these conflicts cleanly.

---

## Proposed Changes

### [Component] Packaging / CLI Entrypoints

#### [MODIFY] [pyproject.toml](file://~/VC/pubrun/pyproject.toml)
- Remove `pr = "pubrun.__main__:main"` from `[project.scripts]`.
- Add `pbr = "pubrun.__main__:main"` to `[project.scripts]`.

---

### [Component] CLI Main Entrypoint

#### [MODIFY] [__main__.py](file://~/VC/pubrun/src/pubrun/__main__.py)
- In the dynamic program name checker:
  ```python
  prog_name = Path(sys.argv[0]).name if sys.argv[0] else "pubrun"
  if prog_name not in ("pubrun", "pbr"):
      prog_name = "pubrun"
  ```
- Implement the `pbr me` easter egg at the beginning of `main()`:
  ```python
  if len(sys.argv) >= 2 and prog_name == "pbr" and sys.argv[1] == "me":
      print("ASAP")
      sys.exit(0)
  ```
- At the end of `main()`, if no commands or options were executed (`if not executed:`):
  - Print the help: `parser.print_help()`.
  - Scan for and count runs:
    ```python
    try:
        from pubrun.status import scan_runs
        runs = scan_runs()
        if runs:
            print(f"\nFound {len(runs)} run(s) in the output directory. Run '{prog_name} status' to view them.")
        else:
            print("\nNo runs found in the output directory.")
    except Exception:
        pass
    ```

---

### [Component] Test Suite

#### [MODIFY] [test_cli.py](file://~/VC/pubrun/tests/test_cli.py)
- Update `test_pr_alias_registered_in_pyproject` to check for `pbr = "pubrun.__main__:main"` instead of `pr`.
- Update `test_subcommand_help_examples` to assert `pbr` in help output:
  ```python
  assert "pubrun " in res.stdout or "pbr " in res.stdout
  ```
- Add a new test checking that running `pbr me` triggers the easter egg (by mocking `sys.argv` / execution name):
  ```python
  def test_pbr_me_easter_egg(self):
      # Invoke main directly with modified argv[0] and argv[1]
      import sys
      from unittest.mock import patch
      from pubrun.__main__ import main

      with patch.object(sys, 'argv', ['/path/to/pbr', 'me']):
          with pytest.raises(SystemExit) as exc_info:
              main()
          assert exc_info.value.code == 0
          # We can also mock/capture stdout here to assert "ASAP"
  ```
- Add a new test checking that running without subcommands/flags outputs the help menu along with the run count summary.

---

## Verification Plan

### Automated Tests
- Run `python -m pytest tests/ -q` to verify the whole suite passes, including the updated/new alias, easter egg, and help scanning tests.

### Manual Verification
- Run `pbr me` and verify it outputs `ASAP`.
- Run `pbr` (with no arguments) in a directory containing runs and verify it outputs the help menu followed by `Found X run(s) in the output directory. Run 'pbr status' to view them.`.
- Run `pbr` in a directory with no runs and verify it says `No runs found in the output directory.`.
