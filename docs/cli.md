[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md)

# pubrun CLI Reference

The `pubrun` CLI is accessible via `pubrun <command>` or `python -m pubrun <command>`. It provides six commands for post-execution analysis and four diagnostic flags.

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

## Diagnostic Flags

These flags can be used independently of any subcommand.

### `--create-config [DEST]`

Bootstraps a fully commented `.pubrun.toml` configuration file.

```bash
pubrun --create-config                    # Interactive: asks local vs global
pubrun --create-config .pubrun.toml       # Direct: writes to specified path
```

- If no destination is given, an interactive prompt offers Local (`./.pubrun.toml`) or Global (`~/.config/pubrun/config.toml`).
- Refuses to overwrite an existing file.

### `--show-config`

Prints the complete default configuration to the terminal. If `rich` is installed, the output is syntax-highlighted.

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
