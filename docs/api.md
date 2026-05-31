[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md)

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
> By default, `pubrun` tees `stdout`/`stderr` to log files. If your scripts produce heavy output, set `capture_mode = "off"` in `.pubrun.toml` or pass `pubrun.start(console={"capture_mode": "off"})`. See [Configuration Reference](configuration.md) for all console options.

### Preventing Auto-Start

If you want to import `pubrun` without automatically starting a trace (e.g., in a shared library module), the cleanest approach is a `.pubrun.toml` file:

```toml
[core]
auto_start = false
```

Or set the environment variable before import:

```python
import os
os.environ["PUBRUN_AUTO_START"] = "false"

import pubrun
# Nothing happens until pubrun.start() is called.
```

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

### `pubrun.stop()`

Finalizes the active run: writes the manifest, closes log files, and resets internal state. Safe to call even if no run is active.

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

## API Summary

| Function | Purpose | Safe without active run? |
|---|---|---|
| `start(**overrides)` | Begin tracking | N/A (creates run) |
| `stop()` | Finalize active run | Yes (silent no-op) |
| `get_current_run()` | Access active `Run` instance | Yes (returns `None`) |
| `annotate(msg, **kw)` | Inject custom events | Yes (configurable) |
| `phase(name)` | Time a named code region | Yes (silent no-op) |
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
| `get_current_run()` | Safe from any thread (read-only). |
| `tracked_run` / `audit_run` | Should wrap main-thread code. |

Signal capture (`SIGINT`, `SIGTERM`, etc.) requires main-thread installation. If `start()` is called from a non-main thread, signal handlers cannot be registered and a warning is emitted. All other capture engines (subprocess spy, console tee, resource watcher, event stream) function normally regardless of which thread calls `start()`.

Internal state mutations (`ref_count`) are protected by a lock to prevent corruption from accidental concurrent `start()`/`stop()` calls.

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md)
