[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)

# pubrun CLI Reference

The `pubrun` CLI is accessible via `pubrun <command>`, `pbr <command>` (a convenient shorthand alias), or `python -m pubrun <command>`. It provides thirteen commands for post-execution analysis and diagnostic flags.

---

## Commands

### `init` — Project Initialization

Creates a `.pubrun.toml` configuration file and displays getting-started guidance.

```bash
pubrun init [DEST]
```

**Options:**

| Argument | Description |
|---|---|
| `DEST` | Destination path (default: `.pubrun.toml`) |

**Example:**
```bash
pubrun init                    # Create .pubrun.toml in current directory
pubrun init ./config/.pubrun.toml  # Custom path
```

After init, add `import pubrun` to your script to begin tracking.

---

### `report-bug` / `feedback` — Report a Bug or Send Feedback

Two commands (same behavior): open the GitHub issue tracker in your default browser and
print system-configuration telemetry to the console for easy copy-paste. `report-bug` is
for bug reports / feature requests; `feedback` is for general feedback — both land as GitHub
issues.

```bash
pubrun report-bug
pubrun feedback
```

> **Changed in 1.4.0:** the old `bug-report` command (and its `issue` alias) were renamed to
> `report-bug`; `feedback` is now its own command rather than an alias.

---

### `cite` — Academic Citation

Generates a formatted citation for crediting `pubrun` in academic publications. The
citation includes the archived Zenodo **concept DOI** (all-versions). Until the repository
is enabled in Zenodo and a release mints the real DOI, the output shows a clearly labeled
placeholder (`10.5281/zenodo.PENDING`).

```bash
pubrun cite [--style apa|mla|chicago|bibtex]
```

**Example:**
```bash
pubrun cite --style bibtex
```

---

### `self-check` — Environment / Install Diagnostics

Report-only checks of the **current machine** for pubrun performance/config pitfalls and
install health. It flags network filesystems (NFS/Lustre/GPFS/CIFS) backing the pubrun
install, output dir, `$TMPDIR`, or Python install (a common cause of slow runs on HPC), low
free RAM, high load, an unwritable output dir, missing `git`, an unsupported Python, and
config errors. It never modifies anything.

It also runs a short **live filesystem probe** (a `statvfs` capacity check in a background
daemon thread, with a ~5s wait budget) and warns if a mount is **wedged/hung** or **slow to
respond**. These warnings are framed honestly as a **system-wide** hazard — a mount that
takes 34s to answer a capacity query will slow *any* script doing I/O there, not just pubrun.
This probe runs only when you invoke `self-check` (or `bench`); it is **never** run by
`import pubrun` or during a normal run, so it can never hang your host script.

```bash
pubrun self-check [--show-suggestions|-v] [--json] [--strict]
```

**Options:**

| Flag | Description |
|---|---|
| `--show-suggestions`, `-v` | Show per-item detail and how to address each concern. |
| `--json` | Emit findings as JSON (always full detail). |
| `--strict` | Exit non-zero if any warning fired (useful in CI / HPC job pre-checks). |

See [Research Use & HPC](hpc.md) for guidance on diagnosing slow runs on clusters.

---

### `inspect` — Post-hoc Run Diagnosis

Report-only diagnosis of a **completed run's** manifest. Surfaces the recorded
I/O/RAM/load/filesystem signals, and — importantly — a **capture-completeness assessment**:
what provenance was *not* captured (e.g. process-scope only, no subprocess/file-I/O record),
why that limits insight, and how to capture more next time (with honest performance
trade-offs). Prints a glaring banner when the inspecting host differs from where the run
executed (e.g. HPC head node vs compute node), because live re-checks then reflect the
wrong machine.

Output is **terse by default** (a one-line summary + a nudge); use `--show-suggestions`
for the full per-item detail, or `--json` for the complete structured findings.

```bash
pubrun inspect [RUN_DIR] [--show-suggestions|-v] [--json] [--strict] [-f QUERY] [-F QUERY] [-s STATUS] [-S STATUS] [--older-than AGE] [--exit-code CODE]
```

