# runtrace Architecture

> Status: Draft v0.1  
> Purpose: Defines architectural principles and constraints for runtrace.  
> Audience: Developers and contributors.

## 1. Overview

`runtrace` is a lightweight Python library that captures execution context for a run to support:

- reproducibility (primary)
- troubleshooting (secondary)
- comparison and inspection (future)

The library is designed for minimal friction. A user should be able to include it with one line and immediately gain meaningful, structured provenance data.

## 2. Core architectural model

runtrace uses a hybrid snapshot + event model.

### Snapshot (canonical)
Each run produces a manifest that represents the run as a whole.

### Events (optional)
Structured events may be emitted during execution.

## 3. Run lifecycle

### Initialization
Capture early metadata and assign run ID.

### Active capture
Collect events and update summary fields.

### Finalization
Write manifest and finalize outputs.

### Abnormal termination
Best-effort partial capture.

## 4. Data model principles

- Structured
- Versioned
- Partially sparse
- Semantically stable

## 5. Manifest design

Example top-level structure:

```
{
  "schema_version": "1.0",
  "run": {},
  "timing": {},
  "invocation": {},
  "host": {},
  "python": {},
  "packages": {},
  "environment": {},
  "git": {},
  "resources": {},
  "console": {},
  "subprocesses": [],
  "artifacts": [],
  "errors": {}
}
```

## 6. Event model

Events include type, timestamp, run ID, and payload.

## 7. Immutable vs mutable

- Mutable during run
- Immutable after finalization

## 8. Normalization rules

- UTC timestamps
- deterministic ordering
- consistent naming

## 9. Observed vs derived vs inferred

Clear distinction between data types.

## 10. Capture categories

Modular and configurable.

## 11. Progressive depth model

off, basic, standard, deep

## 12. Console capture model

Supports tee of stdout/stderr with optional timestamps.

## 13. Run directory model

Each run gets its own directory.

## 14. Race safety and durability

Use atomic creation and avoid exists-based naming.

## 15. Console metadata

Console logs linked in manifest.

## 16. Subprocess model

Separate from console capture.

## 17. Public API

Core primitives: start, stop, annotate, etc.

## 18. Plugin model

Optional, isolated extensions.

## 19. Schema extensibility

Versioned and forward-compatible.

## 20. Failure model

Best-effort capture under failure.

## 21. Activation model

Explicit start preferred.

## 22. Non-goals

Not a workflow engine or experiment platform.

## 23. Design constraints

Manifest is canonical, modular capture, normalization required.

## 24. Summary

runtrace is a low-friction provenance layer for Python execution.
