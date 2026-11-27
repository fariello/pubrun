[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)

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

Phase profiling (`[capture.profiling].enabled`) adds no top-level key to `manifest.json`. Each profiled phase writes `profile-<phase>.prof` in the run directory and emits a `profile_saved` event with the file name in `events.jsonl`.

The JSON Schema also defines `artifacts`, `determinism`, and `extensions`, which `pubrun` does not write (`[capture.determinism]` is not yet implemented). Every top-level key that `pubrun` writes has its own section below.

---

## `run`

Run identity.

| Field | Type | Description |
|---|---|---|
| `run_id` | string | 8-character hex identifier (e.g., `"a1b2c3d4"`). |
| `library_version` | string \| null | Installed or active `pubrun` package version string (resolved from package metadata via `importlib.metadata`, or fallback `"1.0.0"` when metadata is unavailable). |
| `library_commit` | string \| null | 40- or 64-character hex commit Secure Hash Algorithm (SHA) identifying the `pubrun` library itself, or `null` when unknown, timed out, nested, or stale. |
| `capture_state` | object | See [Capture State](#capture-state). |

**`library_commit` resolution semantics:** `pubrun.__commit__` resolves lazily through Python Enhancement Proposal 562 (PEP 562) module `__getattr__` and caches the result under a lock on first access, so importing `pubrun.minimal` or `pubrun.noauto` spawns zero `git` processes. Resolution follows two strict paths:

- **Installed package (wheel or `site-packages`):** Never spawns `git`. Reads packaged `_build_meta.json` and accepts its commit only when the file parses as a JSON object with a valid 40- or 64-character hex SHA and a non-empty `version` matching `pubrun.__version__`. Falls back to a legacy packaged `COMMIT` file only when `_build_meta.json` is absent (never when `_build_meta.json` is malformed or version-mismatched).
- **Verified `pubrun` source checkout:** Applies only when `src/pubrun` resides inside a repository root containing both `.git` and a `pyproject.toml` declaring `[project].name = "pubrun"`. Runs one bounded `git -C <repo_root> rev-parse --show-toplevel HEAD` call with a `1.0`s timeout, stripped `GIT_*` override variables (`GIT_DIR`, `GIT_WORK_TREE`, `GIT_COMMON_DIR`, `GIT_INDEX_FILE`), and `SubprocessSpy` disabled if already loaded. Accepts `HEAD` only when the reported top-level directory matches the checkout root; never falls back to an on-disk `COMMIT` file.
- **Unknown cases:** Returns `null` when Git is missing, times out, fails, detects a nested-repository ownership mismatch, or when packaged metadata is missing, malformed, or stale.

---

## `timing`

Execution chronology and durations. The section uses two clocks for two different jobs:

- **Chronology (when something happened):** every `*_at_utc` field is a Portable Operating System Interface (POSIX) epoch float in Coordinated Universal Time (UTC) from `time.time()`, not an ISO 8601 string. These values place the run on the calendar and order it against other runs, but they can jump if the system clock is adjusted (for example by the Network Time Protocol (NTP) or a manual change).
- **Durations (how long something took):** every `*_seconds` field is computed from the difference of two in-memory monotonic clock readings (`time.perf_counter()`). A monotonic clock never goes backwards, so these durations stay nonnegative and correct across wall-clock jumps. The raw monotonic counter values are process-local and are **never** written to the manifest; only the derived durations are.

Durations are therefore **not** recomputed as `ended_at_utc - started_at_utc`. Subtracting the UTC fields gives an approximate wall-clock span that can disagree with the monotonic durations when the clock was adjusted during the run.

| Field | Type | Description |
|---|---|---|
| `started_at_utc` | float | When tracking began (`Run` construction: `start()`, or `import pubrun` in auto mode). Required. |
| `workload_started_at_utc` | float \| null | When synchronous startup capture finished and your code resumed. `null` if startup never completed (ghost mode). |
| `ended_at_utc` | float \| null | When the tracked workload ended: the moment finalization began (`stop()`, the end of `tracked_run()` / `audit_run()`, or the `atexit` safety net), before `pubrun` waits for background hardware capture. |
| `finalized_at_utc` | float \| null | When pre-manifest finalization finished, just before the final `manifest.json` is built and written. |
| `elapsed_seconds` | float \| null | The headline duration. For new manifests it equals `workload_seconds` (see `elapsed_basis`). `null` while the run is in progress or if timing is incomplete. |
| `workload_seconds` | float \| null | Monotonic duration of the observed tracked workload, from `workload_started_at_utc` to `ended_at_utc`. Excludes `pubrun`'s own startup and finalization work. |
| `startup_overhead_seconds` | float \| null | Monotonic duration of synchronous startup capture, from `started_at_utc` to `workload_started_at_utc`. |
| `finalization_overhead_seconds` | float \| null | Monotonic duration of pre-manifest finalization, from `ended_at_utc` to `finalized_at_utc`. Includes waiting for hardware capture, engine teardown, the package refresh, and writing `config.resolved.json`. Excludes the final atomic write of `manifest.json` itself, because the value must be known before that file is written. |
| `session_seconds` | float \| null | Monotonic duration from `started_at_utc` to `finalized_at_utc`. Equals `startup_overhead_seconds + workload_seconds + finalization_overhead_seconds` (within floating-point rounding). |
| `hardware_wait_seconds` | float \| null | Time finalization spent waiting (up to 2 s) for background hardware capture to finish. A sub-interval of `finalization_overhead_seconds`; do not add it to that value. |
| `background_hardware_seconds` | float \| null | How long the background hardware, host, and filesystem capture took. It runs concurrently with your code, so it **overlaps** `workload_seconds` and must not be added to it. `0.0` when `[capture.hardware].depth = "off"` (collected synchronously during startup instead). |
| `duration_clock` | string \| null | Which clock produced the durations: `"monotonic"` for new manifests, `"wall_clock"` for legacy semantics, `"wall_clock_estimated"` for a crashed-run closeout estimate. `null` when no duration is available (ghost mode). |
| `elapsed_basis` | string \| null | What `elapsed_seconds` measures: `"workload"` (new manifests), `"session"`, `"wall_clock_legacy"`, or `"crashed_estimate"`. `null` when no duration is available. |
| `interval_scope` | string \| null | Always `"tracked_interval"`: the durations cover only the interval `pubrun` tracked, never the whole process lifetime. |
| `cpu_time_seconds` | float \| null | Reserved by the schema for CPU time; not currently emitted by `pubrun`. |
| `capture_state` | object | `"complete"` once finalized timing is frozen, `"partial"` in the startup manifest, in ghost mode, and in crashed-run closeouts. See [Capture State](#capture-state). |

**Disjoint versus overlapping intervals.** `startup_overhead_seconds`, `workload_seconds`, and `finalization_overhead_seconds` are disjoint and consecutive, so they add up to `session_seconds`. `background_hardware_seconds` overlaps the workload and `hardware_wait_seconds` lies inside finalization overhead; summing either with the three disjoint intervals double-counts time.

```text
started_at_utc   workload_started_at_utc            ended_at_utc   finalized_at_utc
     |----------------------|----------------------------|----------------|-> manifest.json write
       startup_overhead           workload_seconds          finalization
                                                              overhead
     |<------------------------- session_seconds ------------------------>|
                         |<- background_hardware ->|        |<- hw wait ->|
                            (overlaps workload)              (inside finalization)
```

**Tracked interval, not process lifetime.** Tracking starts when the `Run` is created. If `pubrun` is imported halfway through a script (or `start()` is called late), everything before that point is outside the measured interval. Likewise, anything the interpreter does after finalization (later `atexit` handlers, interpreter teardown) is not measured.

**Legacy and estimated timing.** Manifests written before monotonic timing (schema `1.0` without `duration_clock` or `elapsed_basis`) remain valid and readable. Consumers (`pubrun status`, `inspect`, `report`, `diff`, and the TUI) classify a manifest that has `elapsed_seconds` but neither field as legacy wall-clock timing (`duration_clock = "wall_clock"`, `elapsed_basis = "wall_clock_legacy"`) and label it as such, because its `elapsed_seconds` was `ended_at_utc - started_at_utc` and includes `pubrun`'s own capture overhead. When `pubrun status` closes out a crashed run (its process died before finalization), it sets `ended_at_utc` from the lock file's modification time, estimates `elapsed_seconds` by wall-clock subtraction (clamped to be nonnegative), and records `duration_clock = "wall_clock_estimated"`, `elapsed_basis = "crashed_estimate"`, and `capture_state.status = "partial"`.

> [!NOTE]
> **Why floats?** POSIX epoch floats provide sub-second precision, timezone-agnostic storage, and deterministic serialization. They are used for chronology only; durations come from the monotonic clock. See [Architecture](architecture.md) for full rationale.

---

## `invocation`

What was run and how.

| Field | Type | Description |
|---|---|---|
| `argv` | list[string] | `sys.argv` at invocation time. Sensitive values may be redacted. |
| `command_line` | string | Joined `argv` string. |
| `rerun_command` | string | Shell command to reproduce the run (e.g., `cd /path && python script.py`). |
| `entrypoint_type` | string | `"script"`, `"module"`, `"interactive"`, or `"unknown"`. |
| `script` | object | Script file metadata (see below). |
| `working_directory` | object | `{"path": "/abs/path", "real_path": "/resolved/path"}`. |
| `inputs` | list[object] | Detected input files from `sys.argv` (path, size, mtime, optional md5). An argument whose value is redacted in `argv` is not recorded. |
| `capture_state` | object | See [Capture State](#capture-state). |

### `invocation.script`

When `sys.argv[0]` is not an existing file (for example `python -c`), `script` is `{}`. Otherwise:

| Field | Type | Description |
|---|---|---|
| `path` | string | Entry-point script path from `sys.argv[0]` as given (may be relative). |
| `real_path` | string | Resolved absolute path to the entry-point script. |
| `basename` | string | Filename only. |
| `size` | int | File size in bytes. |
| `mtime` | float | Last modification time (POSIX epoch float). |
| `ctime` | float | Metadata change or creation time (POSIX epoch float). |
| `sha256` | string | SHA-256 hash of the file contents, computed only for scripts up to 1,048,576 bytes. Omitted for larger scripts. |
| `sha256_skipped` | string | Present only when the script exceeds 1,048,576 bytes, set to `"file exceeds 1MB"` instead of `sha256`. |

---

## `console`

Console capture metadata.

| Field | Type | Description |
|---|---|---|
| `capture_mode` | string | `"off"`, `"basic"`, `"standard"`, or `"deep"`. |
| `stdout` | object | `{"captured": bool, "path": string \| null, "lines_captured": int \| null}`. |
| `stderr` | object | `{"captured": bool, "path": string \| null, "lines_captured": int \| null}`. |
| `combined` | object | `{"captured": bool, "path": string \| null, "lines_captured": int \| null}`. Always `{"captured": false, "path": null, "lines_captured": null}`, because `pubrun` writes only the split logs. |
| `capture_state` | object | See [Capture State](#capture-state). |

In the startup manifest (written before the run finishes) the `console` section is already
self-describing: it carries the resolved `capture_mode` plus `capture_state.status = "pending"`. When
the run finishes, `capture_state.status` is updated to `"complete"`, `"partial"` (with detail
`"console log write failed during execution"`), or `"failed"` (when the interceptor could not start).
It is never emitted as an empty object, so a consumer reading a run before it finishes can tell "not
finalized yet" (`pending`) from a genuine `"off"` result.

---

## `subprocesses`

Array of subprocess records. Each element:

| Field | Type | Description |
|---|---|---|
| `argv` | list[string] | Command and arguments. Sensitive values may be redacted. |
| `started_at_utc` | float | Start time (POSIX epoch float). |
| `ended_at_utc` | float \| null | End time, or `null` when `pubrun` did not observe the process end by finalization. |
| `elapsed_seconds` | float \| null | Optional. Nonnegative monotonic duration (`time.perf_counter()`) from launch until `pubrun` observed the process finish (`wait()`, `communicate()`, a completed `poll()`, `Popen.__del__`, `os.system` returning, or pipe close for `pubrun.popen()`), or until the launch attempt failed. For a child whose exit `pubrun` first observed at the next `Popen` launch or at finalization, the duration ends at that observation. For a child still unobserved at finalization, the duration ends at finalization. Not derived from the UTC fields. |
| `duration_clock` | string \| null | Optional. `"monotonic"` when `elapsed_seconds` is present. Absent on records written before monotonic subprocess timing. |
| `pid` | int \| null | Optional. Written by the explicit wrappers only: the process ID for `pubrun.subprocess.Popen`, `null` for `pubrun.subprocess.run()`, `pubrun.popen()`, and failed launches. |
| `error` | string \| null | Optional. Bounded, redacted error detail when an explicit wrapper's launch failed. |
| `cwd` | string \| null | Working directory passed to the subprocess. The global spy records the `cwd=` argument passed to `subprocess.Popen` (else `null`) and `null` for `os.system`; the explicit `pubrun.subprocess` and `pubrun.popen` wrappers omit this key. |
| `exit_code` | int \| null | Exit code, or `null` when `pubrun` did not observe the exit. |
| `capture_state` | object | `"complete"` for exit code 0, `"failed"` for a nonzero exit code or a failed launch (with a redacted `detail`), and `"partial"` with a `detail` while the process runs, when `pubrun` did not observe its exit by finalization, or when its exit status is unavailable. See [Capture State](#capture-state). |

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
| `uid` | int \| null | User ID (Unix only; `null` on Windows). |
| `gid` | int \| null | Group ID (Unix only; `null` on Windows). |

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
| `virtual_env` | string \| null | Literal string `"venv"` when Python runs in a virtual environment (`sys.prefix` differs from `sys.base_prefix`, or `sys.real_prefix` exists), else `null`; it never holds a path. Use `prefix` for the path, and `environment_kind` and `in_venv` for environment classification. |
| `sys_path` | list[string] | The Python module search path. |
| `environment_kind` | string | `"venv"`, `"conda"`, `"virtualenv"`, `"system"`, or `"frozen"` - a non-identifying classification (no path). |
| `in_venv` | bool | Whether `sys.prefix != sys.base_prefix` (PEP 405). |
| `sys_path_len` | int | `len(sys.path)` - import time scales with it. |
| `pyenv` | bool | Whether the interpreter appears pyenv-managed (orthogonal modifier). |
| `capture_state` | object | See [Capture State](#capture-state). |

> `environment_kind`, `in_venv`, `sys_path_len`, and `pyenv` are deliberately non-identifying
> (they expose no path, username, or home dir) so they **survive the benchmark share-redaction**
> that masks `executable`/`prefix`/`virtual_env`/`sys_path`.

---

## `packages`

Tracked Python dependencies. Import-based modes (`imported-only`, `imported-transitive`) take a startup snapshot and, at finalization, refresh it and merge the two, so the final manifest contains distributions imported at startup, during the run, or both. When `[capture.packages].mode = "off"`, the section is exactly `{"capture_state": {"status": "suppressed"}}` and `mode` is omitted.

| Field | Type | Description |
|---|---|---|
| `mode` | string \| null | `"imported-only"`, `"imported-transitive"`, `"top-level-installed"`, or `"full-environment"`. Omitted when capture is off. |
| `snapshot_stage` | string \| null | `"startup"` for the startup snapshot (what a crashed run keeps), `"final"` for the merged startup-plus-finalization snapshot, or `"single"` for a standalone capture outside a run lifecycle. |
| `records` | list[object] | Package records (see below). |
| `unresolved` | list[object] | Modules or dependencies that could not be mapped to exactly one installed distribution (see below). Default `[]`. |
| `local_modules` | list[string] | Sorted top-level names of loaded modules that live outside `site-packages` (for example the project's own modules). Default `[]`. |
| `coverage_notes` | list[string] | Factual notes on what this snapshot could not observe. For import-based modes at finalization this states the no-import-hook limitation described below. Default `[]`. |
| `capture_state` | object | See [Capture State](#capture-state). |

`capture_state.status` is `"partial"` when `unresolved` is non-empty, when a distribution's version changed between the startup and finalization snapshots (a warning names it), or when the startup snapshot, the finalization refresh, or the transitive closure reported an error; the error text is kept in `capture_state.detail`. If the finalization refresh itself raises, the startup snapshot's records are kept and the status is `"partial"`, or `"failed"` when the startup snapshot had also failed.

Limitation: `pubrun` does not install a global import hook. A module imported after startup and removed from `sys.modules` before finalization is not observed, so its distribution is absent from `records`.

### `packages.records[]`

| Field | Type | Description |
|---|---|---|
| `name` | string | Package name. |
| `version` | string \| null | Installed version, or `null` when the distribution metadata has no version. |
| `location` | string \| null | Install location path, if available. |
| `editable` | bool \| null | Whether the package is installed in editable (development) mode. |
| `source` | string \| null | How the record was discovered (e.g. `"imported"`, `"transitive"`). |
| `required_by` | list[string] \| null | In `imported-transitive` mode, the imported packages that require this (transitive) dependency. Absent/`null` for non-transitive records. |
| `import_names` | list[string] \| null | Sorted import names observed in `sys.modules` that map to this distribution (for example `yaml` for `PyYAML`). `null` for records that were not discovered through imports. |
| `observed_at` | string \| null | For imported records, when the import was seen: `"startup"`, `"final"`, or `"startup_and_final"`. `null` for records not discovered through imports. |

### `packages.unresolved[]`

| Field | Type | Description |
|---|---|---|
| `module` | string | Import name, dependency name, or distribution hint that could not be resolved. |
| `reason` | string | One of `"ambiguous"` (several installed distributions provide the module), `"unmapped_site_package"` (a module under `site-packages` matches no distribution), `"missing_metadata"` (distribution metadata lacks a valid `Name`), `"metadata_error"` (reading the metadata raised an error), `"missing_transitive_dependency"` (a declared dependency is not installed), or `"unparseable_marker"` (a dependency's PEP 508 marker could not be evaluated). |
| `candidates` | list[string] | Candidate distribution names, when known (for `"ambiguous"`). Default `[]`. |
| `observed_at` | string \| null | `"startup"`, `"final"`, `"startup_and_final"`, or `null`. |
| `detail` | string \| null | Short human-readable explanation. |

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
| `repo_root` | string \| null | Absolute path to the git repository root directory, or `null` when unavailable. |
| `commit` | string \| null | Full 40-character SHA-1 commit hash, or `null` when unavailable. |
| `branch` | string \| null | Active branch name (for example `"main"`), or `null` when unavailable or detached. |
| `dirty` | bool \| null | Whether there are uncommitted changes, or `null` when unavailable or skipped. |
| `remote_url` | object | A `redacted_value` object containing the remote URL. |
| `capture_state` | object | See [Capture State](#capture-state). Records `"timeout"` when `[capture.git].timeout` or `[capture.git].total_timeout` expires before `repo_root` is determined, or `"partial"` when a subsequent query (`HEAD`, branch, `status --porcelain`, or `remote get-url origin`) times out or is skipped after budget exhaustion. |

---

## `errors`

Captured errors during the run, including isolated capture and cleanup failures.

| Field | Type | Description |
|---|---|---|
| `records` | list[object] | Structured error records (see `errors.records[]` below). Empty if no errors occurred. Capped at `MAX_CAPTURE_ERRORS = 50` entries per run. |
| `capture_state` | object | See [Capture State](#capture-state). Reports `{"status": "complete"}` when all errors fit within the cap, or `{"status": "partial", "detail": "<N> additional capture error(s) omitted"}` when more than 50 capture errors occurred. |

### `errors.records[]`

Each entry conforms to `$defs.error_record` in `schemas/manifest.schema.json`:

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | string | Yes | One of `"exception"`, `"warning"`, `"capture-error"`, `"signal"`, or `"other"`. Isolated engine and cleanup failures record `"capture-error"`. |
| `type` | string \| null | No | Exception class name (for example `"RuntimeError"`), or `null`. |
| `message` | string \| null | No | Single-line, redacted, length-bounded detail string (at most 240 characters, formatted by `format_safe_error_detail()`). Sensitive values (Uniform Resource Identifier (URI) credentials, `Bearer` tokens, `sk-...` keys, `key=value`, `key: value`, `--flag=value`, and `--flag value` pairs matching the configured secret pattern) are replaced with `[REDACTED]`. Falls back to default secret patterns and then to the exception type name if redaction fails. |
| `traceback` | string \| null | No | Always `null` for `"capture-error"` records (no traceback dumps are written into manifests). |
| `section` | string \| null | No | Optional manifest section or subsystem name where the failure occurred (for example `"git"`, `"packages"`, `"console"`, `"subprocesses"`, `"resources"`, `"signals"`, `"events"`, `"hardware"`, `"host"`, `"filesystem"`, or `"writer"`). |
| `stage` | string \| null | No | Optional lifecycle stage where the failure occurred (`"bootstrap"`, `"runtime"`, `"finalization"`, `"rollback"`, or `"writer"`). |

When an individual capture engine fails, its own manifest section records `capture_state: {"status": "failed", "detail": "<bounded redacted detail>"}` (distinct from `"suppressed"`, which indicates the section was disabled by configuration).

---

## `signals`

OS signals received during execution and the process exit code. This section is populated by the signal capture engine, which installs non-intrusive shim handlers that chain to any pre-existing handlers without disrupting the importing script's behavior.

| Field | Type | Description |
|---|---|---|
| `signals_received` | list[object] | Signals received during execution, capped at 1,000 entries per run. Each entry has `signal` (int), `signal_name` (string), and `timestamp_utc` (float). |
| `signals_truncated` | int \| absent | Number of additional signals omitted after the 1,000-entry cap was reached. Present only when greater than `0`; `capture_state` also becomes `partial` when not already `failed` or unavailable. |
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
| `resolved_config_path` | string | Filename of the resolved config snapshot (e.g., `"config.resolved.json"`). Written atomically at startup and rewritten only when effective configuration changes, `run_dir` migrates via mid-run overrides, or the file is missing (under `[core].artifact_durability = "finalize"`, an unchanged startup snapshot is synchronized in place via `os.fsync()` at finalization without rewriting). |
| `sources_path` | string \| null | Filename of config source tracking, if generated. |
| `source_files` | list[object] | Config files that contributed to the resolved config, each `{"path": string, "hash"?: object}`. **Currently always empty** (`[]`): pubrun does not yet record per-file config provenance in the manifest, so `source_files` and `sources_path` are reserved and unpopulated today. |
| `notices` | list[object] | Non-disruptive config notices recorded at run time (never raised into the host; surfaced by `pubrun status`/`inspect`/`show`). Each: `{"code", "setting", "value", "message"}`. Currently emitted for a deprecated, inert `core.profile` set to a non-default value. Empty list when none. |
| `capture_state` | object | See [Capture State](#capture-state). |

---

## `hardware`

Physical hardware details.

| Field | Type | Description |
|---|---|---|
| `cpu` | object | CPU metadata (see below). |
| `memory_total_bytes` | int | Total system RAM in bytes. |
| `gpus` | list[object] | Detected GPU devices. |
| `capture_state` | object | See [Capture State](#capture-state). Records `"timeout"` when `[capture.hardware].timeout` or `[capture.hardware].total_timeout` expires and zero probed fields succeeded, or `"partial"` when at least one probed field succeeded before timeout or budget exhaustion. |

### `hardware.cpu`

| Field | Type | Description |
|---|---|---|
| `model` | string | CPU model string (e.g., `"Intel(R) Core(TM) i7-12700H"`). |
| `logical_cores` | int | Number of logical CPU cores. |
| `architecture` | string | CPU architecture (e.g., `"x86_64"`, `"aarch64"`). |

### `hardware.gpus[]`

| Field | Type | Description |
|---|---|---|
| `vendor` | string | `"NVIDIA"` from `nvidia-smi`, `"Generic"` from Windows WMI, or `"Apple / Generic"` from macOS `system_profiler`. |
| `model` | string \| null | GPU model name. |
| `memory_total_bytes` | int \| null | Dedicated GPU memory in bytes; `null` on macOS or when unavailable. |
| `driver_version` | string \| null | GPU driver version string; absent on macOS. |
| `clock_speed_mhz` | int | Present for `nvidia-smi` only when `[capture.hardware].capture_gpu_clock_speed = true`. |

`schemas/manifest.schema.json` (`$defs.gpu_record`) also defines `floating_point_precision`, which `pubrun` never writes.

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

## `filesystem`

Filesystem type of run-relevant paths, so a later `pubrun inspect` can flag when a run
lived on a slow **network filesystem** (NFS/Lustre/GPFS/CIFS) - a common cause of inflated
I/O on HPC clusters. Classified by parsing `/proc/self/mountinfo` (preferred) or
`/proc/mounts` (Linux), the `mount` table (macOS), or `GetVolumeInformationW` (Windows);
**never** by `statvfs`/`df`/`stat` on the target, so it cannot hang on a wedged network
mount. Each entry keyed by path label (`output_dir`, `run_dir`, `tmpdir`):

| Field | Type | Description |
|---|---|---|
| `<label>.path` | string | The path that was classified. |
| `<label>.mount_point` | string | The mount point backing the path (longest-prefix match). |
| `<label>.fstype` | string | Filesystem type (`ext4`, `xfs`, `tmpfs`, `nfs4`, `lustre`, …). |
| `<label>.is_network` | bool | Whether the filesystem is a network/remote filesystem. |
| `capture_state` | object | See [Capture State](#capture-state). `suppressed`/`failed` when unavailable. |

> **Live capacity/health metrics (`<label>.live`) do NOT appear in the normal run manifest.**
> The blocking `statvfs` probe that produces free-space/inode/read-only data and the
> hung/slow status is **diagnostic-only** - it runs solely for `pubrun bench` and
> `pubrun self-check`, never during a tracked run - so those fields surface only in the
> benchmark result JSON and `self-check` output, keeping the always-on capture path
> non-blocking.

---

## `resources`

Runtime resource utilization, sampled by a background thread.

| Field | Type | Description |
|---|---|---|
| `scope` | string | `"process"` or `"tree"`. Indicates measurement scope. |
| `peak_rss_bytes` | int \| null | Peak resident set size (RAM) of the main process in bytes, or `null` when no positive sample was taken. |
| `end_rss_bytes` | int \| null | RSS of the main process at finalization, or `null` when no positive sample was taken. |
| `peak_cpu_percent` | float \| null | Peak CPU utilization percentage, or `null` when no positive sample was taken. |
| `peak_tree_rss_bytes` | int \| null | Peak RSS summed across the process tree (only when `scope = "tree"`). |
| `end_tree_rss_bytes` | int \| null | Tree RSS at finalization (only when `scope = "tree"`). |
| `peak_tree_cpu_percent` | float \| null | Peak CPU% summed across the process tree (only when `scope = "tree"`; Linux-only). Computed from summed CPU-time deltas over the sample interval - **"% of one core"**, so it may exceed 100% on multiple cores (not clamped). `null` where unmeasured. Per-sample `tree_cpu_percent` is also emitted to `events.jsonl` for avg/min/max. |
| `system_memory` | object \| absent | System-wide memory (Linux), present when `[capture.resources].system_metrics = true`. `{"start": {...}, "last": {...}, "min_available": {...}}`, each with `total_bytes`/`available_bytes`/`free_bytes`/`cached_bytes`. |
| `load_average` | object \| absent | `{"start": {...}, "last": {...}, "max_1min": float}`, each of start/last being `{"1min","5min","15min"}`. |
| `system_iowait_pct` | object \| absent | `{"last": float, "max": float}`. **NODE-WIDE, indicative only** - `/proc/stat` iowait is a system-wide counter, not run-scoped, and is unreliable on shared/multi-core nodes. A hint that the *node* was I/O-bound, not a per-run measurement. |
| `io_counters` | object \| absent | Per-**process** cumulative I/O byte counters from Linux `/proc/self/io`, present when `system_metrics` is on. `{"start": {...}, "last": {...}, "delta": {...}}` with `rchar`/`wchar` (bytes through read()/write(), incl. cache) and `read_bytes`/`write_bytes` (bytes to/from storage). The `delta` is this run's I/O volume. Linux-only; omitted elsewhere. |
| `capture_state` | object | See [Capture State](#capture-state). |

The `system_memory`/`load_average`/`system_iowait_pct` sections are omitted on platforms
where they cannot be read cheaply (e.g. non-Linux for memory/iowait) rather than reporting
misleading nulls.

---

## `data_files`

Provenance-tracked files: files opened through `pubrun.open()` and files recorded with
`pubrun.register_file()`, `pubrun.register_input()`, or `pubrun.register_output()`. Files
written into the run directory with `pubrun.artifact()` are part of the run itself and are
not listed here.

| Field | Type | Description |
|---|---|---|
| `inputs` | list[object] | Files read (`role = "input"`). Each entry is a file provenance record (below). |
| `outputs` | list[object] | Files written (`role = "output"`). |
| `mixed` | list[object] | Files both read and written (`role = "input_output"`, for example a `"r+"` open or `register_file(..., role="input_output")`). |
| `records_truncated` | int \| absent | Number of additional file provenance records omitted after `[capture.file_io].max_tracked_files` was reached. Present only when greater than `0`. |
| `hashing_summary` | object \| null | Run-wide hashing budget and outcome counters: `max_hash_bytes`, `max_total_hash_bytes`, `max_total_hash_seconds`, `hash_algorithm`, `total_bytes_hashed`, `total_hash_seconds`, `files_hashed`, `files_skipped_over_budget`, `files_changed`, `files_failed`. Present once the run has used its hashing budget (for example a file handled at `hash` level); otherwise absent. |

### File provenance record (`$defs.file_provenance_record`)

Which fields appear depends on the effective `[capture.file_io].level`: `name` records the
path as given; `stat` and above add the absolute path and `fstat`/`stat` metadata
(`size_bytes`, `mtime`, `ctime`, `mtime_ns`, `inode`, `device`); `realpath` and above add
`realpath`, `is_symlink`, and `symlink_target`; `hash` adds a content digest. `sha256` is
present at every level but is `null` unless a SHA-256 digest was observed.

| Field | Type | Description |
|---|---|---|
| `path` | string | Absolute path (the path as given at `name` level). Required. |
| `role` | string | `input` \| `output` \| `input_output`. |
| `label` | string \| null | Caller-supplied logical name. |
| `mode` | string \| null | The `open()` mode string (`pubrun.open()` records only). |
| `open_disposition` | string \| null | `read` \| `write` \| `append` \| `exclusive_create` \| `read_write`, derived from the open mode. |
| `registration_source` | string \| null | `pubrun.open` \| `register_file` \| `register_input` \| `register_output`. |
| `entry_type` | string \| null | `file` \| `directory` \| `symlink` \| `special` \| `missing` \| `unsupported_remote_uri`. |
| `hash_status` | string \| null | `completed` (digest observed by pubrun) \| `disabled` (level below `hash`) \| `over_budget` \| `unavailable` (missing file, directory, remote URI) \| `failed` (read error or `caller_digest_mismatch`) \| `file_changed` (changed while observed) \| `asserted` (caller-supplied digest, not read) \| `pending` (output registered before creation). |
| `hash_status_detail` | string \| null | Human-readable reason for a non-`completed` status. |
| `hash_algorithm` | string \| null | Algorithm of `digest`, or `null` when there is none. |
| `digest` | object \| null | `{algorithm, value}` of the digest pubrun observed, or of an asserted digest when `hash_status = "asserted"`. |
| `caller_digest` | object \| null | `{algorithm, value, verified}` as supplied by the caller. `verified` is `true`/`false` after `verify_digest=True`, else `null`. |
| `evidence_source` | string \| null | `observed` (pubrun looked at the file) \| `asserted` (taken from the caller) \| `none`. |
| `evidence_strength` | string \| null | `verified_content` \| `asserted_content` \| `metadata_only` \| `path_only` \| `changed_unverified` \| `unavailable`. Read this before trusting a digest. |
| `observation_time` | string \| null | When the evidence was gathered: `during_stream` \| `at_close` \| `at_registration` \| `at_finalization` \| `caller_supplied` \| `not_observed`. |
| `change_detected` | bool | `true` when the file's identity (size, mtime, and inode/device where reported) changed while pubrun observed it. |
| `change_details` | object \| null | Before/after identity fields that differed. |
| `access_observations` | object \| null | `pubrun.open()` only: `bytes_read`, `bytes_written`, `read_calls`, `write_calls`, `seek_used`, `truncate_used`, `eof_reached`, `raw_or_buffer_accessed`. |
| `hash_stats` | object \| null | `bytes_hashed`, `extra_read_bytes` (bytes pubrun read beyond what the caller read; `0` for a streamed digest), `hash_duration_seconds`. |
| `registration_count` | int | Number of registrations merged into this record (>= 1). |
| `registered_before_creation` | bool | `true` when an output was registered before it existed. |
| `metadata` | object \| null | Caller-supplied JSON metadata from `register_file(..., metadata=...)`. |
| `accessed_at_utc` / `modified_at_utc` | number \| null | POSIX time of the read or write observation. |
| `registered_at_utc` / `last_observed_at_utc` | number \| null | POSIX time of first registration and of the latest observation. |

**Race limits.** Identity checks compare `fstat`/`stat` snapshots, so they narrow but
cannot close every race: a writer that restores size and mtime exactly, coarse filesystem
timestamps, or a change after pubrun's last observation goes undetected.
`verified_content` means "these were the bytes when pubrun observed them", as stated by
`observation_time`; it is not a guarantee about the file at any later time.

> The default `[capture.file_io].level` is `stat` (metadata, no hashing). See
> [Configuration](configuration.md) → `[capture.file_io]` and the API docs for
> `pubrun.open()` and `pubrun.register_file()`.

---

## `capture`

Run-level capture metadata.

| Field | Type | Description |
|---|---|---|
| `output_base_dir` | string | The base output directory (e.g., `"./runs"`). |
| `run_dir` | string | Full path to this run's directory. |
| `event_stream_enabled` | bool | Whether `events.jsonl` was active. |
| `console_capture_mode` | string | The configured `[console].capture_mode` (default `"off"`), read before import-mode forcing (`full`, `noconsole`) and the Jupyter and non-TTY guards. The mode actually used is `console.capture_mode`. |
| `subprocesses_enabled` | bool | Whether the subprocess spy was installed for this run. Lets tooling distinguish "subprocess tracking was OFF" from "on but no subprocesses ran" (an empty `subprocesses` list is otherwise ambiguous). |
| `file_provenance_available` | bool | Whether file-open provenance was available (a run was active and `pubrun.open` was importable). `data_files` is filled only by `pubrun.open()`, `pubrun.register_file()`, `pubrun.register_input()`, and `pubrun.register_output()`; an empty `data_files` section means none of those APIs were used, not that provenance was unavailable. |
| `capture_state` | object | See [Capture State](#capture-state). Reports `{"status": "complete"}` when every enabled section succeeded, or `{"status": "partial", "detail": "capture degraded in: <sorted failed sections>"}` whenever any section failed (covering both escaping exceptions recorded in `errors.records` and self-caught engine returns whose own `capture_state.status` is `"failed"`). |

---

## `pubrun_imports`

Import-mode provenance metadata. Records how pubrun was imported, which mode was selected, and whether any conflicts occurred.

| Field | Type | Description |
|---|---|---|
| `selected_mode` | string \| null | The effective import mode: `"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, or `"full"`. |
| `selected_behavior` | object \| null | Effective behavior flags: `{"auto_start": bool, "global_hooks": bool, "patch_subprocesses": bool, "patch_console": bool, "signal_hooks": bool}`. Includes `"force_console": true` only for `"full"`. |
| `selected_by` | string \| null | Who selected the mode (for example `"pubrun"`, `"pubrun.<mode>"` such as `"pubrun.noauto"` or `"pubrun.minimal"`, or `"cli:pubrun run --mode"`). |
| `selected_source` | string \| null | Where the selection came from: `"cli:pubrun run --mode"`, `"default"`, `"explicit"` (a `pubrun.<mode>` import), `"env:PUBRUN_IMPORT_MODE"`, `"env:PUBRUN_AUTO_START"`, `"config:[imports].mode"`, or `"config:[core].auto_start"`. |
| `selected_at_utc` | float \| null | Timestamp when the mode was selected. |
| `core_loaded` | bool | Whether `pubrun.core` was loaded (irreversible work started). |
| `conflict_policy` | string \| null | The active conflict policy: `null` until a conflicting import-mode request occurs, then `"warn"`, `"error"`, or `"ignore"`. |
| `conflicts_detected` | int | Number of conflicting import-mode requests observed. |
| `requests` | list[object] | History of import-mode selection requests (at most 50 requests are recorded; see below). |

### `pubrun_imports.requests[]`

| Field | Type | Description |
|---|---|---|
| `timestamp_utc` | float | When this request was made. |
| `requested_mode` | string | The mode that was requested. |
| `selected_by` | string | Identifier for the requester. |
| `effective_behavior` | object | Behavior flags for the requested mode: `{"auto_start": bool, "global_hooks": bool, "patch_subprocesses": bool, "patch_console": bool, "signal_hooks": bool}`. Includes `"force_console": true` only for `"full"`. |
| `selected` | bool | Whether this request won (first request always wins). |
| `conflict` | bool | Whether this request conflicted with the already-selected mode. |
| `core_loaded_at_request` | bool | Whether `pubrun.core` was already loaded when this request arrived. |
| `caller` | object \| null | Optional caller provenance: `{"filename": str, "line_number": int, "function": str}`. |

---

## `status`

Run outcome.

| Field | Type | Description |
|---|---|---|
| `outcome` | string | Values written by `pubrun`: `"running"` (startup and in-progress manifests), `"completed"`, `"failed"`, `"interrupted"`, `"crashed"`, and `"ghost"`. `pubrun status` and `pubrun show` write `"crashed"` into a run directory when they close out a confirmed dead local lock file. `"partial"` and `"unknown"` are in the schema enum, though `pubrun` does not write them directly; readers display `"unknown"` when the field is missing. See [`pubrun.stop()`](api.md#pubrunstop) for the outcome classification rules. |
| `capture_state` | object | See [Capture State](#capture-state). |

> [!NOTE]
> `pubrun status` displays a `broken pipe` status (yellow) for runs that completed but received SIGPIPE. This is a **display-level classification only** - the manifest outcome remains `"completed"` and the exit code is unchanged. Check the `signals.signals_received` array for the raw SIGPIPE record.

---

## Common Objects

### Capture State

Every manifest section includes a `capture_state` object indicating the status of that capture.

| Field | Type | Description |
|---|---|---|
| `status` | string | `"complete"`, `"partial"`, `"unavailable"`, `"suppressed"`, `"failed"`, `"pending"`, or `"timeout"`. |
| `detail` | string | Optional single-line diagnostic context. For `"failed"` sections and capture errors, `detail` is bounded to at most 240 characters and redacted via `format_safe_error_detail()`. |
| `warnings` | list[string] | Optional list of non-fatal warning strings associated with the section. |

- `complete`: Data captured successfully.
- `partial`: Some data captured, but errors occurred.
- `unavailable`: The data source was not accessible (e.g., no git repo).
- `suppressed`: Capture was disabled by configuration (a `capture.*` `depth`/`mode` set to `off`).
- `failed`: Capture attempted but failed entirely.
- `pending`: Transient: the section is captured asynchronously by the background hardware thread and had not completed when the manifest was written. Seen in the **startup manifest** (written at `start()`) and therefore in a run that **crashed before finalizing** - the `hardware`/`host`/`filesystem` sections are `pending` until the thread fills them in. A normally-finalized manifest never leaves a section `pending`.
- `timeout`: The capture's external tool did not respond within its configured timeout or total budget (e.g. `git` on a slow/large repository, or a hung GPU query). Distinct from `unavailable` so a slow repo is never mislabeled as "not a git repository". See `[capture.git].timeout`, `[capture.git].total_timeout`, `[capture.hardware].timeout`, and `[capture.hardware].total_timeout`.

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

**Hashed (when `[redaction].representation = "hashed"`):**
```json
{"representation": "hashed", "hash_algorithm": "sha256", "hash_value": "<64 hex characters>"}
```

**Unavailable (when no value exists, for example `git.remote_url` with no remote):**
```json
{"representation": "unavailable"}
```

`schemas/manifest.schema.json` (`$defs.redacted_value`) also allows `"suppressed"` and accepts both the flat runtime hashed representation (`hash_algorithm` and `hash_value`) and the nested `hash: {"algorithm": "...", "value": "..."}` object for interoperability.

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
| `argv` | list[string] | Command-line arguments (excluding `sys.argv[0]`). Sensitive values are redacted. |
| `sys_argv` | list[string] | Full `sys.argv` list (including `sys.argv[0]`). Sensitive values are redacted. Used when reconstructing invocation commands from a lock file (for example during crashed-run closeout or `pubrun rerun`). |
| `import_mode` | string \| null | The active import mode (`"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, or `"full"`). |
| `import_selected_by` | string \| null | Who selected the mode (e.g., `"pubrun"`, `"pubrun.noauto"`). |

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
  "argv": ["--epochs", "100", "--lr", "0.001"],
  "sys_argv": ["train.py", "--epochs", "100", "--lr", "0.001"],
  "import_mode": "auto",
  "import_selected_by": "pubrun"
}
```

---

## Meta Snapshot

The `pubrun meta` command generates a similar JSON structure, with `manifest_type` set to `"pubrun-meta-snapshot"` instead of `"pubrun-manifest"`. A snapshot holds `manifest_type`, `timing.started_at_utc` (used for the parent-age check during hydration), `hardware`, `python`, `packages`, `git`, `environment`, and `host`, and omits `schema_version`, `process`, `invocation`, `status`, `console`, and `resources`.

### Inheritance from a parent snapshot (`meta_ref`)

A child manifest's top-level `meta_ref` names a parent snapshot, resolved relative to the
child's run directory. Report and analysis callers (`pubrun show` and its hidden alias `report`,
`pubrun inspect`, `pubrun methods`, `pubrun rerun`, `pubrun diff`, `pubrun res`, `pubrun cpu`,
`pubrun mem`, the TUI, and `pubrun.diff()`) apply the parent at **report time**:

- **No change on disk:** hydration builds an in-memory copy. `manifest.json` is never
  rewritten, so the recorded file always shows what the child itself captured.
- **What is filled:** the hydrable sections `hardware`, `host`, `process`, `python`, `packages`,
  `environment`, and `git`, and only when the child section is missing or its capture status is
  `suppressed`, `off`, `unavailable`, `unknown`, or `partial`. A section the child captured
  directly is never replaced.
- **`is_hydrated`:** each filled section is a copy of the parent section with
  `"is_hydrated": true` added. The key appears only in the hydrated view, never in a written
  manifest.
- **Evidence status:** the reproducibility assessment classifies filled sections as
  `inherited`, distinct from `observed` data the child recorded directly.
- **Snapshot checks:** the assessment reports a parent that is missing, blocked by the
  `[report].allow_external_meta_ref` / `[report].meta_ref_allowed_dirs` policy, not a `.json`
  file, malformed, or not a `"pubrun-meta-snapshot"`. It also reports a parent whose
  `timing.started_at_utc` is more than one day before the child run or later than it, and a
  parent whose `host.hostname`, `host.os_name`, `python.version`, or `git.commit` differs from
  the child's directly observed value.
- **Script modification time:** when `invocation.script.mtime` is later than the parent
  snapshot, the assessment flags script drift. The reverse does not hold: an unchanged script
  modification time does not prove the child ran with the parent's dependencies, because
  packages can change without the script changing.

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
