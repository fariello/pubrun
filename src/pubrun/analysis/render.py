"""
Diff report rendering -- plain-text ANSI output (git-style).
"""
import json
import os
from typing import Any, Dict, Iterable


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    DIM = '\033[2m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def _tag(x: Any) -> Any:
    """Type-tagged comparison key so ``True``/``1`` and ``False``/``0`` stay distinct."""
    return (type(x).__name__, x)


def _format_array_diff(
    elements: list,
    is_new_list: bool,
    added_set: Iterable[Any],
    removed_set: Iterable[Any],
    common_a: list,
    common_b: list,
    use_color: bool
) -> str:
    """Format an array/list of simple types with color coding for additions, removals, and rearrangements."""
    grn = Colors.BOLD + Colors.GREEN if use_color else ""
    red = Colors.BOLD + Colors.RED if use_color else ""
    yel = Colors.BOLD + Colors.YELLOW if use_color else ""
    rst = Colors.RESET if use_color else ""

    # Compare by a type-tagged key so bool/int do not alias (True == 1, False == 0).
    added_tags = {_tag(x) for x in added_set}
    removed_tags = {_tag(x) for x in removed_set}
    tags_a = [_tag(x) for x in common_a]
    tags_b = [_tag(x) for x in common_b]

    def _moved(t: Any) -> bool:
        return t in tags_a and t in tags_b and tags_a.index(t) != tags_b.index(t)

    parts = []
    for x in elements:
        x_repr = repr(x)
        t = _tag(x)
        if is_new_list:
            if t in added_tags:
                parts.append(f"{grn}+{x_repr}{rst}")
            elif _moved(t):
                parts.append(f"{yel}~{x_repr}{rst}")
            else:
                parts.append(x_repr)
        else:
            if t in removed_tags:
                parts.append(f"{red}-{x_repr}{rst}")
            elif _moved(t):
                parts.append(f"{yel}~{x_repr}{rst}")
            else:
                parts.append(x_repr)

    return "[" + ", ".join(parts) + "]"


def _has_color(no_color_flag: bool) -> bool:
    """Determine if color output should be used."""
    if no_color_flag:
        return False
    if os.environ.get("NO_COLOR", ""):
        return False
    return True


def _fmt(val: Any, max_length: int, wrap: bool) -> str:
    """Format a value for display, handling truncation or wrapping."""
    s = json.dumps(val, indent=2) if isinstance(val, (dict, list)) else str(val)
    if len(s) > max_length:
        if wrap:
            return s  # Let the terminal wrap naturally
        return s[:max_length] + " ... [TRUNCATED]"
    return s


def _render_inline(diff_report: Dict[str, Any], use_color: bool, max_length: int = 300, wrap: bool = False, depth: str = "basic") -> None:
    """Print a plain-text diff using +/- prefixes (git-style)."""
    grn = Colors.GREEN if use_color else ""
    red = Colors.RED if use_color else ""
    yel = Colors.YELLOW if use_color else ""
    dim = Colors.DIM if use_color else ""
    rst = Colors.RESET if use_color else ""

    print("--- Pubrun Diagnostic Difference ---")

    # ADDED
    for k, v in sorted(diff_report["added"].items()):
        print(f"{grn}+ [ADDED] {k}: {_fmt(v, max_length, wrap)}{rst}")

    # REMOVED
    for k, v in sorted(diff_report["removed"].items()):
        print(f"{red}- [REMOVED] {k}: {_fmt(v, max_length, wrap)}{rst}")

    # MODIFIED
    for k, mod in sorted(diff_report["modified"].items()):
        print(f"\n{yel}~ [CHANGED] {k}:{rst}")

        if mod["type"] == "path_split":
            # PATH-style: show added/removed path segments
            for p_add in mod.get("added", []):
                print(f"    {grn}+ {p_add}{rst}")
            for p_sub in mod.get("removed", []):
                print(f"    {red}- {p_sub}{rst}")
            if mod.get("order_changed") or (not mod.get("added") and not mod.get("removed")):
                print(f"    {yel}~ [ORDER CHANGED]{rst}")
                if "old" in mod and "new" in mod:
                    print(f"    {red}- {_fmt(mod.get('old', ''), max_length, wrap)}{rst}")
                    print(f"    {grn}+ {_fmt(mod.get('new', ''), max_length, wrap)}{rst}")
        elif mod["type"] == "list_diff":
            if depth in ("standard", "deep"):
                added_set = list(mod.get("added", []))
                removed_set = list(mod.get("removed", []))
                val_a = mod.get("old", [])
                val_b = mod.get("new", [])

                tags_a = {_tag(x) for x in val_a}
                tags_b = {_tag(x) for x in val_b}
                common_a = [x for x in val_a if _tag(x) in tags_b]
                common_b = [x for x in val_b if _tag(x) in tags_a]

                old_repr = _format_array_diff(val_a, False, added_set, removed_set, common_a, common_b, use_color)
                new_repr = _format_array_diff(val_b, True, added_set, removed_set, common_a, common_b, use_color)

                print(f"    {grn}+{rst} {_fmt(new_repr, max_length, wrap)}")
                print(f"    {red}-{rst} {_fmt(old_repr, max_length, wrap)}")
            else:
                # List-style: show added/removed elements, order change warning
                for p_sub in mod.get("removed", []):
                    print(f"    {red}- {p_sub}{rst}")
                for p_add in mod.get("added", []):
                    print(f"    {grn}+ {p_add}{rst}")
                if mod.get("order_changed", False):
                    print(f"    {yel}~ [ORDER CHANGED]{rst}")
        else:
            old_val = _fmt(mod.get("old", ""), max_length, wrap)
            new_val = _fmt(mod.get("new", ""), max_length, wrap)
            print(f"    {red}- {old_val}{rst}")
            print(f"    {grn}+ {new_val}{rst}")

        note = mod.get("note")
        if note:
            print(f"    {yel}note: {note}{rst}")

    # SAME (if present)
    same = diff_report.get("same", {})
    if same:
        print(f"\n{dim}--- Unchanged ---{rst}")
        for k, v in sorted(same.items()):
            print(f"{dim}= {k}: {_fmt(v, max_length, wrap)}{rst}")


