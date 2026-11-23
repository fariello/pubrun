[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)

# pubrun Architecture

> Status: v1.0.0
> Purpose: Defines architectural principles and constraints for pubrun.
> Audience: Developers and contributors.

## 1. Overview

`pubrun` is a lightweight Python library that captures execution context for a run to support:

- reproducibility (primary)
- troubleshooting (secondary)
- comparison and inspection (secondary)

The library is designed for minimal friction. A user should be able to include it with one line and immediately gain meaningful, structured provenance data.

## 2. Core Architectural Model

pubrun uses a hybrid snapshot + event model.

### Snapshot (canonical)
Each run produces a `manifest.json` that represents the run as a whole. This is the canonical output.

### Events (optional)
Structured events may be emitted during execution to `events.jsonl`, providing a time-series record of phases, annotations, and errors.

## 3. Run Lifecycle

### Initialization
Resolve the import mode without importing the full configuration engine: `_config_boot.py` reads and parses `./.pubrun.toml` at most once when checking `[imports].mode` and `[core].auto_start`. Library commit identity (`pubrun.__commit__`) resolves lazily through Python Enhancement Proposal 562 (PEP 562) module `__getattr__` only when requested, so installed imports and `minimal` or `noauto` imports spawn zero `git` processes.

When a run starts, `pubrun` assigns a run ID, creates the run directory, and runs every capture engine (`invocation`, `git`, `process`, `python`, `packages`, `environment`, `hardware`, `host`, `filesystem`, `subprocesses`, `console`, `events`, `resources`, and `signals`) inside its own isolated failure guard. A failure in one engine marks only that section `"failed"`, records a bounded redacted entry in `errors.records`, and never promotes healthy tracking into ghost mode. Package capture at this stage records a startup snapshot (`packages.snapshot_stage = "startup"`), so a run that crashes before finalization still records which distributions were loaded; the installed-distribution index it builds is cached under a fingerprint of `sys.path` and reused by the finalization refresh. Git and script source-state capture stay synchronous before user code runs so user edits cannot race with provenance capture; `get_git()` combines `--show-toplevel`, `HEAD`, and `--abbrev-ref HEAD` into one `git rev-parse` subprocess call and enforces a shared monotonic budget (`[capture.git].total_timeout`, default `5`s).

When `[capture.hardware].depth == "off"`, hardware (suppressed), host, and filesystem metadata are collected synchronously in three separate failure-isolated guards without spawning a background thread or triggering a second startup manifest write. When hardware capture is enabled, the background `pubrun-hw` daemon thread runs `get_hardware()`, `get_host()`, and `get_filesystem()` in three independent failure guards within `[capture.hardware].total_timeout` (default `10`s) and refreshes `manifest.json` only if the initial startup write did not already include completed hardware data and the run is still active and unfinalized.

At startup, `ArtifactWriter.write_startup_manifest()` writes `manifest.json` and `config.resolved.json` atomically, records the config target path, canonical SHA-256 digest, and applied durability rank, and returns a boolean indicating whether startup output succeeded. If `run_dir` creation or initial startup manifest writing fails, `Run` latches `_finalized = True`, `_hardware_write_closed = True`, and `is_active = False` under `_run_lock`, rolls back only hooks, workers, file handles, and `.pubrun.lock` owned by that run via `_rollback_owned_hooks(stage="rollback")`, skips `atexit` registration, and enters ghost mode.

### Timing anchors
`Run` records four timing anchors. Each anchor stores a UTC epoch float (`time.time()`) for chronology and an in-memory monotonic reading (`time.perf_counter()`) for durations; the monotonic readings are never serialized.

