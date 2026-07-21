[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)

# pubrun for provenance and reproducibility in scientific and ML work

**When a result has to be defensible, "the run finished" is not the same as "the run is trustworthy."** In model development, drug discovery, genomics, and any analysis whose methodology must hold up later, the questions that matter are: exactly which code, inputs, dependencies, and environment produced this checkpoint or figure, and can you reproduce it or explain why two runs differ. pubrun answers those by capturing the full run context automatically, with no code change beyond `import pubrun`, so provenance is not an afterthought you reconstruct from memory months later.

Why this is not optional in high-stakes work:

- **Silent environment drift.** A dependency or driver changes and results shift with no record of what moved. pubrun captures the dependency graph and environment for every run, so a run-to-run `diff` shows exactly what changed.
- **Unversioned inputs.** "Which data file produced this?" is unanswerable after the fact unless it was recorded at run time. pubrun records the invocation, inputs, and code state as the run happens.
- **Confidently-wrong outputs.** A run that completes can still be untrustworthy. pubrun records exit status, logs, and resource usage alongside the inputs, so a result is traceable back to the conditions that produced it.

`pubrun` is used in active Python-based computational research workflows. This page records current research use without claiming citation-based impact; published examples and citations are added here as they become available.

For how pubrun sits alongside experiment-tracking and data-versioning tools (MLflow, Weights and Biases, DVC), see [Where pubrun fits](hpc.md#where-pubrun-fits-alongside-mlflow-weights-and-biases-and-dvc).

## Current use

Current uses include active Python-based computational research workflows where researchers need durable records of:

- The command or script that was executed
- The Python runtime and package state
- The operating environment
- The source-code state
- Logs and exit status
- User-recorded analysis events
- Methods-supporting text derived from the actual run context

## Public example workflow

A public example workflow lives under [`examples/minimal-research-workflow/`](../examples/minimal-research-workflow/).
It uses synthetic, non-sensitive data (no unpublished data or private project files) and
demonstrates the full round trip:

1. Installing `pubrun`
2. Running a Python analysis with `import pubrun`
3. Inspecting the generated run directory
4. Viewing a manifest excerpt
5. Generating methods text
6. Comparing two runs
7. Extracting a rerun command

It is exercised by `tests/test_example_minimal_research_workflow.py`, so it stays runnable as
the code evolves. The `examples/` directory also holds focused single-feature scripts
(`00_auto_start.py` through `11_cli_report.py`) plus a `verify_all.py` harness.

## How to cite pubrun

If you use `pubrun` in research, please cite it. The quickest ways to get a ready-to-use
citation are the `pubrun cite` command (`pubrun cite --style apa|mla|chicago|bibtex`),
GitHub's "Cite this repository" button (backed by `CITATION.cff`), or the archived DOI on
Zenodo. A suggested citation:

> Fariello, G. (2026). pubrun: Low-friction execution provenance for Python research [Computer software]. https://github.com/fariello/pubrun. https://doi.org/10.5281/zenodo.PENDING

<!-- DOI is a PLACEHOLDER until Zenodo mints the real concept DOI; see
.agents/plans/pending/20260706-citation-doi-and-enforceable-attribution.md (Phase 2). -->

**What is required vs. requested.** Under the Apache License 2.0 (§4(d)), any
*redistribution or derivative work* of the `pubrun` **software** must retain the `NOTICE`
file and display its attribution. This is a license condition, not optional. **Citation
in a publication is requested, not legally required**: a software license governs copying
the software, not citing it in a paper. Citing the DOI is the practical, community-standard
way to give that credit.

## Citation status

No peer-reviewed publication currently cites `pubrun` directly. This statement should be updated as soon as public workflows, preprints, papers, or archived research artifacts cite the software.

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
