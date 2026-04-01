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

## Vision

Modern Python workflows often rely on implicit state:

- environment differences
- dependency drift
- hidden configuration
- machine-specific behavior

`runtrace` aims to eliminate this ambiguity.

The vision is a world where:

- every run can be understood after the fact
- differences between runs are transparent
- debugging is based on facts, not guesswork
- reproducibility is a default, not an afterthought

---

## Philosophy

`runtrace` is built around a few core principles:

### 1. Reproducibility first

The primary goal is not logging or monitoring, but ensuring that a run can be understood and, as much as possible, reproduced.

### 2. Minimal friction

It should be easy to adopt:

```python
import runtrace
runtrace.start()
```

No frameworks, no restructuring, no heavy setup.

### 3. Manifest over logs

Structured data beats unstructured logs.

A run produces a machine-readable `manifest.json` that captures what matters, rather than relying on parsing console output.

### 4. Non-invasive by default

`runtrace` should not change program behavior.

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

---

## Key Features

- Manifest-first design (`manifest.json` per run)
- Optional event stream for deeper diagnostics
- Tee-style console capture (`stdout` / `stderr`)
- Config-driven behavior with sensible defaults
- Run-scoped directory structure
- Structured, comparable output
- Designed for future comparison and replay tooling

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

## Status

Early-stage design (Draft v0.2)

---

## License

Released under the BSD 3-Clause License.

Copyright (c) 2007-2026 Gabriele Fariello

See the LICENSE file for full terms.
