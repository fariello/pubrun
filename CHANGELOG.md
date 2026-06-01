# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-05-31

### Added

- **Signal and exit-code capture**: New `capture/signals.py` engine non-intrusively records OS signals (`SIGINT`, `SIGTERM`, `SIGHUP`, `SIGUSR1`, `SIGUSR2`, `SIGBREAK`) and the process exit code. Chains to any pre-existing signal handlers so importing scripts are never disrupted. Manifest now includes a `"signals"` section with `signals_received`, `exit_code`, and `exit_exception` fields. Configurable via `[capture.signals].enabled` in `.pubrun.toml`.
- **`pubrun status` CLI command**: List all runs with a compact table (`pubrun status`), verbose detail (`pubrun status -v`), or inspect a specific run (`pubrun status <run-id>`). Shows status (completed/running/interrupted/crashed/failed), exit code, elapsed time, git commit, command-line arguments, and live RSS/CPU for running processes. Script column width adapts to terminal width; command-line args are displayed when space permits.
- **Run lock file**: A `.pubrun.lock` file is written at run start and removed at finalization. Enables external tools to detect active, crashed, or orphaned runs via PID liveness checks with start-time verification to handle PID recycling.
- **Cross-platform process liveness** (`capture/liveness.py`): PID alive check, process start time, RSS memory, and CPU usage queries for Linux (`/proc`), macOS (`ps`), and Windows (`ctypes`/`wmic`). All stdlib, zero dependencies.
- **`pubrun clean` CLI command**: Interactively delete old run directories. Lists candidates with exit code, args, age, and size (terminal-width-adaptive). Requires explicit selection via numbers, ranges (e.g. `1-3,5`), or `all` — then shows the selected runs in a confirmation table before final `y/N` prompt. Supports `--older-than` (e.g. `7d`, `24h`), `--status` filter, `--yes` (non-interactive), and `--dry-run`. Running processes are never deleted.
- **`interrupted` outcome**: Runs that received SIGINT, SIGTERM, or SIGHUP are now marked as `"interrupted"` rather than `"completed"`. This applies even when user code catches `KeyboardInterrupt` — the signal was still received and recorded. Displayed in magenta in `pubrun status`.

### Security

- **`meta_ref` path traversal**: External `meta_ref` paths that resolve outside the manifest's parent directory are now rejected by default. Controlled by new `[report].allow_external_meta_ref` (bool) and `[report].meta_ref_allowed_dirs` (list) config keys.
- **Run directory permissions**: Run directories are now created with mode `0o700` on POSIX to prevent other users on shared systems from reading captured environment data.

### Fixed

- **Schema validation**: Added `signals` property and `signals_section` definition to `manifest.schema.json`. Added `ghost` to the `outcome` enum. Manifests now validate correctly.
- **`pubrun status` field extraction**: Fixed incorrect manifest field lookups (`git.commit_sha` → `git.commit`; `invocation.script_name` → `invocation.script.basename` with argv fallback).
- **`docs/manifest.md`**: Corrected `is_dirty` → `dirty` to match the actual manifest field name.
- **`docs/configuration.md`**: Added missing `[capture.signals]` section to match the actual config schema in `default.toml`.
- **Atomic manifest writes**: `manifest.json` and `config.resolved.json` are now written via temp file + `os.replace()` to prevent readers from seeing partially written files.
- **Engine crash isolation**: If any capture engine raises during initialization, the run promotes to ghost mode rather than propagating the exception to the host script.
- **Signal handler re-installation**: After SIG_DFL re-delivery, the shim handler is re-installed so subsequent signals are still recorded if the process survives.
- **Signal handler ordering**: `_previous_handlers` now only records entries after `signal.signal()` succeeds, preventing stale entries on failure.
- **Non-main-thread warning**: A WARNING is logged when signal capture is unavailable due to non-main-thread execution.
- **`audit_run` metadata**: Decorated functions now preserve `__name__`, `__doc__`, and `__qualname__` via `functools.wraps`.
- **`ref_count` atomicity**: Increment/decrement of `ref_count` in `start()`/`stop()` is now protected by a lock.
- **macOS liveness parsing**: Replaced locale-dependent `%c` datetime format with explicit `"%a %b %d %H:%M:%S %Y"`.
- **Console stream restore safety**: `stop()` now only restores `sys.stdout`/`sys.stderr` if they still point to pubrun's tees. If a third-party wrapper was installed after pubrun, streams are left alone.
- **`pubrun status` script column**: Removed hard cap of 24 characters on the script column. Width now scales proportionally with terminal width (up to 40% of available columns).
- **Removed `rich` dependency**: Dropped the optional `rich` integration from `pubrun diff` and `pubrun --show-config`. All output now uses the built-in ANSI renderer, which supports color, truncation, wrapping, and path-split diffs natively. Eliminates the "pip install rich" suggestion and the risk of runtime errors from broken rich installations.
- **Ghost outcome preserved after `stop()`**: Previously, calling `stop()` on a ghost-mode run would overwrite the outcome to `"completed"`. The outcome is now sticky — `"ghost"` and `"failed"` outcomes are never overwritten.
- **SIGTERM/SIGHUP finalization**: Active runs now write artifacts (manifest) before SIG_DFL re-delivery on SIGTERM/SIGHUP, preventing data loss on polite kills.
- **Config resolution fallback**: If `.pubrun.toml` contains invalid TOML, `Run()` now falls back to default config with a warning instead of crashing.
- **Critical-event secondary cap**: Annotations and phases have a secondary cap (10x `max_tracked_events`, minimum 10,000) to prevent unbounded disk writes from `annotate()` in tight loops.
- **macOS `disable_spy()` in hardware capture**: Darwin `sysctl` and `system_profiler` calls are now wrapped in `disable_spy()` to prevent self-logging in subprocess records.
- **ResourceWatcher thread join**: `stop()` now joins the background thread (capped at 5s) before taking the final measurement, eliminating a race between the daemon thread and the caller.
- **CLI error message consistency**: All CLI error messages now use the `Error: ...` prefix format consistently.
- **Convenience kwarg flattening**: `start(profile="deep", output_dir="./x")` now works — flat kwargs matching `core` keys (`profile`, `output_dir`, `auto_start`, `meta_ref`) are automatically nested. The caller's dict is not mutated.
- **Removed undocumented `pbr` easter egg** from CLI entrypoint.
- **GitHub URLs**: Fixed `pyproject.toml` and `CITATION.cff` URLs from `gfariello/pubrun` to `fariello/pubrun`.

