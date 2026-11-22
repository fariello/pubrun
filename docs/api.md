[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)

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
import pubrun.auto as pubrun     # Explicit form of the default `import pubrun` (auto-start).
import pubrun.full as pubrun     # Auto-start and FORCE console capture on (capture everything).
import pubrun.noauto as pubrun   # Load API only. Start manually later.
import pubrun.nopatch as pubrun  # Auto-start, skip subprocess/console patches, keep signal hooks.
import pubrun.noconsole as pubrun # Auto-start, skip console patch, keep subprocess/signal hooks.
import pubrun.minimal as pubrun  # API only. No auto-start, all hooks/patches disabled.
```

| Mode | Auto-start | Global hooks/patches | Use case |
|------|-----------|-------------|----------|
| `auto` | Yes | Yes (permitted) | Default. Auto-start on import. Console tee is permitted but off unless `capture_mode` is set (see note above). |
| `full` | Yes | Yes; **console forced on** | One-import "capture everything," including console output. Forces the console tee on regardless of `capture_mode` (the opposite of `noconsole`), still respecting the Jupyter/non-TTY safety guards. |
| `noauto` | No | Yes | Libraries or scripts that start tracking explicitly. |
| `nopatch` | Yes | No patches (signals active) | When monkey-patching conflicts with other tools (debuggers, profilers). |
| `noconsole` | Yes | Subprocesses/signals active | When stdout/stderr console wrapping is undesirable but subprocesses/signals tracking is needed. |
| `minimal` | No | No | Shared library code that may or may not want tracking. |

> **Import mode is absolute.** An in-code `import pubrun.<mode>` overrides env vars and config files for the scope/hooks it dictates; only the launch-time `pubrun run --mode <mode>` overrides the in-code import. So `full` forces console capture even if config sets `capture_mode = "off"`, and `noconsole` forbids it even if config sets `"standard"`.

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

**Partial capture versus narrow ghost mode:**
- If an individual capture engine fails during `start()`, `pubrun` isolates that failure to the affected section (`capture_state.status = "failed"` with a bounded redacted `detail`), appends a `"capture-error"` entry to `errors.records` (up to `MAX_CAPTURE_ERRORS = 50`), sets `capture.capture_state.status = "partial"`, and keeps all other capture active without affecting host execution.
- Ghost mode (`outcome = "ghost"`, `is_active = False`, `writer = None`) activates only when run output itself is unusable at startup (`run_dir` creation or initial startup manifest write fails, such as on read-only storage). If output fails after hooks were installed, `start()` rolls back every hook, thread, open handle, and lock file owned by that run before returning the ghost `Run` instance.
- Calling `start(**overrides)` while a ghost run is active increments `ref_count` and returns the ghost run without running `_merge_and_migrate()`. Calling `start(**overrides)` while a healthy run is active merges overrides and respects the active import mode's `patch_subprocesses` permission before installing `SubprocessSpy` mid-run.

### `pubrun.stop()`

Finalizes the active run: writes the manifest, closes log files, and resets internal state. Safe to call even if no run is active.

`stop()` decrements `ref_count` and finalizes only when `ref_count` reaches zero. Repeated `stop()` calls (and the `atexit` safety net) are idempotent and never rewrite already-finalized artifacts. Every teardown step runs independently so a failure in one cleanup step never skips restoring other hooks, unregistering `atexit`, writing artifacts, or clearing `get_current_run()`. Calling `stop()` on a ghost run preserves `outcome = "ghost"` and clears the active run reference when `ref_count` reaches zero.

The run outcome is determined automatically:
- `"completed"` — Normal exit, no termination signals received.
- `"failed"` — An unhandled exception occurred (set by `tracked_run` / `audit_run`).
- `"interrupted"` — The process received SIGINT, SIGTERM, or SIGHUP during execution (even if user code caught `KeyboardInterrupt`).
- `"ghost"`: The run entered ghost mode because run output was unusable at startup.

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

### `pubrun.paused() → ContextManager`

Suspend pubrun's **recording** for a block — useful when a section prints noisy
output or spawns helper processes you don't want in the record:

```python
import pubrun   # capturing stdout, subprocesses, ...

