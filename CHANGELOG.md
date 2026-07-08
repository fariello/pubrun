[README](https://github.com/fariello/pubrun/blob/main/README.md) | [Architecture](https://github.com/fariello/pubrun/blob/main/docs/architecture.md) | [Functional Spec](https://github.com/fariello/pubrun/blob/main/docs/functional_spec.md) | [API](https://github.com/fariello/pubrun/blob/main/docs/api.md) | [CLI](https://github.com/fariello/pubrun/blob/main/docs/cli.md) | [Configuration](https://github.com/fariello/pubrun/blob/main/docs/configuration.md) | [Manifest](https://github.com/fariello/pubrun/blob/main/docs/manifest.md) | [Performance](https://github.com/fariello/pubrun/blob/main/docs/performance.md) | [Research Use](https://github.com/fariello/pubrun/blob/main/docs/research-use.md) | [HPC](https://github.com/fariello/pubrun/blob/main/docs/hpc.md) | [Changelog](https://github.com/fariello/pubrun/blob/main/CHANGELOG.md)

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- **`pubrun diff --basic`/`--standard` are now genuinely concise.** Previously `--basic` could
  explode a subprocess-heavy run pair into 11,000+ lines and surfaced per-run volatile fields
  (`filesystem.run_dir.path`) and derived duplicates (`invocation.command_line` /
  `rerun_command`, both derived from `argv`). Now: `--basic` shows only high-signal, user-facing
  differences (script/argv, packages, python, git, config) and hides the high-volume sections;
  `--standard` **summarizes** list sections (e.g. `subprocesses.count: 300 → 302`,
  `subprocesses.by_command.bash: +2`) instead of diffing every element; a single `argv` change
  is reported once (the derived `command_line`/`rerun_command` appear only at `--deep`).
  **`--deep` output is unchanged** (full element-by-element detail). New `pubrun diff --table`
  renders a compact aligned `change / field / A → B` table (the git-style `+/-/~` inline output
  remains the default). Also fixed a stale doc claim that `--basic` was the default (it is
  `--standard`).
- **Normalized CLI output prefixes + alphabetized the `-h` command list.** All pubrun status
  lines now use a consistent, accessible vocabulary — `[INFO ]` (green), `[ OK  ]` (green),
  `[WARN ]` (yellow), `[ERROR]` (red), `[DEBUG]` (light blue, silent unless `PUBRUN_DEBUG`),
  `[FAIL ]` (self-test failures) — replacing the previous ad-hoc mix (`[*]`, `[OK]`, `[ERRO]`,
  `[WARNING]`, lowercase `[warn]`/`[info]`, `[dry run]`). One central helper now emits them;
  color is optional reinforcement (never dimmed; suppressed under `NO_COLOR`/`--no-color`/non-TTY;
  the textual label is authoritative). The `pubrun -h` command list is now alphabetical. If you
  grep pubrun output, match on the level word (e.g. `WARN`), not the exact bracket text.
- **BREAKING (command rename): `pubrun bug-report` → `pubrun report-bug`, and `feedback` is
  now its own command.** The old `bug-report` command and its `issue` alias were removed
  (hard rename). Use `pubrun report-bug` (bug reports / feature requests) or `pubrun
  feedback` (general feedback) — both open the GitHub issue tracker and print diagnostics.
- **`pubrun res` now shows a comprehensive resource summary**, not just single-process
  CPU%/RSS: it also surfaces process-tree RSS, system available memory (start + lowest),
  load average, node iowait (labeled indicative-only), and per-process I/O byte volume
  (`/proc/self/io`) — each shown only when captured. `pubrun cpu`/`mem` remain single-metric.
- **Behavior change: `pubrun.open()` no longer hashes file contents by default.** The default
  `[capture.file_io].level` is now `stat` (path + size + mtime/ctime), not content hashing.
  Hashing is opt-in via `level = "hash"`. Rationale: hashing reads every byte (expensive,
  especially over NFS) for information that file size + mtime usually already capture. The
  `data_files` record shape is unchanged; `sha256` is `null` unless the level is `hash`.
- **BREAKING (`pubrun combined`): `-f` now means `--filter`, not `--force`.** For CLI
  consistency, `-f`/`--filter` on `combined` now filters runs (as it does on every other
  command). The force-large-file flag is now **`--force`** (long form only). Scripts that
  relied on `combined -f` to force must switch to `combined --force`.
- **`pubrun diff` now accepts the standard run filters** (`-f`/`--filter`,
  `-F`/`--not-filter`, `-s`/`--status`, `-S`/`--not-status`, `--older-than`, `--exit-code`).
  When run directories are omitted, the auto-selected comparison pair is drawn from the
  matching runs; if a filter matches fewer than two runs, `diff` errors clearly instead of
  ignoring the filter. Behavior with no filters and no run directories is unchanged (still
  compares the two most recent runs).
- **License changed from BSD-3-Clause to Apache-2.0.** Now licensed under the Apache License 2.0
  (see `LICENSE` and the new `NOTICE`). Apache-2.0 requires redistributions and derivative works to
  retain the `NOTICE` file and display its attribution reasonably prominently ("Based on the original
  pubrun by Gabriele G. R. Fariello — https://github.com/fariello/pubrun"), and adds an explicit
  patent grant. Copyright holder normalized to the full legal name **Gabriele G. R. Fariello**
  (copyright span 2007–2026 preserved); author email set to gfariello@fariel.com.
- **Package metadata license fixed**: `pubrun.__license__` now reports `Apache-2.0` (was still
  `BSD-3-Clause`). Legal/copyright surfaces (`LICENSE`, `NOTICE`, `__copyright__`, README copyright)
  use the full legal name **Gabriele G. R. Fariello**; **citation** surfaces (`pubrun cite`, generated
  methods report, `CITATION.cff`, PyPI author) use the publication name **Gabriele Fariello** so
  citations aggregate with the author's existing record.
- **`pubrun cite` and generated methods citation corrected**: now cite the software itself
  (`[Computer software]`, repository URL, version-aware) instead of an unsubmitted "Journal of Open
  Source Software (In Submission)" reference; a single consistent title is used across all surfaces.
  Will switch to the peer-reviewed citation with DOI once a journal article is accepted.
- **`pubrun --version`** now prints the required NOTICE attribution line.
- **Import-mode docs accuracy**: the README "Preset Modes Behavior Matrix" (and
  `functional_spec.md`, `api.md`, and the `auto`/`noauto` docstrings) previously implied
  console wrapping is ON in `auto`/`noauto`. Corrected: a mode only *permits* the console
  tee; it is **off by default** in every mode because `[console].capture_mode` defaults to
  `"off"`. Also clarified that background resource monitoring is NOT gated by import mode
  (it runs in every mode while a run is active). Removed a stale `pubrun.quiet` reference
  in the `noauto` docstring (the mode is `noconsole`).

### Added
- **Benchmark pass tiers + uncaptured baseline pass + total wall-time.** Every `pubrun bench`
  run now begins with a **baseline (uncaptured) pass** — the workload run without pubrun — that
  warms caches and records the pubrun-absent cost floor, stored separately so it never mixes
  into overhead stats. Three tiers replace the old flat 2×30: `--quick` (baseline + 2×15),
  `--full`/default (baseline + 3×30), and new `--rigorous` (baseline + 5×50, for tight
  confidence intervals; can take many minutes). `--iterations`/`--passes` still override. The
  result JSON now records `mode`, `baseline_pass`, the baseline sweep, and `total_wall_time_s`
  (whole-invocation wall time). `--full` remains the default's clarity alias (not the heavy
  mode). `--no-baseline` skips the baseline pass.
- **TUI resource view (`pubrun ui`).** Selecting a run now populates a new **Resources** tab
  showing peak/avg/min for CPU and memory (main process, and the process tree when captured)
  plus a compact sparkline of each over the run's lifecycle — reusing the same per-sample data
  as `pubrun res`. Press `r` to jump to it; runs with no resource samples show a clear message.
  (TUI is the optional `[tui]` extra — the core library gains no dependency.)
- **Recency-index run selector.** Every command that takes a run (`show`/`report`,
  `res`/`cpu`/`mem`, `methods`, `inspect`, `rerun`, `diff`, `status`) now accepts a bare
  positive integer as a **recency index** — `1` = most recent run, `2` = second most recent,
  and so on — in addition to the existing run-id/prefix and directory-path forms. `pubrun
  status` shows the index in a leading `#` column. Resolution is additive (id-prefix and path
  behavior are unchanged); a run id being a bare small integer is effectively impossible (ids
  are timestamp+hash), and in the vanishing case one collided, pubrun refuses to guess and
  points you at the full id / path.
- **Verbose, transparent `self-check` and `meta`.** `pubrun self-check` is now **itemized by
  default**: one line per check with its `[ OK  ]`/`[WARN ]`/`[INFO ]` outcome (including the
  checks that PASSED) plus a `N checks in 0.0Xs` timing footer — instead of a bare one-line
  verdict. `--quiet`/`-q` restores the terse one-liner (for scripts/CI); `--json` now emits the
  full structured result (`checks`, `findings`, `elapsed_seconds`); `--show-suggestions` adds
  remediation detail. `--strict` still keys on WARN only. `pubrun meta` likewise itemizes each
  gathered section (hardware/python/packages/git/environment/host) with an outcome and
  per-section timing plus a total, surfacing any failed section as `[WARN ]` (the `meta.json`
  file remains the source of truth).
- **Richer `report`/`res` output + `report`/`show` flag parity.** `pubrun res` now shows
  **peak / avg / min** (computed from the per-sample `events.jsonl`) for each metric, with
  explicit `RSS (main)` / `CPU (main)` / `RSS (tree)` / `CPU (tree)` labels. **Process-tree CPU
  is now captured** (`resources.peak_tree_cpu_percent` + per-sample `tree_cpu_percent`) when
  `[capture.resources].scope = "tree"` — computed from summed CPU-time deltas across the tree
  (not a sum of instantaneous percentages), labeled "% of one core" and not clamped (may exceed
  100% on multiple cores; Linux-only). This intentionally changes the prior "child CPU excluded
  from the CPU metric" behavior, gated to tree scope. The `report`/`show` **event timeline**
  now uses a compact `YYYY-MM-DD HH:MM:SS` timestamp (local by default, `--utc` for UTC) and
  shows the oldest 10 + newest 10 events with a truncation marker above 20 (was full ISO with
  microseconds, truncating only above 40). `pubrun report` now accepts `--utc` (previously only
  `show` did — an accidental asymmetry).
- **HPC multi-scheduler benchmark submission (Slurm/PBS/LSF/SGE).** `pubrun bench` now detects
  and offers to submit to PBS/Torque, LSF, and SGE/Grid Engine in addition to Slurm (auto-detect
  order Slurm > PBS > LSF > SGE), with a new `--scheduler {auto,slurm,pbs,lsf,sge,local}` override.
  Detection is env+PATH only (no scheduler query, no network); the PBS-vs-SGE `qsub` ambiguity is
  reported and resolved with `--scheduler`. New starting-point submit scripts
  `submit_bench_pbs.sh`/`_lsf.sh`/`_sge.sh` (submit to the default queue, let the scheduler place
  the job; adapt account/queue/walltime to your site — not CI-validated against live clusters).
  Never auto-submits (same consent gate as Slurm; argv-list, no shell injection). `pubrun
  self-check` now emits an INFO nudge when you appear to be on an HPC login node, suggesting a
  compute-node `pubrun bench` for representative numbers (INFO, so it does not trip `--strict`).
- **Benchmark data quality + filesystem-health diagnostics.** Benchmark results now record
  **raw per-iteration timings** (in run order) alongside the summary stats (schema
  `pubrun-benchmark/4`), so distribution shape, warmup drift, and correct cross-submission
  pooling are recoverable. Results also capture non-identifying **environment classification**
  (`environment_kind` = venv/conda/system/virtualenv/frozen, `in_venv`, `sys_path_len`) and
  classify more paths (Python install prefix, `/dev/shm`, the I/O-baseline target) — all of
  which **survive share-redaction** so a slow/odd result stays interpretable after PII
  masking. Filesystem classification now prefers Linux `/proc/self/mountinfo` (bind/overlay
  aware) and gains a **Windows** `ctypes` fstype branch. New **diagnostic-only** live probe
  (`os.statvfs`) surfaces free space, inode counts, read-only mounts, and — crucially —
  **wedged (hung) or slow** mounts; it runs in a daemon thread with a decoupled wait budget
  (a slow-but-alive mount is captured with its measured latency, not falsely called hung) and
  is **never invoked by `import pubrun`** or the startup path. `pubrun self-check` now warns
  about hung/slow/network-backed mounts as an honest **system-wide** hazard (affects any
  script, not just pubrun). Zero new runtime dependencies.
- **Low-friction, consent-gated benchmark result submission.** After a local `pubrun bench`
  run, pubrun now **offers** to contribute the redacted result to the public
  `pubrun-benchmarks` repo. It never transmits without an explicit yes: the prompt defaults to
  No (Enter = don't send), and it tries the GitHub CLI (`gh`) → a direct GitHub Issues API call
  (stdlib `urllib`, needs a token) → printing a ready-to-paste submission, in that order. New
  `pubrun bench --submit-file <redacted.json>` submits a previously produced file without
  re-running (the "oh, I meant yes" recovery, and the HPC run-on-compute-node →
  submit-from-login-node path). New flags: `--submit-file`, `--no-submit`, `--submit-method
  {gh,http,print}`, `--gh-repo`, `--gh-token`, `--print-submission`. pubrun **never
  auto-transmits an un-redacted result** — the submit path verifies the file looks redacted
  (no hostname/username/home-path leak) and refuses otherwise. Zero new runtime dependencies.
- **Benchmark ground-truth I/O baselines.** New `io_baseline` scenarios establish reference
  floors for I/O so storage-dependent numbers are interpretable: `io-baseline-devnull`
  (write-only null sink — isolates the open/write path from storage; `NUL` on Windows),
  `io-baseline-devshm` (RAM-backed tmpfs, Linux; cleanly skipped where `/dev/shm` is absent),
  and `io-baseline-tmpdir` (the default temp filesystem). `pubrun bench` gained a `--full`
  flag (explicit alias of the default) alongside `--quick` for clarity.
- **Graded file-I/O provenance for `pubrun.open()` + per-process I/O counters.** `pubrun.open()`
  now records provenance at a configurable `[capture.file_io].level` — `none | name | stat |
  realpath | hash` (progressive). `stat` uses `fstat` on the open fd (size/mtime/ctime, ~free
  even on NFS); `realpath` adds symlink resolution (costlier on network filesystems); `hash`
  adds a SHA-256 read from the on-disk bytes at close (correct regardless of read path).
  `max_hash_bytes` caps hashing of large files. Still opt-in and per-file — pubrun never
  patches the global `open()`. Also: the resource watcher now records per-process I/O byte
  counters from Linux `/proc/self/io` (`resources.io_counters`, `system_metrics`-gated).
- **`pubrun bench` command (friendly benchmark runner + HPC submit + shareable results).**
  Runs the overhead benchmark suite locally by default; on an HPC login node with Slurm
  detected it **offers** to submit to a compute node (never submits without confirmation).
  Writes a **redacted, shareable** copy of the results by default (`--no-redact` to opt out)
  that masks hostname, OS username, and all home-directory paths while preserving the
  analysis-relevant data (CPU/GPU model, timings, versions, filesystem type, Slurm
  partition), and prints how to contribute it to the (forthcoming) public `pubrun-benchmarks`
  repository. Requires a source checkout (the benchmark tooling is not shipped in the pip
  package). The harness also gained a `--redacted-out` option and a reusable `redact_result`
  helper (deep-scan scrub of home-dir/username substrings as a safety net).
- **`pubrun self-check` and `pubrun inspect` commands (environment & run diagnosis).**
  `self-check` reports pubrun performance/config pitfalls on the current machine (network
  filesystems backing the install/output/`$TMPDIR`, low RAM, high load) plus install health
  (config validity, output-dir writability, `git` availability, Python version) — report-only.
  `inspect` diagnoses a completed run's manifest: recorded I/O/RAM/load/filesystem signals, a
  **capture-completeness assessment** (what provenance was NOT captured and how to capture more,
  with honest performance trade-offs), and a glaring banner when the inspecting host differs
  from where the run executed (HPC head-node vs compute-node). Both support
  `--show-suggestions`/`-v` (terse by default), `--json`, and `--strict` (non-zero exit on any
  warning). The findings logic is CLI-only and is **not** imported by `import pubrun`, so it
  cannot affect a host script. New [HPC & performance diagnosis](docs/hpc.md) doc.
- **Run-time I/O / environment capture (enables post-hoc diagnosis of NFS/contention).** A run now
  records the **filesystem type** of its output dir, run dir, and `$TMPDIR` (new `filesystem` manifest
  section) — flagging network filesystems (NFS/Lustre/GPFS/CIFS) that can silently inflate I/O on HPC
  clusters. Classification parses `/proc/mounts` (Linux) / the `mount` table (macOS) and **never** calls
  `statvfs`/`df`/`stat` on the target, so it cannot hang on a sick network mount. The background resource
  watcher additionally samples **system-wide available memory, load average, and (Linux) node iowait**
  (new `resources.system_memory`/`load_average`/`system_iowait_pct`), controlled by the new
  `[capture.resources].system_metrics` key (default `true`; only samples while the watcher runs). All
  reads are cheap, stdlib-only, exception-safe, and never disturb the host script. Note: `system_iowait_pct`
  is **node-wide, indicative only** (not run-scoped). Two additive manifest flags
  (`capture.subprocesses_enabled`, `capture.file_provenance_available`) let tooling distinguish "feature was
  OFF" from "on but produced no records".
- **Benchmark schema `pubrun-benchmark/3`.** The harness now captures filesystem context + Slurm allocation
  context in the `machine` block and the dynamic host state (RAM/load/iowait) at the **start of each pass**
  (`pass_results[i].pass_env`), so cross-machine/cross-node results are interpretable and a node loaded
  between passes is visible. `aggregate.py`/`plot.py` still read `/2` files.
- **Citation DOI metadata (Zenodo-ready).** Added `.zenodo.json` so the next GitHub release can mint a
  Zenodo **concept DOI** (all-versions) with controlled metadata. `CITATION.cff` gained an
  `identifiers` (DOI) block, a `version` field, and the author's ORCID
  (`0000-0002-0326-4752`) and affiliation (University of Rhode Island); `pubrun cite` (all styles),
  the README Citation section, and `docs/research-use.md` now include the DOI. The DOI is a clearly
  labeled placeholder (`10.5281/zenodo.PENDING`) until the repository is enabled in Zenodo and a
  release mints the real one; no fabricated DOI is shipped. No `preferred-citation`/paper reference is
  added — pubrun has no peer-reviewed paper yet and does not imply one. A consistency test guards
  against author-name/DOI/version drift across these surfaces. Author display name remains the
  **publication** form (`Gabriele Fariello` / `Fariello, G.`); ORCID/affiliation are additive.
- **`NOTICE`** file with the required Apache-2.0 attribution string; **`CITATION.cff`** added/updated
  for citation; README gained a License/Attribution/Citation section.
- **`pubrun init` command**: Creates `.pubrun.toml` and prints getting-started guidance.
- **Process-tree resource capture**: `[capture.resources].scope = "tree"` sums RSS/CPU across all child processes (Linux /proc walk, macOS ps-based tree walk).
- **Phase-scoped profiling**: `[capture.profiling].enabled = true` profiles `pubrun.phase()` blocks via cProfile or yappi. Saves `profile-<phase>.prof` per phase.
- **`imported-transitive` package mode**: Records imported packages plus their declared dependencies (one level deep) with `source` and `required_by` fields.
- **Status summary line**: `pubrun status` ends with a colored summary showing run count, date range, status frequencies, and non-zero exit codes. Reflects full run set even with `-n` limit.
- **`[console].non_tty_mode`**: Override capture behavior when stdout is piped/redirected.
- **`[console].jupyter_mode`**: Auto-disable console capture in Jupyter notebooks (default `"off"`).
- **`[capture.git].check_dirty`**: Skip `git status --porcelain` for faster startup on large repos.
- **`[events].flush_interval_events`**: Buffer non-critical events (default 100) for throughput.
- **Secret scanning CI**: `gitleaks` workflow on push/PR + `.gitleaksignore`.
- **Dependency audit CI**: `pip-audit` workflow on push/PR.
- **Pre-commit framework**: gitleaks + hygiene hooks (large-file guard, whitespace, YAML/TOML check).
- **Benchmark suite** (`benchmarks/`): a reproducible, stdlib-only harness that measures
  pubrun's startup and run-time overhead per feature (import modes, resource watcher,
  subprocess spy, git/hardware/packages capture, patched `open()`/`print()` hot paths).
  `harness.py` writes machine-tagged result JSONs; `aggregate.py` merges them into CSV +
  Markdown; optional `plot.py`/`test_benchmarks.py` use a new dev-only `[bench]` extra
  (`pytest-benchmark`, `matplotlib`). New `docs/performance.md` documents how to run it
  and holds a placeholder results table. Does not affect the runtime install (zero deps
  on 3.11+).
- **`pubrun methods --all`**: aggregate the whole matching run set into ONE
  representative "Computational Methods" paragraph plus a variance note (only the
  fields that differ across runs — OS/CPU/RAM/Python/git commit/pubrun/packages).
  Homogeneous sets read like the single-run output with "across N runs" added; a
  differing git commit is disclosed as variance, not an error. Bound/curate with
  the shared run filters (`-n`/`-f`/`-F`/`-s`/`-S`); `-n` is now enabled for
  `methods`. A large/divergent set prints a "narrow it" suggestion to stderr that
  is clearly marked as **not part of the methods section** (and respects
  `NO_COLOR`). Single-run `pubrun methods` is unchanged; aggregation is opt-in via
  `--all` (unlike `pubrun show`, which iterates per-run — a deliberate difference,
  since a methods section is one publication artifact).
- **`pubrun.paused()` context manager**: `with pubrun.paused(): ...` suspends
  pubrun's *recording* for a block — the console tee and subprocess spy stop
  recording while output still prints and subprocesses still run. Thread-local
  (other threads keep being captured), nestable, and resumes automatically even
  on exception. Does not pause `annotate()`/`phase()` markers or resource
  sampling. Useful for silencing a noisy call without disabling capture globally.
- **`full` import mode**: `import pubrun.full as pubrun` (or `[imports].mode = "full"`, `PUBRUN_IMPORT_MODE=full`, `pubrun run --mode full`) captures everything on import, including console output — it forces the console tee on regardless of `[console].capture_mode` (the mirror of `noconsole`), while still respecting the Jupyter/non-TTY safety guards. An in-code import mode is an absolute imperative over env/config; only `pubrun run --mode` overrides it.
- **`status`/`show --utc` flag**: Display timestamps in UTC (default remains local time). Timestamps are always stored as UTC epochs; this only affects display.
- **Capture subprocess timeouts**: `[capture.hardware].timeout` (default 10s), `[capture.resources].poll_timeout` (default 3s), and `[capture.git].timeout` (default 5s) bound hung external tools so they cannot orphan a capture thread/child. A git timeout is recorded as `capture_state.status = "timeout"` (distinct from "not a git repository").

### Changed
- **BREAKING: `capture_mode` default is now `"off"`**. `import pubrun` no longer wraps stdout/stderr without explicit opt-in. To restore the old behavior, add `capture_mode = "standard"` to `.pubrun.toml`. Jupyter/IPython is auto-detected and capture is suppressed.
- **Hardware detection deferred to background thread**: Import/startup is ~200-500ms faster. Hardware data appears in the manifest after the thread completes; crash-safety manifest shows `pending` until then.
- **Event stream buffering**: Non-critical events are buffered (100 events) before flushing. Critical events (annotations, phases) still flush immediately.
- **Default config and regex caching**: `load_default_config()` cached at module level; redaction regex compiled once.
- **Console tee timestamps**: Computed once per `write()` call, not per line.
- **Script hash gated by size**: Files >= 1MB skip SHA-256 at startup.

### Fixed
- **macOS RSS**: Reverted from `resource.getrusage` (peak only) to `ps -o rss=` (current RSS) for accurate polling. Tree mode uses `ps -eo pid,ppid,rss`.
- **`start()` race condition**: Double-checked locking prevents concurrent threads from creating duplicate Runs.
- **ProvenanceFileProxy**: Uses incremental hash for read-mode files (no redundant re-read); added `write()`/`writelines()` for write-mode hash accuracy.
- **Hardware manifest staleness**: Background thread re-writes startup manifest after hardware data is collected.
- **Event stream serialization errors**: Non-serializable payloads log at warning level (not debug).
- **SubprocessSpy records**: Cleared on uninstall to prevent cross-run leakage; saved before clearing.
- **Event stream migration**: Guarded emit after failed directory migration.
- **Orphaned profilers**: Disabled in `_finalize_state()` if phase entered without exit.
- **yappi concurrent guard**: Nested/concurrent phases with yappi log a warning and skip.

#### Other fixes
- **Namespaced import-mode aliases now expose the full public API.** `import pubrun.auto/
  noauto/nopatch/noconsole/minimal as pubrun` previously rebound only 8 of the 12 public
  names, so `pubrun.print`, `pubrun.open`, `pubrun.report`, `pubrun.artifact`,
  `pubrun.subprocess`, and `pubrun.popen` raised `AttributeError` via the alias (top-level
  `import pubrun` was unaffected). All aliases now match the top-level surface; a
  regression test asserts parity. This makes `pubrun.print()` usable as the output-capture
  escape hatch in `noconsole`/`nopatch`/`minimal` as documented.

#### Edge-case / failure-mode hardening
- **Status reader tolerance**: A single malformed, truncated, hand-edited, or foreign-version `manifest.json`/`.pubrun.lock` (non-numeric `started_at_utc`, out-of-range/NaN epoch, non-dict `signals_received`, non-string `argv`) no longer crashes `pubrun status`/`show`/`inspect`; the bad run is shown degraded and the rest still list. Numeric fields are coerced at a single choke point; `scan_runs` has a per-run backstop.
- **PID liveness**: `is_pid_alive` rejects `None`/non-positive/overflow PIDs before `os.kill` (which would signal a process group for `pid <= 0`); same-process script matching now trusts only an exact basename (substring-only or generic tokens like `python`/`-c` fall through to timing), correcting recycled-PID false positives; the conservative "assume alive when start time is unreadable" default is preserved to avoid false "crashed" verdicts on macOS.
- **Package capture**: A distribution with a missing/`None` name no longer crashes package capture (and thus no longer demotes the whole run to ghost mode).
- **Manual subprocess records**: `pubrun.subprocess.run`/`Popen`/`popen` records are now bounded by `[capture.subprocesses].max_tracked_commands` (previously unbounded — an OOM risk in tight loops); a failed `run()` invocation is now recorded before re-raising.
- **Config tolerance**: A malformed `.pubrun.toml`/user config is warned-and-skipped instead of crashing CLI commands.
- **Resource watcher**: Only unreadable polls (errors/timeouts) count toward the consecutive-failure self-abort; a legitimate RSS of 0 no longer permanently disables telemetry.
- **`sys.excepthook` restore**: Only restores pubrun's wrapper if it is still installed, so a third party's later-installed hook is not clobbered.
- **Console tee**: Passthrough tolerates `OSError`/`ValueError` from the original stream (e.g. host closed stdout), matching plain-stream behavior.
- **`show --export json`**: Tolerates flat-key prefix collisions (e.g. a package named `numpy.core`) instead of raising.
- **Diff correctness**: Guards non-list `environment.variables`/`packages.records`; list diffs use a type-tagged comparison so `bool`/`int` (`True`/`1`) no longer alias.
- **Combined logs**: Interleave uses a stable secondary sort key so untimestamped/partial lines keep their original position instead of being hoisted to the top.
- **`pubrun.print`**: Tolerates `sep=None`/`end=None` (accepted by the builtin `print`).
- **`pubrun status` timestamps**: Now rendered in local time by default with an explicit zone, resolving the prior status-vs-diff inconsistency; event counts shown from the size estimate are labeled `~N (est.)`.

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