### Tests

- Added 47 new tests across 3 test files: `test_signals.py` (signal capture lifecycle, chaining, excepthook, config toggle), `test_liveness.py` (PID liveness, start time, RSS, CPU, hostname), `test_status.py` (lock file lifecycle, status scanning, classification, rendering, CLI dispatch).
- Added 28 additional tests covering: `_merge_and_migrate()` (directory moves, file preservation, failure resilience), CLI error exit codes (6 paths), `_handle_inactive` policy enforcement (`error`/`warn`/`ignore`), `_bootstrap_engines` multi-failure ghost mode, diff engine edge cases (empty/identical/disjoint manifests), ResourceWatcher failure threshold and `to_manifest_dict` edge cases, auto-start boot sequence (`PUBRUN_AUTO_START=true/false`).
- Added 41 additional tests in second improvement pass: `generate_report()` with degraded manifests (missing git, empty python, no hardware, no packages, LaTeX escaping), `generate_meta_snapshot()` unit tests (JSON structure, required keys, default path), `_render_inline()` fallback rendering and `NO_COLOR` env var, `print_report()` at each depth level, `SubprocessSpy.finalize_all()` state transitions and `_max_records` overflow, `disable_spy()` nesting, `TqdmSafeTee` multi-CR handling and `line_count` accuracy and `__getattr__` delegation, `EventStream` constructor failure path, config non-overlapping merge from both local files.
- Added 10 tests for `pubrun clean`: deletion, running-process safety, `--older-than` filter, `--status` filter, `--dry-run`, batch deletion, CLI help and dry-run.
- Added 9 tests for `_parse_selection`: single numbers, comma-separated, ranges, mixed, out-of-bounds, invalid input, spaces, empty string.
- Added 2 tests for `interrupted` outcome: SIGINT sets outcome; no-signal stays completed.
- Added defensive assertions in flaky annotate tests (fast-fail on ghost mode).
- Updated render tests for rich removal (truncation, wrap, same section).
- Added 11 regression tests from QA/QC pass: auto-start failure resilience, resolve_config fallback, `_finalize_active_run` write_artifacts call, ghost outcome preserved after stop, kwarg flattening, kwarg non-mutation. Total: 408 tests.

### Documentation

- **README.md**: Added footnote clarifying `tomli` dependency on Python <3.11. Added `--version` to diagnostic flags table. Added `ghost` and `interrupted` statuses to the Monitoring Runs table. Added `pubrun clean` command reference. Added Installation section. Fixed API override examples to use correct nested syntax. Updated roadmap.
- **`docs/cli.md`**: Added full `clean` command reference with all options and interactive mode documentation. Added `interrupted` status. Updated command count to eight. Removed stale `rich` reference from `--show-config`.
- **`docs/manifest.md`**: Added missing `git.repo_root` field. Corrected `status.outcome` enum to include all actual values: `"completed"`, `"failed"`, `"interrupted"`, `"ghost"`, `"unknown"`. Documented `.pubrun.lock` file format.
- **`docs/functional_spec.md`**: Corrected `meta --out` default behavior description. Added `status` and `clean` commands to the CLI subcommands specification. Removed stale `rich` references. Fixed meta_ref security to match implementation (blocked by default). Added critical-event secondary cap documentation. Removed phantom `summary.txt` references.
- **`docs/api.md`**: Added outcome determination documentation to `stop()`. Fixed API override examples.
- **`docs/configuration.md`**: Added `max_tracked_events` to `[events]` section. Marked `[logging].write_summary` as not yet implemented.
- **`pyproject.toml`**: Fixed GitHub URLs (`gfariello` → `fariello`).
- **`default.toml`**: Added `max_tracked_events` to `[events]`, commented `meta_ref` to `[core]`, marked `[capture.determinism]` and `[logging].write_summary` as not yet implemented, fixed documentation URL, updated console mode descriptions.
- **`TODO.md`**: Added deferred audit issues, test coverage gaps, feature plans (timestamped console capture, `pubrun combined` command), and removed-from-roadmap rationale.
- **CI**: Added GitHub Actions workflow (`.github/workflows/ci.yml`) with matrix testing across Python 3.8–3.13 on Linux, macOS, and Windows.

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
