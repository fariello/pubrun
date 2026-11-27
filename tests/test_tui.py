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
            mock_app = mock.Mock()
            # Inject mocked module; patch.dict restores the real module on exit so
            # later tests in the same worker never import this Mock.
            mock_module = mock.Mock()
            mock_module.PubrunTUIApp = mock_app
            with mock.patch.dict(sys.modules, {"pubrun.tui.app": mock_module}):
                try:
                    main()
                except SystemExit as e:
                    # main() might exit 0 after executing command
                    assert e.code in (0, None)

            mock_app.assert_called_once_with(output_dir="/tmp/runs")
            mock_app.return_value.run.assert_called_once()


def test_tui_cli_parser_and_run_leaves_real_tui_module():
    """Running the CLI launch test must leave the real pubrun.tui.app module in sys.modules."""
    pytest.importorskip("textual")
    import pubrun.tui.app as real_app_module

    test_tui_cli_parser_and_run()

    assert sys.modules.get("pubrun.tui.app") is real_app_module
    from pubrun.tui.app import PubrunTUIApp
    assert PubrunTUIApp is real_app_module.PubrunTUIApp


def test_tui_missing_dependencies_prints_notice(capsys, monkeypatch):
    """Verify that when TUI dependencies are missing, a friendly explanation is printed and exits 1."""
    from pubrun.__main__ import main

    # Temporarily remove pubrun.tui.app so pytest restores any pre-existing module on teardown.
    monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)

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


def test_tui_missing_dependencies_leaves_real_tui_module(capsys, monkeypatch):
    """Running the missing-dependency test must restore the real pubrun.tui.app module on teardown."""
    pytest.importorskip("textual")
    import pubrun.tui.app as real_app_module

    with monkeypatch.context() as inner_mp:
        test_tui_missing_dependencies_prints_notice(capsys, inner_mp)

    assert sys.modules.get("pubrun.tui.app") is real_app_module
    from pubrun.tui.app import PubrunTUIApp
    assert PubrunTUIApp is real_app_module.PubrunTUIApp
    assert PubrunTUIApp.RefreshSidebar is real_app_module.PubrunTUIApp.RefreshSidebar


def test_tui_toml_serialization():
    """Verify that the dict_to_toml helper serializes configurations correctly."""
    pytest.importorskip("textual")
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


class TestBuildRerunCommand:
    """Unit tests for the pure _build_rerun_command helper (E-01)."""

    def test_win32_emits_powershell_newline_and_no_double_ampersand(self, monkeypatch):
        pytest.importorskip("textual")
        import types
        from pubrun.tui.widgets import actions as actions_mod

        monkeypatch.setattr(actions_mod, "sys", types.SimpleNamespace(platform="win32"))
        cmd = actions_mod._build_rerun_command(
            {
                "script": "train.py",
                "argv": ["--epochs", "5"],
                "cwd": r"C:\work\my project",
            }
        )
        assert "&&" not in cmd
        lines = cmd.splitlines()
        assert len(lines) == 2
        assert lines[0].startswith("cd ")
        assert "my project" in lines[0]
        assert lines[1] == "python train.py --epochs 5"

    def test_avoids_duplicating_script_from_argv_or_sys_argv(self, monkeypatch):
        pytest.importorskip("textual")
        import types
        from pubrun.tui.widgets import actions as actions_mod

        monkeypatch.setattr(actions_mod, "sys", types.SimpleNamespace(platform="linux"))
        cmd_dup = actions_mod._build_rerun_command(
            {"script": "train.py", "argv": ["train.py", "--lr", "0.01"], "cwd": "/tmp/work"}
        )
        assert cmd_dup == "cd /tmp/work && python train.py --lr 0.01"

        cmd_sys = actions_mod._build_rerun_command(
            {
                "script": "train.py",
                "argv": ["--lr", "0.01"],
                "sys_argv": ["src/train.py", "--lr", "0.01"],
                "cwd": "",
            }
        )
        assert cmd_sys == "python src/train.py --lr 0.01"


class TestConfigTomlHardening:
    """Unit tests for dict_to_toml hardening and _SELECT_OPTIONS cleanup (E-04)."""

    def test_dict_to_toml_omits_none_quotes_non_bare_keys_and_round_trips(self):
        pytest.importorskip("textual")
        import sys as _sys

        if _sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib  # type: ignore[no-redef]

        from pubrun.tui.widgets.config import _SELECT_OPTIONS, dict_to_toml

        assert "cfg-profile" not in _SELECT_OPTIONS
        assert [val for _, val in _SELECT_OPTIONS["cfg-imports-mode"]] == [
            "auto",
            "full",
            "noauto",
            "nopatch",
            "noconsole",
            "minimal",
        ]

        data = {
            "core": {
                "output_dir": "./runs",
                "nullable": None,
                "key with spaces": "v1",
                "tags": ["a", None, "b", True, 3],
            },
            "only_none": {"empty_val": None},
            "dotted.section": {"x.y": 42},
        }
        toml_str = dict_to_toml(data)
        assert "nullable" not in toml_str
        assert "only_none" not in toml_str
        parsed = tomllib.loads(toml_str)
        assert parsed == {
            "core": {
                "output_dir": "./runs",
                "key with spaces": "v1",
                "tags": ["a", "b", True, 3],
            },
            "dotted.section": {"x.y": 42},
        }


