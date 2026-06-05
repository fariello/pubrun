[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md)

# pubrun CLI Reference

The `pubrun` CLI is accessible via `pubrun <command>` or `python -m pubrun <command>`. It provides nine commands for post-execution analysis and diagnostic flags.

---

## Commands

### `methods` — Academic Methodology Writer

Compiles a run's manifest into a publication-ready "Computational Methods" paragraph in Markdown or LaTeX.

```bash
pubrun methods [RUN_DIR] [--format markdown|latex]
```

- If `RUN_DIR` is omitted, automatically uses the most recent run in `./runs/`.
- If the manifest references a `meta_ref`, the parent context is hydrated before generating the output.

**Example:**
```bash
pubrun methods ./runs/pubrun-train-20260509-a1b2 --format latex
```

---

### `report` — Diagnostic Viewer

Renders a human-readable diagnostic summary of one or more runs, including timing, hardware, dependencies, and codebase drift.

```bash
pubrun report [RUN_DIR ...] [--basic|--standard|--deep]
```

- Pass multiple directories to evaluate them sequentially.
- If the manifest references a `meta_ref`, the parent context is hydrated automatically.

**Depth Controls:**

| Flag | Scope |
|---|---|
| `--basic` | Timing and outcome only |
| `--standard` | Hardware, Git, Python, and dependency summary (default) |
| `--deep` | Full environment variables and complete package list |

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

### `status` — Run Monitoring

Lists all runs in the output directory with their current status, or inspects a specific run in detail. Classifies runs as completed, failed, interrupted, running, crashed, or ghost via lock-file PID liveness checks.

```bash
pubrun status [RUN_ID] [--dir PATH] [-v|--verbose]
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
```

For running processes, the inspect view also shows live RSS memory and CPU usage (cross-platform: Linux, macOS, Windows).

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

### `cite` — Academic Citation

Generates a formatted citation for crediting `pubrun` in academic publications.

```bash
pubrun cite [--style apa|mla|chicago|bibtex]
```

**Example:**
```bash
pubrun cite --style bibtex
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
| `--mode MODE` | Import mode for the child process: `auto` (default), `noauto`, `nopatch`, or `quiet` |

The double dash (`--`) separates pubrun wrapper options from the target command.

**Example:**
```bash
pubrun run --mode quiet -- python script.py      # No auto-start in child
pubrun run --mode nopatch -- python train.py     # Auto-start but no hooks
pubrun run -- python script.py                   # Default auto mode
```

The wrapper returns the child process exit code. It does not create a run in the wrapper process itself.

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

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md)
