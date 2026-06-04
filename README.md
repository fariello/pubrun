[README](README.md) | [Architecture](docs/architecture.md) | [Functional Spec](docs/functional_spec.md) | [API](docs/api.md) | [CLI](docs/cli.md) | [Configuration](docs/configuration.md) | [Manifest](docs/manifest.md)

# pubrun

> **Let your code monitor itself and write its own Methods section while you go to the pub.**

`pubrun` is a stupidly simple, zero-dependency[^1] Python library that eliminates the boilerplate of documenting methodology, tracking versions, recording inputs, and monitoring resources — making it dramatically easier to publish, share, and reproduce your models and research. If you're feeling formal, you can think of "publication-ready runner" as the meaning of the name.

[^1]: On Python 3.11+, pubrun uses only the standard library. On Python 3.8–3.10, the sole runtime dependency is `tomli` (a backport of the standard-library `tomllib`).

## Installation

```bash
pip install pubrun
```

On Python 3.8–3.10, this also installs `tomli` (a backport of the standard-library `tomllib`). On Python 3.11+, there are zero runtime dependencies.

## Quick Start

```python
import pubrun  # That's it 90% of the time!
```
or
```bash
pubrun -h  # Lots of info here.
```
That's it. No frameworks, no heavy integrations, no syntax hijacking.
When the script exits, `pubrun` silently generates a structured, lightweight footprint in your local `./runs/` directory.

> [!NOTE]
> **Console capture**: By default, `pubrun` tees `stdout` and `stderr` to log files in the run directory. Your terminal output is unchanged, but a copy is saved alongside the manifest. If your script produces very high output volume, you can disable this with `capture_mode = "off"` in `.pubrun.toml` or via `pubrun.start(console={"capture_mode": "off"})`. See [Configuration](docs/configuration.md) for details.

See [CLI Reference](docs/cli.md) and [API Reference](docs/api.md) for full details.

## Features

- **Automatic Execution Tracing** — Captures environment variables, hardware specs, and dependency graphs without manual configuration.
- **Publication-Ready Output** — Generates LaTeX/Markdown methodology blocks ready for academic papers.
- **Semantic Diffing** — Compares execution footprints to identify subtle but critical differences between runs.
- **Secret Redaction** — Automatically detects and redacts passwords, tokens, and API keys in environment variables and CLI arguments.
- **Codebase Drift Detection** — Compares current code state against the execution snapshot to highlight changes.
- **Cross-Platform Reproducibility** — Extracts initialization commands for seamless environment replication.
- **HPC Optimized** — Supports global parent-child manifest hydration to minimize overhead on massive clusters.

## The Problem

Modern scientific workflows rely on implicit state. When it's time to publish a paper or ship a model, researchers are forced to retroactively piece together their methodology — PyTorch versions, OS constraints, hardware parameters — from memory.

## The Solution

`pubrun` permanently ends this friction.

With a single `import pubrun`, the library quietly traces your script execution, hashes your environment dependencies, detects codebase drift, and compiles publication-ready **Computational Methodology** LaTeX/Markdown blocks so your run is instantly citable.

### Import Modes

By default, `import pubrun` starts tracking immediately. For more control, use namespaced import modes:

```python
import pubrun.noauto as pubrun   # Load API, start later with pubrun.start()
import pubrun.nopatch as pubrun  # Auto-start, but no subprocess/console/signal hooks
import pubrun.quiet as pubrun    # API only — no auto-start, no hooks
```

Or configure project-wide in `.pubrun.toml`:

```toml
[imports]
mode = "noauto"
```

Or use the CLI wrapper for scripts you can't modify:

```bash
pubrun run --mode quiet -- python script.py
```

Legacy approaches still work: `PUBRUN_AUTO_START=false` and `[core].auto_start = false`.

See [Configuration](docs/configuration.md) for the full `[imports]` section.

### Explicit Tracking Example

```python
import pubrun.noauto as pubrun

pubrun.start(output_dir="./custom_storage", profile="deep")
# ... your code ...
pubrun.stop()
```

Now extract your method paragraph for your paper:

```bash
pubrun methods --format latex
```

### Sample Output

> Computational experiments were executed on a machine running Linux (5.15.0-91-generic) equipped with an Intel(R) Core(TM) i7-12700H and 32.0 GB of RAM. The execution environment relied on Python 3.10.12 (CPython). Key dependencies tracked include torch (v2.0.1) and numpy (v1.24.3). To guarantee computational reproducibility, the exact state of the source code was anchored at Git commit `a1b2c3d4`. Environment and execution provenance were tracked using the `pubrun` library [1].

