"""
Configuration management widget for viewing and editing .pubrun.toml settings.
"""

from __future__ import annotations
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef]

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Checkbox, Input, Label, Select, Static
from rich.text import Text

from pubrun.config import load_local_config, resolve_config
from pubrun.tui.widgets.actions import _refresh_sidebar_message


_SELECT_EMPTY_VALUE: Any = (
    Select.__dict__["NULL"]
    if "NULL" in Select.__dict__
    else getattr(Select, "NULL", Select.__dict__.get("BLANK"))
)

_BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _is_select_empty(val: Any) -> bool:
    """Return True when a ``Select`` value means "nothing selected".

    ``Select.NULL`` (Textual 8.x) and ``Select.BLANK`` (Textual 0.x) are truthy,
    so a plain truthiness check misses them. ``BLANK`` is read from
    ``Select.__dict__`` only: on Textual 8.x ``Select.BLANK`` resolves to the
    inherited ``Widget.BLANK`` (``False``), which must not classify ``False`` or
    ``0`` as empty.
    """
    if val is None:
        return True
    if _SELECT_EMPTY_VALUE is not None:
        if val is _SELECT_EMPTY_VALUE:
            return True
        try:
            if val == _SELECT_EMPTY_VALUE:
                return True
        except Exception:
            pass
    blank = Select.__dict__.get("BLANK")
    if blank is not None:
        try:
            if val == blank:
                return True
        except Exception:
            pass
    return False


_SELECT_OPTIONS: Dict[str, List[Any]] = {
    "cfg-imports-mode": [
        ("Auto (auto-start + hooks)", "auto"),
        ("Full (auto-start + force console capture)", "full"),
        ("No Auto-Start (manual pubrun.start())", "noauto"),
        ("No Patch (auto-start, no subprocess/console hooks)", "nopatch"),
        ("No Console (auto-start, no console wrapping)", "noconsole"),
        ("Minimal (API only, no auto-start or hooks)", "minimal"),
    ],
    "cfg-console-mode": [
        ("Off", "off"),
        ("Basic (Tee to log)", "basic"),
        ("Standard", "standard"),
        ("Deep", "deep"),
    ],
    "cfg-redact-repr": [
        ("Redacted [REDACTED]", "redacted"),
        ("Hashed (SHA-256)", "hashed"),
    ],
}


def _toml_scalar_or_list(value: Any) -> str:
    """Return a string or list as TOML, escaping quotes, backslashes, and control characters."""
    return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007f")


def _toml_key(key: Any) -> str:
    """Format a TOML key, quoting any key that is not a valid bare TOML key."""
    key_str = str(key)
    if _BARE_KEY_RE.fullmatch(key_str):
        return key_str
    return _toml_scalar_or_list(key_str)


def _toml_value(value: Any) -> Optional[str]:
    """Serialize a non-section value into valid TOML syntax, or None to omit."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return _toml_scalar_or_list(value)
    if isinstance(value, (list, tuple)):
        items: List[str] = []
        for elem in value:
            serialized = _toml_value(elem)
            if serialized is not None:
                items.append(serialized)
        return "[" + ", ".join(items) + "]"
    if isinstance(value, dict):
        pairs: List[str] = []
        for k, v in sorted(value.items(), key=lambda kv: str(kv[0])):
            serialized = _toml_value(v)
            if serialized is not None:
                pairs.append(f"{_toml_key(k)} = {serialized}")
        return "{" + ", ".join(pairs) + "}"
    return _toml_scalar_or_list(str(value))


def dict_to_toml(d: dict, prefix: str = "") -> str:
    """Zero-dependency recursive TOML serializer for nested dict configurations."""
    lines: List[str] = []

    # 1. Write flat key-value pairs first (omitting None values, which TOML lacks)
    for k, v in sorted(d.items(), key=lambda kv: str(kv[0])):
        if isinstance(v, dict) or v is None:
            continue
        val_str = _toml_value(v)
        if val_str is not None:
            lines.append(f"{_toml_key(k)} = {val_str}")

    # 2. Process non-empty sections recursively
    for k, v in sorted(d.items(), key=lambda kv: str(kv[0])):
        if isinstance(v, dict) and v:
            key_part = _toml_key(k)
            section_name = f"{prefix}.{key_part}" if prefix else key_part
            sub_body = dict_to_toml(v, section_name)
            if not sub_body:
                continue
            has_direct_keys = any(
                not isinstance(sv, dict) and sv is not None for sv in v.values()
            )
            if has_direct_keys:
                lines.append(f"\n[{section_name}]")
            else:
                lines.append("")
            lines.append(sub_body)

    return "\n".join(lines).strip()


def _atomic_write_text(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically via temp file + fsync + os.replace."""
    tmp_path = path.parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    replaced = False
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        for attempt in range(10 if os.name == "nt" else 1):
            try:
                os.replace(str(tmp_path), str(path))
                replaced = True
                break
            except PermissionError:
                if os.name != "nt" or attempt == 9:
                    raise
                time.sleep(0.005 * (attempt + 1))
    finally:
        if not replaced:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass


