# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Signal and exit-code capture**: New `capture/signals.py` engine non-intrusively records OS signals (`SIGINT`, `SIGTERM`, `SIGHUP`, `SIGUSR1`, `SIGUSR2`, `SIGBREAK`) and the process exit code. Chains to any pre-existing signal handlers so importing scripts are never disrupted. Manifest now includes a `"signals"` section with `signals_received`, `exit_code`, and `exit_exception` fields. Configurable via `[capture.signals].enabled` in `.pubrun.toml`.
- **`pubrun status` CLI command**: List all runs with a compact table (`pubrun status`), verbose detail (`pubrun status -v`), or inspect a specific run (`pubrun status <run-id>`). Shows status (completed/running/crashed/failed), exit code, elapsed time, git commit, and live RSS/CPU for running processes.
- **Run lock file**: A `.pubrun.lock` file is written at run start and removed at finalization. Enables external tools to detect active, crashed, or orphaned runs via PID liveness checks with start-time verification to handle PID recycling.
- **Cross-platform process liveness** (`capture/liveness.py`): PID alive check, process start time, RSS memory, and CPU usage queries for Linux (`/proc`), macOS (`ps`), and Windows (`ctypes`/`wmic`). All stdlib, zero dependencies.

### Fixed

- **Schema validation**: Added `signals` property and `signals_section` definition to `manifest.schema.json`. Added `ghost` to the `outcome` enum. Manifests now validate correctly.
- **`pubrun status` field extraction**: Fixed incorrect manifest field lookups (`git.commit_sha` → `git.commit`; `invocation.script_name` → `invocation.script.basename` with argv fallback).
- **`docs/manifest.md`**: Corrected `is_dirty` → `dirty` to match the actual manifest field name.
- **`docs/configuration.md`**: Added missing `[capture.signals]` section to match the actual config schema in `default.toml`.

### Tests

- Added 47 new tests across 3 test files: `test_signals.py` (signal capture lifecycle, chaining, excepthook, config toggle), `test_liveness.py` (PID liveness, start time, RSS, CPU, hostname), `test_status.py` (lock file lifecycle, status scanning, classification, rendering, CLI dispatch). Total: 292 tests.

## [0.1.1] - 2026-05-09

### Added

- **`--version` CLI flag**: `pubrun --version` now prints the installed version.
- **`PUBRUN_PROFILE` environment variable**: Overrides `[core].profile` at runtime without a config file.
- **`__all__` declaration**: `__init__.py` now declares a formal public API surface.
- **Console tee documentation**: README Quick Start now documents the stdout/stderr tee behavior and how to disable it for high-output scripts.

### Changed

- **Single-source versioning**: `__version__` is now read from installed package metadata via `importlib.metadata` instead of being hard-coded.
- **CLI `prog` name**: Help output now shows `pubrun` instead of `__main__.py`.
- **CLI help text**: All help strings rewritten for conciseness. Removed verbose and non-technical phrasing.
- **Error messages**: Standardized CLI error messages to use consistent `Error: Failed to ...` format.
- **`default.toml` comments**: Full rewrite. All configuration comments now use concise, technical phrasing.
- **Module docstring**: `__init__.py` docstring rewritten for clarity.
- **`CITATION.cff`**: Version bumped to 0.1.1; abstract cleaned.

### Improved

- **Docstring audit**: All docstrings and inline comments across 24 source files cleaned to remove non-technical prose.
- **`_handle_inactive()` extraction**: Duplicate inactive-run handling from `annotate()` and `phase.__enter__()` consolidated into a shared helper.

### Security

- **Subprocess argv redaction**: CLI arguments in `sys.argv` and subprocess records matching sensitive patterns (passwords, tokens, API keys, etc.) are now redacted before being written to the manifest. Configurable via `[redaction].argv_enabled` in `.pubrun.toml`.
- **Expanded secret detection**: Added patterns for `private`, `conn_str`, `connection_string`, `database_url`, `dsn`, `signing`, and `bearer` to the default sensitive key regex.
- **Thread-safe subprocess tracking**: `SubprocessSpy._records` mutations are now protected by `threading.Lock` to prevent race conditions in parallelized HPC array jobs.

### Fixed

