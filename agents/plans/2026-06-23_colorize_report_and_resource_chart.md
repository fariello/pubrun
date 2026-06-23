# Implementation Plan: Colorize PBR Report & Add Resource Monitoring Chart

This plan outlines the changes to colorize the diagnostic report, respect the `--no-color` option, add standalone `cpu` and `mem` subcommands to display CPU and memory graphs over the life of a run, and rename the `report` subcommand to `show` with optional section filtering (`show [run_dir] [section]`). The `report` subcommand is kept as a hidden, undocumented alias of `show` for full backward compatibility.

## Proposed Changes

### Command Line Interface

#### [MODIFY] [__main__.py](file:///home/gfariello/VC/pubrun/src/pubrun/__main__.py)
- Register `show`, `res`, `cpu`, and `mem` subcommands.
- Add `show` subcommand parser (with `report` as a separate, hidden subparser using `help=argparse.SUPPRESS`). They will accept positional `run_dir` and `section` arguments, and `--depth` flag.
- Implement argument shifting logic: if the parsed `run_dir` is one of the known section names (`"logs"`, `"env"`, `"packages"`), shift it to `section` and set `run_dir = None` (defaulting to the latest run).
- Register `cpu`, `mem`, and `res` (with aliases `resources`, `monitor`, `chart`, `stats`) as standalone root subparsers.
- Pass the appropriate `metric` parameter (`"cpu"`, `"mem"`, or `"all"`) and the `section` parameter to the run handlers.
- Update nested alias collapse preprocessor to include the new command aliases (`res`, `cpu`, `mem`).

---

### Telemetry Reporting

#### [MODIFY] [diagnostics.py](file:///home/gfariello/VC/pubrun/src/pubrun/report/diagnostics.py)
- Update `print_resources_report(manifest_path, average=False, last=None, metric="all")` to filter charts based on the `metric` parameter:
  - If `metric == "cpu"`, only render the CPU utilization chart.
  - If `metric == "mem"`, only render the Memory (RSS) chart.
  - If `metric == "all"`, render both charts.
- Update `print_report(manifest_path, depth="standard", section=None)`:
  - If `section == "logs"`, read and print the contents of `stdout.log` (and `stderr.log` if present) from the run directory, then exit.
  - If `section == "env"`, extract and print only the environment variables block, then exit.
  - If `section == "packages"`, extract and print only the packages block, then exit.
  - Otherwise, print the full diagnostic report as usual.

---

### Verification and Tests

#### [NEW] [test_show_sections.py](file:///home/gfariello/VC/pubrun/tests/test_show_sections.py)
- Add tests verifying `pubrun show env`, `pubrun show packages`, and `pubrun show logs` print the correct segments.
- Add tests verifying argument shifting logic handles `pubrun show <section>` and `pubrun show <run-id> <section>` correctly.
- Add tests verifying `pubrun report` continues to function exactly like `pubrun show` but remains hidden in `--help`.

#### [MODIFY] [test_cli.py](file:///home/gfariello/VC/pubrun/tests/test_cli.py)
- Update mock assertions to reflect new parameter structures (`metric`, `section`, `last`).
- Verify that `pbr cpu`, `pbr mem`, and `pbr res` correctly call the resources report function with expected filters.

---

## Verification Plan

### Automated Tests
- Run `PYTHONPATH=src pytest tests/test_cli.py tests/test_reports.py tests/test_show_sections.py`
- Run the full test suite with `PYTHONPATH=src pytest` to ensure no regressions.

### Manual Verification
- Execute `pbr show` to verify the full report is printed.
- Execute `pbr show env` to verify only environment variables are listed.
- Execute `pbr show logs` to view log output.
- Execute `pbr cpu` and `pbr mem` to inspect single utilization graphs.
- Verify `pbr --help` lists `show`, `cpu`, `mem`, and `res` in alphabetical order, and does *not* list `report`.
