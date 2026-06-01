# TODO

Known issues and deferred improvements for future releases.

---

## Deferred from 0.2.0 Audit

### Security / Privacy

- **Key-name-only redaction misses sensitive values in innocuous keys** (Medium)
  - `environment.py` / `redaction.py`: The redaction regex only matches variable *names* (e.g., `PASSWORD`, `API_KEY`). An env var like `MY_APP_CONFIG={"db_password":"secret"}` or `JAVA_OPTS=-Dpassword=x` will not be redacted.
  - Recommendation: Consider value-scanning heuristics (detect URLs with embedded credentials, detect base64 tokens of certain lengths), or document the limitation prominently for users.

### Correctness

- **EventStream migration path: `event_stream.directory` is a no-op** (Low)
  - `tracker.py:273`: `_merge_and_migrate()` sets `self.event_stream.directory = new_dir`, but `EventStream` has no `directory` attribute. Events continue writing to the old path after directory migration. This is a rare path (mid-run `output_dir` change).
  - Recommendation: Close the old event stream and reopen at the new path, or update `stream_path` and reopen the file handle.

- **`script_name` not sanitized for filesystem-invalid characters** (Low-Medium)
  - `tracker.py:57`: `Path(sys.argv[0]).stem` could theoretically contain characters invalid on Windows (e.g., `<>:"|?*`). On Unix this is a non-issue. The ghost-mode fallback handles `mkdir` failure gracefully, so this won't crash.
  - Recommendation: Sanitize by replacing non-alphanumeric/dash/underscore/dot characters with `_`.

### Reliability

- **ResourceWatcher peak values written without lock** (Low-Medium)
  - `resources.py:109-130`: `peak_rss_bytes`, `peak_cpu_percent`, and `_consecutive_failures` are read/written from both the daemon thread and the `stop()` caller. On CPython with the GIL, this is safe. On free-threaded Python (PEP 703, 3.13+), this could race.
  - Recommendation: Add a `threading.Lock` around peak-value updates, or accept that `join()` (now added) makes this moot for the normal flow.

- **File handle leak in `_merge_and_migrate` on exception** (Low)
  - `tracker.py:281`: If `open(...)` succeeds but a later exception occurs, the new file handle is not closed in the except path.
  - Recommendation: Use a local variable and only assign to `self.console_interceptor.file` after success.

### Performance

- **TOCTOU on `_max_records` check in SubprocessSpy** (Low / Benign)
  - `subprocesses.py:99,157`: The length check is outside the lock. In concurrent scenarios, `_max_records` can be exceeded by at most `N_threads - 1` extra records. This is a soft safety cap, not a security boundary.
  - Recommendation: Accept as benign or move the check inside the lock (minor perf cost).

---

## Test Coverage Gaps (from P3 Review)

Tests marked **(done)** were implemented in `d3f4b45`. The rest are deferred.

### Implemented

- **P3-T4** (done): Auto-start failure doesn't crash `import pubrun`
- **P3-T6** (done): `resolve_config()` failure falls back to defaults
- **P3-R2** (done): `_finalize_active_run()` calls `write_artifacts()`
- **P3-R5** (done): Ghost outcome preserved after `stop()`

### Missing Unit Tests — Modules

- **P3-T1**: `writer.py` — no dedicated unit tests. Atomic write, temp-file cleanup, error paths untested in isolation. (Medium)
- **P3-T2**: `report/templates.py` — no dedicated tests. Template substitution/escaping only verified indirectly. (Low)

### Missing Unit Tests — Functions

- **P3-T3**: `status.py` private formatting helpers — `_format_elapsed`, `_format_timestamp`, `_format_bytes`, `_truncate`, `_format_age`, `_status_marker`, `_dir_size`. Edge cases (zero, negative, GB-range, wide terminal) untested. (Low-Medium)

### Missing Regression Tests — Recent Fixes

