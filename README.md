# runtrace

A lightweight Python library for capturing execution context to enable reproducibility, comparison, and troubleshooting of script runs.

---

## Overview

`runtrace` is a provenance library designed to make reproducibility the default.

With minimal effort, it records:

- how a script was invoked
- where and when it ran
- environment and dependency details
- system and resource context
- console output (optional)
- configuration used for the run

The goal is simple:

> Make every run explainable.

---

## Key Features

- Manifest-first design (`manifest.json` per run)
- Optional event stream for deeper diagnostics
- Tee-style console capture (`stdout` / `stderr`)
- Config-driven behavior with sensible defaults
- Run-scoped directory structure
- Structured, comparable output
- Designed for future `compare()`, `diff()`, and `replay()` capabilities

---

## Quick Start

### Minimal usage

```python
import runtrace
runtrace.start()
```

### Context manager

```python
from runtrace import tracked_run

with tracked_run():
    ...
```

### Decorator

```python
from runtrace import audit_run

@audit_run
def main():
    ...
```

---

## Output Structure

Each run produces a directory:

```
<base_dir>/runs/runtrace-<script>-<timestamp>-<pid>-<run_id>/
```

Example:

```
runs/runtrace-myscript-20260401T193331Z-12345-4f2a91c3/
```

Contents may include:

- `manifest.json` (required)
- `stdout.log`
- `stderr.log`
- `events.jsonl`
- `config.resolved.json`
- `summary.txt`

---

## Configuration

`runtrace` supports configuration from:

- user config: `~/.config/runtrace/`
- local project config: `.runtrace` or `.runtrace.toml`
- environment variables
- runtime arguments

### Create a default config

```bash
python -m runtrace --create-config
```

This generates a fully commented config file with default values.

---

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

---

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

---

## Design Principles

- Minimal friction
- Structured data over logs
- Reproducibility first
- Non-invasive by default
- Explicit over implicit
- Forward-compatible with comparison and replay tooling

---

## Status

Early-stage design (Draft v0.1)

---

## License

Released under the BSD 3-Clause License.

Copyright (c) 2007-2026 Gabriele Fariello

See the LICENSE file for full terms.