class ConfigPanel(Vertical):
    """Component to view, edit, and save project .pubrun.toml settings."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.config_data: Dict[str, Any] = {}

    def _target_path(self) -> Path:
        return Path.cwd() / ".pubrun.toml"

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="panel-card"):
            yield Static(
                Text(f"Target file: {self._target_path()}"),
                id="cfg-target-path",
                classes="panel-card-title",
            )

            yield Label("CORE & IMPORT SETTINGS", classes="panel-card-title")

            yield Label("Base Output Directory (e.g. ./runs/):", classes="info-label")
            yield Input(id="cfg-output-dir", placeholder="Default: ./runs/")

            yield Label("Import Mode ([imports].mode):", classes="info-label")
            yield Select(_SELECT_OPTIONS["cfg-imports-mode"], id="cfg-imports-mode")
            yield Static(
                "Note: [imports].mode takes precedence over [core].auto_start when both are set.",
                id="cfg-imports-mode-hint",
                classes="info-value",
            )

            yield Checkbox("Enable Auto Start on Import ([core].auto_start)", value=True, id="cfg-auto-start")

            yield Label("CONSOLE INTERCEPTION", classes="panel-card-title")
            yield Label("Stdout / Stderr Interception Mode:", classes="info-label")
            yield Select(_SELECT_OPTIONS["cfg-console-mode"], id="cfg-console-mode")

            yield Label("EVENT STREAM SETTINGS", classes="panel-card-title")
            yield Checkbox("Enable Events Logging (events.jsonl)", value=True, id="cfg-events-enabled")

            yield Label("REDACTION & SECURITY", classes="panel-card-title")
            yield Label("Sensitive Keys Regex Pattern:", classes="info-label")
            yield Input(id="cfg-sensitive-regex")
            yield Label("Masking Representation:", classes="info-label")
            yield Select(_SELECT_OPTIONS["cfg-redact-repr"], id="cfg-redact-repr")
            yield Checkbox("Redact Environment Variables", value=True, id="cfg-redact-env")
            yield Checkbox("Redact Command Line Arguments", value=True, id="cfg-redact-argv")

        with Horizontal(id="config-buttons-container"):
            yield Button("Save Configuration", id="btn-save-config", variant="success")
            yield Button("Reset to Resolved", id="btn-reset-config", variant="primary")

    def on_mount(self) -> None:
        self.load_settings()

    def _set_select(self, widget_id: str, setting: str, value: Any) -> None:
        """Assign a loaded value to a Select, blanking it (with a warning) when unknown."""
        select = self.query_one(f"#{widget_id}", Select)
        allowed = [opt[1] for opt in _SELECT_OPTIONS[widget_id]]
        if value in allowed:
            select.value = value
            return
        select.value = _SELECT_EMPTY_VALUE
        if value is not None:
            self.app.notify(
                f"Unknown {setting} value {value!r}; left unselected (expected one of: {', '.join(allowed)}).",
                severity="warning",
            )

    def load_settings(self) -> None:
        """Load configuration using resolve_config and populate form elements."""
        self.query_one("#cfg-target-path", Static).update(
            Text(f"Target file: {self._target_path()}")
        )
        self.config_data = resolve_config()

        # Core
        core = self.config_data.get("core", {})
        if not isinstance(core, dict):
            core = {}
        profile_val = core.get("profile")
        if profile_val is not None and profile_val not in ("default", ""):
            self.app.notify(
                f"Deprecated core.profile={profile_val!r} has no effect; configure capture.* keys instead.",
                severity="warning",
            )
        raw_local = load_local_config()
        local_core = raw_local.get("core") if isinstance(raw_local, dict) else None
        local_output_dir = (
            local_core.get("output_dir") if isinstance(local_core, dict) else None
        )
        resolved_output_dir = core.get("output_dir")
        if isinstance(local_output_dir, str):
            display_output_dir = local_output_dir
        elif isinstance(resolved_output_dir, str):
            display_output_dir = resolved_output_dir
        else:
            display_output_dir = ""
        self.query_one("#cfg-output-dir", Input).value = display_output_dir
        self.query_one("#cfg-auto-start", Checkbox).value = bool(core.get("auto_start", True))

        # Imports
        imports_sec = self.config_data.get("imports", {})
        if not isinstance(imports_sec, dict):
            imports_sec = {}
        self._set_select("cfg-imports-mode", "imports.mode", imports_sec.get("mode", "auto"))

        # Console
        console = self.config_data.get("console", {})
        if not isinstance(console, dict):
            console = {}
        self._set_select("cfg-console-mode", "console.capture_mode", console.get("capture_mode", "off"))

        # Events
        events = self.config_data.get("events", {})
        if not isinstance(events, dict):
            events = {}
        self.query_one("#cfg-events-enabled", Checkbox).value = bool(events.get("enabled", True))

        # Redaction
        redact = self.config_data.get("redaction", {})
        if not isinstance(redact, dict):
            redact = {}
        self.query_one("#cfg-sensitive-regex", Input).value = redact.get("sensitive_keys_regex") or ""
        self._set_select("cfg-redact-repr", "redaction.representation", redact.get("representation", "redacted"))
        self.query_one("#cfg-redact-env", Checkbox).value = bool(redact.get("env_enabled", True))
        self.query_one("#cfg-redact-argv", Checkbox).value = bool(redact.get("argv_enabled", True))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-config":
            self.save_settings()
        elif event.button.id == "btn-reset-config":
            self.load_settings()
            self.app.notify("Settings reloaded to current resolved values.", severity="information")

    def save_settings(self) -> None:
        """Validate form values, merge with local configuration, and atomically save .pubrun.toml."""
        # 0. Validate sensitive_keys_regex before touching disk (preserve user text on failure)
        regex_val = self.query_one("#cfg-sensitive-regex", Input).value
        if regex_val:
            try:
                re.compile(regex_val)
            except re.error as e:
                self.app.notify(
                    f"Invalid sensitive_keys_regex pattern: {e}",
                    severity="error",
                )
                return

        prev_core = self.config_data.get("core", {})
        prev_raw_output_dir = (
            prev_core.get("output_dir") if isinstance(prev_core, dict) else None
        )
        prev_resolved_output_dir = (
            prev_raw_output_dir if isinstance(prev_raw_output_dir, str) else ""
        )

        # 1. Fetch current local configurations to avoid overwriting unrelated settings
        raw_local = load_local_config()
        local_conf: Dict[str, Any] = dict(raw_local) if isinstance(raw_local, dict) else {}

        for sec in ("core", "imports", "console", "events", "redaction"):
            if not isinstance(local_conf.get(sec), dict):
                local_conf[sec] = {}

        # 2. Update section values (do not write deprecated inert core.profile)
        new_output_dir = self.query_one("#cfg-output-dir", Input).value
        local_conf["core"]["output_dir"] = new_output_dir
        local_conf["core"]["auto_start"] = self.query_one("#cfg-auto-start", Checkbox).value

        imports_mode = self.query_one("#cfg-imports-mode", Select).value
        if not _is_select_empty(imports_mode):
            local_conf["imports"]["mode"] = imports_mode

        console_mode = self.query_one("#cfg-console-mode", Select).value
        if not _is_select_empty(console_mode):
            local_conf["console"]["capture_mode"] = console_mode

        local_conf["events"]["enabled"] = self.query_one("#cfg-events-enabled", Checkbox).value

        local_conf["redaction"]["sensitive_keys_regex"] = regex_val

        redact_repr = self.query_one("#cfg-redact-repr", Select).value
        if not _is_select_empty(redact_repr):
            local_conf["redaction"]["representation"] = redact_repr

        local_conf["redaction"]["env_enabled"] = self.query_one("#cfg-redact-env", Checkbox).value
        local_conf["redaction"]["argv_enabled"] = self.query_one("#cfg-redact-argv", Checkbox).value

        # 3. Serialize and validate TOML before writing
        toml_str = dict_to_toml(local_conf)
        try:
            tomllib.loads(toml_str)
        except Exception as e:
            self.app.notify(f"Failed to serialize valid TOML: {e}", severity="error")
            return

        # 4. Save atomically to project root .pubrun.toml
        target_path = self._target_path()
        try:
            _atomic_write_text(target_path, toml_str + ("\n" if toml_str else ""))
            self.app.notify(f"Configuration saved to: {target_path.name}", severity="information")
            self.load_settings()

            new_core = self.config_data.get("core", {})
            new_raw_output_dir = (
                new_core.get("output_dir") if isinstance(new_core, dict) else None
            )
            new_resolved_output_dir = (
                new_raw_output_dir if isinstance(new_raw_output_dir, str) else ""
            )

            if new_resolved_output_dir != prev_resolved_output_dir and not getattr(
                self.app, "_explicit_output_dir", False
            ):
                updater = getattr(self.app, "update_output_dir", None)
                if callable(updater):
                    updater(None)
                self.app.post_message(_refresh_sidebar_message(self.app))
        except Exception as e:
            self.app.notify(f"Failed to write configuration: {e}", severity="error")