- **`t0`** (`started_at_utc`): `Run` construction begins.
- **`t1`** (`workload_started_at_utc`): synchronous startup capture and the startup manifest write are complete and control returns to user code. `t1 - t0` is `startup_overhead_seconds`. Ghost mode never reaches `t1`.
- **`t2`** (`ended_at_utc`): `_finalize_state()` latches `_finalized` under `_run_lock`, before waiting for background hardware capture. `t2 - t1` is `workload_seconds`, the observed tracked workload.
- **`t3`** (`finalized_at_utc`): `ArtifactWriter.write_artifacts()` has written `config.resolved.json` and is about to build `manifest.json`. `t3 - t2` is `finalization_overhead_seconds` and `t3 - t0` is `session_seconds`. `Run.to_manifest_dict()` freezes the timing section on its first call after finalization, so the final atomic `manifest.json` write is not included in any persisted duration; `ArtifactWriter` keeps the whole write duration in memory only as `Run.writer_overhead_seconds`.

The background `pubrun-hw` thread times itself (`background_hardware_seconds`) while running concurrently with the workload, and finalization times its bounded wait for that thread (`hardware_wait_seconds`, part of `t3 - t2`). These two values overlap other intervals and are never summed with them. Because tracking starts at `t0`, a late `import pubrun` or a late `start()` measures only the tracked interval, not the whole process lifetime.

### Active Capture
Collect events, subprocess records, and console output. Update summary fields. If a re-entrant `start(**overrides)` call merges new configuration or migrates `run_dir` through `Run._merge_and_migrate()`, `ArtifactWriter.sync_config_if_changed()` writes the updated `config.resolved.json` immediately while the run is active and unfinalized. `Run._merge_and_migrate()` is a no-op on ghost, inactive, or finalized runs, guards `resolve_config()` failures safely, and checks import-mode `patch_subprocesses` permission before activating `SubprocessSpy` mid-run.

### Finalization
Call `_finalize_state()` before acquiring `ArtifactWriter._write_lock` so lock order stays strictly `_run_lock` before `_write_lock`. Inside `_finalize_state()`, every pre-teardown step (`_hardware_future_done.wait(timeout=2.0)`, signal interruption check, and exit-code recording) and every teardown step (`SubprocessSpy.finalize_all()`, record snapshot, `SubprocessSpy.uninstall(owner=...)`, `ConsoleInterceptor.stop()`, `ResourceWatcher.stop()` and snapshot, deferred file registrations, `EventStream.close()`, profiler disable, `SignalExitCapture` snapshot and `uninstall()`, `.pubrun.lock` removal, and finalization package refresh) runs inside an independent `try/except` guard so one or more cleanup errors never skip remaining cleanup. The finalization package refresh re-reads `sys.modules`, resolves imports made during the run, and merges them with the startup snapshot through `merge_package_snapshots()` (records gain `observed_at` of `"startup"`, `"final"`, or `"startup_and_final"`; in `imported-transitive` mode the recursive dependency closure is computed once over the merged set). It installs no global import hook, so a module imported and then removed from `sys.modules` before finalization is not observed; if the refresh fails, the startup snapshot is kept and the section is marked `"partial"` (or `"failed"` when the startup snapshot had also failed). `ArtifactWriter.write_artifacts()` persists `config.resolved.json` only when the target path, canonical SHA-256 digest, or file presence changed (or synchronizes an unchanged startup snapshot in place via `os.fsync()` under `[core].artifact_durability = "finalize"`), guards `config.resolved.json` separately from `manifest.json`, writes final `manifest.json` once atomically, marks `_artifacts_written = True`, and treats `methods.{md,tex}` generation failures as non-fatal. `Run.stop()` unregisters `atexit` and clears `_active_run` in a `finally` block when `ref_count` reaches zero.

### Abnormal Termination
Best-effort partial capture. Both `_finalize_state()` (guarded by `_finalized`) and `write_artifacts()` (guarded by `_artifacts_written`) are idempotent, so calling them from `stop()`, signal handlers, and `atexit` never rewrites finalized artifacts.

## 4. Data Model Principles

- **Structured**: All output is JSON with defined schemas.
- **Versioned**: The manifest includes a `schema_version` field (`"1.0"`).
- **Partially sparse**: Sections may be suppressed or unavailable. Every section carries a `capture_state` indicating its status.
- **Semantically stable**: Field names and types do not change within a schema version.

