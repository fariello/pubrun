[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)

# pubrun Configuration Reference

`pubrun` uses a hierarchical TOML configuration system. Every setting has a sensible default — you only need a config file if you want to change something.

---

## Configuration Discovery

`pubrun` looks for configuration in these locations, applied in this precedence order (highest to lowest):

| Priority | Source | Example |
|---|---|---|
| 1 (highest) | API overrides | `pubrun.start(profile="deep")` |
| 2 | Environment variables | `PUBRUN_AUTO_START=false` |
| 3 | Local project `.pubrun.toml` | `./.pubrun.toml` |
| 4 | Local project deep config | `./.config/pubrun/config.toml` |
| 5 | User home config | `~/.config/pubrun/config.toml` |
| 6 (lowest) | Built-in defaults | `default.toml` (shipped with the library) |

When both `.pubrun.toml` and `.config/pubrun/config.toml` exist in the same directory, `.pubrun.toml` takes precedence (it is applied last).

### Generating a Configuration File

```bash
pubrun --create-config                    # Interactive prompt
pubrun --create-config .pubrun.toml       # Write to specific path
```

### Viewing the Default Configuration

```bash
pubrun --show-config
```

---

## Configuration Sections

### `[core]`

Core behaviors governing run initialization and storage.

| Key | Type | Default | Description |
|---|---|---|---|
| `profile` | string | `"default"` | Master capture depth: `"minimal"`, `"default"`, or `"deep"`. Controls default depth for all categories unless overridden. |
| `output_dir` | string | `""` | Base directory for run output. Empty string defaults to `./runs/` in the current working directory. |
| `auto_start` | bool | `true` | If `true`, `import pubrun` automatically starts a trace. If `false`, you must call `pubrun.start()` explicitly. Equivalent to `[imports].mode = "noauto"` when set to `false`. |

### `[imports]`

Controls import-time behavior. These settings determine what happens when `import pubrun` is executed.

| Key | Type | Default | Description |
|---|---|---|---|
| `mode` | string | `"auto"` | Import behavior preset: `"auto"` (start tracking on import), `"full"` (start tracking and force console capture on — the opposite of `"noconsole"`), `"noauto"` (load API only, start manually), `"nopatch"` (start tracking but skip global hooks), `"noconsole"` (start tracking, skip console wrapping), `"minimal"` (load API only, no hooks). An in-code `import pubrun.<mode>` overrides this key and any env var; only `pubrun run --mode` overrides the in-code import. |
| `on_conflict` | string | `"warn"` | What to do if a later import requests a different mode: `"ignore"`, `"warn"`, or `"error"`. |
| `record_provenance` | bool | `true` | Record import-mode provenance (caller file, line) in the manifest. |
| `provenance_depth` | int | `3` | Number of external caller frames to capture for diagnostics. |
| `provenance_path_mode` | string | `"relative"` | How paths appear in provenance: `"absolute"`, `"relative"`, `"basename"`, or `"redacted"`. |
| `max_requests` | int | `50` | Maximum import-mode requests to retain in metadata. |

> [!NOTE]
> You can also use namespaced imports as an alternative to config:
> ```python
> import pubrun.full as pubrun     # Equivalent to mode = "full"
> import pubrun.noauto as pubrun   # Equivalent to mode = "noauto"
> import pubrun.nopatch as pubrun  # Equivalent to mode = "nopatch"
> import pubrun.noconsole as pubrun # Equivalent to mode = "noconsole"
> import pubrun.minimal as pubrun  # Equivalent to mode = "minimal"
> ```
> An in-code import mode overrides this config key and env vars; only
> `pubrun run --mode` overrides the in-code import.

### `[console]`

Controls interception and logging of stdout/stderr.

| Key | Type | Default | Description |
|---|---|---|---|
| `capture_mode` | string | `"off"` | `"off"` — no capture (default, zero-footprint); `"basic"` — tee stdout/stderr to text files; `"standard"` — tee with timestamps on each line; `"deep"` — reserved for future structured capture (currently same as standard). |
| `non_tty_mode` | string | `"inherit"` | Override capture behavior when stdout is not a TTY (piped/redirected): `"inherit"` (use capture_mode as-is), `"off"`, or `"basic"`. |
| `jupyter_mode` | string | `"off"` | Override capture behavior when running inside Jupyter/IPython. Default `"off"` auto-disables capture in notebooks. Set to `"standard"` to force capture in Jupyter. |

### `[events]`