do_work()                    # captured
with pubrun.paused():
    call_something_noisy()   # runs and prints normally, but NOT recorded
resume_work()                # captured again
```

Semantics:

- **Mute, not unpatch.** Output still goes to your terminal and subprocesses
  still run; only *recording* is suspended — the console tee stops writing to
  `stdout.log`/`stderr.log` and the subprocess spy stops recording spawned
  processes for the duration of the block.
- **Thread-local.** Only the calling thread's recording is suspended; other
  threads keep being captured. (There is one `sys.stdout`, so terminal output
  still appears for all threads — only the recording decision is per-thread.)
- **Nestable and exception-safe.** Nested `paused()` blocks compose; recording
  resumes only when the outermost block exits, and always resumes even if the
  block raises (it is a context manager for exactly this reason — there is no
  bare `pause()`/`resume()`).
- **Does NOT pause:** your explicit `annotate()`/`phase()` markers (they still
  fire) or background resource sampling (RAM/CPU are process-wide and still
  counted — the noisy subprocess still used real memory).

Safe in any import mode and even with no active run (a no-op on uninstalled
engines).

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

Drop-in replacement for `builtins.open()`. When a run is active, records provenance for the
opened file in the manifest's `data_files` section. **pubrun never patches the global
`open()`** — only files you route through `pubrun.open()` are recorded.

The detail recorded is controlled by `[capture.file_io].level` (progressive; each includes
the ones before it):

| Level | Records | Cost |
|---|---|---|
| `none` | nothing (behaves exactly like `builtins.open`) | — |
| `name` | the path as given | trivial |
| `stat` **(default)** | + size, mtime, ctime (via `fstat` on the open fd) and the absolute path | ~free, incl. on NFS |
| `realpath` | + the symlink-resolved canonical path | higher — walks every path component; **noticeably costlier on NFS/Lustre** |
| `hash` | + SHA-256 of the file contents | highest — reads every byte |

```python
import pubrun

with pubrun.open("data/input.csv", "r") as f:   # recorded at the configured level
    df = process(f.read())

with pubrun.open("results/output.json", "w") as f:
    f.write(json.dumps(results))
