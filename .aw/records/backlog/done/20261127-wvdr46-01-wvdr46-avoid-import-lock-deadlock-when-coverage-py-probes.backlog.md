- Id: wvdr46
- Status: done
- Graduated-To: wvdr46
- Set: wvdr46
- Work-Kind: bug
- Priority: medium
- Summary: Avoid import-lock deadlock when coverage.py probes pubrun submodules during auto-start
- Short-Description: Avoid import-lock deadlock when coverage.py probes pubrun submodules during auto-start
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-28 done (aw backlog): closed by aw agy run: IPD 3ed2o4 executed (every IPD carrier is executed and this run executed .aw/records/plans/executed/20261127-wvdr46-01-3ed2o4-avoid-import-lock-deadlock-when-coverage-py-probes-pubrun-su.ipd.md); evidence .aw/records/plans/executed/20261127-wvdr46-01-3ed2o4-avoid-import-lock-deadlock-when-coverage-py-probes-pubrun-su.ipd.md
- 2026-11-28 graduated (aw backlog): graduated by run run-20261128T034305Z-475903: 3ed2o4
- 2026-11-28 created (aw backlog): Avoid import-lock deadlock when coverage.py probes pubrun submodules during auto-start

Running pytest -p randomly with --cov=pubrun.<submodule> on Python 3.14 (coverage.py 7.1.0 with sys.monitoring) deadlocks during pytest startup before test collection and creates stray runs/pubrun-pytest-* directories in the repository root. Faulthandler shows coverage.inorout.file_and_path_for_module calling importlib.util.find_spec('pubrun.<submodule>') inside sysmon_py_start, which imports src/pubrun/__init__.py and runs _execute_boot_sequence() when PUBRUN_IMPORT_MODE is unset. That spawns the pubrun-hw background thread (src/pubrun/tracker.py::_collect_hardware -> write_startup_manifest -> _get_dep -> importlib.import_module), deadlocking with the main thread on Python _ModuleLock ('pubrun.capture' / 'pubrun.capture.subprocesses'). Setting PUBRUN_IMPORT_MODE=minimal avoids the deadlock.