> [!NOTE]
> **Windows support**: `pubrun` works on Windows, but some capture engines have reduced functionality. Process `uid`/`gid` fields are not available, and `os.system` interception uses shell-string parsing rather than structured argument lists. All other features work identically.

---

## CLI Reference

The `pubrun` CLI provides nine commands and diagnostic flags, all designed to work equally well on a developer laptop or across a Slurm array of thousands of HPC jobs.

### `pubrun cite`
Generates the bibliographic citation for crediting this library in your paper.
```bash
pubrun cite --style bibtex
```

### `pubrun methods`
Translates raw JSON diagnostic payloads into publication-ready methodology paragraphs.
```bash
pubrun methods [RUN_DIR] --format markdown|latex
```

### `pubrun report`
A diagnostic viewer that surfaces execution timing, hardware, dependencies, and codebase drift. Accepts multiple run directories for sequential evaluation.
```bash
pubrun report ./runs/pubrun-A ./runs/pubrun-B --deep
```

### `pubrun rerun`
Extracts the exact shell command needed to reproduce a run.
```bash
pubrun rerun ./runs/pubrun-A
```

### `pubrun diff`
Generates a semantic side-by-side comparison between two execution traces, filtering volatile noise (timestamps, PIDs) by default.
```bash
pubrun diff ./runs/pubrun-A ./runs/pubrun-B --same --basic --wrap
```

### `pubrun meta`
Generates a standalone environment snapshot for HPC parent-child hydration.
```bash
pubrun meta --out ./runs/meta.json --deep
```

### `pubrun status`
Lists all runs with their current status (completed, failed, interrupted, running, crashed, ghost), or inspects a specific run in detail. Detects active processes via cross-platform PID liveness checks.
```bash
pubrun status              # Compact table of all runs
pubrun status -v           # Verbose listing with PID, RSS, CPU, events
pubrun status a3f9         # Inspect a specific run by ID prefix
pubrun status --dir /path  # Scan a non-default output directory
```

### `pubrun clean`
Interactively delete old run directories. Lists candidates with age and size, then prompts for confirmation.
```bash
pubrun clean                        # Interactive: list and confirm
pubrun clean --older-than 7d --yes  # Non-interactive: delete all completed runs older than 7 days
pubrun clean --status crashed --yes # Delete all crashed runs
pubrun clean --dry-run              # Preview what would be deleted
```

### `pubrun run`
Spawn a command with a specific import mode. Useful for CI, Slurm, and scripts you can't modify.
```bash
pubrun run --mode quiet -- python script.py
pubrun run --mode nopatch -- python train.py
```

### Diagnostic Flags

| Flag | Description |
|---|---|
| `--version` | Print the installed pubrun version and exit |
| `--create-config` | Bootstrap a fully commented `.pubrun.toml` file |
| `--show-config` | Print the default configuration to the terminal |
| `--info` | Display system capabilities and pubrun version |
| `--run-tests` | Execute the built-in self-test suite |

See [CLI Reference](docs/cli.md) for full details and examples.

---

## Monitoring Runs

`pubrun` tracks the lifecycle of every run from start to finish, enabling real-time and post-hoc inspection of execution state.

### Lock Files and Liveness Detection

When a run starts, `pubrun` writes a `.pubrun.lock` file to the run directory containing the PID, start timestamp, hostname, and git commit. This file is removed when the run finalizes normally.

If a process is killed (`SIGKILL`, OOM, power loss), the lock file persists. `pubrun status` detects these orphaned runs by checking whether the recorded PID is still alive and whether its start time matches (to handle PID recycling). Runs are classified as:

| Status | Meaning |
|---|---|
| **completed** | Manifest exists, outcome is "completed" |
| **failed** | Manifest exists, outcome is "failed" |
| **interrupted** | Run received SIGINT, SIGTERM, or SIGHUP (e.g., Ctrl+C) |
| **running** | Lock file present, process is alive |
| **crashed** | Lock file present, process is dead |
| **ghost** | Run entered ghost mode (filesystem write failure at init) |

### Signal and Exit Code Capture

