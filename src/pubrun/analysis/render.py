"""
Diff report rendering -- plain-text ANSI output (git-style).
"""
import json
import os
from typing import Any, Dict


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    DIM = '\033[2m'
    RESET = '\033[0m'


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


def _render_inline(diff_report: Dict[str, Any], use_color: bool, max_length: int = 300, wrap: bool = False) -> None:
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
        else:
            old_val = _fmt(mod.get("old", ""), max_length, wrap)
            new_val = _fmt(mod.get("new", ""), max_length, wrap)
            print(f"    {red}- {old_val}{rst}")
            print(f"    {grn}+ {new_val}{rst}")

    # SAME (if present)
    same = diff_report.get("same", {})
    if same:
        print(f"\n{dim}--- Unchanged ---{rst}")
        for k, v in sorted(same.items()):
            print(f"{dim}= {k}: {_fmt(v, max_length, wrap)}{rst}")


def print_diff(diff_report: Dict[str, Any], no_color: bool = False, wrap: bool = False, max_length: int = 300) -> None:
    """Render a diff report to stdout using ANSI-colored text.

    Args:
        diff_report: Structured diff from ``compare_manifests()``.
        no_color: Suppress ANSI color output.
        wrap: Allow long values to wrap naturally instead of truncating.
        max_length: Max characters before truncation (ignored when wrap=True).
    """
    has_colors = _has_color(no_color)
    _render_inline(diff_report, has_colors, max_length=max_length, wrap=wrap)
