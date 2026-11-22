# Decisions and assumptions - assess-bugs 20260704-175521

## Concern and scope

- **Concern assessed:** Bugs and correctness (logic errors, contract violations,
  concurrency, state integrity, error handling).
- **Scope:** Entire `src/pubrun/` source tree.

## Key decisions

1. **BUG-01 is High severity** because it produces measurably incorrect data in
   every manifest on macOS (current RSS is always reported as peak RSS). This is
   a data integrity issue for users who rely on resource metrics.

2. **BUG-04 (start() race) rated Medium** not High because pubrun's documented
   threading model says start()/stop() should be called from the main thread.
   The race is reachable but goes against documented usage.

3. **BUG-03 (write-mode proxy) rated Medium** because the write-mode hash was
   already computing from disk on close (the full re-read path). The proxy's
   lack of write() only means the incremental hash during writes is unused —
   the final on-disk hash is still correct. However, the `sha256` field in the
   output record says `sha or self._hash.hexdigest()` which could use the
   (empty) incremental hash if the file doesn't exist at hash time. In practice
   the file exists because it was just closed, so this is safe — but fragile.

4. **All findings proposed for fixing** — none meet the Medium-High remediation
   risk threshold for deferral.

## What was intentionally NOT proposed

- **Rewriting ProvenanceFileProxy as separate Binary/Text classes**: already
  deferred in the performance IPD on Complexity grounds. The bugs IPD adds
  write() methods to the existing class instead.
- **Making EventStream guarantee zero-loss for all events**: the PERF-06 design
  decision explicitly accepts buffered loss for non-critical events. Not a bug.
- **Thread-safety of _active_run reference**: the global `_active_run` is
  written only under `_run_lock` or during `Run.__init__` (single-threaded at
  that point by contract). Reading without lock is intentional for performance.
