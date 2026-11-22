"""Tests for pubrun TUI CLI command and dynamic dependency imports."""
import sys
import pytest
from unittest import mock
import argparse

def test_tui_cli_parser_and_run():
    """Verify that pubrun ui parses correctly and launches when dependencies exist."""
    from pubrun.__main__ import main

    for sub in ("ui", "tui", "gui"):
        with mock.patch("sys.argv", ["pubrun", sub, "--dir", "/tmp/runs"]):
            with mock.patch("pubrun.tui.app.PubrunTUIApp") as mock_app:
                # Inject mocked module
                mock_module = mock.Mock()
                mock_module.PubrunTUIApp = mock_app
                sys.modules["pubrun.tui.app"] = mock_module

                try:
                    main()
                except SystemExit as e:
                    # main() might exit 0 after executing command
                    assert e.code in (0, None)

                mock_app.assert_called_once_with(output_dir="/tmp/runs")
                mock_app.return_value.run.assert_called_once()


def test_tui_missing_dependencies_prints_notice(capsys):
    """Verify that when TUI dependencies are missing, a friendly explanation is printed and exits 1."""
    from pubrun.__main__ import main

    # Remove mock module if populated
    if "pubrun.tui.app" in sys.modules:
        del sys.modules["pubrun.tui.app"]

    with mock.patch("sys.argv", ["pubrun", "ui"]):
        # Mock import to raise ImportError
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if "pubrun.tui" in name or "textual" in name:
                raise ImportError("No module named 'textual'")
            return original_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

            captured = capsys.readouterr()
            assert "pubrun is by default zero-dependency based" in captured.err
            assert "Run `pip install textual rich`" in captured.err


def test_tui_toml_serialization():
    """Verify that the dict_to_toml helper serializes configurations correctly."""
    from pubrun.tui.widgets.config import dict_to_toml

    test_dict = {
        "core": {
            "profile": "default",
            "auto_start": True,
            "sample_int": 15
        },
        "capture": {
            "environment": {
                "mode": "filtered"
            }
        }
    }

    toml_str = dict_to_toml(test_dict)

    # Assert section headers are generated correctly
    assert "[core]" in toml_str
    assert "[capture.environment]" in toml_str

    # Assert values are serialized correctly
    assert 'profile = "default"' in toml_str
    assert 'auto_start = true' in toml_str
    assert 'sample_int = 15' in toml_str
    assert 'mode = "filtered"' in toml_str


# ------------------------------------------------- IPD-F: TUI resource graphs (2026-07-07)

import json as _json
from pathlib import Path as _Path


class TestResourceDigest:
    """The pure text digest reused by the TUI resource view (no textual dependency)."""

    def test_summary_and_sparklines(self):
        from pubrun.report.diagnostics import format_resource_digest
        MB = 1024 * 1024
        series = {"timestamps": [1, 2, 3], "rss": [10 * MB, 30 * MB, 20 * MB],
                  "cpu": [5.0, 90.0, 40.0], "tree_rss": [], "tree_cpu": []}
        out = format_resource_digest(series)
        assert "RSS (main)" in out and "peak 30.0 MB" in out and "avg 20.0 MB" in out
        assert "CPU (main)" in out and "peak 90.0%" in out
        # a sparkline row (unicode block chars) is present
        assert any(ch in out for ch in "▁▂▃▄▅▆▇█")

    def test_empty_series_message(self):
        from pubrun.report.diagnostics import format_resource_digest
        assert "No resource samples" in format_resource_digest({"timestamps": []})

    def test_tree_metrics_shown_when_present(self):
        from pubrun.report.diagnostics import format_resource_digest
        series = {"timestamps": [1, 2], "rss": [1, 2], "cpu": [1.0, 2.0],
                  "tree_rss": [10, 20], "tree_cpu": [100.0, 250.0]}
        out = format_resource_digest(series)
        assert "RSS (tree)" in out and "CPU (tree)" in out and "peak 250.0%" in out


def _make_run_with_samples(tmp_path):
    """Create a minimal run dir with an events.jsonl of resource samples."""
    run = tmp_path / "runs" / "pubrun-abcd1234"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(_json.dumps({
        "run": {"run_id": "abcd1234"}, "status": {"outcome": "completed"},
        "timing": {"started_at_utc": 1000.0}, "resources": {"scope": "process"},
    }))
    with open(run / "events.jsonl", "w") as f:
        for i in range(5):
            f.write(_json.dumps({"type": "resource_sample", "timestamp_utc": 1000.0 + i,
                                 "name": "", "payload": {"rss_bytes": (10 + i) * 1024 * 1024,
                                                          "cpu_percent": 10.0 * i}}) + "\n")
    return run


