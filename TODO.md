# TODO

Known issues and deferred improvements for future releases.

---

## Test Coverage Gaps (from P3 Review)

### Missing Regression Tests — Recent Fixes

- **P3-T10**: `clean` interactive TTY selection — only programmatic API tested, not real stdin prompting. (Low)

### Missing Regression Tests — Existing Behavior

- **P3-R4**: Critical event cap with `max_events=0` — indirectly covered by existing `test_phase_events_bypass_throttle` and `test_zero_max_events`. (Low)
- **P3-R6**: `EventStream.directory` dead assignment — untested; document-only until the bug is fixed. (Low)

### Brittle Tests (Consider Refactoring)

- **P3-T11**: `test_resources_watcher_threads` — `time.sleep(0.15)` timing-dependent; may flake on slow CI.
- **P3-T12**: `test_resource_watcher_failure_threshold` — `time.sleep(0.3)` timing-dependent.
- **P3-T15**: `test_run_tests_exits_zero` — recursively invokes test suite; latent CI time bomb.

### Infrastructure

- `pytest-cov` is in dev deps but coverage is not configured or enforced.

---

## Removed from Roadmap

### Determinism Tracking (`[capture.determinism]`)

**Removed.** Recording pseudorandom seeds (`random.getstate()`, `numpy.random.get_state()`,
`torch.manual_seed()`) was considered but rejected for the following reasons:

1. **Fragile detection**: Detecting which RNG libraries are in use requires probing
   optional imports (numpy, torch, tensorflow, jax) at runtime. Each has a different
   API surface, and versions change frequently.
2. **Locking seeds is harmful**: Overwriting user seeds would break scripts that
   intentionally use randomness for exploration. Recording-only is the only safe option.
3. **Recording-only has limited value**: If the user didn't explicitly set a seed,
   recording the internal RNG state is useless for reproduction — the state is opaque
   and not portable across library versions.
4. **Better solved by the user**: A single `pubrun.annotate(seed=42)` call is more
   explicit, safer, and requires no magic detection.

The `[capture.determinism].depth = "off"` config key is retained for forward compatibility
but documented as "not yet implemented / reserved."

### `summary.txt` Generation (`[logging].write_summary`)

**Removed.** A human-readable glance file was planned but is superseded by:

- `pubrun status <run-id>` — Shows the same information interactively.
- `pubrun report --basic` — Produces a full diagnostic summary.
- `manifest.json` — Machine-readable and more complete.

Writing a redundant text file to every run directory adds disk I/O, increases the
run directory footprint, and provides no information not already available via the
CLI. The config key is retained as "not yet implemented / reserved" for users who
may want it in the future.

---

## Future Feature Considerations

### Direct Bug Reporting and Feature Requests option in CLI
- **Provide a built-in CLI command to file bug reports or request features** (Deferred) (Low-Medium)
  - Suggestion: Add a `pubrun bug-report` (or `pubrun feedback` / `pubrun issue`) command that guides the user through filing an issue or opens the GitHub issue forms in their default web browser directly, possibly pre-populating environment context.
  - This increases community interaction and simplifies reporting problems or proposing enhancements.
