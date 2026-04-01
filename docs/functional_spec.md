# runtrace Functional Specification

> Status: Draft v0.1
> Purpose: Defines functional requirements aligned with architecture.
> Audience: Developers and contributors.

## 1. Purpose

`runtrace` captures execution context for reproducibility, troubleshooting, and comparison of Python runs.

The library must support a very low-friction user model. It should be usable in multiple ways, including:

```python
import runtrace
```

or:

```python
from runtrace import start
```

The product goal is that a user can get useful behavior with minimal ceremony, while still allowing deeper, explicit control when desired.

## 2. Core model

- manifest-first design
- optional event stream
- optional console capture
- configurable defaults from config files
- explicit APIs for deeper control

## 3. Import and activation model

### 3.1 Import compatibility

The package MUST support standard Python import patterns, including:

```python
import runtrace
```

and:

```python
from runtrace import start
from runtrace import tracked_run
from runtrace import audit_run
```

### 3.2 Lightweight import requirement

A plain import MUST be lightweight and safe.

Importing `runtrace` MUST NOT:

- significantly slow startup
- fail if optional dependencies are unavailable
- unexpectedly wrap `stdout` or `stderr` unless configured to do so
- unexpectedly write output unless configured to do so

### 3.3 Auto-start support

The library SHOULD support configuration-driven auto-start behavior so that a simple:

```python
import runtrace
```

can provide useful automatic capture when enabled by policy or configuration.

This behavior MUST be configurable and easy to disable.

### 3.4 Explicit activation support

The library MUST also support explicit activation via APIs such as:

```python
import runtrace
runtrace.start()
```

and:

```python
from runtrace import tracked_run

with tracked_run():
    ...
```

## 4. Required artifacts

Each run MUST produce a `manifest.json` containing structured metadata about the run.

The manifest is the canonical output for the run.

It MUST be usable without requiring event replay.

Each run MUST also produce a `config.resolved.json` containing the final configuration used for the run.

## 5. Capture categories

Core categories:

- run identity
- timing
- invocation
- process
- host
- host architecture
- python runtime
- packages
- environment
- git provenance
- errors

Optional categories:

- hardware
- resources
- subprocesses
- console
- artifacts
- determinism
- framework plugins

Each category MUST be independently configurable.

## 6. Profiles

Built-in profiles:

- minimal
- default
- deep

Each profile controls capture depth.

Categories SHOULD also support per-category depth controls such as:

- off
- basic
- standard
- deep

## 7. Events

Optional JSONL event stream with structured events.

Minimum event types:

- `phase_started`
- `phase_ended`
- `exception_captured`

Optional event types may include:

- subprocess events
- console events
- resource samples
- custom annotations

## 8. Console capture

Supports tee-style capture of `stdout` and `stderr`.

Modes:

- off
- basic
- standard
- deep

Produces:

- `stdout.log`
- `stderr.log`

Optional:

- `combined.log`

The implementation MUST preserve normal console behavior as closely as practical.

## 9. Completeness and redaction

Each manifest section MUST report status:

- complete
- partial
- unavailable
- suppressed
- failed

The system MUST support:

- redaction
- hashing
- allowlist / denylist control

Secrets MUST NOT be captured by default.

## 10. Configuration system

### 10.1 Purpose

`runtrace` MUST support a configuration system that allows users to define default behavior without modifying every script.

### 10.2 Configuration discovery

The library MUST look for configuration in standard locations.

At minimum, it MUST support:

- `~/.config/runtrace/`
- a runtrace config file in the user's home configuration area
- a `.runtrace`-style config file in the directory from which the program was started

Examples of acceptable supported paths include:

- `~/.config/runtrace/config.toml`
- `~/.config/runtrace/runtrace.toml`
- `~/.runtrace`
- `<start_working_directory>/.runtrace`
- `<start_working_directory>/.runtrace.toml`

The exact supported set may be defined more precisely later, but the product MUST support both:

- user-level defaults in the home directory
- per-project or per-run-directory defaults in the directory from which the process was launched

### 10.3 Configuration precedence

Configuration precedence SHOULD be:

1. explicit runtime arguments and API arguments
2. environment-variable overrides
3. local project / current-start-directory config
4. user home config
5. built-in defaults

This precedence order MUST be documented.

### 10.4 Configuration contents

The configuration MUST support defaults for at least:

- profile / capture depth
- output base directory
- console capture mode
- event capture enablement
- redaction policy
- environment capture settings
- package capture settings
- subprocess capture settings
- artifact behavior
- auto-start behavior
- logging / summary behavior

### 10.5 Configuration format

