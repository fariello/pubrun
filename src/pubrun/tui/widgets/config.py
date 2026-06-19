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
            yield Label("Profile Mode (Controls telemetry depth):", classes="info-label")
            yield Select([("Default", "default"), ("Minimal", "minimal"), ("Deep", "deep")], id="cfg-profile")
            
            yield Label("Base Output Directory (e.g. ./runs/):", classes="info-label")
            yield Input(id="cfg-output-dir", placeholder="Default: ./runs/")
            
            yield Checkbox("Enable Auto Start on Import", value=True, id="cfg-auto-start")

            yield Label("CONSOLE INTERCEPTION", classes="panel-card-title")
            yield Label("Stdout / Stderr Interception Mode:", classes="info-label")
            yield Select([("Off", "off"), ("Basic (Tee to log)", "basic"), ("Standard", "standard"), ("Deep", "deep")], id="cfg-console-mode")

            yield Label("EVENT STREAM SETTINGS", classes="panel-card-title")
            yield Checkbox("Enable Events Logging (events.jsonl)", value=True, id="cfg-events-enabled")
            
            yield Label("REDACTION & SECURITY", classes="panel-card-title")
            yield Label("Sensitive Keys Regex Pattern:", classes="info-label")
            yield Input(id="cfg-sensitive-regex")
            yield Label("Masking Representation:", classes="info-label")
            yield Select([("Redacted [REDACTED]", "redacted"), ("Hashed (SHA-256)", "hashed")], id="cfg-redact-repr")
            yield Checkbox("Redact Environment Variables", value=True, id="cfg-redact-env")
            yield Checkbox("Redact Command Line Arguments", value=True, id="cfg-redact-argv")

        with Horizontal(id="config-buttons-container"):
            yield Button("Save Configuration", id="btn-save-config", variant="success")
            yield Button("Reset to Resolved", id="btn-reset-config", variant="primary")

    def on_mount(self) -> None:
        self.load_settings()

    def load_settings(self) -> None:
        """Load configuration using resolve_config and populate form elements."""
        self.config_data = resolve_config()

        # Core
        core = self.config_data.get("core", {})
        self.query_one("#cfg-profile", Select).value = core.get("profile", "default")
        self.query_one("#cfg-output-dir", Input).value = core.get("output_dir") or ""
        self.query_one("#cfg-auto-start", Checkbox).value = core.get("auto_start", True)

        # Console
        console = self.config_data.get("console", {})
        self.query_one("#cfg-console-mode", Select).value = console.get("capture_mode", "standard")

        # Events
        events = self.config_data.get("events", {})
        self.query_one("#cfg-events-enabled", Checkbox).value = events.get("enabled", True)

        # Redaction
        redact = self.config_data.get("redaction", {})
        self.query_one("#cfg-sensitive-regex", Input).value = redact.get("sensitive_keys_regex") or ""
        self.query_one("#cfg-redact-repr", Select).value = redact.get("representation", "redacted")
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
        local_conf.setdefault("core", {})["profile"] = self.query_one("#cfg-profile", Select).value
        local_conf.setdefault("core", {})["output_dir"] = self.query_one("#cfg-output-dir", Input).value
        local_conf.setdefault("core", {})["auto_start"] = self.query_one("#cfg-auto-start", Checkbox).value

        local_conf.setdefault("console", {})["capture_mode"] = self.query_one("#cfg-console-mode", Select).value

        local_conf.setdefault("events", {})["enabled"] = self.query_one("#cfg-events-enabled", Checkbox).value

        local_conf.setdefault("redaction", {})["sensitive_keys_regex"] = self.query_one("#cfg-sensitive-regex", Input).value
        local_conf.setdefault("redaction", {})["representation"] = self.query_one("#cfg-redact-repr", Select).value
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
