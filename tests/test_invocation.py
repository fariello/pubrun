"""Behavioral tests for src/pubrun/capture/invocation.py."""
import hashlib
import logging
import os
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
        monkeypatch.setattr(sys, "executable", "/opt/my venv/bin/python3")
        argv(["s.py", "--password", "hunter2", "my file.csv"])

        res = get_invocation()
        expected_argv = ["s.py", "--password", "[REDACTED]", "my file.csv"]
        assert res["argv"] == expected_argv
        assert res["command_line"] == shlex.join(expected_argv)
        assert res["rerun_command"] == (
            f"cd {shlex.quote(str(Path.cwd()))} && "
            f"{shlex.quote('/opt/my venv/bin/python3')} {shlex.join(expected_argv)}"
        )
        assert "hunter2" not in res["command_line"]
        assert "hunter2" not in res["rerun_command"]

    def test_win32_commands_use_redacted_argv(self, argv, monkeypatch):
        win_py = r"C:\Program Files\Python311\python.exe"
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setattr(sys, "executable", win_py)
        argv(["s.py", "--password", "hunter2", "my file.csv"])

        res = get_invocation()
        expected_argv = ["s.py", "--password", "[REDACTED]", "my file.csv"]
        assert res["argv"] == expected_argv
        assert res["command_line"] == subprocess.list2cmdline(expected_argv)
        assert res["rerun_command"] == (
            f"cd {subprocess.list2cmdline([str(Path.cwd())])}\n"
            f"{subprocess.list2cmdline([win_py])} "
            f"{subprocess.list2cmdline(expected_argv)}"
        )
        assert "hunter2" not in res["command_line"]
        assert "hunter2" not in res["rerun_command"]

    def test_empty_sys_executable_falls_back_to_python(self, argv, monkeypatch):
        monkeypatch.setattr(sys, "executable", "")
        argv(["s.py", "--epochs", "2"])

        monkeypatch.setattr(sys, "platform", "linux")
        res_posix = get_invocation()
        assert res_posix["rerun_command"] == (
            f"cd {shlex.quote(str(Path.cwd()))} && python s.py --epochs 2"
        )

        monkeypatch.setattr(sys, "platform", "win32")
        res_win = get_invocation()
        assert res_win["rerun_command"] == (
            f"cd {subprocess.list2cmdline([str(Path.cwd())])}\npython s.py --epochs 2"
        )

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


