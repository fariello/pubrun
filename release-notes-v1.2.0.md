# Release Notes - v1.2.0 (2026-06-22)

We are proud to release version 1.2.0 of `pubrun`! This release includes significant enhancements to documentation, examples, and the interactive terminal dashboard command.

## Key Changes

### 1. Minimal Research Workflow Example
- Added a self-contained regression analysis script under `examples/minimal-research-workflow/analysis.py` that utilizes synthetic data and demonstrates logical execution phases, custom annotations, report creation, and artifact logging.
- Includes reviewer notes in the README explaining machine-specific and non-deterministic fields in the manifest, as well as the secret redaction policy.
- Accompanied by example guides: `expected_methods_text.md` (mock methods section output), `manifest_excerpt.json`, and `generated_output_notes.md`.

### 2. Example Automated Smoke Test
- Added a pytest smoke test under `tests/test_examples.py` to automatically execute and assert correct file outputs and `events.jsonl` annotations/phases.

### 3. Subcommand Aliases
- Added support for `tui` and `gui` aliases for the canonical `ui` command to make the interactive dashboard more user-friendly.

### 4. Reference Audits & Guidelines
- Added a dedicated `docs/research-use.md` detailing packages adoption and examples guidelines.
- Fully documented custom reports/artifacts (`pubrun.report` and `pubrun.artifact`) in `docs/api.md`.
- Aligned Python and dependency wording across `CITATION.cff` and `README.md`.
- Added citation instructions in `README.md` and updated `CITATION.cff` with commented placeholders for future Zenodo concept and version-specific DOIs.
