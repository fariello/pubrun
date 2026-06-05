[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md)

# pubrun Manifest Reference

Every `pubrun` run produces a `manifest.json` file containing structured metadata about the execution. This document defines every field in the manifest.

The formal JSON Schema is at [`schemas/manifest.schema.json`](../schemas/manifest.schema.json).

---

## Top-Level Fields

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Always `"1.0"`. |
| `manifest_type` | string | Always `"pubrun-manifest"`. Distinguishes from `"pubrun-meta-snapshot"`. |
| `meta_ref` | string \| null | Path to a parent `meta.json` for HPC hydration. `null` if not used. |

---

## `run`

Run identity.

| Field | Type | Description |
|---|---|---|
| `run_id` | string | 8-character hex identifier (e.g., `"a1b2c3d4"`). |
| `capture_state` | object | See [Capture State](#capture-state). |

---

## `timing`

Execution timestamps. All values are **POSIX epoch floats** (`time.time()`), not ISO 8601 strings.

| Field | Type | Description |
|---|---|---|
| `started_at_utc` | float | When `start()` was called. |
| `ended_at_utc` | float | When `stop()` was called. |
| `elapsed_seconds` | float | `ended_at_utc - started_at_utc`. |
| `capture_state` | object | See [Capture State](#capture-state). |

> [!NOTE]
> **Why floats?** POSIX epoch floats provide sub-second precision, timezone-agnostic storage, trivial elapsed-time arithmetic, and deterministic serialization. See [Architecture](architecture.md) for full rationale.

---

## `invocation`

What was run and how.

| Field | Type | Description |
|---|---|---|
| `argv` | list[string] | `sys.argv` at invocation time. Sensitive values may be redacted. |
| `command_line` | string | Joined `argv` string. |
| `rerun_command` | string | Shell command to reproduce the run (e.g., `cd /path && python script.py`). |
| `entrypoint_type` | string | `"script"`, `"module"`, or `"interactive"`. |
| `script` | object | Script file metadata (see below). |
| `working_directory` | object | `{"path": "/abs/path", "real_path": "/resolved/path"}`. |
| `inputs` | list[object] | Detected input files from `sys.argv` (path, size, mtime, optional md5). |
| `capture_state` | object | See [Capture State](#capture-state). |

### `invocation.script`

| Field | Type | Description |
|---|---|---|
| `path` | string | Absolute path to the entry-point script. |
| `basename` | string | Filename only. |
| `size` | int | File size in bytes. |
| `mtime` | float | Last modification time (POSIX epoch float). |
| `sha256` | string | SHA-256 hash of the file contents. |

---

## `console`

Console capture metadata.

| Field | Type | Description |
|---|---|---|
| `capture_mode` | string | `"off"`, `"basic"`, `"standard"`, or `"deep"`. |
| `stdout` | object | `{"path": "stdout.log", "lines_captured": N}`. |
| `stderr` | object | `{"path": "stderr.log", "lines_captured": N}`. |
| `capture_state` | object | See [Capture State](#capture-state). |

---

## `subprocesses`

Array of subprocess records. Each element:

| Field | Type | Description |
|---|---|---|
| `argv` | list[string] | Command and arguments. Sensitive values may be redacted. |
| `started_at_utc` | float | Start time (POSIX epoch float). |
| `ended_at_utc` | float \| null | End time, or `null` if the process was still running at finalization. |
| `cwd` | string | Working directory of the subprocess. |
| `exit_code` | int \| null | Exit code, or `null` if the process was not waited on. |
| `capture_state` | object | See [Capture State](#capture-state). |

---

## `process`

Process-level metadata.

| Field | Type | Description |
|---|---|---|
| `pid` | int | Process ID. |
| `ppid` | int | Parent process ID. |
| `user` | object | User identity (see below). |
| `capture_state` | object | See [Capture State](#capture-state). |

### `process.user`

| Field | Type | Description |
|---|---|---|
| `username` | object | `{"representation": "plain", "value": "username"}`. May be `"redacted"`. |
| `uid` | int | User ID (Unix only; `null` on Windows). |
| `gid` | int | Group ID (Unix only; `null` on Windows). |

---

## `python`

Python runtime environment.

| Field | Type | Description |
|---|---|---|
| `executable` | string | Path to the Python binary. |
| `version` | string | Full version string from `sys.version`. |
| `implementation` | string | `"cpython"`, `"pypy"`, etc. |
| `prefix` | string | `sys.prefix`. |
| `base_prefix` | string | `sys.base_prefix`. Differs from `prefix` inside a virtual environment. |
| `virtual_env` | string \| null | Path to the active virtual environment, or `null`. |
| `sys_path` | list[string] | The Python module search path. |
| `capture_state` | object | See [Capture State](#capture-state). |

---

## `packages`

Tracked Python dependencies.

| Field | Type | Description |
|---|---|---|
| `mode` | string | `"imported-only"`, `"top-level-installed"`, or `"full-environment"`. |
| `records` | list[object] | Package records (see below). |
| `capture_state` | object | See [Capture State](#capture-state). |

### `packages.records[]`

| Field | Type | Description |
|---|---|---|
| `name` | string | Package name. |
| `version` | string | Installed version. |
| `location` | string \| null | Install location path, if available. |
| `editable` | bool \| null | Whether the package is installed in editable (development) mode. |

---

## `environment`

Captured environment variables.

| Field | Type | Description |
|---|---|---|
| `mode` | string | `"allowlist"`, `"filtered"`, or `"full"`. |
| `variables` | list[object] | Variable records (see below). Sorted by name. |
| `capture_state` | object | See [Capture State](#capture-state). |

### `environment.variables[]`

| Field | Type | Description |
|---|---|---|
| `name` | string | Variable name (e.g., `"PATH"`). |
| `value` | object | A `redacted_value` object (see [Redacted Values](#redacted-values)). |
| `source` | string | Origin of the variable (e.g., `"process"`). |

---

## `git`

Git repository state.

| Field | Type | Description |
|---|---|---|
| `repo_root` | string | Absolute path to the git repository root directory. |
| `commit` | string | Full 40-character SHA-1 commit hash. |
| `branch` | string | Active branch name (e.g., `"main"`). |
| `dirty` | bool | Whether there are uncommitted changes. |
| `remote_url` | object | A `redacted_value` object containing the remote URL. |
| `capture_state` | object | See [Capture State](#capture-state). |

---

## `errors`

Captured errors during the run.

| Field | Type | Description |
|---|---|---|
| `records` | list[object] | Error records. Empty if no errors occurred. |
| `capture_state` | object | See [Capture State](#capture-state). |

---

## `signals`

OS signals received during execution and the process exit code. This section is populated by the signal capture engine, which installs non-intrusive shim handlers that chain to any pre-existing handlers without disrupting the importing script's behavior.

| Field | Type | Description |
|---|---|---|
| `signals_received` | list[object] | Signals received during execution. Each entry has `signal` (int), `signal_name` (string), and `timestamp_utc` (float). |
| `exit_code` | int \| null | Process exit code at finalization. `0` for clean exit, `1` for unhandled exception, or the `SystemExit` code. Null if unknown. |
| `exit_exception` | string \| null | String representation of the exit-causing exception (e.g., `"SystemExit(42)"`), or null. |
| `capture_state` | object | See [Capture State](#capture-state). |

**Example:**
```json
{
  "signals_received": [
    {"signal": 2, "signal_name": "SIGINT", "timestamp_utc": 1780250544.068}
  ],
  "exit_code": 0,
  "exit_exception": null,
  "capture_state": {"status": "complete"}
}
```

Configurable via `[capture.signals].enabled` in `.pubrun.toml`. When disabled, the manifest contains `{"capture_state": {"status": "suppressed"}}`.

---

## `config`

Configuration provenance.

| Field | Type | Description |
|---|---|---|
| `resolved_config_path` | string | Filename of the resolved config snapshot (e.g., `"config.resolved.json"`). |
| `sources_path` | string \| null | Filename of config source tracking, if generated. |
| `source_files` | list[string] | Paths to config files that contributed to the resolved config. |
| `capture_state` | object | See [Capture State](#capture-state). |

---

## `hardware`

Physical hardware details.

| Field | Type | Description |
|---|---|---|
| `cpu` | object | CPU metadata (see below). |
| `memory_total_bytes` | int | Total system RAM in bytes. |
| `gpus` | list[object] | Detected GPU devices. |
| `capture_state` | object | See [Capture State](#capture-state). |

### `hardware.cpu`

| Field | Type | Description |
|---|---|---|
| `model` | string | CPU model string (e.g., `"Intel(R) Core(TM) i7-12700H"`). |
| `logical_cores` | int | Number of logical CPU cores. |
| `architecture` | string | CPU architecture (e.g., `"x86_64"`, `"aarch64"`). |

---

## `host`

Operating system and host identity.

| Field | Type | Description |
|---|---|---|
| `os_name` | string | Operating system name (e.g., `"Linux"`, `"Windows"`, `"Darwin"`). |
| `os_version` | string | Kernel or OS version string. |
| `os_release` | string | OS release details. |
| `hostname` | string | Machine hostname. |
| `capture_state` | object | See [Capture State](#capture-state). |

---

## `resources`

Runtime resource utilization, sampled by a background thread.

| Field | Type | Description |
|---|---|---|
| `peak_rss_bytes` | int | Peak resident set size (RAM) in bytes. |
| `end_rss_bytes` | int | RSS at finalization. |
| `peak_cpu_percent` | float | Peak CPU utilization percentage. |
| `capture_state` | object | See [Capture State](#capture-state). |

---

## `capture`

Run-level capture metadata.

| Field | Type | Description |
|---|---|---|
| `output_base_dir` | string | The base output directory (e.g., `"./runs"`). |
| `run_dir` | string | Full path to this run's directory. |
| `event_stream_enabled` | bool | Whether `events.jsonl` was active. |
| `console_capture_mode` | string | The effective console mode for this run. |
| `capture_state` | object | See [Capture State](#capture-state). |

---

## `pubrun_imports`

Import-mode provenance metadata. Records how pubrun was imported, which mode was selected, and whether any conflicts occurred.

| Field | Type | Description |
|---|---|---|
| `selected_mode` | string \| null | The effective import mode: `"auto"`, `"noauto"`, `"nopatch"`, or `"quiet"`. |
| `selected_behavior` | object | `{"auto_start": bool, "global_hooks": bool}` — the effective behavior flags. |
| `selected_by` | string \| null | Who selected the mode (e.g., `"pubrun"`, `"pubrun.noauto"`, `"pubrun.quiet"`). |
| `selected_source` | string \| null | Where the selection came from (e.g., `"default"`, `"env:PUBRUN_IMPORT_MODE"`, `"config:[imports].mode"`). |
| `selected_at_utc` | float \| null | Timestamp when the mode was selected. |
| `core_loaded` | bool | Whether `pubrun.core` was loaded (irreversible work started). |
| `conflict_policy` | string \| null | The active conflict policy: `"warn"`, `"error"`, or `"ignore"`. |
| `conflicts_detected` | int | Number of conflicting import-mode requests observed. |
| `requests` | list[object] | History of import-mode selection requests (see below). |

### `pubrun_imports.requests[]`

| Field | Type | Description |
|---|---|---|
| `timestamp_utc` | float | When this request was made. |
| `requested_mode` | string | The mode that was requested. |
| `selected_by` | string | Identifier for the requester. |
| `effective_behavior` | object | `{"auto_start": bool, "global_hooks": bool}` for the requested mode. |
| `selected` | bool | Whether this request won (first request always wins). |
| `conflict` | bool | Whether this request conflicted with the already-selected mode. |
| `core_loaded_at_request` | bool | Whether `pubrun.core` was already loaded when this request arrived. |
| `caller` | object \| null | Optional caller provenance: `{"filename": str, "line_number": int, "function": str}`. |

---

## `status`

Run outcome.

| Field | Type | Description |
|---|---|---|
| `outcome` | string | `"completed"`, `"failed"`, `"interrupted"`, `"ghost"`, or `"unknown"`. `"interrupted"` indicates the run received a termination signal (SIGINT, SIGTERM, or SIGHUP). |
| `capture_state` | object | See [Capture State](#capture-state). |

---

## Common Objects

### Capture State

Every manifest section includes a `capture_state` object indicating the status of that capture.

| Field | Type | Description |
|---|---|---|
| `status` | string | `"complete"`, `"partial"`, `"unavailable"`, `"suppressed"`, or `"failed"`. |

- `complete` — Data captured successfully.
- `partial` — Some data captured, but errors occurred.
- `unavailable` — The data source was not accessible (e.g., no git repo).
- `suppressed` — Capture was disabled by configuration or profile.
- `failed` — Capture attempted but failed entirely.

### Redacted Values

Sensitive values use a standard `redacted_value` object:

**Plain (not redacted):**
```json
{"representation": "plain", "value": "/home/user"}
```

**Redacted:**
```json
{"representation": "redacted"}
```

**Hashed (if configured):**
```json
{"representation": "hashed", "value": "sha256:a1b2c3d4..."}
```

---

## Lock File (`.pubrun.lock`)

While a run is active, a `.pubrun.lock` JSON file exists in the run directory. It is removed on normal finalization. If the process is killed without cleanup (SIGKILL, OOM, power loss), the lock file persists and is used by `pubrun status` to detect crashed/orphaned runs.

| Field | Type | Description |
|---|---|---|
| `pid` | int | Process ID of the running script. |
| `started_at_utc` | float | POSIX epoch timestamp of when the run started. Used with PID to detect PID recycling. |
| `script` | string | Script name (stem of `sys.argv[0]`). |
| `run_id` | string | 8-character hex run ID. |
| `hostname` | string | Machine hostname. |
| `git_commit` | string \| null | Git commit hash at start, or `null` if not in a repo. |
| `cwd` | string | Working directory of the process. |
| `argv` | list[string] | Command-line arguments (excluding `sys.argv[0]`). |

**Example:**
```json
{
  "pid": 12345,
  "started_at_utc": 1780250544.068,
  "script": "train",
  "run_id": "a1b2c3d4",
  "hostname": "gpu-node-07",
  "git_commit": "3df16cf",
  "cwd": "/home/user/project",
  "argv": ["--epochs", "100", "--lr", "0.001"]
}
```

---

## Meta Snapshot

The `pubrun meta` command generates a similar JSON structure, but with `manifest_type` set to `"pubrun-meta-snapshot"` instead of `"pubrun-manifest"`. Meta snapshots contain only environment-level data (hardware, python, packages, git, environment, host) and do not include run-specific fields (timing, invocation, status, etc.).

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md)
