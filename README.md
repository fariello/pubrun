# pubrun

> **Let your code monitor itself and write its own Methods section while you go to the pub.**

This does so much with so little. `pubrun` is a stupidly simple, zero-dependency Python library designed to eliminate the boilerplate of documenting methodology, tracking versions, recording inputs, and monitoring resources thereby making it dramatically easier to publish, share, and reproduce your models and research. Alternatively, if you're lame, you can think of "publication-ready runner" as the meaning of the name.

## Quick Start

```python
import pubrun
```
or
```bash
pubrun -h
```
For more info.

See [CLI.md](docs/CLI.md) and [API.md](docs/API.md) for more information.

## Features

- **Automatic Execution Tracing**: Captures environment variables, hardware specs, and dependency graphs without manual configuration.
- **Codebase Drift Detection**: Compares current code state against the execution snapshot to highlight unauthorized changes.
- **Publication-Ready Output**: Generates LaTeX/Markdown methodology blocks ready for academic papers.
- **Cross-Platform Reproducibility**: Extracts initialization logic for seamless environment replication on Linux/Windows.
- **Semantic Diffing**: Compares multiple execution footprints to identify subtle but critical differences.
- **HPC Optimized**: Supports global parent-child hydration to minimize overhead on massive clusters.

## The Problem
Modern scientific workflows rely on implicit state. When it's time to publish a paper or ship a model, researchers are forced to retroactively piece together their methodology (PyTorch versions, OS constraints, Hardware parameters) from memory.

## The Solution
`pubrun` permanently terminates this friction. 

With a single `import pubrun`, the framework quietly traces your script execution, hashes your environment dependencies, detects codebase drift, and natively compiles publication-ready **Computational Methodology** LaTeX/Markdown blocks so your run is instantly citable.

---

## ⚡The "Stupid Simple" Quick Start⚡

For absolute simplicity:

```python
import pubrun
# Do your actual work here
```

That’s it. There are no frameworks, no heavy integrations, and no syntax hijacking. 
When the script exits, `pubrun` silently generates a highly structured and lightweight footprint in your local `./runs/` directory.

### Lazy Initialization (Explicit Tracking)
By default, simply importing `pubrun` immediately spins up an invisible tracer safely. If you want to import `pubrun` harmlessly across multiple scripts *without* instantly generating a footprint until you explicitly call `pubrun.start()`, simply inject this environment flag structurally *before* the module is evaluated:

```python
import os
os.environ["PUBRUN_AUTO_START"] = "false" # <--- The explicit "Wait" signal!

import pubrun
# No directory is generated implicitly.

pubrun.start(output_dir="./custom_storage", profile="deep")
```

Now that your script has executed, instantly extract your method paragraph for research publication natively from your terminal:

```bash
pubrun methods --format latex
```

### Proved Output:
> Computational experiments were executed on a machine running Windows_NT equipped with an AMD Ryzen 7 3700X 8-Core Processor and 64 GB of RAM. The execution environment relied on Python 3.14.3 (Cpython). Key dependencies explicitly tracked include torch (v2.0.1) and numpy (v1.24.1). To guarantee computational reproducibility, the exact state of the source code was anchored at Git commit `c5d1ad8b`. Environment and execution provenance were natively tracked using the `pubrun` library [1].

---

## The Core Command Reference

The `pubrun` decoupled CLI consists of four highly-targeted commands built to support solo-developers on laptops as beautifully as massively parallelized Slurm Array HPC workflows.

### 1. `pubrun cite`
Instantly spits out the specific bibliographic citation you need if you use this library to capture your methodology.
```bash
pubrun cite --style bibtex
```

### 2. `pubrun methods`
Your automated paper-writer. It translates the raw JSON diagnostic payloads into beautifully formatted publication methodology paragraphs. It automatically detects your most recent local execution by default.
```bash
pubrun methods [RUN_DIR] --format markdown|latex
```

### 3. `pubrun report`
A diagnostic timeline visualizer. This detects dynamic code-drift and visualizes exact dependencies and explicitly targeted environment variables without requiring you to manually read hundreds of lines of JSON. Pass multiple directory footprints to evaluate them sequentially!
```bash
pubrun report ./runs/pubrun-A ./runs/pubrun-B --deep
```

### 4. `pubrun rerun`
A native cross-platform reproducibility script extractor that safely queries a footprint's initialization mapping and structurally streams the identical terminal initialization logic globally across Linux and Windows effortlessly natively.
```bash
pubrun rerun ./runs/pubrun-A
```

### 5. `pubrun diff`
A semantic analyzer generating native structural side-by-side diagnostic payloads cleanly masking missing footprint properties natively.
```bash
pubrun diff ./runs/pubrun-A ./runs/pubrun-B --same --basic --wrap
```

---

## Advanced HPC Ecosystems (Global Hydration)

If you run thousands of Array jobs concurrently across massive clusters, you do *not* want each child run wasting gigabytes logging identically heavy dependency graphs. `pubrun` supports a highly advanced **Global Parent-Child Dependency Hydration Ecosystem**.

#### Step 1: Snap the Parent Cluster
On the head node, physically snap the global state of the entire environment using:
```bash
pubrun meta --out ./runs/meta.json --deep
```
This bypasses script-execution and natively generates an introspective metadata map of the hardware, environment variables, and deeply nested Python graphs directly into `meta.json`.

#### Step 2: Hydrate Children
Inside your Slurm script or batch runner, simply define the reference variable:
```bash
export PUBRUN_META_REF=meta.json
# python minimal_script.py
```

`pubrun` respects the HPC environment natively. Child scripts will bypass heavy footprint tracking automatically. 

When it comes time to run `pubrun report` or `pubrun methods`, the orchestrator detects the `PUBRUN_META_REF`, dynamically pulls in the massive `meta.json` context you froze in Step 1, and mathematically stitches all hardware and dependency matrices perfectly back together for your paper. It even strictly compares your target python file anchor against the original `meta.json` timestamps and warns you natively if environmental **Drift has been detected**.

---

## Configuration Philosophy

`pubrun` supports configurations intelligently via:
* Local configurations `.pubrun.toml`
* System-wide variables (`PUBRUN_AUTO_START=true`)
* Decorators (`@pubrun.audit_run()`)
* Context managers (`with pubrun.tracked_run()`)

### Create the Default Engine Architecture
Generate a fully commented architecture right inside your active directory without ever leaving the terminal:
```bash
pubrun --create-config
```

## Replay and Prove
Every generated directory captures heavily structured `manifest.json` files alongside configurations natively engineered to support future evaluation via `compare()` and `diff()`.

## Security Limitations & Community Input Request

**Subprocess Argument Redaction**  
Currently, the `SubprocessSpy` engine effectively intercepts `subprocess.run(["curl", "-H", "Authorization: Bearer 123..."])` but blindly documents it in plaintext directly into the `manifest.json`.

We are actively polling the community regarding how restrictively an execution telemetry framework should override user commands via Regex redaction without accidentally destroying clean scientific outputs. Please see `TODO.md` in this repository for full details!

## Acknowledgements
`pubrun` was structurally redesigned and re-written from pre-existing custom libraries, code fragments, scripts, and ideas over almost two decades with the assistance of Google Antigravity for its official v0.1.0 release.

## License
Released under the BSD 3-Clause License. Copyright (c) 2007-2026 Gabriele Fariello. See the LICENSE file for full terms.
