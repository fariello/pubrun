"""
Run details widget for presenting telemetry, python packages, and subprocess logs.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from textual.app import ComposeResult
    from textual.containers import ScrollableContainer, Vertical
    from textual.widgets import DataTable, Input, Static, TabbedContent, TabPane
    from rich.markup import escape as rich_escape
except ImportError:
    ComposeResult = Any  # type: ignore[assignment,misc]
    Vertical = object  # type: ignore[assignment,misc]
    ScrollableContainer = object  # type: ignore[assignment,misc]
    Static = object  # type: ignore[assignment,misc]
    DataTable = object  # type: ignore[assignment,misc]
    TabbedContent = object  # type: ignore[assignment,misc]
    TabPane = object  # type: ignore[assignment,misc]
    Input = object  # type: ignore[assignment,misc]

    def rich_escape(markup: str) -> str:  # type: ignore[misc]
        return markup

from pubrun.status import (
    RunInfo,
    STATUS_RUNNING,
    _as_float,
    _format_bytes,
    _format_duration_detail,
    _format_timestamp,
    classify_timing_semantics,
)


def _escape_markup(text: str) -> str:
    """Escape bracketed tokens safely for both Rich and Textual markup parsers."""
    escaped = rich_escape(text)
    return re.sub(r"(?<!\\)\[", r"\[", escaped)


def _filter_package_rows(
    records: Any,
    filter_text: str = "",
) -> List[Tuple[str, str, str]]:
    """Filter manifest package records into ``(name, version, location_label)`` rows.

    Pure helper with no ``textual`` dependency so null-version filtering is
    directly testable even when optional TUI packages are not installed.
    """
    if not isinstance(records, list):
        return []
    needle = (filter_text or "").lower()
    rows: List[Tuple[str, str, str]] = []
    for pkg in records:
        if not isinstance(pkg, dict):
            continue
        raw_name = pkg.get("name")
        name = raw_name if isinstance(raw_name, str) else ("" if raw_name is None else str(raw_name))
        raw_version = pkg.get("version")
        version = (
            raw_version
            if isinstance(raw_version, str)
            else ("" if raw_version is None else str(raw_version))
        )
        raw_location = pkg.get("location")
        location = (
            raw_location
            if isinstance(raw_location, str)
            else ("" if raw_location is None else str(raw_location))
        )
        editable = pkg.get("editable")
        editable_str = "Editable" if editable else "Installed"

        if needle and needle not in name.lower() and needle not in version.lower():
            continue

        loc_str = f"{editable_str} ({location})" if location else editable_str
        rows.append((name, version, loc_str))
    return rows


def _format_subprocess_rows(subprocesses: Any) -> List[Tuple[str, str, str, str]]:
    """Format manifest subprocess records into ``(cmd, start_time, elapsed, exit_code)`` rows.

    Pure helper with no ``textual`` dependency so monotonic duration preference,
    legacy wall-clock fallback, and malformed-entry guards are directly testable.
    """
    if not isinstance(subprocesses, list):
        return []
    rows: List[Tuple[str, str, str, str]] = []
    for sub in subprocesses:
        if not isinstance(sub, dict):
            continue
        raw_argv = sub.get("argv", [])
        if isinstance(raw_argv, list):
            cmd = " ".join(str(a) for a in raw_argv)
        elif raw_argv is None:
            cmd = ""
        else:
            cmd = str(raw_argv)
        start_val = _as_float(sub.get("started_at_utc"))
        end_val = _as_float(sub.get("ended_at_utc"))
        start_time = _format_timestamp(start_val)

        sp_elapsed = _as_float(sub.get("elapsed_seconds"))
        if sp_elapsed is not None:
            dur = _format_duration_detail(max(0.0, sp_elapsed))
            clock = sub.get("duration_clock")
            if clock == "monotonic":
                elapsed = f"{dur} (mono)"
            elif clock == "wall_clock":
                elapsed = f"{dur} (wall)"
            else:
                elapsed = dur
        elif start_val is not None and end_val is not None:
            elapsed = f"{_format_duration_detail(max(0.0, end_val - start_val))} (wall)"
        else:
            elapsed = "-"

        exit_code = str(sub.get("exit_code")) if sub.get("exit_code") is not None else "Running"
        rows.append((cmd, start_time, elapsed, exit_code))
    return rows


def _format_remote_url(remote: Any) -> str:
    """Return the display text for a manifest ``git.remote_url`` value."""
    if isinstance(remote, dict):
        remote = remote.get("value")
    return remote if isinstance(remote, str) and remote else "-"


def _format_os_text(host: Any) -> str:
    """Format manifest ``host.os_name``/``host.os_release`` for the OS line.

    Pure helper with no ``textual`` dependency. Missing, null, or
    whitespace-only fields never render as ``None``: a missing release is
    omitted, a missing name becomes ``unknown``, and both missing gives ``-``.
    Values are markup-escaped because the pane parses Textual markup.
    """
    if not isinstance(host, dict):
        return "-"

    def _norm(value: Any) -> str:
        text = value if isinstance(value, str) else ("" if value is None else str(value))
        return text.strip()

    name = _norm(host.get("os_name"))
    release = _norm(host.get("os_release"))
    if name and release:
        return f"{_escape_markup(name)} ({_escape_markup(release)})"
    if name:
        return _escape_markup(name)
    if release:
        return f"unknown ({_escape_markup(release)})"
    return "-"


def _format_cpu_text(cpu: Any) -> str:
    """Format manifest ``hardware.cpu`` fields for the CPU model line.

    Pure helper with no ``textual`` dependency. Missing, null, or
    whitespace-only fields never render as ``None``: when all three fields
    are missing the result is ``-``, a missing model becomes ``unknown``,
    and a missing core count or architecture is omitted from the
    parenthesized details. Values are markup-escaped because the pane
    parses Textual markup.
    """
    if not isinstance(cpu, dict):
        return "-"

    def _norm(value: Any) -> str:
        text = value if isinstance(value, str) else ("" if value is None else str(value))
        return text.strip()

    model = _norm(cpu.get("model"))
    cores = _norm(cpu.get("logical_cores"))
    arch = _norm(cpu.get("architecture"))
    if not model and not cores and not arch:
        return "-"

    head = _escape_markup(model) if model else "unknown"
    details: List[str] = []
    if cores:
        details.append(f"{_escape_markup(cores)} cores")
    if arch:
        details.append(_escape_markup(arch))
    if details:
        return f"{head} ({', '.join(details)})"
    return head


def _unwrap_hostname(host: Any) -> Optional[str]:
    """Extract a plain hostname string from a manifest ``host`` section."""
    if not isinstance(host, dict):
        return None
    val = host.get("hostname")
    if isinstance(val, dict):
        val = val.get("value")
    return val if isinstance(val, str) and val else None


class RunDetailsView(Vertical):
    """Component to display all metadata groups for a single selected run."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.run_info: Optional[RunInfo] = None
        self._hydrated_manifest: Optional[Dict[str, Any]] = None
        self._hydration_report: Optional[Any] = None
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
        # Setup Packages table with narrow-terminal-friendly widths
        pkg_table = self.query_one("#packages-table", DataTable)
        pkg_table.add_column("Package Name", width=22)
        pkg_table.add_column("Version", width=12)
        pkg_table.add_column("Editable / Location")
        pkg_table.cursor_type = "row"

        # Setup Subprocesses table (preserve Elapsed width=18 for timing consumers)
        sub_table = self.query_one("#subprocesses-table", DataTable)
        sub_table.add_column("Command", width=24)
        sub_table.add_column("Start Time", width=16)
        sub_table.add_column("Elapsed", width=18)
        sub_table.add_column("Exit Code", width=9)
        sub_table.cursor_type = "row"

        # Start periodic refresh for active runs
        self.set_interval(1.0, self.refresh_live_metrics)

    def show_onboarding(self) -> None:
        """Render getting-started guidance when no runs exist in the output directory."""
        self.run_info = None
        self._hydrated_manifest = None
        self._hydration_report = None
        self.query_one("#packages-table", DataTable).clear()
        self.query_one("#subprocesses-table", DataTable).clear()
        lines = [
            "[bold #cba6f7]=== NO RUNS FOUND ===[/bold #cba6f7]",
            "",
            "No pubrun runs were found in the configured output directory.",
            "",
            "[bold]Get started:[/]",
            "  1. Add [bold]import pubrun[/] to your Python script and run it normally.",
            "  2. Run [bold]pubrun init[/] in your project directory to create a .pubrun.toml file.",
            "  3. Press [bold]Ctrl+R[/] to refresh once runs appear, or press [bold]?[/] for keybindings.",
        ]
        self.query_one("#lbl-general-info", Static).update("\n".join(lines))

    def _active_manifest(self) -> Optional[Dict[str, Any]]:
        """Return the cached hydrated manifest (falling back to ``run_info.manifest``)."""
        if self._hydrated_manifest is not None:
            return self._hydrated_manifest
        if self.run_info is not None and isinstance(self.run_info.manifest, dict):
            return self.run_info.manifest
        return None

    def display_run(self, run_info: RunInfo) -> None:
        """Load manifest on demand, hydrate once, and update all detail panes."""
        self.run_info = run_info
        self._hydrated_manifest = None
        self._hydration_report = None

        raw_manifest = run_info.manifest if run_info.manifest is not None else run_info.load_manifest()
        if isinstance(raw_manifest, dict):
            try:
                from pubrun.report.utils import hydrate_manifest_with_report

                manifest_path = str(Path(run_info.run_dir) / "manifest.json")
                hydrated, _, report = hydrate_manifest_with_report(manifest_path, raw_manifest)
                self._hydrated_manifest = hydrated if isinstance(hydrated, dict) else raw_manifest
                self._hydration_report = report
            except Exception:
                self._hydrated_manifest = raw_manifest
                self._hydration_report = None

        self.update_general_pane()
        self.update_packages_pane()
        self.update_subprocesses_pane()

    def refresh_live_metrics(self) -> None:
        """Periodic callback to update CPU/Memory for running processes without retaining manifests."""
        if self.run_info and self.run_info.status == STATUS_RUNNING:
            try:
                refreshed = RunInfo(self.run_info.run_dir, keep_manifest=False)
                self.run_info = refreshed
                self.update_general_pane()
            except Exception:
                pass

    def update_general_pane(self) -> None:
        """Re-render the core run stats on the General Info tab."""
        if not self.run_info:
            return

        r = self.run_info
        manifest = self._active_manifest()
        lines: List[str] = []
        lines.append("[bold #cba6f7]=== RUN IDENTITY ===[/bold #cba6f7]")
        lines.append(f"  [bold]Run ID:[/]        {r.run_id or '-'}")
        lines.append(f"  [bold]Script:[/]        {_escape_markup(str(r.script)) if r.script else '-'}")
        lines.append(f"  [bold]Arguments:[/]     {_escape_markup(str(r.args)) if r.args else '-'}")
        lines.append(f"  [bold]Status:[/]        {r.status.upper()}")
        lines.append(f"  [bold]Directory:[/]     {_escape_markup(str(r.run_dir))}")
        lines.append("")

        lines.append("[bold #cba6f7]=== TIMING & METRICS ===[/bold #cba6f7]")
        lines.append(f"  [bold]Started:[/]       {_format_timestamp(r.started_at_utc)}")
        if r.ended_at_utc is not None:
            lines.append(f"  [bold]Ended:[/]         {_format_timestamp(r.ended_at_utc)}")
        sem = getattr(r, "timing_semantics", None) or classify_timing_semantics(
            manifest.get("timing") if isinstance(manifest, dict) else None,
            status=r.status,
        )
        elapsed_label = _escape_markup(str(sem.get("label", "Elapsed")))
        elapsed_display = (
            "-"
            if r.elapsed is None or sem.get("is_incomplete")
            else _format_duration_detail(r.elapsed)
        )
        lines.append(f"  [bold]{elapsed_label}:[/] {elapsed_display}")
        lines.append(
            "  [bold]Timing Scope:[/]  tracked interval "
            "(start() to stop(), not full process lifetime if imported late)"
        )
        if r.startup_overhead_seconds is not None:
            lines.append(
                f"  [bold]Startup overhead:[/] {_format_duration_detail(r.startup_overhead_seconds)}"
            )
        if r.finalization_overhead_seconds is not None:
            fin_str = _format_duration_detail(r.finalization_overhead_seconds)
            if r.hardware_wait_seconds is not None:
                fin_str += (
                    f" (includes Hardware wait: {_format_duration_detail(r.hardware_wait_seconds)})"
                )
            lines.append(f"  [bold]Finalization overhead:[/] {fin_str}")
        elif r.hardware_wait_seconds is not None:
            lines.append(
                f"  [bold]Hardware wait:[/] {_format_duration_detail(r.hardware_wait_seconds)}"
            )
        if r.session_seconds is not None:
            lines.append(
                f"  [bold]Tracked session:[/] {_format_duration_detail(r.session_seconds)}"
            )
        if r.background_hardware_seconds is not None:
            lines.append(
                f"  [bold]Background hardware (overlaps workload):[/] "
                f"{_format_duration_detail(r.background_hardware_seconds)}"
            )
        lines.append(f"  [bold]Exit Code:[/]     {r.exit_code if r.exit_code is not None else '-'}")
        lines.append("")

        # Live or Peak resources
        lines.append("[bold #cba6f7]=== RESOURCE CONSUMPTION ===[/bold #cba6f7]")
        if r.status == STATUS_RUNNING:
            lines.append(f"  [bold]Process PID:[/]   {r.pid or '-'}")
            lines.append(f"  [bold]Live RSS Memory:[/] {_format_bytes(r.rss_bytes)}")
            cpu_str = f"{r.cpu_percent:.1f}%" if r.cpu_percent is not None else "-"
            lines.append(f"  [bold]Live CPU usage:[/] {cpu_str}")
        elif isinstance(manifest, dict):
            res = manifest.get("resources")
            res = res if isinstance(res, dict) else {}
            peak_rss = res.get("peak_rss_bytes")
            peak_cpu = res.get("peak_cpu_percent")
            lines.append(f"  [bold]Peak RSS Memory:[/] {_format_bytes(peak_rss)}")
            lines.append(f"  [bold]Peak CPU usage:[/] {f'{peak_cpu:.1f}%' if peak_cpu is not None else '-'}")
        else:
            lines.append("  (No resource metadata recorded)")
        lines.append("")

        # Git (uses hydrated manifest when available)
        lines.append("[bold #cba6f7]=== REPOSITORY PROVENANCE (GIT) ===[/bold #cba6f7]")
        git = manifest.get("git") if isinstance(manifest, dict) else None
        if isinstance(git, dict):
            dirty_val = git.get("dirty")
            dirty_str = "not checked" if dirty_val is None else str(dirty_val)
            lines.append(f"  [bold]Commit Hash:[/]   {_escape_markup(str(git.get('commit') or '-'))}")
            lines.append(f"  [bold]Branch:[/]        {_escape_markup(str(git.get('branch') or '-'))}")
            lines.append(f"  [bold]Repo Dirty:[/]     {dirty_str}")
            lines.append(f"  [bold]Remote URL:[/]     {_escape_markup(_format_remote_url(git.get('remote_url')))}")
        elif r.lock_data:
            lines.append(f"  [bold]Commit Hash:[/]   {_escape_markup(str(r.git_commit or '-'))}")
            lines.append(f"  [bold]Working Cwd:[/]   {_escape_markup(str(r.cwd or '-'))}")
        else:
            lines.append("  (No git information available)")
        lines.append("")

        # System/Host (uses hydrated manifest when available)
        lines.append("[bold #cba6f7]=== HOST & HARDWARE SPECS ===[/bold #cba6f7]")
        host_sec = manifest.get("host") if isinstance(manifest, dict) else None
        hostname_val = r.hostname or _unwrap_hostname(host_sec)
        lines.append(f"  [bold]Hostname:[/]      {_escape_markup(hostname_val) if hostname_val else '-'}")
        if isinstance(manifest, dict):
            host = host_sec if isinstance(host_sec, dict) else {}
            hw = manifest.get("hardware")
            hw = hw if isinstance(hw, dict) else {}
            cpu = hw.get("cpu")
            cpu = cpu if isinstance(cpu, dict) else {}
            gpus = hw.get("gpus")
            gpus = [g for g in gpus if isinstance(g, dict)] if isinstance(gpus, list) else []
            lines.append(f"  [bold]OS:[/]            {_format_os_text(host)}")
            lines.append(f"  [bold]CPU model:[/]     {_format_cpu_text(cpu)}")
            lines.append(f"  [bold]Total RAM:[/]     {_format_bytes(hw.get('memory_total_bytes'))}")
            if gpus:
                lines.append("  [bold]GPUs Detected:[/]")
                for idx, gpu in enumerate(gpus):
                    gpu_model = _escape_markup(str(gpu.get("model") or gpu.get("name") or "unknown"))
                    driver = _escape_markup(str(gpu.get("driver_version") or "-"))
                    lines.append(f"    - [{idx}] {gpu_model} (Driver: {driver})")
        else:
            lines.append("  (No host specs recorded)")
        lines.append("")

        # Reproducibility & Evidence (read-only manifest summary; never runs live preflight)
        lines.append("[bold #cba6f7]=== REPRODUCIBILITY & EVIDENCE ===[/bold #cba6f7]")
        if r.status == STATUS_RUNNING:
            lines.append(
                "  Run is still in progress; full reproducibility assessment is available "
                "once manifest.json finalizes."
            )
        elif isinstance(manifest, dict):
            try:
                import socket
                from pubrun.report.reproducibility import (
                    assess_run,
                    format_reproducibility_summary,
                )

                manifest_path = str(Path(r.run_dir) / "manifest.json")
                try:
                    current_hostname: Optional[str] = socket.gethostname()
                except Exception:
                    current_hostname = None
                assessment = assess_run(
                    manifest,
                    manifest_path=manifest_path,
                    hydration_report=self._hydration_report,
                    current_hostname=current_hostname,
                    preflight=False,
                )
                for summary_line in format_reproducibility_summary(assessment).splitlines():
                    lines.append(f"  {_escape_markup(summary_line)}")
            except Exception:
                lines.append("  (Reproducibility assessment unavailable for this run)")
        else:
            lines.append("  (No finalized manifest.json available for reproducibility assessment)")

        self.query_one("#lbl-general-info", Static).update("\n".join(lines))

    def update_packages_pane(self, filter_text: Optional[str] = None) -> None:
        """Repopulate the dependencies table, reapplying current search text when omitted."""
        table = self.query_one("#packages-table", DataTable)
        table.clear()

        manifest = self._active_manifest()
        if not self.run_info or not isinstance(manifest, dict):
            return

        if filter_text is None:
            try:
                filter_text = self.query_one("#pkg-search", Input).value.strip()
            except Exception:
                filter_text = ""

        packages_sec = manifest.get("packages") or {}
        records = packages_sec.get("records") if isinstance(packages_sec, dict) else []

        for row_idx, (name, version, loc_str) in enumerate(
            _filter_package_rows(records, filter_text)
        ):
            table.add_row(name, version, loc_str, key=str(row_idx))

    def update_subprocesses_pane(self) -> None:
        """Repopulate the child subprocess execution table."""
        table = self.query_one("#subprocesses-table", DataTable)
        table.clear()

        manifest = self._active_manifest()
        if not self.run_info or not isinstance(manifest, dict):
            return

        subprocesses = manifest.get("subprocesses", [])
        for row_idx, (cmd, start_time, elapsed, exit_code) in enumerate(
            _format_subprocess_rows(subprocesses)
        ):
            table.add_row(cmd, start_time, elapsed, exit_code, key=str(row_idx))

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "pkg-search":
            self.update_packages_pane(event.value.strip())