def _summarize_change(mod: Dict[str, Any], max_length: int) -> str:
    """One-cell 'A -> B' summary of a modified entry for the table view."""
    t = mod.get("type")
    note = mod.get("note")
    note_suffix = f" [{note}]" if note else ""
    if t == "path_split":
        added = mod.get("added", [])
        removed = mod.get("removed", [])
        bits = []
        if added:
            bits.append(f"+{len(added)}")
        if removed:
            bits.append(f"-{len(removed)}")
        if mod.get("order_changed"):
            bits.append("reordered")
        cell = (f"PATH {' '.join(bits)}" if bits else "PATH changed") + note_suffix
        if len(cell) > max_length:
            cell = cell[:max_length] + " ..."
        return cell
    if t == "list_diff":
        added = mod.get("added", [])
        removed = mod.get("removed", [])
        parts = []
        if added:
            parts.append(f"+{len(added)}")
        if removed:
            parts.append(f"-{len(removed)}")
        if mod.get("order_changed"):
            parts.append("reordered")
        cell = (f"list [{', '.join(parts)}]" if parts else "list changed") + note_suffix
        if len(cell) > max_length:
            cell = cell[:max_length] + " ..."
        return cell
    old = str(mod.get("old", ""))
    new = str(mod.get("new", ""))
    cell = f"{old}  ->  {new}{note_suffix}"
    if len(cell) > max_length:
        cell = cell[:max_length] + " ..."
    return cell


def _render_table(diff_report: Dict[str, Any], use_color: bool, max_length: int = 300) -> None:
    """Aligned two-column table view: 'change | field | A -> B'. Opt-in (--table)."""
    grn = Colors.GREEN if use_color else ""
    red = Colors.RED if use_color else ""
    yel = Colors.YELLOW if use_color else ""
    bold = Colors.BOLD if use_color else ""
    rst = Colors.RESET if use_color else ""

    dim = Colors.DIM if use_color else ""

    def _cell(v: Any) -> str:
        s = str(v)
        if len(s) > max_length:
            s = s[:max_length] + " ..."
        return s

    rows = []  # (mark, color, key, detail)
    for k, v in sorted(diff_report.get("added", {}).items()):
        rows.append(("+", grn, k, _cell(v)))
    for k, v in sorted(diff_report.get("removed", {}).items()):
        rows.append(("-", red, k, _cell(v)))
    for k, mod in sorted(diff_report.get("modified", {}).items()):
        rows.append(("~", yel, k, _summarize_change(mod, max_length)))
    has_differences = bool(rows)
    for k, v in sorted(diff_report.get("same", {}).items()):
        rows.append(("=", dim, k, _cell(v)))

    print("--- Pubrun Diagnostic Difference ---")
    if not has_differences:
        print("(no differences)")
    if not rows:
        return

    # Column widths (based on the uncolored text), capped so a huge key can't blow out.
    key_w = min(48, max(len("Field"), max(len(k) for _, _, k, _ in rows)))
    print(f"{bold}{'':1}  {'Field'.ljust(key_w)}  Change{rst}")
    print(f"{'-' * (key_w + 12)}")
    for mark, color, k, detail in rows:
        key_disp = k if len(k) <= key_w else k[: key_w - 1] + "\u2026"
        detail = detail.replace("\n", " ")
        print(f"{color}{mark}{rst}  {key_disp.ljust(key_w)}  {color}{detail}{rst}")


def print_diff(diff_report: Dict[str, Any], no_color: bool = False, wrap: bool = False, max_length: int = 300, depth: str = "basic", table: bool = False) -> None:
    """Render a diff report to stdout using ANSI-colored text.

    Args:
        diff_report: Structured diff from ``compare_manifests()``.
        no_color: Suppress ANSI color output.
        wrap: Allow long values to wrap naturally instead of truncating.
        max_length: Max characters before truncation (ignored when wrap=True).
        depth: The diff depth level ("basic", "standard", or "deep").
        table: If True, render the compact aligned table view instead of the
            default git-style ``+/-/~`` inline output.
    """
    has_colors = _has_color(no_color)
    if table:
        _render_table(diff_report, has_colors, max_length=max_length)
    else:
        _render_inline(diff_report, has_colors, max_length=max_length, wrap=wrap, depth=depth)
