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

When a run starts, `pubrun` assigns a run ID, creates the run directory, and captures early metadata (invocation, script metadata, environment, packages, and Git state). Git and script source-state capture stay synchronous before user code runs so user edits cannot race with provenance capture; `get_git()` combines `--show-toplevel`, `HEAD`, and `--abbrev-ref HEAD` into one `git rev-parse` subprocess call and enforces a shared monotonic budget (`[capture.git].total_timeout`, default `5`s).

When `[capture.hardware].depth == "off"`, hardware (suppressed), host, and filesystem metadata are collected synchronously in three separate failure-isolated guards without spawning a background thread or triggering a second startup manifest write. When hardware capture is enabled, the background `pubrun-hw` daemon thread runs within `[capture.hardware].total_timeout` (default `10`s) and refreshes `manifest.json` only if the initial startup write did not already include completed hardware data and the run is still active and unfinalized. At startup, `ArtifactWriter` writes `manifest.json` and `config.resolved.json` atomically and records the config target path, canonical SHA-256 digest, and applied durability rank.

### Active Capture
Collect events, subprocess records, and console output. Update summary fields. If a re-entrant `start(**overrides)` call merges new configuration or migrates `run_dir` through `Run._merge_and_migrate()`, `ArtifactWriter.sync_config_if_changed()` writes the updated `config.resolved.json` immediately while the run is active and unfinalized.

### Finalization
Call `_finalize_state()` before acquiring `ArtifactWriter._write_lock` so lock order stays strictly `_run_lock` before `_write_lock`. Persist `config.resolved.json` only when the target path, canonical SHA-256 digest, or file presence changed (or synchronize an unchanged startup snapshot in place via `os.fsync()` under `[core].artifact_durability = "finalize"`). Write final `manifest.json` once atomically, mark `_artifacts_written = True`, close console tees and event streams, and mark the run complete.

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
- **Arithmetic simplicity**: Elapsed time is `ended_at - started_at` with no datetime conversion.
- **Native production**: Directly matches `time.time()`, `os.stat().st_mtime`, and similar system calls.
- **Deterministic**: No string formatting jitter across platforms or Python versions.
- **Compact**: A float is smaller and faster to serialize than an ISO 8601 string.

## 9. Observed vs Derived vs Inferred

The manifest distinguishes between:

- **Observed** — directly read from the system (e.g., `os.uname()`, `sys.version`)
- **Derived** — computed from observed data (e.g., `elapsed_seconds = ended_at - started_at`)
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

Console capture uses a tee-style wrapper around `sys.stdout` and `sys.stderr`. Output is preserved for the user while being simultaneously written to log files.

The `TqdmSafeTee` implementation squashes carriage-return redraws (common with progress bars) to prevent log bloat, keeping only the final state of each redrawn line.

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

The `SubprocessSpy` transparently monkey-patches `subprocess.Popen` and `os.system` to capture spawned process metadata (argv, timing, exit codes). Access is thread-safe via `threading.Lock`.

Internal library subprocess calls (e.g., `git` queries) use the `disable_spy()` context manager to prevent circular logging.

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

- Never crash the host script due to capture failure.
- Emit a partial manifest if needed.
- Record capture errors in the `errors` section.
- Degrade gracefully when optional features are unavailable.

"Ghost mode" activates automatically when filesystem operations fail (e.g., read-only filesystem). In ghost mode, all capture methods become silent no-ops.

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