class TestTuiManifestResourcesFallback:
    """Verify RunResourcesView renders manifest.resources fields with and without events.jsonl (E-02)."""

    def test_manifest_resources_rendered_without_and_with_events(self, tmp_path):
        pytest.importorskip("textual")
        import asyncio
        from pubrun.status import RunInfo
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.resources import RunResourcesView

        runs = tmp_path / "runs"
        summary_only = runs / "pubrun-resm0001"
        summary_only.mkdir(parents=True)
        (summary_only / "manifest.json").write_text(
            _json.dumps(
                {
                    "run": {"run_id": "resm0001"},
                    "status": {"outcome": "completed"},
                    "timing": {"started_at_utc": 1000.0},
                    "resources": {
                        "peak_rss_bytes": 256 * 1024 * 1024,
                        "peak_cpu_percent": 82.5,
                        "system_memory": {
                            "start": {"available_bytes": 8 * 1024**3, "total_bytes": 16 * 1024**3},
                            "min_available": {"available_bytes": 6 * 1024**3},
                        },
                        "load_average": {"start": {"1min": 1.25}, "max_1min": 3.5},
                        "system_iowait_pct": {"max": 12.4},
                        "io_counters": {
                            "delta": {
                                "read_bytes": 4 * 1024 * 1024,
                                "write_bytes": 2 * 1024 * 1024,
                                "rchar": 10 * 1024 * 1024,
                                "wchar": 5 * 1024 * 1024,
                            }
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        with_events = _make_run_with_samples(tmp_path)
        ev_manifest = _json.loads((with_events / "manifest.json").read_text(encoding="utf-8"))
        ev_manifest["resources"]["peak_rss_bytes"] = 64 * 1024 * 1024
        ev_manifest["resources"]["load_average"] = {"start": {"1min": 0.5}, "max_1min": 1.0}
        (with_events / "manifest.json").write_text(_json.dumps(ev_manifest), encoding="utf-8")

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs))
            async with app.run_test() as pilot:
                view = app.query_one("#resources-view", RunResourcesView)

                # Fallback when events.jsonl is absent but manifest.resources is populated
                # (uses keep_manifest=False to verify on-demand load_manifest()).
                info_summary = RunInfo(summary_only, keep_manifest=False)
                assert info_summary.manifest is None
                view.display_run(info_summary)
                await pilot.pause()
                text = str(app.query_one("#resources-body").render())
                assert "Peak RSS:" in text and "256.0MB" in text
                assert "Peak CPU:" in text and "82.5%" in text
                assert "System RAM:" in text and "Min Avail RAM:" in text
                assert "Load Average:" in text and "3.50 peak (1-min)" in text
                assert "Node iowait:" in text and "12.4%" in text
                assert "Disk I/O:" in text and "Logical I/O:" in text

                # Alongside per-sample events.jsonl digest
                view.display_run(RunInfo(with_events, keep_manifest=False))
                await pilot.pause()
                both_text = str(app.query_one("#resources-body").render())
                assert "RSS (main)" in both_text
                assert "Manifest Resource Summary:" in both_text
                assert "Load Average:" in both_text

        asyncio.run(_drive())


class TestTuiLayout80x24:
    """Verify 80x24 terminal layout renders all tabs and modals without error or clipping (E-04)."""

    def test_80x24_pilot_mount_all_tabs_and_help_modal(self, tmp_path):
        pytest.importorskip("textual")
        import asyncio
        from textual.widgets import DataTable, TabbedContent
        from pubrun.tui.app import KeybindHelpModal, PubrunTUIApp
        from pubrun.tui.widgets.actions import ActionsPanel

        run = _make_run_with_samples(tmp_path)
        (run / "stdout.log").write_text("line 1\nline 2\n", encoding="utf-8")

        async def _drive():
            app = PubrunTUIApp(output_dir=str(tmp_path / "runs"))
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                sidebar = app.query_one("#sidebar")
                assert 20 <= sidebar.size.width <= 35

                # Verify subprocesses-table Elapsed column retains width=18
                sub_table = app.query_one("#subprocesses-table", DataTable)
                elapsed_cols = [c for c in sub_table.columns.values() if str(c.label) == "Elapsed"]
                assert elapsed_cols and elapsed_cols[0].width == 18

                tabs = app.query_one("#workspace-tabs", TabbedContent)
                for tab_id in (
                    "tab-details",
                    "tab-logs",
                    "tab-resources",
                    "tab-diff",
                    "tab-actions",
                    "tab-config",
                ):
                    tabs.active = tab_id
                    await pilot.pause()
                    assert tabs.active == tab_id

                # ActionsPanel wraps content in ScrollableContainer so bottom controls are reachable
                panel = app.query_one("#actions-view", ActionsPanel)
                assert panel.query_one("#actions-scroll") is not None
                assert panel.query_one("#btn-prune-execute") is not None

                # Help modal fits within 80x24 viewport (max-width: 90%)
                app.action_show_help()
                await pilot.pause()
                assert isinstance(app.screen, KeybindHelpModal)
                dialog = app.screen.query_one("#dialog-container")
                assert dialog.size.width <= 72
                app.screen.dismiss(None)
                await pilot.pause()

        asyncio.run(_drive())
