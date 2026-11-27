"""
Actions and Citations panel for managing runs (deleting, archiving, and methods citations).
"""

from __future__ import annotations
import contextlib
import io
import re
import shlex
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, RichLog, Static
from rich.text import Text

from pubrun.status import (
    RunInfo,
    STATUS_RUNNING,
    VALID_STATUSES,
    _dir_size,
    _format_bytes,
    _inspect_run_lock,
    _resolve_output_dir,
    clean_runs,
    filter_runs,
    safe_delete_run_dir,
    scan_runs,
)
from pubrun.report.diagnostics import format_redacted_rerun_advisory
from pubrun.report.methods import generate_report
from pubrun.report.utils import hydrate_manifest


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _refresh_sidebar_message(app: Any) -> Message:
    """Create a RefreshSidebar message for ``app`` without a top-level circular import."""
    refresh_cls = getattr(app, "RefreshSidebar", None)
    if isinstance(refresh_cls, type) and issubclass(refresh_cls, Message):
        return refresh_cls()
    from pubrun.tui.app import PubrunTUIApp
    return PubrunTUIApp.RefreshSidebar()


def _format_delete_reason(run_dir: Path, reason: Optional[str]) -> str:
    """Normalize ``safe_delete_run_dir`` error messages to avoid redundant prefixes."""
    detail = reason or "unknown error"
    prefix = f"Failed to remove {run_dir.name}: "
    if detail.startswith(prefix):
        detail = detail[len(prefix):]
    return detail


def _build_rerun_command(lock_data: Dict[str, Any]) -> str:
    """Reconstruct a shell-safe rerun command from a run's ``.pubrun.lock`` payload.

    On Windows (``sys.platform == "win32"``), emits PowerShell 5.1-safe two-line
    output (``cd <cwd>\\n<py_cmd>``) instead of ``&&``. On POSIX, preserves
    ``cd <cwd> && <py_cmd>``. Avoids duplicating ``script`` when ``sys_argv`` is
    present or ``argv`` already begins with ``script``.
    """
    sys_argv = lock_data.get("sys_argv")
    if isinstance(sys_argv, list) and sys_argv:
        tokens = [str(a) for a in sys_argv]
    else:
        raw_argv = lock_data.get("argv", [])
        argv = [str(a) for a in raw_argv] if isinstance(raw_argv, list) else []
        script = str(lock_data.get("script") or "")
        if script:
            if argv and (
                argv[0] == script
                or Path(argv[0]).name == script
                or Path(argv[0]).stem == script
            ):
                tokens = argv
            else:
                tokens = [script] + argv
        else:
            tokens = argv

    cmd_tokens = ["python"] + tokens
    cwd = str(lock_data.get("cwd") or "")
    if sys.platform == "win32":
        py_cmd = subprocess.list2cmdline(cmd_tokens)
        if cwd:
            return f"cd {subprocess.list2cmdline([cwd])}\n{py_cmd}"
        return py_cmd

    py_cmd = shlex.join(cmd_tokens)
    return f"cd {shlex.quote(cwd)} && {py_cmd}" if cwd else py_cmd