## 5. Manifest Design

The manifest is the canonical record for every run. Its top-level structure:

```json
{
  "schema_version": "1.0",
  "manifest_type": "pubrun-manifest",
  "meta_ref": null,
  "run": {},
  "timing": {},
  "invocation": {},
  "console": {},
  "subprocesses": [],
  "process": {},
  "python": {},
  "packages": {},
  "environment": {},
  "git": {},
  "errors": {},
  "config": {},
  "hardware": {},
  "host": {},
  "resources": {},
  "capture": {},
  "signals": {},
  "status": {}
}
```

See [Manifest Reference](manifest.md) for field-level details.

## 6. Event Model

Events are optional, structured JSONL records written to `events.jsonl`. Each event contains:

- `type` — `annotation`, `phase_start`, `phase_end`
- `timestamp_utc` — POSIX epoch float
- `name` — Human-readable label
- `payload` — Optional key-value data

A `phase_end` event's payload carries `elapsed_seconds` (a nonnegative monotonic duration of the phase body) and `duration_clock: "monotonic"`, plus `error` when the body raised. The duration excludes optional phase profiler setup and profile dump I/O.

Events are subject to throttling via `max_tracked_events` to prevent runaway disk usage.

## 7. Immutable vs Mutable

- **Mutable during run**: The manifest is built incrementally while the run is active.
- **Immutable after finalization**: Once `stop()` is called, the manifest is written and not modified.

## 8. Normalization Rules

- UTC timestamps as POSIX epoch floats (see below)
- Deterministic key ordering in JSON output
- Consistent naming (snake_case throughout)

### Timestamp Format

All timestamps in the manifest and event stream are stored as **POSIX epoch floats** (`time.time()`), not ISO 8601 strings. This is a deliberate design choice:

- **Precision**: IEEE 754 floats provide sub-second / microsecond resolution.
- **Timezone agnostic**: No locale-dependent formatting or parsing ambiguity.
- **Chronology only**: Timestamps order events in absolute time. They are not used to compute durations, because the system clock can jump during a run.
- **Native production**: Directly matches `time.time()`, `os.stat().st_mtime`, and similar system calls.
- **Deterministic**: No string formatting jitter across platforms or Python versions.
- **Compact**: A float is smaller and faster to serialize than an ISO 8601 string.

### Duration Format

Durations (`timing.*_seconds`, `phase_end` `elapsed_seconds`, and subprocess `elapsed_seconds`) are nonnegative floats in seconds computed from differences of monotonic `time.perf_counter()` readings and are labeled `duration_clock: "monotonic"`. Raw monotonic counter readings are process-local and meaningless outside the process, so they are never serialized. Legacy manifests whose `timing` lacks `duration_clock` and `elapsed_basis` used wall-clock subtraction; consumers label them `wall_clock_legacy`. A crashed-run closeout written by `pubrun status` can only estimate its duration from wall-clock values and labels it `wall_clock_estimated` / `crashed_estimate`.

## 9. Observed vs Derived vs Inferred

The manifest distinguishes between:

- **Observed** — directly read from the system (e.g., `os.uname()`, `sys.version`)
- **Derived**: computed from observed data (e.g., `workload_seconds` as the difference of two in-memory monotonic clock readings, or a crashed-run `elapsed_seconds` estimated from wall-clock values and labeled `crashed_estimate`)
- **Inferred** — heuristically determined (e.g., input file detection from `sys.argv`)

## 10. Capture Categories

Each capture category is a modular sub-engine responsible for one section of the manifest. Categories are independently configurable.

