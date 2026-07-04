# Evidence - assess-bugs 20260704-175521

## Files inspected

| File | Lines | Focus |
|------|-------|-------|
| `src/pubrun/tracker.py` | 596 | Run lifecycle, _bootstrap_engines, _finalize_state, hardware thread, migration |
| `src/pubrun/core.py` | 686 | start(), ProvenanceFileProxy, subprocess namespace, open() |
| `src/pubrun/events.py` | 141 | EventStream emit/close/buffer, serialization error handling |
| `src/pubrun/capture/resources.py` | 162 | ResourceWatcher, _poll_rss, _poll_cpu formulas |
| `src/pubrun/capture/console.py` | 194 | TqdmSafeTee write/flush, BrokenPipeError handling |
| `src/pubrun/capture/subprocesses.py` | 204 | SubprocessSpy class-level state, patched_popen_init |
| `src/pubrun/capture/signals.py` | 258 | Signal handler chaining, exit code capture |
| `src/pubrun/capture/redaction.py` | 219 | Regex caching, argv/env redaction |
| `src/pubrun/capture/git.py` | 70 | Git subprocess calls, dirty check |
| `src/pubrun/capture/invocation.py` | 184 | Script hashing, input discovery |
| `src/pubrun/writer.py` | 103 | Atomic writes, atexit handler |
| `src/pubrun/config.py` | 148 | Config resolution, deep merge, caching |
| `src/pubrun/status.py` | 1021 | RunInfo classification, scan_runs |
| `src/pubrun/_bootstrap.py` | 281 | Import mode state, conflict detection |

## Analysis methodology

1. **Read every code path** in the core modules looking for logic errors,
   wrong conditionals, incorrect assumptions, and contract violations.
2. **Traced concurrency**: identified all shared mutable state (`_active_run`,
   `SubprocessSpy._records`, `EventStream._buffer`, `ResourceWatcher` fields)
   and verified synchronization.
3. **Verified error handling**: checked all `except Exception: pass` blocks
   for cases where silent swallowing loses important information.
4. **Checked platform assumptions**: verified `os.getrusage` semantics on
   macOS vs Linux for RSS reporting.
5. **Verified the recently-introduced PERF changes** for regressions (the
   macOS `ru_maxrss` change in PERF-14 introduced BUG-01).

## Key verification

BUG-01 confirmed via Python docs and macOS man page:
- `man getrusage` on macOS: "ru_maxrss: the maximum resident set size utilized (in bytes)"
- This is the high-water mark, NOT the current RSS at the time of the call.
- On Linux, `ru_maxrss` is in kilobytes and is also the peak, not current.

BUG-02 confirmed by manual trace:
- First call: `_last_times = None`, returns 0.0 (correct).
- Second call: `user_delta = (cur.user - prev.user) + cur.children_user - prev.children_user`
  This computes `(user_delta_process) + (children_delta)` which is correct.
  Wait — re-reading: `user_delta = (current_times.user - self._last_times.user) + getattr(current_times, "children_user", 0) - getattr(self._last_times, "children_user", 0)`
  This IS `(cur.user - prev.user) + (cur.children_user - prev.children_user)` = correct delta.
  
  **Correction**: On re-analysis, BUG-02 formula is actually correct — it computes
  `(cur.user - prev.user) + (cur.children_user - prev.children_user)` which is the
  right delta. Downgrading severity to Low and noting the formula is correct but
  poorly readable. However, `getattr(current_times, "children_user", 0)` is redundant
  since `os.times()` always has these fields on Python 3.3+. This is a style issue,
  not a bug. **Reclassifying BUG-02 as Low/style rather than Medium/bug.**
