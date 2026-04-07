# Pubrun Command Line Interface (CLI)

The `pubrun` CLI is a zero-dependency orchestrator that bridges the gap between raw execution footprints and human-readable, publication-ready intelligence. It provides six deeply isolated, cross-platform subsystems natively accessible via `python -m pubrun <command>` or `pubrun <command>`.

---

## 1. `methods` - The Academic Writer
Instantly compile dynamic execution payloads into strict academic methodology prose paragraphs natively suitable for copy-pasting directly into your manuscripts.

**Usage:**
```bash
pubrun methods [RUN_DIR] [--format markdown|latex]
```
If `RUN_DIR` is omitted, the framework automatically searches `./runs/` resolving strictly the most recently completed footprint. 

**Example (LaTeX Generation):**
```bash
pubrun methods ./runs/pubrun-training_loop-1234 --format latex
```

---

## 2. `report` - The Timeline Diagnostics UI
Transform raw JSON payloads into an elegant terminal timeline exposing execution jitter, structural configuration, hardware footprints, and natively capturing codebase drift.

**Usage:**
```bash
pubrun report [RUN_DIR_A] [RUN_DIR_B...] [--basic|--standard|--deep]
```
*   Pass multiple isolated directory paths to generate vertically delimited diagnostic bounds simultaneously!

**Depth Controls:**
*   `--basic`: Isolates simply temporal paths and outcomes.
*   `--standard`: Generates the primary layout incorporating hardware, commits, and Python footprints (Default).
*   `--deep`: Completely dumps every captured dependency structure and environment variable.

---

## 3. `diff` - The Semantic Target Analyzer 
The true powerhouse. Execute an exhaustive side-by-side array evaluation parsing literally what changed mathematically between two footprint traces.

**Usage:**
```bash
pubrun diff [RUN_DIR_A] [RUN_DIR_B] [--basic|--standard|--deep] [--same|--no-same] [--wrap|--no-wrap] [--export]
```
*   `--basic`: Drastically filters runtime noise restricting output strictly to script executions, package changes, and user telemetry modifications.
*   `--same`: Explicitly forces properties that match perfectly identically (e.g. Hostnames) to evaluate into the matrix safely `dimmed`.
*   `--wrap`: Enables `rich` UI folding boundaries maintaining terminal block constraints tightly.
*   `--export`: Disable the UI terminal router entirely, spitting flat structured semantic text cleanly designed for IDE GUI comparisons (like `meld`).

---

## 4. `rerun` - The Reproducibility Script
Isolates a generated trace natively fetching the explicit cross-platform CLI string initialization array. 

**Usage:**
```bash
pubrun rerun [RUN_DIR]
```

It guarantees safe structural pipeline commands safely returning: 
```powershell
cd 'C:\directory' 
python 'run.py'
```

---

## 5. `meta` - Global Configuration Hydration
(HPC Advanced Context). Evaluates the execution hardware and software boundaries independent of any running script natively printing a generalized `meta.json`. 

**Usage:**
```bash
pubrun meta [--out PATH] [--basic|--standard|--deep]
```

Use this exclusively to generate a "Parent footprint" inside massive Array compute clusters to prevent redundant memory utilization across identical children environments intelligently.

---

## 6. `cite` - Automatic Academic Citations
When finalizing your manuscript, intelligently export the exact framework credit citation cleanly.

**Usage:**
```bash
pubrun cite [--style apa|mla|chicago|bibtex]
```
