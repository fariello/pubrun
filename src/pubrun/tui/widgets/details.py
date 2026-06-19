"""
Run details widget for presenting telemetry, python packages, and subprocess logs.
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Label, DataTable, TabbedContent, TabPane, Input
from rich.text import Text
from rich.table import Table

from pubrun.status import RunInfo, STATUS_RUNNING, _format_bytes, _format_elapsed, _format_timestamp

class RunDetailsView(Vertical):
    """Component to display all metadata groups for a single selected run."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.run_info: Optional[RunInfo] = None
        self.timer_id: Optional[Any] = None

    def compose(self) -> ComposeResult:
        with TabbedContent(id="details-tabs"):
            with TabPane("General Info", id="pane-general"):
                yield ScrollableContainer(Static("Select a run to view details.", id="lbl-general-info"))
            with TabPane("Python & Packages", id="pane-packages"):
                with Vertical():
                    yield Input(placeholder="Search packages...", id="pkg-search")
                    yield DataTable(id="packages-table")
            with TabPane("Subprocesses", id="pane-subprocesses"):
                yield DataTable(id="subprocesses-table")

    def on_mount(self) -> None:
        # Setup Packages table
        pkg_table = self.query_one("#packages-table", DataTable)
        pkg_table.add_column("Package Name", width=30)
        pkg_table.add_column("Version", width=15)
        pkg_table.add_column("Editable / Location", width=40)
        pkg_table.cursor_type = "row"

        # Setup Subprocesses table
        sub_table = self.query_one("#subprocesses-table", DataTable)
        sub_table.add_column("Command", width=50)
        sub_table.add_column("Start Time", width=20)
        sub_table.add_column("Elapsed", width=12)
        sub_table.add_column("Exit Code", width=10)
        sub_table.cursor_type = "row"

        # Start periodic refresh for active runs
        self.set_interval(1.0, self.refresh_live_metrics)

    def display_run(self, run_info: RunInfo) -> None:
        """Update the display with details from the selected run."""
        self.run_info = run_info
        self.update_general_pane()
        self.update_packages_pane()
        self.update_subprocesses_pane()

    def refresh_live_metrics(self) -> None:
        """Periodic callback to update CPU/Memory for running processes."""
        if self.run_info and self.run_info.status == STATUS_RUNNING:
            try:
                # Reload RunInfo to re-classify and check process resource utilization
                refreshed = RunInfo(self.run_info.run_dir)
                self.run_info = refreshed
                self.update_general_pane()
            except Exception:
                pass

    def update_general_pane(self) -> None:
        """Re-render the core run stats on the General Info tab."""
        if not self.run_info:
            return

        r = self.run_info
        lines = []
        lines.append(f"[bold #cba6f7]=== RUN IDENTITY ===[/bold #cba6f7]")
        lines.append(f"  [bold]Run ID:[/]        {r.run_id or '-'}")
        lines.append(f"  [bold]Script:[/]        {r.script or '-'}")
        lines.append(f"  [bold]Arguments:[/]     {r.args or '-'}")
        lines.append(f"  [bold]Status:[/]        {r.status.upper()}")
        lines.append(f"  [bold]Directory:[/]     {r.run_dir}")
        lines.append("")

        lines.append(f"[bold #cba6f7]=== TIMING & METRICS ===[/bold #cba6f7]")
        lines.append(f"  [bold]Started:[/]       {_format_timestamp(r.started_at_utc)}")
        if r.ended_at_utc:
            lines.append(f"  [bold]Ended:[/]         {_format_timestamp(r.ended_at_utc)}")
        lines.append(f"  [bold]Elapsed:[/]       {_format_elapsed(r.elapsed)}")
        lines.append(f"  [bold]Exit Code:[/]     {r.exit_code if r.exit_code is not None else '-'}")
        lines.append("")

        # Live or Peak resources
        lines.append(f"[bold #cba6f7]=== RESOURCE CONSUMPTION ===[/bold #cba6f7]")
        if r.status == STATUS_RUNNING:
            lines.append(f"  [bold]Process PID:[/]   {r.pid or '-'}")
            lines.append(f"  [bold]Live RSS Memory:[/] {_format_bytes(r.rss_bytes)}")
            cpu_str = f"{r.cpu_percent:.1f}%" if r.cpu_percent is not None else "-"
            lines.append(f"  [bold]Live CPU usage:[/] {cpu_str}")
        elif r.manifest:
            res = r.manifest.get("resources", {})
            peak_rss = res.get("peak_rss_bytes")
            peak_cpu = res.get("peak_cpu_percent")
            lines.append(f"  [bold]Peak RSS Memory:[/] {_format_bytes(peak_rss)}")
            lines.append(f"  [bold]Peak CPU usage:[/] {f'{peak_cpu:.1f}%' if peak_cpu is not None else '-'}")
        else:
            lines.append("  (No resource metadata recorded)")
        lines.append("")

        # Git
        lines.append(f"[bold #cba6f7]=== REPOSITORY PROVENANCE (GIT) ===[/bold #cba6f7]")
        if r.manifest and "git" in r.manifest:
            git = r.manifest["git"]
            lines.append(f"  [bold]Commit Hash:[/]   {git.get('commit') or '-'}")
            lines.append(f"  [bold]Branch:[/]        {git.get('branch') or '-'}")
            lines.append(f"  [bold]Repo Dirty:[/]     {str(git.get('dirty'))}")
            lines.append(f"  [bold]Remote URL:[/]     {git.get('remote_url', {}).get('value') or '-'}")
        elif r.lock_data:
            lines.append(f"  [bold]Commit Hash:[/]   {r.git_commit or '-'}")
            lines.append(f"  [bold]Working Cwd:[/]   {r.cwd or '-'}")
        else:
            lines.append("  (No git information available)")
        lines.append("")

        # System/Host
        lines.append(f"[bold #cba6f7]=== HOST & HARDWARE SPECS ===[/bold #cba6f7]")
        lines.append(f"  [bold]Hostname:[/]      {r.hostname or '-'}")
        if r.manifest:
            host = r.manifest.get("host", {})
            hw = r.manifest.get("hardware", {})
            cpu = hw.get("cpu", {})
            gpus = hw.get("gpus", [])
            lines.append(f"  [bold]OS:[/]            {host.get('os_name')} ({host.get('os_release')})")
            lines.append(f"  [bold]CPU model:[/]     {cpu.get('model')} ({cpu.get('logical_cores')} cores, {cpu.get('architecture')})")
            lines.append(f"  [bold]Total RAM:[/]     {_format_bytes(hw.get('memory_total_bytes'))}")
            if gpus:
                lines.append("  [bold]GPUs Detected:[/]")
                for idx, gpu in enumerate(gpus):
                    lines.append(f"    - [{idx}] {gpu.get('name')} (Driver: {gpu.get('driver_version')})")
        else:
            lines.append("  (No host specs recorded)")

        self.query_one("#lbl-general-info", Static).update("\n".join(lines))

    def update_packages_pane(self, filter_text: str = "") -> None:
        """Repopulate the dependencies table, applying any filter text."""
        table = self.query_one("#packages-table", DataTable)
        table.clear()

        if not self.run_info or not self.run_info.manifest:
            return

        packages_sec = self.run_info.manifest.get("packages", {})
        records = packages_sec.get("records", [])

        filter_text = filter_text.lower()
        row_idx = 0
        for pkg in records:
            name = pkg.get("name", "")
            version = pkg.get("version", "")
            location = pkg.get("location") or ""
            editable = pkg.get("editable")
            editable_str = "Editable" if editable else "Installed"

            if filter_text and filter_text not in name.lower() and filter_text not in version.lower():
                continue

            loc_str = f"{editable_str} ({location})" if location else editable_str
            table.add_row(name, version, loc_str, key=str(row_idx))
            row_idx += 1

    def update_subprocesses_pane(self) -> None:
        """Repopulate the child subprocess execution table."""
        table = self.query_one("#subprocesses-table", DataTable)
        table.clear()

        if not self.run_info or not self.run_info.manifest:
            return

        subprocesses = self.run_info.manifest.get("subprocesses", [])
        row_idx = 0
        for sub in subprocesses:
            argv = sub.get("argv", [])
            cmd = " ".join(argv)
            start_time = _format_timestamp(sub.get("started_at_utc"))
            
            # Elapsed
            start_val = sub.get("started_at_utc")
            end_val = sub.get("ended_at_utc")
            elapsed = _format_elapsed(end_val - start_val) if (start_val and end_val) else "-"
            
            exit_code = str(sub.get("exit_code")) if sub.get("exit_code") is not None else "Running"

            table.add_row(cmd, start_time, elapsed, exit_code, key=str(row_idx))
            row_idx += 1

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "pkg-search":
            self.update_packages_pane(event.value.strip())
