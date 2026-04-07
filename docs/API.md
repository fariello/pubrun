# Pubrun Python API

Beyond passive execution capturing natively performed via standard terminal scripts, `pubrun` defines a minimal, structural python instrumentation API enabling intelligent semantic telemetry dynamically across your codebase.

---

## 1. Zero-Friction Invocation
By default, simply evaluating the module natively safely evaluates a default standard track without configuration loops.

```python
import pubrun

# Your code automatically tracks here.
print("Running execution telemetry...")
```

### 1a. Preventing Auto-Start
To safely evaluate the module strictly without instantly writing artifact directories (e.g. across heavy monolithic packages), physically override the OS mapping before evaluating the module:

```python
import os
os.environ["PUBRUN_AUTO_START"] = "false"

import pubrun
# Nothing executes dynamically until pubrun.start() is directly evaluated!
```

**Configuration Path Alternative:** You don't actually need to pollute your python scripts with `os.environ` hacks. A much cleaner approach is generating a `.pubrun.toml` file in your root directory and explicitly disabling the core feature natively (see `pubrun --help` and `pubrun --create-config`):
```toml
[core]
auto_start = false
```

---

## 2. Explicit Structural Control
When `PUBRUN_AUTO_START` is disabled natively, manually configure tracking layers deterministically.

```python
import pubrun

# Inject overriding configuration boundaries natively mapping python variables!
# These API parameters ALWAYS aggressively override `./.pubrun.toml` variables.
tracer = pubrun.start(profile="deep", output_dir="./custom_storage")

# ... Do Work ...

# Forcefully flush serialization buffers physically closing footprint paths.
pubrun.stop()
```

**Configuration Path Alternative:** If you want your script to remain entirely agnostic to *where* logs are stored or *how deep* to profile, simply invoke `pubrun.start()` empty, and let the `.pubrun.toml` gracefully dictate the logic behind the scenes (see `pubrun --help` and `pubrun --create-config`):
```toml
[core]
profile = "deep"
output_dir = "./runs/"
```

---

## 3. Custom Telemetry Injections
Inside actively traced sessions, directly inject customized execution telemetry asynchronously natively injecting custom dictionary properties into your `events.jsonl` pipeline dynamically!

```python
import pubrun

def process_chunk(matrix):
    # Log native array constraints dynamically
    pubrun.annotate("chunk_evaluation", shape=str(matrix.shape), loss=0.54)
```

**Configuration Path Context:** What happens if `process_chunk` is evaluated but `pubrun` is strictly disabled or hasn't started? By default, `pubrun` fails gracefully and ignores the call. You can dictate this exact behavior inside `.pubrun.toml` (see `pubrun --help` and `pubrun --create-config`):
```toml
[events]
# Safely toggle custom telemetry streams cleanly
enabled = true

# Dictate exactly what happens if `annotate` is called out-of-bounds:
# Valid options: "ignore" (safest), "warn", "error" (crashes script)
on_inactive_annotate = "ignore" 
```

---

## 4. Subprocess Temporal Benchmarking
Delimit structural timing footprints mapping explicit boundaries around variable durations elegantly natively wrapped in standard python constructs. 

### Method A: Context Managers (with)
```python
import pubrun

with pubrun.phase("gradient_descent"):
    model.backward()
    optimizer.step()
```
This safely intercepts timing scopes injecting the literal duration metric dynamically without overhead.

### Method B: Function Decorators
Automatically wrap entire functions explicitly natively ensuring exception captures and boundaries are evaluated safely.
```python
import pubrun

@pubrun.audit_run(profile="basic")
def entrypoint_function():
    # Only evaluates basic footprint arrays strictly mapping outcomes inherently!
    execute_logic()
```

**Configuration Path Context:** Similar to `pubrun.start()`, the decorator safely falls back to your `.pubrun.toml` defaults globally if you simply use `@pubrun.audit_run()`. Specifying `profile="basic"` in the code acts as a hardcoded API override mathematically trumping your local or user global TOML constraints! (see `pubrun --help` and `pubrun --create-config`)
