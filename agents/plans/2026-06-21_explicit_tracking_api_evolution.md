# Implementation Plan - Explicit Telemetry and Provenance API Evolution

This document details the architectural design, engineering constraints, and implementation phases to transition `pubrun` from a purely passive execution monitoring tool to a robust developer-centric API for explicit tracking, scientific dataset provenance, and non-intrusive environment auditing.

---

## Background & Rationale

Currently, `pubrun` captures execution telemetry through automatic, global monkeypatching (e.g., wrapping `sys.stdout`/`sys.stderr` and patching `subprocess.Popen`). While effective for zero-configuration setups, this has two major drawbacks in scientific computing:
1. **System Intrusiveness**: Global monkeypatching can conflict with profiling tools, testing frameworks (like pytest), or alternative logger configurations.
2. **Dataset Ignorance**: Simply tracking environment variables and CLI arguments fails to capture the true lineage of a run: **what dataset was consumed, and what metrics or models were generated?**

By introducing an **Explicit Tracking API**, we empower developers with standard, zero-overhead tools (`print`, `report`, `artifact`, `open`, `subprocess`) that capture deep execution metadata natively.

---

## Phase Dependency & Execution Order

```text
[Phase 1: report & artifact API]
      │
      ▼
[Phase 2: pubrun.print API]
      │
      ▼
[Phase 3: pubrun.open Dataset Provenance] (Hashed streams, no-OOM proxy)
      │
      ▼
[Phase 4: Explicit Subprocess Wrappers]
```

---

## Detailed Specifications

---

### Phase 1: Structured Reports and Artifacts

#### Goal
Allow developers to save scientific reports (dictionaries/JSON) and artifacts (plots, binaries, weights) directly in the unique run directory, automatically linking them to the execution manifest.

#### Architecture & Implementation Details
- **`pubrun.report(name: str, data: Any) -> None`**:
  - If `data` is a `dict` or `list`, it is written to the run directory as `{name}.json` formatted via `json.dumps(data, indent=2)`.
  - If `data` is a string or other type, it is written as plain text to `{name}.txt` using `str(data)`.
  - To ensure discoverability, it emits a `report` annotation event into `events.jsonl` with the path and a metadata summary preview.
- **`pubrun.artifact(filename: str, content: Any) -> None`**:
  - Writes raw `bytes` (using `write_bytes`) or `str` (using `write_text`) to `run_dir / filename`.
  - Emits an `artifact` annotation event in `events.jsonl`.
- **Safety**: Wrap file IO in a `try/except` block logging to `logging.getLogger("pubrun")` so that storage space exhaustion or file locks never crash the host application.

---

### Phase 2: Shorter `pubrun.print` API

#### Goal
Provide a drop-in replacement for Python's built-in `print` that writes to the console and simultaneously logs the output inside the run directory (`stdout.log`), even if global console interception is disabled.

#### Architecture & Implementation Details
- **`pubrun.print(*args: Any, **kwargs: Any) -> None`**:
  1. Captures the printed string by replicating the builtin print formatting (`sep.join(map(str, args)) + end`).
  2. Forwards the call immediately to Python's standard `print(*args, **kwargs)` using `sys.__stdout__` or the user's overridden stream.
  3. If a run is active, checks if `run.run_dir / "stdout.log"` exists. It appends the string to this file.
  4. If `core.profile` is set to `standard` or `deep`, prepends a UTC ISO 8601 timestamp to the logged line (e.g., `[2026-06-21T01:57:17.123Z] msg`).

---

### Phase 3: Dataset Provenance with `pubrun.open`

#### Goal
Provide a drop-in wrapper around Python's built-in `open()` that hashes input datasets on-the-fly without loading them entirely into memory, avoiding Out-Of-Memory (OOM) crashes on large inputs.

#### Architectural Constraints & Hashing Strategy
If a user loads a 30GB dataset file, calling `.read()` and hashing the entire string in memory would exceed system RAM constraints. We must hash the file **incrementally** as the user reads it.

```text
User Code ──► ProvenanceFileProxy ──► Incremental Hash (SHA-256)
                       │
                       ▼
              Target file on disk
```

