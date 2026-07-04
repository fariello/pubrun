# IPD: Assess Bugs (Round 2) - New Code Correctness

- Date: 20260704
- Concern: bugs and correctness
- Scope: newly-added code from today's session (console resolve, tree RSS, profiling, transitive packages)
- Status: PENDING (awaiting human approval; not executed)
- Author: OpenCode (its_direct/pt3-claude-opus-4.6-1m-us)

## Goal

Fix bugs introduced in today's new feature implementations. This is a focused
follow-up to the earlier bugs assessment, targeting only the code added since
the first bugs IPD was executed.

## Findings

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence (file:line) |
|----|----------|------------------|---------|------|---------|----------------------|
| BUG2-01 | Medium | Low | QA/Engineer | tree RSS macOS | `_get_tree_rss_darwin()` uses `pgrep -P <pid>` which only returns DIRECT children (one level). Grandchildren and deeper descendants are missed. For a multiprocessing pool with worker sub-children, the tree total is incomplete. | `capture/resources.py:105-108` — `pgrep -P` is not recursive. |
| BUG2-02 | Medium | Low | Engineer | tree RSS Linux | `/proc/<pid>/task/<pid>/children` only lists direct children of that thread group leader. For processes with deeply nested child trees (e.g., bash → python → worker), grandchildren require recursive traversal — which the code DOES do via `pids_to_check`, BUT the children file is read from `/proc/<p>/task/<p>/children` which requires the child PID to also be a thread group leader. If a child has threads, its sub-children are listed under `/proc/<child>/task/<child>/children`, which IS correctly walked. **On re-analysis: the walk is correct.** Downgrading to informational. | `capture/resources.py:84-88` — recursive walk via pids_to_check is correct. |
| BUG2-03 | Low | Low | Engineer | profiling | `yappi.start()` is called globally (not per-phase). If two `pubrun.phase()` blocks run concurrently (e.g., in threads), they'll both call `yappi.start()`/`yappi.stop()` creating interference. Unlikely in practice (phases are typically sequential) but architecturally unsound. | `core.py:264-265` — global yappi state, no guard against concurrent phases. |
| BUG2-04 | Low | Low | QA | profiling | If `phase.__enter__` succeeds but `__exit__` is never called (e.g., user does `p = pubrun.phase("x"); p.__enter__()` without context manager and then the exception is caught elsewhere), the cProfile profiler remains enabled indefinitely, profiling ALL subsequent code and accumulating unbounded memory. | `core.py:261-262` — profiler.enable() with no timeout or safety bound. |
| BUG2-05 | Low | Low | Engineer | transitive packages | The `required_by` list for a transitive package is a mutable reference shared with the `required_by` dict. If two imported packages both require the same transitive dep, the list is appended to in-place and the record's `required_by` field updates silently (correct behavior, but confusing because it mutates after append). Not actually a bug — just a subtle shared-reference pattern that works correctly. | `capture/packages.py:94` — record references `required_by[dep_lower]` directly. |
| BUG2-06 | Medium | Low | QA/Engineer | tree RSS macOS | `pgrep -P <pid>` raises `subprocess.CalledProcessError` (exit code 1) when there are NO children. The `except Exception` catches this, but then returns 0 for tree RSS — which is wrong (the tree RSS should be at least the self RSS). The main process's own RSS is lost. | `capture/resources.py:104-108` — if pgrep fails (no children), total = 0 instead of self RSS. |
| BUG2-07 | Low | Low | Engineer | console resolve | `resolve_console_mode()` checks `sys.stdout.isatty()` but during early boot, `sys.stdout` might already be replaced by a prior `ConsoleInterceptor` from a previous run in the same process (test scenarios). The `isatty()` call on `TqdmSafeTee` delegates to the original stream, so this is actually correct. Not a bug. | `capture/console.py:47` — delegates correctly via `__getattr__`. |

## Proposed changes (ordered, validatable)

| Step | Source finding IDs | Change | Files | Remediation Risk | Validation |
|------|-------------------|--------|-------|------------------|------------|
| 1 | BUG2-01 | On macOS, use recursive `pgrep` or walk children iteratively: call `pgrep -P` for each discovered child PID to find grandchildren. Or use a single `ps -eo pid,ppid` and filter the tree in Python. | `capture/resources.py` | Low | Test: spawn a child that spawns a grandchild; verify tree RSS includes all 3. |
| 2 | BUG2-06 | When `pgrep -P` fails (no children), fall back to returning just the self RSS via `_get_rss_darwin()` instead of 0. Restructure: always include self RSS, then add children's RSS on top. | `capture/resources.py` | Low | Test: process with no children, verify tree RSS == self RSS. |
| 3 | BUG2-03 | For yappi backend, track a module-level `_yappi_active` flag and skip `yappi.start()` if already running (nested/concurrent phases). Or use cProfile per-phase instances only (yappi doesn't support per-phase easily). Add a warning if concurrent phase detected with yappi. | `core.py` | Low | Test: nested phases with yappi; verify no crash. |
| 4 | BUG2-04 | Add an atexit or weakref-based safety net: if a profiler was enabled but never disabled (orphaned phase), disable it during `_finalize_state()`. | `tracker.py` or `core.py` | Low | Test: enter phase without exit; verify profiler stopped at run.stop(). |

## Deferred / out of scope

| Finding ID | Remediation Risk | Axis | Reason |
|------------|------------------|------|--------|
| (none) | — | — | All findings Low remediation risk. |

## Required tests / validation

1. macOS tree RSS with grandchildren (platform-skip on non-macOS).
2. No-children fallback: tree RSS equals self RSS.
3. Yappi concurrent/nested phase guard.
4. Orphaned profiler cleanup on finalization.
5. Full regression: 583+ tests green.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution, and it is NOT auto-executed.
