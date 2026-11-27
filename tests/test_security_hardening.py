"""Behavioral regression tests for redaction, meta_ref sandbox, TUI safety, and benchmarks."""

import csv
import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from pubrun.capture.redaction import format_safe_error_detail, redact_argv
from pubrun.report.utils import _is_meta_ref_allowed
from pubrun.__main__ import _format_rerun_cmd_for_platform


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_empty_username_uri_credentials_are_redacted() -> None:
    """Empty-username URIs like https://:pat@host and redis://:pass@host must be redacted."""
    argv = [
        "git",
        "clone",
        "https://:ghp_SuperSecretToken123@github.com/org/repo.git",
        "redis://:redispass99@cache.internal:6379/0",
    ]
    out = redact_argv(argv)
    assert "ghp_SuperSecretToken123" not in " ".join(out)
    assert "redispass99" not in " ".join(out)
    assert "https://:[REDACTED]@github.com/org/repo.git" in out
    assert "redis://:[REDACTED]@cache.internal:6379/0" in out

    err = format_safe_error_detail(RuntimeError("connect redis://:topsecret@host:6379"))
    assert "topsecret" not in err
    assert ":[REDACTED]@host:6379" in err


def test_redact_argv_handles_non_flag_kv_and_unsplit_command_strings() -> None:
    """Non-flag KEY=VALUE (env/Hydra) and unsplit shell command strings must be redacted."""
    argv = [
        "env",
        "DB_PASSWORD=hunter2",
        "api_key=my_hydra_secret",
        "NORMAL_VAR=hello",
        "API_TOKEN=tok123 --password=pw456 python train.py",
    ]
    out = redact_argv(argv)
    joined = " ".join(out)
    assert "hunter2" not in joined
    assert "my_hydra_secret" not in joined
    assert "tok123" not in joined
    assert "pw456" not in joined
    assert "DB_PASSWORD=[REDACTED]" in out
    assert "api_key=[REDACTED]" in out
    assert "NORMAL_VAR=hello" in out


def test_meta_ref_allowed_dirs_fails_closed_on_string_and_empty_entries(
    tmp_path: Path, monkeypatch
) -> None:
    """A string meta_ref_allowed_dirs typo must not iterate '/' and disable the sandbox."""
    manifest_dir = tmp_path / "run_a"
    manifest_dir.mkdir()
    outside = tmp_path / "secret" / "meta.json"
    outside.parent.mkdir()
    outside.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        "pubrun.config.resolve_config",
        lambda: {"report": {"allow_external_meta_ref": False, "meta_ref_allowed_dirs": "/scratch/meta"}},
    )
    assert _is_meta_ref_allowed(manifest_dir, outside) is False

    monkeypatch.setattr(
        "pubrun.config.resolve_config",
        lambda: {"report": {"allow_external_meta_ref": False, "meta_ref_allowed_dirs": ["", "   "]}},
    )
    assert _is_meta_ref_allowed(manifest_dir, outside) is False


def test_windows_rerun_cmd_formatting_uses_proper_quoting(monkeypatch) -> None:
    """Windows rerun command formatting must handle apostrophes, spaces, and backslashes safely."""
    monkeypatch.setattr(sys, "platform", "win32")
    cmd = "cd '/tmp/it'\\''s a dir' && python train.py --msg 'hello world'"
    formatted = _format_rerun_cmd_for_platform(cmd)
    assert "\n" in formatted
    cd_line, py_line = formatted.split("\n", 1)
    assert cd_line.startswith("cd ")
    assert "it's a dir" in cd_line
    assert '"hello world"' in py_line

    # Unquoted Windows backslash paths must keep all backslashes intact
    win_cmd = r"cd C:\work\project\runs && python C:\work\project\train.py --epochs 3"
    win_fmt = _format_rerun_cmd_for_platform(win_cmd)
    assert win_fmt == r"cd C:\work\project\runs" + "\n" + r"python C:\work\project\train.py --epochs 3"


def test_share_safety_catches_sys_path_filesystem_and_forward_slash_windows() -> None:
    """share_safety catches unredacted sys_path, filesystem path/mount_point, and C:/Users/."""
    repo_root = Path(__file__).resolve().parent.parent
    ss = _load_module("share_safety_test_mod", repo_root / "benchmarks" / "share_safety.py")

    bad_sys = {"machine": {"python": {"sys_path": ["/opt/venv/lib"]}}}
    ok, reasons = ss.check_share_safe(bad_sys)
    assert not ok and any("sys_path" in r for r in reasons)

    bad_fs = {"machine": {"filesystem": {"cwd": {"path": "/scratch/lab", "mount_point": "/scratch"}}}}
    ok, reasons = ss.check_share_safe(bad_fs)
    assert not ok and any("filesystem.cwd.path" in r for r in reasons)

    bad_win = {"notes": "ran in C:/Users/carol/project"}
    ok, reasons = ss.check_share_safe(bad_win)
    assert not ok

    good = {
        "machine": {
            "python": {"sys_path": ["<redacted>", "<redacted>"]},
            "filesystem": {"cwd": {"path": "<redacted>", "mount_point": "<redacted>"}},
        }
    }
    ok, reasons = ss.check_share_safe(good)
    assert ok and reasons == []


def test_aggregate_sanitizes_markdown_and_csv_formula_injection(tmp_path: Path) -> None:
    """benchmarks/aggregate.py neutralizes CSV formula prefixes and escapes Markdown cells."""
    repo_root = Path(__file__).resolve().parent.parent
    agg = _load_module("aggregate_test_mod", repo_root / "benchmarks" / "aggregate.py")

    rows = [
        {
            "machine": "=cmd|' /C calc'!A0\n<script>alert(1)</script>[x](http://evil)",
            "pubrun_version": "+1.4.0",
            "group": "startup",
            "scenario": "@evil_scenario|pipe`tick`",
            "mode": "minimal",
            "workload": "noop",
            "median_ms": 12.5,
            "p95_ms": 15.0,
            "stdev_ms": 1.1,
            "n": 10,
            "vs_baseline": "",
            "overhead_ms": -0.5,
            "overhead_pct": -1.2,
        }
    ]
    csv_path = tmp_path / "summary.csv"
    md_path = tmp_path / "summary.md"
    agg.write_csv(rows, csv_path)
    agg.write_markdown(rows, md_path)

    with open(csv_path, newline="", encoding="utf-8") as f:
        parsed = list(csv.DictReader(f))
    assert parsed[0]["machine"].startswith("'=")
    assert parsed[0]["pubrun_version"].startswith("'+")
    assert parsed[0]["scenario"].startswith("'@")
    # Numeric negative values remain numeric (not quoted)
    assert parsed[0]["overhead_ms"] == "-0.5"

    md_text = md_path.read_text(encoding="utf-8")
    assert "<script>" not in md_text
    assert "&lt;script&gt;" in md_text
    assert "\\|" in md_text
    assert "\\`" in md_text
    # No injected newline breaking the table row
    table_rows = [ln for ln in md_text.splitlines() if ln.startswith("| ") and "Machine" not in ln]
    assert len(table_rows) == 1
