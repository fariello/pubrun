# IPD: Reconcile the shipped manifest JSON schema with reality + add a conformance gate

- Date: 2026-07-09
- Concern: documentation (accuracy) / testing
- Scope: `schemas/manifest.schema.json`, `docs/manifest.md`, `tests/test_manifest_schema.py`,
  possibly `.github/workflows/ci.yml`
- Status: EXECUTED 2026-07-09 (approved). Schema reconciled; conformance gate live (8 tests, 0
  xfail); full suite green. See "Execution notes" below.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Execution notes (2026-07-09)

- **`host.hostname` question resolved (Open Q1): the implementation is authoritative — it emits a
  plain string** (`capture/host.py:23` `platform.node() or socket.gethostname()`). The schema was
  wrong (typed it as a `redacted_value` object). Fixed the schema (no impl change). The whole `host`
  def was rewritten to the real shape (`os_name`/`os_version`/`os_release`/`hostname`/`capture_state`);
  the schema had also listed never-emitted fields (`fqdn`/`kernel_version`/`platform`/`architecture`).
- **Reconciled `$defs`** against the actual emitted shapes: `host` (rewrite), `capture`
  (`subprocesses_enabled`, `file_provenance_available`), `python_runtime` (`environment_kind`,
  `in_venv`, `sys_path_len`, `pyenv`), `package_record` (`source`), `resources_section` (`scope`,
  `peak_cpu_percent`, `system_memory`, `load_average`, `system_iowait_pct`, `io_counters`, `tree_*`),
  and added the missing root **`filesystem`** section (`filesystem_section` def).
- **Docs were already the accurate twin** — only `packages.records[].source` needed adding to
  `docs/manifest.md`; `host`/`python`/`resources`/`capture`/`filesystem` docs already matched reality.
  The drift was schema-only.
- **Validated 0 errors across variants**: default, profile-notice, console-capture-on, tree-scope,
  and a git-repo-populated run. `test_manifest_schema.py`: the full-manifest test is now a **hard
  gate** (xfail removed) plus a 4-variant parametrized conformance test (8 tests total).
- **Open Q2 resolved:** the gate validates **freshly-generated** manifests (always current), not
  committed fixtures.

### CI follow-up (Windows) — console section

First push (`0b44c38`) was green locally but **failed on windows-latest/3.12**: the `console`
section can be an empty `{}` (console capture is optional; the interceptor never populated it in
that headless path), but the schema *required* `capture_mode`. Fixed by relaxing
`console_section.required` to `[]` — an empty console section is a legitimate emitted shape. This is
exactly the cross-platform gap the CI matrix exists to catch (local Linux validation always had a
populated console).

### Follow-up noted (out of scope here): ghost-manifest section shapes

Ghost mode (filesystem write failure at init) emits `{}` for **every** section
(`tracker.py:128-134`), so a ghost manifest currently produces ~16 `required: [capture_state]`
violations against the schema. The reconciliation + gate here target the NORMAL manifest; ghost
manifests were never schema-validated. Options for a follow-up: either make ghost sections carry a
`capture_state` (consistent with the "every section has capture_state" intent) or relax the section
defs to accept the empty-object case. Tracked, not fixed here (separate scope + its own test).

### Follow-up noted (out of scope here): stale test fixture

`tests/fixtures/sample_manifest.json` is stale vs. current reality (has `git.is_dirty` and
`invocation.working_directory.basename`, neither of which the code emits — the live git manifest uses
`dirty`). It is NOT used by the new conformance test (which generates fresh manifests), so it does not
affect the gate, but it should be refreshed or removed as a separate test-hygiene task. (Low priority;
recorded here rather than expanding this IPD further.)

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
