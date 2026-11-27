"""
Semantic diff widget for comparing two runs.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Checkbox, Label, RichLog, Select
from rich.text import Text

from pubrun.status import RunInfo
from pubrun.report.utils import hydrate_manifest
from pubrun.analysis.diff import compare_manifests
from pubrun.config import resolve_config
from pubrun.tui.widgets.config import _is_select_empty


class DiffView(Vertical):
    """Component to select, execute, and display semantic differences between two runs."""

    def __init__(self, output_dir: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.output_dir = output_dir

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-card", id="diff-controls-card"):
            yield Label("SEMANTIC DIFF SETUP", classes="panel-card-title")
            with Horizontal(id="diff-dropdowns"):
                yield Select([], id="select-diff-a", prompt="Baseline Run A...")
                yield Select([], id="select-diff-b", prompt="Comparison Run B...")
            with Horizontal(id="diff-settings"):
                yield Select(
                    [
                        ("Basic (Script & config summary; hides env/packages/hardware)", "basic"),
                        ("Standard (Default; hides volatile jitter, compares code/env/packages)", "standard"),
                        ("Deep (Full comparison; hides nothing)", "deep"),
                    ],
                    id="select-diff-depth",
                    value="standard",
                    prompt="Select Depth...",
                )
                yield Checkbox("Show Identical Keys", value=False, id="check-show-same")
            with Horizontal(id="diff-actions-row"):
                yield Button("Compare Runs", id="btn-execute-diff", variant="success")
                yield Button("Clear View", id="btn-clear-diff", variant="primary")

        yield Label("DIFFERENCE REPORT:", classes="info-label")
        yield RichLog(id="diff-output-area", max_lines=5000, classes="log-area")

    def populate_dropdowns(self, runs: List[RunInfo]) -> None:
        """Populate Run A/B dropdowns with manifest-bearing runs and pre-select latest two."""
        select_a = self.query_one("#select-diff-a", Select)
        select_b = self.query_one("#select-diff-b", Select)

        # Only include runs that have a manifest.json file to compare.
        comparable = [r for r in runs if (Path(r.run_dir) / "manifest.json").is_file()]
        options = [
            (f"{r.script or 'unknown'} ({(r.run_id or 'unknown')[:8]})", str(r.run_dir))
            for r in comparable
        ]
        option_values = {opt[1] for opt in options}

        prev_a = select_a.value
        prev_b = select_b.value

        select_a.set_options(options)
        select_b.set_options(options)

        valid_a = (not _is_select_empty(prev_a)) and prev_a in option_values
        valid_b = (not _is_select_empty(prev_b)) and prev_b in option_values

        if valid_a:
            select_a.value = prev_a
        if valid_b:
            select_b.value = prev_b

        # When both selections are empty/invalid and at least two comparable runs exist,
        # pre-select the two most recent comparable runs (older baseline A, newer B).
        if not valid_a and not valid_b and len(comparable) >= 2:
            select_a.value = str(comparable[1].run_dir)
            select_b.value = str(comparable[0].run_dir)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-execute-diff":
            self.run_difference()
        elif event.button.id == "btn-clear-diff":
            self.query_one("#diff-output-area", RichLog).clear()

    def run_difference(self) -> None:
        """Hydrate manifests, perform semantic comparison, and output the report."""
        output = self.query_one("#diff-output-area", RichLog)
        output.clear()

        run_dir_a = self.query_one("#select-diff-a", Select).value
        run_dir_b = self.query_one("#select-diff-b", Select).value

        if _is_select_empty(run_dir_a) or _is_select_empty(run_dir_b) or not run_dir_a or not run_dir_b:
            self.app.notify("Please select both Run A and Run B to compare.", severity="error")
            output.write("Error: Select baseline and comparison runs.")
            return

        if run_dir_a == run_dir_b:
            self.app.notify("Selected the same run for both parameters.", severity="warning")
            output.write("Warning: Cannot compare a run against itself.")
            return

        # Prepare paths
        path_a = Path(str(run_dir_a)) / "manifest.json"
        path_b = Path(str(run_dir_b)) / "manifest.json"

        if not path_a.exists():
            output.write(f"Error: Manifest A not found at {path_a}")
            return
        if not path_b.exists():
            output.write(f"Error: Manifest B not found at {path_b}")
            return

        output.write("Computing semantic difference...")

        try:
            # Load manifests
            with open(path_a, "r", encoding="utf-8") as f:
                manifest_a = json.load(f)
            with open(path_b, "r", encoding="utf-8") as f:
                manifest_b = json.load(f)

            # Hydrate manifests (HPC parent merge)
            manifest_a, warn_a = hydrate_manifest(str(path_a), manifest_a)
            manifest_b, warn_b = hydrate_manifest(str(path_b), manifest_b)

            warnings = list(warn_a or []) + list(warn_b or [])

            # Determine ignores list (default matches CLI/API "standard")
            depth_val = self.query_one("#select-diff-depth", Select).value
            depth = "standard" if _is_select_empty(depth_val) or not depth_val else str(depth_val)
            conf = resolve_config().get("diff", {})
            if depth == "basic":
                ignores = conf.get("ignore_basic", [])
            elif depth == "standard":
                ignores = conf.get("ignore_standard", [])
            else:
                ignores = conf.get("ignore_deep", [])

            show_same = self.query_one("#check-show-same", Checkbox).value

            # Compare
            diff_report = compare_manifests(
                manifest_a, manifest_b, ignores, show_same=show_same, depth=depth
            )

            # Format and render
            self.render_diff_report(diff_report, warnings=warnings)

        except Exception as e:
            output.write(f"Error computing diff: {e}")

    def render_diff_report(self, diff_report: Dict[str, Any], warnings: Optional[List[str]] = None) -> None:
        """Render difference report to the RichLog area using Textual colors."""
        output = self.query_one("#diff-output-area", RichLog)
        output.clear()

        for w in warnings or []:
            output.write(Text(f"[Warning] {w}", style="#f9e2af"))

        def _fmt_val(val: Any) -> str:
            return json.dumps(val, indent=2) if isinstance(val, (dict, list)) else str(val)

        output.write(Text("=== PUBRUN SEMANTIC DIFFERENCE ===", style="bold #cba6f7"))
        output.write("")

        # ADDED (Green)
        added = diff_report.get("added", {})
        if added:
            output.write(Text("ADDED KEYS (+):", style="bold #a6e3a1"))
            for k, v in sorted(added.items()):
                t = Text(f"  + {k}: ", style="#a6e3a1")
                t.append(_fmt_val(v), style="#cdd6f4")
                output.write(t)
            output.write("")

        # REMOVED (Red)
        removed = diff_report.get("removed", {})
        if removed:
            output.write(Text("REMOVED KEYS (-):", style="bold #f38ba8"))
            for k, v in sorted(removed.items()):
                t = Text(f"  - {k}: ", style="#f38ba8")
                t.append(_fmt_val(v), style="#cdd6f4")
                output.write(t)
            output.write("")

        # MODIFIED (Yellow)
        modified = diff_report.get("modified", {})
        if modified:
            output.write(Text("MODIFIED KEYS (~):", style="bold #f9e2af"))
            for k, mod in sorted(modified.items()):
                output.write(Text(f"  ~ {k}:", style="#f9e2af"))
                mod_type = mod.get("type")
                if mod_type == "path_split":
                    for p_add in mod.get("added", []):
                        output.write(Text(f"      + {p_add}", style="#a6e3a1"))
                    for p_sub in mod.get("removed", []):
                        output.write(Text(f"      - {p_sub}", style="#f38ba8"))
                    if mod.get("order_changed") or (not mod.get("added") and not mod.get("removed")):
                        output.write(Text("      ~ [ORDER CHANGED]", style="#f9e2af"))
                        if "old" in mod and "new" in mod:
                            output.write(Text(f"      - {_fmt_val(mod.get('old', ''))}", style="#f38ba8"))
                            output.write(Text(f"      + {_fmt_val(mod.get('new', ''))}", style="#a6e3a1"))
                elif mod_type == "list_diff":
                    for item in mod.get("removed", []):
                        output.write(Text(f"      - {_fmt_val(item)}", style="#f38ba8"))
                    for item in mod.get("added", []):
                        output.write(Text(f"      + {_fmt_val(item)}", style="#a6e3a1"))
                    if mod.get("order_changed"):
                        output.write(Text("      ~ [ORDER CHANGED]", style="#f9e2af"))
                else:
                    old_str = _fmt_val(mod.get("old", ""))
                    new_str = _fmt_val(mod.get("new", ""))
                    output.write(Text(f"      - Old: {old_str}", style="#f38ba8"))
                    output.write(Text(f"      + New: {new_str}", style="#a6e3a1"))
                note = mod.get("note")
                if note:
                    output.write(Text(f"      ! Note: {note}", style="#f9e2af"))
            output.write("")

        # SAME (Dim/Unchanged)
        same = diff_report.get("same", {})
        if same:
            output.write(Text("UNCHANGED KEYS (=):", style="bold #a6adc8"))
            for k, v in sorted(same.items()):
                t = Text(f"  = {k}: ", style="#a6adc8")
                t.append(_fmt_val(v), style="#cdd6f4")
                output.write(t)

        # Summarize if nothing changed
        if not added and not removed and not modified:
            output.write("No differences detected between the selected runs.")