- We will implement a `ProvenanceFileProxy` wrapper class that wraps the underlying file stream:
  - Internally instantiates `self._hash = hashlib.sha256()`.
  - Overrides read operations: `.read(size)`, `.readline()`, `.readlines()`, and `__iter__()`.
  - As data chunks are read from the disk and passed back to the user, they are forwarded to `self._hash.update(chunk_data)`.
  - Overrides `.close()`. Upon closing the file, the proxy finalizes the hash (`self._hash.hexdigest()`), queries the file size via `os.path.getsize(file)`, and registers the metadata in the active `Run` manifest under the `data_files` section:
    ```json
    "data_files": {
      "inputs": [
        {
          "path": "/absolute/path/to/dataset.csv",
          "size_bytes": 1024567,
          "sha256": "8f3cf...",
          "accessed_at_utc": 1780250544.123
        }
      ],
      "outputs": []
    }
    ```
- For **outputs** (files opened with `"w"`, `"wb"`, or `"a"`): We register their final paths, sizes, and modification timestamps on `.close()`.

---

### Phase 4: Explicit Subprocesses and Popen

#### Goal
Provide wrappers under the `pubrun.subprocess` namespace that allow users to run and track shell commands explicitly, without turning on global process interception.

#### Architecture & Implementation Details
- **`pubrun.subprocess.run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess`**:
  - Captures start time and command arguments.
  - Temporarily disables the global `SubprocessSpy` (if active) during execution to prevent duplicate telemetry logging.
  - Calls `subprocess.run(*args, **kwargs)`.
  - Captures exit code and end time.
  - Logs the record to `manifest.json` under `"subprocesses"`.
- **`pubrun.subprocess.Popen(*args: Any, **kwargs: Any) -> subprocess.Popen`**:
  - Returns a wrapped `subprocess.Popen` subclass that intercepts `.wait()`, `.poll()`, or `.communicate()` to finalize exit code capture and log timing data.

---

## Schema Changes (`schemas/manifest.schema.json`)

We will add a new top-level optional property `"data_files"` to the JSON Schema:
```json
"data_files": {
  "type": "object",
  "properties": {
    "inputs": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "path": { "type": "string" },
          "size_bytes": { "type": "integer" },
          "sha256": { "type": "string" },
          "accessed_at_utc": { "type": "number" }
        },
        "required": ["path", "size_bytes", "sha256", "accessed_at_utc"]
      }
    },
    "outputs": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "path": { "type": "string" },
          "size_bytes": { "type": "integer" },
          "sha256": { "type": "string" },
          "modified_at_utc": { "type": "number" }
        },
        "required": ["path", "size_bytes", "sha256", "modified_at_utc"]
      }
    }
  }
}
```

---

## Verification Plan

### Automated Tests (`tests/test_explicit_api.py`)

#### Phase 1: report & artifact Verification
- **`test_report_json`**: Run a script emitting `pubrun.report("eval", {"score": 0.99})`. Verify `runs/pubrun-*/eval.json` exists with the exact dictionary, and that `pubrun report` prints `report: eval {'score': 0.99}` in the event stream timeline.
- **`test_report_string`**: Emit a raw text report, verify it gets formatted as `{name}.txt`.

#### Phase 2: print Verification
- **`test_pubrun_print_logging`**: Call `pubrun.print("test line")` with global console capture disabled. Verify stdout receives the text, and that `stdout.log` inside the run directory is created and contains the printed string.

#### Phase 3: open (Incremental Hashing) Verification
- **`test_open_input_provenance`**: Create a 5MB text file. Open it via `pubrun.open()`, read 1MB chunks sequentially, and close it. Verify:
  1. The dataset hash is computed correctly on-the-fly.
  2. The manifest contains the file's path, size, and hash under `data_files.inputs`.
  3. Memory consumption remains low (no full-file buffer load).

#### Phase 4: subprocess Verification
- **`test_explicit_subprocess_run`**: Execute `pubrun.subprocess.run(["echo", "hello"])`. Verify it executes successfully and is added to the subprocesses registry of the manifest.