```

> **Changed in 1.4.0:** the default level is now `stat` (metadata only). Previously
> `pubrun.open()` always computed a SHA-256 hash. To restore content hashing, set
> `[capture.file_io].level = "hash"` (or `capture={"file_io": {"level": "hash"}}` at
> `pubrun.start(...)`). The `data_files` record shape is unchanged; `sha256` is `null`
> unless the level is `hash`. Hashing is also skipped for files larger than
> `[capture.file_io].max_hash_bytes` (0 = no cap).

#### How `pubrun.open()` hashes: streaming versus fallback

At `level = "hash"`, `pubrun.open()` tries to compute the digest from the bytes your code
already reads, so hashing costs no extra I/O:

- **Streaming (single pass).** A binary read (`"rb"`) of a regular file that reads
  sequentially from the start to the end, or a binary write/exclusive create (`"wb"`,
  `"xb"`), is hashed as the bytes pass through. The record has
  `observation_time = "during_stream"` and `hash_stats.extra_read_bytes = 0`.
- **Fallback (re-read at close).** Text mode, a partial read, any `seek()` or
  `truncate()`, access to the underlying `.raw`/`.buffer`, or append and `+` modes make
  the streamed bytes unusable as a whole-file digest. pubrun then re-reads the file from
  disk after close and records `observation_time = "at_close"`, with
  `hash_stats.extra_read_bytes` equal to the bytes it re-read.

Either way the digest describes the on-disk bytes, never a guess from a partial stream.

#### File-change detection and race limits

pubrun compares the open-fd `fstat` identity (device, inode, size, mtime) taken at open
with the one taken just before close. If a file read through `pubrun.open()` changed in
between, the record has `change_detected = true`, `change_details`, and, at `hash`,
`hash_status = "file_changed"` with `evidence_strength = "changed_unverified"` and no
digest. A fallback hash also re-checks identity around the re-read. These checks narrow
but cannot close every race: a writer that restores size and mtime exactly, a change on a
filesystem with coarse timestamps, or a change after pubrun's last observation is not
detectable. Treat `verified_content` as "these were the bytes at observation time".

### `pubrun.register_file(path, role="input", *, label=None, digest=None, digest_algorithm="sha256", level=None, verify_digest=False, defer=False, metadata=None)`

Records provenance for a file that your code, or a library you cannot modify (pandas,
PyArrow, NumPy, a C extension), reads or writes itself. It does **not** wrap or patch any
reader or writer and does not patch `builtins.open`. The record goes into
`data_files.inputs`, `data_files.outputs`, or `data_files.mixed` by `role`.

*   **Arguments**:
    *   `path`: local path (`str` or `os.PathLike`). Remote object-store URIs (for
        example `s3://...`) are recorded as `entry_type = "unsupported_remote_uri"`
        without network access.
    *   `role`: `"input"`, `"output"`, or `"input_output"`.
    *   `label`: optional logical name (for example `"training_data"`).
    *   `digest` / `digest_algorithm`: a digest you already know. Without
        `verify_digest`, it is recorded as **asserted** evidence
        (`hash_status = "asserted"`, `evidence_source = "asserted"`, `sha256 = null`):
        pubrun did not read the bytes.
    *   `verify_digest`: if `True`, pubrun hashes the file and compares.
        A match gives `verified_content` and `caller_digest.verified = true`; a mismatch
        gives `hash_status = "failed"`, `hash_status_detail = "caller_digest_mismatch"`.
    *   `level`: per-call override of `[capture.file_io].level`.
    *   `defer`: for outputs, record a `pending` entry now and inspect the file later
        (on a post-creation registration or at run finalization).
    *   `metadata`: optional JSON-serializable dict stored on the record.
*   **Return value**: the recorded provenance dict, or `None` when no run is active or
    the effective level is `"none"`. Invalid arguments raise `ValueError`/`TypeError`
    even without an active run.

Registering an output that does not exist yet is allowed and records
`registered_before_creation = true` with `hash_status = "pending"`; the entry is completed
automatically when the run finalizes (`observation_time = "at_finalization"`).

### `pubrun.register_input(path, *, label=None, digest=None, ...)` / `pubrun.register_output(path, *, label=None, digest=None, ..., defer=False)`

Convenience wrappers for `register_file(path, role="input")` and
`register_file(path, role="output")` with the same keyword arguments
(`register_input` has no `defer`).

```python
import pubrun
import pandas as pd

pubrun.register_input("data/raw.parquet", label="raw", level="hash")    # verified
pubrun.register_input("data/ref.csv", digest=known_sha256)              # asserted
pubrun.register_output("results/summary.csv", label="summary", level="hash")  # before creation
df = pd.read_parquet("data/raw.parquet")
df.describe().to_csv("results/summary.csv")   # hashed when the run finalizes
```

A runnable, dependency-free version is `examples/12_external_file_provenance.py`.

#### Which file API to use

| You want to | Use |
|---|---|
| Write a file **into the run directory** (it becomes part of the run record) | `pubrun.artifact()` |
| Read or write an external file **through your own code**, with provenance | `pubrun.open()` |
| Record an external file that **a library reads or writes** | `pubrun.register_input()` / `register_output()` / `register_file()` |

### `pubrun.print(*args, **kwargs)`

