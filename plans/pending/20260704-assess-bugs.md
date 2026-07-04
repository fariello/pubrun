# IPD: Assess Bugs - Correctness and Logic Defects

- Date: 2026-07-04
- Concern: bugs and correctness
- Scope: whole project (src/pubrun/)
- Status: PENDING (awaiting human approval; not executed)
- Author: OpenCode (its_direct/pt3-claude-opus-4.6-1m-us)

## Goal

Identify and fix logic errors, contract violations, concurrency bugs, and
incorrect behavior in pubrun's codebase. These are defects that produce wrong
output, lose data, or fail on reachable paths — not performance or style issues.

## Project conventions discovered (Step 0)

- Guiding principles: Universal fallback (KISS, honest docs, general case).
- Pending-plans location: `plans/pending/` (established convention).
- Contributor contract: `AGENTS.md` documents workflows and plan lifecycle.
- Stack: Python 3.8+, zero runtime deps except `tomli` on <3.11.

## Findings

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence (file:line) |
|----|----------|------------------|---------|------|---------|----------------------|
| BUG-01 | High | Low | Engineer/QA | ResourceWatcher macOS | `_get_rss_darwin()` uses `resource.getrusage(RUSAGE_SELF).ru_maxrss` which returns the **peak** RSS (high-water mark), not the **current** RSS. On macOS, `ru_maxrss` is the maximum resident set size ever reached, so it can never decrease — making `end_rss_bytes` identical to `peak_rss_bytes` and the "current RSS" metric meaningless. | `capture/resources.py:46-52` — `usage.ru_maxrss` is documented as peak, not current. |
| BUG-02 | Medium | Low | Engineer | ResourceWatcher CPU | `_poll_cpu()` includes `children_user` and `children_system` in the delta but uses `getattr(current_times, "children_user", 0)` which always returns `0` because `os.times()` returns a named tuple with fields `children_user` (not a missing attribute). The bug: it subtracts children from the *previous* sample but adds children from the *current* one, which means the delta double-counts children on subsequent samples. | `capture/resources.py:96-97` — `getattr(current_times, "children_user", 0)` gives the cumulative value, but the formula adds current children and subtracts previous children from the user/system delta, when it should compute `(current_total - previous_total)`. |
| BUG-03 | Medium | Low | Engineer/QA | ProvenanceFileProxy | `_to_bytes()` in binary mode blindly returns `data` assuming it's `bytes`, but if `data` is empty string `""` (which `read()` can return in text mode when the mode string lacks 'b' but the proxy's `_is_binary` check incorrectly triggers), `hashlib.update()` will silently accept it — but this is fragile. More critically: if a user opens a file with mode `"rb+"` the proxy correctly detects binary, but a `write()` call won't be intercepted (no `write` method on the proxy), leaking data through to the underlying file without hash tracking. | `core.py:427` — proxy only implements read methods; writes go through `__getattr__` delegation without hashing. |
| BUG-04 | Medium | Low | Engineer | start() race condition | `start()` reads `get_current_run()` under `_run_lock`, but then calls `Run(overrides=kwargs)` OUTSIDE the lock. Two concurrent threads calling `start()` when no run exists can both see `active=None`, both create `Run()`, and the second one silently overwrites `_active_run`. The first Run will never be stopped. | `core.py:97-105` — lock released before `Run()` construction; no re-check after construction. |
| BUG-05 | Low | Low | QA | EventStream buffer loss | When `emit()` raises an exception (e.g. disk full) after appending to `self._buffer` but before `writelines()`, the line is in the buffer permanently but the exception is swallowed. On next successful flush, the buffer includes all accumulated lines including ones from failed iterations. This is actually desired resilience, not a bug. However, if `json.dumps(record)` fails (non-serializable payload), the exception is raised OUTSIDE the lock, which means the failed line `line = json.dumps(record) + "\n"` was never appended — but the caller sees the exception silently swallowed by the outer `try/except`. The event is silently dropped with only a debug log. | `events.py:82-104` — if `json.dumps` raises, event is silently lost. |
| BUG-06 | Medium | Low | Engineer/QA | hardware thread + startup manifest | The startup manifest is written by `write_startup_manifest()` immediately after `_bootstrap_engines()`. At this point, `self.hardware_data` is `{"capture_state": {"status": "pending"}}`. The startup manifest is written atomically to disk. If another process (e.g. `pubrun status`) reads this manifest while the run is active, it will see `hardware: {capture_state: pending}` — this is acceptable. BUT: if the hardware thread completes and sets `self.hardware_data` to the real data, and then the process crashes before `stop()`, the atexit handler calls `write_artifacts()` which writes the FINAL manifest. However, if atexit doesn't fire (SIGKILL), the on-disk manifest remains with `pending` hardware forever — stale state. | `tracker.py:159-164` (startup manifest write) vs `tracker.py:274-280` (background hardware). |
| BUG-07 | Low | Low | QA | _get_rss_darwin returns peak not current | The `end_rss_bytes` in `ResourceWatcher.stop()` calls `_poll_rss()` which on macOS returns `ru_maxrss` (the peak). This means `end_rss_bytes` and `peak_rss_bytes` will always be identical on macOS, making the "end RSS" field meaningless — it can never be less than the peak. | `capture/resources.py:138-141` — `end_rss = self._poll_rss()` gets peak, not current. Same root cause as BUG-01. |
| BUG-08 | Low | Low | Engineer | ProvenanceFileProxy write mode hash | For write-mode files, `_register_provenance()` hashes the file from disk after close. But `close()` calls `self._file_obj.close()` THEN `_register_provenance()`. If the file system hasn't flushed yet (buffered writes), the hash may not include the final buffered data. In practice, Python's `close()` flushes before closing so this is safe — but if the underlying file object is a custom wrapper that doesn't flush on close, the hash could be wrong. | `core.py:468-472` — close then hash; relies on close() flushing. |
| BUG-09 | Low | Low | QA | SubprocessSpy class-level state | `SubprocessSpy._records` is a class-level list. If a user runs multiple tests in the same process or calls `install()` multiple times without `uninstall()`, records from previous runs accumulate. `install()` does `cls._records = []` so it resets on install, but `get_records()` is called by `to_manifest_dict()` which reads from the class — if the user forgets to call `start()`/`stop()` properly, stale records from a prior run can leak into a new manifest. | `capture/subprocesses.py:41-43` — class-level mutable state shared across all instances. |
| BUG-10 | Low | Low | Engineer | `_merge_and_migrate` event stream reference | After `event_stream.close()` and before `event_stream.migrate_directory(new_dir)`, there is no null check. If `migrate_directory` is called on an already-closed stream, it will try to close the file again (harmless, `_file` is None) and reopen in the new directory. But the reference `self.event_stream` is still the old object. If `close()` had set `self._file = None` (which it does), the migration reopens it — this is correct. However, the `emit("warning", ...)` call after `migrate_directory` will work only if the stream successfully reopened. If it failed to reopen, `self._file` is None and `emit()` returns early — the warning is silently lost. | `tracker.py:381-385` — emit after migration may silently fail. |

