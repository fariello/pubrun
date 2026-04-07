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

---

## 2. Explicit Structural Control
When `PUBRUN_AUTO_START` is disabled natively, manually configure tracking layers deterministically.

```python
import pubrun

# Inject overriding configuration boundaries natively without touching toml
tracer = pubrun.start(profile="deep", output_dir="./custom_storage")

# ... Do Work ...

# Forcefully flush serialization buffers physically closing footprint paths.
pubrun.stop()
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