Controls the real-time `events.jsonl` stream.

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `true` | Whether to write events (phases, annotations) to `events.jsonl`. |
| `max_tracked_events` | int | `1000000` | Maximum number of regular events written per run. When exhausted, non-critical events are silently dropped. Critical events (annotations, phases) bypass this limit up to a secondary cap of 10x this value (minimum 10,000). |
| `flush_interval_events` | int | `100` | Number of non-critical events to buffer before flushing to disk. Higher values improve throughput but increase data-loss window on hard crashes. Critical events (annotations, phases) always flush immediately regardless. |
| `on_inactive_annotate` | string | `"ignore"` | Behavior when `annotate()` is called with no active run: `"ignore"`, `"warn"`, or `"error"`. |

### `[redaction]`

Security policies for preventing secret leakage into manifest files.

| Key | Type | Default | Description |
|---|---|---|---|
| `sensitive_keys_regex` | string | *(see below)* | Regex pattern for detecting sensitive variable names. |
| `representation` | string | `"redacted"` | How detected secrets are masked: `"redacted"` (destructive) or `"hashed"` (SHA-256). |
| `env_enabled` | bool | `true` | Whether to redact matching environment variable values. |
| `argv_enabled` | bool | `true` | Whether to redact matching CLI argument values in `sys.argv` and subprocess records. |

**Default sensitive_keys_regex:**
```
(?i)(password|secret|token|api_key|key|auth|cred|private|conn_str|connection_string|database_url|dsn|signing|bearer)
```

> [!IMPORTANT]
> Redaction is **destructive by default**. Raw values are replaced with `{"representation": "redacted"}` and no hashes are generated, to prevent brute-force rainbow table attacks. Switch to `representation = "hashed"` only if you need to verify whether a secret changed across runs.

---

### `[capture.environment]`

| Key | Type | Default | Description |
|---|---|---|---|
| `mode` | string | `"filtered"` | `"allowlist"` — only permitted vars; `"filtered"` — all vars with secret redaction; `"full"` — raw dump (unsafe). |
| `depth` | string | `"standard"` | Capture depth for this category. |

### `[capture.packages]`

| Key | Type | Default | Description |
|---|---|---|---|
| `mode` | string | `"imported-only"` | `"imported-only"` — scan `sys.modules`; `"imported-transitive"` — imported packages plus their declared dependencies (one level); `"top-level-installed"` — pip/conda list; `"full-environment"` — every dependency in the virtualenv. |
| `depth` | string | `"standard"` | Capture depth for this category. |

### `[capture.subprocesses]`

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `true` | Whether to intercept `subprocess.Popen` and `os.system` calls. |
| `depth` | string | `"basic"` | Capture depth for this category. |
| `max_tracked_commands` | int | `5000` | Stop recording after this many subprocesses to prevent OOM. |

### `[capture.process]`

| Key | Type | Default | Description |
|---|---|---|---|
| `depth` | string | `"standard"` | Capture depth for process metadata (PID, user, etc.). |

### `[capture.host]`

| Key | Type | Default | Description |
|---|---|---|---|
| `depth` | string | `"standard"` | Capture depth for OS-level machine details. |

### `[capture.python]`

| Key | Type | Default | Description |
|---|---|---|---|
| `depth` | string | `"standard"` | Capture depth for Python runtime details. |

### `[capture.git]`

| Key | Type | Default | Description |
|---|---|---|---|
| `depth` | string | `"standard"` | Capture depth for Git repository state. |
| `check_dirty` | bool | `true` | Whether to run `git status --porcelain` to detect uncommitted changes. Set to `false` for faster startup on large or network-mounted repos. |
| `timeout` | int | `5` | Per-command timeout (seconds) for every git invocation, including repository detection. A timeout is recorded as `capture_state.status = "timeout"` (distinct from "not a git repository"), so a slow/large repo is never mislabeled as "not a repo". |

### `[capture.inputs]`

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `true` | Whether to scan `sys.argv` for input file paths. |
| `ignore_extensions` | list | `[]` | File extensions to skip (e.g., `["pyc", "log"]`). |
| `compute_md5` | bool | `false` | If `true`, hash all detected input files (slow for large files). If `false`, record only mtime/size. |

### `[capture.hardware]`

| Key | Type | Default | Description |
|---|---|---|---|
| `depth` | string | `"basic"` | Capture depth for hardware introspection. |
| `capture_gpu_clock_speed` | bool | `false` | Query GPU clock speeds (requires NVML; slow). |
| `capture_gpu_fp_precision` | bool | `false` | Query GPU floating-point precision support. |
| `capture_cpu_clock_speed` | bool | `false` | Query CPU clock speeds (reads `/proc`). |
| `capture_cpu_fp_precision` | bool | `false` | Query CPU floating-point precision support. |
| `timeout` | int | `10` | Per-command timeout (seconds) for hardware-inspection subprocesses (`nvidia-smi`, `system_profiler`, `sysctl`, `wmic`). Bounds a hung tool (e.g. a wedged GPU driver) so it cannot orphan the background hardware thread. |

