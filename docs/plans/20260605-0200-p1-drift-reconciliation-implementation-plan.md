# P1 Drift Reconciliation Implementation Plan

**Date**: 2026-06-05 02:00 UTC
**Scope**: Fix all drift, inconsistencies, and release concerns identified in the Part 1 reconciliation review.
**Constraint**: No behavioral changes. Documentation and artifact sync only.

---

## Design Decisions (Resolved)

- **P1-Q1**: `nopatch` mode keeps resource monitoring (background thread) enabled. It is not a global hook.
- **P1-Q2**: `noauto` mode installs global hooks when `start()` is called. `noauto` controls timing, not scope. This matches the 2×2 mode matrix.

---

## Changes Required

### 1. P1-A1: Rebuild dist/ (stale 0.2.0 artifacts)

- Delete `dist/` contents
- Rebuild after all other changes are committed
- This is the last step before publish

### 2. P1-A2 + P1-A7: Update CHANGELOG 0.3.0

- Correct test count from 457 to 462
- Add entry for `global_hooks` enforcement fix
- Add entry for the 5 hook suppression tests

### 3. P1-A3: Document `pubrun_imports` in manifest.md

Add a new section to `docs/manifest.md` describing the `pubrun_imports` top-level manifest field with:
- `selected_mode` (string)
- `selected_behavior` (object: auto_start, global_hooks)
- `selected_by` (string)
- `selected_source` (string)
- `selected_at_utc` (float)
- `core_loaded` (bool)
- `conflict_policy` (string|null)
- `conflicts_detected` (int)
- `requests` (array of request objects)

### 4. P1-A4: Update functional_spec.md

- Update command count from "eight" to "nine"
- Add Section 11.13: `pubrun run` wrapper specification
- Add new subsection to Section 3: Import modes (auto, noauto, nopatch, quiet)
- Add `global_hooks` concept to Section 15 (Subprocess Spy) or a new Section 23
- Reference `[imports]` config section in Section 10

### 5. P1-A5: Update architecture.md

- Add `pubrun.core` to System Components (Section 21)
- Mention `_bootstrap.py`, `_config_boot.py`, `_modes.py` as internal modules
- Note the target-aware `__init__.py` routing pattern

### 6. P1-A6: Add `pubrun_imports` to manifest schema

- Add `pubrun_imports` property to the top-level `properties` in `schemas/manifest.schema.json`
- Define it as an object with the fields listed in item 3
- Mark it as optional (not in `required`) since older manifests won't have it

---

## Order of Operations

1. Update CHANGELOG (P1-A2 + P1-A7)
2. Update docs/manifest.md (P1-A3)
3. Update docs/functional_spec.md (P1-A4)
4. Update docs/architecture.md (P1-A5)
5. Update schemas/manifest.schema.json (P1-A6)
6. Run tests to confirm nothing broke
7. Commit and push
8. Verify CI green (P1-REL1 — already confirmed)
9. Rebuild dist/ (P1-A1)

---

## What Must NOT Change

- No behavioral changes to any module
- No test changes
- No config key changes
- No API signature changes
- Public API surface remains identical
- All 462 tests must continue to pass