- **Double-finalization guard**: `_finalize_state()` is now idempotent, preventing redundant cleanup calls in writer or exit hooks.
- **Ghost mode stability**: Tracker now initializes `_outcome` and `_finalized` attributes even on failure (e.g., read-only filesystem), preventing `AttributeError` on `stop()`.
- **Event stream race condition**: Consolidated double-lock into a single atomic lock covering both budget check and file I/O.
- **Config merge leakage**: `_deep_merge()` now uses `copy.deepcopy()` to prevent nested dictionary reference sharing across run instances.
- **Diagnostics field names**: Subprocess reports now use `argv`/`exit_code` to match the actual manifest schema (was `command`/`return_code`).
- **Mutable default argument**: Fixed `get_invocation(config: Dict = {})` to `Optional[Dict] = None`.
- **OS detection**: Methods report now uses `host.os_name` from the manifest instead of the Windows-only `OS` environment variable.
- **Import-time safety**: Boot sequence wrapped in `try/except` to prevent corrupt configs from crashing `import pubrun`.
- **shlex fallback**: `SubprocessSpy` now handles unterminated quotes in command strings without crashing.

### Improved

- **Console performance**: `TqdmSafeTee.write()` rewritten from O(n²) char-by-char to O(n) split-based processing.
- **File hashing**: SHA-256 generation uses chunked 8KB reads instead of full-file read, preventing memory spikes on large inputs.
- **Redaction configurability**: Env var and argv redaction are independently toggleable via `[redaction].env_enabled` and `[redaction].argv_enabled`. Both default to on.
- **Git safety**: `_run_git()` calls wrapped in `disable_spy()` to prevent circular subprocess logging.

### Removed

- 224 redundant `pass # for auto-indentation` statements across 18 source files.

### Tests

- Test suite expanded from 13 to 232 tests across 12 test files.
- New coverage: manifest schema contract, all 6 capture engines, public API contracts (start/stop/annotate/phase/tracked_run/audit_run/diff), config file discovery and precedence, diff normalization and PATH splitting, report generation (markdown/LaTeX), manifest hydration, and exhaustive CLI dispatch for every subcommand.
- Added `tests/fixtures/sample_manifest.json` golden fixture for deterministic contract tests.

## [0.1.0] - 2026-04-03

### Added

- **Core library**: Singleton `Run` tracker with automatic provenance capture via `start()`, `stop()`, `annotate()`, `phase()`, `tracked_run()`, `audit_run()`, and `diff()`.
- **Manifest-first design**: Each run produces a `manifest.json` (schema v1.0), `config.resolved.json`, and optional `events.jsonl`, console logs, and `methods.md`/`.tex`.
- **Capture engines**: Modular sub-engines for hardware, environment, packages, git, invocation, subprocesses, console (tee-style with tqdm-safe carriage return squashing), resources (background thread sampling), and process metadata.
- **Configuration system**: Hierarchical TOML configuration (`default.toml` -> user-global -> project-local -> API overrides) with per-category depth controls (`off`, `basic`, `standard`, `deep`).
- **Redaction engine**: Regex-based detection and destructive redaction of sensitive environment variables.
- **CLI commands**: `pubrun report`, `pubrun methods`, `pubrun rerun`, `pubrun diff`, `pubrun meta`, `pubrun cite`.
- **CLI utilities**: `--create-config`, `--show-config`, `--info`, `--run-tests`.
- **HPC support**: Parent-child manifest hydration via `PUBRUN_META_REF` for array job provenance.
- **Ghost mode**: Silent failure if filesystem operations fail, preventing the library from crashing the host application.
- **Subprocess spy**: Transparent monkey-patching of `subprocess.Popen` and `os.system` to capture spawned processes.
- **Schema**: Formal JSON Schema (`schemas/manifest.schema.json`) for manifest validation.
- **Documentation**: Architecture spec, functional spec, CLI reference, API reference.
- **Test suite**: pytest-based tests covering tracker lifecycle, config resolution, event streaming, hardware capture, resource monitoring, subprocess interception, and console tee.

### Design Decisions

- **Timestamps as POSIX epoch floats**: All timestamps use `time.time()` for sub-second precision, timezone-agnostic storage, trivial arithmetic, and deterministic serialization.
- **Zero dependencies**: No runtime dependencies except `tomli` for Python < 3.11.
- **Auto-start**: Configurable import-time activation via `auto_start = true` in config.

### Notes

- Tests require `pytest >= 7.0` for `pythonpath` support in `pyproject.toml`.
- `tox.ini` targets Python 3.10 and 3.11.
