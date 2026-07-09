# IPD: Reconcile the shipped manifest JSON schema with reality + add a conformance gate

- Date: 2026-07-09
- Concern: documentation (accuracy) / testing
- Scope: `schemas/manifest.schema.json`, `docs/manifest.md`, `tests/test_manifest_schema.py`,
  possibly `.github/workflows/ci.yml`
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Origin

Surfaced during a scoped `/assess documentation` run (2026-07-09) after the profile-deprecation
work. Adding `manifest.config.notices` and validating a real manifest against the shipped schema
revealed that **`schemas/manifest.schema.json` is substantially stale**: a default-run manifest
produces **7 conformance errors**, all from manifest sections that were extended over time without
updating the schema. Nothing validated manifests against the schema, so it drifted silently.

The `config.notices` addition itself was fixed in the profile-deprecation IPD (the schema now lists
`notices`), and a regression test plus an `xfail` tripwire were added (`tests/test_manifest_schema.py`).
This IPD covers the **remaining pre-existing drift** and the **CI gate** to stop it recurring.

## Why it matters

The JSON schema is the published, machine-readable **contract/documentation** of the manifest — the
canonical answer to "what fields does a pubrun manifest contain?" A stale schema is a
documentation-accuracy defect (honest-docs principle) and actively misleads any downstream consumer
that validates against it (they would reject valid pubrun manifests).

## Verified drift (default-run manifest, 2026-07-09)

Authoritative list from `jsonschema.Draft202012Validator.iter_errors`:

| # | Path | Problem |
|---|------|---------|
| 1 | `[root]` | `filesystem` section not in schema (`additionalProperties:false`) |
| 2 | `capture` | `file_provenance_available`, `subprocesses_enabled` not in schema |
| 3 | `host` | `os_release` not in schema |
| 4 | `host.hostname` | schema requires object; manifest emits a **string** (schema/impl disagree on shape) |
| 5 | `packages.records[]` | `source` not in schema |
| 6 | `python` | `environment_kind`, `in_venv`, `pyenv`, `sys_path_len` not in schema |
| 7 | `resources` | `io_counters`, `load_average`, `peak_cpu_percent`, `scope`, `system_iowait_pct`, `system_memory`, `tree_*` not in schema |

Note #4 is not merely additive — the schema and implementation **disagree on the type** of
`host.hostname` (object vs. string), so reconciliation must decide which is correct (verify against
`src/pubrun/capture/host.py` and `docs/manifest.md`) rather than blindly widening the schema.

## Proposed changes (ordered, validatable)

| Step | Change | Files | Remediation Risk | Validation |
|------|--------|-------|------------------|------------|
| 1 | For each drifted section (1-3, 5-7), reconcile the schema against the ACTUAL emitted manifest AND `docs/manifest.md`: add the missing properties with correct types/descriptions. Prefer describing what the code emits; only tighten where the field is genuinely internal. | `schemas/manifest.schema.json`, `docs/manifest.md` | Low | each section validates against a real manifest |
| 2 | Resolve `host.hostname` type disagreement (#4): determine the real shape from `capture/host.py`, fix whichever of schema/impl/doc is wrong. If the impl is authoritative (string), fix schema + doc; treat any impl change as a behavior change needing its own note. | `schemas/manifest.schema.json`, `docs/manifest.md` (and impl only if it is the wrong one) | Low-Medium (functionality if impl changes) | round-trips; no manifest-shape regression |
| 3 | Flip `tests/test_manifest_schema.py::test_full_manifest_conforms_to_schema` from `xfail` to a **hard gate** (remove the marker) once all sections conform, incl. a `profile`-notice manifest and a deep-profile manifest. | `tests/test_manifest_schema.py` | Low | test passes (XPASS → PASS) |
| 4 | Ensure `jsonschema` (dev extra, added 2026-07-09) is installed in CI so the conformance test actually runs on the matrix (confirm `pip install -e ".[dev,tui]"` covers it; it does). | `.github/workflows/ci.yml` (verify only) | Low | conformance test executes in CI, not skipped |

## Scope check

- Over-scope: none — every change traces to a verified conformance error.
- Under-scope: the manifest may have OTHER sections not exercised by a default run (e.g. `signals`
  with records, `data_files` populated, ghost/crashed variants). Step 1 should validate against a
  few manifest *variants* (default, profile-notice, console-capture-on, a crashed/ghost manifest)
  to catch drift a single happy-path manifest misses.

## Required tests / validation

- The `xfail` becomes a passing hard gate across manifest variants.
- `pytest tests/ -v` green on the full matrix; the conformance test runs (not skipped) because
  `jsonschema` is in the `dev` extra.
- Guards the whole CLASS of drift going forward (any future manifest field without a schema update
  fails CI).

## Spec / documentation sync

`docs/manifest.md` tables must match the reconciled schema field-for-field (they are the
human-readable twin of the schema). Add a CHANGELOG entry (schema now validated + reconciled).

## Open questions

1. Is `host.hostname` intended to be a string or an object (`{value, representation}` like redacted
   fields)? Resolve against the code before editing (drives step 2).
2. Should the conformance gate validate a fixed set of committed manifest fixtures (deterministic,
   fast, but can themselves go stale) or freshly-generated manifests (always current, but
   environment-sensitive)? Recommend freshly-generated + a couple of committed edge-case fixtures
   (ghost/crashed) that are hard to generate on demand.

## Approval and execution gate

This IPD is a proposal. It MUST be human-approved before execution and is NOT auto-run. On approval:
reconcile per-section, flip the xfail to a gate, verify on the matrix, sync docs + CHANGELOG, then
move this IPD to `.agents/plans/executed/`.