# Dynamic clipboard helper
def copy_to_clipboard(text: str) -> bool:
    """Attempt to copy text to system clipboard using native commands."""
    try:
        if sys.platform == "darwin":
            subprocess.run(
                ["pbcopy"],
                input=text,
                text=True,
                check=True,
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        elif sys.platform == "win32":
            subprocess.run(
                ["clip"],
                input=text,
                text=True,
                check=True,
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        else:
            # Linux / BSD: try wl-copy (Wayland), xclip, then xsel
            for cmd in [
                ["wl-copy"],
                ["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"],
            ]:
                try:
                    subprocess.run(
                        cmd,
                        input=text,
                        text=True,
                        check=True,
                        timeout=5,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True
                except (
                    FileNotFoundError,
                    subprocess.CalledProcessError,
                    subprocess.TimeoutExpired,
                ):
                    continue
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        pass
    return False


class ConfirmDeleteModal(ModalScreen[bool]):
    """Safety modal confirming deletion of a run directory."""

    def __init__(self, run_id: Optional[str], is_running: bool = False) -> None:
        super().__init__()
        self.run_id = run_id
        self.run_is_active = is_running

    def compose(self) -> ComposeResult:
        title = "CONFIRM ACTIVE RUN DELETION" if self.run_is_active else "CONFIRM RUN DELETION"
        short_id = (self.run_id or "unknown")[:8]
        yield Vertical(
            Label(title, id="dialog-title"),
            Label(f"Are you sure you want to permanently delete run {short_id}?", classes="info-label"),
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


class ConfirmBulkPruneModal(ModalScreen[bool]):
    """Safety modal confirming permanent bulk deletion of matched runs."""

    def __init__(
        self,
        matched_count: int,
        total_size_bytes: int,
        older_than: str = "",
        status_filter: str = "",
    ) -> None:
        super().__init__()
        self.matched_count = matched_count
        self.total_size_bytes = total_size_bytes
        self.older_than = older_than
        self.status_filter = status_filter

    def compose(self) -> ComposeResult:
        size_str = _format_bytes(self.total_size_bytes)
        criteria_parts: List[str] = []
        if self.older_than:
            criteria_parts.append(f"older than {self.older_than}")
        if self.status_filter:
            criteria_parts.append(f"statuses: {self.status_filter}")
        criteria_note = f"Criteria: {'; '.join(criteria_parts)}." if criteria_parts else "Criteria: all deletable runs."
        yield Vertical(
            Label("CONFIRM BULK PRUNE", id="dialog-title"),
            Label(
                f"Permanently delete {self.matched_count} run(s) freeing {size_str}?",
                classes="info-label",
            ),
            Label(
                f"{criteria_note} This action cannot be undone!",
                id="dialog-message",
            ),
            Horizontal(
                Button("Cancel", id="btn-cancel-bulk-prune"),
                Button("CONFIRM PRUNE", id="btn-confirm-bulk-prune", variant="error"),
                classes="horizontal-buttons",
            ),
            id="dialog-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel-bulk-prune":
            self.dismiss(False)
        elif event.button.id == "btn-confirm-bulk-prune":
            self.dismiss(True)


class ActionsPanel(Vertical):
    """Component handling citations compiler, rerun command, archive compress, and deletions."""

    def __init__(self, output_dir: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.output_dir = output_dir
        self.run_info: Optional[RunInfo] = None
        self.raw_manifest: Optional[Dict[str, Any]] = None
        self.rerun_command: Optional[str] = None

    def compose(self) -> ComposeResult:
        all_statuses = ", ".join(VALID_STATUSES)
        with ScrollableContainer(id="actions-scroll"):
            with Horizontal(classes="grid-container"):
                # Left Card: Citation & Rerun
                with Vertical(classes="panel-card"):
                    yield Label("CITATION & REPLICABILITY", classes="panel-card-title")
                    yield Label("Rerun Command:", classes="info-label")
                    yield Static("Select a run to view rerun command.", id="lbl-rerun-command", classes="info-value")
                    yield Static("", id="lbl-rerun-advisory", classes="info-value")
                    yield Button("Copy Rerun Command", id="btn-copy-rerun", variant="primary")
                    yield Label("Academic Methods Citation:", classes="info-label")
                    yield ScrollableContainer(Static("", id="lbl-methods-citation"), classes="transcript-area")
                    with Horizontal(classes="button-row"):
                        yield Button("Copy Markdown", id="btn-copy-md", variant="primary")
                        yield Button("Copy LaTeX", id="btn-copy-latex", variant="primary")

                # Right Card: Run Archiving & Deletion
                with Vertical(classes="panel-card"):
                    yield Label("RUN MANAGEMENT", classes="panel-card-title")
                    yield Label("Archive / Compress Run Folder:", classes="info-label")
                    yield Static(
                        "Packs current run folder into <output_dir>/archive/<run_id>.zip.",
                        id="lbl-archive-dest",
                        classes="info-value",
                    )
                    yield Button("Archive Run (ZIP)", id="btn-archive-run", variant="success")
                    yield Checkbox("Delete raw directory after archiving", value=False, id="check-delete-raw")
                    yield Label("Danger Zone:", classes="info-label")
                    yield Button("Delete Selected Run", id="btn-delete-selected", variant="error")

            # Bottom section: Bulk cleanup
            with Vertical(classes="panel-card margin-vertical"):
                yield Label("BULK RUN CLEANUP", classes="panel-card-title")
                with Horizontal(id="cleanup-inputs"):
                    yield Label("Older Than:", classes="info-label")
                    yield Input(
                        "7d",
                        id="input-clean-older",
                        placeholder="Units: d, h, m, s, or bare days (e.g. 7d, 24h, 30m, 90s, 3)",
                    )
                    yield Label("Statuses (comma separated):", classes="info-label")
                    yield Input(
                        "completed,failed,crashed,ghost",
                        id="input-clean-status",
                        placeholder="completed,failed,interrupted,broken pipe,running,crashed,ghost",
                    )
                yield Static(
                    f"Valid statuses: {all_statuses} (running runs are never deleted). "
                    "Age units: d, h, m, s, or bare days.",
                    id="lbl-cleanup-hints",
                    classes="info-value",
                )
                with Horizontal(classes="button-row"):
                    yield Button("Preview Prune (Dry Run)", id="btn-prune-dry", variant="primary")
                    yield Button("Execute Prune", id="btn-prune-execute", variant="error")
                yield RichLog(id="cleanup-log-output", max_lines=500, classes="log-area")

    def display_run(self, run_info: Optional[RunInfo]) -> None:
        """Update display citation, rerun, and manifest fields."""
        self.run_info = run_info
        self.raw_manifest = None
        self.rerun_command = None

        rerun_lbl = self.query_one("#lbl-rerun-command", Static)
        advisory_lbl = self.query_one("#lbl-rerun-advisory", Static)
        citation_lbl = self.query_one("#lbl-methods-citation", Static)

        if not run_info:
            rerun_lbl.update("Select a run.")
            advisory_lbl.update("")
            citation_lbl.update("")
            return

        manifest = run_info.manifest if run_info.manifest is not None else run_info.load_manifest()

        # Fetch Rerun Command
        rerun_cmd = "-"
        if isinstance(manifest, dict):
            self.raw_manifest = manifest
            inv = manifest.get("invocation")
            raw_cmd = inv.get("rerun_command") if isinstance(inv, dict) else None
            rerun_cmd = raw_cmd if isinstance(raw_cmd, str) and raw_cmd else "-"
        elif run_info.lock_data:
            rerun_cmd = _build_rerun_command(run_info.lock_data)

        self.rerun_command = None if rerun_cmd == "-" else rerun_cmd
        rerun_lbl.update(Text(rerun_cmd))

        advisory = format_redacted_rerun_advisory(self.rerun_command)
        if advisory:
            advisory_lbl.update(Text(advisory))
        else:
            advisory_lbl.update("")

        # Generate Methods Citation
        methods_str = "(No citation available - manifest not complete)"
        if isinstance(manifest, dict):
            try:
                path = Path(run_info.run_dir) / "manifest.json"
                hydrated, _ = hydrate_manifest(str(path), manifest)
                methods_str = generate_report(hydrated, "markdown")
            except Exception as e:
                methods_str = f"Failed to compile citation: {e}"

        citation_lbl.update(methods_str)

    def _preview_prune_candidates(
        self, older_val: str, status_val: str
    ) -> List[RunInfo]:
        """Validate prune criteria and return the runs eligible for bulk deletion."""
        all_runs = scan_runs(self.output_dir, keep_manifest=False)
        candidates = filter_runs(
            all_runs,
            status_filter=status_val or None,
            older_than=older_val or None,
        )
        eligible: List[RunInfo] = []
        for r in candidates:
            if r.status == STATUS_RUNNING:
                continue
            lock_state, _ = _inspect_run_lock(r.run_dir)
            if lock_state == "remote":
                continue
            eligible.append(r)
        return eligible

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self.run_info and event.button.id in (
            "btn-copy-rerun",
            "btn-copy-md",
            "btn-copy-latex",
            "btn-archive-run",
            "btn-delete-selected",
        ):
            self.app.notify("Please select a run first.", severity="error")
            return

        if event.button.id == "btn-copy-rerun":
            cmd = self.rerun_command
            if cmd and cmd != "-":
                is_redacted = "[REDACTED]" in cmd
                if copy_to_clipboard(cmd):
                    if is_redacted:
                        self.app.notify(
                            "Rerun command copied to clipboard. Supply [REDACTED] arguments manually before running.",
                            severity="warning",
                        )
                    else:
                        self.app.notify("Rerun command copied to clipboard.", severity="information")
                else:
                    msg = "Failed to copy automatically. Please copy text manually."
                    if is_redacted:
                        msg += " Remember to supply [REDACTED] arguments before running."
                    self.app.notify(msg, severity="warning")

        elif event.button.id in ("btn-copy-md", "btn-copy-latex"):
            if self.run_info is None:
                return
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
            if self.run_info is None:
                return
            is_active = (self.run_info.status == STATUS_RUNNING)
            self.app.push_screen(
                ConfirmDeleteModal(self.run_info.run_id or self.run_info.run_dir.name, is_active),
                self.handle_deletion_result,
            )

        elif event.button.id == "btn-prune-dry":
            self.run_bulk_prune(dry_run=True)

        elif event.button.id == "btn-prune-execute":
            older_val = self.query_one("#input-clean-older", Input).value.strip()
            status_val = self.query_one("#input-clean-status", Input).value.strip()
            log = self.query_one("#cleanup-log-output", RichLog)
            try:
                candidates = self._preview_prune_candidates(older_val, status_val)
            except ValueError as e:
                log.clear()
                log.write(f"Pruning failed: {e}")
                self.app.notify(f"Invalid prune criteria: {e}", severity="error")
                return
            except Exception as e:
                log.clear()
                log.write(f"Pruning failed: {e}")
                self.app.notify(f"Prune failed: {e}", severity="error")
                return

            if not candidates:
                log.clear()
                log.write("No runs match the cleanup criteria.")
                self.app.notify("No runs match the cleanup criteria.", severity="information")
                return

            total_bytes = sum(_dir_size(r.run_dir) for r in candidates)
            self.app.push_screen(
                ConfirmBulkPruneModal(
                    matched_count=len(candidates),
                    total_size_bytes=total_bytes,
                    older_than=older_val,
                    status_filter=status_val,
                ),
                self.handle_bulk_prune_confirm,
            )

    def handle_bulk_prune_confirm(self, confirmed: Optional[bool]) -> None:
        """Execute bulk prune only after explicit modal confirmation."""
        if confirmed:
            self.run_bulk_prune(dry_run=False)

    def archive_selected_run(self) -> None:
        """Create zip archive in <output_dir>/archive/ and optionally delete original folder."""
        r = self.run_info
        if not r:
            return
        if not r.run_dir.exists():
            self.app.notify(f"Archive failed: run directory {r.run_dir.name} no longer exists.", severity="error")
            return

        base_dir = _resolve_output_dir(self.output_dir)
        archive_dir = base_dir / "archive"
        raw_stem = str(r.run_id or r.run_dir.name)
        safe_stem = re.sub(r"[^A-Za-z0-9._-]", "_", raw_stem).strip("._") or "run"
        zip_path = archive_dir / f"{safe_stem}.zip"

        try:
            archive_dir.mkdir(parents=True, exist_ok=True)
            resolved_archive = archive_dir.resolve()
            resolved_zip = zip_path.resolve()
            if resolved_zip.parent != resolved_archive:
                raise ValueError(f"Archive path escapes archive directory: {zip_path.name}")
            resolved_run_dir = r.run_dir.resolve()
            # Zip original folder (skipping symlinks and any path escaping run_dir)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_f:
                for file_p in r.run_dir.rglob("*"):
                    if file_p.is_symlink() or not file_p.is_file():
                        continue
                    try:
                        file_p.resolve().relative_to(resolved_run_dir)
                    except ValueError:
                        continue
                    zip_f.write(file_p, file_p.relative_to(r.run_dir))

            self.app.notify(f"Created archive: {zip_path.name}", severity="information")

            # Check if deleting raw
            delete_raw = self.query_one("#check-delete-raw", Checkbox).value
            if delete_raw:
                ok, reason = safe_delete_run_dir(r.run_dir, base_dir)
                if ok:
                    self.app.notify("Deleted original uncompressed directory.", severity="information")
                    self.display_run(None)
                    self.app.post_message(_refresh_sidebar_message(self.app))
                else:
                    detail = _format_delete_reason(r.run_dir, reason)
                    self.app.notify(f"Deletion failed: {detail}", severity="error")

        except Exception as e:
            self.app.notify(f"Archive failed: {e}", severity="error")

    def handle_deletion_result(self, confirmed: Optional[bool]) -> None:
        if not confirmed or not self.run_info:
            return

        run_dir = self.run_info.run_dir
        label = (self.run_info.run_id or run_dir.name)[:8]
        base_dir = _resolve_output_dir(self.output_dir)
        ok, reason = safe_delete_run_dir(run_dir, base_dir)
        if ok:
            self.app.notify(f"Successfully deleted run {label}", severity="information")
            self.display_run(None)
            self.app.post_message(_refresh_sidebar_message(self.app))
        else:
            detail = _format_delete_reason(run_dir, reason)
            self.app.notify(f"Deletion failed: {detail}", severity="error")

    def run_bulk_prune(self, dry_run: bool) -> None:
        """Execute or dry-run a bulk cleanup pruning candidates."""
        log = self.query_one("#cleanup-log-output", RichLog)
        log.clear()

        # Age parsing (d/h/m/s or bare days) is owned by clean_runs, which raises
        # ValueError on an invalid, negative, or non-finite age.
        older_val = self.query_one("#input-clean-older", Input).value.strip()

        # Parse statuses
        status_val = self.query_one("#input-clean-status", Input).value.strip()
        status_filter = [s.strip() for s in status_val.split(",")] if status_val else None

        log.write(f"Scanning runs for pruning (dry_run={dry_run})...")

        # Redirect both stdout and stderr so no raw terminal output bleeds into the live TUI.
        buffer = io.StringIO()

        try:
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                clean_runs(
                    output_dir=self.output_dir,
                    older_than=older_val or None,
                    status_filter=status_filter,
                    yes=True,
                    dry_run=dry_run,
                )

            output_str = buffer.getvalue()
            clean_str = _ANSI_ESCAPE_RE.sub("", output_str)
            log.write(clean_str)

            if not dry_run:
                self.app.notify("Pruning complete.", severity="information")
                self.app.post_message(_refresh_sidebar_message(self.app))
        except ValueError as e:
            log.write(f"Pruning failed: {e}")
            self.app.notify(f"Invalid prune criteria: {e}", severity="error")
        except Exception as e:
            log.write(f"Pruning failed: {e}")
            self.app.notify(f"Prune failed: {e}", severity="error")
