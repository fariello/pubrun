# pubrun

> **Because you have better things to do than remember what PyTorch version you used six months ago.**

A stupidly-simple Python library that eliminates the boilerplate of documenting methodology, making it dramatically easier to publish, share, and reproduce your models and research.

## Overview

Researchers and engineers spend countless hours manually writing down what dependencies, environment variables, hardware constraints, and configurations were used to generate a specific outcome. `pubrun` automates this burden.

With a single `import pubrun`, it silently records:

- how a script was invoked
- where and when it ran
- environment and dependency matrices
- hardware constraints (GPU models, precisions, cores)
- console output (optional)
- configuration states

The goal is simple:

> Make publishing and reproducing results effortless.

## Vision

Modern scientific and computational workflows often rely on implicit state, which acts as a massive barrier to publishing clean, reproducible code. When it's time to publish a paper or ship a model, researchers are forced to retroactively piece together their methodology from memory.

`pubrun` exists to eliminate this friction.

The vision is a world where:

- documenting a run's environment requires zero manual overhead
- creating the "how to reproduce" guide for peers is entirely automated
- differences between runs are instantly transparent via machine-readable manifests
- reproducibility is practically free, reducing the tax on publishing

## Philosophy

`pubrun` is built around a few core principles:

### 1. Built for Publishing

The primary goal is not auditing: it's empowering researchers to painlessly verify and publish their computational methods so that others can validate and reproduce their exact work without guesswork.

### 2. Minimal friction

It should be easy to adopt:

```python
import pubrun
```

For most people, that's it. No frameworks, no restructuring, no heavy setup.

### 3. Manifest over logs

Structured data beats unstructured logs.

A run produces a machine-readable `manifest.json` that captures what matters, rather than relying on parsing console output.

### 4. Non-invasive by default

`pubrun` should not change program behavior.

- no heavy instrumentation by default
- no fragile hooks
- no unexpected side effects on import

### 5. Progressive depth

Basic usage should be simple.

Advanced capture should be available, but only when explicitly enabled.

### 6. Explicit and auditable

What was captured, what was not, and why must be clear.

Every section includes completeness status and respects redaction policies.

### 7. Built for comparison

The data model is designed from the start to support:

- `compare()`
- `diff()`
- `inspect()`
- future `replay()` guidance

## Key Features

- Manifest-first design (`manifest.json` per run)
- **Automated Methods Generation** (Writes publication methodology summaries natively)
- **Deep Metadata Introspection** (`pubrun meta` parser)
- Optional event stream for deeper diagnostics
- Tee-style console capture (`stdout` / `stderr`)
- Config-driven behavior with sensible defaults
- Run-scoped directory structure
- Structured, comparable output
- Designed for future comparison and replay tooling

## Quick Start

### Minimal usage
If you're a normal person running Python 3.11 or later:
```python
import pubrun
```
That's it. Nothing else.

If you've changed the config file so that `auto_run` is `false`:

```python
import pubrun
pubrun.start()
```

### Context manager

```python
from pubrun import tracked_run

with tracked_run():
    ...
```

### Decorator

```python
from pubrun import audit_run

@audit_run
def main():
    ...
```

## Output Structure

Each run produces a directory:

```
<base_dir>/runs/pubrun-<script>-<timestamp>-<pid>-<run_id>/
```

Example:

```
runs/pubrun-myscript-20260401T193331Z-12345-4f2a91c3/
```

Contents may include:

- `manifest.json` (required)
- `config.resolved.json`
- `methods.md` (Auto-generated computational methods text for publication)
- `stdout.log`
- `stderr.log`
- `events.jsonl`
- `summary.txt`

## Configuration

`pubrun` supports configuration from:

- user config: `~/.config/pubrun/`
- local project config: `.pubrun` or `.pubrun.toml`
- environment variables
- runtime arguments

### Create a default config

```bash
pubrun --create-config
```

This generates a fully commented config file with default values.

### Academic Reporting
To generate a "Computational Methods" paragraph natively derived from a run, you can pull it out of a captured manifest into Markdown or LaTeX:
```bash
pubrun methods ./runs/pubrun.../manifest.json --format latex
```
If you omit the file path, `pubrun` will automatically look out for your most recent local execution and generate the report identically.

### Diagnostics & Inspection
If you want to debug an environment without manually reading hundreds of `JSON` properties, `pubrun` can print a beautiful, structured analysis of any run dynamically (including resolving child-parent references and detecting code-drift!):
```bash
pubrun report --deep
```
By default, if you don't provide a specific `--run` directory flag, it intelligently grabs the most recent execution from your local `./runs/` folder.

### Global Snapshotting (HPC & Distributed Jobs)
If you run thousands of Array jobs concurrently, you don't want each run wasting gigabytes logging the exact identical heavy dependency graphs. `pubrun` enables you to snap an overarching master Environment Node:
```bash
pubrun meta --out ./runs/meta.json --deep
```
Set `PUBRUN_META_REF=meta.json` in your bash file and all lightweight child executions will beautifully hydrate the parent dependencies statically before publication dynamically!

## Console Capture

Optional tee-style capture of:

- `stdout`
- `stderr`

Modes:

- off
- basic
- standard (with timestamps)
- deep

Example output:

```
2026-04-01T19:33:31.482Z +00.482 stdout Starting analysis
```

## Manifest

Each run produces a structured `manifest.json` describing:

- invocation details
- environment and dependencies
- timing and outcome
- system information
- configuration used
- artifact references

The manifest is:

- machine-readable
- versioned
- designed for comparison across runs

Schema available at:

```
schemas/manifest.schema.json
```

## Status

Early-stage design (Draft v0.2)

## Remaining Work (v1 Roadmap)

While the Core Capture engines are fully functional out of the box, `pubrun` is still under active development to reach v1 complete status. Things left to do:
- **Comparison Tooling:** Implement the `pubrun.diff()` and `compare()` APIs to natively evaluate variance between two separate `manifest.json` runs.
- **Event Streaming Phase:** Full implementation of `events.jsonl` output parsing for internal phase tracking.
- **Configuration Hierarchy Engine:** Finish mapping `.pubrun.toml` ingestion from home directory logic and cascading overrides.
- **JOSS Submission:** Finalize documentation targeting the Journal of Open Source Software.

## License

Released under the BSD 3-Clause License.

Copyright (c) 2007-2026 Gabriele Fariello

See the LICENSE file for full terms.
