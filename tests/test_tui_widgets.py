"""Textual Pilot tests for TUI wiring and widget failure paths (IPD bwoyan, Set test-audit)."""

import asyncio
import json
import shutil
import subprocess
import time
import types
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("textual")

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from textual.widgets import Button, Checkbox, Input, RichLog, Select, TabbedContent, Tree  # noqa: E402

from pubrun.config import load_local_config  # noqa: E402
from pubrun.report.methods import generate_report  # noqa: E402
from pubrun.report.utils import hydrate_manifest  # noqa: E402
from pubrun.status import RunInfo  # noqa: E402
from pubrun.tui.app import PubrunTUIApp  # noqa: E402
from pubrun.tui.widgets import actions as actions_mod  # noqa: E402
from pubrun.tui.widgets import details as details_mod  # noqa: E402
from pubrun.tui.widgets import sidebar as sidebar_mod  # noqa: E402
from pubrun.tui.widgets.actions import ActionsPanel, ConfirmDeleteModal, copy_to_clipboard  # noqa: E402
from pubrun.tui.widgets.config import ConfigPanel, _SELECT_EMPTY_VALUE, dict_to_toml  # noqa: E402
from pubrun.tui.widgets.details import RunDetailsView  # noqa: E402
from pubrun.tui.widgets.diff import DiffView  # noqa: E402
from pubrun.tui.widgets.resources import RunResourcesView  # noqa: E402
from pubrun.tui.widgets.sidebar import RunsSidebar  # noqa: E402
from pubrun.tui.widgets.viewer import LogViewer  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    """Isolate user/global config and color/profile env vars for every TUI test."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("PUBRUN_PROFILE", raising=False)
    monkeypatch.delenv("PUBRUN_META_REF", raising=False)


def _write_run(runs, run_id, script="train.py", age=60.0, extra=None, logs=None):
    run_dir = Path(runs) / f"pubrun-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": "1.0",
        "run": {"run_id": run_id},
        "status": {"outcome": "completed", "exit_code": 0},
        "timing": {"started_at_utc": time.time() - age},
        "invocation": {
            "script": {"basename": script},
            "rerun_command": f"python {script}",
        },
    }
    if extra:
        data.update(extra)
    (run_dir / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
    if logs:
        for rel_name, content in logs.items():
            log_path = run_dir / rel_name
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(content, encoding="utf-8")
    return run_dir


def _capture_notifications(app, monkeypatch):
    notes = []
    orig = app.notify

    def _notify(message, *, severity="information", **kwargs):
        notes.append((str(message), severity))
        return orig(message, severity=severity, **kwargs)

    monkeypatch.setattr(app, "notify", _notify)
    return notes


def _capture_posts(app, monkeypatch):
    posted = []
    orig = app.post_message

    def _post(msg):
        posted.append(type(msg).__name__)
        return orig(msg)

    monkeypatch.setattr(app, "post_message", _post)
    return posted


def _log_lines(log):
    return [line.text for line in log.lines]


def _general_text(app):
    return str(app.query_one("#lbl-general-info").render())


def _tree_labels(app):
    tree = app.query_one("#runs-tree", Tree)
    return [str(child.label) for child in tree.root.children]


async def _show_tab(app, pilot, tab_id):
    app.query_one("#workspace-tabs", TabbedContent).active = tab_id
    await pilot.pause()
    await pilot.pause()


def _run_app(runs, body, monkeypatch):
    result = {}

    async def _drive():
        app = PubrunTUIApp(output_dir=str(runs))
        notes = _capture_notifications(app, monkeypatch)
        async with app.run_test() as pilot:
            await body(app, pilot, notes)
            result["running"] = app.is_running
        result["return_code"] = app.return_code

    asyncio.run(_drive())
    return result


def _render_details(tmp_path, run_dir, monkeypatch):
    captured = {}

    async def _body(app, pilot, notes):
        details = app.query_one("#details-view", RunDetailsView)
        details.display_run(RunInfo(run_dir))
        await pilot.pause()
        captured["text"] = _general_text(app)

    _run_app(tmp_path / "runs", _body, monkeypatch)
    return captured["text"]


# --------------------------------------------------------------------------- #
# E-02: App wiring (tree selection -> all four panes; sidebar toggle)
# --------------------------------------------------------------------------- #


class TestAppWiring:
    def test_tree_selection_updates_details_logs_resources_and_actions(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        _write_run(runs, "aaaa1111", script="train.py", age=10, logs={"console.log": "train log\n"})
        _write_run(runs, "bbbb2222", script="eval.py", age=20, logs={"console.log": "eval log\n"})

        async def _body(app, pilot, notes):
            await pilot.pause()
            assert _tree_labels(app) == [
                "train.py [aaaa1111] • COMPLETED",
                "eval.py [bbbb2222] • COMPLETED",
            ]
            tree = app.query_one("#runs-tree", Tree)
            tree.select_node(tree.root.children[1])
            await pilot.pause()
            await pilot.pause()

            assert app.selected_run_info is not None
            assert app.selected_run_info.run_id == "bbbb2222"
            assert "  Run ID:        bbbb2222" in _general_text(app).splitlines()

            # Inactive tabs stay lazy until activated.
            assert app.query_one("#logs-view", LogViewer).run_dir is None
            assert app.query_one("#resources-view", RunResourcesView).run_info is None
            assert app.query_one("#actions-view", ActionsPanel).run_info is None

            await _show_tab(app, pilot, "tab-logs")
            assert [p.name for p in app.query_one("#logs-view", LogViewer).log_files] == [
                "console.log"
            ]

            await _show_tab(app, pilot, "tab-resources")
            assert str(app.query_one("#resources-body").render()).startswith(
                "No resource samples recorded for this run"
            )

            await _show_tab(app, pilot, "tab-actions")
            assert app.query_one("#actions-view", ActionsPanel).rerun_command == "python eval.py"

        res = _run_app(runs, _body, monkeypatch)
        assert res["return_code"] in (None, 0)

    def test_tree_selection_of_run_with_null_remote_url_keeps_app_running(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        _write_run(runs, "null0001", extra={"git": {"commit": "c" * 40, "remote_url": None}})

        async def _body(app, pilot, notes):
            await pilot.pause()
            tree = app.query_one("#runs-tree", Tree)
            tree.select_node(tree.root.children[0])
            await pilot.pause()
            await pilot.pause()
            assert "  Remote URL:     -" in _general_text(app).splitlines()

        res = _run_app(runs, _body, monkeypatch)
        assert res["running"] is True
        assert res["return_code"] in (None, 0)

    def test_toggle_sidebar_binding_and_action(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"

        async def _body(app, pilot, notes):
            await pilot.pause()
            sidebar = app.query_one("#sidebar")
            assert sidebar.display is True
            await pilot.press("ctrl+s")
            await pilot.pause()
            assert sidebar.display is False
            app.action_toggle_sidebar()
            await pilot.pause()
            assert sidebar.display is True

        _run_app(runs, _body, monkeypatch)


# --------------------------------------------------------------------------- #
# E-10: RunsSidebar search and scan failure
# --------------------------------------------------------------------------- #


class TestRunsSidebar:
    def test_search_filters_by_script_and_run_id_case_insensitively(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        _write_run(runs, "aaaa1111", script="train.py", age=10)
        _write_run(runs, "bbbb2222", script="eval.py", age=20)

        async def _body(app, pilot, notes):
            await pilot.pause()
            search = app.query_one("#runs-search", Input)

            search.value = "TRAIN"
            await pilot.pause()
            assert _tree_labels(app) == ["train.py [aaaa1111] • COMPLETED"]

            search.value = "bbbb"
            await pilot.pause()
            assert _tree_labels(app) == ["eval.py [bbbb2222] • COMPLETED"]

            search.value = "zzz"
            await pilot.pause()
            assert _tree_labels(app) == ["No runs found"]
            tree = app.query_one("#runs-tree", Tree)
            assert tree.root.children[0].data is None

            search.value = ""
            await pilot.pause()
            assert len(_tree_labels(app)) == 2

        _run_app(runs, _body, monkeypatch)

    def test_scan_failure_is_shown_as_a_tree_leaf(self, tmp_path, monkeypatch):
        def _boom(_output_dir, **_kwargs):
            raise RuntimeError("disk on fire")

        monkeypatch.setattr(sidebar_mod, "scan_runs", _boom)
        runs = tmp_path / "runs"

        async def _body(app, pilot, notes):
            await pilot.pause()
            assert _tree_labels(app) == ["Scan failed: disk on fire"]
            assert app.query_one("#sidebar", RunsSidebar).all_runs == []

        res = _run_app(runs, _body, monkeypatch)
        assert res["running"] is True


# --------------------------------------------------------------------------- #
# E-03: ActionsPanel archive flows
# --------------------------------------------------------------------------- #


class TestActionsArchive:
    def test_archive_creates_zip_and_keeps_raw_dir(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        run_dir = _write_run(
            runs,
            "arch0001",
            logs={"console.log": "hello\n", "sub/x.txt": "nested\n"},
        )

        async def _body(app, pilot, notes):
            panel = app.query_one("#actions-view", ActionsPanel)
            panel.display_run(RunInfo(run_dir))
            await pilot.pause()
            posts = _capture_posts(app, monkeypatch)
            notes.clear()
            panel.query_one("#btn-archive-run", Button).press()
            await pilot.pause()
            await pilot.pause()

            assert notes == [("Created archive: arch0001.zip", "information")]
            assert "RefreshSidebar" not in posts
            zip_path = runs / "archive" / "arch0001.zip"
            assert zip_path.exists()
            with zipfile.ZipFile(zip_path) as zf:
                assert sorted(zf.namelist()) == ["console.log", "manifest.json", "sub/x.txt"]
            assert run_dir.exists()

        _run_app(runs, _body, monkeypatch)

    def test_archive_with_delete_raw_removes_dir_and_refreshes_sidebar(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        run_dir = _write_run(runs, "arch0002", logs={"console.log": "hello\n"})

        async def _body(app, pilot, notes):
            panel = app.query_one("#actions-view", ActionsPanel)
            panel.display_run(RunInfo(run_dir))
            panel.query_one("#check-delete-raw", Checkbox).value = True
            await pilot.pause()
            notes.clear()
            panel.query_one("#btn-archive-run", Button).press()
            await pilot.pause()
            await pilot.pause()

            assert ("Deleted original uncompressed directory.", "information") in notes
            assert ("Runs database and cache refreshed.", "information") in notes
            assert app.query_one("#sidebar", RunsSidebar).all_runs == []
            assert not run_dir.exists()
            assert (runs / "archive" / "arch0002.zip").exists()

        _run_app(runs, _body, monkeypatch)

    def test_archive_of_vanished_run_dir_reports_error(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        run_dir = _write_run(runs, "gone0001")

        async def _body(app, pilot, notes):
            panel = app.query_one("#actions-view", ActionsPanel)
            panel.display_run(RunInfo(run_dir))
            await pilot.pause()
            shutil.rmtree(run_dir)
            notes.clear()
            panel.query_one("#btn-archive-run", Button).press()
            await pilot.pause()

            assert notes == [
                ("Archive failed: run directory pubrun-gone0001 no longer exists.", "error")
            ]
            assert not (runs / "archive").exists()

        _run_app(runs, _body, monkeypatch)

    def test_archive_dir_creation_failure_reports_error_and_keeps_app(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        run_dir = _write_run(runs, "fail0001")
        (runs / "archive").write_text("blocker file", encoding="utf-8")

        async def _body(app, pilot, notes):
            panel = app.query_one("#actions-view", ActionsPanel)
            panel.display_run(RunInfo(run_dir))
            panel.query_one("#check-delete-raw", Checkbox).value = True
            await pilot.pause()
            notes.clear()
            panel.query_one("#btn-archive-run", Button).press()
            await pilot.pause()
            await pilot.pause()

            assert [sev for _, sev in notes] == ["error"]
            assert notes[0][0].startswith("Archive failed: ")
            assert run_dir.exists()

        res = _run_app(runs, _body, monkeypatch)
        assert res["running"] is True


# --------------------------------------------------------------------------- #
# E-11: ActionsPanel citations and no-selection guard
# --------------------------------------------------------------------------- #


class TestActionsCitations:
    @pytest.mark.parametrize(
        "button_id, fmt",
        [("btn-copy-md", "markdown"), ("btn-copy-latex", "latex")],
    )
    def test_copy_methods_copies_generated_report(self, tmp_path, monkeypatch, button_id, fmt):
        runs = tmp_path / "runs"
        run_dir = _write_run(runs, "cite0001")
        manifest_path = run_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = generate_report(hydrate_manifest(str(manifest_path), manifest)[0], fmt)

        copied = []
        monkeypatch.setattr(actions_mod, "copy_to_clipboard", lambda txt: copied.append(txt) or True)

        async def _body(app, pilot, notes):
            panel = app.query_one("#actions-view", ActionsPanel)
            panel.display_run(RunInfo(run_dir))
            await pilot.pause()
            notes.clear()
            panel.query_one(f"#{button_id}", Button).press()
            await pilot.pause()

            assert notes == [(f"Methods ({fmt}) copied to clipboard.", "information")]
            assert copied == [expected]

        _run_app(runs, _body, monkeypatch)

    def test_copy_methods_clipboard_failure_warns(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        run_dir = _write_run(runs, "cite0002")
        monkeypatch.setattr(actions_mod, "copy_to_clipboard", lambda _txt: False)

        async def _body(app, pilot, notes):
            panel = app.query_one("#actions-view", ActionsPanel)
            panel.display_run(RunInfo(run_dir))
            await pilot.pause()
            notes.clear()
            panel.query_one("#btn-copy-md", Button).press()
            await pilot.pause()

            assert notes == [("Failed to copy. Copy text manually.", "warning")]

        _run_app(runs, _body, monkeypatch)

    def test_copy_methods_without_manifest_reports_unavailable(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        lock_dir = runs / "pubrun-lock0001"
        lock_dir.mkdir(parents=True)
        (lock_dir / ".pubrun.lock").write_text(
            json.dumps(
                {
                    "pid": 999999,
                    "run_id": "lock0001",
                    "hostname": "elsewhere-host",
                    "started_at_utc": time.time(),
                }
            ),
            encoding="utf-8",
        )

        async def _body(app, pilot, notes):
            panel = app.query_one("#actions-view", ActionsPanel)
            panel.display_run(RunInfo(lock_dir))
            await pilot.pause()
            notes.clear()
            panel.query_one("#btn-copy-latex", Button).press()
            await pilot.pause()

            assert notes == [("Citations not available.", "error")]

        _run_app(runs, _body, monkeypatch)

    @pytest.mark.parametrize(
        "button_id",
        [
            "btn-copy-rerun",
            "btn-copy-md",
            "btn-copy-latex",
            "btn-archive-run",
            "btn-delete-selected",
        ],
    )
    def test_run_buttons_without_selection_ask_for_a_run(self, tmp_path, monkeypatch, button_id):
        runs = tmp_path / "runs"

        async def _body(app, pilot, notes):
            panel = app.query_one("#actions-view", ActionsPanel)
            await pilot.pause()
            notes.clear()
            panel.query_one(f"#{button_id}", Button).press()
            await pilot.pause()

            assert notes == [("Please select a run first.", "error")]
            assert not (runs / "archive").exists()

        _run_app(runs, _body, monkeypatch)


# --------------------------------------------------------------------------- #
# E-12: ConfirmDeleteModal
# --------------------------------------------------------------------------- #


class TestConfirmDeleteModal:
    async def _open_modal(self, app, pilot, run_dir):
        panel = app.query_one("#actions-view", ActionsPanel)
        panel.display_run(RunInfo(run_dir))
        await pilot.pause()
        panel.query_one("#btn-delete-selected", Button).press()
        await pilot.pause()

    def test_typing_gates_confirm_and_cancel_keeps_run(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        run_dir = _write_run(runs, "dele0001")

        async def _body(app, pilot, notes):
            await self._open_modal(app, pilot, run_dir)
            assert isinstance(app.screen, ConfirmDeleteModal)
            confirm_btn = app.screen.query_one("#btn-confirm-del", Button)
            confirm_input = app.screen.query_one("#input-confirm-yes", Input)
            assert confirm_btn.disabled is True

            confirm_input.value = "no"
            await pilot.pause()
            assert confirm_btn.disabled is True

            confirm_input.value = " YES "
            await pilot.pause()
            assert confirm_btn.disabled is False

            confirm_input.value = "yess"
            await pilot.pause()
            assert confirm_btn.disabled is True

            app.screen.query_one("#btn-cancel-del", Button).press()
            await pilot.pause()
            assert not isinstance(app.screen, ConfirmDeleteModal)
            assert notes == []
            assert run_dir.exists()

        _run_app(runs, _body, monkeypatch)

    def test_typed_yes_and_confirm_deletes_run(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        run_dir = _write_run(runs, "dele0002")

        async def _body(app, pilot, notes):
            await self._open_modal(app, pilot, run_dir)
            app.screen.query_one("#input-confirm-yes", Input).value = "yes"
            await pilot.pause()
            app.screen.query_one("#btn-confirm-del", Button).press()
            await pilot.pause()
            await pilot.pause()

            assert ("Successfully deleted run dele0002", "information") in notes
            assert app.query_one("#actions-view", ActionsPanel).run_info is None
            assert not run_dir.exists()

        _run_app(runs, _body, monkeypatch)

    def test_delete_error_is_reported_and_run_kept(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        run_dir = _write_run(runs, "dele0003")

        def _deny(_path):
            raise PermissionError("read-only volume")

        async def _body(app, pilot, notes):
            await self._open_modal(app, pilot, run_dir)
            monkeypatch.setattr(actions_mod.shutil, "rmtree", _deny)
            notes.clear()
            app.screen.dismiss(True)
            await pilot.pause()
            await pilot.pause()

            assert notes == [("Deletion failed: read-only volume", "error")]
            assert app.query_one("#actions-view", ActionsPanel).run_info is not None
            assert run_dir.exists()

        _run_app(runs, _body, monkeypatch)


# --------------------------------------------------------------------------- #
# E-13: Bulk prune dry run
# --------------------------------------------------------------------------- #


class TestBulkPruneDryRun:
    def test_dry_run_lists_candidates_and_deletes_nothing(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        run_dir = _write_run(runs, "old00001", age=40 * 86400)

        async def _body(app, pilot, notes):
            await _show_tab(app, pilot, "tab-actions")
            posts = _capture_posts(app, monkeypatch)
            notes.clear()
            app.query_one("#btn-prune-dry", Button).press()
            await pilot.pause()
            await pilot.pause()

            lines = _log_lines(app.query_one("#cleanup-log-output", RichLog))
            assert lines[0] == "Scanning runs for pruning (dry_run=True)..."
            assert "1 run(s) eligible for removal." in lines
            assert "[INFO ] Dry run: no files were deleted." in lines
            assert any(line.startswith("1   old00001") for line in lines)
            assert "RefreshSidebar" not in posts
            assert notes == []
            assert run_dir.exists()

        _run_app(runs, _body, monkeypatch)


# --------------------------------------------------------------------------- #
# E-14: copy_to_clipboard per platform
# --------------------------------------------------------------------------- #


class TestCopyToClipboard:
    def _patch(self, monkeypatch, platform, outcomes=None):
        calls = []
        outcomes = outcomes or {}

        def _run(cmd, input=None, text=None, check=None, timeout=None, stdout=None, stderr=None):
            calls.append((cmd, input, text, check, timeout, stdout, stderr))
            err = outcomes.get(cmd[0])
            if err is not None:
                raise err

        monkeypatch.setattr(actions_mod, "sys", types.SimpleNamespace(platform=platform))
        monkeypatch.setattr(
            actions_mod,
            "subprocess",
            types.SimpleNamespace(
                run=_run,
                DEVNULL=subprocess.DEVNULL,
                CalledProcessError=subprocess.CalledProcessError,
                TimeoutExpired=subprocess.TimeoutExpired,
            ),
        )
        return calls

    def test_darwin_uses_pbcopy(self, monkeypatch):
        calls = self._patch(monkeypatch, "darwin")
        assert copy_to_clipboard("hi") is True
        assert calls == [(["pbcopy"], "hi", True, True, 5, subprocess.DEVNULL, subprocess.DEVNULL)]

    def test_win32_uses_clip(self, monkeypatch):
        calls = self._patch(monkeypatch, "win32")
        assert copy_to_clipboard("hi") is True
        assert calls == [(["clip"], "hi", True, True, 5, subprocess.DEVNULL, subprocess.DEVNULL)]

    def test_linux_uses_wl_copy_first(self, monkeypatch):
        calls = self._patch(monkeypatch, "linux")
        assert copy_to_clipboard("hi") is True
        assert calls == [(["wl-copy"], "hi", True, True, 5, subprocess.DEVNULL, subprocess.DEVNULL)]

    def test_linux_falls_back_to_xclip_then_xsel(self, monkeypatch):
        calls = self._patch(
            monkeypatch,
            "linux",
            {
                "wl-copy": FileNotFoundError("no wl-copy"),
                "xclip": FileNotFoundError("no xclip"),
            },
        )
        assert copy_to_clipboard("hi") is True
        assert [cmd for cmd, *_ in calls] == [
            ["wl-copy"],
            ["xclip", "-selection", "clipboard"],
            ["xsel", "--clipboard", "--input"],
        ]

    def test_linux_all_missing_returns_false(self, monkeypatch):
        calls = self._patch(
            monkeypatch,
            "linux",
            {
                "wl-copy": FileNotFoundError("no wl-copy"),
                "xclip": subprocess.TimeoutExpired(["xclip"], 5),
                "xsel": subprocess.CalledProcessError(1, ["xsel"]),
            },
        )
        assert copy_to_clipboard("hi") is False
        assert len(calls) == 3

    def test_darwin_failure_and_timeout_return_false(self, monkeypatch):
        self._patch(monkeypatch, "darwin", {"pbcopy": FileNotFoundError("no pbcopy")})
        assert copy_to_clipboard("hi") is False
        self._patch(monkeypatch, "darwin", {"pbcopy": subprocess.TimeoutExpired(["pbcopy"], 5)})
        assert copy_to_clipboard("hi") is False


# --------------------------------------------------------------------------- #
# E-04: DiffView states
# --------------------------------------------------------------------------- #


class TestDiffViewStates:
    def _make_runs(self, tmp_path):
        runs = tmp_path / "runs"
        a = _write_run(runs, "diffa001", age=20, extra={"custom": {"x": 1}})
        b = _write_run(runs, "diffb002", age=10, extra={"custom": {"x": 2}})
        return runs, a, b

    def _select_pair(self, app, a, b):
        view = app.query_one("#diff-view", DiffView)
        view.query_one("#select-diff-a", Select).value = str(a)
        view.query_one("#select-diff-b", Select).value = str(b)
        return view

    def test_same_run_guard(self, tmp_path, monkeypatch):
        runs, a, _ = self._make_runs(tmp_path)

        async def _body(app, pilot, notes):
            await _show_tab(app, pilot, "tab-diff")
            self._select_pair(app, a, a)
            await pilot.pause()
            notes.clear()
            app.query_one("#btn-execute-diff", Button).press()
            await pilot.pause()

            assert _log_lines(app.query_one("#diff-output-area", RichLog)) == [
                "Warning: Cannot compare a run against itself."
            ]
            assert notes == [("Selected the same run for both parameters.", "warning")]

        _run_app(runs, _body, monkeypatch)

    @pytest.mark.parametrize("which", ["a", "b"])
    def test_missing_manifest(self, tmp_path, monkeypatch, which):
        runs, a, b = self._make_runs(tmp_path)
        missing_path = (a if which == "a" else b) / "manifest.json"
        label = which.upper()

        async def _body(app, pilot, notes):
            await _show_tab(app, pilot, "tab-diff")
            view = self._select_pair(app, a, b)
            await pilot.pause()
            missing_path.unlink()
            view.run_difference()
            await pilot.pause()

            assert _log_lines(app.query_one("#diff-output-area", RichLog)) == [
                f"Error: Manifest {label} not found at {missing_path}"
            ]

        _run_app(runs, _body, monkeypatch)

    def test_corrupt_manifest_reports_error(self, tmp_path, monkeypatch):
        runs, a, b = self._make_runs(tmp_path)

        async def _body(app, pilot, notes):
            await _show_tab(app, pilot, "tab-diff")
            view = self._select_pair(app, a, b)
            await pilot.pause()
            (b / "manifest.json").write_text("{not json", encoding="utf-8")
            view.run_difference()
            await pilot.pause()

            lines = _log_lines(app.query_one("#diff-output-area", RichLog))
            assert lines[0] == "Computing semantic difference..."
            assert lines[1].startswith("Error computing diff: Expecting property name")

        _run_app(runs, _body, monkeypatch)

    def test_execute_then_clear(self, tmp_path, monkeypatch):
        runs, a, b = self._make_runs(tmp_path)

        async def _body(app, pilot, notes):
            await _show_tab(app, pilot, "tab-diff")
            self._select_pair(app, a, b)
            await pilot.pause()
            app.query_one("#btn-execute-diff", Button).press()
            await pilot.pause()

            lines = _log_lines(app.query_one("#diff-output-area", RichLog))
            assert lines[0] == "=== PUBRUN SEMANTIC DIFFERENCE ==="
            assert "MODIFIED KEYS (~):" in lines
            assert "  ~ custom.x:" in lines
            assert "      - Old: 1" in lines
            assert "      + New: 2" in lines

            app.query_one("#btn-clear-diff", Button).press()
            await pilot.pause()
            assert _log_lines(app.query_one("#diff-output-area", RichLog)) == []

        _run_app(runs, _body, monkeypatch)

    def test_render_diff_report_branches(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"

        async def _body(app, pilot, notes):
            await _show_tab(app, pilot, "tab-diff")
            view = app.query_one("#diff-view", DiffView)
            view.render_diff_report(
                {
                    "added": {"extra.flag": True},
                    "removed": {"old.opt": "off"},
                    "modified": {
                        "env.PATH": {
                            "type": "path_split",
                            "added": ["/opt/bin"],
                            "removed": ["/usr/old"],
                        },
                        "pkg.ver": {
                            "old": "1.0",
                            "new": "1.1",
                            "note": "minor bump",
                        },
                    },
                    "same": {"run.id": "x"},
                },
                warnings=["parent missing"],
            )
            await pilot.pause()

            lines = _log_lines(app.query_one("#diff-output-area", RichLog))
            assert lines[0] == "[Warning] parent missing"
            assert "ADDED KEYS (+):" in lines
            assert "REMOVED KEYS (-):" in lines
            assert "MODIFIED KEYS (~):" in lines
            assert "UNCHANGED KEYS (=):" in lines
            assert "      + /opt/bin" in lines
            assert "      - /usr/old" in lines
            assert "      ! Note: minor bump" in lines
            assert "  = run.id: x" in lines

            view.render_diff_report({"same": {"run.id": "x"}})
            await pilot.pause()
            same_lines = _log_lines(app.query_one("#diff-output-area", RichLog))
            assert same_lines[-1] == "No differences detected between the selected runs."

        _run_app(runs, _body, monkeypatch)

    def test_show_same_checkbox_populates_unchanged_section(self, tmp_path, monkeypatch):
        runs, a, b = self._make_runs(tmp_path)

        async def _body(app, pilot, notes):
            await _show_tab(app, pilot, "tab-diff")
            view = self._select_pair(app, a, b)
            await pilot.pause()
            view.run_difference()
            await pilot.pause()
            assert "UNCHANGED KEYS (=):" not in _log_lines(
                app.query_one("#diff-output-area", RichLog)
            )

            view.query_one("#check-show-same", Checkbox).value = True
            await pilot.pause()
            view.run_difference()
            await pilot.pause()
            assert "UNCHANGED KEYS (=):" in _log_lines(
                app.query_one("#diff-output-area", RichLog)
            )

        _run_app(runs, _body, monkeypatch)

    def test_populate_dropdowns_keeps_valid_selection_and_drops_stale_one(self, tmp_path, monkeypatch):
        runs, a, b = self._make_runs(tmp_path)

        async def _body(app, pilot, notes):
            await pilot.pause()
            view = self._select_pair(app, a, b)
            await pilot.pause()

            all_runs = [RunInfo(a), RunInfo(b)]
            view.populate_dropdowns(all_runs)
            await pilot.pause()
            assert view.query_one("#select-diff-a", Select).value == str(a)
            assert view.query_one("#select-diff-b", Select).value == str(b)

            view.populate_dropdowns([RunInfo(a)])
            await pilot.pause()
            assert view.query_one("#select-diff-a", Select).value == str(a)
            assert view.query_one("#select-diff-b", Select).value == _SELECT_EMPTY_VALUE

        _run_app(runs, _body, monkeypatch)


# --------------------------------------------------------------------------- #
# E-15: LogViewer states
# --------------------------------------------------------------------------- #


class TestLogViewerStates:
    def test_missing_dir_and_dir_without_logs(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        empty_run = _write_run(runs, "nolog001")

        async def _body(app, pilot, notes):
            await _show_tab(app, pilot, "tab-logs")
            viewer = app.query_one("#logs-view", LogViewer)
            log_area = viewer.query_one("#log-content-area", RichLog)

            viewer.display_run_logs(tmp_path / "does-not-exist")
            await pilot.pause()
            assert viewer.log_files == []
            assert _log_lines(log_area) == []

            viewer.display_run_logs(empty_run)
            await pilot.pause()
            lines = _log_lines(log_area)
            assert lines[0] == "No log files found in this run directory."
            joined = "\n".join(lines)
            assert '[console].capture_mode = "standard"' in joined
            assert "import pubrun.full" in joined

        _run_app(runs, _body, monkeypatch)

    def test_select_switches_file_and_wrap_toggles(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        run_dir = _write_run(
            runs,
            "logs0002",
            logs={"console.log": "from console\n", "stderr.txt": "from stderr\n"},
        )

        async def _body(app, pilot, notes):
            await _show_tab(app, pilot, "tab-logs")
            viewer = app.query_one("#logs-view", LogViewer)
            log_area = viewer.query_one("#log-content-area", RichLog)
            select = viewer.query_one("#select-log-file", Select)

            viewer.display_run_logs(run_dir)
            await pilot.pause()
            assert select.value == str(run_dir / "console.log")

            select.value = str(run_dir / "stderr.txt")
            await pilot.pause()
            lines = _log_lines(log_area)
            assert "from stderr" in lines
            assert "from console" not in lines

            assert log_area.wrap is False
            viewer.query_one("#btn-toggle-wrap", Button).press()
            await pilot.pause()
            assert log_area.wrap is True
            viewer.query_one("#btn-toggle-wrap", Button).press()
            await pilot.pause()
            assert log_area.wrap is False

        _run_app(runs, _body, monkeypatch)

    def test_missing_and_unreadable_log_file(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        unreadable_dir = tmp_path / "a_directory.log"
        unreadable_dir.mkdir()

        async def _body(app, pilot, notes):
            await _show_tab(app, pilot, "tab-logs")
            viewer = app.query_one("#logs-view", LogViewer)
            log_area = viewer.query_one("#log-content-area", RichLog)

            viewer.load_log_file(str(tmp_path / "missing.log"))
            await pilot.pause()
            assert _log_lines(log_area) == ["Selected log file does not exist."]

            viewer.load_log_file(str(unreadable_dir))
            await pilot.pause()
            lines = _log_lines(log_area)
            assert len(lines) == 1
            assert lines[0].startswith("Failed to load log file: ")

        _run_app(runs, _body, monkeypatch)


# --------------------------------------------------------------------------- #
# E-05: ConfigPanel states and dict_to_toml types
# --------------------------------------------------------------------------- #


class TestConfigPanelStates:
    def test_reset_reloads_resolved_values(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"

        async def _body(app, pilot, notes):
            await pilot.pause()
            panel = app.query_one("#config-view", ConfigPanel)
            out_input = panel.query_one("#cfg-output-dir", Input)
            out_input.value = "./elsewhere/"
            await pilot.pause()
            notes.clear()
            panel.query_one("#btn-reset-config", Button).press()
            await pilot.pause()

            assert out_input.value == ""
            assert notes == [("Settings reloaded to current resolved values.", "information")]
            assert not (tmp_path / ".pubrun.toml").exists()

        _run_app(runs, _body, monkeypatch)

    def test_write_error_is_reported(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        (tmp_path / ".pubrun.toml").mkdir()

        async def _body(app, pilot, notes):
            await pilot.pause()
            panel = app.query_one("#config-view", ConfigPanel)
            notes.clear()
            panel.query_one("#btn-save-config", Button).press()
            await pilot.pause()

            assert [sev for _, sev in notes] == ["error"]
            assert notes[0][0].startswith("Failed to write configuration: ")

        res = _run_app(runs, _body, monkeypatch)
        assert res["running"] is True


class TestDictToToml:
    def test_scalar_types_and_sections_round_trip(self):
        data = {
            "a": 1.5,
            "b": [1, "x", True],
            "f": False,
            "n": 3,
            "empty": {},
            "g": {"h": {"i": 1}, "e": {}},
        }
        out = dict_to_toml(data)
        assert out.splitlines()[:4] == [
            "a = 1.5",
            'b = [1, "x", true]',
            "f = false",
            "n = 3",
        ]
        assert "[g.h]" in out
        assert "[empty]" not in out
        assert "[g.e]" not in out
        assert tomllib.loads(out) == {
            "a": 1.5,
            "b": [1, "x", True],
            "f": False,
            "n": 3,
            "g": {"h": {"i": 1}},
        }


# --------------------------------------------------------------------------- #
# E-18: dict_to_toml escaping and Save Settings round trip
# --------------------------------------------------------------------------- #


class TestTomlEscaping:
    @pytest.mark.parametrize(
        "value",
        [
            'say "hi"',
            "C:\\path\\to",
            "line1\nline2",
            "tab\there",
            "bell\x07",
            "del\x7f",
            "caf\u00e9 \U0001F600",
        ],
    )
    def test_strings_round_trip(self, value):
        parsed = tomllib.loads(dict_to_toml({"core": {"k": value}}))
        assert parsed == {"core": {"k": value}}

    @pytest.mark.parametrize(
        "value",
        [
            ["a\nb", "\U0001F600"],
            ["x\x7f"],
        ],
    )
    def test_string_lists_round_trip(self, value):
        parsed = tomllib.loads(dict_to_toml({"core": {"k": value}}))
        assert parsed == {"core": {"k": value}}

    def test_save_keeps_unrelated_non_bmp_list_value_loadable(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        (tmp_path / ".pubrun.toml").write_text(
            '[core]\noutput_dir = "./myruns"\n\n'
            '[diff]\nignore_basic = ["caf\\u00e9 \\U0001F600"]\n',
            encoding="utf-8",
        )

        async def _body(app, pilot, notes):
            await pilot.pause()
            panel = app.query_one("#config-view", ConfigPanel)
            notes.clear()
            panel.query_one("#btn-save-config", Button).press()
            await pilot.pause()

            assert notes[0] == ("Configuration saved to: .pubrun.toml", "information")

        _run_app(runs, _body, monkeypatch)
        loaded = load_local_config(tmp_path)
        assert loaded is not None
        assert loaded["diff"]["ignore_basic"] == ["caf\u00e9 \U0001F600"]
        assert loaded["core"]["output_dir"] == "./myruns"


# --------------------------------------------------------------------------- #
# E-16: RunDetailsView git section and degraded states
# --------------------------------------------------------------------------- #


class TestRunDetailsGit:
    @pytest.mark.parametrize(
        "remote_url, expected",
        [
            (None, "-"),
            ("https://example.com/repo", "https://example.com/repo"),
            ({"representation": "unavailable"}, "-"),
            ({"representation": "plain", "value": None}, "-"),
            ({"representation": "plain", "value": "git@host:r.git"}, "git@host:r.git"),
            (
                {"representation": "plain", "value": "https://user:[REDACTED]@h/r.git"},
                "https://user:[REDACTED]@h/r.git",
            ),
            (
                {"representation": "plain", "value": "https://h/[/x]"},
                "https://h/[/x]",
            ),
        ],
    )
    def test_remote_url_shapes(self, tmp_path, monkeypatch, remote_url, expected):
        run_dir = _write_run(
            tmp_path / "runs",
            "git00001",
            extra={"git": {"commit": "c" * 40, "remote_url": remote_url}},
        )
        lines = _render_details(tmp_path, run_dir, monkeypatch).splitlines()
        assert f"  Remote URL:     {expected}" in lines
        assert f"  Commit Hash:   {'c' * 40}" in lines

    def test_missing_remote_url_key(self, tmp_path, monkeypatch):
        run_dir = _write_run(
            tmp_path / "runs",
            "git00002",
            extra={"git": {"commit": "c" * 40}},
        )
        lines = _render_details(tmp_path, run_dir, monkeypatch).splitlines()
        assert "  Remote URL:     -" in lines

    def test_branch_and_commit_markup_is_shown_literally(self, tmp_path, monkeypatch):
        run_dir = _write_run(
            tmp_path / "runs",
            "git00003",
            extra={"git": {"commit": "[bold]c0ffee", "branch": "feat/[wip]"}},
        )
        lines = _render_details(tmp_path, run_dir, monkeypatch).splitlines()
        assert "  Commit Hash:   [bold]c0ffee" in lines
        assert "  Branch:        feat/[wip]" in lines

    def test_unbalanced_closing_tag_in_branch_does_not_raise(self, tmp_path, monkeypatch):
        run_dir = _write_run(
            tmp_path / "runs",
            "git00004",
            extra={"git": {"commit": "c" * 40, "branch": "[/bad]"}},
        )
        lines = _render_details(tmp_path, run_dir, monkeypatch).splitlines()
        assert "  Branch:        [/bad]" in lines

    @pytest.mark.parametrize("git_val", [None, ["x"], "abc"])
    def test_non_dict_git_section_falls_back_to_lock_fields(self, tmp_path, monkeypatch, git_val):
        runs = tmp_path / "runs"
        run_dir = _write_run(runs, "git00005", extra={"git": git_val})
        (run_dir / ".pubrun.lock").write_text(
            json.dumps(
                {
                    "pid": 999999,
                    "run_id": "git00005",
                    "hostname": "elsewhere-host",
                    "cwd": "/tmp/[work]",
                    "started_at_utc": time.time(),
                }
            ),
            encoding="utf-8",
        )
        lines = _render_details(tmp_path, run_dir, monkeypatch).splitlines()
        idx = lines.index("=== REPOSITORY PROVENANCE (GIT) ===")
        assert lines[idx + 1 : idx + 3] == [
            "  Commit Hash:   -",
            "  Working Cwd:   /tmp/[work]",
        ]


class TestRunDetailsStates:
    def test_degraded_run_without_manifest_or_lock(self, tmp_path, monkeypatch):
        run_dir = tmp_path / "runs" / "pubrun-empty001"
        run_dir.mkdir(parents=True)
        lines = _render_details(tmp_path, run_dir, monkeypatch).splitlines()
        assert "  Status:        CRASHED" in lines
        assert "  (No resource metadata recorded)" in lines
        assert "  (No git information available)" in lines

    def test_assess_run_failure_falls_back(self, tmp_path, monkeypatch):
        from pubrun.report import reproducibility as repro_mod

        def _boom(*args, **kwargs):
            raise RuntimeError("assessment failed")

        monkeypatch.setattr(repro_mod, "assess_run", _boom)
        run_dir = _write_run(tmp_path / "runs", "repro001")
        lines = _render_details(tmp_path, run_dir, monkeypatch).splitlines()
        idx = lines.index("=== REPRODUCIBILITY & EVIDENCE ===")
        assert lines[idx + 1] == "  (Reproducibility assessment unavailable for this run)"

    def test_refresh_live_metrics_reloads_running_run_only(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        live_dir = runs / "pubrun-live0001"
        live_dir.mkdir(parents=True)
        lock_path = live_dir / ".pubrun.lock"
        lock_payload = {
            "pid": 999999,
            "run_id": "live0001",
            "script": "train.py",
            "argv": ["--step", "1"],
            "hostname": "elsewhere-host",
            "started_at_utc": time.time(),
        }
        lock_path.write_text(json.dumps(lock_payload), encoding="utf-8")
        done_dir = _write_run(runs, "done0001")

        async def _body(app, pilot, notes):
            details = app.query_one("#details-view", RunDetailsView)
            details.display_run(RunInfo(live_dir))
            await pilot.pause()
            assert "  Arguments:     --step 1" in _general_text(app).splitlines()

            lock_payload["argv"] = ["--step", "2"]
            lock_path.write_text(json.dumps(lock_payload), encoding="utf-8")
            details.refresh_live_metrics()
            await pilot.pause()
            assert "  Arguments:     --step 2" in _general_text(app).splitlines()

            seen = []

            def _fail_run_info(path, **kwargs):
                seen.append((path, kwargs))
                raise OSError("transient read error")

            monkeypatch.setattr(details_mod, "RunInfo", _fail_run_info)
            details.refresh_live_metrics()
            await pilot.pause()
            assert seen == [(live_dir, {"keep_manifest": False})]
            assert "  Arguments:     --step 2" in _general_text(app).splitlines()

            seen.clear()
            details.run_info = RunInfo(done_dir)
            details.refresh_live_metrics()
            await pilot.pause()
            assert seen == []

        _run_app(runs, _body, monkeypatch)


# --------------------------------------------------------------------------- #
# E-17: RunResourcesView states
# --------------------------------------------------------------------------- #


class TestRunResourcesStates:
    def test_corrupt_events_file_shows_no_samples(self, tmp_path, monkeypatch):
        runs = tmp_path / "runs"
        run_dir = _write_run(
            runs,
            "res00001",
            logs={"events.jsonl": "{broken\nnot json at all\n"},
        )

        async def _body(app, pilot, notes):
            view = app.query_one("#resources-view", RunResourcesView)
            view.display_run(RunInfo(run_dir))
            await pilot.pause()
            assert str(app.query_one("#resources-body").render()).startswith(
                "No resource samples recorded for this run"
            )

        _run_app(runs, _body, monkeypatch)

    def test_reader_exception_is_rendered_not_raised(self, tmp_path, monkeypatch):
        from pubrun.report import diagnostics as diag_mod

        def _boom(_path):
            raise RuntimeError("bad series")

        monkeypatch.setattr(diag_mod, "read_resource_series", _boom)
        runs = tmp_path / "runs"
        run_dir = _write_run(runs, "res00002", logs={"events.jsonl": ""})

        async def _body(app, pilot, notes):
            view = app.query_one("#resources-view", RunResourcesView)
            view.display_run(RunInfo(run_dir))
            await pilot.pause()
            assert (
                str(app.query_one("#resources-body").render())
                == "Could not render resource usage: RuntimeError: bad series"
            )

        _run_app(runs, _body, monkeypatch)


# --------------------------------------------------------------------------- #
# 3q5rd5: Bulk prune modal + stderr capture, safe_delete_run_dir, hydration,
#         in-memory sidebar, lazy tabs, keybindings, and atomic ConfigPanel
# --------------------------------------------------------------------------- #


class TestBulkPruneConfirmationAndStderr:
    def test_execute_prune_opens_modal_cancel_preserves_confirm_deletes_and_captures_stderr(
        self, tmp_path, monkeypatch, capsys
    ):
        from pubrun.tui.widgets.actions import ConfirmBulkPruneModal

        runs = tmp_path / "runs"
        old1 = _write_run(runs, "prun0001", age=30 * 86400, logs={"stdout.log": "A" * 2048})
        old2 = _write_run(runs, "prun0002", age=40 * 86400, logs={"stdout.log": "B" * 2048})
        recent = _write_run(runs, "keep0001", age=60)

        real_clean = actions_mod.clean_runs

        def _clean_with_stderr(*args, **kwargs):
            import sys as _sys

            print("Simulated stderr warning from clean_runs", file=_sys.stderr)
            return real_clean(*args, **kwargs)

        monkeypatch.setattr(actions_mod, "clean_runs", _clean_with_stderr)

        async def _body(app, pilot, notes):
            await _show_tab(app, pilot, "tab-actions")
            panel = app.query_one("#actions-view", ActionsPanel)

            # 1. Invalid age reports error and does NOT open modal.
            panel.query_one("#input-clean-older", Input).value = "2w"
            await pilot.pause()
            notes.clear()
            panel.query_one("#btn-prune-execute", Button).press()
            await pilot.pause()
            assert not isinstance(app.screen, ConfirmBulkPruneModal)
            assert any(sev == "error" for _, sev in notes)

            # 2. Zero matching runs notifies without opening modal.
            panel.query_one("#input-clean-older", Input).value = "365d"
            await pilot.pause()
            notes.clear()
            panel.query_one("#btn-prune-execute", Button).press()
            await pilot.pause()
            assert not isinstance(app.screen, ConfirmBulkPruneModal)
            assert any("No runs match" in msg for msg, _ in notes)

            # 3. Valid criteria opens modal with exact count & disk size; cancel deletes nothing.
            panel.query_one("#input-clean-older", Input).value = "7d"
            await pilot.pause()
            panel.query_one("#btn-prune-execute", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, ConfirmBulkPruneModal)
            modal = app.screen
            assert modal.matched_count == 2
            assert modal.total_size_bytes >= 4096
            rendered = " ".join(str(lbl.render()) for lbl in modal.query("Label"))
            assert "2 run(s)" in rendered

            modal.query_one("#btn-cancel-bulk-prune", Button).press()
            await pilot.pause()
            assert not isinstance(app.screen, ConfirmBulkPruneModal)
            assert old1.exists() and old2.exists() and recent.exists()

            # 4. Re-open and confirm -> deletes old1/old2, keeps recent, captures stderr cleanly.
            panel.query_one("#btn-prune-execute", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, ConfirmBulkPruneModal)
            app.screen.query_one("#btn-confirm-bulk-prune", Button).press()
            await pilot.pause()
            await pilot.pause()

            assert not old1.exists()
            assert not old2.exists()
            assert recent.exists()
            log_text = "\n".join(_log_lines(panel.query_one("#cleanup-log-output", RichLog)))
            assert "Simulated stderr warning from clean_runs" in log_text

        _run_app(runs, _body, monkeypatch)
        # No raw stderr bled outside the TUI.
        assert "Simulated stderr warning from clean_runs" not in capsys.readouterr().err


class TestSafeDeleteGuardsAndLabels:
    def test_handle_deletion_and_archive_delete_raw_refuse_symlink_escape_and_remote_lock(
        self, tmp_path, monkeypatch
    ):
        import os

        runs = tmp_path / "runs"
        runs.mkdir(parents=True)

        # 1. Symlink run directory
        real_target = tmp_path / "outside_real"
        real_target.mkdir()
        (real_target / "secret.txt").write_text("keep", encoding="utf-8")
        sym_dir = runs / "pubrun-sym00001"
        sym_dir.symlink_to(real_target)
        sym_info = RunInfo(sym_dir, keep_manifest=False)

        # 2. Out-of-output-dir path
        outside_run = _write_run(tmp_path / "other_runs", "esc00001")
        outside_info = RunInfo(outside_run, keep_manifest=False)

        # 3. Remote-locked run directory
        remote_dir = _write_run(runs, "rem00001")
        (remote_dir / ".pubrun.lock").write_text(
            json.dumps(
                {
                    "pid": 424242,
                    "run_id": "rem00001",
                    "hostname": "other-hpc-node-never-local",
                    "started_at_utc": time.time(),
                }
            ),
            encoding="utf-8",
        )
        remote_info = RunInfo(remote_dir, keep_manifest=False)

        # 4. Active local-locked run directory
        active_dir = _write_run(runs, "act00001")
        (active_dir / ".pubrun.lock").write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "run_id": "act00001",
                    "script": "train.py",
                    "hostname": "",
                    "started_at_utc": time.time(),
                }
            ),
            encoding="utf-8",
        )
        from pubrun import status as status_mod

        monkeypatch.setattr(status_mod, "is_same_process", lambda pid, *a, **kw: pid == os.getpid())
        active_info = RunInfo(active_dir, keep_manifest=False)

        async def _body(app, pilot, notes):
            await _show_tab(app, pilot, "tab-actions")
            panel = app.query_one("#actions-view", ActionsPanel)

            # Check archive destination label and cleanup hints
            dest_text = str(panel.query_one("#lbl-archive-dest").render())
            assert "<output_dir>/archive/<run_id>.zip" in dest_text
            hint_text = str(panel.query_one("#lbl-cleanup-hints").render())
            for st in ("completed", "failed", "interrupted", "broken pipe", "running", "crashed", "ghost"):
                assert st in hint_text

            # Verify handle_deletion_result refuses all 4 unsafe targets and keeps run_info intact.
            for unsafe_info in (sym_info, outside_info, remote_info, active_info):
                panel.display_run(unsafe_info)
                await pilot.pause()
                notes.clear()
                panel.handle_deletion_result(True)
                await pilot.pause()
                assert any(sev == "error" and msg.startswith("Deletion failed: ") for msg, sev in notes)
                assert panel.run_info is unsafe_info
                assert unsafe_info.run_dir.exists()

            # Verify archive_selected_run(delete_raw=True) also enforces safe_delete_run_dir.
            panel.query_one("#check-delete-raw", Checkbox).value = True
            for unsafe_info in (outside_info, remote_info, active_info):
                panel.display_run(unsafe_info)
                await pilot.pause()
                notes.clear()
                panel.archive_selected_run()
                await pilot.pause()
                assert any(sev == "error" and msg.startswith("Deletion failed: ") for msg, sev in notes)
                assert unsafe_info.run_dir.exists()

            assert real_target.exists() and (real_target / "secret.txt").exists()

        _run_app(runs, _body, monkeypatch)


class TestHydrationSidebarLazyAndKeybindings:
    def test_hpc_meta_ref_hydration_once_dirty_none_pkg_search_and_actions_under_keep_manifest_false(
        self, tmp_path, monkeypatch
    ):
        from textual.widgets import DataTable
        from pubrun.report import utils as report_utils

        runs = tmp_path / "runs"
        child_dir = runs / "pubrun-hpc00001"
        child_dir.mkdir(parents=True)
        # Parent meta.json inside child run dir (allowed under default confinement).
        (child_dir / "meta.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "manifest_type": "pubrun-meta-snapshot",
                    "host": {
                        "hostname": "hpc-node-42",
                        "os_name": "Linux",
                        "os_release": "6.6.0",
                        "capture_state": {"status": "complete"},
                    },
                    "hardware": {
                        "cpu": {"model": "AMD EPYC 9654", "logical_cores": 96, "architecture": "x86_64"},
                        "memory_total_bytes": 512 * 1024**3,
                        "capture_state": {"status": "complete"},
                    },
                    "git": {
                        "commit": "deadbeef" * 5,
                        "branch": "hpc-main",
                        "dirty": None,
                        "capture_state": {"status": "complete"},
                    },
                    "packages": {
                        "records": [
                            {"name": "numpy", "version": "1.26.4", "editable": False},
                            {"name": "scipy", "version": "1.13.0", "editable": False},
                        ],
                        "capture_state": {"status": "complete"},
                    },
                }
            ),
            encoding="utf-8",
        )
        (child_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "meta_ref": "meta.json",
                    "run": {"run_id": "hpc00001"},
                    "status": {"outcome": "completed", "exit_code": 0},
                    "timing": {"started_at_utc": time.time() - 10, "elapsed_seconds": 2.0},
                    "invocation": {
                        "script": {"basename": "hpc_train.py"},
                        "argv": ["hpc_train.py", "--batch", "64"],
                        "rerun_command": "python hpc_train.py --batch 64",
                    },
                    "host": {"capture_state": {"status": "suppressed"}},
                    "hardware": {"capture_state": {"status": "suppressed"}},
                    "git": {"capture_state": {"status": "suppressed"}},
                    "packages": {"capture_state": {"status": "suppressed"}},
                }
            ),
            encoding="utf-8",
        )

        other_dir = _write_run(
            runs,
            "hpc00002",
            script="other.py",
            age=100,
            extra={
                "git": {"commit": "1" * 40, "branch": "main", "dirty": False},
                "packages": {
                    "records": [
                        {"name": "numpy", "version": "2.0.0", "editable": False},
                        {"name": "pandas", "version": "2.2.0", "editable": False},
                    ]
                },
            },
        )

        hydrate_calls = []
        real_hydrate = report_utils.hydrate_manifest_with_report

        def _spy_hydrate(path, manifest):
            hydrate_calls.append(path)
            return real_hydrate(path, manifest)

        monkeypatch.setattr(report_utils, "hydrate_manifest_with_report", _spy_hydrate)

        async def _body(app, pilot, notes):
            await pilot.pause()
            # Auto-selected newest run (hpc00001) on mount with keep_manifest=False.
            assert app.selected_run_info is not None
            assert app.selected_run_info.run_id == "hpc00001"
            assert app.selected_run_info.manifest is None
            # Hydrated exactly ONCE per display_run!
            assert len(hydrate_calls) == 1

            gen = _general_text(app)
            assert "AMD EPYC 9654" in gen
            assert "hpc-node-42" in gen
            assert "hpc-main" in gen
            assert "Repo Dirty:     not checked" in gen

            # Hydrated parent packages are populated in #packages-table.
            pkg_table = app.query_one("#packages-table", DataTable)
            assert pkg_table.row_count == 2

            # Set #pkg-search filter and switch runs -> filter reapplies automatically.
            details = app.query_one("#details-view", RunDetailsView)
            details.query_one("#pkg-search", Input).value = "numpy"
            await pilot.pause()
            assert pkg_table.row_count == 1

            details.display_run(RunInfo(other_dir, keep_manifest=False))
            await pilot.pause()
            assert pkg_table.row_count == 1
            assert pkg_table.get_row_at(0)[0] == "numpy"
            assert pkg_table.get_row_at(0)[1] == "2.0.0"
            assert "Repo Dirty:     False" in _general_text(app)

            # Switch back to hpc00001 and activate Actions tab -> citations work under keep_manifest=False.
            app._select_run(RunInfo(child_dir, keep_manifest=False))
            await _show_tab(app, pilot, "tab-actions")
            actions = app.query_one("#actions-view", ActionsPanel)
            assert actions.rerun_command == "python hpc_train.py --batch 64"
            assert actions.raw_manifest is not None
            citation_text = str(actions.query_one("#lbl-methods-citation").render())
            assert "AMD EPYC 9654" in citation_text

        _run_app(runs, _body, monkeypatch)

    def test_in_memory_search_zero_scans_args_status_leaf_nodes_and_onboarding(self, tmp_path, monkeypatch):
        # 1. Zero-run onboarding guidance
        empty_runs = tmp_path / "empty_runs"

        async def _empty_body(app, pilot, notes):
            await pilot.pause()
            gen = _general_text(app)
            assert "import pubrun" in gen
            assert "pubrun init" in gen

        _run_app(empty_runs, _empty_body, monkeypatch)

        # 2. In-memory search with zero disk scans, matching args & status, and leaf nodes
        runs = tmp_path / "runs"
        _write_run(
            runs,
            "srch0001",
            script="train.py",
            age=10,
            extra={
                "invocation": {
                    "script": {"basename": "train.py"},
                    "argv": ["train.py", "--lr", "0.001", "--model", "resnet"],
                }
            },
        )
        _write_run(
            runs,
            "srch0002",
            script="eval.py",
            age=20,
            extra={"status": {"outcome": "failed", "exit_code": 1}},
        )

        scan_calls = []
        real_scan = sidebar_mod.scan_runs

        def _spy_scan(*args, **kwargs):
            scan_calls.append((args, kwargs))
            return real_scan(*args, **kwargs)

        monkeypatch.setattr(sidebar_mod, "scan_runs", _spy_scan)

        async def _body(app, pilot, notes):
            await pilot.pause()
            # Exactly 1 scan on mount, using keep_manifest=False.
            assert len(scan_calls) == 1
            assert scan_calls[0][1].get("keep_manifest") is False

            tree = app.query_one("#runs-tree", Tree)
            assert all(child.allow_expand is False for child in tree.root.children)

            search = app.query_one("#runs-search", Input)
            search.value = "resnet"
            await pilot.pause()
            assert _tree_labels(app) == ["train.py [srch0001] • COMPLETED"]

            search.value = "FAILED"
            await pilot.pause()
            assert _tree_labels(app) == ["eval.py [srch0002] • FAILED"]

            search.value = ""
            await pilot.pause()
            assert len(_tree_labels(app)) == 2

            # Zero additional scan_runs() calls during typing!
            assert len(scan_calls) == 1

        _run_app(runs, _body, monkeypatch)

    def test_keybindings_project_config_tab_and_yield_to_focused_input(self, tmp_path, monkeypatch):
        from pubrun.tui.app import KeybindHelpModal

        runs = tmp_path / "runs"
        _write_run(runs, "keys0001", script="train.py", age=10)

        async def _body(app, pilot, notes):
            await pilot.pause()
            tabs = app.query_one("#workspace-tabs", TabbedContent)

            # Tab 6 is renamed from "TUI Settings" to "Project Config".
            cfg_tab = tabs.get_tab("tab-config")
            assert str(cfg_tab.label) == "Project Config"

            # Unfocused number keys 2..6 and 1 switch tabs.
            await pilot.press("2")
            await pilot.pause()
            assert tabs.active == "tab-logs"

            await pilot.press("6")
            await pilot.pause()
            assert tabs.active == "tab-config"

            await pilot.press("1")
            await pilot.pause()
            assert tabs.active == "tab-details"

            # '?' opens KeybindHelpModal when unfocused.
            await pilot.press("?")
            await pilot.pause()
            assert isinstance(app.screen, KeybindHelpModal)
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, KeybindHelpModal)

            # '/' focuses #runs-search; once focused, 1-6, /, ? go into the Input, NOT bindings!
            await pilot.press("/")
            await pilot.pause()
            search = app.query_one("#runs-search", Input)
            assert app.focused is search

            await pilot.press("2", "?", "/")
            await pilot.pause()
            assert tabs.active == "tab-details"
            assert not isinstance(app.screen, KeybindHelpModal)
            assert search.value == "2?/"

        _run_app(runs, _body, monkeypatch)


class TestConfigPanelHardening:
    def test_target_path_imports_mode_regex_rejection_nondict_guard_and_sidebar_refresh(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        runs_a = tmp_path / "runs_a"
        runs_b = tmp_path / "runs_b"
        _write_run(runs_a, "aaaa1111", script="a.py")
        _write_run(runs_b, "bbbb2222", script="b.py")

        # Write a .pubrun.toml with a non-dict section ("events" as scalar) to verify guard.
        (tmp_path / ".pubrun.toml").write_text(
            '[core]\noutput_dir = "runs_a"\n\n[imports]\nmode = "noauto"\n\nevents = "broken"\n',
            encoding="utf-8",
        )

        async def _drive():
            # Unpinned output_dir=None (no explicit --dir) so changing output_dir refreshes sidebar!
            app = PubrunTUIApp(output_dir=None)
            notes = _capture_notifications(app, monkeypatch)
            async with app.run_test() as pilot:
                await _show_tab(app, pilot, "tab-config")
                panel = app.query_one("#config-view", ConfigPanel)
                sidebar = app.query_one("#sidebar", RunsSidebar)
                assert [r.run_id for r in sidebar.all_runs] == ["aaaa1111"]

                # Target path header displays resolved .pubrun.toml
                header_text = str(panel.query_one("#cfg-target-path").render())
                assert str(tmp_path / ".pubrun.toml") in header_text

                # [imports].mode initialized from resolved config + precedence hint present
                imports_sel = panel.query_one("#cfg-imports-mode", Select)
                assert imports_sel.value == "noauto"
                assert "takes precedence" in str(panel.query_one("#cfg-imports-mode-hint").render())

                # Invalid regex aborts save, notifies error, preserves user input AND disk file!
                regex_input = panel.query_one("#cfg-sensitive-regex", Input)
                orig_disk = (tmp_path / ".pubrun.toml").read_text(encoding="utf-8")
                regex_input.value = "[unclosed"
                await pilot.pause()
                notes.clear()
                panel.save_settings()
                await pilot.pause()
                assert any(sev == "error" and "regex" in msg.lower() for msg, sev in notes)
                assert regex_input.value == "[unclosed"
                assert (tmp_path / ".pubrun.toml").read_text(encoding="utf-8") == orig_disk

                # Fix regex, switch imports.mode and output_dir -> saves atomically and refreshes sidebar!
                regex_input.value = "(?i)token"
                imports_sel.value = "minimal"
                panel.query_one("#cfg-output-dir", Input).value = "runs_b"
                await pilot.pause()
                notes.clear()
                panel.save_settings()
                await pilot.pause()
                await pilot.pause()

                assert notes[0] == ("Configuration saved to: .pubrun.toml", "information")
                # No leftover .tmp files in tmp_path
                assert not list(tmp_path.glob("*.tmp"))
                # Saved TOML parses cleanly and preserves non-dict section recovery
                saved = tomllib.loads((tmp_path / ".pubrun.toml").read_text(encoding="utf-8"))
                assert saved["imports"]["mode"] == "minimal"
                assert saved["core"]["output_dir"] == "runs_b"
                assert saved["events"]["enabled"] is True
                assert saved["redaction"]["sensitive_keys_regex"] == "(?i)token"
                # Sidebar refreshed to runs_b!
                assert [r.run_id for r in sidebar.all_runs] == ["bbbb2222"]

        asyncio.run(_drive())

    def test_atomic_write_cleans_up_temp_file_on_replace_failure(self, tmp_path, monkeypatch):
        from pubrun.tui.widgets import config as config_mod

        def _boom(_src, _dst):
            raise OSError("simulated replace failure")

        monkeypatch.setattr(config_mod.os, "replace", _boom)
        target = tmp_path / ".pubrun.toml"
        with pytest.raises(OSError, match="simulated replace failure"):
            config_mod._atomic_write_text(target, "[core]\nauto_start = true\n")
        assert not target.exists()
        assert not list(tmp_path.glob("*.tmp"))
