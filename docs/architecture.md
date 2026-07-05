[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [Changelog](../CHANGELOG.md)

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
Capture early metadata (invocation, environment, packages) and assign a run ID. Create the run directory.

### Active Capture
Collect events, subprocess records, and console output. Update summary fields.

### Finalization
Write `manifest.json` and `config.resolved.json`. Close console tees and event streams. Mark the run as complete.

### Abnormal Termination
Best-effort partial capture. The `_finalize_state()` method is idempotent, so it can safely be called from both `stop()` and `atexit` handlers without double-writing.

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
- The finalization method is idempotent to handle both explicit `stop()` and `atexit` cleanup.

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

- **Import Mode Router** (`__init__.py`) — Target-aware package initializer that detects mode submodule imports and defers core loading when appropriate.
- **Bootstrap State** (`_bootstrap.py`) — Singleton tracking selected import mode, conflict detection, and provenance metadata.
- **Boot Config Resolver** (`_config_boot.py`) — Lightweight import-mode resolver that reads env vars and `.pubrun.toml` without importing the full config system.
- **Mode Definitions** (`_modes.py`) — Five import presets (auto, noauto, nopatch, noconsole, minimal) with behavior flags.
- **Core API** (`core.py`) — Public API implementation (start, stop, annotate, phase, diff, audit_run, tracked_run) and boot sequence logic.
- **Configuration Resolver** (`config.py`) — Merges and applies settings from API > env vars > local config > user config > defaults.
- **Capture Engine** (`tracker.py`) — Orchestrates individual data collection routines, operating gracefully under partial failures. Respects granular behavior flags (patch_subprocesses, patch_console, signal_hooks).
- **Event Streamer** (`events.py`) — Writes structured execution events to `events.jsonl` with throttling.
- **Console Manager** (`capture/console.py`) — Tee-style wrapper around standard streams with tqdm-safe carriage return squashing. Includes `resolve_console_mode()` for context-aware mode selection (Jupyter detection, non-TTY override).
- **Resource Tree Walker** (`capture/resources.py`) — Background resource sampling with optional process-tree scope (`_get_tree_rss_linux`, `_get_tree_rss_darwin`).
- **Phase Profiler** (`core.py` phase hooks) — Optional cProfile/yappi integration that profiles `pubrun.phase()` blocks and saves per-phase `.prof` files.
- **Artifact Writer** (`writer.py`) — Creates the run directory and serializes all outputs.
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

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [Changelog](../CHANGELOG.md)
