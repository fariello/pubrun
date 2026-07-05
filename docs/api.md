[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [Changelog](../CHANGELOG.md)

# pubrun Python API

`pubrun` provides a minimal Python API for execution tracing. Most users only need `import pubrun`. For deeper control, the API offers explicit start/stop, custom annotations, phase timing, and semantic diffing.

---

## 1. Zero-Friction Invocation

By default, simply importing the module starts a standard trace automatically.

```python
import pubrun

# Your code is already being tracked.
print("Training model...")
```

> [!NOTE]
> By default, `pubrun` does NOT capture stdout/stderr (the default `capture_mode` is `"off"`). To enable output logging, set `capture_mode = "standard"` in `.pubrun.toml` or pass `pubrun.start(console={"capture_mode": "standard"})`. See [Configuration Reference](configuration.md) for all console options including Jupyter auto-detection and non-TTY overrides.

### Import Modes

Use namespaced imports to control import-time behavior without config files:

```python
import pubrun.noauto as pubrun   # Load API only. Start manually later.
import pubrun.nopatch as pubrun  # Auto-start, skip subprocess/console patches, keep signal hooks.
import pubrun.noconsole as pubrun # Auto-start, skip console patch, keep subprocess/signal hooks.
import pubrun.minimal as pubrun  # API only. No auto-start, all hooks/patches disabled.
```

| Mode | Auto-start | Global hooks/patches | Use case |
|------|-----------|-------------|----------|
| `auto` | Yes | Yes (permitted) | Default. Auto-start on import. Console tee is permitted but off unless `capture_mode` is set (see note above). |
| `noauto` | No | Yes | Libraries or scripts that start tracking explicitly. |
| `nopatch` | Yes | No patches (signals active) | When monkey-patching conflicts with other tools (debuggers, profilers). |
| `noconsole` | Yes | Subprocesses/signals active | When stdout/stderr console wrapping is undesirable but subprocesses/signals tracking is needed. |
| `minimal` | No | No | Shared library code that may or may not want tracking. |

Alternatively, configure project-wide:

```toml
[imports]
mode = "noauto"
```

Or use the CLI wrapper:

```bash
pubrun run --mode minimal -- python script.py
```

Legacy approaches still work: `PUBRUN_AUTO_START=false` and `[core].auto_start = false`.

---

## 2. Explicit Tracking Control

When auto-start is disabled, manually control the run lifecycle.

### `pubrun.start(**overrides) → Run`

Begins tracking. Returns the active `Run` instance. API overrides always take the highest precedence over any config file.

```python
import pubrun

tracker = pubrun.start(profile="deep", output_dir="./custom_storage")

# ... do work ...

pubrun.stop()
```

**Override syntax:** For convenience, common `[core]` keys can be passed as flat kwargs:

```python
pubrun.start(profile="deep")                    # Equivalent to core={"profile": "deep"}
pubrun.start(output_dir="./runs")               # Equivalent to core={"output_dir": "./runs"}
pubrun.start(core={"profile": "deep"})          # Explicit nested form also works
```

Flat shortcuts: `profile`, `output_dir`, `auto_start`, `meta_ref`. All other overrides use nested dicts matching the TOML structure (e.g., `console={"capture_mode": "off"}`).

> [!NOTE]
> If both flat and nested forms are passed for the same key, the flat shortcut wins: `start(core={"profile": "minimal"}, profile="deep")` results in `profile = "deep"`.

### `pubrun.stop()`

Finalizes the active run: writes the manifest, closes log files, and resets internal state. Safe to call even if no run is active.

The run outcome is determined automatically:
- `"completed"` — Normal exit, no termination signals received.
- `"failed"` — An unhandled exception occurred (set by `tracked_run` / `audit_run`).
- `"interrupted"` — The process received SIGINT, SIGTERM, or SIGHUP during execution (even if user code caught `KeyboardInterrupt`).
- `"ghost"` — The run entered ghost mode due to filesystem failure at initialization.

```python
pubrun.stop()
```

### `pubrun.get_current_run() → Run | None`

Returns the active `Run` tracker instance, or `None` if no run is active. Useful for conditional logic or accessing the `run_dir` path.

```python
run = pubrun.get_current_run()
if run:
    print(f"Artifacts will be saved to {run.run_dir}")
```

---

## 3. Custom Annotations

Inject custom key-value events into the `events.jsonl` stream during an active run.

### `pubrun.annotate(message=None, **payload)`

```python
import pubrun

def process_chunk(matrix):
    pubrun.annotate("chunk_evaluation", shape=str(matrix.shape), loss=0.54)
```

If no run is active, `annotate()` silently does nothing (by default). This behavior is configurable:

```toml
[events]
enabled = true

# What happens if annotate() is called with no active run?
# "ignore" (default, safest) | "warn" | "error" (raises RuntimeError)
on_inactive_annotate = "ignore"
```

---

## 4. Phase Timing

Delimit named timing regions around sections of your code.

### `pubrun.phase(name) → ContextManager`

```python
import pubrun

with pubrun.phase("gradient_descent"):
    model.backward()
    optimizer.step()
```

This emits `phase_start` and `phase_end` events with timing metadata. If an exception occurs inside the phase, the `phase_end` event records the error type.

Phase calls are safe to use even without an active run — they become silent no-ops.

---

## 5. Lifecycle Wrappers

### `pubrun.tracked_run(**overrides) → ContextManager`

A context manager that wraps `start()` and `stop()` for you. If an exception occurs, the run is finalized with `outcome = "failed"`.

```python
from pubrun import tracked_run

with tracked_run(events={"enabled": True}) as ctx:
    # ctx.run_tracker is the active Run instance
    train_model()
```

### `pubrun.audit_run(**overrides) → Decorator`

A decorator that wraps an entire function in a tracked run. The function's return value is preserved.

```python
from pubrun import audit_run

@audit_run(profile="basic")
def entrypoint():
    train_model()
    return results
```

> [!NOTE]
> Both `tracked_run()` and `audit_run()` accept the same override parameters as `start()`. If no overrides are passed, they fall back to the resolved configuration from `.pubrun.toml` and defaults.

---

## 6. Semantic Diffing

### `pubrun.diff(run_dir_a, run_dir_b, ignores=None) → dict`

Compare two run directories programmatically. Returns a dictionary with `added`, `removed`, `modified`, and `same` keys.

```python
import pubrun

result = pubrun.diff("./runs/pubrun-A", "./runs/pubrun-B",
                     ignores=["timing", "run", "capture"])
for key, detail in result["modified"].items():
    print(f"Changed: {key}")
```

---

## 7. Custom Artifacts and Reports

### `pubrun.report(name: str, data: Any)`
Saves a structured custom report directly to the run directory.
*   **Arguments**:
    *   `name`: The base filename (without extension).
    *   `data`: The payload to write. If `data` is a `dict` or `list`, it is serialized as JSON (`{name}.json`). Otherwise, it is written as plain text (`{name}.txt`).
*   **Return value**: None.
*   **Example**:
    ```python
    import pubrun
    pubrun.report("eval_metrics", {"accuracy": 0.942, "loss": 0.108})
    ```

### `pubrun.artifact(filename: str, content: Any)`
Writes a raw artifact file (such as CSV data, text, or binary bytes) directly to the active run directory.
*   **Arguments**:
    *   `filename`: The output filename (including extension, e.g., `"data.csv"`).
    *   `content`: The file content. If `content` is `bytes`, it is written using binary mode; otherwise, it is cast to `str` and written as UTF-8 text.
*   **Return value**: None.
*   **Example**:
    ```python
    import pubrun
    pubrun.artifact("predictions.csv", "id,pred\n1,0.94\n2,0.12")
    ```

---

## 8. Provenance-Tracked I/O

These APIs are drop-in replacements for standard Python I/O functions that automatically track file and subprocess provenance in the run manifest.

### `pubrun.open(file, mode="r", **kwargs)`

Drop-in replacement for `builtins.open()`. When a run is active, wraps the returned file object to track SHA-256 hashes and access metadata in the manifest's `data_files` section.

```python
import pubrun

with pubrun.open("data/input.csv", "r") as f:
    df = process(f.read())

with pubrun.open("results/output.json", "w") as f:
    f.write(json.dumps(results))
```

### `pubrun.print(*args, **kwargs)`

Drop-in replacement for `builtins.print()`. Calls the real `print()` AND appends the output to `stdout.log` in the run directory (independent of console tee capture_mode).

```python
import pubrun
pubrun.print("Epoch 1 complete", flush=True)
```

### `pubrun.subprocess.run(*args, **kwargs)` / `pubrun.subprocess.Popen(...)`

Explicit subprocess tracking wrappers. Records argv, timing, and exit code without relying on the global subprocess spy (useful in `nopatch` mode).

```python
import pubrun
result = pubrun.subprocess.run(["python", "preprocess.py", "--input", "data.csv"])
```

### `pubrun.popen(cmd, mode="r", bufsize=-1)`

Drop-in replacement for `os.popen()` with provenance tracking.

---

## API Summary

| Function | Purpose | Safe without active run? |
|---|---|---|
| `start(**overrides)` | Begin tracking | N/A (creates run) |
| `stop()` | Finalize active run | Yes (silent no-op) |
| `get_current_run()` | Access active `Run` instance | Yes (returns `None`) |
| `annotate(msg, **kw)` | Inject custom events | Yes (configurable) |
| `phase(name)` | Time a named code region | Yes (silent no-op) |
| `report(name, data)` | Save structured custom report | Yes (configurable) |
| `artifact(filename, content)` | Save raw artifact file | Yes (configurable) |
| `print(*args, **kw)` | Print + log to stdout.log | Yes (falls back to print) |
| `open(file, mode, **kw)` | File I/O with provenance | Yes (falls back to open) |
| `subprocess.run(...)` | Tracked subprocess execution | Yes (falls back to subprocess) |
| `popen(cmd)` | Tracked os.popen replacement | Yes (falls back to popen) |
| `tracked_run(**kw)` | Context manager lifecycle | N/A (creates run) |
| `audit_run(**kw)` | Decorator lifecycle | N/A (creates run) |
| `diff(a, b, ignores)` | Compare two runs | N/A (reads files) |

---

## Threading Model

`pubrun` is designed for single-threaded lifecycle control with safe multi-threaded data capture.

| Function | Thread safety |
|---|---|
| `start()` | **Main thread only.** Creates the run and installs signal handlers (which require the main thread). |
| `stop()` | **Main thread only.** Finalizes engines and writes artifacts. |
| `annotate()` | Safe from any thread. |
| `phase()` | Safe from any thread. |
| `report()` | Safe from any thread. |
| `artifact()` | Safe from any thread. |
| `get_current_run()` | Safe from any thread (read-only). |
| `tracked_run` / `audit_run` | Should wrap main-thread code. |

Signal capture (`SIGINT`, `SIGTERM`, etc.) requires main-thread installation. If `start()` is called from a non-main thread, signal handlers cannot be registered and a warning is emitted. All other capture engines (subprocess spy, console tee, resource watcher, event stream) function normally regardless of which thread calls `start()`.

Internal state mutations (`ref_count`) are protected by a lock to prevent corruption from accidental concurrent `start()`/`stop()` calls.

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [Changelog](../CHANGELOG.md)
