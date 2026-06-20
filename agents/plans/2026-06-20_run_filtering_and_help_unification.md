# Implementation Plan - Run Filtering, Help Unification, and Active Run Usability

This plan details the design and implementation changes to:
1. Standardize runs filtering across all commands that operate on run listings or auto-select run files: `status`, `clean`, `report`, `combined`, `methods`, and `rerun`.
2. Implement a reusable `filter_runs` function in `src/pubrun/status.py`.
3. Support the following filters uniformly:
   - `-f`, `--filter` (plain string or regex query)
   - `-s`, `--status` (comma-separated list of status labels)
   - `-n`, `--limit` (maximum number of runs to return)
   - `--older-than` (age threshold, e.g., `7d` or `24h`)
   - `--exit-code` (filter by execution returncode)
4. Ensure both `pubrun help <command>` and `pubrun <command> help` route to the subcommand's help menu.
5. Move older planning files into `agents/plans/` using standard dated naming conventions and clean up the empty `docs/plans/` directory.
6. Enhance active/crashed run diagnostics output in `pubrun report`:
   - Append the elapsed duration to the `Started` line in `(Xd HH:MM:SS status)` format.
   - Display the run's current working directory (`CWD`).
   - Move the running/crashed state message after the Run Details block, printing it in bold and color (yellow for `STILL RUNNING`, red for `CRASHED`).
7. Auto-detect and close out crashed runs (dead processes with active locks):
   - When a local run is scanned/inspected and determined to have a lock file but its process is dead, write a fallback `manifest.json` (with `outcome = "crashed"` and details hydrated from the lock file).
   - Delete the `.pubrun.lock` file.
   - Print a warning/info message to `sys.stderr` indicating that the crashed run has been closed out.
   - Map `outcome = "crashed"` to `STATUS_CRASHED` during manifest loading so that closed-out runs retain the correct status classification.

## User Review Required

No high-risk changes are introduced. The filtering options expand capabilities for `clean` and add querying features for other commands when target folders/run IDs are omitted. Backward compatibility is fully maintained.

---

## Proposed Changes

### [Component] File Move and Cleanup (Git)
- Move `docs/plans/20260605-0200-p1-drift-reconciliation-implementation-plan.md` to `agents/plans/2026-06-05_drift_reconciliation_implementation_plan.md` via `git mv`.
- Rename `agents/plans/pubrun_import_mode_implementation_plan.md` to `2026-06-04_pubrun_import_mode_implementation_plan.md` via `git mv`.
- Delete the now empty `docs/plans/` directory.

---

### [Component] Run Filtering Logic

#### [MODIFY] [status.py](file:///home/gfariello/VC/pubrun/src/pubrun/status.py)
- Implement `filter_runs()` to apply filters to a list of `RunInfo` objects:
  ```python
  def filter_runs(
      runs: List[RunInfo],
      filter_str: Optional[str] = None,
      status_filter: Optional[str] = None,
      limit: Optional[int] = None,
      older_than: Optional[str] = None,
      exit_code: Optional[int] = None,
  ) -> List[RunInfo]:
  ```
- Refactor `clean_runs()` to call `filter_runs()` and support the new query arguments (`filter_str`, `limit`, `exit_code`). Keep `older_than_days` and list-based `status_filter` as backward-compatible arguments.
- Add `close_out_crashed_run(run_dir: Path, lock_data: Optional[Dict[str, Any]])` to write a fallback `manifest.json` and delete `.pubrun.lock`.
- Update `_load_from_manifest()` to map `outcome == "crashed"` to `STATUS_CRASHED`.
- Update `RunInfo._classify()` to detect `STATUS_CRASHED` on local runs with lock files, invoke `close_out_crashed_run()`, and reload from the new manifest.

---

### [Component] CLI Main Entrypoint

#### [MODIFY] [__main__.py](file:///home/gfariello/VC/pubrun/src/pubrun/__main__.py)
- Implement `_add_run_filter_args(parser: argparse.ArgumentParser, include_limit: bool = True)` to easily attach the shared filter parameters to subparsers.
- Attach the standard filter arguments to:
  - `status_parser`
  - `clean_parser` (replaces its custom `--status` and `--older-than` with the shared ones)
  - `report_parser`
  - `combined_parser`
  - `methods_parser` (without `--limit`)
  - `rerun_parser` (without `--limit`)
- Update preprocessing in `main()` to map `<command> help` to `<command> --help`:
  ```python
  subcommands = {"report", "methods", "rerun", "diff", "meta", "status", "clean", "combined", "cite", "run", "tui"}
  if len(sys.argv) > 1:
      if sys.argv[1] == "help":
          if len(sys.argv) > 2 and sys.argv[2] in subcommands:
              sys.argv = [sys.argv[0], sys.argv[2], "--help"]
          else:
              sys.argv = [sys.argv[0], "--help"]
      elif sys.argv[1] in subcommands and len(sys.argv) > 2 and sys.argv[2] == "help":
          sys.argv = [sys.argv[0], sys.argv[1], "--help"]
  ```
- Update `_get_manifest_path()` to accept filters and apply them when auto-detecting the latest run:
  ```python
  def _get_manifest_path(
      run_dir: str,
      filter_str: Optional[str] = None,
      status_filter: Optional[str] = None,
      older_than: Optional[str] = None,
      exit_code: Optional[int] = None
  ) -> str:
  ```
- Update `_run_methods()` and `_run_rerun()` to accept these filters and pass them to `_get_manifest_path()`.
- Update `_run_status()` and `_run_clean()` to apply all filtering parameters.
- Update `_run_combined()` to filter run logs when no explicit `run_ids` are supplied.
- Update subcommand dispatching in `main()` to pull and pass all query parameters.
- Update `_run_report` handling of `RunInProgressOrCrashedError`:
  - Format the `Started` line with elapsed time.
  - Print the run's `CWD`.
  - Shift the status message after the Run Details list, printing in bold yellow (for `running`) or bold red (for `crashed`).

---

### [Component] Test Suite

#### [MODIFY] [test_status.py](file:///home/gfariello/VC/pubrun/tests/test_status.py)
- Add unit tests for `filter_runs()`.
- Verify backward compatibility for `clean_runs()` (list status filters and `older_than_days` float parameter).
- Add tests for `close_out_crashed_run()` and the automatic close-out trigger in `RunInfo`.

#### [MODIFY] [test_cli.py](file:///home/gfariello/VC/pubrun/tests/test_cli.py)
- Add tests verifying `pubrun help <command>` and `pubrun <command> help` behave identically.
- Add tests verifying filtering logic on `clean`, `report`, `combined`, `methods`, and `rerun`.
- Add tests verifying new formatted error output for locked/running runs in `pubrun report`.

---

## Verification Plan

### Automated Tests
- Run `python -m pytest tests/ -q` to verify the entire test suite passes.

### Manual Verification
- Test `pubrun report --status failed` and check if it runs reports on all failed runs.
- Test `pubrun clean --older-than 1d --limit 1` and verify candidate list displays correct selections.
- Run `pubrun status help` and `pubrun help status` to verify correct help redirection.
- Test `pubrun report` on a running/locked run directory and verify the CWD and elapsed started timestamp print correctly with the status popped in bold yellow.
- Simulate a crashed run (dead process with a lock file), run `pubrun status`, and verify it detects it, prints the close-out message, and replaces the lock with a fallback manifest.