**Options:**

| Flag | Description |
|---|---|
| `RUN_DIR` | Run directory to inspect. Defaults to the most recent matching run. |
| `--show-suggestions`, `-v` | Expand into per-item findings + how to capture more (with perf caveats). |
| `--json` | Emit the full findings as JSON. |
| `--strict` | Exit non-zero if any warning fired. |
| `-f`/`--filter`, `-F`/`--not-filter`, `-s`/`--status`, `-S`/`--not-status`, `--older-than`, `--exit-code` | Standard run selectors (which single run to inspect). |

> **Honesty note:** pubrun does not patch `open()` or subprocess globally, so file-I/O and
> subprocess provenance are recorded only when the script uses `pubrun.open()` /
> `pubrun.subprocess`. `inspect` will not claim a feature was "off" when the manifest merely
> shows no records unless it can determine this definitively.

**Example:**
```bash
pubrun inspect                          # diagnose the most recent run
pubrun inspect runs/pubrun-XYZ -v       # full detail for a specific run
pubrun inspect -f train.py --json       # latest run matching "train.py", as JSON
```

---

### `bench` — Overhead Benchmark Runner

Friendly front-end over the benchmark harness (`benchmarks/harness.py`). Runs the suite
locally by default; on an HPC login node with Slurm detected, it **offers** to submit to a
compute node (and never submits without confirmation). Writes a **redacted, shareable**
copy of the results by default and, after a local run, **offers to contribute it** to the
public [`pubrun-benchmarks`](https://github.com/fariello/pubrun-benchmarks) repo.

**Requires a source checkout** — the benchmark tooling is intentionally not shipped in the
pip package (zero-footprint installs). Clone the repo and run from it.

```bash
pubrun bench [--quick] [--iterations N] [--passes N] [--local | --submit] [-y|--yes] [--no-redact] [--json]
pubrun bench --submit-file PATH [--submit-method {gh,http,print}] [--gh-repo O/N] [--gh-token TOKEN] [--print-submission]
```

**Options:**

| Flag | Description |
|---|---|
| `--quick` | Fast smoke run (fewer iterations). |
| `--iterations N` | Iterations per scenario. |
| `--passes N` | Number of full scenario sweeps (default 2). |
| `--local` | Run here even if Slurm is detected. |
| `--submit` | On HPC: submit to Slurm without prompting. Off HPC: contribute the result without prompting. |
| `-y`, `--yes` | Assume "yes" to the submit/contribute prompt. |
| `--no-redact` | Do NOT write a redacted share copy (full detail only). Also disables auto-contribution (nothing safe to send). |
| `--json` | Emit the result/redacted file paths as JSON. |
| `--submit-file PATH` | Submit an existing **redacted** result file, without running a benchmark (recovery / HPC / batch). |
| `--no-submit` | Do not offer to contribute the result. |
| `--submit-method {gh,http,print}` | Force one submission method instead of probing (default: `gh` → `http` → printed floor). |
| `--gh-repo OWNER/NAME` | Target repo for submission (default `fariello/pubrun-benchmarks`). |
| `--gh-token TOKEN` | Token for the HTTP submission path (else `$GITHUB_TOKEN`/`$GH_TOKEN` or `gh auth token`). |
| `--print-submission` | Print a ready-to-paste submission instead of transmitting (offline / power user). |

**Contributing a result (consent-gated).** After a local run, `pubrun bench` prints where
the redacted copy was written and asks `Contribute this redacted result…? [y/N]` — pressing
Enter (or any non-`y`) **never transmits**. If you say yes (or pass `--submit`/`--yes`), it
tries, in order: the GitHub CLI (`gh`, using your existing auth) → a direct GitHub Issues
API call (needs a token) → printing a ready-to-paste submission. Every automated path files
a **GitHub issue**, so it requires a GitHub account (GitHub has no anonymous-issue
mechanism); fully anonymous submission means a throwaway account or a manual paste.

**"Oh, I meant yes."** The redacted file persists on disk, so if you decline you can submit
it later without re-running:

```bash
pubrun bench --submit-file benchmarks/results/<host>-<ts>.redacted.json
```

This is also the **HPC path**: run the benchmark on a compute node (often no network / no
`gh`), then submit the redacted file later from a login node.

**Safety.** pubrun **never auto-transmits an un-redacted result** to the public repo — the
`--submit-file` path verifies the file looks redacted (no hostname/username/home-path leak)
and refuses otherwise. The redacted copy masks hostname, OS username, and every
home-directory path while preserving analysis-relevant data (CPU/GPU model, timings,
versions, filesystem type, Slurm partition). Even redacted, a distinctive CPU/GPU model plus
a named Slurm partition can be re-identifying in a small group. See
[HPC & performance diagnosis](hpc.md) and `benchmarks/README.md` for more.

**Example:**
```bash
pubrun bench --quick --local                          # quick local run, then offers to contribute
pubrun bench --submit                                 # HPC: submit to Slurm; laptop: contribute (no prompt)
pubrun bench --submit-file res.redacted.json          # submit a previously-produced redacted file
pubrun bench --submit-file res.redacted.json --print-submission  # just print a copy-paste version
```

---

### `clean` — Run Cleanup

Interactively delete old run directories. Lists candidates with their age and size, then prompts for confirmation before removal.

```bash
pubrun clean [--dir PATH] [--older-than AGE] [--status STATUS] [-y|--yes] [--dry-run]
```

**Options:**

| Flag | Description |
|---|---|
| `--dir PATH` | Override the output directory to scan |
| `--older-than AGE` | Only consider runs older than AGE (e.g. `7d`, `24h`, `30` for 30 days) |
| `--status STATUS` | Comma-separated status filter (e.g. `completed,failed`). Default: all non-running statuses |
| `-y`, `--yes` | Skip confirmation prompt (non-interactive mode) |
| `--dry-run` | Show what would be deleted without actually deleting |

Running processes are never deleted, even if explicitly included in `--status`.

**Interactive mode** (default): displays a numbered list with exit codes, args, age, and size. The user must explicitly select runs by number, range (e.g. `1-3,5`), or type `all`. The selected runs are then displayed in a confirmation table before a final `y/N` prompt. Nothing is deleted without explicit confirmation.

**Example:**
```bash
pubrun clean                              # Interactive: list and confirm
pubrun clean --older-than 7d --yes        # Non-interactive: delete completed runs > 7 days
pubrun clean --status crashed,ghost --yes # Delete all crashed/ghost runs
pubrun clean --dry-run                    # Preview without deleting
```

---

### `combined` — Log Interleaver

Post-execution command that chronologically interleaves stdout and stderr logs from one or more runs using the log-line timestamps written in `standard` or `deep` console mode.

```bash
pubrun combined [RUN_ID ...] [--dir PATH] [--output FILE] [-y|--yes] [--force] [-f|--filter QUERY]
```

**Options:**

| Flag | Description |
|---|---|
| `--dir PATH` | Override the output directory to scan (default: configured `output_dir` or `./runs`) |
| `--output FILE` | Write combined logs to this file instead of stdout |
| `-y`, `--yes` | Skip confirmation prompt for files > 250 MB |
| `--force` | Force execution for files > 500 MB |
| `-f`/`--filter`, `-F`/`--not-filter`, `-s`/`--status`, `-S`/`--not-status`, `--older-than`, `--exit-code` | Standard run filters (select which runs to combine when no run IDs are given) |

> **Changed in 1.4.0:** `combined -f` now means `--filter` (consistent with every other command). The force flag is now `--force` (long form only). Previously `-f` meant `--force`.

- If multiple run IDs are supplied, each output line is prefixed with the run ID and stream origin, e.g. `[runA][stdout]`.
- If a single run is combined, each output line is prefixed with the stream origin only, e.g. `[stdout]`.
- If the logs lack timestamps (captured with `"basic"` console mode), it falls back to sequential concatenation and prints a warning.

**Example:**
```bash
pubrun combined a3f9               # Interleave stdout/stderr for run a3f9
pubrun combined a3f9 b2c1 --output all.log  # Combine multiple runs into a file
```

---

### `diff` — Semantic Comparison

Generates a side-by-side structural comparison between two execution traces, filtering volatile noise (timestamps, PIDs) by default.

```bash
pubrun diff RUN_DIR_A RUN_DIR_B [OPTIONS]
```

**Options:**

| Flag | Description |
|---|---|
| `--basic` | Filter heavily; show only script, package, and user telemetry changes (default) |
| `--standard` | Moderate filtering; include hardware and resource changes |
| `--deep` | No filtering; compare everything |
| `--same` / `--no-same` | Show or hide unchanged values |
| `--wrap` / `--no-wrap` | Wrap long strings or truncate with ellipsis |
| `--max-length N` | Maximum character length before truncation |
| `--no-color` | Disable ANSI color output |
| `--export [txt\|json]` | Export flattened key-value output for external diff tools (e.g., `meld`, VS Code) |
| `-f`/`--filter`, `-F`/`--not-filter`, `-s`/`--status`, `-S`/`--not-status`, `--older-than`, `--exit-code` | Standard run filters. When run directories are omitted, the auto-selected pair is drawn from the runs matching these filters (with no filters, from all runs — the historical behavior) |

When no run directories are given, `diff` compares the two most recent runs in the
(optionally filtered) set. If a filter matches fewer than two runs, `diff` reports a clear
error and exits non-zero rather than silently ignoring the filter.

**Example:**
```bash
pubrun diff ./runs/pubrun-A ./runs/pubrun-B --standard --same --wrap
pubrun diff -f train.py            # diff the two most recent runs whose command matches "train.py"
```

---

### `meta` — Global Environment Snapshot

Generates a standalone `meta.json` snapshot of the current environment (hardware, packages, git, environment variables) without running any script. Designed for HPC parent-child hydration workflows.

```bash
pubrun meta [--out PATH] [--basic|--standard|--deep]
```

- If `--out` is omitted, writes to `./runs/meta.json`.
- Default depth is `--deep` (captures full virtual environment).

**Example:**
```bash
pubrun meta --out ./shared/meta.json --deep
```

---

### `methods` — Academic Methodology Writer

Compiles a run's manifest into a publication-ready "Computational Methods" paragraph in Markdown or LaTeX.

```bash
pubrun methods [RUN_DIR] [--format markdown|latex] [--all] [-n N] [-f/-F/-s/-S ...]
```

- If `RUN_DIR` is omitted, automatically uses the **most recent** run in `./runs/` (the default, single-run behavior). Run filters (`-f`, `-F`, `-s`, `-S`, `--older-than`, `--exit-code`) still select the most-recent *matching* run.
- If the manifest references a `meta_ref`, the parent context is hydrated before generating the output.

**Aggregating many runs (`--all`):** for a study run many times (sweeps, seeds, folds), `pubrun methods --all` aggregates the whole matching set into **one** representative paragraph plus a variance note listing only the fields that differ across runs (OS, CPU, RAM, Python, git commit, pubrun version, packages). If the runs are environment-homogeneous, the output reads like the single-run paragraph with "across N runs" added.

- Bound/curate the set with the shared run filters: `-n N` (most-recent N), `-f`/`-F` (include/exclude by script/args/**run-id**), `-s`/`-S` (by status). A differing git commit across the set is *disclosed as variance*, never an error.
- A very large or divergent set prints a suggestion to stderr, **clearly marked as not part of the methods section** (so it can never be pasted into a paper); it respects `NO_COLOR`.
- **Note the difference from `show`:** `pubrun show` (no run dir) prints a *separate report per matching run*; `pubrun methods` stays single-run unless you pass `--all`, and then produces *one aggregated paragraph*. This is deliberate — a methods section is a single publication artifact, so aggregation is opt-in.

**Examples:**
```bash
pubrun methods ./runs/pubrun-train-20260509-a1b2 --format latex
pubrun methods --all -f train.py            # one paragraph across all train.py runs
pubrun methods --all -n 20 -s completed      # aggregate the 20 most-recent completed runs
```

---

### `show` — Diagnostic Viewer

Renders a human-readable diagnostic summary of one or more runs, including timing, hardware, dependencies, and codebase drift.

```bash
pubrun show [RUN_DIR ...] [--basic|--standard|--deep]
```

**Alias:** `report` (backward-compatible)

- Pass multiple directories to evaluate them sequentially.
- If the manifest references a `meta_ref`, the parent context is hydrated automatically.

**Depth Controls:**

| Flag | Scope |
|---|---|
| `--basic` | Timing and outcome only |
| `--standard` | Hardware, Git, Python, and dependency summary (default) |
| `--deep` | Full environment variables and complete package list |

---

### `rerun` — Reproducibility Command

Extracts the exact shell command needed to re-execute a recorded run.

```bash
pubrun rerun [RUN_DIR]
```

Prints the `rerun_command` from the manifest to stdout. Internal log messages go to stderr, so this is safe for piping:

```bash
pubrun rerun ./runs/pubrun-A | bash
```

---

### `res` — Resource Monitoring (comprehensive)

Renders a **comprehensive** resource summary for a run plus CPU and memory utilization
graphs. Unlike `cpu`/`mem` (which focus on a single metric), `res` surfaces **all** captured
resource signals, each shown only when present in the manifest:

- main-process peak/end RSS and peak CPU%,
- **process-tree** peak RSS (when the run used `[capture.resources].scope = "tree"`),
- **system memory** — available RAM at start and the lowest point during the run,
- **load average** (start and 1-min peak),
- **node iowait** (labeled *node-wide, indicative only* — a whole-node hint, not run-scoped),
- **per-process I/O volume** — bytes read/written (storage layer and logical), from
  `/proc/self/io` (Linux).

```bash
pubrun res [RUN_DIR] [-w WIDTH] [-l LAST] [--average]
```

- If `RUN_DIR` is omitted, automatically uses the most recent run in `./runs/`.
- Parses resource_sample events from `events.jsonl` to render utilization timelines.
- Older runs (before these fields were captured) simply show fewer lines — no error.

The `cpu` and `mem` commands show a single focused chart; `res` shows the full picture.

**Example:**
```bash
pubrun res ./runs/pubrun-train-20260509-a1b2
pubrun cpu                    # CPU chart only (most recent run)
pubrun mem -w 120             # Memory chart, custom width
```

---

### `cpu` — CPU Utilization Chart

Renders the CPU utilization history for a run. Standalone shortcut for the CPU portion of `res`.

```bash
pubrun cpu [RUN_DIR] [-w WIDTH] [-l LAST] [--average]
```

---

### `mem` — Memory Utilization Chart

Renders the memory (RSS) utilization history for a run. Standalone shortcut for the memory portion of `res`.

```bash
pubrun mem [RUN_DIR] [-w WIDTH] [-l LAST] [--average]
```

---

### `run` — Import Mode Wrapper

Spawns a child process with `PUBRUN_IMPORT_MODE` set in the environment. Useful for CI pipelines, shell scripts, Slurm submissions, and any case where you want to control pubrun behavior without modifying source code.

```bash
pubrun run [--mode MODE] -- COMMAND [ARGS...]
```

**Options:**

| Flag | Description |
|---|---|
| `--mode MODE` | Import mode for the child process: `auto` (default), `full` (capture everything incl. console), `noauto`, `nopatch`, `noconsole`, or `minimal` |

The double dash (`--`) separates pubrun wrapper options from the target command.

**Example:**
```bash
pubrun run --mode minimal -- python script.py      # No auto-start in child
pubrun run --mode nopatch -- python train.py     # Auto-start but no hooks
pubrun run --mode noconsole -- python train.py   # Auto-start but no console wrap
pubrun run -- python script.py                   # Default auto mode
```

The wrapper returns the child process exit code. It does not create a run in the wrapper process itself.

---

### `status` — Run Monitoring

Lists all runs in the output directory with their current status, or inspects a specific run in detail. Classifies runs as completed, failed, interrupted, running, crashed, or ghost via lock-file PID liveness checks.

```bash
pubrun status [RUN_ID] [--dir PATH] [-v|--verbose] [--utc]
```

**Modes:**

| Usage | Description |
|---|---|
| `pubrun status` | Compact table listing all runs (ID, script, commit, started, status, exit code, elapsed) |
| `pubrun status -v` | Verbose listing with PID, hostname, RSS, CPU, events, signals, and directory |
| `pubrun status <run-id>` | Detailed inspection of a single run (supports prefix matching) |

**Options:**

| Flag | Description |
|---|---|
| `--dir PATH` | Override the output directory to scan (default: configured `output_dir` or `./runs`) |
| `-v`, `--verbose` | Show detailed information for each run in the listing |
| `--utc` | Display timestamps in UTC (with a `Z` suffix) instead of the default local time. Timestamps are always stored as UTC epochs; this only affects display. Also available on `pubrun show`. |

**Status Values:**

| Status | Meaning |
|---|---|
| `completed` | Run finished successfully (manifest exists, outcome is "completed") |
| `failed` | Run finished with an error (manifest exists, outcome is "failed") |
| `interrupted` | Run received a termination signal — SIGINT (Ctrl+C), SIGTERM, or SIGHUP |
| `broken pipe` | Run completed but received SIGPIPE (downstream reader closed) |
| `running` | Lock file exists and the process is still alive |
| `crashed` | Lock file exists but the process is dead (killed without cleanup) |
| `ghost` | Run entered ghost mode (filesystem write failure) |

**Example:**
```bash
pubrun status                    # List all runs
pubrun status -v                 # Detailed listing
pubrun status a3f9               # Inspect run by ID prefix
pubrun status --dir /shared/runs # Scan a different directory
pubrun status -n 10              # Show last 10, full summary
```

The listing ends with a colored summary line showing total run count, date range, status frequencies, and non-zero exit codes:

```
504 runs | 2026-05-31 13:57 to 2026-07-04 14:31
  488 completed, 10 interrupted, 3 crashed, 3 broken pipe | exit 1: 10
```

When using `-n` to limit displayed rows, the summary still reflects all runs (with "(showing N)" appended).

For running processes, the inspect view also shows live RSS memory and CPU usage (cross-platform: Linux, macOS, Windows).

---

### `ui` — Interactive Dashboard

Launches the terminal user interface (TUI) dashboard to browse, inspect, and manage run records interactively.

```bash
pubrun ui [--dir PATH]
```

**Aliases:** `tui`, `gui`

**Options:**

| Flag | Description |
|---|---|
| `--dir PATH` | Override the directory containing the runs (default: configured `output_dir` or `./runs`) |

**Example:**
```bash
pubrun ui
pubrun gui
```

---

## Diagnostic Flags

These flags can be used independently of any subcommand.

### `--version`

Prints the installed pubrun version and exits.

```bash
pubrun --version
```

### `--create-config [DEST]`

Bootstraps a fully commented `.pubrun.toml` configuration file.

```bash
pubrun --create-config                    # Interactive: asks local vs global
pubrun --create-config .pubrun.toml       # Direct: writes to specified path
```

- If no destination is given, an interactive prompt offers Local (`./.pubrun.toml`) or Global (`~/.config/pubrun/config.toml`).
- Refuses to overwrite an existing file.

### `--show-config`

Prints the complete default configuration to the terminal.

```bash
pubrun --show-config
```

### `--info`

Displays system capabilities, pubrun version, and environment details.

```bash
pubrun --info
```

### `--run-tests`

Executes the built-in self-test suite to verify the installation.

```bash
pubrun --run-tests
```

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Error (missing manifest, invalid path, config already exists, etc.) |

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
