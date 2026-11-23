"""Regression tests for TUI widget bugs (IPD 8ebjeg, Set bugs-audit).

Covers BUG-13 (rerun clipboard on Textual 8.x), BUG-14 (Select.NULL handling in
ConfigPanel, DiffView, LogViewer), BUG-15 (RefreshSidebar routing), BUG-51 (GPU
model display), BUG-52 (diff depth fallback and warning preservation), BUG-53
(degraded-run deletion), and Bulk Prune ValueError handling (njn1up contract).
"""
import asyncio
import json
import time
from pathlib import Path

import pytest

pytest.importorskip("textual")

from textual.widgets import Select, RichLog, Input  # noqa: E402

from pubrun.status import RunInfo  # noqa: E402
from pubrun.tui.widgets.config import _SELECT_EMPTY_VALUE  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    """Keep user/global config and PUBRUN_* env out of every TUI test."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.delenv("PUBRUN_PROFILE", raising=False)
    monkeypatch.delenv("PUBRUN_META_REF", raising=False)


def _write_manifest(run_dir: Path, run_id, started_at=None, gpus=None, extra=None):
    run_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": "1.0",
        "run": {"run_id": run_id},
        "status": {"outcome": "completed", "exit_code": 0},
        "timing": {"started_at_utc": started_at if started_at is not None else time.time()},
        "invocation": {"rerun_command": f"python {run_id}.py"},
    }
    if gpus is not None:
        data["hardware"] = {"cpu": {"model": "TestCPU"}, "gpus": gpus}
    if extra:
        data.update(extra)
    (run_dir / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
    return run_dir


def _capture_notifications(app, monkeypatch):
    notes = []
    orig = app.notify

    def _notify(message, *, severity="information", **kwargs):
        notes.append((str(message), severity))
        return orig(message, severity=severity, **kwargs)

    monkeypatch.setattr(app, "notify", _notify)
    return notes


def _log_text(log: RichLog) -> str:
    return "\n".join(line.text for line in log.lines)


async def _show_tab(app, pilot, tab_id):
    """Activate a workspace tab so its RichLog has a size and renders writes."""
    from textual.widgets import TabbedContent

    app.query_one("#workspace-tabs", TabbedContent).active = tab_id
    await pilot.pause()
    await pilot.pause()


# --------------------------------------------------------------------------- #
# BUG-15: RefreshSidebar message routing
# --------------------------------------------------------------------------- #

class TestRefreshSidebarRouting:
    def test_posted_refresh_sidebar_reloads_sidebar_and_diff_dropdowns(self, tmp_path, monkeypatch):
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.sidebar import RunsSidebar

        runs = tmp_path / "runs"
        _write_manifest(runs / "pubrun-aaaa1111", "aaaa1111")

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs))
            notes = _capture_notifications(app, monkeypatch)
            async with app.run_test() as pilot:
                await pilot.pause()
                sidebar = app.query_one("#sidebar", RunsSidebar)
                assert len(sidebar.all_runs) == 1

                _write_manifest(runs / "pubrun-bbbb2222", "bbbb2222")
                app.post_message(app.RefreshSidebar())
                await pilot.pause()
                await pilot.pause()

                assert len(sidebar.all_runs) == 2
                select_a = app.query_one("#select-diff-a", Select)
                raw_legal = getattr(select_a, "_legal_values", None)
                if raw_legal is None:
                    raw_legal = [val for _, val in getattr(select_a, "_options", [])]
                legal = {opt for opt in raw_legal if opt != _SELECT_EMPTY_VALUE}
                assert str(runs / "pubrun-bbbb2222") in legal
                assert any("refreshed" in msg for msg, _ in notes)

        asyncio.run(_drive())


# --------------------------------------------------------------------------- #
# BUG-13, BUG-53, Bulk Prune ValueError handling
# --------------------------------------------------------------------------- #

class TestActionsPanel:
    def test_rerun_copy_for_lock_only_run(self, tmp_path, monkeypatch):
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets import actions as actions_mod
        from pubrun.tui.widgets.actions import ActionsPanel

        copied = []
        monkeypatch.setattr(actions_mod, "copy_to_clipboard", lambda t: copied.append(t) or True)

        runs = tmp_path / "runs"
        lock_dir = runs / "pubrun-lock0001"
        lock_dir.mkdir(parents=True)
        (lock_dir / ".pubrun.lock").write_text(json.dumps({
            "pid": 999999, "run_id": "lock0001", "script": "train.py",
            "argv": ["--epochs", "3"], "cwd": "/tmp/work",
            "hostname": "elsewhere-host", "started_at_utc": time.time(),
        }), encoding="utf-8")

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs))
            notes = _capture_notifications(app, monkeypatch)
            async with app.run_test() as pilot:
                panel = app.query_one("#actions-view", ActionsPanel)
                panel.display_run(RunInfo(lock_dir))
                await pilot.pause()
                assert panel.rerun_command == "cd /tmp/work && python train.py --epochs 3"
                panel.query_one("#btn-copy-rerun").press()
                await pilot.pause()
                assert copied == ["cd /tmp/work && python train.py --epochs 3"]
                assert any("copied" in msg.lower() for msg, _ in notes)

        asyncio.run(_drive())

    def test_delete_degraded_run_with_none_run_id(self, tmp_path, monkeypatch):
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.actions import ActionsPanel, ConfirmDeleteModal

        runs = tmp_path / "runs"
        run_dir = runs / "pubrun-degraded"
        run_dir.mkdir(parents=True)
        (run_dir / "junk.txt").write_text("x", encoding="utf-8")
        info = RunInfo(run_dir)
        info.run_id = None

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs))
            notes = _capture_notifications(app, monkeypatch)
            async with app.run_test() as pilot:
                panel = app.query_one("#actions-view", ActionsPanel)
                panel.display_run(info)
                await pilot.pause()
                panel.query_one("#btn-delete-selected").press()
                await pilot.pause()
                modal = app.screen
                assert isinstance(modal, ConfirmDeleteModal)
                assert modal.run_id == "pubrun-degraded"
                rendered = " ".join(str(lbl.render()) for lbl in modal.query("Label"))
                assert "pubrun-d" in rendered

                modal.dismiss(True)
                await pilot.pause()
                await pilot.pause()
                assert not run_dir.exists()
                assert panel.run_info is None
                assert any(sev == "information" and "deleted run pubrun-d" in msg for msg, sev in notes)
                assert not any(sev == "error" for _, sev in notes)

        asyncio.run(_drive())

    def test_confirm_delete_modal_with_none_run_id_composes(self, tmp_path):
        from textual.app import App
        from pubrun.tui.widgets.actions import ConfirmDeleteModal

        class _Host(App):
            pass

        async def _drive():
            app = _Host()
            async with app.run_test() as pilot:
                modal = ConfirmDeleteModal(None)
                app.push_screen(modal)
                await pilot.pause()
                rendered = " ".join(str(lbl.render()) for lbl in modal.query("Label"))
                assert "unknown" in rendered

        asyncio.run(_drive())

    @pytest.mark.parametrize("age", ["2w", "abc", "-5d", "nan", "inf"])
    def test_bulk_prune_invalid_age_reports_error_and_deletes_nothing(self, tmp_path, monkeypatch, age):
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.actions import ActionsPanel

        runs = tmp_path / "runs"
        old = _write_manifest(runs / "pubrun-old00001", "old00001", started_at=time.time() - 30 * 86400)

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs))
            notes = _capture_notifications(app, monkeypatch)
            posted = []
            orig_post = app.post_message

            def _post(msg):
                posted.append(type(msg).__name__)
                return orig_post(msg)

            monkeypatch.setattr(app, "post_message", _post)
            async with app.run_test() as pilot:
                await _show_tab(app, pilot, "tab-actions")
                panel = app.query_one("#actions-view", ActionsPanel)
                panel.query_one("#input-clean-older", Input).value = age
                await pilot.pause()
                posted.clear()
                panel.run_bulk_prune(dry_run=False)
                await pilot.pause()
                log_text = _log_text(panel.query_one("#cleanup-log-output", RichLog))
                assert "Pruning failed" in log_text
                assert any(sev == "error" for _, sev in notes)
                assert "RefreshSidebar" not in posted
                assert old.exists()

        asyncio.run(_drive())

    @pytest.mark.parametrize("age, expect_deleted", [("60m", True), ("3600s", True), ("90d", False), ("7", True)])
    def test_bulk_prune_accepts_canonical_age_units(self, tmp_path, monkeypatch, age, expect_deleted):
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.actions import ActionsPanel

        runs = tmp_path / "runs"
        old = _write_manifest(runs / "pubrun-old00002", "old00002", started_at=time.time() - 30 * 86400)

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs))
            notes = _capture_notifications(app, monkeypatch)
            async with app.run_test() as pilot:
                panel = app.query_one("#actions-view", ActionsPanel)
                panel.query_one("#input-clean-older", Input).value = age
                await pilot.pause()
                panel.run_bulk_prune(dry_run=False)
                await pilot.pause()
                assert not any(sev == "error" for _, sev in notes)
                assert old.exists() is (not expect_deleted)

        asyncio.run(_drive())


# --------------------------------------------------------------------------- #
# BUG-14: ConfigPanel Select.NULL handling
# --------------------------------------------------------------------------- #

class TestConfigPanel:
    def test_is_select_empty_sentinels(self):
        from pubrun.tui.widgets.config import _is_select_empty

        assert _is_select_empty(_SELECT_EMPTY_VALUE) is True
        assert _is_select_empty(None) is True
        assert _is_select_empty(False) is False
        assert _is_select_empty(0) is False
        assert _is_select_empty("basic") is False

    def test_save_never_writes_select_null(self, tmp_path, monkeypatch):
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.config import ConfigPanel

        async def _drive():
            app = PubrunTUIApp(output_dir=str(tmp_path / "runs"))
            async with app.run_test() as pilot:
                panel = app.query_one("#config-view", ConfigPanel)
                for wid in ("#cfg-profile", "#cfg-console-mode", "#cfg-redact-repr"):
                    panel.query_one(wid, Select).value = _SELECT_EMPTY_VALUE
                await pilot.pause()
                panel.save_settings()
                await pilot.pause()

        asyncio.run(_drive())
        text = (tmp_path / ".pubrun.toml").read_text(encoding="utf-8")
        assert "Select.NULL" not in text
        assert "Select.BLANK" not in text
        assert str(_SELECT_EMPTY_VALUE) not in text
        assert "profile" not in text
        assert "capture_mode" not in text
        assert "representation" not in text
        assert "auto_start" in text

    def test_save_writes_selected_values(self, tmp_path):
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.config import ConfigPanel

        async def _drive():
            app = PubrunTUIApp(output_dir=str(tmp_path / "runs"))
            async with app.run_test() as pilot:
                panel = app.query_one("#config-view", ConfigPanel)
                panel.query_one("#cfg-console-mode", Select).value = "standard"
                await pilot.pause()
                panel.save_settings()
                await pilot.pause()

        asyncio.run(_drive())
        text = (tmp_path / ".pubrun.toml").read_text(encoding="utf-8")
        assert 'capture_mode = "standard"' in text

    def test_unknown_env_profile_mounts_with_warning(self, tmp_path, monkeypatch):
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.config import ConfigPanel

        monkeypatch.setenv("PUBRUN_PROFILE", "standard")
        (tmp_path / ".pubrun.toml").write_text(
            '[redaction]\nrepresentation = "legacy-mask"\n', encoding="utf-8"
        )

        async def _drive():
            app = PubrunTUIApp(output_dir=str(tmp_path / "runs"))
            notes = _capture_notifications(app, monkeypatch)
            async with app.run_test() as pilot:
                await pilot.pause()
                panel = app.query_one("#config-view", ConfigPanel)
                assert panel.query_one("#cfg-profile", Select).value == _SELECT_EMPTY_VALUE
                assert panel.query_one("#cfg-redact-repr", Select).value == _SELECT_EMPTY_VALUE
                assert panel.query_one("#cfg-console-mode", Select).value == "off"
                warnings = [m for m, s in notes if s == "warning"]
                assert any("core.profile" in m and "standard" in m for m in warnings)
                assert any("redaction.representation" in m for m in warnings)

                panel.save_settings()
                await pilot.pause()

        asyncio.run(_drive())
        text = (tmp_path / ".pubrun.toml").read_text(encoding="utf-8")
        assert "Select.NULL" not in text
        assert "Select.BLANK" not in text
        assert str(_SELECT_EMPTY_VALUE) not in text
        # The unknown file value is preserved rather than corrupted.
        assert 'representation = "legacy-mask"' in text


# --------------------------------------------------------------------------- #
# BUG-14 / BUG-52: DiffView
# --------------------------------------------------------------------------- #

class TestDiffView:
    def _setup_runs(self, tmp_path):
        runs = tmp_path / "runs"
        a = _write_manifest(runs / "pubrun-diffa001", "diffa001", extra={"custom": {"x": 1}})
        b = _write_manifest(runs / "pubrun-diffb002", "diffb002", extra={"custom": {"x": 2}})
        return runs, a, b

    def test_blank_runs_report_selection_error(self, tmp_path, monkeypatch):
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.diff import DiffView

        runs, _, _ = self._setup_runs(tmp_path)

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs))
            notes = _capture_notifications(app, monkeypatch)
            async with app.run_test() as pilot:
                await _show_tab(app, pilot, "tab-diff")
                view = app.query_one("#diff-view", DiffView)
                assert view.query_one("#select-diff-a", Select).value == _SELECT_EMPTY_VALUE
                view.run_difference()
                await pilot.pause()
                out = _log_text(view.query_one("#diff-output-area", RichLog))
                assert "Select baseline and comparison runs" in out
                assert "against itself" not in out
                assert "Error computing diff" not in out
                assert any("Please select both Run A and Run B" in m for m, _ in notes)

        asyncio.run(_drive())

    @pytest.mark.parametrize("depth", [_SELECT_EMPTY_VALUE, "standard", "deep"])
    def test_depth_fallback_and_warnings_preserved(self, tmp_path, monkeypatch, depth):
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets import diff as diff_mod
        from pubrun.tui.widgets.diff import DiffView

        runs, a, b = self._setup_runs(tmp_path)
        seen_depth = []
        real_compare = diff_mod.compare_manifests

        def _compare(ma, mb, ignores, show_same=False, depth="basic"):
            seen_depth.append(depth)
            return real_compare(ma, mb, ignores, show_same=show_same, depth=depth)

        monkeypatch.setattr(diff_mod, "compare_manifests", _compare)
        monkeypatch.setattr(
            diff_mod, "hydrate_manifest", lambda p, m: (m, [f"hydration note for {Path(p).parent.name}"])
        )

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs))
            async with app.run_test() as pilot:
                await _show_tab(app, pilot, "tab-diff")
                view = app.query_one("#diff-view", DiffView)
                view.query_one("#select-diff-a", Select).value = str(a)
                view.query_one("#select-diff-b", Select).value = str(b)
                view.query_one("#select-diff-depth", Select).value = depth
                await pilot.pause()
                view.run_difference()
                await pilot.pause()
                out = _log_text(view.query_one("#diff-output-area", RichLog))
                assert "Error computing diff" not in out
                assert "PUBRUN SEMANTIC DIFFERENCE" in out
                assert "[Warning] hydration note for pubrun-diffa001" in out
                assert "[Warning] hydration note for pubrun-diffb002" in out

        asyncio.run(_drive())
        expected = "basic" if depth == _SELECT_EMPTY_VALUE else depth
        assert seen_depth == [expected]


# --------------------------------------------------------------------------- #
# BUG-51: GPU model display
# --------------------------------------------------------------------------- #

class TestRunDetailsGpu:
    def _render(self, tmp_path, monkeypatch, manifest_hw):
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.details import RunDetailsView

        runs = tmp_path / "runs"
        run_dir = _write_manifest(runs / "pubrun-gpu00001", "gpu00001")
        data = json.loads((run_dir / "manifest.json").read_text())
        data["hardware"] = manifest_hw
        (run_dir / "manifest.json").write_text(json.dumps(data))
        result = {}

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs))
            async with app.run_test() as pilot:
                details = app.query_one("#details-view", RunDetailsView)
                details.display_run(RunInfo(run_dir))
                await pilot.pause()
                result["text"] = str(details.query_one("#lbl-general-info").render())

        asyncio.run(_drive())
        return result["text"]

    def test_gpu_model_key_rendered(self, tmp_path, monkeypatch):
        text = self._render(tmp_path, monkeypatch, {
            "cpu": {"model": "TestCPU"},
            "gpus": [
                {"model": "NVIDIA A100 [80GB]", "driver_version": "535.1"},
                {"name": "Legacy GPU"},
                "not-a-dict",
            ],
        })
        assert "NVIDIA A100 [80GB]" in text
        assert "535.1" in text
        assert "Legacy GPU" in text
        assert "(Driver: -)" in text
        assert "None (Driver" not in text

    def test_non_dict_hardware_does_not_crash(self, tmp_path, monkeypatch):
        text = self._render(tmp_path, monkeypatch, ["unexpected"])
        assert "HOST & HARDWARE SPECS" in text


# --------------------------------------------------------------------------- #
# zen6hs: OS line with missing or null host OS fields
# --------------------------------------------------------------------------- #

_DROP = object()


class TestRunDetailsOsLine:
    def _os_line(self, tmp_path, os_name, os_release):
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.details import RunDetailsView

        host = {"capture_state": {"status": "complete"}, "hostname": "arm-01"}
        if os_name is not _DROP:
            host["os_name"] = os_name
        if os_release is not _DROP:
            host["os_release"] = os_release
        runs = tmp_path / "runs"
        run_dir = _write_manifest(runs / "pubrun-os000001", "os000001", extra={"host": host})
        result = {}

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs))
            async with app.run_test() as pilot:
                details = app.query_one("#details-view", RunDetailsView)
                details.display_run(RunInfo(run_dir))
                await pilot.pause()
                result["text"] = str(details.query_one("#lbl-general-info").render())

        asyncio.run(_drive())
        os_lines = [
            line.strip() for line in result["text"].splitlines() if line.strip().startswith("OS:")
        ]
        assert len(os_lines) == 1
        return os_lines[0][len("OS:"):].lstrip()

    @pytest.mark.parametrize(
        "os_name, os_release, expected",
        [
            ("Linux", _DROP, "Linux"),
            ("Linux", None, "Linux"),
            (_DROP, "#101-Ubuntu SMP", "unknown (#101-Ubuntu SMP)"),
            (None, "#101-Ubuntu SMP", "unknown (#101-Ubuntu SMP)"),
            (_DROP, _DROP, "-"),
            ("", "", "-"),
            ("Linux", "  ", "Linux"),
        ],
        ids=[
            "release-missing",
            "release-null",
            "name-missing",
            "name-null",
            "both-missing",
            "both-empty",
            "release-whitespace",
        ],
    )
    def test_missing_fields_never_render_none(self, tmp_path, os_name, os_release, expected):
        text = self._os_line(tmp_path, os_name, os_release)
        assert text == expected
        assert "None" not in text

    def test_both_present_unchanged(self, tmp_path):
        assert self._os_line(tmp_path, "Linux", "#101-Ubuntu SMP") == "Linux (#101-Ubuntu SMP)"

    def test_bracketed_release_rendered_literally(self, tmp_path):
        text = self._os_line(tmp_path, "Linux", "#1 SMP [PREEMPT_DYNAMIC] [/]")
        assert text == "Linux (#1 SMP [PREEMPT_DYNAMIC] [/])"


# --------------------------------------------------------------------------- #
# BUG-14: LogViewer
# --------------------------------------------------------------------------- #

class TestLogViewer:
    def test_blank_selection_ignored_on_change_and_refresh(self, tmp_path, monkeypatch):
        from pubrun.tui.app import PubrunTUIApp
        from pubrun.tui.widgets.viewer import LogViewer

        runs = tmp_path / "runs"
        run_dir = _write_manifest(runs / "pubrun-logs0001", "logs0001")
        (run_dir / "console.log").write_text("hello from console\n", encoding="utf-8")

        async def _drive():
            app = PubrunTUIApp(output_dir=str(runs))
            async with app.run_test() as pilot:
                await _show_tab(app, pilot, "tab-logs")
                viewer = app.query_one("#logs-view", LogViewer)
                loaded = []
                orig_load = viewer.load_log_file

                def _load(path):
                    loaded.append(path)
                    return orig_load(path)

                monkeypatch.setattr(viewer, "load_log_file", _load)

                viewer.display_run_logs(run_dir)
                await pilot.pause()
                assert loaded and loaded[0].endswith("console.log")

                loaded.clear()
                select = viewer.query_one("#select-log-file", Select)
                select.value = _SELECT_EMPTY_VALUE
                await pilot.pause()
                viewer.query_one("#btn-refresh-log").press()
                await pilot.pause()
                assert loaded == []
                assert str(_SELECT_EMPTY_VALUE) not in [str(p) for p in loaded]
                out = _log_text(viewer.query_one("#log-content-area", RichLog))
                assert "does not exist" not in out

        asyncio.run(_drive())
