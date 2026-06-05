[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md)

# pubrun Functional Specification

> Status: v0.3.0
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
- **Explicit APIs**: `start()`, `stop()`, `annotate()`, `phase()`, `tracked_run()`, `audit_run()`, `diff()`.

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

### 3.3 Auto-Start Behavior

When `auto_start = true` (the default), `import pubrun` automatically calls `start()`. This is suppressed when:

- The `PUBRUN_AUTO_START` environment variable is set to `"false"`.
- The `PUBRUN_IMPORT_MODE` environment variable is set to `"noauto"` or `"quiet"`.
- The `[imports].mode` config is set to `"noauto"` or `"quiet"`.
- The process is running the `pubrun` CLI itself (detected by checking `sys.argv[0]`).

### 3.4 Import Modes

The library supports four namespaced import modes via submodule imports:

```python
import pubrun                    # Default: auto mode
import pubrun.auto as pubrun     # Explicit auto (same as above)
import pubrun.noauto as pubrun   # Load API, start later manually
import pubrun.nopatch as pubrun  # Auto-start, no global hooks
import pubrun.quiet as pubrun    # API only, no auto-start, no hooks
```

| Mode | auto_start | global_hooks | Meaning |
| --- | --- | --- | --- |
| `auto` | `true` | `true` | Default. Full tracking on import. |
| `noauto` | `false` | `true` | Delay tracking until explicit `start()` call. Hooks install on start. |
| `nopatch` | `true` | `false` | Start tracking, but do not install subprocess spy, console tee, or signal handlers. |
| `quiet` | `false` | `false` | Load API only. No auto-start, no hooks unless explicitly overridden. |

When `global_hooks = false`, the following process-global side effects are suppressed:

1. `subprocess.Popen` / `os.system` interception.
2. Console stream replacement (`sys.stdout` / `sys.stderr` wrapping).
3. Signal handler installation.

Static capture (hardware, packages, git, environment, host, process, python) and background resource monitoring are unaffected by `global_hooks`.

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
- Trivial elapsed-time arithmetic (`ended_at - started_at`).
- Native compatibility with `time.time()`, `os.stat().st_mtime`, etc.
- Compact and deterministic serialization.

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
| Packages | `packages` | `[capture.packages]` | `imported-only`, `top-level-installed`, `full-environment` |
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
- **Combined console log** — Interleaved stdout+stderr in a single `combined.log`.

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
- `phase_end` — Emitted when exiting a `pubrun.phase()` context. Includes error type in payload if an exception occurred.
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
| `phase(name)` | Context manager | Emits `phase_start`/`phase_end` events with timing. Records error type in payload if an exception occurs. |
| `tracked_run(**overrides)` | Context manager | Wraps `start()`/`stop()`. Sets outcome to `"failed"` on exception. |
| `audit_run(**overrides)` | Decorator | Wraps a function in `start()`/`stop()`. Preserves return value. Sets outcome to `"failed"` on exception, then re-raises. |
| `diff(a, b, ignores)` | Returns `dict` | Compares two run directories. Returns `{"added": ..., "removed": ..., "modified": ..., "same": ...}`. |

### 14.2 Re-Entrant Start Behavior

If `start()` is called while a run is already active:
1. The existing run's `ref_count` is incremented.
2. If the override includes a new `output_dir`, the run directory is migrated via `shutil.move()`.
3. The existing `Run` instance is returned (not a new one).

### 14.3 Deferred APIs (Future Work)

The following APIs are planned but not implemented:

- `register_artifact()` — Track user-produced output files.
- `register_metadata()` — Inject structured metadata into the manifest.
- `register_seed()` — Record pseudorandom seeds for determinism tracking.

---

## 15. Subprocess Spy

### 15.1 Mechanism

`SubprocessSpy` monkey-patches `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` to transparently record spawned process metadata.

### 15.2 Recorded Fields

Each subprocess record includes: `argv`, `started_at_utc`, `ended_at_utc`, `cwd`, `exit_code`.

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

- `sample_interval_seconds` (default 15): How often the thread wakes to sample.
- `max_consecutive_failures` (default 3): The thread self-terminates after this many consecutive read failures.

### 16.3 Platform Support

| Platform | RSS Source |
|---|---|
| Linux | `/proc/self/statm` |
| macOS | `ps -o rss= -p <pid>` |
| Windows | `wmic process get WorkingSetSize` |

### 16.4 Output

The `resources` manifest section contains: `peak_rss_bytes`, `end_rss_bytes`, `peak_cpu_percent`.

---

## 17. Ghost Mode

If the run directory cannot be created (e.g., read-only filesystem on strict HPC nodes):

1. A warning is printed to stderr.
2. All capture is suppressed — the tracker becomes a silent no-op.
3. The run outcome is set to `"ghost"`.
4. The host script continues execution unaffected.

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

The `ArtifactWriter` is responsible for serializing the run state to disk.

Artifacts written:
1. `manifest.json` — via `Run.to_manifest_dict()`.
2. `config.resolved.json` — the resolved configuration dictionary.
3. `methods.md` or `methods.tex` — auto-generated methodology paragraph (failure is non-fatal).

### 19.2 Finalization Lifecycle

1. `stop()` sets the outcome, decrements `ref_count`, and calls `_finalize_state()`.
2. `_finalize_state()` is **idempotent** (guarded by `_finalized` flag). It:
   - Records `ended_at_utc`.
   - Determines outcome (`completed` or `failed` based on `sys.exc_info()`).
   - Uninstalls the subprocess spy.
   - Stops the console interceptor.
   - Stops the resource watcher.
   - Closes the event stream.
3. `write_artifacts()` serializes to disk.
4. The `atexit` handler calls `write_artifacts()` as a safety net.

### 19.3 Golden Rule

The writer MUST catch all exceptions. pubrun MUST NEVER crash the host script due to serialization failure.

---

## 20. Failure Behavior

The system MUST:

- Never crash the host script due solely to capture failure.
- Emit a partial manifest if needed.
- Record capture errors in the `errors` section.
- Degrade gracefully when optional features are unavailable.

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

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md)