### `[capture.resources]`

| Key | Type | Default | Description |
|---|---|---|---|
| `depth` | string | `"standard"` | Capture depth for background resource monitoring. |
| `scope` | string | `"process"` | What RSS to measure: `"process"` (main process only) or `"tree"` (sum resident memory across the whole process tree — parent plus all descendant processes). Tree mode is useful for multiprocessing/Dask/Ray workloads where the main process is a thin orchestrator. **Affects memory (RSS) only** — CPU is always measured for the current process (via `os.times()`, which includes already-reaped children). Tree RSS is captured on **Linux and macOS**; Windows falls back to process scope. When enabled, adds `peak_tree_rss_bytes`/`end_tree_rss_bytes` to the manifest and `tree_rss_bytes` to each `resource_sample` event. |
| `sample_interval_seconds` | int | `15` | How often the background thread samples CPU/memory. |
| `max_consecutive_failures` | int | `3` | Kill the background thread after this many consecutive **unreadable** polls (errors/timeouts). A legitimate reading of 0 does not count, so a transient blip cannot permanently disable telemetry. |
| `poll_timeout` | int | `3` | Per-poll timeout (seconds) for the macOS/Windows sampling subprocesses (`ps`/`wmic`). Bounds a hung tool so it cannot orphan the sampling thread. |
| `system_metrics` | bool | `true` | Also sample **system-wide** dynamic metrics alongside per-process RSS/CPU: available memory, load average, and (Linux only) node iowait. These make post-hoc I/O / contention diagnosis possible (e.g. "was this run starved for RAM or on a busy node?"). Cheap (single `/proc` reads) and only sampled when the watcher is running (`depth != "off"`). Adds `system_memory`/`load_average`/`system_iowait_pct` to the `resources` manifest section. Note: `system_iowait_pct` is **node-wide, indicative only** (not run-scoped). Set `false` to omit. |

#### Enabling process-tree memory capture

`scope` is a nested key, so set it in a config file or pass it as a nested dict to the
API (there is no environment-variable shortcut for nested `capture.*` keys — only
`PUBRUN_PROFILE`, `PUBRUN_META_REF`, and the import-mode variables are wired to env).

**For a whole project** — add to the project's `.pubrun.toml` (or
`.config/pubrun/config.toml`):

```toml
[capture.resources]
scope = "tree"
```

**For your user account (all projects)** — the same stanza in
`~/.config/pubrun/config.toml`.

**For a single script (via the API)** — pass the nested section to `start()`:

```python
import pubrun.noauto as pubrun

pubrun.start(capture={"resources": {"scope": "tree"}})
# ... your work ...
pubrun.stop()
```

The `pubrun.start(profile=..., output_dir=...)` shorthand only flattens the top-level
`[core]` keys; every `[capture.*]` setting must be passed as the nested dict shown
above.

### `[capture.file_io]`

Controls how much detail `pubrun.open(...)` records for files it wraps. This does **not**
globally intercept `open()` — pubrun never patches the builtin; it only governs files you
explicitly route through `pubrun.open()`.

| Key | Type | Default | Description |
|---|---|---|---|
| `level` | string | `"stat"` | Progressive detail level: `none` \| `name` \| `stat` \| `realpath` \| `hash`. `stat` records size/mtime/ctime via `fstat` on the open fd (~free, incl. on NFS) + the absolute path. `realpath` adds symlink resolution (**costlier on NFS/Lustre** — walks every path component). `hash` adds a SHA-256 of the file contents (reads every byte). `none` disables recording. |
| `max_hash_bytes` | int | `0` | At `level = "hash"`, skip hashing files larger than this many bytes (`0` = no cap). |

> **Changed in 1.4.0:** the default level is `stat` (metadata only). Previously
> `pubrun.open()` always hashed; set `level = "hash"` to restore that. The recorded hash is
> computed from the on-disk bytes at close, so it is correct regardless of read path.

### `[capture.profiling]`

Phase-scoped profiling (opt-in). When enabled, `pubrun.phase()` blocks are profiled and stats saved to the run directory.

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `false` | Master switch for profiling. Must be explicitly enabled. |
| `backend` | string | `"cprofile"` | `"cprofile"` — stdlib cProfile (zero dependencies, ~30-50% overhead within phase); `"yappi"` — requires `pip install yappi` (~10-20% overhead). If the selected backend is unavailable, logs a warning and skips. |

