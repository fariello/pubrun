# runtrace Architecture

> Status: Draft v0.1
> Audience: Developers and contributors.

## 1. Core Philosophy: Manifest-First

`runtrace` is built around a **manifest-first** philosophy. The core contract between the Python tracker (producer) and any downstream tools (consumers, CLIs, UI, comparison tools) is the `manifest.json`.

The precise, definitive structure of this manifest is defined by the formal JSON schema located at `schemas/manifest.schema.json`.

## 2. System Components

The system is logically divided into several key components:

### 2.1 Configuration Resolver
Responsible for merging and applying configuration settings from various sources.
- **Precedence:** API/Args > Env Vars > Local Config (`.runtrace`) > User Home Config (`~/.config/runtrace/`) > Defaults.
- **Output:** A single resolved configuration snapshot (`config.resolved.json`) that dictates the capture depth for all downstream components.

### 2.2 Capture Engine
The orchestrator that manages individual data collection routines (e.g., pulling Git data, sniffing package versions, identifying host architecture).
- Subdivides work into distinct **Capture Categories** (e.g., `timing`, `host`, `python`, `hardware`).
- Operates gracefully even when individual data sources fail (see *Partial Failures* below).

### 2.3 Event Streamer
An optional component responsible for streaming real-time structured execution events to `events.jsonl`.
- Ensures low-latency tracking of `phase_started`, `phase_ended`, and generic custom annotations.

### 2.4 Console Manager
An optional tee-style wrapper around standard streams.
- Re-routes or duplicates `stdout` and `stderr` to capture logs without disrupting the console experience.

### 2.5 Artifact Writer
Responsible for atomically generating the isolated **Run Directory** upon initialization and serializing all outputs (`manifest.json`, logs, configs) reliably, even during sudden termination.

## 3. Data Model & Resilience

### 3.1 The Schema
The data model directly mirrors the hierarchical structure of `schemas/manifest.schema.json`. Every system component dumps its output into a designated section of the `runtrace-manifest` type.

### 3.2 Capture States & Partial Failures
Data capture intrinsically carries a risk of failure (e.g., missing permissions to read GPU stats, lack of a `.git` folder). 
`runtrace` does not use Python exceptions to halt tracking upon these failures.

Instead, every single data section implements a `capture_state` object.
If the Git metadata cannot be read, the program continues executing, but the `git` section is recorded with `"capture_state": {"status": "unavailable"}` or `"failed"`.
This guarantees that the user script is never broken by the trace tooling.

### 3.3 Redaction
Data model layers handle secrets via the `redacted_value` object. Sensitive strings are intercepted, and their raw values are swapped with a representation indicating they were `"redacted"` or `"hashed"`, preserving privacy securely.
