"""Negative-path and flag-coverage tests for pubrun CLI diagnostics, diff, status, and top-level dispatch."""
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from test_cli import run_pubrun

_CLI_ENV = {"NO_COLOR": "1", "PUBRUN_AUTO_START": "false"}


def _good_manifest(run_id: str = "aaaa1111", started_at: float = 1000.0, extra=None) -> dict:
    manifest = {
        "schema_version": "1.0",
        "manifest_type": "pubrun-manifest",
        "run": {"run_id": run_id},
        "status": {"outcome": "completed"},
        "invocation": {"argv": ["train.py"]},
        "timing": {"started_at_utc": started_at},
    }
    if extra:
        manifest.update(extra)
    return manifest


def _write_run(
    runs_dir: Path,
    dirname: str,
    manifest=None,
    raw_manifest: str = None,
    events=None,
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


def _dead_pid() -> int:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait(timeout=30)
    return proc.pid


# ---------------------------------------------------------------------------
# E-05: Diagnostics error-path tests
# ---------------------------------------------------------------------------


class TestDiagnosticsNegativePaths:
    """Negative-path tests for corrupt manifests, --last, methods --all, and show."""

    @pytest.mark.parametrize(
        "cmd_builder,expected_err",
        [
            (lambda d: ["show", str(d)], "is corrupt or contains invalid JSON."),
            (lambda d: ["res", str(d)], "is corrupt or contains invalid JSON."),
            (lambda d: ["diff", str(d), str(d)], "Failed to generate diff report: "),
            (lambda d: ["methods", str(d)], "Failed to generate methods section: "),
            (lambda d: ["rerun", str(d)], "Failed to fetch rerun command: "),
            (lambda d: ["inspect", str(d)], "Failed to read manifest: "),
        ],
        ids=["show", "res", "diff", "methods", "rerun", "inspect"],
    )
    def test_corrupt_manifest_exits_1_without_traceback(self, tmp_path, cmd_builder, expected_err):
        bad_dir = _write_run(tmp_path / "runs", "pubrun-bad", raw_manifest="{bad")
        res = run_pubrun(*cmd_builder(bad_dir), cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 1
        assert expected_err in res.stderr
        assert "Traceback" not in res.stderr

    @pytest.mark.parametrize(
        "last_val,expected_err",
        [
            ("bogus", "Invalid duration for --last: could not convert string to float: 'bogu'"),
            ("", "Invalid duration for --last: duration string is empty"),
        ],
        ids=["bogus", "empty"],
    )
    def test_res_invalid_last_duration(self, tmp_path, last_val, expected_err):
        events = [
            {
                "type": "resource_sample",
                "timestamp_utc": 1000.0,
                "payload": {"rss_bytes": 1048576, "cpu_percent": 10.0},
            },
            {
                "type": "resource_sample",
                "timestamp_utc": 1010.0,
                "payload": {"rss_bytes": 2097152, "cpu_percent": 25.0},
            },
        ]
        run_dir = _write_run(tmp_path / "runs", "pubrun-res", manifest=_good_manifest(), events=events)
        res = run_pubrun("res", str(run_dir), "--last", last_val, cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 1
        assert expected_err in res.stderr
        assert "Traceback" not in res.stderr

    @pytest.mark.parametrize("subcmd", ["res", "cpu", "mem"])
    def test_resource_commands_empty_events_jsonl(self, tmp_path, subcmd):
        run_dir = _write_run(tmp_path / "runs", "pubrun-empty-ev", manifest=_good_manifest(), events=[])
        res = run_pubrun(subcmd, str(run_dir), cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 0
        assert "No resource samples found in events.jsonl." in res.stdout

    def test_methods_all_rejects_specific_run_dir(self, tmp_path):
        run_dir = _write_run(tmp_path / "runs", "pubrun-good", manifest=_good_manifest())
        res = run_pubrun("methods", "--all", str(run_dir), cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 1
        assert "do not also pass a specific run directory" in res.stderr

    def test_methods_all_skips_corrupt_and_reports_count(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _write_run(runs_dir, "pubrun-good", manifest=_good_manifest())
        _write_run(runs_dir, "pubrun-bad", raw_manifest="{bad")
        res = run_pubrun("methods", "--all", cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 0
        assert "### Computational Methods" in res.stdout
        assert "1 matching run(s) had no readable manifest and were skipped." in res.stderr

    def test_methods_all_filter_no_match(self, tmp_path):
        _write_run(tmp_path / "runs", "pubrun-good", manifest=_good_manifest())
        res = run_pubrun("methods", "--all", "-f", "nomatch", cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 1
        assert "No runs match the filter criteria." in res.stderr

    def test_methods_all_only_corrupt_runs(self, tmp_path):
        _write_run(tmp_path / "runs", "pubrun-bad", raw_manifest="{bad")
        res = run_pubrun("methods", "--all", cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 1
        assert "No readable manifests among the matching runs." in res.stderr

    def test_show_unknown_section_matches_default_show(self, tmp_path):
        run_dir = _write_run(tmp_path / "runs", "pubrun-good", manifest=_good_manifest())
        res_plain = run_pubrun("show", str(run_dir), cwd=str(tmp_path), env=_CLI_ENV)
        res_bogus = run_pubrun("show", str(run_dir), "bogus_section", cwd=str(tmp_path), env=_CLI_ENV)
        assert res_plain.returncode == 0
        assert res_bogus.returncode == 0
        assert res_bogus.stdout == res_plain.stdout


# ---------------------------------------------------------------------------
# E-16: diff flag tests
# ---------------------------------------------------------------------------


class TestDiffFlags:
    """Behavioral tests for diff inline, --table, --same/--no-same, wrap/max-length, --export, and depth."""

    @pytest.fixture
    def diff_pair(self, tmp_path):
        runs_dir = tmp_path / "runs"
        m_a = _good_manifest(
            run_id="aaaa1111",
            started_at=1000.0,
            extra={
                "python": {"version": "3.11.1"},
                "invocation": {"argv": ["train.py", "--lr", "0.1"]},
                "hardware": {"cpu_model": "Intel X"},
            },
        )
        m_b = _good_manifest(
            run_id="bbbb2222",
            started_at=2000.0,
            extra={
                "python": {"version": "3.12.0"},
                "invocation": {"argv": ["train.py", "--lr", "0.2"]},
                "hardware": {"cpu_model": "AMD Y"},
            },
        )
        dir_a = _write_run(runs_dir, "pubrun-a", manifest=m_a)
        dir_b = _write_run(runs_dir, "pubrun-b", manifest=m_b)
        return str(dir_a), str(dir_b)

    def test_diff_default_inline(self, tmp_path, diff_pair):
        dir_a, dir_b = diff_pair
        res = run_pubrun("diff", dir_a, dir_b, cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 0
        lines = res.stdout.splitlines()
        idx = lines.index("~ [CHANGED] python.version:")
        assert lines[idx + 1] == "    - 3.11.1"
        assert lines[idx + 2] == "    + 3.12.0"
        assert "--- Unchanged ---" not in res.stdout

    def test_diff_table_and_max_length(self, tmp_path, diff_pair):
        dir_a, dir_b = diff_pair
        res_table = run_pubrun("diff", dir_a, dir_b, "--table", cwd=str(tmp_path), env=_CLI_ENV)
        assert res_table.returncode == 0
        rows = [line.split() for line in res_table.stdout.splitlines()]
        assert ["~", "python.version", "3.11.1", "->", "3.12.0"] in rows
        assert ["~", "invocation.argv", "list", "[+1,", "-1]"] in rows

        res_trunc = run_pubrun(
            "diff", dir_a, dir_b, "--table", "--max-length", "5", cwd=str(tmp_path), env=_CLI_ENV
        )
        assert res_trunc.returncode == 0
        rows_trunc = [line.split() for line in res_trunc.stdout.splitlines()]
        assert ["~", "python.version", "3.11.", "..."] in rows_trunc
        assert ["~", "invocation.argv", "list", "..."] in rows_trunc

    def test_diff_same_and_no_same(self, tmp_path, diff_pair):
        dir_a, dir_b = diff_pair
        res_same = run_pubrun("diff", dir_a, dir_b, "--same", cwd=str(tmp_path), env=_CLI_ENV)
        assert res_same.returncode == 0
        assert "--- Unchanged ---" in res_same.stdout
        assert "= schema_version: 1.0" in res_same.stdout

        res_no_same = run_pubrun("diff", dir_a, dir_b, "--no-same", cwd=str(tmp_path), env=_CLI_ENV)
        assert res_no_same.returncode == 0
        assert "--- Unchanged ---" not in res_no_same.stdout

    def test_diff_max_length_wrap_and_no_wrap(self, tmp_path, diff_pair):
        dir_a, dir_b = diff_pair
        res_nowrap = run_pubrun(
            "diff", dir_a, dir_b, "--max-length", "3", "--no-wrap", cwd=str(tmp_path), env=_CLI_ENV
        )
        assert res_nowrap.returncode == 0
        assert "    - Int ... [TRUNCATED]" in res_nowrap.stdout

        res_wrap = run_pubrun(
            "diff", dir_a, dir_b, "--max-length", "3", cwd=str(tmp_path), env=_CLI_ENV
        )
        assert res_wrap.returncode == 0
        assert "    - Intel X" in res_wrap.stdout

    def test_diff_bare_export(self, tmp_path, diff_pair):
        dir_a, dir_b = diff_pair
        res = run_pubrun("diff", dir_a, dir_b, "--export", cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 0
        assert "[ OK  ] Successfully exported semantic baseline A to: .pubrun_diff_A_pubrun-a_clean.txt" in res.stdout
        exported = (tmp_path / ".pubrun_diff_A_pubrun-a_clean.txt").read_text(encoding="utf-8")
        assert "python.version = 3.11.1" in exported.splitlines()

    def test_diff_depth_hardware_filtering(self, tmp_path, diff_pair):
        dir_a, dir_b = diff_pair
        res_basic = run_pubrun("diff", dir_a, dir_b, "--basic", cwd=str(tmp_path), env=_CLI_ENV)
        res_std = run_pubrun("diff", dir_a, dir_b, "--standard", cwd=str(tmp_path), env=_CLI_ENV)
        res_default = run_pubrun("diff", dir_a, dir_b, cwd=str(tmp_path), env=_CLI_ENV)
        assert res_basic.returncode == 0
        assert res_std.returncode == 0
        assert res_default.returncode == 0
        count_basic = sum(1 for line in res_basic.stdout.splitlines() if "hardware.cpu_model" in line)
        count_std = sum(1 for line in res_std.stdout.splitlines() if "hardware.cpu_model" in line)
        count_default = sum(1 for line in res_default.stdout.splitlines() if "hardware.cpu_model" in line)
        assert count_basic == 0
        assert count_std == 1
        assert count_default == 1


# ---------------------------------------------------------------------------
# E-17: status selector and crashed close-out tests
# ---------------------------------------------------------------------------


class TestStatusSelectorsAndCloseOut:
    """Behavioral tests for status --utc, -v, ambiguous integer selector, missing run, and crashed close-out."""

    def test_status_utc_and_verbose(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _write_run(runs_dir, "pubrun-a", manifest=_good_manifest(run_id="aaaa1111", started_at=1000.0))
        _write_run(runs_dir, "pubrun-b", manifest=_good_manifest(run_id="bbbb2222", started_at=2000.0))

        res_utc = run_pubrun("status", "--dir", str(runs_dir), "--utc", cwd=str(tmp_path), env=_CLI_ENV)
        assert res_utc.returncode == 0
        assert "1970-01-01 00:16Z" in res_utc.stdout
        assert "1970-01-01 00:33Z" in res_utc.stdout
        assert "  Run ID:" not in res_utc.stdout

        res_v = run_pubrun("status", "--dir", str(runs_dir), "-v", cwd=str(tmp_path), env=_CLI_ENV)
        assert res_v.returncode == 0
        lines = res_v.stdout.splitlines()
        assert "  Run ID:    aaaa1111" in lines
        assert "  Run ID:    bbbb2222" in lines

    def test_status_ambiguous_recency_selector(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _write_run(runs_dir, "pubrun-id2", manifest=_good_manifest(run_id="2", started_at=3000.0))
        _write_run(runs_dir, "pubrun-b", manifest=_good_manifest(run_id="bbbb2222", started_at=2000.0))
        _write_run(runs_dir, "pubrun-c", manifest=_good_manifest(run_id="cccc3333", started_at=1000.0))

        res = run_pubrun("status", "2", "--dir", str(runs_dir), cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 1
        assert (
            "'2' is ambiguous: it means both the 2th-most-recent run (id bbbb2222) "
            "AND run id '2'. Refusing to guess."
        ) in res.stderr

    def test_status_missing_run_id(self, tmp_path):
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir(parents=True)
        res = run_pubrun("status", "zzzz", "--dir", str(runs_dir), cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 1
        assert "No run found matching 'zzzz'." in res.stderr

    def test_status_inspect_closes_out_crashed_run(self, tmp_path):
        from pubrun.capture.liveness import get_hostname

        runs_dir = tmp_path / "runs"
        run_dir = runs_dir / "pubrun-deadbeef"
        run_dir.mkdir(parents=True)
        lock_data = {
            "run_id": "deadbeef",
            "pid": _dead_pid(),
            "started_at_utc": time.time() - 60,
            "script": "train.py",
            "argv": ["train.py"],
            "hostname": get_hostname(),
        }
        (run_dir / ".pubrun.lock").write_text(json.dumps(lock_data), encoding="utf-8")

        res = run_pubrun("status", "deadbeef", "--dir", str(runs_dir), cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 0
        assert "  Status:        crashed" in res.stdout.splitlines()
        manifest_path = run_dir / "manifest.json"
        assert manifest_path.exists()
        assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"]["outcome"] == "crashed"
        assert not (run_dir / ".pubrun.lock").exists()

    def test_status_list_closes_out_crashed_run(self, tmp_path):
        from pubrun.capture.liveness import get_hostname

        runs_dir = tmp_path / "runs"
        run_dir = runs_dir / "pubrun-deadbeef"
        run_dir.mkdir(parents=True)
        lock_data = {
            "run_id": "deadbeef",
            "pid": _dead_pid(),
            "started_at_utc": time.time() - 60,
            "script": "train.py",
            "argv": ["train.py"],
            "hostname": get_hostname(),
        }
        (run_dir / ".pubrun.lock").write_text(json.dumps(lock_data), encoding="utf-8")

        res = run_pubrun("status", "--dir", str(runs_dir), cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 0
        manifest_path = run_dir / "manifest.json"
        assert manifest_path.exists()
        assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"]["outcome"] == "crashed"
        assert not (run_dir / ".pubrun.lock").exists()


# ---------------------------------------------------------------------------
# E-18: In-process top-level CLI tests
# ---------------------------------------------------------------------------


class TestTopLevelCliInProcess:
    """In-process tests of pubrun.__main__.main() for --create-config, unknown commands, and pbr prog name."""

    @pytest.mark.parametrize("answer", ["1", ""])
    def test_create_config_local_choice(self, tmp_path, monkeypatch, answer):
        from pubrun.__main__ import main

        monkeypatch.setattr(sys, "argv", ["pubrun", "--create-config"])
        monkeypatch.setattr("builtins.input", lambda prompt="": answer)
        main()
        assert (tmp_path / ".pubrun.toml").exists()

    def test_create_config_global_choice(self, tmp_path, monkeypatch):
        from pubrun.__main__ import main

        xdg_dir = tmp_path / "xdg"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))
        monkeypatch.setenv("APPDATA", str(xdg_dir))
        monkeypatch.setattr(sys, "argv", ["pubrun", "--create-config"])
        monkeypatch.setattr("builtins.input", lambda prompt="": "2")
        main()
        assert (xdg_dir / "pubrun" / "config.toml").exists()
        assert not (tmp_path / ".pubrun.toml").exists()

    def test_create_config_invalid_choice(self, tmp_path, monkeypatch, capsys):
        from pubrun.__main__ import main

        monkeypatch.setattr(sys, "argv", ["pubrun", "--create-config"])
        monkeypatch.setattr("builtins.input", lambda prompt="": "3")
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        assert "Invalid selection." in capsys.readouterr().err
        assert not (tmp_path / ".pubrun.toml").exists()

    def test_create_config_keyboard_interrupt(self, tmp_path, monkeypatch, capsys):
        from pubrun.__main__ import main

        def raise_kb(prompt=""):
            raise KeyboardInterrupt

        monkeypatch.setattr(sys, "argv", ["pubrun", "--create-config"])
        monkeypatch.setattr("builtins.input", raise_kb)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        assert "Configuration abandoned." in capsys.readouterr().err
        assert not (tmp_path / ".pubrun.toml").exists()

    def test_unknown_command_lists_primary_commands_only(self, monkeypatch, capsys):
        from pubrun.__main__ import main

        monkeypatch.setattr(sys, "argv", ["pubrun", "bogus"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "unknown command 'bogus' (choose from: init, report-bug," in err
        choices_str = err.split("(choose from: ", 1)[1].split(")", 1)[0]
        choices = [c.strip() for c in choices_str.split(",")]
        assert "res" in choices
        assert "tui" not in choices
        assert "gui" not in choices

    def test_pbr_prog_name_in_help(self, monkeypatch, capsys):
        from pubrun.__main__ import main

        monkeypatch.setattr(sys, "argv", ["/x/pbr", "--help"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert out.startswith("usage: pbr ")