class TestTuiResourceView:
    """Drive the TUI with textual's Pilot to confirm the resource view populates."""

    def test_resource_view_populates_and_degrades(self, tmp_path):
        pytest.importorskip("textual")
        import asyncio
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.resources import RunResourcesView
        from pubrun.status import RunInfo

        run = _make_run_with_samples(tmp_path)

        async def _drive():
            app = PubrunTUIApp(output_dir=str(tmp_path / "runs"))
            async with app.run_test() as pilot:
                view = app.query_one("#resources-view", RunResourcesView)
                # A run WITH samples -> digest with the RSS/CPU summary.
                view.display_run(RunInfo(run))
                await pilot.pause()
                body = app.query_one("#resources-body")
                text = str(body.render())
                assert "RSS (main)" in text and "CPU (main)" in text
                # A run WITHOUT events.jsonl -> graceful message, no crash.
                bare = tmp_path / "runs" / "pubrun-bare0000"
                bare.mkdir()
                (bare / "manifest.json").write_text(_json.dumps(
                    {"run": {"run_id": "bare0000"}, "status": {"outcome": "completed"}}))
                view.display_run(RunInfo(bare))
                await pilot.pause()
                assert "No resource samples" in str(app.query_one("#resources-body").render())
                # The Resources action jumps to the Resources tab. (Invoked directly: a plain
                # 'r' footer binding is intentionally NOT priority, so it yields to a focused
                # text input rather than stealing the key — verify the action's effect.)
                app.action_show_resources()
                await pilot.pause()
                from textual.widgets import TabbedContent
                assert app.query_one("#workspace-tabs", TabbedContent).active == "tab-resources"

        asyncio.run(_drive())


class TestReproducibilityTuiHelpers:
    """Pure-Python formatter and advisory unit tests (unconditional, zero textual dependency)."""

    def test_format_redacted_rerun_advisory(self):
        from pubrun.report.diagnostics import format_redacted_rerun_advisory

        assert format_redacted_rerun_advisory(None) is None
        assert format_redacted_rerun_advisory("") is None
        assert format_redacted_rerun_advisory("cd /tmp && python train.py --lr 0.01") is None

        advisory = format_redacted_rerun_advisory("cd /tmp && python train.py --api-key [REDACTED]")
        assert isinstance(advisory, str) and advisory
        assert "[REDACTED]" in advisory
        assert "\033[" not in advisory

    def test_format_reproducibility_summary_pure_python(self):
        from pubrun.report.reproducibility import (
            NON_GUARANTEE_DISCLAIMER,
            assess_run,
            format_reproducibility_summary,
        )
        from pubrun.report.utils import HydrationReport

        manifest = {
            "schema_version": "1.0",
            "status": {"outcome": "completed", "exit_code": 0},
            "git": {"commit": "a" * 40, "dirty": True, "capture_state": {"status": "complete"}},
            "invocation": {"rerun_command": "python train.py --token [REDACTED]"},
        }
        report = HydrationReport(
            meta_ref="meta.json",
            status="hydrated",
            inherited_sections=["hardware", "packages"],
            direct_sections=["git"],
        )
        assessment = assess_run(manifest, hydration_report=report, preflight=False)
        text = format_reproducibility_summary(assessment)
        assert "\033[" not in text
        assert "Summary:" in text
        assert "Next step:" in text
        assert "Inherited from parent snapshot: hardware, packages" in text
        assert NON_GUARANTEE_DISCLAIMER in text


