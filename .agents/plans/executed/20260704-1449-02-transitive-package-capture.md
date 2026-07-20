# IPD: Transitive Package Dependency Capture

- Date: 20260704
- Concern: feature / reproducibility
- Scope: `capture/packages.py`, `resources/default.toml`, manifest schema
- Status: PENDING (awaiting human approval; not executed)
- Author: OpenCode (its_direct/pt3-claude-opus-4.6-1m-us)

## Goal

Add an `imported-transitive` package capture mode that records not only the
packages directly imported by the user's script, but also their declared
dependencies (the packages those imports depend on). This closes the gap between
"what the script loaded" and "what the script actually needs to reproduce."

Example: if the script imports `pandas`, the current `imported-only` mode
records `pandas==2.2.0`. The new `imported-transitive` mode would also record
`numpy==1.26.4`, `pytz==2024.1`, etc. — the packages pandas declares as deps.

## Project conventions discovered (Step 0)

- Pending-plans location: `.agents/plans/pending/` (YYYYMMDD-slug.md)
- Stack: Python 3.8+, zero runtime deps except tomli on <3.11
- Current default: `[capture.packages].mode = "imported-only"`
- Existing modes: `imported-only`, `full-environment`, `off`

## Design

### New mode: `imported-transitive`

Resolution order for `[capture.packages].mode`:
1. `"off"` — no package capture
2. `"imported-only"` — scan `sys.modules` top-level names, record version (current default)
3. **`"imported-transitive"` (new)** — same as imported-only, plus each imported package's
   declared `Requires-Dist` dependencies (one level deep)
4. `"full-environment"` — every installed distribution (existing, slow)

### How it works

```python
if mode == "imported-transitive":
    # 1. Get imported packages (same as imported-only)
    imported = {name: version for name in sys.modules if is_top_level(name)}

    # 2. For each imported package, read its declared dependencies
    for name in list(imported):
        try:
            dist = importlib.metadata.distribution(name)
            requires = dist.requires  # List[str] or None
            if requires:
                for req_str in requires:
                    # Parse requirement (e.g., "numpy>=1.21" -> "numpy")
                    req_name = packaging_parse(req_str)  # see below
                    try:
                        req_version = importlib.metadata.version(req_name)
                        records.append({"name": req_name, "version": req_version, ...})
                    except PackageNotFoundError:
                        pass  # extra not installed
        except PackageNotFoundError:
            pass
```

### Parsing requirements without `packaging`

`dist.requires` returns strings like `"numpy>=1.21"`, `"pytz ; python_version<'3.9'"`,
`"pytest ; extra == 'dev'"`. We need to extract just the package name.

Options:
1. **Regex**: `re.match(r'^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)', req)` — covers
   PEP 508 names without importing `packaging`. Simple, robust for name extraction.
2. **`importlib.metadata.requires()`** already gives us the raw strings; we just need
   the name portion before any version specifier, semicolon, or bracket.

Recommendation: regex. Zero deps, handles all real-world names, and we only need
the name (not the full version constraint resolution).

### Filtering extras

Requirements with `; extra == "dev"` or similar markers are optional deps. We should:
- **Include by default**: if the dep is installed, record it regardless of the marker.
  The user has it installed, it might affect behavior.
- **Skip if not installed**: `PackageNotFoundError` is the natural filter — if the
  extra isn't installed, we silently skip it.

### Deduplication

Multiple imported packages may share dependencies (e.g., both `pandas` and `scikit-learn`
depend on `numpy`). Deduplicate by package name in the final records list.

## Manifest output

Same schema as current, with an additional `"source"` field:

```json
{
  "packages": {
    "mode": "imported-transitive",
    "records": [
      {"name": "pandas", "version": "2.2.0", "source": "imported"},
      {"name": "numpy", "version": "1.26.4", "source": "transitive", "required_by": ["pandas", "scikit-learn"]},
      {"name": "pytz", "version": "2024.1", "source": "transitive", "required_by": ["pandas"]}
    ],
    "capture_state": {"status": "complete"}
  }
}
```

The `source` field distinguishes directly-imported from transitive. The
`required_by` field traces provenance (which imported package pulled this in).

## Proposed changes (ordered)

| Step | Change | Files | Remediation Risk | Validation |
|------|--------|-------|------------------|------------|
| 1 | Add requirement name parser (regex, no deps) | `capture/packages.py` | Low | Unit test with various PEP 508 requirement strings |
| 2 | Implement `imported-transitive` mode in `get_packages()` | `capture/packages.py` | Low | Test: import pandas, verify numpy appears as transitive |
| 3 | Add `"source"` and `"required_by"` fields to package records | `capture/packages.py` | Low | Backward-compat: existing modes still produce records without these fields |
| 4 | Add mode to default.toml (documented, not the default) | `resources/default.toml` | Low | Config resolution test |
| 5 | Update manifest schema | `schemas/manifest.schema.json` | Low | Schema validation |
| 6 | Update docs | `docs/configuration.md`, `docs/manifest.md` | Low | Human review |

## Deferred / out of scope

| Item | Reason |
|------|--------|
| Deep transitive (multi-level) | Complexity: requires full dependency graph resolution. One level covers 90% of the value. |
| `full-environment` performance fix | Separate concern (PERF-01 already addressed the default). |
| Version constraint resolution | We record what's installed, not what's required. No solver needed. |

## Required tests / validation

1. Regex parser: test against `"numpy>=1.21"`, `"pytz"`, `"foo[extra]>=1.0"`,
   `"bar ; python_version<'3.9'"`, `"baz-qux.thing"`.
2. Transitive mode: mock sys.modules with `pandas`, verify `numpy` appears.
3. Deduplication: two imports share a dep, verify it appears once with both in `required_by`.
4. Graceful fallback: package with no `requires` metadata — verify no crash.
5. Full regression: 583+ tests green.

## Spec / documentation sync

- `docs/configuration.md`: document the new mode and its behavior.
- `docs/manifest.md`: document `source` and `required_by` fields.
- `CHANGELOG.md`: new feature entry.

## Open questions

1. Should `imported-transitive` become the new default (replacing `imported-only`)?
   **Recommendation:** not yet. Let users opt in for one release, then consider
   promoting it once we confirm it's fast enough (~10-50ms overhead for reading
   dist metadata of 20-50 imported packages).
2. Should `required_by` be an array or omitted for directly-imported packages?
   **Recommendation:** omit for `source: "imported"`, present only for
   `source: "transitive"`.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution, and it is NOT auto-executed.