`pubrun` installs non-intrusive signal handlers that record OS signals (`SIGINT`, `SIGTERM`, `SIGHUP`, etc.) received during execution. These handlers **chain to any pre-existing handlers** — if the importing script has its own `SIGINT` handler, it is called normally after `pubrun` records the signal.

The process exit code is also captured at finalization. All signal and exit data appears in the `"signals"` section of the manifest:

```json
{
  "signals_received": [
    {"signal": 2, "signal_name": "SIGINT", "timestamp_utc": 1780250544.068}
  ],
  "exit_code": 0,
  "exit_exception": null
}
```

Signal capture is configurable via `[capture.signals].enabled` in `.pubrun.toml`.

### Live Process Inspection

For running processes, `pubrun status <run-id>` shows live resource usage (RSS memory and CPU percent) queried cross-platform:
- **Linux**: reads from `/proc/<pid>/status` and `/proc/<pid>/stat`
- **macOS**: queries via `ps`
- **Windows**: uses `ctypes` (`kernel32`/`psapi`) and `wmic`

No external dependencies are required.

---

## Advanced HPC Ecosystems (Global Hydration)

If you run thousands of array jobs across a cluster, you don't want each child run wasting time and disk logging identical dependency graphs. `pubrun` supports **parent-child manifest hydration**.

#### Step 1: Snap the Parent Cluster
On the head node, snapshot the global environment:
```bash
pubrun meta --out ./runs/meta.json --deep
```
This generates a deep metadata map of hardware, environment variables, and the full Python package tree.

#### Step 2: Hydrate Children
In your Slurm script, reference the parent snapshot:
```bash
export PUBRUN_META_REF=meta.json
python minimal_script.py
```

Child scripts automatically skip heavy footprint tracking. When you run `pubrun report` or `pubrun methods`, the orchestrator detects the `PUBRUN_META_REF`, pulls in the parent `meta.json` context, and stitches the complete hardware and dependency picture back together. It also compares script timestamps against the parent snapshot and warns you if **environmental drift** has been detected.

---

## Configuration

`pubrun` supports a hierarchical configuration system (highest to lowest precedence):

1. **API overrides** — `pubrun.start(profile="deep")`
2. **Environment variables** — `PUBRUN_AUTO_START=false`
3. **Local project config** — `.pubrun.toml` or `.config/pubrun/config.toml`
4. **User home config** — `~/.config/pubrun/config.toml`
5. **Built-in defaults** — `default.toml` (shipped with the library)

### Generate a Configuration File
```bash
pubrun --create-config
```

See [Configuration Reference](docs/configuration.md) for all settings and examples.

---

## Security & Redaction

`pubrun` automatically detects and redacts sensitive values (passwords, tokens, API keys, credentials) in both environment variables and CLI arguments before writing them to the manifest. Redaction is **destructive by default** — raw values are replaced with `{"representation": "redacted"}`, and no hashes are generated, to prevent brute-force attacks.

Both environment variable and argv redaction are independently configurable:

```toml
[redaction]
env_enabled = true    # Redact matching environment variable values
argv_enabled = true   # Redact matching CLI argument values
```

See [Configuration Reference](docs/configuration.md) for the full redaction policy and regex pattern.

---

## Roadmap

### Future

1. **Sphinx / MkDocs integration** — Generate hosted API documentation from docstrings.
2. **GitHub Actions CI** — Automated test matrix on push/PR.
3. **Plugin / extension model** — Formal extension points for custom capture engines.
4. **Artifact registration API** — `register_artifact()` for tracking user-produced output files.
5. **Custom metadata API** — `register_metadata()` for injecting structured data into the manifest.
6. **Timestamped console capture** — `standard` mode prepends timestamps to log lines, enabling `pubrun combined` (below).
7. **`pubrun combined` command** — Interleaves stdout and stderr from one or more runs using log timestamps. Requires timestamped capture (item 6).

---

## Acknowledgements

`pubrun` was redesigned and rewritten from pre-existing custom libraries, code fragments, scripts, and ideas spanning almost two decades, with the assistance of Google Antigravity for its official release.

## License

Released under the BSD 3-Clause License. Copyright (c) 2007-2026 Gabriele Fariello. See the [LICENSE](LICENSE) file for full terms.

---

[README](README.md) | [Architecture](docs/architecture.md) | [Functional Spec](docs/functional_spec.md) | [API](docs/api.md) | [CLI](docs/cli.md) | [Configuration](docs/configuration.md) | [Manifest](docs/manifest.md)
