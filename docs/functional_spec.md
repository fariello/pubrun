[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)

# pubrun Functional Specification

> Status: v1.0.0
> Purpose: Defines functional requirements aligned with implementation.
> Audience: Developers and contributors.

---

## 1. Purpose and Scope

`pubrun` captures execution context for reproducibility, troubleshooting, and comparison of Python runs.

The library supports a low-friction user model. Useful behavior is available with minimal ceremony:

```python
import pubrun
```

Deeper, explicit control is available when desired:

```python
from pubrun import start, tracked_run, audit_run
```

### 1.1 Non-Goals

pubrun is not:

- A workflow engine or DAG scheduler
- An experiment tracking platform (no server, no dashboard)
- A data versioning tool
- A replacement for proper version control

---

## 2. Core Model

- **Manifest-first design**: Each run produces a `manifest.json` as its canonical output.
- **Optional event stream**: Structured JSONL events may be written to `events.jsonl`.
- **Optional console capture**: Tee-style interception of stdout/stderr.
- **Hierarchical configuration**: Defaults composed from built-in, user, local, environment, and API sources.
- **Explicit APIs**: `start()`, `stop()`, `annotate()`, `phase()`, `paused()`, `tracked_run()`, `audit_run()`, `diff()`.

---

## 3. Import and Activation Model

### 3.1 Import Compatibility

The package MUST support standard Python import patterns:

```python
import pubrun
from pubrun import start, stop, annotate, phase, tracked_run, audit_run, diff
from pubrun import get_current_run
```

### 3.2 Lightweight Import Requirement

Importing `pubrun` MUST NOT:

- significantly slow startup
- fail if optional dependencies are unavailable
- wrap stdout/stderr unless configured to do so
- write output unless configured to do so

The boot sequence is wrapped in `try/except`. If configuration resolution fails (e.g., corrupt TOML), the import succeeds silently with auto-start disabled.

To keep import and startup overhead bounded:

- **Lazy commit identity:** `pubrun.__commit__` resolves lazily via Python Enhancement Proposal 562 (PEP 562) module `__getattr__` and caches under a lock. Importing `pubrun.minimal` or `pubrun.noauto`, or importing an installed wheel, spawns zero `git` processes. Installed packages read version-checked `_build_meta.json` (falling back to legacy `COMMIT` only when `_build_meta.json` is absent) and never launch `git`. Verified `pubrun` source checkouts run one bounded (`1.0`s timeout) `git -C <repo_root> rev-parse --show-toplevel HEAD` call with `GIT_*` override variables stripped and `SubprocessSpy` disabled when loaded, returning `None` on missing Git, timeout, error, or ownership mismatch without falling back to an on-disk `COMMIT` file.
- **Single-read boot configuration:** `src/pubrun/_config_boot.py::resolve_import_mode` opens and parses `./.pubrun.toml` at most once when checking `[imports].mode` and `[core].auto_start`.
- **Bounded capture budgets:** Git and script source-state capture stay synchronous before user code runs so user modifications cannot invalidate captured state. `get_git()` combines `--show-toplevel`, `HEAD`, and `--abbrev-ref HEAD` into one `git rev-parse` subprocess call on normal repositories and enforces `[capture.git].total_timeout` (default `5`s), reporting `capture_state.status` `"timeout"` or `"partial"` when the budget expires. Hardware inspection runs in the background `pubrun-hw` thread within `[capture.hardware].total_timeout` (default `10`s), reporting `"timeout"` when zero probed fields succeed or `"partial"` when at least one succeeds; when `[capture.hardware].depth == "off"`, hardware, host, and filesystem run synchronously in separate failure-isolated guards with no background thread spawn.

### 3.3 Auto-Start Behavior

When `auto_start = true` (the default), `import pubrun` automatically calls `start()`. This is suppressed when:

- The `PUBRUN_AUTO_START` environment variable is set to `"false"`.
- The `PUBRUN_IMPORT_MODE` environment variable is set to `"noauto"` or `"minimal"`.
- The `[imports].mode` config is set to `"noauto"` or `"minimal"`.
- The process is running the `pubrun` CLI itself (detected by checking `sys.argv[0]`).

### 3.4 Import Modes

The library supports five namespaced import modes via submodule imports:

```python
import pubrun                    # Default: auto mode
import pubrun.auto as pubrun     # Explicit auto (same as above)
import pubrun.noauto as pubrun   # Load API, start later manually
import pubrun.nopatch as pubrun  # Auto-start, skip subprocess/console patching, signal hooks active
import pubrun.noconsole as pubrun # Auto-start, skip console patching, subprocess spying and signals active
import pubrun.minimal as pubrun  # API only, no auto-start, all patches and hooks disabled
import pubrun.full as pubrun     # Auto-start, all hooks, and FORCE the console tee on
```

| Mode | auto_start | patch_subprocesses | patch_console | signal_hooks | force_console | Meaning |
| --- | --- | --- | --- | --- | --- | --- |
| `auto` | `true` | `true` | `true` | `true` | `false` | Default. Auto-start on import. |
| `full` | `true` | `true` | `true` | `true` | `true` | Auto-start + all hooks + console tee FORCED on (overrides `capture_mode`; still subject to Jupyter/non-TTY guards). The opposite of `noconsole`. |
| `noauto` | `false` | `true` | `true` | `true` | `false` | Delay tracking until explicit `start()` call. |
| `nopatch` | `true` | `false` | `false` | `true` | `false` | Start tracking, but skip subprocess and console monkey-patching. Signal handlers remain active. |
| `noconsole` | `true` | `true` | `false` | `true` | `false` | Start tracking, patch subprocesses and signals, but skip stdout/stderr console wrapping. |
| `minimal` | `false` | `false` | `false` | `false` | `false` | Load API only. No auto-start, no patches, no signal hooks. |

These flags express what each mode **permits**, not what is active. Two layers gate
actual capture:

