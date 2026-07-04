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

## Project conventions discovered (Step 0)

- Pending-plans location: `.agents/plans/pending/` (YYYYMMDD-slug.md)
- Stack: Python 3.8+, zero runtime deps except tomli on <3.11
- Guiding principles: Universal fallback (KISS, general case, honest docs)
- Domain invariant: pubrun must never crash the host script. Failures in tree
  RSS or profiling must degrade gracefully (log + skip), never raise.

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
| 1 | BUG2-01, BUG2-06 | Rewrite `_get_tree_rss_darwin()` to: (a) always start with self RSS via `_get_rss_darwin()`; (b) use `ps -eo pid,ppid,rss` once to get all processes, then filter in Python for descendants of our PID. This solves both the grandchildren problem (full tree walk in Python) and the no-children fallback (self RSS is always included). Single subprocess call regardless of tree depth. | `capture/resources.py` | Low | Test: process with no children → tree RSS == self RSS. Test (if feasible): spawn child + grandchild → tree includes all. |
| 2 | BUG2-03 | For yappi backend, add a module-level `_yappi_active: bool = False` guard. In `phase.__enter__`: if `_yappi_active` is True, log a warning and skip (don't call `yappi.start()` again). In `__exit__`: only call `yappi.stop()` if this phase instance started it. This prevents interference from concurrent or nested phases. | `core.py` | Low | Test: nested `pubrun.phase()` blocks with yappi enabled; verify no crash and outer phase profile is complete. |
| 3 | BUG2-04 | Track active profilers on the Run instance (`self._active_profilers: List[cProfile.Profile]`). In `_finalize_state()`, disable any still-enabled profilers. This handles orphaned `phase.__enter__()` calls that never reached `__exit__()`. | `tracker.py` + `core.py` | Low | Test: `p = pubrun.phase("x"); p.__enter__()` without `__exit__`; call `run.stop()`; verify profiler disabled and no resource leak. |

## Deferred / out of scope

| Finding ID | Remediation Risk | Axis | Reason |
|------------|------------------|------|--------|
| (none) | — | — | All findings Low remediation risk. |

## Required tests / validation

1. **macOS tree RSS no-children**: mock `ps -eo pid,ppid,rss` to return only self;
   verify `_get_tree_rss_darwin()` returns self RSS (not 0). Platform-skip on non-macOS.
2. **macOS tree RSS with descendants**: mock `ps -eo pid,ppid,rss` with a 3-level
   tree; verify sum includes all descendants.
3. **Yappi concurrent guard**: enable yappi profiling, enter two nested
   `pubrun.phase()` blocks; verify no `yappi.YappiError` and outer profile saved.
4. **Orphaned profiler cleanup**: call `phase.__enter__()` without `__exit__()`;
   call `run.stop()`; verify no `cProfile.Profile` remains enabled.
5. **Domain invariant**: tree RSS failure (mock subprocess to raise) must not
   propagate — returns 0 or self RSS gracefully.
6. **Full regression**: 583+ tests green.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution, and it is NOT auto-executed.
