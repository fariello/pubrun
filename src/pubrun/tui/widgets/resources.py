"""Resource-usage view for the TUI: CPU / memory over a run's lifecycle.

Reuses the same per-sample series (`events.jsonl`) and peak/avg/min digest that `pubrun res`
renders on the CLI, so the numbers are identical, and also surfaces populated
``manifest.resources`` summary fields alongside samples or as a fallback when
``events.jsonl`` has no samples.
"""
from __future__ import annotations
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.widgets import Static

from pubrun.status import RunInfo, _format_bytes


def _as_finite_float(val: Any) -> Optional[float]:
    if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val):
        return float(val)
    return None


def _as_dict(val: Any) -> Dict[str, Any]:
    return val if isinstance(val, dict) else {}


def _format_manifest_resources_summary(resources: Any) -> List[str]:
    """Extract human-readable summary lines from ``manifest['resources']``."""
    if not isinstance(resources, dict):
        return []

    lines: List[str] = []

    peak_rss = _as_finite_float(resources.get("peak_rss_bytes"))
    if peak_rss is not None:
        lines.append(f"  Peak RSS:      {_format_bytes(int(peak_rss))}")

    peak_cpu = _as_finite_float(resources.get("peak_cpu_percent"))
    if peak_cpu is not None:
        lines.append(f"  Peak CPU:      {peak_cpu:.1f}%")

    sysmem = _as_dict(resources.get("system_memory"))
    if sysmem:
        start = _as_dict(sysmem.get("start"))
        worst = _as_dict(sysmem.get("min_available"))
        avail = _as_finite_float(start.get("available_bytes"))
        total = _as_finite_float(start.get("total_bytes"))
        if avail is not None and total is not None and total > 0:
            lines.append(
                f"  System RAM:    {_format_bytes(int(avail))} available of "
                f"{_format_bytes(int(total))} at start"
            )
        worst_avail = _as_finite_float(worst.get("available_bytes"))
        if worst_avail is not None:
            lines.append(f"  Min Avail RAM: {_format_bytes(int(worst_avail))} (lowest during run)")

    load = _as_dict(resources.get("load_average"))
    if load:
        start_dict = _as_dict(load.get("start"))
        start_1m = _as_finite_float(start_dict.get("1min"))
        max_1m = _as_finite_float(load.get("max_1min"))
        parts: List[str] = []
        if start_1m is not None:
            parts.append(f"{start_1m:.2f} at start")
        if max_1m is not None:
            parts.append(f"{max_1m:.2f} peak (1-min)")
        if parts:
            lines.append(f"  Load Average:  {', '.join(parts)}")

    raw_iowait = resources.get("system_iowait_pct")
    if isinstance(raw_iowait, dict):
        mx = _as_finite_float(raw_iowait.get("max"))
        if mx is not None:
            lines.append(f"  Node iowait:   {mx}% peak (node-wide, indicative only)")
    else:
        iowait_val = _as_finite_float(raw_iowait)
        if iowait_val is not None:
            lines.append(f"  Node iowait:   {iowait_val}% (node-wide, indicative only)")

    io_counters = _as_dict(resources.get("io_counters"))
    if io_counters:
        delta = _as_dict(io_counters.get("delta"))
        rb = _as_finite_float(delta.get("read_bytes"))
        wb = _as_finite_float(delta.get("write_bytes"))
        rc = _as_finite_float(delta.get("rchar"))
        wc = _as_finite_float(delta.get("wchar"))
        if rb is not None or wb is not None:
            rb_val = int(rb) if rb is not None else 0
            wb_val = int(wb) if wb is not None else 0
            lines.append(
                f"  Disk I/O:      read {_format_bytes(rb_val)}, "
                f"wrote {_format_bytes(wb_val)} (storage layer)"
            )
        if rc is not None or wc is not None:
            rc_val = int(rc) if rc is not None else 0
            wc_val = int(wc) if wc is not None else 0
            lines.append(
                f"  Logical I/O:   read {_format_bytes(rc_val)}, "
                f"wrote {_format_bytes(wc_val)} (incl. cache)"
            )

    return lines


class RunResourcesView(Vertical):
    """Displays CPU/memory usage (summary + sparklines) for the selected run."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.run_info: Optional[RunInfo] = None

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            Static("Select a run to view its CPU and memory usage.", id="resources-body")
        )

    def clear(self) -> None:
        """Reset the resources view to its empty no-run state."""
        self.run_info = None
        self.query_one("#resources-body", Static).update(
            "Select a run to view its CPU and memory usage."
        )

    def display_run(self, run_info: Optional[RunInfo]) -> None:
        """Render the resource digest and manifest summary for ``run_info`` (never raises)."""
        if run_info is None:
            self.clear()
            return
        self.run_info = run_info
        body = self.query_one("#resources-body", Static)
        try:
            from pubrun.report.diagnostics import format_resource_digest, read_resource_series

            events = Path(run_info.run_dir) / "events.jsonl"
            series: Optional[Dict[str, Any]] = None
            has_samples = False
            if events.exists():
                series = read_resource_series(events)
                has_samples = bool(series and series.get("timestamps"))

            manifest = run_info.manifest if run_info.manifest is not None else run_info.load_manifest()
            resources = manifest.get("resources") if isinstance(manifest, dict) else None
            summary_lines = _format_manifest_resources_summary(resources)

            if has_samples and series is not None:
                digest = format_resource_digest(series)
                if summary_lines:
                    body.update(
                        digest + "\n\nManifest Resource Summary:\n" + "\n".join(summary_lines)
                    )
                else:
                    body.update(digest)
                return

            if summary_lines:
                body.update(
                    "Manifest Resource Summary (no per-sample timeline in events.jsonl):\n"
                    + "\n".join(summary_lines)
                )
                return

            if not events.exists():
                body.update(
                    "No resource samples recorded for this run "
                    "(no events.jsonl — the run was very short or resource capture was off)."
                )
            else:
                body.update(format_resource_digest(series or {"timestamps": []}))
        except Exception as e:  # a rendering hiccup must never crash the TUI
            body.update(f"Could not render resource usage: {type(e).__name__}: {e}")
