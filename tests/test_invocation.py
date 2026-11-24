"""Behavioral tests for src/pubrun/capture/invocation.py."""
import hashlib
import logging
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from pubrun.capture.invocation import get_invocation


@pytest.fixture
def argv(monkeypatch):
    """Set sys.argv for a single test via monkeypatch."""
    def _set(values):
        monkeypatch.setattr(sys, "argv", list(values))
    return _set


class TestEntrypointClassification:
    def test_existing_file_is_script(self, tmp_path, argv):
        script = tmp_path / "train.py"
        script.write_text("print('hi')\n", encoding="utf-8")
        argv(["train.py"])

        res = get_invocation()
        assert res["capture_state"] == {"status": "complete"}
        assert res["entrypoint_type"] == "script"
        assert res["script"]["basename"] == "train.py"

    @pytest.mark.parametrize(
        "arg0, expected",
        [
            ("-m", "module"),
            ("-c", "interactive"),
            ("", "interactive"),
        ],
    )
    def test_non_file_entrypoint_types(self, argv, arg0, expected):
        argv([arg0])
        res = get_invocation()
        assert res["capture_state"] == {"status": "complete"}
        assert res["entrypoint_type"] == expected

    def test_missing_script_is_unknown(self, argv):
        argv(["does_not_exist.py"])
        res = get_invocation()
        assert res["capture_state"] == {"status": "complete"}
        assert res["entrypoint_type"] == "unknown"
        assert res["script"] == {}

    def test_empty_argv_is_interactive(self, argv):
        argv([])
        res = get_invocation()
        assert res["entrypoint_type"] == "interactive"
        assert res["argv"] == []
        assert res["capture_state"]["status"] == "complete"


class TestScriptHashing:
    def test_small_script_is_hashed(self, tmp_path, argv):
        body = b"x = 42\n"
        (tmp_path / "small.py").write_bytes(body)
        argv(["small.py"])

        res = get_invocation()
        assert res["script"]["size"] == len(body)
        assert res["script"]["sha256"] == hashlib.sha256(body).hexdigest()
        assert "sha256_skipped" not in res["script"]

    def test_script_at_limit_is_hashed(self, tmp_path, argv):
        body = b"a" * 1_048_576
        (tmp_path / "exact_1mb.py").write_bytes(body)
        argv(["exact_1mb.py"])

        res = get_invocation()
        assert res["script"]["size"] == 1_048_576
        assert res["script"]["sha256"] == hashlib.sha256(body).hexdigest()
        assert "sha256_skipped" not in res["script"]

    def test_script_over_limit_skips_sha256(self, tmp_path, argv):
        body = b"a" * 1_048_577
        (tmp_path / "over_1mb.py").write_bytes(body)
        argv(["over_1mb.py"])

        res = get_invocation()
        assert res["script"]["size"] == 1_048_577
        assert "sha256" not in res["script"]
        assert res["script"]["sha256_skipped"] == "file exceeds 1MB"