class TestTuiReproducibilityAndActions:
    """Live Textual Pilot tests for RunDetailsView reproducibility and ActionsPanel redacted advisory."""

    def test_details_reproducibility_markup_safety_running_and_no_live_preflight(self, tmp_path, monkeypatch):
        pytest.importorskip("textual")
        import asyncio
        import os
        import time
        from pubrun.report import reproducibility as repro_mod
        from pubrun.report.reproducibility import NON_GUARANTEE_DISCLAIMER
        from pubrun.status import RunInfo
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.details import RunDetailsView

        # Prove live preflight is never executed on TUI display_run.
        preflight_calls = []

        def _forbid_preflight(*args, **kwargs):
            preflight_calls.append((args, kwargs))
            raise AssertionError("TUI RunDetailsView must never run live preflight")

        monkeypatch.setattr(repro_mod, "compare_with_current_environment", _forbid_preflight)

        # Completed run with bracketed tokens ([REDACTED], [/not-a-tag]) to test Rich markup safety.
        runs_dir = tmp_path / "runs"
        completed_dir = runs_dir / "pubrun-repro1"
        completed_dir.mkdir(parents=True)
        (completed_dir / "manifest.json").write_text(
            _json.dumps(
                {
                    "schema_version": "1.0",
                    "run": {"run_id": "repro1"},
                    "status": {"outcome": "completed", "exit_code": 0},
                    "timing": {"started_at_utc": 1780250000.0, "elapsed_seconds": 1.5},
                    "git": {"commit": "b" * 40, "dirty": True, "capture_state": {"status": "complete"}},
                    "invocation": {
                        "script": {"basename": "train[1].py"},
                        "argv": ["train[1].py", "--token", "[REDACTED]", "[/bad]"],
                        "rerun_command": "python train[1].py --token [REDACTED]",
                    },
                }
            ),
            encoding="utf-8",
        )

        # Active running run (current PID so RunInfo classifies it as STATUS_RUNNING).
        running_dir = runs_dir / "pubrun-active1"
        running_dir.mkdir(parents=True)
        (running_dir / ".pubrun.lock").write_text(
            _json.dumps(
                {
                    "run_id": "active1",
                    "pid": os.getpid(),
                    "started_at_utc": time.time(),
                    "script": "live.py",
                    "argv": ["--step", "1"],
                    "hostname": "localhost",
                    "cwd": str(tmp_path),
                }
            ),
            encoding="utf-8",
        )

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs_dir))
            async with app.run_test() as pilot:
                details = app.query_one("#details-view", RunDetailsView)

                # Completed run renders shared summary cleanly without Rich markup crash.
                details.display_run(RunInfo(completed_dir))
                await pilot.pause()
                rendered = str(details.query_one("#lbl-general-info").render())
                assert "REPRODUCIBILITY & EVIDENCE" in rendered
                assert "Summary:" in rendered
                assert "[GAPS]" in rendered
                assert "Next step:" in rendered
                assert NON_GUARANTEE_DISCLAIMER in rendered
                assert "[REDACTED]" in rendered
                assert "[/bad]" in rendered
                assert preflight_calls == []

                # Running run displays preliminary note safely.
                running_info = RunInfo(running_dir)
                details.display_run(running_info)
                await pilot.pause()
                running_rendered = str(details.query_one("#lbl-general-info").render())
                assert "REPRODUCIBILITY & EVIDENCE" in running_rendered
                assert "still in progress" in running_rendered.lower()
                assert preflight_calls == []

        asyncio.run(_drive())

    def test_actions_panel_redacted_advisory_clearing_and_clean_clipboard(self, tmp_path, monkeypatch):
        pytest.importorskip("textual")
        import asyncio
        from pubrun.status import RunInfo
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets import actions as actions_mod
        from pubrun.tui.widgets.actions import ActionsPanel

        copied = []
        monkeypatch.setattr(actions_mod, "copy_to_clipboard", lambda txt: copied.append(txt) or True)

        runs_dir = tmp_path / "runs"
        red_dir = runs_dir / "pubrun-redacted1"
        red_dir.mkdir(parents=True)
        red_cmd = "cd /tmp/work && python train.py --api-key [REDACTED] --tag [v1]"
        (red_dir / "manifest.json").write_text(
            _json.dumps(
                {
                    "schema_version": "1.0",
                    "run": {"run_id": "redacted1"},
                    "status": {"outcome": "completed", "exit_code": 0},
                    "invocation": {"rerun_command": red_cmd},
                }
            ),
            encoding="utf-8",
        )

        clean_dir = runs_dir / "pubrun-clean1"
        clean_dir.mkdir(parents=True)
        clean_cmd = "cd /tmp/work && python train.py --epochs 5"
        (clean_dir / "manifest.json").write_text(
            _json.dumps(
                {
                    "schema_version": "1.0",
                    "run": {"run_id": "clean1"},
                    "status": {"outcome": "completed", "exit_code": 0},
                    "invocation": {"rerun_command": clean_cmd},
                }
            ),
            encoding="utf-8",
        )

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs_dir))
            notifications = []
            orig_notify = app.notify

            def _capture_notify(message, *, severity="information", **kwargs):
                notifications.append((str(message), severity))
                return orig_notify(message, severity=severity, **kwargs)

            monkeypatch.setattr(app, "notify", _capture_notify)

            async with app.run_test() as pilot:
                panel = app.query_one("#actions-view", ActionsPanel)

                # 1. Redacted run: advisory shown separately; command text & clipboard stay clean.
                panel.display_run(RunInfo(red_dir))
                await pilot.pause()
                cmd_text = str(panel.query_one("#lbl-rerun-command").render())
                adv_text = str(panel.query_one("#lbl-rerun-advisory").render())
                assert cmd_text == red_cmd
                assert panel.rerun_command == red_cmd
                assert "[REDACTED]" in adv_text
                assert "not directly executable" in adv_text.lower()
                assert "not directly executable" not in cmd_text.lower()

                btn = panel.query_one("#btn-copy-rerun")
                btn.press()
                await pilot.pause()
                assert copied[-1] == red_cmd
                assert any(sev == "warning" and "[REDACTED]" in msg for msg, sev in notifications)

                # 2. Switch to clean run: advisory clears, clipboard copies clean command with info notice.
                notifications.clear()
                panel.display_run(RunInfo(clean_dir))
                await pilot.pause()
                assert str(panel.query_one("#lbl-rerun-command").render()) == clean_cmd
                assert panel.rerun_command == clean_cmd
                assert str(panel.query_one("#lbl-rerun-advisory").render()) == ""

                btn.press()
                await pilot.pause()
                assert copied[-1] == clean_cmd
                assert any(sev == "information" for _, sev in notifications)

        asyncio.run(_drive())
