# IPD: Assess Testing - Coverage Gaps for New Features

- Date: 20260704
- Concern: testing rigor and completeness
- Scope: newly-added features from today (console resolve, tree RSS, profiling, transitive packages, event buffering, status summary)
- Status: PENDING (awaiting human approval; not executed)
- Author: OpenCode (its_direct/pt3-claude-opus-4.6-1m-us)

## Goal

Add regression tests for all features implemented today that currently have zero
or minimal test coverage. These are critical paths that passed manual verification
but have no automated protection against future regressions.

## Evidence (test suite run)

```
582 passed, 1 flake (ordering), 2 skipped
Overall coverage: 59%
```

Key files with untested new code:
- `capture/packages.py`: 49% (imported-transitive mode entirely untested)
- `capture/resources.py`: 50% (tree RSS Linux/macOS untested)
- `core.py`: 67% (profiling hooks untested)
- `capture/console.py`: 80% (Jupyter detection, non-TTY override untested)
- `events.py`: 79% (serialization error path untested)

## Findings

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence |
|----|----------|------------------|---------|------|---------|----------|
| TST-01 | High | Low | Testing | packages.py | `imported-transitive` mode has ZERO test coverage. PEP 508 parser, deduplication, required_by tracking — all untested. | Coverage: lines 62-107 uncovered |
| TST-02 | High | Low | Testing | resources.py | `_get_tree_rss_linux()` has no test. The /proc walk, child discovery, and RSS summation are unverified by automation. | Coverage: lines 65-94 uncovered |
| TST-03 | High | Low | Testing | resources.py | `_get_tree_rss_darwin()` has no test. The `ps -eo pid,ppid,rss` parse and tree walk are untested. | Coverage: lines 104-148 uncovered |
| TST-04 | Medium | Low | Testing | core.py | Phase profiling (`__enter__`/`__exit__` with cProfile) has no test. Correct .prof generation and orphan cleanup unverified. | Coverage: lines 264-324 uncovered |
| TST-05 | Medium | Low | Testing | console.py | `resolve_console_mode()` Jupyter detection path untested. `non_tty_mode` override untested. | Coverage: lines 14-21, 42-52 uncovered |
| TST-06 | Medium | Low | Testing | events.py | Non-serializable payload error path (json.dumps raising) untested. | Coverage: lines 83-88 uncovered |
| TST-07 | Low | Low | Testing | resources.py | `scope="tree"` integration with ResourceWatcher (passes scope, polls tree, reports in manifest) untested end-to-end. | No integration test for tree scope |
| TST-08 | Low | Low | Testing | status.py | Status summary line rendering (`_render_summary`) untested. | No test for summary output |
| TST-09 | Low | Low | Testing | core.py | `start()` double-checked locking (BUG-04 fix) has no concurrent test. | No threading test for race condition |
| TST-10 | Low | Low | Testing | core.py | ProvenanceFileProxy `write()`/`writelines()` hash accuracy untested. | No test for write-mode provenance |

## Proposed changes (ordered by value)

| Step | Source | Change | Files | Remediation Risk | Validation |
|------|--------|--------|-------|------------------|------------|
| 1 | TST-01 | Add `test_imported_transitive_mode`: mock sys.modules with known packages, verify transitive deps appear with correct `source`/`required_by`. Test PEP 508 parser with edge cases. | `tests/test_packages.py` (new or extend existing) | Low | pytest passes; covers lines 62-107 |
| 2 | TST-02 | Add `test_tree_rss_linux`: mock `builtins.open` for `/proc/<pid>/statm` and `/proc/<pid>/task/<pid>/children` reads. Verify sum includes self + children + grandchildren. Use mocks so it runs on all platforms. | `tests/test_resources.py` | Low | Runs on all CI OSes via mocks; covers lines 65-94 |
| 3 | TST-03 | Add `test_tree_rss_darwin`: mock `subprocess.check_output` for `ps -eo pid,ppid,rss` with synthetic 3-level tree output. Verify correct parse and sum. Use mocks so it runs on all platforms. | `tests/test_resources.py` | Low | Runs on all CI OSes via mocks; covers lines 104-148 |
| 4 | TST-04 | Add `test_phase_profiling_cprofile`: enable profiling in config, enter a phase, verify `profile-<name>.prof` exists and is valid pstats. Test orphan cleanup. | `tests/test_api.py` or `tests/test_profiling.py` (new) | Low | covers lines 264-324 |
| 5 | TST-05 | Add `test_resolve_console_mode_jupyter`: mock `_is_jupyter_kernel()` returning True, verify mode resolves to `jupyter_mode`. Test non-TTY with `isatty()=False`. | `tests/test_capture.py` or `tests/test_console.py` | Low | covers lines 14-52 |
| 6 | TST-06 | Add `test_event_non_serializable_payload`: pass an object() as payload to annotate(), verify warning logged and no crash. | `tests/test_api.py` | Low | covers lines 83-88 |
| 7 | TST-07 | Add `test_resource_watcher_tree_scope`: start a run with `scope="tree"`, verify manifest has `peak_tree_rss_bytes` field. | `tests/test_resources.py` | Low | Integration test |
| 8 | TST-08 | Add `test_status_summary_line`: create synthetic runs, verify `_render_summary()` output contains count, dates, status breakdown. | `tests/test_status.py` | Low | Unit test |
| 9 | TST-09 | Add `test_concurrent_start`: spawn 5 threads calling `start()` simultaneously, verify only one Run created. | `tests/test_api.py` | Low | Threading test |
| 10 | TST-10 | Add `test_provenance_write_mode_hash`: open a file in write mode via `pubrun.open()`, write data, close, verify `data_files.outputs[0].sha256` matches file. | `tests/test_api.py` | Low | covers write hash path |

## Deferred / out of scope

| Finding | Reason |
|---------|--------|
| (none) | All Low remediation risk — test additions never harm complexity/usability/security/functionality |

## Required tests / validation

All proposed tests must:
1. Pass on Python 3.8+ (no walrus operators, no 3.9+ features in tests)
2. Be deterministic (no sleeps, no ordering dependence)
3. Use mocks for platform-specific paths (so they run on all CI OSes)
4. Full regression: existing 583 tests unbroken

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution, and it is NOT auto-executed.