class TestInputDiscovery:
    def test_discovers_existing_files_and_directories(self, tmp_path, argv):
        data_file = tmp_path / "data.csv"
        data_file.write_bytes(b"a,b\n1,2\n")
        ds_dir = tmp_path / "ds"
        ds_dir.mkdir()
        argv(["s.py", "data.csv", "ds", "missing.csv"])

        res = get_invocation()
        inputs = res["inputs"]
        assert [(i["arg_index"], i["path"], i["is_dir"]) for i in inputs] == [
            (1, "data.csv", False),
            (2, "ds", True),
        ]
        for entry in inputs:
            assert "size" in entry
            assert "real_path" in entry
            assert "md5" not in entry

    def test_disabled_input_discovery_returns_empty(self, tmp_path, argv):
        (tmp_path / "data.csv").write_bytes(b"1,2\n")
        argv(["s.py", "data.csv"])

        res = get_invocation({"capture": {"inputs": {"enabled": False}}})
        assert res["inputs"] == []

    def test_option_flags_are_not_inputs(self, tmp_path, argv):
        (tmp_path / "-v").write_bytes(b"flag-file")
        (tmp_path / "--out").mkdir()
        argv(["s.py", "-v", "--out"])

        res = get_invocation()
        assert res["inputs"] == []

    def test_ignore_extensions_is_case_insensitive(self, tmp_path, argv):
        (tmp_path / "a.LOG").write_bytes(b"log-line\n")
        (tmp_path / "keep.csv").write_bytes(b"1,2\n")
        argv(["s.py", "a.LOG", "keep.csv"])

        res = get_invocation({"capture": {"inputs": {"ignore_extensions": ["Log"]}}})
        assert [i["path"] for i in res["inputs"]] == ["keep.csv"]

    def test_compute_md5_hashes_files_and_warns(self, tmp_path, argv, caplog):
        payload = b"binary-dataset-bytes"
        (tmp_path / "d.bin").write_bytes(payload)
        (tmp_path / "folder").mkdir()
        argv(["s.py", "d.bin", "folder"])

        with caplog.at_level(logging.WARNING, logger="pubrun"):
            res = get_invocation({"capture": {"inputs": {"compute_md5": True}}})

        by_path = {i["path"]: i for i in res["inputs"]}
        assert by_path["d.bin"]["md5"] == hashlib.md5(payload).hexdigest()
        assert "md5" not in by_path["folder"]

        warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings == [
            "Computing MD5 for sys.argv[1] (d.bin). This may cause startup latency."
        ]


class TestCommandFormattingAndSecurity:
    def test_posix_commands_use_redacted_argv(self, argv, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        argv(["s.py", "--password", "hunter2", "my file.csv"])

        res = get_invocation()
        expected_argv = ["s.py", "--password", "[REDACTED]", "my file.csv"]
        assert res["argv"] == expected_argv
        assert res["command_line"] == shlex.join(expected_argv)
        assert res["rerun_command"] == (
            f"cd {shlex.quote(str(Path.cwd()))} && python {shlex.join(expected_argv)}"
        )
        assert "hunter2" not in res["command_line"]
        assert "hunter2" not in res["rerun_command"]

    def test_win32_commands_use_redacted_argv(self, argv, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        argv(["s.py", "--password", "hunter2", "my file.csv"])

        res = get_invocation()
        expected_argv = ["s.py", "--password", "[REDACTED]", "my file.csv"]
        assert res["argv"] == expected_argv
        assert res["command_line"] == subprocess.list2cmdline(expected_argv)
        assert res["rerun_command"] == (
            f"cd {subprocess.list2cmdline([str(Path.cwd())])}\n"
            f"python {subprocess.list2cmdline(expected_argv)}"
        )
        assert "hunter2" not in res["command_line"]
        assert "hunter2" not in res["rerun_command"]

    def test_path_entry_in_argv_completes(self, argv):
        argv(["s.py", Path("data.csv"), "--lr=0.1"])

        res = get_invocation()
        assert res["capture_state"] == {"status": "complete"}
        assert res["command_line"] == "s.py data.csv --lr=0.1"

    def test_path_entry_with_argv_redaction_disabled_completes(self, tmp_path, argv):
        (tmp_path / "data.csv").write_bytes(b"x,y\n1,2\n")
        argv(["s.py", Path("data.csv"), "--lr=0.1"])

        res = get_invocation({"redaction": {"argv_enabled": False}})
        assert res["capture_state"] == {"status": "complete"}
        assert res["command_line"] == "s.py data.csv --lr=0.1"
        assert [i["path"] for i in res["inputs"]] == ["data.csv"]

    def test_redacted_argument_is_not_recorded_as_input(self, tmp_path, argv, caplog):
        (tmp_path / "creds.json").write_text('{"secret": "val"}\n', encoding="utf-8")
        (tmp_path / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        argv(["s.py", "--credentials", "creds.json", "data.csv"])

        with caplog.at_level(logging.DEBUG, logger="pubrun"):
            res = get_invocation({"capture": {"inputs": {"compute_md5": True}}})

        assert [i["path"] for i in res["inputs"]] == ["data.csv"]
        assert "creds.json" not in repr(res)
        assert "creds.json" not in caplog.text

        res_unredacted = get_invocation({"redaction": {"argv_enabled": False}})
        assert [i["path"] for i in res_unredacted["inputs"]] == ["creds.json", "data.csv"]
