# evidence (file:line, read-only)

## Current README front door (Layer 0) - treated as DONE

- README.md:5 tagline (universal, no ML gate): "Reproducible runs ... know exactly what any run did, and compare any two of them ... from a single import pubrun."
- README.md:7 lead paragraph; first concrete examples are ordinary: "a one-off script, a nightly job, a data pipeline, or a step in a larger ML or scientific workflow."
- README.md:9 explicit component-not-platform: "It is not an orchestrator, scheduler, or serving platform ... the provenance layer you use inside your pipeline."
- README.md:11 explicit breadth/inclusivity: "grew up in scientific and ML workflows, but ... useful for any run ... from a 20-line script to a thousand-node cluster."

## Bridge / breadth / examples gaps (F1, F2)

- README.md:1 top nav (research-use.md and hpc.md reachable only here, generically).
- README.md:49 the single contextual deep link: "(See [HPC](docs/hpc.md) for PUBRUN_META_REF and the mechanics.)"
- README body has no "examples/" reference; examples/ on disk is feature-indexed: 00_auto_start.py, 01_minimal_start_stop.py, ... 11_cli_report.py, verify_all.py, and examples/minimal-research-workflow/.
- Only doc-referenced example: docs/research-use.md:22-38 (minimal-research-workflow, tested by tests/test_example_minimal_research_workflow.py).

## Deep pages (F3)

- docs/research-use.md:5 leads with adopter count "approximately four to six researchers at the University of Rhode Island."
- docs/hpc.md:5 gotchas-first: "pubrun runs unmodified on HPC clusters (Slurm, etc.)."

## Positioning / competitors (F4)

- Zero MLflow / Weights and Biases / W&B / DVC mentions in README.md or docs/.
- Generic complement framing only: README.md:9 "alongside whatever runs it."
- Strong disclaimers (correct): architecture.md:228-233 and functional_spec.md:29-34 Non-Goals (no workflow engine/DAG scheduler; no experiment-tracking platform; no data-versioning tool).

## House rule (F5)

- AGENTS.md:25: "write no em or en dashes in authored Markdown."
- Em-dash lines: functional_spec.md 47, cli.md 44, README.md 38, architecture.md 33, configuration.md 19, manifest.md 17, api.md 15, hpc.md 7, performance.md 4, research-use.md 1, plus design notes; total ~290 dash-bearing lines. En-dash version ranges e.g. README.md:13,23 ("3.8-3.10").

## Positive / honesty (F6)

- Hype vocabulary (revolutionary/cutting-edge/next-generation/seamless/enterprise/world-class/blazing): zero hits.
- All documented CLI subcommands registered and dispatched: src/pubrun/__main__.py:2152-2486 (subparsers), 2576-2799 (dispatch).
- Tracked-I/O APIs backed: capture/filesystem.py, capture/console.py, capture/subprocesses.py; redaction capture/redaction.py; meta-ref report/meta_snapshot.py.
- Roadmap future-tagged: README.md:454-457 (register_artifact/register_metadata as Future). DOI PENDING: research-use.md:47, README.md:469.

## Method note

Inventory gathered via a read-only explore pass over docs/, README.md, src/pubrun/, AGENTS.md, and .agents/workflows/assess/. No files modified during assessment.
