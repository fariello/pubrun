"""In-process seam tests for pubrun.__main__ (argv injection, preprocessing, and DiagnosticsError)."""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

import pubrun.status as status_mod
from pubrun.__main__ import _apply_global_flags, _preprocess_argv, main


def _good_manifest(
    run_id: str = "aaaa1111",
    started_at: float = 1000.0,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    manifest: Dict[str, Any] = {
        "schema_version": "1.0",
        "manifest_type": "pubrun-manifest",
        "run": {"run_id": run_id},
        "status": {"outcome": "completed"},
        "invocation": {"argv": ["train.py"], "script": {"basename": "train.py"}},
        "timing": {"started_at_utc": started_at, "ended_at_utc": started_at + 60.0},
        "signals": {"exit_code": 0},
        "resources": {"peak_rss_bytes": 2097152, "peak_cpu_percent": 25.0},
    }
    if extra:
        manifest.update(extra)
    return manifest


def _write_run(
    runs_dir: Path,
    dirname: str,
    manifest: Optional[Dict[str, Any]] = None,
    raw_manifest: Optional[str] = None,
    events: Optional[List[Dict[str, Any]]] = None,
) -> Path:
    run_dir = runs_dir / dirname
    run_dir.mkdir(parents=True, exist_ok=True)
    if raw_manifest is not None:
        (run_dir / "manifest.json").write_text(raw_manifest, encoding="utf-8")
    elif manifest is not None:
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if events is not None:
        with open(run_dir / "events.jsonl", "w", encoding="utf-8") as ef:
            for ev in events:
                ef.write(json.dumps(ev) + "\n")
    return run_dir


class TestPreprocessArgv:
    """Pure unit tests for _preprocess_argv() verifying returned lists, flags, and immutability."""

    _SUBCOMMANDS = {"status", "run", "show", "cpu"}

    @pytest.mark.parametrize(
        "raw_argv,expected_argv,expected_no_color",
        [
            (["pubrun", "--no-color", "status"], ["pubrun", "status"], True),
            (["pubrun", "status", "--no-color"], ["pubrun", "status"], True),
            (
                ["pubrun", "--no-color", "run", "--", "python", "x.py", "--no-color"],
                ["pubrun", "run", "--", "python", "x.py", "--no-color"],
                True,
            ),
            (
                ["pubrun", "run", "--", "prog", "--no-color"],
                ["pubrun", "run", "--", "prog", "--no-color"],
                False,
            ),
            (
                ["pubrun", "abc", "cpu", "--last", "1m"],
                ["pubrun", "cpu", "abc", "--last", "1m"],
                False,
            ),
            (["pubrun", "--no-color", "abc", "show"], ["pubrun", "show", "abc"], True),
            (["pubrun", "help", "status"], ["pubrun", "status", "--help"], False),
            (["pubrun", "help", "bogus"], ["pubrun", "--help"], False),
            (["pubrun", "help"], ["pubrun", "--help"], False),
            (["pubrun", "status", "help"], ["pubrun", "status", "--help"], False),
            (["pubrun"], ["pubrun"], False),
        ],
        ids=[
            "no-color-before-subcommand",
            "no-color-after-subcommand",
            "no-color-before-and-inside-run",
            "no-color-only-inside-run",
            "leading-run-id-before-subcommand",
            "no-color-and-leading-run-id",
            "help-before-known-subcommand",
            "help-before-unknown-subcommand",
            "bare-help",
            "help-after-subcommand",
            "prog-only",
        ],
    )
    def test_preprocess_argv_cases(self, raw_argv, expected_argv, expected_no_color):
        original = list(raw_argv)
        rewritten, no_color_present = _preprocess_argv(raw_argv, self._SUBCOMMANDS)
        assert rewritten == expected_argv
        assert no_color_present is expected_no_color
        assert raw_argv == original
        assert rewritten is not raw_argv


class TestMainArgv:
    """In-process tests driving main(argv) without mutating sys.argv."""

    def test_main_argv_does_not_touch_sys_argv(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")
        runs = tmp_path / "runs"
        _write_run(runs, "pubrun-aaaa1111", manifest=_good_manifest(run_id="aaaa1111"))

        sentinel = ["sentinel-prog", "untouched"]
        monkeypatch.setattr(sys, "argv", sentinel)

        main(["pubrun", "--no-color", "status", "--dir", str(runs)])

        assert sys.argv is sentinel
        assert sys.argv == ["sentinel-prog", "untouched"]
        assert "aaaa1111" in capsys.readouterr().out

    def test_main_without_argv_reads_sys_argv(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")
        runs = tmp_path / "runs"
        _write_run(runs, "pubrun-bbbb2222", manifest=_good_manifest(run_id="bbbb2222"))

        original_argv = ["pubrun", "--no-color", "status", "--dir", str(runs)]
        monkeypatch.setattr(sys, "argv", original_argv)

        main()

        assert sys.argv is original_argv
        assert sys.argv == ["pubrun", "--no-color", "status", "--dir", str(runs)]
        assert "bbbb2222" in capsys.readouterr().out

    def test_main_argv_unknown_command_exits_2(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")

        with pytest.raises(SystemExit) as exc_info:
            main(["pubrun", "bogus"])

        assert exc_info.value.code == 2
        assert "unknown command 'bogus' (choose from: init," in capsys.readouterr().err

    def test_main_argv_subcommand_error_uses_argv(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")
        monkeypatch.setattr(sys, "argv", ["pubrun"])

        with pytest.raises(SystemExit) as exc_info:
            main(["pubrun", "status", "--bogus"])

        assert exc_info.value.code == 2
        assert "pubrun status: error: unrecognized arguments: --bogus" in capsys.readouterr().err

    def test_main_argv_prog_name_pbr(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")

        with pytest.raises(SystemExit) as exc_info:
            main(["/x/pbr", "--help"])

        assert exc_info.value.code == 0
        assert capsys.readouterr().out.startswith("usage: pbr ")

    def test_main_argv_pbr_me(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")

        with pytest.raises(SystemExit) as exc_info:
            main(["/x/pbr", "me"])

        assert exc_info.value.code == 0
        assert capsys.readouterr().out == "ASAP\n"

    def test_main_argv_help_translation(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")

        with pytest.raises(SystemExit) as exc_help_first:
            main(["pubrun", "help", "status"])
        out_help_first = capsys.readouterr().out

        with pytest.raises(SystemExit) as exc_flag:
            main(["pubrun", "status", "--help"])
        out_flag = capsys.readouterr().out

        assert exc_help_first.value.code == 0
        assert exc_flag.value.code == 0
        assert out_help_first == out_flag

    def test_main_argv_utc_flag(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")
        runs = tmp_path / "runs"
        _write_run(
            runs,
            "pubrun-utc00001",
            manifest=_good_manifest(run_id="utc00001", started_at=1000.0),
        )

        main(["pubrun", "--no-color", "status", "--dir", str(runs), "--utc"])

        assert "1970-01-01 00:16Z" in capsys.readouterr().out
        assert status_mod._DISPLAY_UTC is True

    def test_main_argv_empty_list_prints_help(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")

        main([])

        assert "usage: pubrun " in capsys.readouterr().out


class TestApplyGlobalFlags:
    """Unit tests for _apply_global_flags()."""

    def test_no_color_present_sets_env_and_namespace_flag(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        args = argparse.Namespace(no_color=False, utc=False)

        _apply_global_flags(args, True)

        assert os.environ["NO_COLOR"] == "1"
        assert args.no_color is True

    def test_utc_flag_enables_display_utc(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        args = argparse.Namespace(no_color=False, utc=True)

        _apply_global_flags(args, False)

        assert status_mod._DISPLAY_UTC is True

    def test_false_flags_leave_no_color_unset(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        args = argparse.Namespace(no_color=False, utc=False)

        _apply_global_flags(args, False)

        assert "NO_COLOR" not in os.environ
        assert status_mod._DISPLAY_UTC is False


class TestDiagnosticsErrorAtCli:
    """In-process CLI tests confirming DiagnosticsError prints cleanly without a wrapper prefix."""

    def test_show_corrupt_manifest_prints_exact_error(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")
        bad_dir = _write_run(tmp_path / "runs", "pubrun-bad", raw_manifest="{bad")

        with pytest.raises(SystemExit) as exc_info:
            main(["pubrun", "--no-color", "show", str(bad_dir)])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "is corrupt or contains invalid JSON." in err
        assert "Failed to generate" not in err

    def test_res_corrupt_manifest_prints_exact_error(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")
        bad_dir = _write_run(tmp_path / "runs", "pubrun-bad", raw_manifest="{bad")

        with pytest.raises(SystemExit) as exc_info:
            main(["pubrun", "--no-color", "res", str(bad_dir)])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "is corrupt or contains invalid JSON." in err
        assert "Failed to generate" not in err

    def test_res_invalid_last_prints_exact_error(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")
        events = [
            {
                "type": "resource_sample",
                "timestamp_utc": 1000.0,
                "payload": {"rss_bytes": 1048576, "cpu_percent": 10.0},
            },
            {
                "type": "resource_sample",
                "timestamp_utc": 1030.0,
                "payload": {"rss_bytes": 1572864, "cpu_percent": 25.0},
            },
            {
                "type": "resource_sample",
                "timestamp_utc": 1060.0,
                "payload": {"rss_bytes": 2097152, "cpu_percent": 15.0},
            },
        ]
        good_dir = _write_run(
            tmp_path / "runs",
            "pubrun-good",
            manifest=_good_manifest(run_id="good1111"),
            events=events,
        )

        with pytest.raises(SystemExit) as exc_info:
            main(["pubrun", "--no-color", "res", str(good_dir), "--last", "bogus"])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "Invalid duration for --last: " in err
        assert "Failed to generate" not in err
