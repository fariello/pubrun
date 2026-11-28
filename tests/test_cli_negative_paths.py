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
            ("bogus", "Invalid duration for --last: invalid duration 'bogus' (valid examples: '30s', '10m', '2h', '1d')"),
            ("", "Invalid duration for --last: duration string is empty (valid examples: '30s', '10m', '2h', '1d')"),
            ("0s", "must be a positive finite value (valid examples: '30s', '10m', '2h', '1d')"),
            ("-5m", "must be a positive finite value (valid examples: '30s', '10m', '2h', '1d')"),
            ("nan", "must be a positive finite value (valid examples: '30s', '10m', '2h', '1d')"),
            ("inf", "must be a positive finite value (valid examples: '30s', '10m', '2h', '1d')"),
        ],
        ids=["bogus", "empty", "zero", "negative", "nan", "inf"],
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
        res = run_pubrun("res", str(run_dir), f"--last={last_val}", cwd=str(tmp_path), env=_CLI_ENV)
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
        assert "0 of 1 runs matched the filter criteria." in res.stderr

    def test_empty_dir_vs_zero_match_messages(self, tmp_path):
        empty_runs = tmp_path / "empty_runs"
        empty_runs.mkdir()
        for cmd in (["show", "--dir", str(empty_runs)], ["combined", "--dir", str(empty_runs)], ["methods", "--all", "--dir", str(empty_runs)]):
            res = run_pubrun(*cmd, cwd=str(tmp_path), env=_CLI_ENV)
            assert res.returncode == 1
            assert "No runs found in" in res.stderr

        pop_runs = tmp_path / "pop_runs"
        _write_run(pop_runs, "pubrun-good", manifest=_good_manifest())
        for cmd in (["show", "--dir", str(pop_runs), "-f", "nomatch"], ["combined", "--dir", str(pop_runs), "-f", "nomatch"], ["methods", "--all", "--dir", str(pop_runs), "-f", "nomatch"]):
            res = run_pubrun(*cmd, cwd=str(tmp_path), env=_CLI_ENV)
            assert res.returncode == 1
            assert "0 of 1 runs matched the filter criteria." in res.stderr

    def test_methods_all_only_corrupt_runs(self, tmp_path):
        _write_run(tmp_path / "runs", "pubrun-bad", raw_manifest="{bad")
        res = run_pubrun("methods", "--all", cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 1
        assert "No readable manifests among the matching runs." in res.stderr

    def test_show_unknown_section_exits_2_and_lists_valid_sections(self, tmp_path):
        run_dir = _write_run(tmp_path / "runs", "pubrun-good", manifest=_good_manifest())
        res_bogus = run_pubrun("show", str(run_dir), "bogus_section", cwd=str(tmp_path), env=_CLI_ENV)
        assert res_bogus.returncode == 2
        assert res_bogus.stdout == ""
        assert "bogus_section" in res_bogus.stderr
        assert "logs, env, packages" in res_bogus.stderr
        assert "Traceback" not in res_bogus.stderr

    def test_show_logs_missing_files_prints_hint_to_stderr(self, tmp_path):
        run_dir = _write_run(tmp_path / "runs", "pubrun-nologs", manifest=_good_manifest())
        res = run_pubrun("show", str(run_dir), "logs", cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 0
        assert res.stdout == ""
        assert 'capture_mode = "standard"' in res.stderr
        assert "pubrun.full" in res.stderr


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


class TestCliHelpAndNegativePaths2ge0ea:
    """Negative-path and self-documenting help regression tests for IPD 2ge0ea."""

    def test_diff_rejects_more_than_two_positional_runs(self, tmp_path):
        runs_dir = tmp_path / "runs"
        d1 = _write_run(runs_dir, "pubrun-1", manifest=_good_manifest("aaaa1111", 1000.0))
        d2 = _write_run(runs_dir, "pubrun-2", manifest=_good_manifest("bbbb2222", 2000.0))
        d3 = _write_run(runs_dir, "pubrun-3", manifest=_good_manifest("cccc3333", 3000.0))
        res = run_pubrun("diff", str(d1), str(d2), str(d3), cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 2
        assert "at most 2" in res.stderr

    def test_diff_rejects_json_combined_with_export(self, tmp_path):
        runs_dir = tmp_path / "runs"
        d1 = _write_run(runs_dir, "pubrun-1", manifest=_good_manifest("aaaa1111", 1000.0))
        d2 = _write_run(runs_dir, "pubrun-2", manifest=_good_manifest("bbbb2222", 2000.0))
        res = run_pubrun("diff", str(d1), str(d2), "--json", "--export", cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 2
        assert "--json" in res.stderr and "--export" in res.stderr

    def test_diff_ambiguous_prefix_prints_candidates_without_traceback(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _write_run(runs_dir, "pubrun-1", manifest=_good_manifest("ab111111", 1000.0))
        _write_run(runs_dir, "pubrun-2", manifest=_good_manifest("ab222222", 2000.0))
        res = run_pubrun("diff", "ab", "--dir", str(runs_dir), cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 1
        assert "Traceback" not in res.stderr
        assert "ab111111" in res.stderr and "ab222222" in res.stderr

    def test_feedback_hidden_alias_not_in_primary_commands(self, monkeypatch, capsys):
        from pubrun.__main__ import main

        monkeypatch.setattr(sys, "argv", ["pubrun", "not-a-cmd"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        choices_str = err.split("(choose from: ", 1)[1].split(")", 1)[0]
        choices = [c.strip() for c in choices_str.split(",")]
        assert "report-bug" in choices
        assert "feedback" not in choices

    def test_self_documenting_help_surfaces(self):
        from pubrun.status import VALID_STATUSES

        # Top-level grouped help
        top = run_pubrun("--help")
        assert top.returncode == 0
        assert top.stdout.splitlines()[0].startswith("usage: pubrun ")
        assert "Command groups:" in top.stdout
        assert "Quick start:" in top.stdout

        # run --help explains import prerequisite and all 6 modes
        run_help = run_pubrun("run", "--help")
        assert run_help.returncode == 0
        assert "import pubrun" in run_help.stdout
        for mode in ("auto", "full", "noauto", "nopatch", "noconsole", "minimal"):
            assert mode in run_help.stdout

        # status --help lists all 7 VALID_STATUSES in -s/-S
        status_help = run_pubrun("status", "--help")
        assert status_help.returncode == 0
        for st in VALID_STATUSES:
            assert st in status_help.stdout

        # show --help does not expose raw config_extra
        show_help = run_pubrun("show", "--help")
        assert show_help.returncode == 0
        assert "config_extra" not in show_help.stdout
        assert "RUN" in show_help.stdout

        # meta & inspect explain hydration; diff explains --export filenames
        meta_help = run_pubrun("meta", "--help")
        assert meta_help.returncode == 0
        assert "PUBRUN_META_REF" in meta_help.stdout

        inspect_help = run_pubrun("inspect", "--help")
        assert inspect_help.returncode == 0
        assert "PUBRUN_META_REF" in inspect_help.stdout
        assert "mismatch" in inspect_help.stdout and "unknown" in inspect_help.stdout

        diff_help = run_pubrun("diff", "--help")
        assert diff_help.returncode == 0
        assert ".pubrun_diff_A_" in diff_help.stdout
        assert "[diff].export_format" in diff_help.stdout

    def test_crashed_run_suggestion_uses_pubrun_show(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _write_run(runs_dir, "pubrun-done", manifest=_good_manifest("done1111", 1000.0))
        crashed = runs_dir / "pubrun-crash"
        crashed.mkdir(parents=True)
        (crashed / ".pubrun.lock").write_text(
            json.dumps({
                "run_id": "crash222",
                "pid": _dead_pid(),
                "started_at_utc": time.time() - 100,
                "script": "train.py",
                "hostname": "remote-other-host",
            }),
            encoding="utf-8",
        )
        res = run_pubrun("show", str(crashed), "--dir", str(runs_dir), cwd=str(tmp_path), env=_CLI_ENV)
        assert res.returncode == 1
        assert "pubrun show " in res.stderr
        assert "pubrun report " not in res.stderr


# ---------------------------------------------------------------------------
# TEST-U4 (IPD kk83rk): pubrun run SIGTERM forwarding & KeyboardInterrupt escalation
# ---------------------------------------------------------------------------


class TestPubrunRunSignalSupervision:
    """Behavioral tests for `pubrun run` SIGTERM forwarding and KeyboardInterrupt escalation."""

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX SIGTERM forwarding test")
    def test_pubrun_run_forwards_sigterm_to_child_with_no_orphan(self, tmp_path):
        import os

        ready_file = tmp_path / "child_ready.pid"
        sig_marker = tmp_path / "child_sigterm.txt"
        child_script = (
            "import os, signal, sys, time\n"
            f"ready = {str(ready_file)!r}\n"
            f"marker = {str(sig_marker)!r}\n"
            "def _on_term(signum, frame):\n"
            "    with open(marker, 'w', encoding='utf-8') as fh:\n"
            "        fh.write('CHILD_GOT_SIGTERM')\n"
            "    sys.exit(0)\n"
            "signal.signal(signal.SIGTERM, _on_term)\n"
            "with open(ready, 'w', encoding='utf-8') as fh:\n"
            "    fh.write(str(os.getpid()))\n"
            "deadline = time.monotonic() + 20.0\n"
            "while time.monotonic() < deadline:\n"
            "    time.sleep(0.05)\n"
            "sys.exit(99)\n"
        )
        src_dir = Path(__file__).resolve().parents[1] / "src"
        env = dict(os.environ)
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing}" if existing else str(src_dir)
        env["NO_COLOR"] = "1"
        env["PUBRUN_AUTO_START"] = "false"

        proc = subprocess.Popen(
            [sys.executable, "-m", "pubrun", "run", "--", sys.executable, "-c", child_script],
            cwd=str(tmp_path),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            deadline = time.monotonic() + 10.0
            child_pid = None
            while time.monotonic() < deadline:
                if ready_file.exists():
                    raw = ready_file.read_text(encoding="utf-8").strip()
                    if raw.isdigit():
                        child_pid = int(raw)
                        break
                if proc.poll() is not None:
                    break
                time.sleep(0.02)
            assert child_pid is not None, f"child did not signal readiness (proc rc={proc.poll()})"

            proc.terminate()
            rc = proc.wait(timeout=10)
            assert rc == 0
            assert sig_marker.exists()
            assert sig_marker.read_text(encoding="utf-8") == "CHILD_GOT_SIGTERM"

            # Verify no orphan process remains.
            with pytest.raises(ProcessLookupError):
                os.kill(child_pid, 0)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)

    def test_pubrun_run_keyboard_interrupt_escalates_terminate_then_kill(self, monkeypatch):
        from pubrun.__main__ import main

        events = []

        class _FakePopen:
            def __init__(self, cmd, env=None):
                self.cmd = cmd
                self.env = env
                self._alive = True
                self._wait_calls = 0

            def poll(self):
                return None if self._alive else -9

            def wait(self, timeout=None):
                self._wait_calls += 1
                events.append(("wait", timeout))
                if self._wait_calls == 1:
                    raise KeyboardInterrupt
                if self._wait_calls == 2:
                    assert timeout == 3.0
                    raise subprocess.TimeoutExpired(self.cmd, timeout)
                if self._wait_calls == 3:
                    assert timeout == 5.0
                    raise subprocess.TimeoutExpired(self.cmd, timeout)
                return -9

            def terminate(self):
                events.append("terminate")

            def kill(self):
                events.append("kill")
                self._alive = False

        monkeypatch.setattr(subprocess, "Popen", _FakePopen)

        with pytest.raises(SystemExit) as exc_info:
            main(["pubrun", "run", "--", "fake-child-cmd"])

        assert exc_info.value.code == 130
        assert events == [
            ("wait", None),
            ("wait", 3.0),
            "terminate",
            ("wait", 5.0),
            "kill",
            ("wait", None),
        ]