Drop-in replacement for `builtins.print()`. Calls the real `print()` AND appends the output to `stdout.log` in the run directory, **independently of console-stream wrapping**. It only needs an active run.

This is the recommended way to capture output when the console tee is NOT active — any mode with `capture_mode = "off"` (the default), or the `noconsole`/`nopatch`/`minimal` modes. It records output without monkeypatching `sys.stdout`/`sys.stderr`, and is available via every import mode alias.

```python
import pubrun.noconsole as pubrun   # streams are not wrapped

pubrun.print("Epoch 1 complete", flush=True)  # still recorded to stdout.log
```

### `pubrun.subprocess.run(*args, **kwargs)` / `pubrun.subprocess.Popen(...)`

Explicit subprocess tracking wrappers. Records argv, timing, and exit code without relying on the global subprocess spy (useful in `nopatch` mode).

```python
import pubrun
result = pubrun.subprocess.run(["python", "preprocess.py", "--input", "data.csv"])
```

### `pubrun.popen(cmd, mode="r", bufsize=-1)`

Drop-in replacement for `os.popen()` with provenance tracking.

### Third-Party Hook Ownership Rules

When global hooks are permitted by the active import mode and enabled in configuration, `pubrun` enforces strict ownership rules so third-party wrappers installed before or after `pubrun.start()` are preserved:

| Global Hook | Install Behavior | Teardown / Rollback Behavior |
|---|---|---|
| `sys.stdout` and `sys.stderr` (`ConsoleInterceptor`) | Snapshots live streams at `start()` and wraps them in `TqdmSafeTee`. Rolls back streams and opened log files if setup fails. | Restores each stream only when `sys.stdout` or `sys.stderr` is still `pubrun`'s tee. If a third-party wrapper sits outside `pubrun`, leaves that wrapper intact and detaches `log_file = None` so `pubrun`'s tee becomes a passive passthrough. |
| `faulthandler` (`ConsoleInterceptor`) | Checks `faulthandler.is_enabled()` before touching it; enables `faulthandler` on `stderr.log` only when previously disabled. | Calls `faulthandler.disable()` (before closing `stderr.log`) only when `pubrun` enabled it. A pre-existing user or test-runner `faulthandler` remains enabled. |
| OS signal handlers (`SignalExitCapture`) | Records each installed shim and chains to the prior handler. Rolls back registered shims on unexpected install errors. | Restores each signal only when `signal.getsignal(signum)` is still `pubrun`'s shim. Deactivated shims left under a later third-party handler pass signals through passively without recording or calling `_finalize_active_run()`. |
| `sys.excepthook` (`SignalExitCapture`) | Captures the prior `sys.excepthook` in a local closure and redacts sensitive values in captured exception messages. | Restores `sys.excepthook` only when it is still `pubrun`'s wrapper. If a third-party hook wraps `pubrun`, `pubrun`'s deactivated wrapper forwards passively to the closure-captured prior hook. |
| `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` (`SubprocessSpy`) | Snapshots live targets at `install()`, chains to pre-existing wrappers, tags spawned processes with install-generation state, and rolls back already-patched targets if a later patch fails. | Verifies caller ownership token when set, marks the generation inactive first, and restores each target independently only when it still matches `pubrun`'s installed wrapper. Any wrapper left beneath a later third-party wrapper passes calls through passively without recording. |

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
| `artifact(filename, content)` | Save a file inside the run directory | Yes (configurable) |
| `print(*args, **kw)` | Print + log to stdout.log | Yes (falls back to print) |
| `open(file, mode, **kw)` | File I/O with provenance | Yes (falls back to open) |
| `register_file(path, role, ...)` | Record an external file read or written elsewhere | Yes (returns `None`) |
| `register_input(path, ...)` | `register_file` with `role="input"` | Yes (returns `None`) |
| `register_output(path, ...)` | `register_file` with `role="output"` | Yes (returns `None`) |
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

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
