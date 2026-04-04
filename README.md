# pubrun

> **Let your code write its own Methods section while you go to the pub.**

`pubrun` is a stupidly simple, zero-dependency Python library designed to eliminate the boilerplate of documenting methodology, making it dramatically easier to publish, share, and reproduce your models and research. Alternatively, if you're lame, you can think of "publication-ready runner" as an alternative meaning.

## The Problem
Modern scientific workflows rely on implicit state. When it's time to publish a paper or ship a model, researchers are forced to retroactively piece together their methodology (PyTorch versions, OS constraints, Hardware parameters) from memory.

## The Solution
`pubrun` permanently terminates this friction. 

With a single `import pubrun`, the framework quietly traces your script execution, hashes your environment dependencies, detects codebase drift, and natively compiles publication-ready **Computational Methodology** LaTeX/Markdown blocks so your run is instantly citable.

---

## ⚡⚡⚡ The "Stupid Simple" Quick Start⚡⚡⚡

For absolute simplicity:

```python
import pubrun
# Do your actual ML/Compute work here
```

That’s it. There are no frameworks, no heavy integrations, and no syntax hijacking. 
When the script exits, `pubrun` silently generates a highly structured and lightweight footprint in your local `./runs/` directory.

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
A diagnostic timeline visualizer. This detects dynamic code-drift and visualizes exact dependencies and explicitly targeted environment variables without requiring you to manually read hundreds of lines of JSON.
```bash
pubrun report --deep
```

---

##  🚀 Advanced HPC Ecosystems (Global Hydration)

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

## 🛡️ Security Limitations & Community Input Request

**Subprocess Argument Redaction**  
`pubrun` implements "True Destructive Redaction," safely wiping recognizable secrets (like `AWS_SECRET_KEY`) natively from captured Environment variables. However, the `SubprocessSpy` engine natively captures Python subprocess shell commands exactly as they are executed (e.g. `subprocess.run(["curl", "-H", "Authorization: Bearer 123..."])`). These process executions are currently written to the `manifest.json` **in plaintext without redaction**.

We are actively polling the community: **Should `pubrun` aggressively strip subprocess arguments matching `password/bearer/key` heuristics?**  
Aggressive regex redaction risks inevitably damaging harmless strings (e.g., `--output=password_stats.csv`). We would love the open-source community's feedback on exactly how aggressively an execution telemetry framework should override user commands. If you have an opinion, please open an Issue!

## Acknowledgements
`pubrun` was structurally redesigned and re-written from code fragments, scripts, and ideas over almost two decades with the assistance of Google Antigravity for its official v0.1.0 release.

## License
Released under the BSD 3-Clause License. Copyright (c) 2007-2026 Gabriele Fariello. See the LICENSE file for full terms.
