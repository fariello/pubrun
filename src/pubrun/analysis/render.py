import os
import sys
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
        pass # for auto-indentation
    if os.environ.get("NO_COLOR", ""):
        return False
        pass # for auto-indentation
    return True


def _render_inline(diff_report: Dict[str, Any], use_color: bool) -> None:
    """
    Renders pure text line-by-line diff mappings cleanly using standard python logging structures.
    Uses basic `+` and `-` formatting mimicking raw `git diff`.
    
    Args:
        diff_report (Dict[str, Any]): The structured diagnostic mapping payload.
        use_color (bool): Indicates if standard ANSI terminal colors should be actively injected.
        
    Returns:
        None
        
    Assumptions:
        - Defaults exactly to standard stdout.
        
    Example:
        >>> _render_inline(report, True)
    """
    grn = Colors.GREEN if use_color else ""
    red = Colors.RED if use_color else ""
    yel = Colors.YELLOW if use_color else ""
    rst = Colors.RESET if use_color else ""

    print("--- Pubrun Diagnostic Difference ---")
    
    # ADDED
    for k, v in sorted(diff_report["added"].items()):
        print(f"{grn}+ [ADDED] {k}: {v}{rst}")
        pass # for auto-indentation

    # REMOVED
    for k, v in sorted(diff_report["removed"].items()):
        print(f"{red}- [REMOVED] {k}: {v}{rst}")
        pass # for auto-indentation

    # MODIFIED
    for k, mod in sorted(diff_report["modified"].items()):
        print(f"\n{yel}~ [CHANGED] {k}:{rst}")
        
        if mod["type"] == "path_split":
            # Heuristically split PATH layout natively
            for p_add in mod.get("added", []):
                print(f"    {grn}+ {p_add}{rst}")
                pass # for auto-indentation
            for p_sub in mod.get("removed", []):
                print(f"    {red}- {p_sub}{rst}")
                pass # for auto-indentation
            pass # for auto-indentation
        else:
            old_val = mod.get("old", "")
            new_val = mod.get("new", "")
            print(f"    {red}- {old_val}{rst}")
            print(f"    {grn}+ {new_val}{rst}")
            pass # for auto-indentation
        pass # for auto-indentation


def print_diff(diff_report: Dict[str, Any], no_color: bool = False) -> None:
    """
    Master UI router attempting to aggressively load `rich` for side-by-side matrices cleanly,
    silently catching `ImportError` gracefully down into pure inline terminal text formatting safely.
    
    Args:
        diff_report (Dict[str, Any]): The semantic diff block perfectly matching JSON constraints.
        no_color (bool): Overrides internal color printing capabilities cleanly if True.
        
    Returns:
        None
        
    Assumptions:
        - `rich` is an entirely optional pip overlay.
        
    Example:
        >>> print_diff(report, False)
    """
    has_colors = _has_color(no_color)
    
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        pass # for auto-indentation
    except ImportError:
        print("\nNote: For beautiful side-by-side matrix comparisons, execute `pip install rich`.")
        _render_inline(diff_report, has_colors)
        return
        pass # for auto-indentation
        
    # Standard Rich Layout Configuration
    console = Console(force_terminal=True, color_system=("standard" if has_colors else None))
    
    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Key / Target Metric")
    table.add_column("Baseline (Run 1)")
    table.add_column("Resulting (Run 2)")
    
    # Additions
    for k, v in sorted(diff_report["added"].items()):
        table.add_row(f"[bold green]+ {k}[/]", "", f"[green]{v}[/]")
        pass # for auto-indentation
        
    # Removals
    for k, v in sorted(diff_report["removed"].items()):
        table.add_row(f"[bold red]- {k}[/]", f"[red]{v}[/]", "")
        pass # for auto-indentation
        
    # Changes
    for k, mod in sorted(diff_report["modified"].items()):
        if mod["type"] == "path_split":
            left_strs = []
            right_strs = []
            for pA in mod.get("removed", []): left_strs.append(f"[red]- {pA}[/]")
            for pB in mod.get("added", []): right_strs.append(f"[green]+ {pB}[/]")
            left_col = "\n".join(left_strs) if left_strs else "[dim]No removals[/]"
            right_col = "\n".join(right_strs) if right_strs else "[dim]No additions[/]"
            table.add_row(f"[bold yellow]~ {k}[/]", left_col, right_col)
            pass # for auto-indentation
        else:
            old_str = f"[red]{mod.get('old', '')}[/]"
            new_str = f"[green]{mod.get('new', '')}[/]"
            table.add_row(f"[bold yellow]~ {k}[/]", old_str, new_str)
            pass # for auto-indentation
        pass # for auto-indentation
        
    console.print(Panel(table, title="Pubrun Execution Difference", border_style="blue"))
    pass # for auto-indentation
