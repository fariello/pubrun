# Implementation Plan - Standardized CLI Error/Warning Prefixes, rerun Reconstruction, Not-Filters & Smarter Diffing

This plan details the design and implementation changes to standardize error/warning prefixes in pubrun CLI, enable command reconstruction on rerun for active runs, add not-filtering capabilities to CLI filters, and enhance the semantic diff engine to natively compare lists, identify order changes, flatten complex list-of-dicts nested elements (like `pubrun_imports.requests`), and support wildcard key ignores.

## Proposed Changes

### 1. Standardized CLI Error/Warning Formatting

#### [MODIFY] [__main__.py](file:///home/gfariello/VC/pubrun/src/pubrun/__main__.py)
- Convert all standard user-facing errors (where `print("Error: ...", file=sys.stderr)` was used) to utilize the `_print_error(...)` function.
- Update `_get_manifest_path` to print errors using `_print_error` (e.g. for "No --run directory provided").
- Ensure all other print statements with "Error: " in `__main__.py` (like in `_run_diff`, `_run_report`, `_run_meta`, `_run_cite`, `_run_methods`, `status` command, etc.) are routed through `_print_error` (or `_print_warn` for warnings/non-critical issues).

#### [MODIFY] [diagnostics.py](file:///home/gfariello/VC/pubrun/src/pubrun/report/diagnostics.py)
- Define a local formatting helper `_print_error` for standard error output, changing "Error:" prints to use the `[ERRO]` prefix.

---

### 2. Not-Filtering (Exclusions) in CLI

#### [MODIFY] [status.py](file:///home/gfariello/VC/pubrun/src/pubrun/status.py)
- Extend `filter_runs()` to support `not_filter_str` and `not_status_filter` parameters.
  - `not_status_filter` splits on comma and excludes runs matching any of those status labels (using `not in`).
  - `not_filter_str` compiles a regex (or performs string matching) and excludes runs where the script, args, or run ID match.
- Extend `clean_runs()` to accept `not_filter_str` and `not_status_filter`, and forward them to `filter_runs()`.

#### [MODIFY] [__main__.py](file:///home/gfariello/VC/pubrun/src/pubrun/__main__.py)
- Update `_add_run_filter_args()` to register:
  - `-F`, `--not-filter` (type `str`, default `None`)
  - `-S`, `--not-status` (type `str`, default `None`)
- Update subcommand dispatch logic in `main()` to extract these arguments and pass them:
  - In `report` subcommand (when auto-detecting).
  - To `_run_methods()`, `_run_rerun()`, `_run_status()`, `_run_clean()`, and `_run_combined()`.
- Update the signatures of `_get_manifest_path()`, `_run_methods()`, `_run_rerun()`, `_run_status()`, `_run_clean()`, and `_run_combined()` to accept and forward these arguments.

---

### 3. Smarter Diff Engine

#### [MODIFY] [diff.py](file:///home/gfariello/VC/pubrun/src/pubrun/analysis/diff.py)
- Update `_normalize_manifest()` to recursively flatten complex structures:
  - If a value `v` is a list:
    - If it is empty, set to `[]`.
    - If all elements are simple types (string, int, float, bool, None), keep it as a Python list: `flat[full_key] = v`.
    - Otherwise (e.g. list of dicts/lists), flatten elements using index-suffixes: `full_key.{index}`.
  - Implement a `_should_ignore(key, ignores)` helper using `fnmatch.fnmatch` to support wildcard patterns in `ignores` (e.g., `pubrun_imports.requests.*.timestamp_utc`).
- Update `compare_manifests()` to:
  - Check if two compared values `val_a` and `val_b` are lists.
  - If they are lists of simple types, compute a `"list_diff"` structure:
    - `added`: Elements present in `val_b` but not `val_a`.
    - `removed`: Elements present in `val_a` but not `val_b`.
    - `order_changed`: Boolean indicating if the intersection elements in both lists are in a different order.

#### [MODIFY] [render.py](file:///home/gfariello/VC/pubrun/src/pubrun/analysis/render.py)
- Update `_render_inline()` to support `list_diff` types:
  - Show removed elements with `-` prefix in red.
  - Show added elements with `+` prefix in green.
  - Show a yellow `~ [ORDER CHANGED]` warning if order changed.

#### [MODIFY] [default.toml](file:///home/gfariello/VC/pubrun/src/pubrun/resources/default.toml)
- Update default `diff.ignore_standard` configuration to exclude volatile metadata:
  - `"pubrun_imports.selected_at_utc"`
  - `"pubrun_imports.requests.*.timestamp_utc"`
  - `"pubrun_imports.requests.*.caller.line_number"`

---

### 4. Tests

#### [MODIFY] [test_cli.py](file:///home/gfariello/VC/pubrun/tests/test_cli.py)
- Add integration/unit tests for `pubrun rerun` on running/crashed runs.
- Add integration tests for not-filtering:
  - Verify `pubrun status -S completed` excludes completed runs.
  - Verify `pubrun status -F train` excludes runs with "train" in script name or ID.

#### [MODIFY] [test_quality.py](file:///home/gfariello/VC/pubrun/tests/test_quality.py)
- Add unit tests under `TestDiffEngine` and `TestDiffNormalization` to assert:
  - Correct wildcard pattern matching in ignores.
  - Correct flattening of complex lists.
  - Correct `list_diff` generation for added/removed elements and order changes.

---

## Verification Plan

### Automated Tests
- Run `PYTHONPATH=$(pwd)/src pytest` to execute all tests.

### Manual Verification
- Execute `pubrun status -S completed` and verify no completed runs are printed.
- Compare two runs with different `sys_path` or imports using `pubrun diff <run1> <run2>` and verify that instead of raw dump strings, the added/removed entries and order changes are clearly highlighted.