## Proposed changes (ordered, validatable)

| Step | Source finding IDs | Change | Files | Remediation Risk | Validation |
|------|-------------------|--------|-------|------------------|------------|
| 1 | BUG-01, BUG-07 | On macOS, use `mach_task_info` via ctypes or fall back to `ps -o rss=` for *current* RSS (not peak). Reserve `ru_maxrss` only for the `peak_rss_bytes` field. | `capture/resources.py` | Low | Add test: run on macOS, allocate then free memory, verify end_rss < peak_rss (or at least that the function returns a value different from peak). |
| 2 | BUG-02 | Fix `_poll_cpu()` formula: compute total CPU delta as `(current_user + current_system + current_children_user + current_children_system) - (prev_user + prev_system + prev_children_user + prev_children_system)` instead of the current broken formula that adds children partially. | `capture/resources.py` | Low | Add unit test with mocked `os.times()` values verifying correct delta computation. |
| 3 | BUG-04 | Add a re-check inside `start()`: after `Run()` construction, acquire `_run_lock` and verify `_active_run` wasn't set by a concurrent thread. If it was, stop the just-created run and return the existing one. Or: hold the lock across `Run()` construction (simpler, but blocks concurrent callers during init). | `core.py` | Low (the lock-across-construction approach is simplest; init is fast now that hardware is deferred) | Add concurrent start() test with threading. |
| 4 | BUG-03 | Add `write()` and `writelines()` methods to `ProvenanceFileProxy` that delegate to the underlying file AND update the hash for write-mode files. This ensures the incremental hash is accurate even for write mode. | `core.py` | Low | Add test: open file in write mode via `pubrun.open()`, write data, close, verify hash in provenance matches actual file hash. |
| 5 | BUG-06 | After hardware thread completes, re-write the startup manifest with hardware data included (a "hardware supplement" write). This ensures on-disk state converges even if the process is killed before `stop()`. | `tracker.py` | Low | Test: start a run, wait for hardware thread, verify manifest.json on disk contains hardware data before stop(). |
| 6 | BUG-05 | When `json.dumps()` raises (non-serializable payload), catch `TypeError`/`ValueError` specifically, log at warning level (not just debug), and include the event_type in the message so the user knows which event was dropped. | `events.py` | Low | Test: pass a non-serializable payload to `annotate()`; verify warning is logged. |
| 7 | BUG-09 | Add a `reset()` classmethod to `SubprocessSpy` that's called in `uninstall()`, or document that `install()` always resets. Ensure `get_records()` returns only records from the current installation cycle. | `capture/subprocesses.py` | Low | Existing tests should still pass; add test that verifies records are empty after uninstall+reinstall. |
| 8 | BUG-10 | After `migrate_directory()`, check if `self._file` is not None before calling `emit()`. If migration failed, log a warning directly via the logger instead of through the (broken) event stream. | `tracker.py` | Low | Test: mock a migration failure and verify no exception + warning logged. |
| 9 | BUG-08 | Document in docstring that ProvenanceFileProxy relies on the underlying file's `close()` flushing buffered data. No code change needed — this is correct behavior for standard Python file objects. | `core.py` | Low | N/A (documentation only). |

