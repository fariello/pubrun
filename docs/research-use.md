[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)

# Research use of pubrun

`pubrun` is used by the author and by approximately four to six researchers at the University of Rhode Island in active computational research workflows. To date, the package has recorded over 500 direct downloads (excluding mirrors) on PyPI, indicating adoption outside the immediate development group. These uses are presently concentrated in works in progress rather than in published studies that cite `pubrun` directly.


This page records current research use without claiming citation-based impact. Published examples and citations should be added here as they become available.

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
file and display its attribution — this is a license condition, not optional. **Citation
in a publication is requested, not legally required**: a software license governs copying
the software, not citing it in a paper. Citing the DOI is the practical, community-standard
way to give that credit.

## Citation status

No peer-reviewed publication currently cites `pubrun` directly. This statement should be updated as soon as public workflows, preprints, papers, or archived research artifacts cite the software.

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
