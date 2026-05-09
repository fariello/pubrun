import os
import sys
import json
from typing import Any, Dict

# Standard ANSI Fallback
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

def _has_color(no_color_flag: bool) -> bool:
    if no_color_flag:
        return False
    if os.environ.get("NO_COLOR", ""):
        return False
    return True


def _render_inline(diff_report: Dict[str, Any], use_color: bool) -> None:
    """Print a plain-text diff using +/- prefixes (git-style)."""
    grn = Colors.GREEN if use_color else ""
    red = Colors.RED if use_color else ""
    yel = Colors.YELLOW if use_color else ""
    rst = Colors.RESET if use_color else ""

    print("--- Pubrun Diagnostic Difference ---")
    
    # ADDED
    for k, v in sorted(diff_report["added"].items()):
        print(f"{grn}+ [ADDED] {k}: {v}{rst}")

    # REMOVED
    for k, v in sorted(diff_report["removed"].items()):
        print(f"{red}- [REMOVED] {k}: {v}{rst}")

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
            old_val = mod.get("old", "")
            new_val = mod.get("new", "")
            print(f"    {red}- {old_val}{rst}")
            print(f"    {grn}+ {new_val}{rst}")


def print_diff(diff_report: Dict[str, Any], no_color: bool = False, wrap: bool = False, max_length: int = 300) -> None:
    """Render a diff report. Uses ``rich`` tables if available, falls back to inline text.

    Args:
        diff_report: Structured diff from ``compare_manifests()``.
        no_color: Suppress ANSI color output.
        wrap: Wrap long values instead of truncating.
        max_length: Max characters before truncation.
    """
    has_colors = _has_color(no_color)
    
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        from rich import box
    except ImportError:
        print("\nNote: For beautiful side-by-side matrix comparisons, execute `pip install rich`.")
        _render_inline(diff_report, has_colors)
        return
        
    # Standard Rich Layout Configuration
    console = Console(force_terminal=True, color_system=("standard" if has_colors else None))
    
    table = Table(
        title="Pubrun Execution Difference", 
        title_style="bold blue",
        show_header=True, 
        header_style="bold magenta", 
        expand=True,
        box=box.HEAVY,
        row_styles=["none", "on grey15"]
    )
    
    overflow_mode = "fold" if wrap else "ellipsis"
    table.add_column("Key / Target Metric")
    table.add_column("Baseline (Run 1)", overflow=overflow_mode)
    table.add_column("Resulting (Run 2)", overflow=overflow_mode)
    
    def _fmt(val: Any) -> str:
        s = json.dumps(val, indent=2) if isinstance(val, (dict, list)) else str(val)
        if len(s) > max_length:
            return s[:max_length] + " ... [TRUNCATED]"
        return s
    
    # Additions
    for k, v in sorted(diff_report["added"].items()):
        table.add_row(f"[bold green]+ {k}[/]", "", f"[green]{_fmt(v)}[/]")
        
    # Removals
    for k, v in sorted(diff_report["removed"].items()):
        table.add_row(f"[bold red]- {k}[/]", f"[red]{_fmt(v)}[/]", "")
        
    # Changes
    for k, mod in sorted(diff_report["modified"].items()):
        if mod["type"] == "path_split":
            left_strs = []
            right_strs = []
            for pA in mod.get("removed", []): left_strs.append(f"[yellow]- {_fmt(pA)}[/]")
            for pB in mod.get("added", []): right_strs.append(f"[yellow]+ {_fmt(pB)}[/]")
            left_col = "\n".join(left_strs) if left_strs else "[dim]No removals[/]"
            right_col = "\n".join(right_strs) if right_strs else "[dim]No additions[/]"
            table.add_row(f"[bold yellow]~ {k}[/]", left_col, right_col)
        else:
            old_str = f"[yellow]{_fmt(mod.get('old', ''))}[/]"
            new_str = f"[yellow]{_fmt(mod.get('new', ''))}[/]"
            table.add_row(f"[bold yellow]~ {k}[/]", old_str, new_str)
        
    # Same
    for k, v in sorted(diff_report.get("same", {}).items()):
        formatted_val = f"[dim]{_fmt(v)}[/]"
        table.add_row(f"[dim white]= {k}[/]", formatted_val, formatted_val)
        
    console.print(table)