| Category | Manifest Key | Configurable Modes |
|---|---|---|
| Environment | `environment` | `allowlist`, `filtered`, `full` |
| Packages | `packages` | `imported-only`, `imported-transitive`, `top-level-installed`, `full-environment` |
| Subprocesses | `subprocesses` | `enabled = true/false` |
| Console | `console` | `off`, `basic`, `standard`, `deep` |
| Git | `git` | depth-based |
| Hardware | `hardware` | depth-based |
| Host | `host` | depth-based |
| Process | `process` | depth-based |
| Python | `python` | depth-based |
| Resources | `resources` | depth-based |
| Signals | `signals` | `enabled = true/false` |
| Inputs | `invocation.inputs` | `enabled = true/false` |

## 11. Progressive Depth Model

- `off` — Category entirely disabled.
- `basic` — Fast, lightweight capture. Skips expensive system calls.
- `standard` — Default. Comprehensive capture without significant overhead.
- `deep` — Maximum information gathering. May include slow system calls (e.g., GPU clock speed queries).

## 12. Console Capture Model

Console capture uses a tee-style wrapper (`TqdmSafeTee`) around `sys.stdout` and `sys.stderr`. Output is preserved for the user while being written to `stdout.log` and `stderr.log`.

The `TqdmSafeTee` implementation squashes carriage-return redraws (common with progress bars) to prevent log bloat, keeping only the final state of each redrawn line. Runtime log-file write or flush errors never break user output or recurse through a wrapped `sys.stderr`: `TqdmSafeTee` guards `original_stream.flush()` against `(BrokenPipeError, OSError, ValueError)`, detaches `log_file = None` on the first log error to stop repeated failing system calls, guards its single debug log with an `_in_error_log` re-entry flag, and causes `ConsoleInterceptor.stop()` to report `capture_state.status = "partial"`.

`ConsoleInterceptor.start()` installs transactionally and preserves prior `faulthandler` ownership:

- It snapshots live `sys.stdout`, `sys.stderr`, and `faulthandler.is_enabled()` at start time.
- It calls `faulthandler.enable(file=self.stderr_log)` only when `faulthandler.is_enabled()` is `False`, so a user or test-runner `faulthandler` is never hijacked or disabled later.
- If any setup step fails, it rolls back opened files, replaced streams, and owned `faulthandler` state, records a bounded redacted detail, and returns `False` so the manifest reports `capture_state.status = "failed"` with `captured = false`.

`ConsoleInterceptor.stop()` is idempotent (returning a copy of its cached result on repeat calls) and runs seven independent cleanup steps: identity-guarded `sys.stdout` restore, identity-guarded `sys.stderr` restore, `stdout_tee` flush and `log_file = None` detach, `stderr_tee` flush and `log_file = None` detach, `faulthandler.disable()` (only if owned, before closing `stderr.log`), `stdout.log` close, and `stderr.log` close. If a third-party library wrapped `sys.stdout` or `sys.stderr` after `start()`, `stop()` leaves that wrapper intact while `pubrun`'s detached tee passes output through passively.

## 13. Run Directory Model

Each run gets its own uniquely named directory:

```
<base_dir>/runs/pubrun-<script>-<timestamp>-<pid>-<run_id>/
```

Example:
```
./runs/pubrun-train-20260509T120000Z-12345-a1b2c3d4/
```

Contents:
- `manifest.json` (required)
- `config.resolved.json` (required)
- `stdout.log` (if console capture enabled)
- `stderr.log` (if console capture enabled)
- `events.jsonl` (if event stream enabled)
- `methods.md` or `methods.tex` (if methods generation enabled)

## 14. Race Safety and Durability

