[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [Changelog](../CHANGELOG.md)

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

### `bug-report` — Feature Request or Bug Reporter

Opens the GitHub issue tracker in your default browser and displays system configuration telemetry in the console for easy copying and pasting.

```bash
pubrun bug-report
```

**Aliases:** `feedback`, `issue`

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
pubrun combined [RUN_ID ...] [--dir PATH] [--output FILE] [-y|--yes] [-f|--force]
```

**Options:**

| Flag | Description |
|---|---|
| `--dir PATH` | Override the output directory to scan (default: configured `output_dir` or `./runs`) |
| `--output FILE` | Write combined logs to this file instead of stdout |
| `-y`, `--yes` | Skip confirmation prompt for files > 250 MB |
| `-f`, `--force` | Force execution for files > 500 MB |

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

**Example:**
```bash
pubrun diff ./runs/pubrun-A ./runs/pubrun-B --standard --same --wrap
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

### `res` — Resource Monitoring Graphs

Renders ASCII or Unicode graphs in the terminal showing CPU and memory utilization history over the execution lifecycle of a specific run.

```bash
pubrun res [RUN_DIR] [-w WIDTH] [-l LAST] [--average]
```

- If `RUN_DIR` is omitted, automatically uses the most recent run in `./runs/`.
- Parses resource_sample events from `events.jsonl` to render utilization timelines.

The `cpu` and `mem` commands show individual charts; `res` shows both.

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

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [Changelog](../CHANGELOG.md)