The configuration format SHOULD be human-readable, versionable, and easy to comment.

A commented config format such as TOML-style or INI-style is acceptable, provided it supports a clear, maintainable default configuration file.

### 10.6 Configuration loggin
The system MUST produce a resolved configuration snapshot per run and store it in the run directory.

## 11. Create-config behavior

### 11.1 CLI support

When invoked via Python as a command-line entry point, `runtrace` MUST support a config-generation command such as:

```bash
python -m runtrace --create-config
```

A direct CLI entry point may also support the same behavior.

### 11.2 Generated config requirements

The generated config file MUST:

- be fully commented
- include all major configurable options
- show the default values already set
- be suitable for immediate user editing
- be written to a clearly defined location
- avoid overwriting an existing config unless explicitly told to do so

### 11.3 Target location

The command SHOULD support generating:

- a user-level config
- a local config in the current directory

If no target is specified, the default location and behavior MUST be documented clearly.

### 11.4 Safety

If a config file already exists, the command MUST either:

- refuse to overwrite it by default, or
- create a uniquely named alternative, or
- require an explicit overwrite flag

Silent destructive overwrite is NOT allowed.

## 12. Run directory (revised)

Each run MUST be stored in a dedicated, uniquely named run directory.

### Default structure

```text
<base_dir>/runs/runtrace-<script>-<timestamp>-<pid>-<run_id>/
```

Example:

```text
<base_dir>/runs/runtrace-myscript-20260401T193331Z-12345-4f2a91c3/
```

### Requirements

- A `runs/` subdirectory SHOULD be used by default to avoid cluttering the base directory.
- Each run directory name MUST:
  - include a UTC timestamp
  - include a script or entry-point identifier
  - include the process ID (PID)
  - include a short unique run identifier
- Directory creation MUST be race-safe.
- Run directory names MUST be globally unique within the base directory.
- The naming scheme MUST be deterministic and machine-parsable.

### Contents

Each run directory contents MUST include:

- `manifest.json`
- `config.resolved.json`

Optional contents may include:

- `stdout.log`
- `stderr.log`
- `events.jsonl`
- `summary.txt`

### Configuration capture

Each run directory MUST include a representation of the effective configuration used for that run.

Recommended:

- config.resolved.json (fully resolved, machine-readable)
- optionally config.sources.json (describing config provenance)

The resolved configuration MUST:

- reflect all defaults, overrides, and runtime parameters
- represent the actual behavior used during execution
- be sufficient to understand how capture behavior was determined

If original config files were used (e.g., ~/.config/runtrace/..., .runtrace), the system MAY also:

- record their paths
- include hashes
- optionally snapshot them (configurable)

### Rationale

The run directory provides namespace isolation for all artifacts associated with a run. This allows internal filenames to remain simple and stable while guaranteeing uniqueness.

Capturing the resolved configuration ensures that each run is fully explainable and reproducible, even when configuration is composed from multiple sources or changed between runs.

## 13. Replay / compare readiness

The manifest MUST support future:

- `compare()`
- `diff()`
- `replay()` guidance

To support this, it MUST include structured and normalized information about:

- command line
- working directory
- Python executable
- package versions
- environment hints
- git state
- artifacts
- output locations

Replay is advisory, not guaranteed.

The resolved configuration stored in the run directory MUST be structured and normalized to support comparison across runs.

## 14. API

Core APIs:

- `start()`
- `stop()`
- `get_current_run()`

Optional APIs:

- `register_artifact()`
- `register_metadata()`
- `register_seed()`
- `mark_phase()`

Convenience interfaces SHOULD include:

- decorator support
- context-manager support
- import-safe top-level exports

## 15. Failure behavior

The system MUST:

- never crash the host script due solely to capture failure
- emit a partial manifest if needed
- record capture errors
- degrade gracefully when optional features are unavailable
- each run directory contains a resolved configuration snapshot

## 16. Acceptance criteria

A valid v1 implementation must satisfy all of the following:

1. `import runtrace` works cleanly
2. `from runtrace import start` works cleanly
3. plain import is lightweight and safe
4. configuration is discovered from home and local locations
5. `python -m runtrace --create-config` creates a fully commented default config
6. one-line explicit usage works
7. a manifest is produced for tracked runs
8. failures are captured without breaking the host script
9. console teeing is configurable
10. output is deterministic enough for comparison tooling

## 17. Summary

`runtrace` provides structured, low-friction run provenance with optional depth and extensibility.

It must support both explicit activation and configuration-driven low-friction behavior, including standard import patterns, discoverable configuration files, and generation of a fully commented default configuration file for users who want to set default policy once and reuse it across scripts.