## Deferred / out of scope (with reason)

| Finding ID | Remediation Risk | Axis | Reason | Recommended later step |
|------------|------------------|------|--------|------------------------|
| (none) | — | — | All findings have Low remediation risk and are proposed for fixing. | — |

## Scope check

- Over-scope: None identified.
- Under-scope: No test exists for concurrent `start()` calls (BUG-04). No test exists for write-mode provenance hash accuracy (BUG-03). Both are proposed as part of the fix validation.

## Required tests / validation

1. **BUG-01/07**: macOS RSS test (may need platform skip on Linux/Windows).
2. **BUG-02**: Unit test with mock `os.times()` values testing CPU% formula.
3. **BUG-03**: Write-mode file provenance hash correctness test.
4. **BUG-04**: Concurrent `start()` threading test.
5. **BUG-05**: Non-serializable payload event test.
6. **BUG-06**: Hardware manifest convergence test.
7. **Full regression suite**: 583+ existing tests must remain green.

## Spec / documentation sync

- BUG-08: Add docstring clarification to ProvenanceFileProxy about flush-on-close.
- If BUG-01 changes the macOS RSS behavior, update any docs that reference
  resource monitoring accuracy.

## Open questions

1. **BUG-04**: Should `start()` hold the lock across `Run()` construction
   (simpler, blocks callers ~50ms during init) or use a double-checked pattern
   (more complex, non-blocking)? Recommendation: hold the lock, since hardware
   is now deferred and init is fast.
2. **BUG-01**: On macOS, should we use `ps -o rss=` (subprocess, accurate but
   slow) or `mach_task_info` via ctypes (fast, no subprocess, but platform-
   specific FFI)? Recommendation: ctypes `task_info` for current RSS in the
   polling loop, `ru_maxrss` only for peak.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution, and it is NOT auto-executed. Recommended next steps:

1. Review this IPD (optionally run the `plan-review` workflow to harden it).
2. On approval, execute the ordered changes, run the validation, and sync
   specs/docs.
3. Only then move this IPD out of `pending/` per the project's lifecycle
   convention.