- Directory names include timestamp, PID, and random hex ID to prevent collisions.
- Directory creation uses `mkdir()` rather than exists-check + create.
- Both `_finalize_state()` and `ArtifactWriter.write_artifacts()` (`_artifacts_written`) are idempotent so explicit `stop()`, signal handlers, and `atexit` never overwrite finalized artifacts.
- **Lock ordering:** `_run_lock` is always acquired before reentrant `ArtifactWriter._write_lock`. `write_artifacts()` calls `self.run._finalize_state()` outside `_write_lock` to prevent AB-BA deadlocks with the background `pubrun-hw` thread and to avoid holding `_write_lock` while waiting for hardware completion.
- **Config snapshot coalescing:** `ArtifactWriter` tracks `(target_path, sha256_digest, durability_rank)` over canonical sorted JSON for `config.resolved.json`. Unchanged configuration skips redundant rewrites during background hardware refreshes and finalization while preserving immediate persistence on startup and mid-run `_merge_and_migrate()` updates.
- **Atomic visibility versus explicit durability:** Every write of `manifest.json` and `config.resolved.json` uses a unique temporary file (`*.tmp`), `flush()`, and `os.replace()` so concurrent readers never see truncated JSON. Disk synchronization is controlled separately by `[core].artifact_durability`:
  - `"fsync"` (default): File `os.fsync()` before `os.replace()` on startup, refresh, and finalized writes (no parent-directory sync).
  - `"finalize"`: Skips `os.fsync()` on startup and refresh snapshots while keeping atomic visibility; applies file `os.fsync()` on finalization, including in-place `r+b` `os.fsync()` upgrade of an unchanged startup `config.resolved.json` (falling back to atomic rewrite on `OSError`).
  - `"atomic"`: Atomic temporary file and `os.replace()` without `os.fsync()`.
  - `"strict"`: File `os.fsync()` plus best-effort Portable Operating System Interface (POSIX) parent-directory `os.fsync()` (opened with `O_DIRECTORY | O_CLOEXEC`) after `os.replace()`.
- **Platform durability limits:** Linux uses POSIX `fsync(2)`; macOS uses POSIX `fsync(2)` rather than `F_FULLFSYNC` (disk write caches are not flushed to physical media); Windows uses `FlushFileBuffers` on files only (parent-directory sync is unsupported and skipped cleanly in `"strict"` mode); Network File System (NFS) and Lustre incur synchronous remote procedure call (RPC) and writeback latency on every `fsync` and may skip unsupported directory sync on `OSError`.

## 15. Subprocess Model

`SubprocessSpy` transparently monkey-patches `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` to capture spawned process metadata (argv, UTC start and end timestamps, monotonic `elapsed_seconds` with `duration_clock: "monotonic"`, exit codes). Per-record monotonic start readings stay in an in-memory map keyed by record identity and are never serialized. Record mutations and lifecycle transitions are thread-safe under `SubprocessSpy._lock`.

- **Live target chaining and transactional install:** `SubprocessSpy.install(max_records, config, owner)` snapshots the live `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` attributes at install time, builds generation-scoped wrapper closures that chain to those pre-existing targets, and rolls back any already-patched target if a later patch fails.
- **Generation-scoped records:** Each spawned `Popen` instance carries its install generation's `state` dict and direct record reference (`_pubrun_state`, `_pubrun_rec`), and `os.system` holds a direct local reference to its record. Post-uninstall `wait()` calls or concurrent `uninstall()` calls cannot corrupt a newer run's records or raise `IndexError`. Failed spawn details pass through `format_safe_error_detail()`.
- **Ownership-guarded uninstall and passive passthrough:** `SubprocessSpy.uninstall(owner=...)` verifies the caller's ownership token when set, flips `state["active"] = False` first, and restores each target independently only when the current attribute is still `pubrun`'s installed wrapper. If a third-party wrapper sits outside `pubrun`, that wrapper remains intact while `pubrun`'s deactivated closure passes calls through passively without recording.

Internal library subprocess calls (for example, `git` queries) use the `disable_spy()` context manager to prevent circular logging.

## 16. Public API

Core primitives exposed at module level:

| Function | Purpose |
|---|---|
| `start()` | Begin tracking. Returns the `Run` tracker. |
| `stop()` | Finalize the active run. |
| `get_current_run()` | Access the active `Run` instance. |
| `annotate()` | Inject custom key-value events. |
| `phase()` | Context manager for timing named phases. |
| `tracked_run()` | Context manager for full run lifecycle. |
| `audit_run()` | Decorator for full run lifecycle. |
| `diff()` | Compare two run directories. |

