[README](https://github.com/fariello/pubrun/blob/main/README.md) | [Architecture](https://github.com/fariello/pubrun/blob/main/docs/architecture.md) | [Functional Spec](https://github.com/fariello/pubrun/blob/main/docs/functional_spec.md) | [API](https://github.com/fariello/pubrun/blob/main/docs/api.md) | [CLI](https://github.com/fariello/pubrun/blob/main/docs/cli.md) | [Configuration](https://github.com/fariello/pubrun/blob/main/docs/configuration.md) | [Manifest](https://github.com/fariello/pubrun/blob/main/docs/manifest.md) | [Performance](https://github.com/fariello/pubrun/blob/main/docs/performance.md) | [Research Use](https://github.com/fariello/pubrun/blob/main/docs/research-use.md) | [HPC](https://github.com/fariello/pubrun/blob/main/docs/hpc.md) | [Changelog](https://github.com/fariello/pubrun/blob/main/CHANGELOG.md)

# pubrun

> **Reproducible runs: know exactly what any run did, and compare any two of them. Automatic provenance and environment capture, from a single `import pubrun`.**

`pubrun` is the reproducibility and provenance component you drop into any Python run: a one-off script, a nightly job, a data pipeline, or a step in a larger ML or scientific workflow. With one `import pubrun` (no config, no infrastructure, no framework) it captures the full **provenance** of a run (a complete record of how it happened: code version, dependency graph, hardware, environment, inputs, logs, exit status, resource usage) into a structured `manifest.json`, then lets you diff any two runs to see exactly what changed. Zero runtime dependencies[^1], non-intrusive ([it never alters, slows, or crashes your program](https://github.com/fariello/pubrun/blob/main/docs/performance.md)), and it scales from a laptop to a thousand-node cluster.

pubrun does one thing well: it makes runs trustworthy. It is **not** an orchestrator, scheduler, or serving platform. It is the provenance layer you use *inside* your pipeline, alongside whatever runs it.

It grew up in scientific and ML workflows, but it is useful for **any** run you would ever want to reproduce, compare, or explain, from a 20-line script to a thousand-node cluster.

[^1]: On Python 3.11+, pubrun uses only the standard library. On Python 3.8-3.10, the sole runtime dependency is `tomli` (a backport of the standard-library `tomllib`).

## Installation

Available on [PyPI](https://pypi.org/project/pubrun/):

```bash
pip install pubrun
```

On Python 3.8-3.10, this also installs `tomli` (a backport of the standard-library `tomllib`). On Python 3.11+, there are zero runtime dependencies.

## Quick Start

```python
import pubrun  # That's it 90% of the time!
```
or
```bash
pubrun -h  # Lots of info here.
```
That's it. No frameworks, no heavy integrations, no syntax hijacking.
When the script exits, `pubrun` silently writes a structured, lightweight **manifest** for the run into your local `./runs/` directory.

> [!NOTE]
> **Console capture**: By default, `pubrun` does NOT wrap stdout/stderr (`capture_mode = "off"`). To enable output logging, set `capture_mode = "standard"` in `.pubrun.toml` or via `pubrun.start(console={"capture_mode": "standard"})`. When enabled, your terminal output is unchanged but a timestamped copy is saved alongside the manifest. See [Configuration](https://github.com/fariello/pubrun/blob/main/docs/configuration.md) for details.

See [CLI Reference](https://github.com/fariello/pubrun/blob/main/docs/cli.md) and [API Reference](https://github.com/fariello/pubrun/blob/main/docs/api.md) for full details.

## Is pubrun for me?

Almost certainly yes, if you run Python and would ever want to reproduce, compare, or explain a run:

- **New here, or running an everyday script, data job, or scraper?** See [why pubrun helps a plain script or data job](https://github.com/fariello/pubrun/blob/main/docs/research-use.md), then try the worked example below.
- **Running HPC array jobs, large pipelines, or ML training and evaluation?** See [using pubrun at scale and in ML/scientific pipelines](https://github.com/fariello/pubrun/blob/main/docs/hpc.md).

### Examples

The [`examples/`](https://github.com/fariello/pubrun/tree/main/examples) directory has runnable scripts, from trivial to real, so you can find your own use and climb from there:

- **A trivial script:** [`examples/01_minimal_start_stop.py`](https://github.com/fariello/pubrun/blob/main/examples/01_minimal_start_stop.py) (add provenance to any script in one import).
- **A data or analysis run:** [`examples/minimal-research-workflow/`](https://github.com/fariello/pubrun/tree/main/examples/minimal-research-workflow) (a full round trip on synthetic data: run, inspect, diff two runs, extract a rerun command).
- **Recording inputs and outputs** (ETL, scrapers, file-producing jobs): [`examples/07_file_capture.py`](https://github.com/fariello/pubrun/blob/main/examples/07_file_capture.py).
- **Comparing two runs:** [`examples/08_diff_engine.py`](https://github.com/fariello/pubrun/blob/main/examples/08_diff_engine.py).
- **An HPC array job:** no dedicated worked example yet; see [HPC](https://github.com/fariello/pubrun/blob/main/docs/hpc.md) for the parent-child `PUBRUN_META_REF` pattern.
- **An ML training and evaluation run:** no dedicated worked example yet; the pattern is the same one import, plus the deep-dive links above.

See [`examples/`](https://github.com/fariello/pubrun/tree/main/examples) for the full set (`00_*` through `11_*`, plus a `verify_all.py` harness).

## Features

- **Automatic Provenance Capture**: Records code version (git), the dependency graph, hardware specs, environment, inputs, logs, exit status, and resource usage into a structured, **schema-validated** `manifest.json`, without manual configuration.
- **Run-to-Run Comparison**: Semantically diffs two runs (`pubrun diff`, at basic / standard / deep depth) so you can see exactly what changed between them.
- **Codebase Drift Detection**: Compares the current code state against a run's snapshot to highlight changes.
- **Reproduce a Run**: Extracts the initialization commands needed to replicate a run's environment (`pubrun rerun`).
- **Secret Redaction**: Automatically detects and redacts passwords, tokens, and API keys in environment variables and CLI arguments *before* the manifest is written.
- **Scales from Laptop to Cluster**: Keeps provenance cheap across thousands of jobs on an HPC cluster: instead of each job re-recording the shared environment, jobs reference one parent snapshot. (See [HPC](https://github.com/fariello/pubrun/blob/main/docs/hpc.md) for `PUBRUN_META_REF` and the mechanics.)
- **Publication-Ready Methods**: Optionally generates LaTeX/Markdown methodology blocks from a run (`pubrun methods`), handy when a run needs to become a paper's Methods section.

## The Problem

Real runs depend on implicit state: the exact code, dependency versions, hardware, and environment that produced a result. Six months later, when a nightly job starts failing, or you need to know which version of your script produced last quarter's output, or you're comparing two runs to explain why the numbers moved (or shipping a model with confidence), that context has usually evaporated and has to be reconstructed from memory.

## The Solution

`pubrun` removes that friction by capturing the state automatically and making it comparable.

With a single `import pubrun`, the library quietly traces your run, records the code version and dependency graph, captures hardware and environment, detects codebase drift, and writes it all to a schema-validated manifest, so any run is immediately auditable, reproducible, and diffable against another. (Need a paper's Methods section from a run? `pubrun methods` will render one.)

## Built to be Trustworthy

Provenance tooling is only as trustworthy as its own engineering, so pubrun holds itself to the same bar:

- **Tested on every supported platform**: continuous integration runs the suite across Linux, macOS, and Windows on Python 3.8 through 3.14.
- **The manifest has a published contract**: its shape is defined by a JSON Schema (`schemas/manifest.schema.json`) that a conformance test enforces, so downstream tooling can rely on the format.
- **Zero runtime dependencies** on Python 3.11+ (a single `tomli` backport on 3.8-3.10), and non-intrusive by design: it never alters, slows, or crashes the program it observes.
- **A real changelog** and honest-documentation discipline: every capability claimed here is checkable against the code.

### Import Modes

By default, `import pubrun` starts tracking immediately. For more control, use namespaced import modes:

```python
import pubrun.auto as pubrun      # Explicit form of the default `import pubrun` (auto-start)
import pubrun.full as pubrun      # Capture everything, incl. console output (forces the console tee on)
import pubrun.noauto as pubrun    # Load API, start later with pubrun.start()
import pubrun.nopatch as pubrun   # Auto-start; no subprocess/console monkeypatching; standard hooks active
import pubrun.noconsole as pubrun # Auto-start; intercepts subprocesses and signals, but skips wrapping console streams
import pubrun.minimal as pubrun   # API only; no auto-start; all monkeypatches and hooks disabled
```

> **Not wrapping console streams?** In `noconsole`/`nopatch`/`minimal` (and by default in
> any mode, since `capture_mode` is `"off"`), pubrun does not tee stdout/stderr. To still
> record output, use `pubrun.print(...)`, a drop-in `print` replacement that writes to
> the run's `stdout.log` **without** monkeypatching your streams. The import mode is
> chosen once per process (first import wins); a mode that forbids console wrapping
> (`noconsole`/`nopatch`/`minimal`) cannot be re-enabled later via `start(console=...)`.
>
> Access it via the top-level package (`import pubrun; pubrun.print(...)`).

> **Silence a noisy block?** Wrap it in `with pubrun.paused(): ...` to suspend
> *recording* for that block. Output still prints and subprocesses still run,
> but the console tee and subprocess spy don't record them. It's thread-local
> (other threads keep being captured), nestable, and resumes automatically even
> on exception. Your `annotate()`/`phase()` markers and resource sampling are not
> affected. See the [API docs](https://github.com/fariello/pubrun/blob/main/docs/api.md#pubrunpaused--contextmanager).

#### Preset Modes Behavior Matrix

The matrix shows whether each mode **permits** a hook. Whether a permitted hook is
actually *active* is a separate, per-feature config decision (see the footnotes).

| Import Mode | Auto-Start | Intercept Subprocesses (`SubprocessSpy`) | Wrap Console Streams (`ConsoleInterceptor`) | Intercept Signals & Exits (`SignalExitCapture`) | Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`auto`** *(default)* | ✅ | ✅ | ⚠️ permitted, **off by default** | ✅ | Tracking begins automatically on import. |
| **`full`** | ✅ | ✅ | ✅ **forced on** | ✅ | Capture everything on import, including console output. Forces the console tee on regardless of config (the mirror of `noconsole`), while still respecting the Jupyter/non-TTY safety guards. |
| **`noauto`** | ❌ | ✅ | ⚠️ permitted, **off by default** | ✅ | Tracking must be started manually; the same hooks as `auto` apply once `start()` is called. |
| **`nopatch`** | ✅ | ❌ | ❌ | ✅ | Telemetry tracking begins automatically; no intrusive stdout/stderr wrapping or subprocess patching; standard exit/signal hooks remain active. |
| **`noconsole`** | ✅ | ✅ | ❌ | ✅ | Telemetry tracking begins automatically; intercepts subprocesses and signals, but skips wrapping stdout/stderr console streams. |
| **`minimal`** | ❌ | ❌ | ❌ | ❌ | API only; tracking must be started manually; all patches and hooks are disabled (zero-footprint mode). |

**Footnotes:**

- **Console wrapping is OFF by default in every mode EXCEPT `full`.** For the other
  modes the mode only *permits* console wrapping; the tee activates only when
  `[console].capture_mode` is set to `"basic"`/`"standard"`/`"deep"` (default `"off"`).
  `nopatch`/`noconsole`/`minimal` forbid it regardless of `capture_mode`. **`full`
  forces it on** regardless of `capture_mode` (still subject to the Jupyter/non-TTY
  guards), the mirror of how `noconsole` forces it off.
- **Subprocess interception** is permitted in `auto`/`full`/`noauto`/`noconsole` and is
  **on by default** there (`[capture.subprocesses].enabled` defaults `true`); disable it
  via that key. **Signal/exit capture** is likewise on by default where permitted
  (`[capture.signals].enabled` defaults `true`).
- **Background resource monitoring is NOT gated by import mode.** It samples in every
  mode whenever a run is active and `[capture.resources].depth != "off"` (default
  `"standard"`), even in `nopatch` and `minimal` once `start()` has been called.
- **Import mode is an absolute imperative.** An in-code `import pubrun.<mode>` overrides
  what any environment variable or config file says about scope/hooks (e.g. `full`
  forces console on even if config sets `capture_mode = "off"`; `noconsole` forces it
  off even if config sets `"standard"`). Only the launch-time CLI override
  `pubrun run --mode <mode> -- <script>` sits above the in-code import.

Or configure project-wide in `.pubrun.toml`:

```toml
[imports]
mode = "noauto"
```

Or use the CLI wrapper for scripts you can't modify:

```bash
pubrun run --mode minimal -- python script.py
```

Legacy approaches still work: `PUBRUN_AUTO_START=false` and `[core].auto_start = false`.

See [Configuration](https://github.com/fariello/pubrun/blob/main/docs/configuration.md) for the full `[imports]` section.

### Explicit Tracking Example

```python
import pubrun.noauto as pubrun

pubrun.start(output_dir="./custom_storage")
# ... your code ...
pubrun.stop()
```

Now extract your method paragraph for your paper:

```bash
pubrun methods --format latex
```

### Sample Output

> Computational experiments were executed on a machine running Linux (5.15.0-91-generic) equipped with an Intel(R) Core(TM) i7-12700H and 32.0 GB of RAM. The execution environment relied on Python 3.10.12 (CPython). Key dependencies tracked include torch (v2.0.1) and numpy (v1.24.3). To facilitate computational reproducibility, the exact state of the source code was anchored at Git commit `a1b2c3d4`. Environment and execution provenance were tracked using the `pubrun` library [1].

> [!NOTE]
> **Windows support**: `pubrun` works on Windows, but some capture engines have reduced functionality. Process `uid`/`gid` fields are not available, and `os.system` interception uses shell-string parsing rather than structured argument lists. All other features work identically.

---

## CLI Reference

The `pubrun` CLI (and its convenient shorthand alias `pbr`) provides a family of subcommands and diagnostic flags, all designed to work equally well on a developer laptop or across a Slurm array of thousands of HPC jobs. The most common are covered below; run `pubrun -h` for the full list and see the [CLI Reference](https://github.com/fariello/pubrun/blob/main/docs/cli.md) for exhaustive detail.

**Selecting a run.** Any command that takes a run accepts a **recency index** (`1` = most recent run, `2` = second most recent, and so on), a run-id prefix, or a directory path, e.g. `pubrun show 1`, `pubrun res 2`, `pubrun diff 1 2`. `pubrun status` prints the index in a leading `#` column.

**Output conventions.** Status lines use consistent, `NO_COLOR`-aware prefixes (`[INFO ]`, `[ OK  ]`, `[WARN ]`, `[ERROR]`, `[DEBUG]`) so output is easy to scan and grep (match on the level word, not the brackets).

### `pubrun init`
Initialize pubrun in the current project (writes a commented `.pubrun.toml`) and prints getting-started guidance.
```bash
pubrun init
```

### `pubrun report-bug` / `pubrun feedback`
Open the GitHub issue tracker and print environment diagnostics for copy-pasting. `report-bug` files a bug report or feature request; `feedback` sends general feedback.
```bash
pubrun report-bug
pubrun feedback
```

### `pubrun cite`
Generates the bibliographic citation for crediting this library in your paper.
```bash
pubrun cite --style bibtex
```

### `pubrun self-check`
Report-only checks of the **current machine** for pubrun performance/config pitfalls and install health (network filesystems, low RAM, high load, wedged/slow mounts, config errors). Never modifies anything. By default it **itemizes each check** (one `[ OK  ]`/`[WARN ]` line + a timing footer); `--quiet` prints just a one-line verdict.
```bash
pubrun self-check                    # itemized: what was checked + each outcome + timing
pubrun self-check --show-suggestions # add how to address each concern (-v)
pubrun self-check --quiet            # one-line verdict only
pubrun self-check --json             # full structured result (checks + findings)
pubrun self-check --strict           # exit non-zero if any warning fired
```

### `pubrun inspect`
Diagnose a completed run: what was captured, what wasn't, and how to capture more.
```bash
pubrun inspect [RUN_DIR] [--show-suggestions]
```

### `pubrun bench`
Run the pubrun overhead benchmark suite (auto-detects an HPC scheduler, Slurm/PBS/LSF/SGE, and offers to submit the job to a compute node). Every run starts with an uncaptured **baseline pass** (pubrun absent), then N measured passes: `--quick` (2x15), `--full`/default (3x30), or `--rigorous` (5x50). Requires a source checkout.
```bash
pubrun bench                        # default: baseline + 3 passes x 30 iterations
pubrun bench --quick                # baseline + 2 x 15
pubrun bench --rigorous             # baseline + 5 x 50 (tight CIs; can be slow)
pubrun bench --prepare-submission   # stage the safe file in a clean pubrun-share/ folder
```

**Contribute a benchmark result (attach, do not paste).** Each run writes two files: a private
`*.unredacted.json` (for your own analysis; embeds your hostname) and a shareable `*.redacted.json`.
`pubrun bench` prints which file is which, runs a share-safety check, and gives you a link to a GitHub
Issue Form. Attach the `*.redacted.json` file to that form (do not paste the JSON). The easiest safe
path is `pubrun bench --prepare-submission`, which copies only the redacted file into a clean
`pubrun-share/` folder so you cannot pick the wrong file. A validate-only check on the issue posts a
pass/fail receipt.

### `pubrun clean`
Interactively delete old run directories. Lists candidates with age and size, then prompts for confirmation.
```bash
pubrun clean                        # Interactive: list and confirm
pubrun clean --older-than 7d --yes  # Non-interactive: delete all completed runs older than 7 days
pubrun clean --status crashed --yes # Delete all crashed runs
pubrun clean --dry-run              # Preview what would be deleted
```

### `pubrun combined`
Interleave stdout and stderr logs chronologically from one or more runs.
```bash
pubrun combined [RUN_ID ...] --output combined.log
```

### `pubrun diff`
Generates a semantic comparison between two execution traces. `--standard` (the default) filters volatile noise and **summarizes** high-volume sections (e.g. subprocess counts) so it stays concise; `--basic` shows only high-signal user-facing changes; `--deep` shows everything. Add `--table` for a compact aligned view.
```bash
pubrun diff ./runs/pubrun-A ./runs/pubrun-B          # standard (default)
pubrun diff A B --basic --table                      # concise, tabular
```

### `pubrun meta`
Generates a standalone environment snapshot for HPC parent-child hydration.
```bash
pubrun meta --out ./runs/meta.json --deep
```

### `pubrun methods`
Translates raw JSON diagnostic payloads into publication-ready methodology paragraphs.
```bash
pubrun methods [RUN_DIR] --format markdown|latex
```

### `pubrun show`
A diagnostic viewer that surfaces execution timing, hardware, dependencies, and codebase drift. Accepts multiple run directories for sequential evaluation. (The name `report` remains as a backward-compatible alias.)
```bash
pubrun show ./runs/pubrun-A ./runs/pubrun-B --deep
```

### `pubrun show config`
Inspect the resolved configuration for three contexts, and see how any ambiguity resolved (keys overridden by a higher-precedence layer are annotated; add `--all` to annotate every key's source).
```bash
pubrun show config              # what `import pubrun` would use right now, in this directory
pubrun show run config [<id>]   # the config a past run actually used (default: most recent)
pubrun show default config      # the shipped built-in defaults only
```
See the [CLI Reference](https://github.com/fariello/pubrun/blob/main/docs/cli.md) for details.

### `pubrun rerun`
Extracts the exact shell command needed to reproduce a run.
```bash
pubrun rerun ./runs/pubrun-A
```

### `pubrun res` / `pubrun cpu` / `pubrun mem`
Render resource-utilization charts over a run's lifecycle: `res` shows the comprehensive picture (**peak/avg/min** for CPU and memory for the main process, and the process tree when captured, plus system memory/load/iowait and per-process I/O), while `cpu` and `mem` show a single focused chart. (`resources` remains as a backward-compatible alias of `res`.)
```bash
pubrun res [RUN_DIR]
pubrun cpu [RUN_DIR]
pubrun mem [RUN_DIR]
```

### `pubrun run`
Spawn a command with a specific import mode. Useful for CI, Slurm, and scripts you can't modify.
```bash
pubrun run --mode minimal -- python script.py
pubrun run --mode nopatch -- python train.py
```

### `pubrun status`
Lists all runs with their current status (completed, failed, interrupted, running, crashed, ghost), or inspects a specific run in detail. Detects active processes via cross-platform PID liveness checks.
```bash
pubrun status              # Compact table of all runs (with a leading # recency index)
pubrun status -v           # Verbose listing with PID, RSS, CPU, events
pubrun status 1            # Inspect the most recent run (recency index)
pubrun status a3f9         # Inspect a specific run by ID prefix
pubrun status --dir /path  # Scan a non-default output directory
```

### `pubrun ui`
Launches the interactive terminal user interface (TUI) dashboard to browse, inspect, and manage runs.
Note: Requires optional TUI dependencies (installable via `pip install "pubrun[tui]"` or `pip install textual rich`).
```bash
pubrun ui              # Open the interactive TUI manager (aliases: tui, gui)
pubrun ui --dir /path  # Scan a non-default output directory
```

### Diagnostic Flags

| Flag | Description |
|---|---|
| `--version` | Print the installed pubrun version and exit |
| `--create-config` | Bootstrap a fully commented `.pubrun.toml` file |
| `--info` | Display system capabilities and pubrun version |
| `--run-tests` | Execute the built-in self-test suite |

> `--show-config` is **deprecated** (hidden from `--help`); it still prints the built-in defaults but use [`pubrun show default config`](#pubrun-show-config) instead.

See [CLI Reference](https://github.com/fariello/pubrun/blob/main/docs/cli.md) for full details and examples.

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
| **broken pipe** | Run completed but received SIGPIPE (downstream consumer closed) |
| **running** | Lock file present, process is alive |
| **crashed** | Lock file present, process is dead |
| **ghost** | Run entered ghost mode (filesystem write failure at init) |

### Signal and Exit Code Capture

`pubrun` installs non-intrusive signal handlers that record OS signals (`SIGINT`, `SIGTERM`, `SIGHUP`, etc.) received during execution. These handlers **chain to any pre-existing handlers**: if the importing script has its own `SIGINT` handler, it is called normally after `pubrun` records the signal.

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

Setting `PUBRUN_META_REF` records the reference in each child's manifest and enables
**report-time hydration**: when you run `pubrun show` or `pubrun methods`, the orchestrator
detects the `PUBRUN_META_REF`, pulls in the parent `meta.json` context, and stitches the
complete hardware and dependency picture back into any section the child did not capture. It
also compares script timestamps against the parent snapshot and warns you if **environmental
drift** has been detected.

To actually reduce per-child overhead (so children don't each re-capture the identical
hardware/dependency graph), suppress the heavy engines on the child, e.g. run with
`capture.hardware.depth = "off"` and `capture.packages.mode = "off"` in `.pubrun.toml` (or the
equivalent `pubrun.start(capture=...)` overrides). Hydration then fills those suppressed
sections back in from the parent snapshot at report time. Note that the `core.profile` setting
alone does **not** suppress capture; use the explicit `capture.*` keys.

---

## Configuration

`pubrun` supports a hierarchical configuration system (highest to lowest precedence):

1. **API overrides**: `pubrun.start(output_dir="./runs")`
2. **Environment variables**: `PUBRUN_AUTO_START=false`
3. **Local project config**: `.pubrun.toml` or `.config/pubrun/config.toml`
4. **User home config**: `~/.config/pubrun/config.toml`
5. **Built-in defaults**: `default.toml` (shipped with the library)

### Generate a Configuration File
```bash
pubrun --create-config
```

See [Configuration Reference](https://github.com/fariello/pubrun/blob/main/docs/configuration.md) for all settings and examples.

---

## Security & Redaction

`pubrun` automatically detects and redacts sensitive values (passwords, tokens, API keys, credentials) in both environment variables and CLI arguments before writing them to the manifest. Redaction is **destructive by default**: raw values are replaced with `{"representation": "redacted"}`, and no hashes are generated, to prevent brute-force attacks.

Both environment variable and argv redaction are independently configurable:

```toml
[redaction]
env_enabled = true    # Redact matching environment variable values
argv_enabled = true   # Redact matching CLI argument values
```

See [Configuration Reference](https://github.com/fariello/pubrun/blob/main/docs/configuration.md) for the full redaction policy and regex pattern.

---

## Roadmap

### Future

1. **Sphinx / MkDocs integration**: Generate hosted API documentation from docstrings.
2. **Plugin / extension model**: Formal extension points for custom capture engines.
3. **Artifact registration API**: `register_artifact()` for tracking user-produced output files.
4. **Custom metadata API**: `register_metadata()` for injecting structured data into the manifest.

Recently shipped (see the [Changelog](https://github.com/fariello/pubrun/blob/main/CHANGELOG.md)): GitHub Actions CI, timestamped console capture, the `pubrun combined` log interleaver, `self-check`/`inspect` diagnostics, and the `pubrun bench` benchmark suite.

---

## Citation

If you use `pubrun` in your research, please cite it. Because no peer-reviewed
publication exists yet, cite the software itself (see `pubrun cite`, the `CITATION.cff`
file, or GitHub's "Cite this repository" button):

> Fariello, Gabriele. (2026). *pubrun* [Computer software]. https://github.com/fariello/pubrun. https://doi.org/10.5281/zenodo.PENDING

<!-- The DOI above is a PLACEHOLDER ("zenodo.PENDING") until the repository is enabled in
Zenodo and the first GitHub release mints a real concept DOI. See
.agents/plans/pending/20260706-citation-doi-and-enforceable-attribution.md (Phase 2):
replace "10.5281/zenodo.PENDING" here, in CITATION.cff, and in `pubrun cite` with the real
concept DOI, then add a "Cite this DOI" Zenodo badge. -->

The DOI is archived via [Zenodo](https://zenodo.org/); citing the **concept DOI**
(`10.5281/zenodo.PENDING`, above) always resolves to the latest archived version. This
citation will be updated to a peer-reviewed reference only *if and when* a journal article
(e.g. JOSS) is actually accepted; pubrun does not yet have one, and this section will not
imply otherwise. See the consolidated **License, Attribution & Citation** section below for
the required attribution.

---

## About the name

"pubrun" is short for *publication-ready runner*. The name also winks at the original pitch (let your code monitor itself and write its own Methods section while you step out to the pub), which is where the project's character (and its `pub`-flavored aliases) comes from.

## Acknowledgements

`pubrun` was redesigned and rewritten from pre-existing custom libraries, code fragments, scripts, and ideas spanning almost two decades, with the assistance of Google Antigravity for its official release.

## License & Attribution

`pubrun` is licensed under the **Apache License 2.0**. Copyright 2007-2026 Gabriele G. R.
Fariello. See the [LICENSE](https://github.com/fariello/pubrun/blob/main/LICENSE) and
[NOTICE](https://github.com/fariello/pubrun/blob/main/NOTICE) files for full terms.

**Attribution (required).** Under Apache-2.0 §4(d), any distribution of this software or a
derivative work must retain the `NOTICE` file and display its attribution reasonably
prominently. Concretely, derived/redistributed works must include the following, visibly,
in the project README (or equivalent top-level documentation) and in any "About"/credits
screen the software presents:

> Based on the original pubrun by Gabriele G. R. Fariello (https://github.com/fariello/pubrun).

For how to cite `pubrun` in academic work, see the [Citation](#citation) section above. The
attribution and citation requests impose no warranty or liability on the author; the software
is provided "AS IS" per the LICENSE.

---

[README](https://github.com/fariello/pubrun/blob/main/README.md) | [Architecture](https://github.com/fariello/pubrun/blob/main/docs/architecture.md) | [Functional Spec](https://github.com/fariello/pubrun/blob/main/docs/functional_spec.md) | [API](https://github.com/fariello/pubrun/blob/main/docs/api.md) | [CLI](https://github.com/fariello/pubrun/blob/main/docs/cli.md) | [Configuration](https://github.com/fariello/pubrun/blob/main/docs/configuration.md) | [Manifest](https://github.com/fariello/pubrun/blob/main/docs/manifest.md) | [Performance](https://github.com/fariello/pubrun/blob/main/docs/performance.md) | [Research Use](https://github.com/fariello/pubrun/blob/main/docs/research-use.md) | [HPC](https://github.com/fariello/pubrun/blob/main/docs/hpc.md) | [Changelog](https://github.com/fariello/pubrun/blob/main/CHANGELOG.md)