When enabled, each `pubrun.phase("name")` block saves a `profile-<name>.prof` file (pstats-compatible) to the run directory. Load with `snakeviz`, `pstats`, or `flameprof`.

### `[capture.signals]`

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `true` | Install non-intrusive signal handlers (`SIGINT`, `SIGTERM`, `SIGHUP`, `SIGUSR1`, `SIGUSR2`, `SIGBREAK` where available) that record received signals and the process exit code. Handlers chain to any pre-existing handlers without disrupting the importing script. Disable to skip the `"signals"` manifest section entirely. |

### `[capture.determinism]`

| Key | Type | Default | Description |
|---|---|---|---|
| `depth` | string | `"off"` | Track/lock pseudorandom seeds (Python `random`, numpy). Currently off by default. |

---

### `[report]`

Controls for `pubrun report` and `pubrun methods` manifest hydration.

| Key | Type | Default | Description |
|---|---|---|---|
| `allow_external_meta_ref` | bool | `false` | When hydrating a manifest via `meta_ref`, allow the referenced file to live outside the manifest's parent directory. When `false` (default), external paths are rejected to prevent arbitrary file reads from tampered manifests. |
| `meta_ref_allowed_dirs` | list | `[]` | Allowlist of absolute directory paths permitted as sources for `meta_ref` files. Only consulted when `allow_external_meta_ref` is `false`. Example: `["/scratch/projects/myproject"]`. |

---

### `[logging]`

| Key | Type | Default | Description |
|---|---|---|---|
| `write_summary` | bool | `false` | Reserved for future use. Intended to generate a `summary.txt` in the run directory. Not yet implemented. |

### `[methods]`

| Key | Type | Default | Description |
|---|---|---|---|
| `format` | string | `"markdown"` | Default output format for `pubrun methods`: `"markdown"` or `"latex"`. |

### `[diff]`

Configuration for the `pubrun diff` engine. The three ignore lists control how much each
depth level hides; they are nested by intent — **`--basic` hides the most, `--deep` hides
nothing**:

- **`ignore_basic`** — hides everything `--standard` hides, PLUS the high-volume, low-signal
  sections (`process`, `hardware`, `resources`, `environment`, `subprocesses`, `packages`) so
  `--basic` shows only the user-facing changes (script/argv, python, git, config).
- **`ignore_standard`** — hides volatile / always-different fields: timestamps (`*_utc`), run
  ids, PIDs, per-run absolute paths (`filesystem.*.path`/`mount_point`, `capture.run_dir`),
  and import-request timestamps. Keeps meaningful signals like `fstype`/`is_network`. At
  `--standard`, list-valued sections (subprocesses, packages) are **summarized** (counts +
  identities) rather than diffed element-by-element.
- **`ignore_deep`** — empty; `--deep` compares everything, element by element.

The authoritative default lists live in the shipped `default.toml` `[diff]` section (they are
long); override any of them in your `.pubrun.toml`.

| Key | Type | Description |
|---|---|---|
| `ignore_basic` | list | Keys ignored at `--basic` depth (see above; the largest list). |
| `ignore_standard` | list | Keys ignored at `--standard` depth (see above). |
| `ignore_deep` | list | Keys ignored at `--deep` depth — `[]` by default. |
| `show_same` | bool (`false`) | Show unchanged values in diff output. |
| `export_format` | string | `"txt"` | Output format for `--export`: `"txt"` or `"json"`. |
| `wrap` | bool | `true` | Wrap long strings instead of truncating with ellipsis. |
| `max_string_length` | int | `300` | Maximum characters per value before wrapping/truncation. |

---

## Environment Variables

| Variable | Description |
|---|---|
| `PUBRUN_IMPORT_MODE` | Canonical import mode: `auto`, `noauto`, `nopatch`, `noconsole`, or `minimal`. Takes highest precedence. |
| `PUBRUN_PROFILE` | Override `[core].profile`. Set to `"minimal"`, `"default"`, or `"deep"`. |
| `PUBRUN_AUTO_START` | Legacy alias for import mode. `"false"` maps to `noauto`, `"true"` maps to `auto`. |
| `PUBRUN_META_REF` | Path to a parent `meta.json` for HPC hydration. Child runs will reference this. |
| `PUBRUN_IMPORT_CONFLICT` | Override `[imports].on_conflict`. Set to `"ignore"`, `"warn"`, or `"error"`. |

---

## Example: Minimal `.pubrun.toml`

```toml
[core]
auto_start = false
profile = "deep"

[console]
capture_mode = "off"

[events]
enabled = true
```

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