## 17. Schema Extensibility

The manifest schema is versioned (`schema_version: "1.0"`). New sections can be added without breaking existing consumers. The `capture_state` pattern ensures forward compatibility — unknown sections can be skipped safely.

## 18. Failure Model

The system must:

- Never crash the host script due to capture, cleanup, or serialization failure.
- Isolate each capture engine so one failing engine produces a schema-valid partial manifest rather than suppressing healthy sections.
- Reserve ghost mode strictly for unusable run output at startup, with transactional rollback of owned hooks.
- Record bounded, redacted capture errors in `errors.records` and surface partial capture honestly across downstream consumers.

### Partial Capture vs. Narrow Ghost Mode

- **Per-engine failure isolation:** Every capture engine (`invocation`, `git`, `process`, `python`, `packages`, `environment`, `hardware`, `host`, `filesystem`, `subprocesses`, `console`, `events`, `resources`, and `signals`) executes in its own isolated guard (`hardware`, `host`, and `filesystem` each have separate guards). If an engine raises or returns `capture_state.status = "failed"`, only that section is marked `"failed"` with a bounded redacted `detail`. Unrelated healthy sections remain complete, the host script's return value and exit code are unaffected, `status.outcome` keeps the host script's outcome, and `capture.capture_state` reports `"partial"`.
- **Narrow ghost-mode boundary:** Ghost mode (`status.outcome = "ghost"`, `is_active = False`, `writer = None`) activates only when run output itself is unusable at startup: either `run_dir.mkdir()` fails or the initial `ArtifactWriter.write_startup_manifest()` fails (for example, on read-only or unavailable storage). If output fails after hooks were installed, `Run` latches `_finalized = True` and `_hardware_write_closed = True` under `_run_lock`, rolls back every hook, background thread, open handle, and `.pubrun.lock` owned by that run via `_rollback_owned_hooks(stage="rollback")`, skips `atexit` registration, publishes `_active_run` safely for nested `start()` calls, and emits one bounded redacted warning to `sys.stderr`.

### Bounded Redacted Diagnostics, Independent Cleanup, and Consumer Honesty

- **Bounded redacted error records:** Capture and cleanup exceptions pass through `format_safe_error_detail()` (single-line, sensitive values redacted, 240-character cap, `traceback = null`, falling back to default patterns and then `type(exc).__name__`). `Run` retains up to `MAX_CAPTURE_ERRORS = 50` entries in `errors.records` under `_errors_lock`; additional errors increment the omitted counter and set `errors.capture_state.status = "partial"`. Runtime warnings in `Run`, `EventStream`, and `ArtifactWriter` are emitted at most once per `(section, stage)` or failure episode, outside internal locks.
- **Independent cleanup and hook ownership:** `_finalize_state()` and `_rollback_owned_hooks()` isolate every pre-teardown and teardown step independently, separating `SubprocessSpy.finalize_all()` and record snapshotting from `SubprocessSpy.uninstall(owner=...)`. Process-global hooks (`sys.stdout`, `sys.stderr`, `faulthandler`, signal handlers, `sys.excepthook`, `subprocess.Popen.__init__`, `subprocess.Popen.wait`, `os.system`) use identity-guarded restoration and passive passthrough so later third-party wrappers are never clobbered.
- **Honest consumers:** `pubrun report`, `pubrun inspect`, `pubrun methods`, and `pubrun status` tolerate failed, `null`, or malformed section fields without crashing. They surface failed sections and deduplicated `capture-error` findings explicitly (distinct from `"suppressed"`) and disclose partial provenance instead of claiming complete capture or standard-library-only dependencies.

## 19. Redaction Model

Sensitive strings (passwords, tokens, API keys) are detected via configurable regex patterns and destructively replaced with `{"representation": "redacted"}`. By default, no hashes are generated to eliminate brute-force rainbow table risk.

Redaction applies to:
- Environment variables (configurable via `[redaction].env_enabled`)
- CLI arguments in `sys.argv` and subprocess records (configurable via `[redaction].argv_enabled`)

