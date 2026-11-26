[README](https://github.com/fariello/pubrun/blob/main/README.md) | [Architecture](https://github.com/fariello/pubrun/blob/main/docs/architecture.md) | [Functional Spec](https://github.com/fariello/pubrun/blob/main/docs/functional_spec.md) | [API](https://github.com/fariello/pubrun/blob/main/docs/api.md) | [CLI](https://github.com/fariello/pubrun/blob/main/docs/cli.md) | [Configuration](https://github.com/fariello/pubrun/blob/main/docs/configuration.md) | [Manifest](https://github.com/fariello/pubrun/blob/main/docs/manifest.md) | [Performance](https://github.com/fariello/pubrun/blob/main/docs/performance.md) | [Research Use](https://github.com/fariello/pubrun/blob/main/docs/research-use.md) | [HPC](https://github.com/fariello/pubrun/blob/main/docs/hpc.md) | [Changelog](https://github.com/fariello/pubrun/blob/main/CHANGELOG.md)

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **`pubrun bench` command and one-command GitHub contribution (`fariello/pubrun`).** Friendly front-end over the benchmark harness that runs locally by default and, on an HPC login node, detects the batch scheduler (`--scheduler {auto,slurm,pbs,lsf,sge,local}`) and offers to submit the job to a compute node (never submits without confirmation; `--submit`/`--yes` govern HPC scheduler job submission only and never imply consent to publish). Writes only a share-safe redacted result by default (`benchmarks/results/pubrun-bench-<hash>-<UTC-timestamp>.redacted.json`; pass `--unredacted` to also write the identifying local copy). After a run, `pubrun bench` runs the shared structural share-safety validator (`benchmarks/share_safety.py`) and offers to contribute the redacted result to `fariello/pubrun` (`--contribute` / `--no-contribute`, `--no-submit`, `--gh-repo`): via `gh` it creates an unlisted Gist and opens a GitHub issue linking the raw `.json` URL, falling back to embedding JSON inline under GitHub's ~65 KB body cap and then to a manual browser Issue Form (`--prepare-submission` copies only the redacted file into a clean `pubrun-share/` folder). `--submit-file <file>` validates and contributes an existing redacted file without re-running. All transport uses argv lists or stdin (never a shell), re-checks share-safety immediately before sending, never prints tokens or payloads, and rolls back an orphaned Gist if issue creation fails. A validate-only GitHub Actions workflow (`.github/workflows/benchmark-intake.yml`, `contents: read` + `issues: write`) checks attachments, Gist raw URLs, and inline JSON as data only and comments an idempotent pass/fail receipt. Requires a source checkout (benchmark tooling is not shipped in the wheel).
- **Slurm submit-and-wait.** On a Slurm login node, `pubrun bench` offers to submit the benchmark job (`benchmarks/submit_bench.sh` / `benchmarks/run_bench.sbatch`, emitting a parseable job ID via `sbatch --parsable`) and poll for completion (`--wait-timeout` to extend or disable), then runs the interactive share-check and contribution from the login node. Any interruption, timeout, or job failure falls back to `pubrun bench --submit-file <path>`; the result stays on the shared filesystem.
- **HPC multi-scheduler benchmark submission (Slurm/PBS/LSF/SGE).** `pubrun bench` detects and offers to submit to PBS/Torque, LSF, and SGE/Grid Engine in addition to Slurm (auto-detect order Slurm > PBS > LSF > SGE) using env+PATH checks only (resolving PBS-vs-SGE `qsub` ambiguity with `--scheduler pbs|sge`). Starting-point template scripts `benchmarks/submit_bench_pbs.sh`, `benchmarks/submit_bench_lsf.sh`, and `benchmarks/submit_bench_sge.sh` submit to the default queue (not CI-validated against live clusters; they currently pass `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`, writing a gitignored unredacted bare `.json` alongside the default `.redacted.json`). `pubrun self-check` emits an `INFO` nudge on HPC login nodes suggesting a compute-node `pubrun bench` run (does not trip `--strict`).
- **Maintainer tool to collect benchmark submissions locally (`benchmarks/pull_submissions.py`).** Fetches benchmark-submission issues via `gh`, runs the same fail-closed validation as CI (schema `pubrun-benchmark/5` + structural share-safety + 256 KB size cap), stores accepted redacted results content-addressed under `benchmarks/data/accepted/<sha256>.redacted.json` (with a metadata sidecar recording contributing issues), aggregates into `benchmarks/data/summary.csv` and `benchmarks/data/summary.md` via `benchmarks/aggregate.py`, and re-tags issues. Dry-run by default (`--apply` to write), invokes `gh` via argv lists, parses untrusted JSON as data only, and never pushes. Dev/reproducibility tooling, not shipped in the wheel.
- **Benchmark suite (`benchmarks/`) and `pubrun-benchmark/5` schema (`schemas/benchmark.schema.json`).** A reproducible, stdlib-only harness (`benchmarks/harness.py`) measuring startup and run-time overhead per feature (import modes, resource watcher, subprocess spy, git/hardware/packages capture, `pubrun.open()` / `pubrun.register_input()` and `print()` console tee hot paths; `pubrun` never patches `open()`). Includes `aggregate.py` (CSV + Markdown summary), optional `plot.py` and `test_benchmarks.py` under the dev-only `[bench]` extra, `docs/performance.md`, and a Draft 2020-12 JSON Schema (`schemas/benchmark.schema.json`) validated against both full and redacted `pubrun-benchmark/5` results.
- **Benchmark pass tiers, uncaptured baseline pass, and total wall time.** Every benchmark run starts with an uncaptured baseline pass (workload without `pubrun`, stored separately so it never mixes into overhead stats; `--no-baseline` skips it), followed by three preset tiers: `--quick` (baseline + 2x15), `--full`/default (baseline + 3x30), and `--rigorous` (baseline + 5x50), overridable with `--iterations`/`--passes`. Records `mode`, `baseline_pass`, `baseline`, and `total_wall_time_s`.
- **Benchmark data quality, ground-truth I/O baselines, and filesystem-health diagnostics.** Benchmark results (`pubrun-benchmark/5`) retain raw per-iteration timings, `environment_kind` (`venv`/`conda`/`system`/`virtualenv`/`frozen`), `in_venv`, `sys_path_len`, filesystem and Slurm allocation context, and per-pass dynamic host state (`pass_results[i].pass_env`: available RAM, load average, node iowait) while surviving share-redaction; `aggregate.py`/`plot.py` remain backward-compatible with older `/2`, `/3`, and `/4` files. New `io_baseline` scenarios (`io-baseline-devnull`, `io-baseline-devshm`, `io-baseline-tmpdir`) establish storage reference floors. Filesystem classification prefers Linux `/proc/self/mountinfo` (bind/overlay aware) and adds a Windows `ctypes` fstype branch. A diagnostic-only `os.statvfs` live probe surfaces free space, inode counts, read-only mounts, and wedged/slow mounts in a bounded daemon thread (never invoked by `import pubrun`); `pubrun self-check` warns about hung/slow/network-backed mounts as a system-wide hazard.
- **`pubrun --version` shows the commit hash.** Prints `pubrun <version> (commit <hash>)` when resolvable: live `git rev-parse HEAD` in source checkouts, falling back to build-time commit metadata stamped by `hatch_build.py` (`_build_meta.json` and legacy `COMMIT` written into wheel and sdist artifacts during build without mutating the working tree). Both paths are best-effort and stdlib-only.
- **Path/hostname/IP sanitizer (`scripts/sanitize_paths.py`).** Stdlib-only guard wired into pre-commit and CI (`--check` and `--fix` modes, with `--scrub`/`--match`/`--replace`/`--dry-run`) that blocks commits containing absolute home-directory paths, the machine hostname, and opt-in IP addresses, configured via tracked `.sanitize-allow.toml` and gitignored `.sanitize-local.toml` (`.sanitize-local.toml.example` documents the schema).
- **`pubrun show config` family.** Inspect resolved configuration across three contexts: `pubrun show config` (current directory), `pubrun show run config [<id>]` (from a past run's `config.resolved.json`, showing labeled startup snapshots for crashed runs and a clear error for ghost runs), and `pubrun show default config` (built-in defaults). Annotates keys overridden by higher-precedence layers (`--all` annotates every key), backed by `resolve_config_with_provenance()`.
- **TUI resource view (`pubrun ui`).** Adds a **Resources** tab showing peak/avg/min for CPU and memory (main process and process tree when captured) with compact sparklines (`r` shortcut; optional `[tui]` extra).
- **Recency-index run selector.** Commands accepting a run (`show`/`report`, `res`/`cpu`/`mem`, `methods`, `inspect`, `rerun`, `diff`, `status`) accept a bare positive integer recency index (`1` = most recent, `2` = second most recent) alongside run-ID prefixes and directory paths; `pubrun status` shows the index in a leading `#` column and refuses to guess on any collision.
- **Verbose, transparent `self-check` and `meta`.** `pubrun self-check` is itemized by default (one line per check with `[ OK  ]`/`[WARN ]`/`[INFO ]` and a timing footer; `--quiet`/`-q` restores the terse one-liner; `--json` emits `checks`, `findings`, `elapsed_seconds`; `--show-suggestions` adds remediation detail; `--strict` keys on `WARN` only). `pubrun meta` itemizes each gathered section with outcome, per-section timing, and total, surfacing failed sections as `[WARN ]`.
- **Richer `report`/`res` output and `report`/`show` flag parity.** `pubrun res` displays peak/avg/min with explicit `RSS (main)` / `CPU (main)` / `RSS (tree)` / `CPU (tree)` labels. Process-tree CPU (`resources.peak_tree_cpu_percent` and per-sample `tree_cpu_percent`) is captured under `[capture.resources].scope = "tree"` from summed CPU-time deltas across the tree (labeled "% of one core", unclamped, Linux-only). The `report`/`show` event timeline uses compact `YYYY-MM-DD HH:MM:SS` timestamps (local by default, `--utc` for UTC) showing the oldest 10 and newest 10 events with a truncation marker above 20, and `pubrun report` now accepts `--utc`.
- **Graded file-I/O provenance for `pubrun.open()` and per-process I/O counters.** `pubrun.open()` records provenance at configurable `[capture.file_io].level` (`none | name | stat | realpath | hash`): `stat` uses `fstat` on the open fd, `realpath` adds symlink resolution, and `hash` computes a streamed SHA-256 hash during sequential reads via `ProvenanceFileProxy`, falling back to re-reading at close only when streaming is not possible (capped by `max_hash_bytes`). Still opt-in and per-file (`pubrun` never patches global `open()`). The resource watcher also records per-process Linux `/proc/self/io` byte counters (`resources.io_counters`, `system_metrics`-gated).
- **`pubrun self-check` and `pubrun inspect` commands.** `self-check` reports local performance/config pitfalls (network filesystems, low RAM, high load) and install health (report-only). `inspect` diagnoses a completed run's manifest (I/O/RAM/load/filesystem signals, capture-completeness assessment, and a cross-host mismatch banner when inspecting from a different machine). Both support `--show-suggestions`/`-v`, `--json`, and `--strict`, and remain CLI-only (never imported by `import pubrun`). Added [HPC & performance diagnosis](docs/hpc.md).
- **Run-time I/O and environment capture.** Records filesystem types of output dir, run dir, and `$TMPDIR` (`filesystem` manifest section, flagging NFS/Lustre/GPFS/CIFS by parsing mount tables without blocking on `statvfs`/`df`/`stat`). The resource watcher samples system-wide available memory, load average, and Linux node iowait (`resources.system_memory`/`load_average`/`system_iowait_pct`, gated by `[capture.resources].system_metrics`, default `true`; `system_iowait_pct` is node-wide and indicative only). Added `capture.subprocesses_enabled` and `capture.file_provenance_available` manifest flags.
- **Citation and Zenodo concept DOI metadata.** Added `.zenodo.json`, `NOTICE` (Apache-2.0 attribution), and updated `CITATION.cff` (author ORCID `0000-0002-0326-4752`, affiliation `University of Rhode Island`, `version`, and live Zenodo concept DOI `10.5281/zenodo.20801582`), plus matching DOI/citation metadata across `pubrun cite` (all styles), `README.md` (with a Zenodo DOI badge), `docs/research-use.md`, and `docs/cli.md`. No `preferred-citation`/paper reference is added (no peer-reviewed paper exists yet). A citation consistency test guards author, DOI, and version alignment across all citation surfaces and rejects placeholder DOIs.
- **`pubrun init` command**: Creates `.pubrun.toml` and prints getting-started guidance.
- **Process-tree resource capture**: `[capture.resources].scope = "tree"` sums RSS/CPU across all child processes (Linux `/proc` walk, macOS `ps`-based tree walk).
- **Phase-scoped profiling**: `[capture.profiling].enabled = true` profiles `pubrun.phase()` blocks via `cProfile` or `yappi`, saving `profile-<phase>.prof` per phase.
- **`imported-transitive` package mode**: Records imported packages plus their recursive, cycle-safe transitive dependency closure (`src/pubrun/capture/packages.py::_resolve_transitive_closure`) with `source` and `required_by` fields.
- **Status summary line**: `pubrun status` ends with a colored summary showing run count, date range, status frequencies, and non-zero exit codes (reflecting the full run set even with `-n`).
- **`[console].non_tty_mode`**: Override capture behavior when stdout is piped or redirected.
- **`[console].jupyter_mode`**: Auto-disable console capture in Jupyter notebooks (default `"off"`).
- **`[capture.git].check_dirty`**: Skip `git status --porcelain` for faster startup on large repositories.
- **`[events].flush_interval_events`**: Buffer non-critical events (default 100) for throughput.
- **Secret scanning CI**: `gitleaks` workflow on push/PR + `.gitleaksignore`.
- **Dependency audit CI**: `pip-audit` workflow on push/PR.
- **Pre-commit framework**: gitleaks + hygiene hooks (large-file guard, whitespace, YAML/TOML check).
- **`pubrun methods --all`**: Aggregates a matching run set into one representative "Computational Methods" paragraph plus a variance note for fields that differ across runs (OS/CPU/RAM/Python/git commit/pubrun/packages), supporting the shared run filters (`-n`/`-f`/`-F`/`-s`/`-S`). Large/divergent sets print a narrowing hint to stderr clearly marked as outside the methods text (respecting `NO_COLOR`). Single-run `pubrun methods` is unchanged.
- **`pubrun.paused()` context manager**: `with pubrun.paused(): ...` suspends console tee and subprocess spy recording while output still prints and subprocesses still run. Thread-local, nestable, exception-safe; does not pause `annotate()`/`phase()` markers or resource sampling.
- **`full` import mode**: `import pubrun.full as pubrun` (or `[imports].mode = "full"`, `PUBRUN_IMPORT_MODE=full`, `pubrun run --mode full`) captures everything on import, forcing the console tee on regardless of `[console].capture_mode` while still respecting Jupyter/non-TTY safety guards. An in-code import mode overrides env/config; only `pubrun run --mode` overrides it.
- **`status`/`show --utc` flag**: Display timestamps in UTC (default remains local time; stored timestamps are always UTC epochs).
- **Capture subprocess timeouts**: `[capture.hardware].timeout` (default 10s), `[capture.resources].poll_timeout` (default 3s), and `[capture.git].timeout` (default 5s) bound hung external tools; git timeouts record `capture_state.status = "timeout"`.

### Changed
- **BREAKING: `capture_mode` default is now `"off"`.** `import pubrun` no longer wraps stdout/stderr without explicit opt-in. To restore the old behavior, add `capture_mode = "standard"` to `.pubrun.toml`. Jupyter/IPython is auto-detected and capture is suppressed.
- **BREAKING (command rename): `pubrun bug-report` -> `pubrun report-bug`, and `feedback` is now its own command.** The old `bug-report` command and its `issue` alias were removed (hard rename). Use `pubrun report-bug` (bug reports / feature requests) or `pubrun feedback` (general feedback); both open the GitHub issue tracker and print diagnostics.
- **BREAKING (`pubrun combined`): `-f` now means `--filter`, not `--force`.** For CLI consistency, `-f`/`--filter` on `combined` now filters runs (as on every other command). The force-large-file flag is now **`--force`** (long form only). Scripts relying on `combined -f` to force must switch to `combined --force`.
- **Behavior change: `pubrun.open()` no longer hashes file contents by default.** The default `[capture.file_io].level` is now `stat` (path + size + mtime/ctime), not content hashing. Hashing is opt-in via `level = "hash"`. The `data_files` record shape is unchanged; `sha256` is `null` unless the level is `hash`.
- **Behavior change: `pubrun bench` and `benchmarks/harness.py` write only a redacted result by default.** Only `benchmarks/results/pubrun-bench-<hostname-hash>-<UTC-timestamp>.redacted.json` is written by default; pass `--unredacted` (or `--out <path>` on `harness.py`) to also write the identifying `*.unredacted.json` copy for local debugging. `harness.py` default output, `pubrun bench`, and `benchmarks/run_bench.sbatch` never write a bare `*.json` (the adaptable PBS/LSF/SGE template scripts `benchmarks/submit_bench_{pbs,lsf,sge}.sh` currently pass `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`, writing a gitignored unredacted bare `.json` alongside the default `.redacted.json`).
- **Benchmark result JSON uses compact schema `pubrun-benchmark/5`.** Removes structural redundancy with zero analytical data loss so redacted results (~38 KB for a default run) fit GitHub's ~65 KB issue-body cap: static descriptors live once in `scenario_defs` (removing the old top-level `scenarios` alias), each pass stores only `timings`/`failures`/`skipped` maps with raw timings rounded to 6 decimal places, derived stats are recomputed on read by `aggregate.py` (which still reads older `/2`, `/3`, and `/4` files with identical output), and both `generated_utc` and `generated_local` are recorded. A non-fatal warning prints if a redacted file exceeds the GitHub issue-body budget.
- **CI test suites run in random order with `pytest-randomly`.** Every `pytest` command in `.github/workflows/ci.yml` passes `-p randomly` without a fixed seed and prints `Using --randomly-seed=<N>` for local reproduction (`python -m pytest -p randomly --randomly-seed=<N>`). Local and `tox` runs keep deterministic order via `addopts = "-p no:randomly"` in `pyproject.toml`.
- **Full-package 3-platform static type checking (`mypy`) repaired and gated in CI.** Fixed the duplicate-module import in `src/pubrun/__main__.py` (preventing `pubrun report-bug` from loading `pubrun` twice) and type errors in `src/pubrun/__main__.py`, `src/pubrun/tui/widgets/actions.py`, `src/pubrun/tui/widgets/diff.py`, and `src/pubrun/report/reproducibility.py`. `mypy` now checks every module of the `pubrun` package with no `ignore_errors` exemptions in `pyproject.toml`, and the blocking Linux Python 3.12 CI `typecheck` job runs `mypy` for Linux plus `--platform win32` and `--platform darwin`.
- **Testable entry points.** `pubrun.__main__.main()` accepts an optional argument list without modifying `sys.argv`, and `print_report` and `print_resources_report` in `pubrun.report.diagnostics` accept a keyword-only `out` stream and raise `DiagnosticsError` instead of exiting the process. Output and exit codes are unchanged, except `pubrun --no-color --info` now includes `--no-color` in its printed invocation fields.
- **Pytest coverage is opt-in, `tox` is repaired, and CI gates additional suites and builds.** Removed unconditional `--cov` flags from `pyproject.toml` `addopts`, registered the `slow` marker, and updated `tox.ini` for tox 4 (`extras = dev`). CI enforces a 78% coverage floor on `ubuntu-latest` Python 3.12, runs numbered example smoke tests across the matrix, and adds `extra-suites`, `no-tui`, and `packaging` (sdist/wheel round-trip and build-stamped commit verification) jobs.
- **`pubrun diff --basic`/`--standard` are concise, and `pubrun diff` accepts standard run filters.** `--basic` shows only high-signal user-facing differences (script/argv, packages, python, git, config); `--standard` summarizes list sections (such as `subprocesses.count` and `subprocesses.by_command`) and deduplicates `command_line`/`rerun_command` (shown at `--deep`); `--deep` is unchanged. Added `pubrun diff --table` for a compact aligned table. `pubrun diff` also accepts `-f`/`--filter`, `-F`/`--not-filter`, `-s`/`--status`, `-S`/`--not-status`, `--older-than`, and `--exit-code` when auto-selecting runs, and corrects the doc claim that `--basic` was default (`--standard` is default).
- **Normalized CLI output prefixes and alphabetized `-h` command list.** Unified status prefixes to `[INFO ]` (green), `[ OK  ]` (green), `[WARN ]` (yellow), `[ERROR]` (red), `[DEBUG]` (light blue, silent unless `PUBRUN_DEBUG`), and `[FAIL ]` via one central helper (color is optional reinforcement, never dimmed, suppressed under `NO_COLOR`/`--no-color`/non-TTY). Alphabetized the `pubrun -h` command list.
- **`pubrun res` shows a comprehensive resource summary.** Surfaces process-tree RSS, system available memory (start + lowest), load average, node iowait (labeled indicative-only), and per-process `/proc/self/io` byte volume when captured; `pubrun cpu`/`mem` remain single-metric.
- **License changed from BSD-3-Clause to Apache-2.0 and package metadata aligned.** Relicensed under Apache-2.0 (`LICENSE`, `NOTICE`, `pubrun.__license__ = "Apache-2.0"`, copyright span 2007-2026 preserved, author email `gfariello@fariel.com`). Legal, copyright, and citation surfaces (`LICENSE`, `NOTICE`, `__copyright__`, README copyright, `pubrun cite`, generated methods report, `CITATION.cff`, PyPI author) consistently use **Gabriele Fariello**.
- **`pubrun cite` and generated methods citation corrected.** Cite the software itself (`[Computer software]`, repository URL, version-aware, live Zenodo concept DOI `10.5281/zenodo.20801582`) with one consistent title across all surfaces instead of a premature, unpublished reference.
- **`pubrun --version` prints the required NOTICE attribution line.**
- **Import-mode documentation accuracy.** Clarified across README, `functional_spec.md`, `api.md`, and `auto`/`noauto` docstrings that import modes only permit the console tee (`[console].capture_mode` defaults to `"off"` in every mode), background resource monitoring runs in every mode while active, and removed a stale `pubrun.quiet` reference in the `noauto` docstring (the mode is `noconsole`).
- **Hardware detection deferred to background thread**: Import/startup is ~200-500ms faster; startup manifests show `pending` until the thread completes.
- **Event stream buffering**: Non-critical events buffer (default 100 events) before flushing; critical events (annotations, phases) still flush immediately.
- **Default config and regex caching**: `load_default_config()` cached at module level; redaction regexes compiled once.
- **Console tee timestamps**: Computed once per `write()` call, not per line.
- **Script hash gated by size**: Files >= 1MB skip SHA-256 at startup.

### Deprecated
- **`--show-config` is deprecated in favor of `pubrun show default config`.** It still works (prints built-in defaults) and emits a one-line deprecation notice to stderr; hidden from `--help` and slated for removal in a future release. Also corrected `--info` help text so it no longer claims to list detected config files.
- **`core.profile` (and `PUBRUN_PROFILE`, `start(profile=)`, and the TUI "Profile Mode" selector) is deprecated and inert.** `profile` was never wired to any capture engine, so setting it had no effect on capture. It remains accepted for backward compatibility, records a deprecation notice in `config.notices` (surfaced by `pubrun status`, `pubrun inspect`, and `pubrun show`) when set to a non-default value, and may be removed in a future release. To control capture depth, set the specific `capture.*` keys (such as `[capture.hardware].depth` and `[capture.packages].mode`). Wiring `profile` to real capture tiers was considered and declined; `core.profile` remains deprecated and inert.

### Fixed
- **`pubrun inspect` and `pubrun show` Data Files badges require a non-empty digest value before labeling a file `verified`.** Display classification now delegates to the shared file-evidence classifier so digestless records render as `metadata-only` (or `path-only` when `evidence_strength` is `path_only`), and legacy records with only an `md5` digest render as `verified` with a sanitized `md5:<prefix>` digest.
- **Methods reports no longer count a file record without a digest value as independently verified.** `methods.md`, `methods.tex`, and `pubrun methods` now use the same file-evidence classifier as `pubrun inspect`, counting digestless records as path/stat metadata only and legacy `md5`-only records as verified.
- **`pubrun run --mode <mode>` overrides explicit in-code `import pubrun.<mode>` imports.** The wrapper now sets `PUBRUN_RUN_MODE_OVERRIDE` alongside `PUBRUN_IMPORT_MODE`, taking precedence ahead of explicit submodule imports, recording `"cli:pubrun run --mode"` as manifest provenance, and avoiding spurious conflicts under `[imports].on_conflict = "error"`. Setting `PUBRUN_IMPORT_MODE` alone still yields to explicit in-code submodule imports.
- **Manifest schema declares every import-mode behavior flag.** `pubrun_imports.selected_behavior` in `schemas/manifest.schema.json` now declares `patch_subprocesses`, `patch_console`, `signal_hooks`, and `force_console` alongside `auto_start` and `global_hooks`, and rejects undeclared flags (older manifests with only `auto_start` and `global_hooks` still validate).
- **SIGTERM or SIGHUP no longer hangs the process when arriving while `pubrun` holds an internal lock.** During lethal-signal finalization, `pubrun` waits a bounded time for internal locks and falls back to lock-free completion, and reading recorded signals no longer waits on a lock held by the interrupted main thread, so runs finalize cleanly as `interrupted` and exit.
- **`pubrun ui` run details pane handles null or plain-string `git.remote_url` and escapes Git markup.** Non-object `git` sections or null/string `git.remote_url` no longer close the TUI; commit hashes, branch names, remote URLs, and working directories are escaped so bracketed text and `[REDACTED]` markers render literally.
- **`pubrun ui` Archive action reports errors instead of closing the TUI or returning silently.** Failure to create the `archive` folder or archiving a removed run directory now displays an error notification and keeps the TUI running.
- **`pubrun ui` Save Settings writes valid TOML for control characters and non-BMP characters.** Strings and lists with newlines, control characters, or emoji now serialize as valid TOML that `pubrun` reloads cleanly.
- **Live `python -m <package>` runs are no longer closed out as crashed or deleted by `pubrun clean`.** Liveness checks treat `__main__` as too generic to match by script name and resolve liveness by process start time.
- **`pubrun --create-config` handles closed stdin cleanly without a traceback.** Prints `Configuration abandoned.` and exits 1 instead of raising `EOFError`.
- **Redacted `sys.argv` values are no longer recorded in `invocation.inputs`.** Input discovery in `get_invocation()` runs after `redact_argv()` and skips arguments changed by redaction, keeping secret flag paths out of `invocation.inputs` and MD5 warnings.
- **Hyphenated prefixed API keys (such as `sk-proj-...`) are redacted in environment and argument values.** Value heuristics in `redaction.py` now match prefixed keys containing hyphens and underscores.
- **A `pathlib.Path` entry in `sys.argv` no longer fails invocation capture.** Removed the unused pre-redaction `rerun_command` block in `get_invocation()`, stringified `sys.argv` entries during input discovery, and ensured `redact_argv()` returns strings even when `argv_enabled` is false.
- **Unknown `[capture.profiling].backend` values log a warning instead of failing silently.** `phase.__enter__()` raises `ValueError("unknown backend")` inside its guarded profiling block so unsupported backends log the documented warning and skip profiling.
- **Unwaited `subprocess.Popen` children record observable exit codes and report unobserved exits as `"partial"` instead of `"complete"`.** `SubprocessSpy` hooks `subprocess.Popen.__del__` lock-free and performs a non-blocking poll at finalization, recording real `exit_code` (`"complete"` for 0, `"failed"` for nonzero) when observable and `exit_code: null`, `ended_at_utc: null`, `capture_state.status: "partial"` when unobserved.
- **`workload_seconds` no longer includes a background manifest refresh write.** `Run._finalize_state` records the workload-end anchor before waiting on `_run_lock`, attributing any in-flight hardware-refresh wait to `finalization_overhead_seconds` instead (covered by regression tests for both `stop()` and `atexit`).
- **Hardware, host, and filesystem capture no longer fails under `import pubrun.auto`, `pubrun.full`, `pubrun.nopatch`, or `pubrun.noconsole`.** Fixed the `ImportError: cannot import name '_run_lock'` failure in `pubrun-hw` and the bug where `[capture.hardware].depth = "off"` disabled tracking under those mode imports; covered by a regression test across all six mode modules and plain `import pubrun`.
- **`[imports].on_conflict` set in `./.config/pubrun/config.toml` or the user config file is no longer ignored.** Now read from the same files in the same order as `[imports].mode`.
- **Calls made with no active run no longer resolve full configuration on every call.** `annotate()`, `phase()`, `report()`, `artifact()`, `register_file()`, `register_input()`, and `register_output()` cache `[events].on_inactive_annotate` and reload only when config files, working directory, or user config directory change (cutting inactive `phase()` from ~114 us to ~22 us on the reference machine); malformed config files are reported once per change.
- **Minimal research workflow example no longer leaves `outputs/` in the caller's working directory.** `examples/minimal-research-workflow/analysis.py` writes `synthetic_data.csv` and `summary.json` under `outputs/` next to the script (gitignored) and adds `--output-dir <path>`.
- **Citation metadata and repository hygiene correction.** Cleaned up residual placeholder DOI tokens and venue-specific phrasing in historical plan records; live citation surfaces (`pubrun cite`, `CITATION.cff`, `README.md`) emit an honest software citation with no paper claim.
- **Startup manifest no longer emits an empty `console` section.** Writes the resolved `capture_mode` with `capture_state.status = "pending"` at startup and `"complete"` at finalization (covered by a regression test).
- **Manifest schema reconciled with emitted manifests and enforced as a hard test gate.** `schemas/manifest.schema.json` now covers `config.notices`, `imported-transitive` and `package_record.required_by`, transient `pending` and `timeout` capture states, root `filesystem`, `capture` enable flags, the full `host` section (with string `hostname`), `packages.records[].source`, `python` env-classification fields, and `resources` system/tree metrics. `docs/manifest.md` matches field-for-field, and `tests/test_manifest_schema.py` validates freshly generated manifests across variants (default, profile-notice, console-on, tree-scope, startup, and `imported-transitive`) as a hard gate via the dev-only `jsonschema` dependency.
- **`import pubrun.report.<submodule>` no longer breaks after selecting an import mode.** Mode modules and deferred `__init__` keep `pubrun.report` as the callable subpackage (`CallableModule`) instead of shadowing it with a plain function; regression tests cover every import mode and guard against subpackage shadowing.
- **`pubrun resources` works as the documented alias of `pubrun res`.** Registered across the subparser, dispatch, and pre-parser; removed dead unreachable `monitor`/`chart`/`stats` dispatch strings.
- **Honest HPC hydration documentation.** Corrected README and docs to state that `PUBRUN_META_REF` provides report-time hydration rather than automatically suppressing child capture; suppress heavy engines explicitly via `capture.hardware.depth = "off"` and `capture.packages.mode = "off"`. (`core.profile` is deprecated and inert.)
- **macOS RSS**: Reverted from `resource.getrusage` (peak only) to `ps -o rss=` (current RSS) for accurate polling; tree mode uses `ps -eo pid,ppid,rss`.
- **`start()` race condition**: Double-checked locking prevents concurrent threads from creating duplicate `Run` instances.
- **`ProvenanceFileProxy`**: Uses incremental streamed hashing for read-mode files (avoiding redundant re-reads); added `write()`/`writelines()` support for write-mode hash accuracy.
- **Hardware manifest staleness**: Background thread rewrites the startup manifest after hardware data is collected.
- **Event stream serialization errors**: Non-serializable payloads log at warning level (not debug).
- **`SubprocessSpy` records**: Saved before clearing and cleared on uninstall to prevent cross-run leakage.
- **Event stream migration**: Guarded emit after failed directory migration.
- **Orphaned profilers**: Disabled in `_finalize_state()` if a phase was entered without exiting.
- **`yappi` concurrent guard**: Nested/concurrent phases with `yappi` log a warning and skip.

#### Other fixes
- **Namespaced import-mode aliases expose the full public API.** `import pubrun.auto/noauto/nopatch/noconsole/minimal as pubrun` now match the full top-level `pubrun` symbol surface (including `pubrun.print`, `pubrun.open`, `pubrun.report`, `pubrun.artifact`, `pubrun.subprocess`, and `pubrun.popen`), guarded by a parity regression test.

#### Edge-case / failure-mode hardening
- **Status reader tolerance**: A single malformed, truncated, hand-edited, or foreign-version `manifest.json`/`.pubrun.lock` (non-numeric `started_at_utc`, out-of-range/NaN epoch, non-dict `signals_received`, non-string `argv`) no longer crashes `pubrun status`/`show`/`inspect`; the bad run is shown degraded and the rest still list. Numeric fields are coerced at a single choke point; `scan_runs` has a per-run backstop.
- **PID liveness**: `is_pid_alive` rejects `None`/non-positive/overflow PIDs before `os.kill` (which would signal a process group for `pid <= 0`); same-process script matching trusts only an exact basename (substring-only or generic tokens like `python`/`-c` fall through to timing), correcting recycled-PID false positives; the conservative "assume alive when start time is unreadable" default is preserved to avoid false "crashed" verdicts on macOS.
- **Package capture**: A distribution with a missing/`None` name no longer crashes package capture (and no longer demotes the run to ghost mode).
- **Manual subprocess records**: `pubrun.subprocess.run`/`Popen`/`popen` records are bounded by `[capture.subprocesses].max_tracked_commands` (preventing unbounded memory growth in tight loops); a failed `run()` invocation is recorded before re-raising.
- **Config tolerance**: A malformed `.pubrun.toml`/user config is warned-and-skipped instead of crashing CLI commands.
- **Resource watcher**: Only unreadable polls (errors/timeouts) count toward the consecutive-failure self-abort; a legitimate RSS of 0 no longer permanently disables telemetry.
- **`sys.excepthook` restore**: Only restores `pubrun`'s wrapper if it is still installed, so a third party's later-installed hook is not clobbered.
- **Console tee**: Passthrough tolerates `OSError`/`ValueError` from the original stream (such as a closed stdout), matching plain-stream behavior.
- **`show --export json`**: Tolerates flat-key prefix collisions (such as a package named `numpy.core`) instead of raising.
- **Diff correctness**: Guards non-list `environment.variables`/`packages.records`; list diffs use a type-tagged comparison so `bool`/`int` (`True`/`1`) no longer alias.
- **Combined logs**: Interleave uses a stable secondary sort key so untimestamped/partial lines keep their original position instead of being hoisted to the top.
- **`pubrun.print`**: Tolerates `sep=None`/`end=None` (accepted by the builtin `print`).
- **`pubrun status` timestamps**: Rendered in local time by default with an explicit zone, resolving the prior status-vs-diff inconsistency; event counts shown from the size estimate are labeled `~N (est.)`.

### Documentation
- **Synced benchmark-intake documentation and Issue Form with live `pubrun bench` behavior.** Updated `docs/cli.md`, `benchmarks/README.md`, `.github/ISSUE_TEMPLATE/benchmark-result.yml`, `.github/workflows/benchmark-intake.yml`, and `pubrun bench --help` to reflect the redacted-only default, `--unredacted` / `--contribute` / `--prepare-submission` / `--wait-timeout` flags, main-repo (`fariello/pubrun`) targeting, and the local-pull collection workflow (`benchmarks/pull_submissions.py`). Fixed a stale `Code of Conduct` link in `CONTRIBUTING.md`.
- **Adoption bridges, an examples ladder, and deep-page positioning (no behavior change).** Added an "Is pubrun for me?" section and an examples ladder to `README.md`, reframed `docs/research-use.md` around high-stakes scientific and ML provenance (removing unverifiable download/adopter counts), and framed `docs/hpc.md` around a laptop-to-cluster workflow with a "Where pubrun fits" note positioning `pubrun` as a complement to MLflow, Weights and Biases, and DVC. Removed em and en dashes from those three files per house style.
- **Reframed the README lead to the trustworthy-ML register (no behavior change).** Leads with reproducible, auditable runs via automatic provenance, environment capture, and run-to-run comparison from a single `import pubrun`, clearly states that `pubrun` is a reproducibility/provenance component used inside an ML pipeline (not an orchestrator, scheduler, or serving platform), elevates laptop-to-cluster scaling, and adds a "Built to be Trustworthy" section highlighting cross-platform CI (Python 3.8 to 3.14), the schema-validated manifest contract, zero runtime dependencies, and a real changelog.

## [1.3.1] - 2026-06-24

### Changed
- **Human-Friendly Timestamps**: Started time in diagnostic reports is now formatted as `YYYY-MM-DD HH:MM:SS` (UTC), and elapsed duration is formatted as `Xd HH:MM:SS` (matching the status list format).
- **Inline Exit Codes**: Diagnostic reports now display the process exit code inline with the run status, colored in bold green for successful runs (0) and bold red for failures (non-zero), eliminating the redundant separate line.
- **Resource Utilization Charts x-axis Tickmarks**: CPU and memory utilization history charts now display vertical tickmarks and evenly distributed elapsed duration values (space-permitting) aligned with x-axis ticks. The peak values are cleanly moved to the chart titles.

## [1.3.0] - 2026-06-23

### Added
- **ASCII/Unicode Resource Charts**: Added the `resources` subcommand to print terminal CPU and memory utilization graphs over the lifecycle of a run.
- **Standalone Resource Commands**: Added standalone `cpu`, `mem`, and `res` commands to view specific or combined utilization charts.
- **Custom Chart Width**: Added `-w`/`--width` options for resource monitoring commands to customize terminal column widths.
- **Colorized Diagnostics Telemetry**: The `pbr show` command output is now colorized by default, respecting the `--no-color` CLI option and the `NO_COLOR` environment variable.
- **Trailing Time Filter**: Added the `-l`/`--last` option to the resource commands to filter and display telemetry only for a specific trailing duration.
- **Dyslexic-Friendly CLI Syntax**: Implemented command preprocessor in `main()` to support placing the run ID before subcommands (e.g., `pubrun 16528343 cpu`).

### Changed
- **Renamed Diagnostics Command**: Renamed the diagnostics command from `report` to `show` with support for optional positional sections (`logs`, `env`, `packages`) and parameter shifting. The old `report` command remains hidden for backward compatibility.
- **Alphabetical CLI Subcommands**: Alphabetized subcommand help blocks in `--help` output.
- **Dynamic Chart Width**: Utilization charts now dynamically adjust their width to match the terminal size.
- **Human-Readable X-Axis Labels**: Replaced raw seconds on the x-axis with human-readable elapsed durations, including custom start/end time markers (`Start: 0s` / `End: Xs`) and proportional axis tick marks.
- **Peak Data Center-Labels**: Displays the peak data value centered along the timeline axis when space permits.
- **Dropped Obsolete Aliases**: Removed `resources`, `monitor`, `chart`, `stats` aliases from `res` subparser to simplify command listings.

### Fixed
- **Python 3.8 Compatibility**: Fixed PEP 585 subscripted type hints and Path-like subprocess arguments in tests to ensure compatibility with Python 3.8.
- **Nested Command Aliases Preprocessing**: Automatically collapse consecutive resources aliases in `sys.argv` to prevent argument parsing errors.
- **Graph Decimation / Data Loss**: Replaced index-based downsampling in `draw_ascii_chart` with robust time-based binning using maximum values (default) or mean values (when `--average` is set) to prevent telemetry data spikes from being lost.
- **Crashed Run Report Suggestions**: Excluded crashed runs from suggestion listing.

## [1.2.0] - 2026-06-22

### Added
- **Minimal Research Workflow Example**: Added a complete, self-contained mock research regression fit script under `examples/minimal-research-workflow/analysis.py`, along with detailed reviewer notes in the README, manifest excerpts, and artifact notes.
- **Example Automated Smoke Test**: Added a pytest smoke test under `tests/test_examples.py` to automatically run and validate the research workflow execution and event outputs.
- **UI Command Aliases**: Supported `tui` and `gui` aliases for the canonical `pubrun ui` subcommand.
- **Research Use Documentation**: Created `docs/research-use.md` outlining project adoption statistics and guidelines for public example workflows.
- **API Audit Documentation**: Documented custom reports/artifacts API (`pubrun.report` and `pubrun.artifact`) in `docs/api.md`.
- **Citation Guidelines**: Added a dedicated `Citation` section in `README.md` and updated `CITATION.cff` with placeholders for future Zenodo concept and version-specific DOIs.
- **Direct Bug and Feature Reporting CLI**: Added a built-in `bug-report` CLI command (with aliases `feedback` and `issue`) to print system diagnostics and open the GitHub issues form.
- **Enforced Test Coverage**: Configured `pytest-cov` settings in `pyproject.toml` to automatically gather and report code coverage during test runs.

### Fixed
- **Recursive Pytest Subprocesses**: Defused a latent CI time bomb where `--run-tests` would run the entire test suite recursively by mocking pytest invocation in tests.
- **Tested Clean Interactive Prompts**: Implemented comprehensive unit tests validating `pubrun clean` interactive selection parsing and confirmation flows.
- **Critical Event Capping**: Validated event stream capping and verified that `max_tracked_events=0` correctly defaults the critical event cap to 10,000.
- **Eliminated Brittle Sleep Timings**: Refactored resource watcher thread tests to use dynamic polling deadlines rather than fixed sleep delays.

## [1.1.2] - 2026-06-22

### Fixed
- **Windows GHA runner compatibility**: Skip process command-line mismatch tests on systems where process command-line retrieval via `wmic` is deprecated or unavailable, falling back correctly to start-time checks.

## [1.1.1] - 2026-06-21

### Changed
- **CLI diff default depth**: Changed default diff depth from `--basic` to `--standard` to align with the `report` subcommand and provide standard telemetry comparison by default.

### Fixed
- **CLI diff formatting**: Fixed a bug where the `depth` parameter was not passed to `print_diff` in the `diff` CLI command, causing it to fall back to basic formatting instead of standard/deep list formatting.

## [1.1.0] - 2026-06-21

### Added
- **Smarter array/list diffing**: Depth-aware array comparisons in `pubrun diff`. Under `--basic` depth, outputs additions and deletions as standard multi-line items. Under `--standard` and `--deep` depths, outputs full lists on two lines with inline green (`+`), red (`-`), and yellow (`~`) ANSI colors highlighting added, removed, and rearranged elements.
- **Epoch time formatting**: Formats epoch timestamps into human-readable local date strings in diff output.
- **Rerun Command Reconstruction**: Rebuilds run commands from active/crashed lock files.
- **CLI error standardization**: CLI error prefix standardized to `[ERRO]` and warning prefix to `[WARN]`.
- **Exclude volatile timestamps**: Exclude volatile execution timestamps in basic/standard diff.
- **Not-filters**: Implemented exclusions filtering via `-S`/`--not-status` and `-F`/`--not-filter`.

### Fixed
- **Windows CI compatibility**: Made rerun tests platform-independent to ensure Windows CI compatibility.

## [1.0.3] - 2026-06-21

### Added
- **Explicit Telemetry and Provenance API**: Added explicit file, output, and provenance tracking APIs (`e301c44`).

### Fixed
- **Subparser error handling**: Improved CLI subparser error handling to display subcommand usage on invalid arguments (`2c0ee37`).
- **Position-independent `--no-color`**: Accepted `--no-color` in any position on the CLI (`fe99380`).
- **Windows newline test assertion**: Fixed Windows newline handling in `test_explicit_api.py` (`98058ec`).

## [1.0.2] - 2026-06-20

### Fixed
- **Remote-host liveness checks**: Improved liveness checks for remote-host runs using lock age (`a015c14`).

## [1.0.1] - 2026-06-20

### Fixed
- **Crashed-run timing and elapsed formatting**: Set crashed-run timing fields to `None` and implemented `HH:MM:SS` elapsed duration formatting (`88fe38b`).

## [1.0.0] - 2026-06-19

### Added

- **Interactive TUI Manager (`pubrun tui`)**: Launch a full terminal user interface manager to browse, filter, search, inspect, and clean up historical runs interactively.
- **TUI Optional Dependencies**: Support textual/rich optional installs via `pip install "pubrun[tui]"`. Core package remains zero-dependency.
- **`pubrun combined` CLI Command**: Interleave stdout and stderr logs chronologically across one or more runs using prepended timestamps. Enforces safety thresholds (warns at 250 MB, aborts at 500 MB unless `--force` is used). Falls back to sequential concatenation for logs without timestamps.
- **Value-Scanning Redaction Heuristics**: Recursively inspects nested JSON environment values and CLI arguments to redact connection string passwords, OpenAI keys (`sk-...`), and bearer authorization tokens.
- **Timestamped Console Capture (`standard` mode)**: Console log files recorded in `standard` and `deep` capture modes now prepend ISO 8601 timestamps to each line.

### Fixed

- **EventStream Directory Migration**: Safely migrate open EventStream file handles when output_dir changes mid-execution.
- **`script_name` Stem Sanitization**: Regex sanitization of script name to filter out invalid filesystem characters on Windows/Unix.
- **ResourceWatcher Concurrency Lock**: Added threading Lock to resource watcher metric updates to prevent race conditions on free-threaded Python 3.13+.
- **SubprocessSpy TOCTOU check**: Protected max_records length verification under lock to resolve race conditions.
- **Console Interceptor Migration Leak**: Atomic log file assignment prevents descriptor leaks or corrupted state on path migration failure.
- **Clock Skew Defense**: Capped negative age parameters to `0.0` in `_format_age` to handle skewed system time cleanly.

### Tests

- **Signal Test Hardening**: Replaced brittle signal tests that send OS signals asynchronously using `os.kill` with direct, deterministic signal capture handler invocations.
- **ResourceWatcher Join Coverage**: Added test verifying that `stop()` successfully joins the resource watcher thread.
- **`report/templates.py` Unit Tests**: Added unit tests for academic paragraph generation templates and LaTeX/Markdown formatting.
- **`pubrun combined` Integration Tests**: Added comprehensive test suite for log interleaving, size warning prompts, basic-mode fallback, and output options.
- Dedicated unit tests for `writer.py` (`_atomic_json_write` and `ArtifactWriter`).
- Unit tests for private status formatting helpers in `status.py`.
- Regression tests for `EventStream` migration, critical event throttling capping, lethal signal finalization, and macOS `disable_spy()` hardware probe wrapping.

## [0.3.0] - 2026-06-04

### Added

- **Import modes**: Namespaced import presets for controlling import-time behavior:
  - `import pubrun.noauto as pubrun` — Load API without auto-starting.
  - `import pubrun.nopatch as pubrun` — Auto-start without global hooks (subprocess spy, console tee, signals).
  - `import pubrun.quiet as pubrun` — API only, no auto-start, no hooks.
  - `import pubrun.auto as pubrun` — Explicit auto mode (same as plain `import pubrun`).
- **`pubrun run` CLI command**: Spawn a child process with `PUBRUN_IMPORT_MODE` set. Useful for CI, shell scripts, Slurm, and HPC workflows where source code should remain unchanged. Returns the child's exit code.
- **Import provenance metadata**: Manifest now includes a `pubrun_imports` section recording the selected mode, source, timestamp, conflict count, and caller provenance. Lock files include compact `import_mode` and `import_selected_by` fields.
- **Import conflict detection**: When multiple imports request different modes, pubrun warns by default (configurable to `error` or `ignore` via `[imports].on_conflict` or `PUBRUN_IMPORT_CONFLICT`).
- **`[imports]` config section**: New configuration section with `mode`, `on_conflict`, `record_provenance`, `provenance_depth`, `provenance_path_mode`, and `max_requests`.
- **`PUBRUN_IMPORT_MODE` environment variable**: Canonical way to set import mode from the shell. Takes precedence over config files.
- **`broken pipe` status display**: `pubrun status` now shows `broken pipe` (yellow) instead of `completed` when a run received SIGPIPE during execution. Surfaces cases where a script terminated early because a downstream reader closed. The manifest outcome remains `"completed"` and the exit code is unchanged — this is a display-level enhancement only.

### Changed

- **Internal architecture**: Public API moved from `__init__.py` to `pubrun.core`. The root package is now a thin router that delegates to `core.py`. This is an internal refactor — all public symbols remain at `pubrun.*`.
- **Boot sequence centralized**: Import-mode resolution moved to `_config_boot.py` and `_bootstrap.py`. The old inline logic in `__init__.py` is replaced by `_execute_boot_sequence()`.

### Security

- **Run directory permissions (umask)**: Directories are now created with `umask(0o077)` active, preventing a brief world-readable window between mkdir and chmod on shared systems.
- **Lock file argv redaction**: Command-line arguments in `.pubrun.lock` are now passed through `redact_argv()` before writing, preventing secrets from being persisted to disk.
- **Signal forwarding in `pubrun run`**: SIGTERM is now forwarded to the child process, preventing orphaned children when the wrapper is killed by CI/Slurm.

### Fixed

- **`global_hooks` enforcement**: `nopatch` and `quiet` modes now genuinely suppress global hooks (subprocess spy, console tee, signal handlers). Previously the mode was recorded in metadata but hooks were still installed. The tracker now reads `global_hooks` from the bootstrap state and skips hook installation when `false`.
- **SIGPIPE capture**: Added `SIGPIPE` to the signal capture target list. Previously the signal handler did not intercept SIGPIPE, making the broken pipe status feature non-functional.
- **BrokenPipeError in console tee**: `TqdmSafeTee.write()` and `flush()` now catch `BrokenPipeError` when the downstream pipe is closed (e.g., `script.py | head`). Previously this crashed the script before the manifest could be written.
- **Critical event double-counting**: Critical events (annotations, phases) no longer consume the general event budget. Previously they were counted against both the critical cap and the regular cap.
- **Negative returncode in `pubrun run`**: Child processes killed by a signal now return the conventional `128+N` exit code instead of a raw negative value.
- **Temp file cleanup**: `_atomic_json_write` now removes the `.tmp` file if `os.replace()` fails.
- **Event stream close race**: `self._file = None` is now set inside the lock in `EventStream.close()`.
- **start() TOCTOU**: The lock in `start()` now covers both `get_current_run()` and `ref_count` increment atomically.
- **ResourceWatcher stop safety**: `stop()` now checks `is_alive()` after join and skips the final poll if the thread is still stuck.

### Tests

- Added 65 new tests covering mode definitions, config boot resolver, bootstrap state, conflict detection (warn/error/ignore), namespaced import modes (subprocess tests), `pubrun run` wrapper (including env var assertion, signal-killed exit codes, permission errors), import metadata in manifest/lock file, hook suppression verification, broken pipe status classification (unit + real SIGPIPE integration test), BrokenPipeError unit tests, lock file argv redaction, umask directory permissions, and temp file cleanup. Total: 473 tests.
- Replaced fixed `time.sleep()` with polling loops in resource watcher tests to eliminate CI flakes.

---

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

---

[README](https://github.com/fariello/pubrun/blob/main/README.md) | [Architecture](https://github.com/fariello/pubrun/blob/main/docs/architecture.md) | [Functional Spec](https://github.com/fariello/pubrun/blob/main/docs/functional_spec.md) | [API](https://github.com/fariello/pubrun/blob/main/docs/api.md) | [CLI](https://github.com/fariello/pubrun/blob/main/docs/cli.md) | [Configuration](https://github.com/fariello/pubrun/blob/main/docs/configuration.md) | [Manifest](https://github.com/fariello/pubrun/blob/main/docs/manifest.md) | [Performance](https://github.com/fariello/pubrun/blob/main/docs/performance.md) | [Research Use](https://github.com/fariello/pubrun/blob/main/docs/research-use.md) | [HPC](https://github.com/fariello/pubrun/blob/main/docs/hpc.md) | [Changelog](https://github.com/fariello/pubrun/blob/main/CHANGELOG.md)