1. **The mode flag** (above) — whether the hook is permitted at all.
2. **Per-feature config** — whether the permitted hook is turned on.

The most important consequence: `patch_console = true` in `auto`/`noauto` only *permits*
the console tee; it does **not** wrap stdout/stderr by default, because
`[console].capture_mode` defaults to `"off"`. The tee activates only when
`capture_mode` is `"basic"`/`"standard"`/`"deep"`. Similarly, `patch_subprocesses`/
`signal_hooks` are permitted-and-on-by-default via `[capture.subprocesses].enabled` /
`[capture.signals].enabled` (both default `true`).

The exception is `force_console` (only `full`): it does not merely *permit* the tee, it
**forces** it on regardless of `capture_mode` (subject only to the Jupyter/non-TTY
safety guards). An in-code `import pubrun.<mode>` is thus an absolute imperative that
overrides env/config for the scope it dictates — `full` forces console on even against
`capture_mode = "off"`, and `noconsole` forces it off even against `"standard"`. Only
the launch-time `pubrun run --mode <mode>` overrides the in-code import.

When patching or signal hooks are disabled (by mode or config), the corresponding side
effects (`subprocess.Popen` interception, stdout/stderr wrapping, signal handler
registration) are suppressed. Static capture (hardware, packages, git, environment,
host, process, python) and background resource monitoring are **not gated by import
mode** and remain active in every mode whenever a run is running.

### 3.5 Explicit Activation

The library MUST support explicit activation via:

```python
pubrun.start()                        # Manual start
with pubrun.tracked_run():            # Context manager
    ...
@pubrun.audit_run(profile="deep")     # Decorator
def my_func(): ...
```

---

## 4. Required Artifacts

Each run MUST produce:

- `manifest.json` — The canonical structured metadata record. Schema version `"1.0"`.
- `config.resolved.json` — The fully resolved configuration used for the run.

The manifest MUST be usable without requiring event replay. It MUST strictly adhere to the JSON Schema defined in `schemas/manifest.schema.json`.

### 4.1 Timestamp Format

All timestamps in the manifest, event stream, and subprocess records MUST be stored as **POSIX epoch floats** (`time.time()`). ISO 8601 strings MUST NOT be used.

Rationale:

- Sub-second precision via IEEE 754 without truncation.
- Timezone-agnostic: eliminates locale-dependent formatting and parsing.
- Native compatibility with `time.time()`, `os.stat().st_mtime`, etc.
- Compact and deterministic serialization.

Timestamps establish absolute chronology only. Durations MUST NOT be computed by subtracting timestamps, because the system clock can jump during a run.

### 4.1.1 Duration Format

- Every persisted duration (`timing.*_seconds`, `phase_end` payload `elapsed_seconds`, and subprocess record `elapsed_seconds`) MUST be a nonnegative float in seconds computed from the difference of two monotonic `time.perf_counter()` readings, and MUST be labeled `duration_clock: "monotonic"`.
- Raw monotonic counter readings MUST NOT be serialized.
- Run durations are split into three disjoint, consecutive intervals: `startup_overhead_seconds` (`started_at_utc` to `workload_started_at_utc`), `workload_seconds` (`workload_started_at_utc` to `ended_at_utc`), and `finalization_overhead_seconds` (`ended_at_utc` to `finalized_at_utc`), which sum to `session_seconds`. `elapsed_seconds` equals `workload_seconds` with `elapsed_basis: "workload"`.
- `background_hardware_seconds` overlaps `workload_seconds` and `hardware_wait_seconds` is contained in `finalization_overhead_seconds`; neither may be summed with the disjoint intervals.
- `finalization_overhead_seconds` excludes the final atomic write of `manifest.json`.
- `interval_scope` is `"tracked_interval"`: durations cover only the interval from `Run` construction to finalization, so a late `import pubrun` or `start()` does not measure the whole process lifetime.
- Legacy v1.0 manifests whose `timing` has `elapsed_seconds` but neither `duration_clock` nor `elapsed_basis` MUST remain readable and MUST be labeled as legacy wall-clock timing (`wall_clock` / `wall_clock_legacy`) by consumers. Crashed-run closeouts record `duration_clock: "wall_clock_estimated"`, `elapsed_basis: "crashed_estimate"`, and `capture_state.status: "partial"`.
- Ghost-mode runs record `workload_seconds`, `elapsed_seconds`, `duration_clock`, and `elapsed_basis` as `null` with `capture_state.status: "partial"`.