class TestModuleNotebookAndInputHardening:
    def test_python_m_module_and_package_detection_and_origin_guard(
        self, tmp_path, argv, monkeypatch
    ):
        from types import SimpleNamespace

        mod_file = tmp_path / "mod.py"
        mod_file.write_text("x = 1\n", encoding="utf-8")
        pkg_main = tmp_path / "__main__.py"
        pkg_main.write_text("y = 2\n", encoding="utf-8")
        other_script = tmp_path / "other.py"
        other_script.write_text("z = 3\n", encoding="utf-8")

        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(sys, "executable", "/usr/bin/python3")

        # 1. python -m mypkg.mod with matching __spec__.origin
        fake_main = SimpleNamespace(
            __spec__=SimpleNamespace(name="mypkg.mod", origin=str(mod_file))
        )
        monkeypatch.setitem(sys.modules, "__main__", fake_main)
        argv([str(mod_file), "--epochs", "5"])
        res = get_invocation()
        assert res["entrypoint_type"] == "module"
        assert res["script"]["basename"] == "mod.py"
        assert res["rerun_command"] == (
            f"cd {shlex.quote(str(Path.cwd()))} && /usr/bin/python3 -m mypkg.mod --epochs 5"
        )

        # 2. python -m mypkg (__spec__.name ends with .__main__)
        fake_pkg = SimpleNamespace(
            __spec__=SimpleNamespace(name="mypkg.__main__", origin=str(pkg_main))
        )
        monkeypatch.setitem(sys.modules, "__main__", fake_pkg)
        argv([str(pkg_main), "--lr", "0.01"])
        res_pkg = get_invocation()
        assert res_pkg["entrypoint_type"] == "module"
        assert res_pkg["script"]["basename"] == "__main__.py"
        assert res_pkg["rerun_command"] == (
            f"cd {shlex.quote(str(Path.cwd()))} && /usr/bin/python3 -m mypkg --lr 0.01"
        )

        # 3. Non-matching origin (e.g. under `python -m pytest`) must NOT hijack script.py
        argv([str(other_script)])
        res_other = get_invocation()
        assert res_other["entrypoint_type"] == "script"
        assert "-m mypkg" not in (res_other["rerun_command"] or "")

        # 4. argv[0] == "-m" with spec avoids duplicate "-m -m"
        argv(["-m", "--verbose"])
        res_dash_m = get_invocation()
        assert res_dash_m["entrypoint_type"] == "module"
        assert res_dash_m["rerun_command"] == (
            f"cd {shlex.quote(str(Path.cwd()))} && /usr/bin/python3 -m mypkg --verbose"
        )

    def test_dash_c_and_interactive_rerun_command_is_none(self, argv):
        for vals in (["-c"], ["-c", "print(1)"], [""], []):
            argv(vals)
            res = get_invocation()
            assert res["entrypoint_type"] == "interactive"
            assert res["rerun_command"] is None

    def test_jupyter_zmq_kernel_detected_and_omits_kernel_files(
        self, tmp_path, argv, monkeypatch
    ):
        from types import SimpleNamespace

        launcher = tmp_path / "ipykernel_launcher.py"
        launcher.write_text("# launcher\n", encoding="utf-8")
        kernel_json = tmp_path / "kernel-123.json"
        kernel_json.write_text('{"ip": "127.0.0.1"}\n', encoding="utf-8")
        conn2 = tmp_path / "conn2.json"
        conn2.write_text("{}\n", encoding="utf-8")
        conn3 = tmp_path / "conn3.json"
        conn3.write_text("{}\n", encoding="utf-8")

        class ZMQInteractiveShell:
            pass

        fake_ipython = SimpleNamespace(get_ipython=lambda: ZMQInteractiveShell())
        monkeypatch.setitem(sys.modules, "IPython", fake_ipython)
        argv([
            str(launcher),
            "-f",
            str(kernel_json),
            f"--f={conn2}",
            f"--ConnectionFile={conn3}",
        ])

        res = get_invocation()
        assert res["entrypoint_type"] == "notebook"
        assert res["script"] == {}
        assert res["rerun_command"] is None
        assert res["inputs"] == []

    def test_flag_eq_path_discovered_and_redacted_flag_eq_suppressed(
        self, tmp_path, argv, caplog
    ):
        (tmp_path / "train.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        (tmp_path / "secret.txt").write_text("super-secret\n", encoding="utf-8")
        argv(["s.py", "--data=train.csv", "--api-key=secret.txt", "--empty="])

        with caplog.at_level(logging.DEBUG, logger="pubrun"):
            res = get_invocation({"capture": {"inputs": {"compute_md5": True}}})

        assert [(i["arg_index"], i["path"]) for i in res["inputs"]] == [(1, "train.csv")]
        assert "secret.txt" not in repr(res)
        assert "secret.txt" not in caplog.text

    def test_input_discovery_uses_single_os_stat_call(self, tmp_path, argv, monkeypatch):
        import os
        import pubrun.capture.invocation as inv_mod

        data = tmp_path / "single_stat.csv"
        data.write_bytes(b"1,2,3\n")
        argv(["s.py", str(data)])

        real_stat = os.stat
        stat_calls = []

        def counting_stat(path, *args, **kwargs):
            if str(path) == str(data):
                stat_calls.append(str(path))
            return real_stat(path, *args, **kwargs)

        monkeypatch.setattr(inv_mod.os, "stat", counting_stat)
        res = get_invocation()
        assert len(res["inputs"]) == 1
        assert len(stat_calls) == 1

    def test_missing_stat_skips_main_file_hashing(self, tmp_path, argv, monkeypatch):
        script = tmp_path / "unstat.py"
        script.write_text("print(1)\n", encoding="utf-8")
        argv([str(script)])

        real_stat = Path.stat

        def failing_stat(self, *args, **kwargs):
            if self.name == "unstat.py":
                raise OSError("stat failed")
            return real_stat(self, *args, **kwargs)

        # Ensure exists() and is_file() succeed while stat() fails for the script.
        monkeypatch.setattr(Path, "exists", lambda self: True if self.name == "unstat.py" else os.path.exists(self))
        monkeypatch.setattr(Path, "is_file", lambda self: True if self.name == "unstat.py" else os.path.isfile(self))
        monkeypatch.setattr(Path, "stat", failing_stat)

        res = get_invocation()
        assert res["entrypoint_type"] == "script"
        assert "size" not in res["script"]
        assert "sha256" not in res["script"]
        assert "sha256_skipped" not in res["script"]

    def test_compute_md5_max_md5_bytes_cap_and_zero_uncapped(self, tmp_path, argv, caplog):
        payload = b"0123456789ABCDEF"  # 16 bytes
        f = tmp_path / "big.bin"
        f.write_bytes(payload)
        argv(["s.py", "big.bin"])

        # Over cap -> skipped with md5_skipped and NO latency warning
        with caplog.at_level(logging.WARNING, logger="pubrun"):
            res_capped = get_invocation(
                {"capture": {"inputs": {"compute_md5": True, "max_md5_bytes": 10}}}
            )
        entry = res_capped["inputs"][0]
        assert "md5" not in entry
        assert entry["md5_skipped"] == "file exceeds 10 bytes"
        assert [r for r in caplog.records if r.levelno == logging.WARNING] == []

        # max_md5_bytes = 0 disables cap -> hashed
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="pubrun"):
            res_uncapped = get_invocation(
                {"capture": {"inputs": {"compute_md5": True, "max_md5_bytes": 0}}}
            )
        entry0 = res_uncapped["inputs"][0]
        assert entry0["md5"] == hashlib.md5(payload).hexdigest()
        assert "md5_skipped" not in entry0
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1

        # Invalid/negative/bool values fall back to default (100 MiB) -> 16-byte file is hashed
        for bad in (-5, True, "bad"):
            res_bad = get_invocation(
                {"capture": {"inputs": {"compute_md5": True, "max_md5_bytes": bad}}}
            )
            assert res_bad["inputs"][0]["md5"] == hashlib.md5(payload).hexdigest()
