"""
Actions and Citations panel for managing runs (deleting, archiving, and methods citations).
"""

from __future__ import annotations
import json
import shutil
import zipfile
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Label, RichLog, Input, Checkbox
from textual.screen import ModalScreen
from rich.text import Text

from pubrun.status import RunInfo, clean_runs, STATUS_RUNNING
from pubrun.report.methods import generate_report
from pubrun.report.utils import hydrate_manifest

# Dynamic clipboard helper
def copy_to_clipboard(text: str) -> bool:
    """Attempt to copy text to system clipboard using native commands."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text, text=True, check=True)
            return True
        elif sys.platform == "win32":
            subprocess.run(["clip"], input=text, text=True, check=True)
            return True
        else:
            # Linux / BSD: try xclip or xsel
            for cmd in [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
                try:
                    subprocess.run(cmd, input=text, text=True, check=True)
                    return True
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
    except Exception:
        pass
    return False


class ConfirmDeleteModal(ModalScreen[bool]):
    """Safety modal confirming deletion of a run directory."""

    def __init__(self, run_id: str, is_running: bool = False) -> None:
        super().__init__()
        self.run_id = run_id
        self.is_running = is_running

    def compose(self) -> ComposeResult:
        title = "CONFIRM ACTIVE RUN DELETION" if self.is_running else "CONFIRM RUN DELETION"
        yield Vertical(
            Label(title, id="dialog-title"),
            Label(f"Are you sure you want to permanently delete run {self.run_id[:8]}?", classes="info-label"),
            Label("This will delete the manifest, configuration, and log files. This is irreversible!", id="dialog-message"),
            Input(placeholder="Type 'yes' to confirm", id="input-confirm-yes"),
            Horizontal(
                Button("Cancel", id="btn-cancel-del"),
                Button("CONFIRM DELETE", id="btn-confirm-del", variant="error", disabled=True),
                classes="horizontal-buttons"
            ),
            id="dialog-container"
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "input-confirm-yes":
            confirm_btn = self.query_one("#btn-confirm-del", Button)
            confirm_btn.disabled = (event.value.strip().lower() != "yes")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel-del":
            self.dismiss(False)
        elif event.button.id == "btn-confirm-del":
            self.dismiss(True)


class ActionsPanel(Vertical):
    """Component handling citations compiler, rerun command, archive compress, and deletions."""

    def __init__(self, output_dir: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.output_dir = output_dir
        self.run_info: Optional[RunInfo] = None
        self.raw_manifest: Optional[Dict[str, Any]] = None

    def compose(self) -> ComposeResult:
        with Horizontal(classes="grid-container"):
            # Left Card: Citation & Rerun
            with Vertical(classes="panel-card"):
                yield Label("CITATION & REPLICABILITY", classes="panel-card-title")
                yield Label("Rerun Command:", classes="info-label")
                yield Static("Select a run to view rerun command.", id="lbl-rerun-command", classes="info-value")
                yield Button("Copy Rerun Command", id="btn-copy-rerun", variant="primary")
                yield Label("Academic Methods Citation:", classes="info-label")
                yield ScrollableContainer(Static("", id="lbl-methods-citation"), classes="transcript-area")
                with Horizontal():
                    yield Button("Copy Markdown", id="btn-copy-md", variant="primary")
                    yield Button("Copy LaTeX", id="btn-copy-latex", variant="primary")

            # Right Card: Run Archiving & Deletion
            with Vertical(classes="panel-card"):
                yield Label("RUN MANAGEMENT", classes="panel-card-title")
                yield Label("Archive / Compress Run Folder:", classes="info-label")
                yield Static("Packs current run folder into zip under run_dir/archive/.", classes="info-value")
                yield Button("Archive Run (ZIP)", id="btn-archive-run", variant="success")
                yield Checkbox("Delete raw directory after archiving", value=False, id="check-delete-raw")
                yield Label("Danger Zone:", classes="info-label")
                yield Button("Delete Selected Run", id="btn-delete-selected", variant="error")

        # Bottom section: Bulk cleanup
        with Vertical(classes="panel-card margin-vertical"):
            yield Label("BULK RUN CLEANUP", classes="panel-card-title")
            with Horizontal(id="cleanup-inputs"):
                yield Label("Older Than:", classes="info-label")
                yield Input("7d", id="input-clean-older", placeholder="e.g. 7d, 24h")
                yield Label("Statuses (comma separated):", classes="info-label")
                yield Input("completed,failed,crashed,ghost", id="input-clean-status")
            with Horizontal():
                yield Button("Preview Prune (Dry Run)", id="btn-prune-dry", variant="primary")
                yield Button("Execute Prune", id="btn-prune-execute", variant="error")
            yield RichLog(id="cleanup-log-output", max_lines=500, classes="log-area")

    def display_run(self, run_info: RunInfo) -> None:
        """Update display citation, rerun, and manifest fields."""
        self.run_info = run_info
        self.raw_manifest = None

        rerun_lbl = self.query_one("#lbl-rerun-command", Static)
        citation_lbl = self.query_one("#lbl-methods-citation", Static)

        if not run_info:
            rerun_lbl.update("Select a run.")
            citation_lbl.update("")
            return

        # Fetch Rerun Command
        rerun_cmd = "-"
        if run_info.manifest:
            self.raw_manifest = run_info.manifest
            rerun_cmd = run_info.manifest.get("invocation", {}).get("rerun_command") or "-"
        elif run_info.lock_data:
            # Reconstruct rerun if locked
            argv = run_info.lock_data.get("argv", [])
            script = run_info.lock_data.get("script", "")
            cwd = run_info.lock_data.get("cwd", "")
            rerun_cmd = f"cd {cwd} && python {script} " + " ".join(argv)

        rerun_lbl.update(rerun_cmd)

        # Generate Methods Citation
        methods_str = "(No citation available - manifest not complete)"
        if run_info.manifest:
            try:
                # Hydrate manifest
                path = Path(run_info.run_dir) / "manifest.json"
                hydrated, _ = hydrate_manifest(str(path), run_info.manifest)
                methods_str = generate_report(hydrated, "markdown")
            except Exception as e:
                methods_str = f"Failed to compile citation: {e}"

        citation_lbl.update(methods_str)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self.run_info and event.button.id in ("btn-copy-rerun", "btn-copy-md", "btn-copy-latex", "btn-archive-run", "btn-delete-selected"):
            self.app.notify("Please select a run first.", severity="error")
            return

        if event.button.id == "btn-copy-rerun":
            cmd = self.query_one("#lbl-rerun-command", Static).renderable
            if cmd and cmd != "-":
                if copy_to_clipboard(str(cmd)):
                    self.app.notify("Rerun command copied to clipboard.", severity="information")
                else:
                    self.app.notify("Failed to copy automatically. Please copy text manually.", severity="warning")

        elif event.button.id in ("btn-copy-md", "btn-copy-latex"):
            if not self.raw_manifest:
                self.app.notify("Citations not available.", severity="error")
                return
            try:
                path = Path(self.run_info.run_dir) / "manifest.json"
                hydrated, _ = hydrate_manifest(str(path), self.raw_manifest)
                fmt = "markdown" if event.button.id == "btn-copy-md" else "latex"
                text = generate_report(hydrated, fmt)
                if copy_to_clipboard(text):
                    self.app.notify(f"Methods ({fmt}) copied to clipboard.", severity="information")
                else:
                    self.app.notify("Failed to copy. Copy text manually.", severity="warning")
            except Exception as e:
                self.app.notify(f"Failed: {e}", severity="error")

        elif event.button.id == "btn-archive-run":
            self.archive_selected_run()

        elif event.button.id == "btn-delete-selected":
            is_active = (self.run_info.status == STATUS_RUNNING)
            self.app.push_screen(ConfirmDeleteModal(self.run_info.run_id, is_active), self.handle_deletion_result)

        elif event.button.id in ("btn-prune-dry", "btn-prune-execute"):
            dry_run = (event.button.id == "btn-prune-dry")
            self.run_bulk_prune(dry_run)

    def archive_selected_run(self) -> None:
        """Create zip archive in runs_dir/archive/ and optionally delete original folder."""
        r = self.run_info
        if not r or not r.run_dir.exists():
            return

        runs_dir = r.run_dir.parent
        archive_dir = runs_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        zip_path = archive_dir / f"{r.run_id or r.run_dir.name}.zip"

        try:
            # Zip original folder
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_f:
                for file_p in r.run_dir.rglob("*"):
                    if file_p.is_file():
                        zip_f.write(file_p, file_p.relative_to(r.run_dir))

            self.app.notify(f"Created archive: {zip_path.name}", severity="information")

            # Check if deleting raw
            delete_raw = self.query_one("#check-delete-raw", Checkbox).value
            if delete_raw:
                shutil.rmtree(r.run_dir)
                self.app.notify("Deleted original uncompressed directory.", severity="information")
                # Post refresh to main app
                self.app.post_message(self.app.RefreshSidebar())

        except Exception as e:
            self.app.notify(f"Archive failed: {e}", severity="error")

    def handle_deletion_result(self, confirmed: bool) -> None:
        if not confirmed or not self.run_info:
            return

        try:
            shutil.rmtree(self.run_info.run_dir)
            self.app.notify(f"Successfully deleted run {self.run_info.run_id[:8]}", severity="information")
            self.app.post_message(self.app.RefreshSidebar())
        except Exception as e:
            self.app.notify(f"Deletion failed: {e}", severity="error")

    def run_bulk_prune(self, dry_run: bool) -> None:
        """Execute or dry-run a bulk cleanup pruning candidates."""
        log = self.query_one("#cleanup-log-output", RichLog)
        log.clear()

        # Parse older than
        older_val = self.query_one("#input-clean-older", Input).value.strip()
        older_than_days: Optional[float] = None
        if older_val:
            val = older_val.lower()
            try:
                if val.endswith("d"):
                    older_than_days = float(val[:-1])
                elif val.endswith("h"):
                    older_than_days = float(val[:-1]) / 24.0
                else:
                    older_than_days = float(val)
            except ValueError:
                self.app.notify("Invalid age format. Use '7d' or '24h'.", severity="error")
                return

        # Parse statuses
        status_val = self.query_one("#input-clean-status", Input).value.strip()
        status_filter = [s.strip() for s in status_val.split(",")] if status_val else None

        log.write(f"Scanning runs for pruning (dry_run={dry_run})...")

        # Redirect print functions to our TUI Log area
        import io
        import contextlib
        buffer = io.StringIO()

        try:
            with contextlib.redirect_stdout(buffer):
                # Run the status.py clean_runs logic
                clean_runs(
                    output_dir=self.output_dir,
                    older_than_days=older_than_days,
                    status_filter=status_filter,
                    yes=True,
                    dry_run=dry_run
                )
            
            # Print output to textual widget
            output_str = buffer.getvalue()
            
            # Strip color escape codes if any
            clean_str = output_str.replace("\033[32m", "").replace("\033[31m", "")
            clean_str = clean_str.replace("\033[35m", "").replace("\033[33m", "")
            clean_str = clean_str.replace("\033[90m", "").replace("\033[0m", "")
            
            log.write(clean_str)
            
            if not dry_run:
                self.app.notify("Pruning complete.", severity="information")
                self.app.post_message(self.app.RefreshSidebar())
        except Exception as e:
            log.write(f"Pruning failed: {e}")
            self.app.notify(f"Prune failed: {e}", severity="error")
