"""
Configuration management widget for viewing and editing .pubrun.toml settings.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import Label, Input, Checkbox, Button, Select

from pubrun.config import resolve_config, load_local_config, get_global_config_dir


def _is_select_empty(val: Any) -> bool:
    """Return True when a ``Select`` value means "nothing selected".

    ``Select.NULL`` is truthy, so a plain truthiness check misses it. ``BLANK`` is
    read from ``Select.__dict__`` only: on Textual 8.x ``Select.BLANK`` resolves to
    the inherited ``Widget.BLANK`` (``False``), which must not classify ``False`` or
    ``0`` as empty.
    """
    if val is None or val is Select.NULL:
        return True
    try:
        if val == Select.NULL:
            return True
    except Exception:
        pass
    blank = Select.__dict__.get("BLANK")
    return blank is not None and val == blank


_SELECT_OPTIONS: Dict[str, List[Any]] = {
    "cfg-profile": [("Default", "default"), ("Minimal", "minimal"), ("Deep", "deep")],
    "cfg-console-mode": [("Off", "off"), ("Basic (Tee to log)", "basic"), ("Standard", "standard"), ("Deep", "deep")],
    "cfg-redact-repr": [("Redacted [REDACTED]", "redacted"), ("Hashed (SHA-256)", "hashed")],
}

def dict_to_toml(d: dict, prefix: str = "") -> str:
    """Zero-dependency recursive TOML serializer for simple nested dict configurations."""
    lines = []

    # 1. Write flat key-value pairs first
    for k, v in sorted(d.items()):
        if not isinstance(v, dict):
            if isinstance(v, bool):
                val_str = "true" if v else "false"
            elif isinstance(v, (int, float)):
                val_str = str(v)
            elif isinstance(v, str):
                # Double escape backslashes and quotes in strings
                escaped = v.replace("\\", "\\\\").replace('"', '\\"')
                val_str = f'"{escaped}"'
            elif isinstance(v, list):
                val_str = json.dumps(v)
            else:
                val_str = f'"{str(v)}"'
            lines.append(f"{k} = {val_str}")

    # 2. Process sections recursively
    for k, v in sorted(d.items()):
        if isinstance(v, dict):
            section_name = f"{prefix}.{k}" if prefix else k
            # Only append section header if it contains keys or non-empty sub-dicts
            if v:
                lines.append(f"\n[{section_name}]")
                lines.append(dict_to_toml(v, section_name))

    return "\n".join(lines).strip()


class ConfigPanel(Vertical):
    """Component to view, edit, and save pubrun configuration settings."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config_data: Dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="panel-card"):
            yield Label("CORE SETTINGS", classes="panel-card-title")
            yield Label("Profile Mode (deprecated; no effect — use capture.* keys):", classes="info-label")
            yield Select(_SELECT_OPTIONS["cfg-profile"], id="cfg-profile")

            yield Label("Base Output Directory (e.g. ./runs/):", classes="info-label")
            yield Input(id="cfg-output-dir", placeholder="Default: ./runs/")

            yield Checkbox("Enable Auto Start on Import", value=True, id="cfg-auto-start")

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
        select.value = Select.NULL
        if value is not None:
            self.app.notify(
                f"Unknown {setting} value {value!r}; left unselected (expected one of: {', '.join(allowed)}).",
                severity="warning",
            )

    def load_settings(self) -> None:
        """Load configuration using resolve_config and populate form elements."""
        self.config_data = resolve_config()

        # Core
        core = self.config_data.get("core", {})
        self._set_select("cfg-profile", "core.profile", core.get("profile", "default"))
        self.query_one("#cfg-output-dir", Input).value = core.get("output_dir") or ""
        self.query_one("#cfg-auto-start", Checkbox).value = core.get("auto_start", True)

        # Console
        console = self.config_data.get("console", {})
        self._set_select("cfg-console-mode", "console.capture_mode", console.get("capture_mode", "off"))

        # Events
        events = self.config_data.get("events", {})
        self.query_one("#cfg-events-enabled", Checkbox).value = events.get("enabled", True)

        # Redaction
        redact = self.config_data.get("redaction", {})
        self.query_one("#cfg-sensitive-regex", Input).value = redact.get("sensitive_keys_regex") or ""
        self._set_select("cfg-redact-repr", "redaction.representation", redact.get("representation", "redacted"))
        self.query_one("#cfg-redact-env", Checkbox).value = redact.get("env_enabled", True)
        self.query_one("#cfg-redact-argv", Checkbox).value = redact.get("argv_enabled", True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-config":
            self.save_settings()
        elif event.button.id == "btn-reset-config":
            self.load_settings()
            self.app.notify("Settings reloaded to current resolved values.", severity="information")

    def save_settings(self) -> None:
        """Collect form values, merge with existing local configuration, and save to .pubrun.toml."""
        # 1. Fetch current local configurations to avoid overwriting unrelated settings
        local_conf = load_local_config() or {}

        # 2. Update section values
        profile_val = self.query_one("#cfg-profile", Select).value
        if not _is_select_empty(profile_val):
            local_conf.setdefault("core", {})["profile"] = profile_val

        local_conf.setdefault("core", {})["output_dir"] = self.query_one("#cfg-output-dir", Input).value
        local_conf.setdefault("core", {})["auto_start"] = self.query_one("#cfg-auto-start", Checkbox).value

        console_mode = self.query_one("#cfg-console-mode", Select).value
        if not _is_select_empty(console_mode):
            local_conf.setdefault("console", {})["capture_mode"] = console_mode

        local_conf.setdefault("events", {})["enabled"] = self.query_one("#cfg-events-enabled", Checkbox).value

        local_conf.setdefault("redaction", {})["sensitive_keys_regex"] = self.query_one("#cfg-sensitive-regex", Input).value

        redact_repr = self.query_one("#cfg-redact-repr", Select).value
        if not _is_select_empty(redact_repr):
            local_conf.setdefault("redaction", {})["representation"] = redact_repr

        local_conf.setdefault("redaction", {})["env_enabled"] = self.query_one("#cfg-redact-env", Checkbox).value
        local_conf.setdefault("redaction", {})["argv_enabled"] = self.query_one("#cfg-redact-argv", Checkbox).value

        # 3. Serialize to TOML
        toml_str = dict_to_toml(local_conf)

        # 4. Save to project root .pubrun.toml
        target_path = Path.cwd() / ".pubrun.toml"
        try:
            target_path.write_text(toml_str, encoding="utf-8")
            self.app.notify(f"Configuration saved to: {target_path.name}", severity="information")
            # Refresh local resolved state
            self.load_settings()
        except Exception as e:
            self.app.notify(f"Failed to write configuration: {e}", severity="error")