## 20. Non-Goals

pubrun is not:

- A workflow engine or DAG scheduler
- An experiment tracking platform (no server, no dashboard)
- A data versioning tool
- A replacement for proper version control

## 21. System Components

The execution engine is divided into these key systems:

- **Import Mode Router** (`__init__.py`): Target-aware package initializer that detects mode submodule imports, defers core loading when appropriate, and resolves `pubrun.__commit__` lazily via PEP 562 `__getattr__` (version-checked build metadata for installed wheels with zero `git` spawns; bounded ownership-verified live `HEAD` lookup for verified source checkouts).
- **Bootstrap State** (`_bootstrap.py`) — Singleton tracking selected import mode, conflict detection, and provenance metadata.
- **Boot Config Resolver** (`_config_boot.py`): Lightweight import-mode resolver that reads environment variables and parses `./.pubrun.toml` at most once without importing the full config system.
- **Mode Definitions** (`_modes.py`) — Six import presets (auto, full, noauto, nopatch, noconsole, minimal) with behavior flags.
- **Core API** (`core.py`) — Public API implementation (start, stop, annotate, phase, diff, audit_run, tracked_run) and boot sequence logic.
- **Configuration Resolver** (`config.py`) — Merges and applies settings from API > env vars > local config > user config > defaults.
- **Capture Engine** (`tracker.py`): Orchestrates failure-isolated data collection routines, keeps Git and script source-state capture synchronous before user code runs under `[capture.git].total_timeout`, runs hardware/host/filesystem synchronously without a background thread when `capture.hardware.depth == "off"` (or in a bounded `pubrun-hw` thread under `[capture.hardware].total_timeout` with coalesced refresh), and syncs `config.resolved.json` on mid-run `_merge_and_migrate()` changes.
- **Event Streamer** (`events.py`) — Writes structured execution events to `events.jsonl` with throttling.
- **Console Manager** (`capture/console.py`) — Tee-style wrapper around standard streams with tqdm-safe carriage return squashing. Includes `resolve_console_mode()` for context-aware mode selection (Jupyter detection, non-TTY override).
- **Resource Tree Walker** (`capture/resources.py`) — Background resource sampling with optional process-tree scope (`_get_tree_rss_linux`, `_get_tree_rss_darwin`).
- **Phase Profiler** (`core.py` phase hooks) — Optional cProfile/yappi integration that profiles `pubrun.phase()` blocks and saves per-phase `.prof` files.
- **Artifact Writer** (`writer.py`): Creates the run directory, enforces atomic visibility via unique temporary files and `os.replace()`, applies `[core].artifact_durability`, coalesces unchanged `config.resolved.json` writes by SHA-256 digest and durability rank, and guards finalized artifacts with `_artifacts_written`.
- **Diagnostics Analyzer** (`pubrun report`) — Evaluates and renders execution metrics from manifests.
- **Methods Generator** (`pubrun methods`) — Compiles manifest data into prose methodology paragraphs.
- **Global Context Snapshotter** (`pubrun meta`) — Generates standalone environment snapshots for HPC hydration.
- **Diff Semantic Analyzer** (`pubrun diff`) — Generates side-by-side structural comparisons with configurable depth filtering.
- **Reproducibility Extractor** (`pubrun rerun`) — Extracts cross-platform replay commands from historical manifests.
- **Run Monitor** (`pubrun status`) — Lists and inspects runs with live PID liveness checking, signal detection, and resource usage queries.
- **Run Cleanup** (`pubrun clean`) — Interactive deletion of old run directories with safety constraints and explicit confirmation.
- **Import Mode Wrapper** (`pubrun run`) — Spawns child processes with `PUBRUN_IMPORT_MODE` set for external workflow integration.

## 22. Summary

pubrun is a low-friction provenance layer for Python execution. It captures what you ran, where you ran it, and what changed — so you can prove it, reproduce it, or publish it without thinking twice.

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