See [Manifest Reference](manifest.md#timing) for the full field table.

### 4.2 Optional Artifacts

Depending on configuration, a run may also produce:

- `stdout.log` — Captured standard output (if console capture enabled)
- `stderr.log` — Captured standard error (if console capture enabled)
- `events.jsonl` — Structured event stream (if events enabled)
- `methods.md` or `methods.tex` — Auto-generated methodology paragraph

---

## 5. Capture Categories

### 5.1 Implemented Categories

Each category corresponds to a modular capture engine and a top-level manifest section.

| Category | Manifest Key | Config Section | Modes / Depth |
|---|---|---|---|
| Run identity | `run` | — | Always captured |
| Timing | `timing` | — | Always captured |
| Invocation | `invocation` | `[capture.inputs]` | `enabled`, `compute_md5` |
| Console | `console` | `[console]` | `off`, `basic`, `standard`, `deep` |
| Subprocesses | `subprocesses` | `[capture.subprocesses]` | `enabled = true/false` |
| Process | `process` | `[capture.process]` | depth-based |
| Host | `host` | `[capture.host]` | depth-based |
| Python | `python` | `[capture.python]` | depth-based |
| Packages | `packages` | `[capture.packages]` | `imported-only`, `imported-transitive`, `top-level-installed`, `full-environment` |
| Environment | `environment` | `[capture.environment]` | `allowlist`, `filtered`, `full` |
| Git | `git` | `[capture.git]` | depth-based |
| Hardware | `hardware` | `[capture.hardware]` | depth-based, explicit GPU/CPU flags |
| Resources | `resources` | `[capture.resources]` | depth-based, background thread |
| Signals | `signals` | `[capture.signals]` | `enabled = true/false` |
| Errors | `errors` | — | Always captured |
| Config | `config` | — | Always captured |
| Capture metadata | `capture` | — | Always captured |
| Status | `status` | — | Always captured |

### 5.2 Configured but Not Yet Implemented

| Category | Config Section | Status |
|---|---|---|
| Determinism | `[capture.determinism]` | Config key exists (`depth = "off"`). No capture engine implemented. |

### 5.3 Deferred (Future Work)

The following categories are planned but have no code or config:

- **Extensions** — Framework plugin model for custom capture engines.
- **Artifacts** — User-registered output file tracking.

Each category MUST be independently configurable.

---

## 6. Profiles

Built-in profile values (set via `[core].profile`):

- `minimal`
- `default`
- `deep`

Profiles control the default capture depth across all categories. Individual categories may override the profile via per-category `depth` settings:

- `off` — Category entirely disabled.
- `basic` — Fast, lightweight capture.
- `standard` — Comprehensive capture without significant overhead.
- `deep` — Maximum information gathering (may include slow system calls).

**Implementation note**: Profiles currently serve as a semantic hint. Per-category depth settings in `default.toml` define the actual capture behavior. The profile value is stored in the resolved config but does not programmatically map to specific depth combinations.

---

## 7. Events

Optional JSONL event stream written to `events.jsonl`.

### 7.1 Implemented Event Types

- `phase_start` — Emitted when entering a `pubrun.phase()` context.
- `phase_end`: Emitted when exiting a `pubrun.phase()` context. The payload includes `elapsed_seconds` (nonnegative monotonic duration of the phase body, excluding optional profiler setup and profile dump I/O) and `duration_clock: "monotonic"`, plus `error` (the exception type name) if an exception occurred.
- `annotation` — Emitted by `pubrun.annotate()`.

### 7.2 Event Record Format

```json
{
  "timestamp_utc": 1715290800.123,
  "type": "annotation",
  "name": "checkpoint",
  "payload": {"loss": 0.54}
}
```

`name` and `payload` are optional fields.

### 7.3 Throttling

Events are subject to a configurable budget (`max_tracked_events`, default 1,000,000). When the budget is exhausted, non-critical events are silently dropped.

**Critical events** (`phase_start`, `phase_end`, `annotation`) bypass the regular throttle. However, to prevent unbounded disk writes from scripts calling `annotate()` in tight loops, critical events are subject to a secondary cap of 10x `max_tracked_events` (minimum 10,000). Once this secondary cap is reached, all events — including critical ones — are dropped.

### 7.4 Thread Safety

Event writes are protected by a single `threading.Lock` covering both the budget check and the file I/O, preventing out-of-order writes and count overruns.

---

## 8. Console Capture

Supports tee-style capture of `stdout` and `stderr` via `TqdmSafeTee`.

Modes: `off`, `basic`, `standard`, `deep`.

Produces: `stdout.log` and `stderr.log`.

### 8.1 Carriage Return Squashing

The tee implementation detects carriage return (`\r`) sequences — common in progress bars (tqdm, rich) — and squashes redraws, keeping only the final state of each line. This prevents log files from growing to gigabytes during long training loops.

### 8.2 Behavioral Guarantee

Console capture MUST preserve normal console behavior. The user MUST see the same output they would see without pubrun installed.

---

## 9. Completeness, Redaction, and Security

### 9.1 Capture State

Each manifest section MUST include a `capture_state` object recording the status:

- `complete` — Data captured successfully.
- `partial` — Some data captured, errors occurred.
- `unavailable` — Data source not accessible (e.g., no git repo).
- `suppressed` — Capture disabled by configuration or profile.
- `failed` — Capture attempted but failed entirely.

If a capture section partially fails, the host script MUST NOT crash.

### 9.2 Redaction Engine

The system MUST support:

- **Regex-based detection** of sensitive variable names.
- **Destructive redaction** (default): values replaced with `{"representation": "redacted"}`.
- **Hashed redaction** (opt-in): values replaced with `{"representation": "hashed", "hash_algorithm": "sha256", "hash_value": "..."}`.

Default sensitive key regex:
```
(?i)(password|secret|token|api_key|key|auth|cred|private|conn_str|connection_string|database_url|dsn|signing|bearer)
```

### 9.3 Redaction Targets

Redaction applies to two independently configurable targets:

| Target | Config Key | Default | Mechanism |
|---|---|---|---|
| Environment variables | `[redaction].env_enabled` | `true` | Values of matching env var names are redacted |
| CLI arguments | `[redaction].argv_enabled` | `true` | `--flag=value` and `--flag VALUE` patterns where the flag name matches |

### 9.4 Security Requirements

- Secrets MUST NOT be captured by default.
- Unsalted hashes MUST NOT be computed unless explicitly configured.
- Redacted fields MUST emit a standard `redacted_value` object, not simply omit the key.

---

## 10. Configuration System

### 10.1 Purpose

Users MUST be able to define default behavior without modifying every script.

### 10.2 Configuration Discovery

Supported locations, applied in precedence order (lowest to highest):

| Priority | Source | Path |
|---|---|---|
| 1 (lowest) | Built-in defaults | `default.toml` (shipped with the library) |
| 2 | User home config | `~/.config/pubrun/config.toml` (or `%APPDATA%/pubrun/config.toml` on Windows) |
| 3 | Local deep config | `./.config/pubrun/config.toml` |
| 4 | Local root config | `./.pubrun.toml` |
| 5 | Environment variables | `PUBRUN_PROFILE`, `PUBRUN_AUTO_START`, `PUBRUN_META_REF` |
| 6 (highest) | API overrides | `pubrun.start(profile="deep")` |

When both `.pubrun.toml` and `.config/pubrun/config.toml` exist in the same directory, `.pubrun.toml` takes precedence (it is applied last).

### 10.3 Supported Environment Variables

| Variable | Effect |
|---|---|
| `PUBRUN_PROFILE` | Overrides `[core].profile`. Consumed in `resolve_config()` between local config and API overrides. |
| `PUBRUN_AUTO_START` | Overrides `[core].auto_start`. Consumed in the boot sequence (not in `resolve_config`). |
| `PUBRUN_META_REF` | Sets `[core].meta_ref`. Consumed in `resolve_config()` between local config and API overrides. |

### 10.4 Configuration Contents

The configuration MUST support defaults for:

- Profile / capture depth (`[core]`)
- Output base directory (`[core]`)
- Auto-start behavior (`[core]`)
- Import mode and conflict policy (`[imports]`)
- Console capture mode (`[console]`)
- Event capture enablement (`[events]`)
- Redaction policy (`[redaction]`)
- All capture category settings (`[capture.*]`)
- Diff engine configuration (`[diff]`)
- Methods format (`[methods]`)
- Logging / summary behavior (`[logging]`)

### 10.5 Configuration Format

TOML is the required format, leveraging Python 3.11+ `tomllib` (with `tomli` fallback for Python 3.8–3.10).

### 10.6 Configuration Logging

Each run MUST produce a `config.resolved.json` containing the fully resolved configuration snapshot.

### 10.7 Deep Merge Semantics

Configuration layers are merged recursively. Dictionary values are deeply merged; non-dictionary values (including lists) are overwritten by higher-precedence sources. The merge function uses `copy.deepcopy()` to prevent reference sharing.

---

## 11. CLI Tools

The CLI is accessible via `pubrun <command>` or `python -m pubrun <command>`.

### 11.1 Config Generation (`--create-config`)

Bootstraps a fully commented `.pubrun.toml` file.

Requirements:
- MUST include all major configurable options with default values already set.
- MUST be suitable for immediate user editing.
- MUST refuse to overwrite an existing file.
- If no destination is specified, an interactive prompt offers Local (`./.pubrun.toml`) or Global (`~/.config/pubrun/config.toml`).

### 11.2 Config Display (`--show-config`)

Prints the complete default configuration to the terminal.

### 11.3 System Info (`--info`)

Displays system capabilities, pubrun version, and environment details.

### 11.4 Self-Test (`--run-tests`)

Executes the built-in pytest test suite to verify the installation.

### 11.5 Global Context Generation (`meta`)

Captures a standalone environment snapshot for HPC parent-child hydration.

```
pubrun meta [--out PATH] [--basic|--standard|--deep]
```

- Default depth is `--deep` (captures full virtual environment).
- If `--out` is omitted, defaults to `./runs/meta.json`.
- Generates a JSON snapshot with `manifest_type = "pubrun-meta-snapshot"`.

### 11.6 Run Diagnostics (`report`)

Compiles execution metrics into a human-readable diagnostic summary.

```
pubrun report [RUN_DIR ...] [--basic|--standard|--deep]
```

- Accepts multiple run directories; processes them sequentially with visual separation.
- If no directory is given, auto-detects the most recent run in `./runs/`.
- Supports parent-child manifest hydration: if the manifest has a `meta_ref`, the parent context is merged.
- Detects environmental drift by comparing child script `mtime` against the parent snapshot timestamp.

### 11.7 Academic Methodology Exporter (`methods`)

Compiles execution provenance into a publication-ready "Computational Methods" paragraph.

```
pubrun methods [RUN_DIR] [--format markdown|latex]
```

- Hydrates the manifest with any linked parent `meta.json` before generating output.
- If `RUN_DIR` is omitted, auto-detects the most recent run.
- Default format honors `[methods].format` from configuration.

### 11.8 Reproducibility Fetcher (`rerun`)

Extracts the shell command needed to re-execute a recorded run.

```
pubrun rerun [RUN_DIR]
```

- Reads `invocation.rerun_command` from the manifest and prints it to stdout.
- Internal log messages go to stderr to support clean piping (`pubrun rerun | bash`).

### 11.9 Semantic Differ (`diff`)

Generates a structural comparison between two execution traces.

```
pubrun diff RUN_DIR_A RUN_DIR_B [OPTIONS]
```

Options:
- `--basic` (default) / `--standard` / `--deep` — Controls filtering via `[diff].ignore_*` lists.
- `--same` / `--no-same` — Show or hide unchanged values.
- `--wrap` / `--no-wrap` — Wrap long strings or truncate with ellipsis.
- `--max-length N` — Maximum character length before truncation.
- `--no-color` — Disable ANSI color output.
- `--export [txt|json]` — Export flattened output for external diff tools.

Terminal output uses the built-in inline ANSI renderer with color, truncation, wrapping, and path-split diffs.

### 11.10 Academic Citation (`cite`)

Generates a formatted citation for crediting `pubrun`.

```
pubrun cite [--style apa|mla|chicago|bibtex]
```

### 11.11 Run Monitoring (`status`)

Lists all runs with their current status or inspects a specific run in detail.

```
pubrun status [RUN_ID] [--dir PATH] [-v|--verbose]
```

- Classifies runs as completed, failed, interrupted, broken pipe, running, crashed, or ghost via lock-file PID liveness checks and signal analysis.
- Shows script name with command-line arguments when terminal width permits.
- Verbose mode (`-v`) includes PID, hostname, RSS, CPU, events, and signals.
- Inspect mode (`pubrun status <id>`) shows full detail for a single run.

### 11.12 Run Cleanup (`clean`)

Interactively delete old run directories.

```
pubrun clean [--dir PATH] [--older-than AGE] [--status STATUS] [-y|--yes] [--dry-run]
```

- Lists candidates with age and size before prompting for confirmation.
- Interactive mode: requires explicit selection by number, range (e.g. `1-3,5`), or `all`. Shows a confirmation table of selected runs before final `y/N` prompt. Nothing is deleted without explicit confirmation.
- Running processes are never deleted regardless of filters.
- `--older-than` accepts days (`7d`), hours (`24h`), or bare numbers (days).
- `--status` accepts comma-separated values (e.g. `completed,failed`). Default: all non-running.

### 11.13 Import Mode Wrapper (`run`)

Spawns a child process with `PUBRUN_IMPORT_MODE` set in the environment.

```
pubrun run [--mode MODE] -- COMMAND [ARGS...]
```

- Sets `PUBRUN_IMPORT_MODE` in the child process environment.
- Returns the child process exit code.
- Does not create a run in the wrapper process itself.
- The double dash (`--`) separates pubrun wrapper options from the target command.

Use cases: CI pipelines, shell scripts, Slurm submission scripts, and any case where source code should remain unchanged but import behavior needs control.

### 11.14 Log Interleaving (`combined`)

Post-execution command that chronologically interleaves stdout and stderr logs from one or more runs.

```
pubrun combined [RUN_IDS ...] [--dir PATH] [--output FILE] [-y|--yes] [-f|--force]
```

- Accepts one or more run IDs. If omitted, defaults to the most recent run in `./runs/`.
- Parses ISO 8601 timestamps written in standard/deep console modes to chronological order.
- Prefixes each line with stream origin: `[stdout]` / `[stderr]` (and run ID if multiple runs).
- Size thresholds: warns at 250 MB (skipped via `--yes`), aborts at 500 MB (overridden via `--force`).
- If logs lack timestamps, falls back to sequential concatenation.

---

## 12. Run Directory

### 12.1 Naming Convention

```
<base_dir>/runs/pubrun-<script>-<timestamp>-<pid>-<run_id>/
```

Example:
```
./runs/pubrun-train-20260509T120000Z-12345-a1b2c3d4/
```

### 12.2 Requirements

- Each run directory name MUST include a UTC timestamp, script identifier, PID, and 8-character hex run ID.
- Directory creation MUST be race-safe (uses `mkdir(parents=True, exist_ok=True)`).
- Run directory names MUST be globally unique within the base directory.

### 12.3 Contents

Required: `manifest.json`, `config.resolved.json`.

Optional: `stdout.log`, `stderr.log`, `events.jsonl`, `methods.md`/`methods.tex`.

---

## 13. Replay and Comparison

The manifest MUST support:

- `pubrun diff` — Semantic comparison between two run manifests.
- `pubrun rerun` — Extraction of the exact replay command.

To support this, the manifest MUST include structured and normalized information about: command line, working directory, Python executable, package versions, environment hints, git state, and output locations.

Replay is **advisory, not guaranteed**. Environment differences between the original and replay machine may cause divergent behavior.

---

## 14. Public API

### 14.1 Implemented Functions

| Function | Signature | Behavior |
|---|---|---|
| `start(**overrides)` | Returns `Run` | Begins tracking. If a run is already active, increments `ref_count` and merges overrides (re-entrant). |
| `stop()` | Returns `None` | Finalizes the active run. Decrements `ref_count`; only writes artifacts when count reaches zero. Safe to call with no active run. |
| `get_current_run()` | Returns `Run \| None` | Returns the active singleton tracker, or `None`. |
| `annotate(message, **kwargs)` | Returns `None` | Emits an `annotation` event. Behavior with no active run is configurable: `ignore` (default), `warn`, or `error`. |
| `phase(name)` | Context manager | Emits `phase_start`/`phase_end` events; `phase_end` carries a monotonic `elapsed_seconds` and `duration_clock: "monotonic"`. Records error type in payload if an exception occurs. |
| `paused()` | Context manager | Suspends *recording* (console tee + subprocess spy) on the calling thread for the block — output still prints, subprocesses still run, but are not recorded. Thread-local, ref-counted/nestable, resumes on exception. Does not pause `annotate()`/`phase()` or resource sampling. |
| `tracked_run(**overrides)` | Context manager | Wraps `start()`/`stop()`. Sets outcome to `"failed"` on exception. |
| `audit_run(**overrides)` | Decorator | Wraps a function in `start()`/`stop()`. Preserves return value. Sets outcome to `"failed"` on exception, then re-raises. |
| `diff(a, b, ignores)` | Returns `dict` | Compares two run directories. Returns `{"added": ..., "removed": ..., "modified": ..., "same": ...}`. |
| `report(name, data)` | Returns `None` | Writes a JSON (`dict`/`list`) or text report into the run directory and emits an annotation. |
| `artifact(filename, content)` | Returns `None` | Writes a text or bytes file into the run directory (run-internal output) and emits an annotation. |
| `print(*args, **kwargs)` | Returns `None` | Calls the builtin `print()` and appends the text to `stdout.log`, independently of console wrapping. |
| `open(file, mode="r", **kwargs)` | Returns a file object | Wraps `builtins.open()` for that one file and records a `data_files` entry at `[capture.file_io].level`. Never patches the global `open()`. At `hash`, a sequential binary read or write is hashed as it streams; otherwise the file is re-read at close. |
| `subprocess.run(...)` / `subprocess.Popen(...)` | As `subprocess` | Explicit subprocess wrappers that record argv, timing, and exit code without the global spy. |
| `popen(cmd, mode="r", bufsize=-1)` | As `os.popen` | Tracked `os.popen()` replacement. |
| `register_file(path, role="input", *, label, digest, digest_algorithm, level, verify_digest, defer, metadata)` | Returns `dict \| None` | Records an external file read or written by other code (for example a library) into `data_files.inputs`, `outputs`, or `mixed`, without wrapping its I/O. A caller digest is recorded as asserted unless `verify_digest=True`. Outputs may be registered before they exist and are completed at finalization. Returns `None` with no active run or at level `none`. |
| `register_input(path, ...)` | Returns `dict \| None` | `register_file(path, role="input", ...)`. |
| `register_output(path, ..., defer=False)` | Returns `dict \| None` | `register_file(path, role="output", ...)`. |

### 14.2 Re-Entrant Start Behavior

If `start()` is called while a run is already active:
1. The existing run's `ref_count` is incremented.
2. If the override includes a new `output_dir`, the run directory is migrated via `shutil.move()`.
3. The existing `Run` instance is returned (not a new one).

### 14.3 Deferred APIs (Future Work)

The following APIs are planned but not implemented:

- `register_metadata()` — Inject structured metadata into the manifest.
- `register_seed()` — Record pseudorandom seeds for determinism tracking.

The previously planned `register_artifact()` is retired and will not be added: use
`pubrun.artifact()` to write a file into the run directory, and
`pubrun.register_output()` or `pubrun.register_file()` to record an external file
produced elsewhere (see 14.1).

---

## 15. Subprocess Spy

### 15.1 Mechanism

`SubprocessSpy` monkey-patches `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` to transparently record spawned process metadata.

### 15.2 Recorded Fields

Each subprocess record includes: `argv`, `started_at_utc`, `ended_at_utc`, `cwd`, `exit_code`, and `capture_state`. Once the process is observed to finish (or the launch fails, or finalization closes an unwaited record), the record also carries `elapsed_seconds` (nonnegative monotonic duration) and `duration_clock: "monotonic"`. Monotonic start readings are held in an internal map keyed by record identity and are never serialized. The explicit wrappers (`pubrun.subprocess.run`, `pubrun.subprocess.Popen`, `pubrun.popen`) record the same timing fields plus `pid`, and on a failed launch record `error` and `capture_state: {"status": "failed", "detail": ...}` before re-raising.

### 15.3 Memory Safety

Recording stops after `max_tracked_commands` (default 5000) to prevent OOM in long-running loops.

### 15.4 Thread Safety

Record mutations are protected by `threading.Lock`.

### 15.5 Internal Bypass

Internal `pubrun` subprocess calls (e.g., `git` queries) use the `disable_spy()` context manager to prevent circular logging.

### 15.6 Argv Redaction

If `[redaction].argv_enabled = true`, subprocess argument values matching the sensitive key regex are replaced with `[REDACTED]` before recording.

### 15.7 OS System Interception

`os.system(cmd)` calls are intercepted. The command string is parsed via `shlex.split()` with a fallback for unterminated quotes.

**Windows limitation**: `os.system` interception uses shell-string parsing rather than structured argument lists.

---

## 16. Resource Watcher

### 16.1 Mechanism

`ResourceWatcher` is a daemon thread that periodically samples process memory (RSS) and CPU utilization.

### 16.2 Configuration

- `scope` (default `"process"`): `"process"` monitors only the main process; `"tree"` sums RSS/CPU across the entire process tree (parent + all child processes).
- `sample_interval_seconds` (default 15): How often the thread wakes to sample.
- `max_consecutive_failures` (default 3): The thread self-terminates after this many consecutive read failures.

### 16.3 Platform Support

| Platform | RSS Source (process) | RSS Source (tree) |
|---|---|---|
| Linux | `/proc/self/statm` | `/proc/<pid>/task/<pid>/children` recursive walk |
| macOS | `ps -o rss= -p <pid>` | `ps -eo pid,ppid,rss` with in-Python tree walk |
| Windows | `wmic process get WorkingSetSize` | Not yet implemented (falls back to process) |

### 16.4 Output

The `resources` manifest section contains: `scope`, `peak_rss_bytes`, `end_rss_bytes`, `peak_cpu_percent`. When `scope = "tree"`, also includes `peak_tree_rss_bytes` and `end_tree_rss_bytes`.

---

## 16b. Phase-Scoped Profiling

### 16b.1 Mechanism

When `[capture.profiling].enabled = true`, `pubrun.phase()` blocks are profiled using the configured backend. A `profile-<phase_name>.prof` file is saved to the run directory for each phase.

### 16b.2 Configuration

- `enabled` (default `false`): Must be explicitly opted in.
- `backend` (default `"cprofile"`): `"cprofile"` uses stdlib (zero dependencies); `"yappi"` requires user installation.

### 16b.3 Output

Each profiled phase produces a pstats-compatible `.prof` file. A `profile_saved` event is emitted to `events.jsonl` for discoverability.

---

## 17. Ghost Mode

Ghost mode activates strictly when run output is unusable at startup: either `run_dir.mkdir()` fails or the initial `ArtifactWriter.write_startup_manifest()` fails (for example, on a read-only filesystem or unavailable storage). A failure inside an individual capture engine MUST NOT trigger ghost mode; it degrades only that section into a partial manifest.

When startup output fails:

1. If any hooks, background workers, file handles, or `.pubrun.lock` were already created by the failing run, `Run` latches `_finalized = True`, `_hardware_write_closed = True`, and `is_active = False` under `_run_lock`, then calls `_rollback_owned_hooks(stage="rollback")` to tear down only resources owned by this run while leaving pre-existing and later third-party wrappers intact.
2. `atexit` registration is skipped (or unregistered).
3. `writer` is cleared to `None`, `is_active` is set to `False`, `status.outcome` is set to `"ghost"`, and `_active_run` is published so nested `start()` calls increment `ref_count` without running `_merge_and_migrate()`.
4. One bounded, redacted warning is printed to `sys.stderr` (never raw exception tracebacks or sensitive values).
5. The host script continues execution unaffected. Calling `stop()` on a ghost run preserves `outcome = "ghost"` and clears `_active_run` when `ref_count` reaches zero.

Ghost mode MUST never crash the host script.

---

## 18. HPC Parent-Child Hydration

### 18.1 Purpose

In large cluster deployments, child runs can skip heavy capture (packages, hardware, environment) and inherit it from a shared parent snapshot.

### 18.2 Workflow

1. **Parent**: `pubrun meta --out ./shared/meta.json --deep`
2. **Children**: `export PUBRUN_META_REF=meta.json && python script.py`

### 18.3 Hydration Rules

When `meta_ref` is set and a report/methods command is invoked:

- The hydrator loads the referenced `meta.json`.
- For each section in `[hardware, process, python, packages, environment, git]`: if the child section is missing or has `capture_state.status` in `[suppressed, off, unavailable, unknown, partial]`, it is replaced with the parent section.
- Hydrated sections are marked with `is_hydrated = true`.

### 18.4 Drift Detection

The hydrator compares the child script's `mtime` against the parent snapshot's `started_at_utc`. If the script was modified after the parent snapshot, a drift warning is emitted.

### 18.5 Security

The `meta_ref` path MUST end with `.json`. If it resolves outside the manifest's parent directory, it is **rejected by default** to prevent arbitrary file reads from tampered manifests. This behavior is controlled by `[report].allow_external_meta_ref` (bool, default `false`) and `[report].meta_ref_allowed_dirs` (list of permitted absolute paths). HPC workflows that legitimately reference shared files should add the shared directory to the allowlist.

---

## 19. Writer and Finalization

### 19.1 Artifact Writer

The `ArtifactWriter` serializes run state to disk and reports write outcomes without raising into the host script.

Artifacts written:
1. `manifest.json`: Written atomically via `Run.to_manifest_dict()` at startup (`write_startup_manifest()`, returning `True` on success or `False` on failure while recording a bounded redacted `last_error`), optionally refreshed once when background hardware finishes (if initial startup did not already include completed hardware and the run is still active and unfinalized), and written once at finalization (`write_artifacts()`, returning `True` when `manifest.json` wrote atomically or was already written for a finalized run, and `False` on failure).
2. `config.resolved.json`: Written atomically at startup with the resolved configuration dictionary. `ArtifactWriter` tracks `(target_path, sha256_digest, durability_rank)` over canonical sorted JSON so unchanged configuration skips redundant rewrites during hardware refreshes and finalization. Mid-run configuration changes or `run_dir` migrations via `Run._merge_and_migrate()` persist updated `config.resolved.json` immediately through `sync_config_if_changed()`. At finalization, `config.resolved.json` writes are guarded separately so a config write failure logs at most one bounded redacted warning and never prevents writing `manifest.json`.
3. `methods.md` or `methods.tex`: Auto-generated methodology paragraph written at finalization. A failure in methods generation is non-fatal and MUST NOT cause `write_artifacts()` to return `False`.

When `write_artifacts()` fails to write `manifest.json`, it records a bounded redacted `last_error` and emits at most one bounded redacted warning (`_write_failure_warned`) without dumping tracebacks or configuration dictionaries. `ArtifactWriter.unregister_atexit()` removes the registered `atexit` callback cleanly during normal `stop()` or ghost rollback.

### 19.2 Finalization Lifecycle

1. `stop()` preserves sticky `"failed"` and `"ghost"` outcomes, decrements `ref_count`, and when `ref_count` reaches zero calls `_finalize_state()` and `write_artifacts()` inside `try ... finally:`. The `finally` block always unregisters `atexit` (when a writer exists) and clears `_active_run` if it still points to this run.
2. `_finalize_state()` is **idempotent** (guarded by `_finalized` under `_run_lock`). It:
   - Latches `_finalized = True` and records the workload-end anchor `t2` (`ended_at_utc` plus an in-memory monotonic reading) under `_run_lock`, before waiting for background hardware, so teardown latency never inflates `workload_seconds`.
   - Runs every pre-teardown step independently in its own `try/except` guard: waiting up to `2.0`s for background hardware completion (then closing `_hardware_write_closed = True` under `_run_lock`), checking `signal_capture.get_records()` for interruption signals (`SIGINT`, `SIGTERM`, `SIGHUP`), and recording the process exit code.
   - Runs every teardown step independently via `_rollback_owned_hooks(stage="finalization")` so a first or second cleanup failure never blocks remaining steps: (a) `SubprocessSpy.finalize_all()`, record snapshot, and `SubprocessSpy.uninstall(owner=...)` in separate guards; (b) `ConsoleInterceptor.stop()` (marking `console` `"failed"` instead of `"pending"` if teardown raises); (c) `ResourceWatcher.stop()` and `to_manifest_dict()` in separate guards; (d) pending deferred file registrations; (e) `EventStream.close()`; (f) disabling active profilers individually; (g) `SignalExitCapture.get_records()` and `uninstall()` in separate guards; (h) removing `.pubrun.lock`.
   - Refreshes and merges finalization package snapshots safely without losing startup package data if refresh fails.
3. `write_artifacts()` calls `_finalize_state()` before acquiring reentrant `_write_lock` (preserving `_run_lock` before `_write_lock` lock ordering to prevent deadlock with `pubrun-hw`), checks `_artifacts_written` for idempotency, persists or durability-upgrades `config.resolved.json` if needed, records the finalization-end anchor `t3` (`finalized_at_utc`), builds the manifest (which freezes the finalized `timing` section on first build so it is never recomputed), writes final `manifest.json` once atomically, sets `_artifacts_written = True`, and writes `methods.{md,tex}` non-fatally.
4. The `atexit` handler calls `write_artifacts()` as a safety net (unregistered after normal `stop()`; if invoked after finalization, `_artifacts_written` returns `True` immediately without rewriting finalized artifacts).
5. During active execution, if `EventStream.emit()` encounters a disk write or flush error, it closes and detaches `self._file = None` and clears its buffer under `self._lock` (preventing repeated failing writes) and emits at most one bounded redacted warning outside `self._lock` per failure episode.

### 19.3 Atomic Visibility, Explicit Durability Policy, and Platform Limits

Atomic visibility is always enforced regardless of durability policy: every write to `manifest.json` and `config.resolved.json` uses a unique temporary file, `flush()`, and `os.replace()`, ensuring concurrent readers never observe partial JSON and cleaning up temporary files on error.

Explicit disk synchronization is configured separately via `[core].artifact_durability` (default `"fsync"`):

- `"fsync"` (default): Calls file `os.fsync()` before `os.replace()` on startup, refresh, and finalized writes (no parent-directory sync).
- `"finalize"`: Omits `os.fsync()` on intermediate startup and refresh snapshots while preserving atomic visibility; applies file `os.fsync()` on finalization in `write_artifacts()`, upgrading an unchanged startup `config.resolved.json` in place (`open(..., "r+b")` + `os.fsync()`) without rewriting it (falling back to atomic rewrite on `OSError`).
- `"atomic"`: Atomic temporary file and `os.replace()` with zero `os.fsync()` calls.
- `"strict"`: File `os.fsync()` before `os.replace()` plus best-effort Portable Operating System Interface (POSIX) parent-directory `os.fsync()` (`O_DIRECTORY | O_CLOEXEC`) after `os.replace()`.
- Invalid values log one bounded warning per distinct invalid value and fall back safely to `"fsync"`.

Platform limits: Linux uses POSIX `fsync(2)`; macOS uses POSIX `fsync(2)` rather than `F_FULLFSYNC`; Windows uses `FlushFileBuffers` on files only (parent-directory sync is unsupported and skipped cleanly in `"strict"` mode); Network File System (NFS) and Lustre incur synchronous remote procedure call (RPC) and writeback overhead on `fsync` and skip unsupported directory sync cleanly on `OSError`.

### 19.4 Golden Rule

The writer MUST catch all exceptions. pubrun MUST NEVER crash the host script due to serialization failure.

---

## 20. Failure Behavior

The system MUST:

- Never crash the host script due solely to capture, cleanup, or serialization failure.
- Isolate every capture engine (`invocation`, `git`, `process`, `python`, `packages`, `environment`, `hardware`, `host`, `filesystem`, `subprocesses`, `console`, `events`, `resources`, and `signals`) inside its own failure guard (`hardware`, `host`, and `filesystem` each isolated separately) so an error in one engine preserves unrelated healthy sections and the host script's normal return value and exit code.
- Mark each failed section with `capture_state.status = "failed"` and a single-line, redacted, length-bounded `detail` string (`<= 240` characters via `format_safe_error_detail()`, with no tracebacks or leaked secrets).
- Set `capture.capture_state.status = "partial"` (naming the degraded sections in `detail`) whenever any section failed, covering both escaping exceptions and self-caught failed returns, while keeping `status.outcome` accurate to the host script's execution outcome.
- Record structured `capture-error` entries (`kind = "capture-error"`, `type`, bounded redacted `message`, `traceback = null`, optional `section`, optional `stage`) in `errors.records` under `_errors_lock`, capped at `MAX_CAPTURE_ERRORS = 50`. When additional errors exceed the cap, set `errors.capture_state.status = "partial"` with the omitted count.
- Emit bounded runtime warnings without traceback spam: at most one warning per `(section, stage)` in `Run`, at most one per write-failure episode in `EventStream` (outside its lock), and at most one on finalization write failure in `ArtifactWriter`.
- Enforce transactional installation, prior `faulthandler.is_enabled()` preservation, identity-guarded restoration, and passive passthrough across all process-global hooks (`sys.stdout`/`sys.stderr`, `faulthandler`, signal handlers, `sys.excepthook`, `subprocess.Popen.__init__`, `subprocess.Popen.wait`, `os.system`) so later third-party wrappers are never overwritten.
- Surface partial manifests honestly in downstream consumers without crashing on `null` or malformed fields:
  - `pubrun report` (across `basic`, `standard`, `deep`, and `section="env"`/`"packages"` extracts, respecting `NO_COLOR`) renders a bounded `[WARN ]` summary of failed sections and up to 10 `capture-error` records (with overflow and truncation detail) and displays `capture failed` instead of misleading empty counts.
  - `pubrun inspect` emits `WARN` findings (`{section}_capture_failed`, deduplicated `capture_error_{section}`, and `errors_capture_partial` truncation notices) distinct from `"suppressed"` (`*_off`).
  - `pubrun methods` (both single-run and multi-run across all manifests in scope) states explicitly when package capture failed or was disabled rather than claiming standard-library-only dependencies, and appends a partial-provenance disclosure (escaping underscores in LaTeX) while leaving healthy complete manifests unchanged.

---

## 21. Acceptance Criteria

A valid implementation must satisfy all of the following:

1. `import pubrun` works cleanly.
2. `from pubrun import start` works cleanly.
3. Plain import is lightweight and safe (boot failure does not crash).
4. Configuration is discovered from home and local locations.
5. `pubrun --create-config` creates a fully commented default config.
6. `pubrun --show-config` displays the default config.
7. `pubrun --info` displays system capabilities.
8. `pubrun --run-tests` executes the self-test suite.
9. One-line explicit usage (`pubrun.start()` / `pubrun.stop()`) works.
10. A manifest is produced for tracked runs.
11. Failures are captured without breaking the host script.
12. Console teeing is configurable and preserves normal output.
13. Output is deterministic enough for comparison tooling.
14. Sensitive values are redacted by default.
15. Environment variable `PUBRUN_META_REF` sets `core.meta_ref`.
16. Environment variable `PUBRUN_AUTO_START` overrides auto-start.
17. Environment variable `PUBRUN_PROFILE` overrides `core.profile`.
18. Phase and annotation events bypass event throttling.

---

## 22. Summary

`pubrun` provides structured, low-friction run provenance with optional depth and extensibility.

It supports both explicit activation and configuration-driven automatic behavior, including standard import patterns, discoverable configuration files, and generation of a fully commented default configuration file.

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
