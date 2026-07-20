# Depth-Aware List Diff Formatting

This plan details the design and implementation changes to customize the formatting of simple array/list diffs (like `python.sys_path`) under different depth levels.

## User Review Required

> [!IMPORTANT]
> The proposed formatting behavior is as follows:
> - **`--basic` depth**: Only prints added (`+`) and removed (`-`) elements on their own lines (similar to the current behavior).
> - **`--standard` and `--deep` depths**: Prints the full array as a Python list representation on two lines (one starting with `+` for the new list, one with `-` for the old list) with color-coded and prefix-annotated elements:
>   - Added elements: bold green with a `+` prefix (e.g. `+ 'added_item'`).
>   - Removed elements: bold red with a `-` prefix (e.g. `- 'removed_item'`).
>   - Rearranged elements: bold yellow with a `~` prefix (e.g. `~ 'moved_item'`).
>   - Unchanged elements: default text color without prefixes.

## Proposed Changes

## Diff Rendering Engine

### [MODIFY] [render.py](file://~/VC/pubrun/src/pubrun/analysis/render.py)
- Define a new helper function `_format_array_diff(elements: list, is_new_list: bool, added_set: set, removed_set: set, common_a: list, common_b: list, use_color: bool) -> str` to format lists of simple types with ANSI colors/prefixes for standard/deep levels.
- Update `print_diff` and `_render_inline` to accept a `depth: str = "basic"` parameter.
- Update `_render_inline` to conditionally format `list_diff` type modifications:
  - If `depth == "basic"`, use the current line-by-line format.
  - If `depth in ("standard", "deep")`, construct the formatted array representations for the old and new lists and output them on `-` and `+` lines respectively.

### [MODIFY] [__main__.py](file://~/VC/pubrun/src/pubrun/__main__.py)
- Update `_run_diff` to pass `depth=depth` to `print_diff`.

---

## Tests

### [MODIFY] [test_quality.py](file://~/VC/pubrun/tests/test_quality.py)
- Update/add test cases in `TestDiffEngine` to verify the colored representation of list differences under different depth levels.

## Verification Plan

### Automated Tests
- Run `PYTHONPATH=$(pwd)/src pytest` to execute all tests.

### Manual Verification
- Run `pubrun diff` on two runs with different `sys_path` values under `--basic`, `--standard`, and `--deep` to visually confirm the formatting.