- **P3-T5**: SIGTERM/SIGHUP finalization — no test verifies a lethal signal triggers `run.stop()` before process death. Requires subprocess-based test. (Medium)
- **P3-T7**: Critical-event secondary cap — no test emits >10,000 critical events to verify the 10x cap fires. (Low)
- **P3-T8**: `disable_spy()` on macOS hardware calls — no test verifies subprocess calls are wrapped. Monkeypatch-based test possible. (Low)
- **P3-T9**: `ResourceWatcher.join()` — no test verifies the thread is joined before final poll. (Low)
- **P3-T10**: `clean` interactive TTY selection — only programmatic API tested, not real stdin prompting. (Low)

### Missing Regression Tests — Existing Behavior

- **P3-R1**: Auto-start crash protection — covered by P3-T4 (done).
- **P3-R3**: Config fallback — covered by P3-T6 (done).
- **P3-R4**: Critical event cap with `max_events=0` — indirectly covered by existing `test_phase_events_bypass_throttle` and `test_zero_max_events`. (Low)
- **P3-R6**: `EventStream.directory` dead assignment — untested; document-only until the bug is fixed. (Low)

### Brittle Tests (Consider Refactoring)

- **P3-T11**: `test_resources_watcher_threads` — `time.sleep(0.15)` timing-dependent; may flake on slow CI.
- **P3-T12**: `test_resource_watcher_failure_threshold` — `time.sleep(0.3)` timing-dependent.
- **P3-T13**: `test_sigint_sets_outcome_interrupted` — sends real SIGINT to test process.
- **P3-T14**: `test_captures_sigint_as_keyboard_interrupt` — sends real SIGINT to test process.
- **P3-T15**: `test_run_tests_exits_zero` — recursively invokes test suite; latent CI time bomb.

### Infrastructure

- No GitHub Actions CI workflow (tox matrix exists but is manual-only).
- `pytest-cov` is in dev deps but coverage is not configured or enforced.

---

## Feature Plans

### P5-F1: Timestamped Console Capture (`standard` mode)

Currently all non-`"off"` console modes produce identical plain-text tee output. The
`standard` mode should prepend ISO 8601 timestamps to each line written to the log
files (terminal output remains unchanged):

```
[2026-05-31T12:00:01.234Z] Training epoch 1...
[2026-05-31T12:00:03.891Z] Loss: 0.542
```

Implementation plan:
1. Add a `timestamped` flag to `TqdmSafeTee` (enabled when mode is `"standard"` or `"deep"`).
2. In `_write_to_log()`, prepend `f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z] "` to each line before writing to the log file.
3. Terminal output remains untouched (timestamps only go to the file).
4. `"deep"` mode remains reserved for future structured JSON capture.
5. Tests: verify timestamps appear in log files when mode is `"standard"`, do not appear when `"basic"`.

This is a prerequisite for `pubrun combined` (below).

### P5-F5: `pubrun combined` Command

Post-F1 command that interleaves stdout and stderr from one or more runs using the
log-line timestamps written by `standard` mode.

```
pubrun combined [RUN_ID ...] [--dir PATH] [--output FILE]
```

Design:
- Accepts one or more run IDs (prefix-matched like `pubrun status`).
- Reads `stdout.log` and `stderr.log` from each run directory.
- Parses the ISO 8601 timestamps prepended by `standard` mode.
- Merges all lines across streams and runs into timestamp order.
- Prefixes each line with stream origin: `[stdout]` or `[stderr]` (and run ID if multiple runs).
- Outputs to stdout by default (pipeable), or to a file with `--output`.
- **Size warning**: If combined file size exceeds 250 MB, prints a warning to stderr
  and prompts for confirmation (skipped with `--yes`). At 500 MB, refuses unless
  `--force` is passed.
- If logs lack timestamps (captured with `"basic"` mode), falls back to sequential
  concat with `[stdout]`/`[stderr]` headers and emits a warning that true interleaving
  requires `capture_mode = "standard"`.

CLI addition to `__main__.py`:
```python
subparsers.add_parser("combined", help="Interleave stdout/stderr logs from one or more runs.")
```

Tests:
- Verify interleaving with timestamped logs produces correct order.
- Verify fallback behavior with non-timestamped logs.
- Verify size warning triggers at threshold.
- Verify `--output` writes to file.
- Verify multiple run IDs merge correctly.

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
