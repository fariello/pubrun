"""Regression tests for the bugs-audit CLI, diff, and render fixes (IPD r68o07).

Each test drives the real CLI entry point, a command handler, or the diff/render
engine and asserts on exit codes, printed output, or returned diff structures.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import pubrun.__main__ as m
from pubrun.analysis.diff import _is_path_var, compare_manifests
from pubrun.analysis.render import print_diff

PYTHON = sys.executable
_SRC = Path(__file__).resolve().parents[1] / "src"


def run_pubrun(*args, cwd=None):
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{_SRC}{os.pathsep}{existing}" if existing else str(_SRC)
    env.pop("PUBRUN_AUTO_START", None)
    return subprocess.run([PYTHON, "-m", "pubrun"] + [str(a) for a in args],
                          capture_output=True, text=True, cwd=str(cwd), env=env,
                          timeout=60, stdin=subprocess.DEVNULL)


def _make_run(runs_dir: Path, name: str, started: float, script: str = "train.py",
              outcome: str = "completed", stdout: str = None, env_vars=None) -> Path:
    d = runs_dir / f"pubrun-{name}"
    d.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run": {"run_id": name},
        "timing": {"started_at_utc": started, "ended_at_utc": started + 1.0,
                   "elapsed_seconds": 1.0},
        "status": {"outcome": outcome},
        "signals": {"exit_code": 0 if outcome == "completed" else 1},
        "invocation": {"script": {"basename": script}, "argv": [script]},
        "environment": {"variables": env_vars or []},
    }
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if stdout is not None:
        (d / "stdout.log").write_text(stdout, encoding="utf-8")
    return d


def _make_lock_run(runs_dir: Path, name: str, started: float, stdout: str = None) -> Path:
    d = runs_dir / f"pubrun-{name}"
    d.mkdir(parents=True, exist_ok=True)
    lock = {"run_id": name, "pid": 999999, "started_at_utc": started,
            "script": "train.py", "argv": ["train.py"], "hostname": "localhost"}
    (d / ".pubrun.lock").write_text(json.dumps(lock), encoding="utf-8")
    if stdout is not None:
        (d / "stdout.log").write_text(stdout, encoding="utf-8")
    return d


@pytest.fixture
def runs_cwd(tmp_path, monkeypatch):
    """A cwd containing ./runs so scan_runs() resolves to it."""
    monkeypatch.chdir(tmp_path)
    runs = tmp_path / "runs"
    runs.mkdir()
    return runs


def _call_main(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["pubrun"] + list(argv))
    m.main()


# ---------------------------------------------------------------- BUG-11: routing

class TestSubcommandRouting:

    def test_inspect_with_run_filter_routes_to_inspect(self, monkeypatch):
        calls = []
        monkeypatch.setattr(m, "_run_inspect", lambda *a, **k: calls.append((a, k)))

        def _no_popen(*a, **k):
            raise AssertionError("pubrun inspect -f run must not launch a child process")
        monkeypatch.setattr(subprocess, "Popen", _no_popen)
        _call_main(monkeypatch, "inspect", "-f", "run")
        assert len(calls) == 1
        assert calls[0][1]["filter_str"] == "run"

    @pytest.mark.parametrize("argv", [("help", "init"), ("init", "help")])
    def test_help_for_init(self, monkeypatch, capsys, argv):
        with pytest.raises(SystemExit) as ei:
            _call_main(monkeypatch, *argv)
        assert ei.value.code == 0
        assert "usage: pubrun init" in capsys.readouterr().out

    def test_help_inspect(self, monkeypatch, capsys):
        with pytest.raises(SystemExit) as ei:
            _call_main(monkeypatch, "help", "inspect")
        assert ei.value.code == 0
        assert "usage: pubrun inspect" in capsys.readouterr().out

    def test_run_selector_before_inspect(self, monkeypatch):
        calls = []
        monkeypatch.setattr(m, "_run_inspect", lambda *a, **k: calls.append(a))
        _call_main(monkeypatch, "1", "inspect")
        assert len(calls) == 1
        assert calls[0][0] == "1"


# ------------------------------------------------- BUG-43: combined filter detection

class TestCombinedFilters:

    def _three_runs(self, runs):
        now = time.time()
        for i, name in enumerate(("aaa111", "bbb222", "ccc333")):
            _make_run(runs, name, now - 100 * (i + 1), stdout=f"log-from-{name}\n")

    def test_not_status_keeps_all_matches(self, runs_cwd, capsys):
        self._three_runs(runs_cwd)
        m._run_combined([], str(runs_cwd), None, True, False, not_status_filter="failed")
        out = capsys.readouterr().out
        for name in ("aaa111", "bbb222", "ccc333"):
            assert f"log-from-{name}" in out

    def test_not_filter_keeps_all_matches(self, runs_cwd, capsys):
        self._three_runs(runs_cwd)
        m._run_combined([], str(runs_cwd), None, True, False, not_filter_str="zzz-nomatch")
        out = capsys.readouterr().out
        for name in ("aaa111", "bbb222", "ccc333"):
            assert f"log-from-{name}" in out


# ------------------------------------------------------ BUG-44: show run limiting

class TestShowRunLimit:

    def _setup(self, runs, monkeypatch):
        now = time.time()
        _make_run(runs, "new111", now - 10, script="train.py")
        _make_run(runs, "mid222", now - 20, script="train.py")
        _make_run(runs, "old333", now - 30, script="eval.py")
        calls = []
        monkeypatch.setattr(m, "_run_report", lambda rd, *a, **k: calls.append(Path(rd).name))
        return calls

    def test_bare_show_reports_only_most_recent(self, runs_cwd, monkeypatch):
        calls = self._setup(runs_cwd, monkeypatch)
        _call_main(monkeypatch, "show")
        assert calls == ["pubrun-new111"]

    def test_filtered_show_reports_all_matches(self, runs_cwd, monkeypatch):
        calls = self._setup(runs_cwd, monkeypatch)
        _call_main(monkeypatch, "show", "-f", "train")
        assert calls == ["pubrun-new111", "pubrun-mid222"]

    def test_explicit_limit_is_respected(self, runs_cwd, monkeypatch):
        calls = self._setup(runs_cwd, monkeypatch)
        _call_main(monkeypatch, "show", "-n", "2")
        assert calls == ["pubrun-new111", "pubrun-mid222"]


# ---------------------------------------------- BUG-68: diff with a manifest path

class TestDiffManifestPath:

    def test_single_manifest_path_alone_exits_1(self, runs_cwd, capsys):
        d = _make_run(runs_cwd, "only111", time.time() - 10)
        with pytest.raises(SystemExit) as ei:
            m._run_diff([str(d / "manifest.json")], None, True)
        assert ei.value.code == 1
        assert "no other runs" in capsys.readouterr().err

    def test_single_manifest_path_compares_against_other_run(self, runs_cwd, capsys):
        now = time.time()
        newer = _make_run(runs_cwd, "new111", now - 10, script="a.py")
        _make_run(runs_cwd, "old222", now - 20, script="b.py")
        m._run_diff([str(newer / "manifest.json")], None, True)
        captured = capsys.readouterr()
        assert "against most recent other run: pubrun-old222" in captured.err
        assert "a.py" in captured.out and "b.py" in captured.out


# ---------------------------------------------- invalid --older-than across the CLI

class TestOlderThanValueError:

    @pytest.mark.parametrize("argv", [
        ("status",),
        ("clean", "--yes"),
        ("combined",),
        ("show",),
        ("inspect",),
        ("methods", "--all"),
        ("methods",),
        ("res",),
    ])
    def test_invalid_older_than_exits_1_without_traceback(self, tmp_path, argv):
        _make_run(tmp_path / "runs", "abc123", time.time() - 10)
        r = run_pubrun(*argv, "--older-than", "bogus", cwd=tmp_path)
        assert r.returncode == 1, (r.stdout, r.stderr)
        assert "Traceback" not in r.stderr
        assert "Invalid --older-than value 'bogus'" in r.stderr


# ------------------------------------------------- BUG-42: lock-only exit codes

class TestLockOnlyExitCodes:

    def test_methods_lock_only_exits_1(self, runs_cwd, capsys):
        d = _make_lock_run(runs_cwd, "lock111", time.time() - 5)
        with pytest.raises(SystemExit) as ei:
            m._run_methods(str(d), "text")
        assert ei.value.code == 1
        assert "does not have a manifest.json" in capsys.readouterr().err

    def test_resources_lock_only_exits_1(self, runs_cwd, capsys):
        d = _make_lock_run(runs_cwd, "lock222", time.time() - 5)
        with pytest.raises(SystemExit) as ei:
            m._run_resources(str(d))
        assert ei.value.code == 1
        assert "does not have a manifest.json" in capsys.readouterr().err


# ---------------------------------------------- BUG-44: multi-run show logs

class TestShowLogsMultiRun:

    def test_lock_only_run_does_not_stop_loop(self, tmp_path):
        runs = tmp_path / "runs"
        now = time.time()
        _make_lock_run(runs, "lock111", now - 5, stdout="LOCK-RUN-OUTPUT\n")
        _make_run(runs, "done222", now - 50, stdout="DONE-RUN-OUTPUT\n")
        r = run_pubrun("show", "logs", "-f", "train", cwd=tmp_path)
        assert r.returncode == 0, r.stderr
        assert "LOCK-RUN-OUTPUT" in r.stdout
        assert "DONE-RUN-OUTPUT" in r.stdout

    def test_single_crashed_report_still_exits_1(self, tmp_path):
        d = _make_lock_run(tmp_path / "runs", "lock333", time.time() - 5)
        r = run_pubrun("report", str(d), cwd=tmp_path)
        assert r.returncode == 1


# ------------------------------------------------------------ BUG-45: bench

class TestBenchScheduler:

    def _fake_repo(self, tmp_path, monkeypatch):
        bench = tmp_path / "benchmarks"
        bench.mkdir()
        harness = bench / "harness.py"
        harness.write_text("", encoding="utf-8")
        (bench / "submit_bench_pbs.sh").write_text("exit 3\n", encoding="utf-8")
        monkeypatch.setattr(m, "_find_bench_harness", lambda: harness)
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)

    def test_failed_pbs_submission_exits_nonzero(self, tmp_path, monkeypatch, capsys):
        self._fake_repo(tmp_path, monkeypatch)
        monkeypatch.setattr(m, "_detect_schedulers",
                            lambda: [{"name": "pbs", "submit_script": "submit_bench_pbs.sh",
                                      "on_compute_node": False}])
        monkeypatch.setattr(subprocess, "run",
                            lambda cmd, *a, **k: subprocess.CompletedProcess(cmd, 3, "", "qsub: denied"))
        with pytest.raises(SystemExit) as ei:
            m._run_bench(None, None, True, False, True, True, False, False, scheduler="auto")
        assert ei.value.code != 0
        err = capsys.readouterr().err
        assert "Submitted." not in err
        assert "submission failed" in err

    def test_ambiguous_qsub_warns_when_nothing_detected(self, tmp_path, monkeypatch, capsys):
        self._fake_repo(tmp_path, monkeypatch)
        monkeypatch.setattr(m, "_detect_schedulers", lambda: [])
        monkeypatch.setattr(m, "_qsub_ambiguous", lambda: True)
        monkeypatch.setattr(subprocess, "run",
                            lambda cmd, *a, **k: subprocess.CompletedProcess(cmd, 1, "", ""))
        with pytest.raises(SystemExit):
            m._run_bench(None, None, True, False, False, False, False, False, scheduler="auto")
        err = capsys.readouterr().err
        assert "PBS-vs-SGE could not be determined" in err


# ------------------------------------------------------------ BUG-66: gist rollback

class TestGistRollback:

    def _gh(self, monkeypatch, create_out, api_out):
        deleted = []

        def fake(args, *, input_text=None, timeout=30):
            if args[:2] == ["gist", "create"]:
                return create_out
            if args[0] == "api":
                return api_out
            if args[:2] == ["gist", "delete"]:
                deleted.append(args[2])
                return ""
            raise AssertionError(f"unexpected gh call {args}")
        monkeypatch.setattr(m, "_run_gh", fake)
        return deleted

    def test_blank_page_url_raises_gh_error(self, tmp_path, monkeypatch):
        self._gh(monkeypatch, "   ", "{}")
        with pytest.raises(m._GhError):
            m._create_result_gist(tmp_path / "x.json")

    @pytest.mark.parametrize("api_out", [
        "this is not json",
        json.dumps({"files": {}}),
        json.dumps({"files": {"a": {}, "b": {}}}),
        json.dumps({"files": {"a": "not-a-dict"}}),
        json.dumps({"files": {"a": {"raw_url": "https://evil.example.com/r.json"}}}),
    ])
    def test_post_create_failure_deletes_gist(self, tmp_path, monkeypatch, api_out):
        deleted = self._gh(monkeypatch, "https://gist.github.com/u/abc123\n", api_out)
        with pytest.raises(m._GhError):
            m._create_result_gist(tmp_path / "x.json")
        assert deleted == ["abc123"]

    def test_submit_falls_back_to_inline_on_bad_metadata(self, tmp_path, monkeypatch):
        red = tmp_path / "g.redacted.json"
        red.write_text(json.dumps({"schema": "pubrun-benchmark/5",
                                   "machine": {"host": {"hostname": "<redacted>"}}}))
        deleted = self._gh(monkeypatch, "https://gist.github.com/u/abc123\n", "not json")
        monkeypatch.setattr(m, "_probe_gh", lambda: m.GhReadiness(True, True))
        monkeypatch.setattr(m, "_create_benchmark_issue",
                            lambda t, b, r: "https://github.com/fariello/pubrun/issues/9")
        res = m._submit_benchmark_result(str(red), "fariello/pubrun")
        assert res.submitted and res.method == "inline"
        assert deleted == ["abc123"]


# ------------------------------------------------------------ BUG-67a: --run-tests

class TestRunTests:

    def test_failed_pytest_exits_nonzero_and_uses_sys_executable(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "tests").mkdir()
        (tmp_path / "tox.ini").write_text("", encoding="utf-8")
        seen = []
        real_run = subprocess.run

        def fake(cmd, *a, **k):
            if isinstance(cmd, list) and cmd[1:3] == ["-m", "pytest"]:
                seen.append(cmd[0])
                return subprocess.CompletedProcess(cmd, 1)
            return real_run(cmd, *a, **k)
        monkeypatch.setattr(subprocess, "run", fake)
        with pytest.raises(SystemExit) as ei:
            m._run_tests()
        assert ei.value.code == 1
        assert seen == [sys.executable]

    def test_mock_script_failure_exits_nonzero(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(subprocess, "run",
                            lambda cmd, *a, **k: subprocess.CompletedProcess(cmd, 2, "", ""))
        with pytest.raises(SystemExit) as ei:
            m._run_tests()
        assert ei.value.code == 1

    def test_mock_script_without_manifest_exits_nonzero(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(subprocess, "run",
                            lambda cmd, *a, **k: subprocess.CompletedProcess(cmd, 0, "", ""))
        with pytest.raises(SystemExit) as ei:
            m._run_tests()
        assert ei.value.code == 1
        assert "Validation complete" not in capsys.readouterr().out


# ------------------------------------------------------ BUG-12 / BUG-50 / BUG-64: diff

def _env_manifest(*variables):
    return {"environment": {"variables": list(variables)}}


class TestDiffEngine:

    def test_changed_hash_value_is_modified(self):
        a = _env_manifest({"name": "API_KEY", "value": {"representation": "hashed",
                           "hash_algorithm": "sha256", "hash_value": "aaa"}})
        b = _env_manifest({"name": "API_KEY", "value": {"representation": "hashed",
                           "hash_algorithm": "sha256", "hash_value": "bbb"}})
        rep = compare_manifests(a, b)
        assert "environment.API_KEY" in rep["modified"]

    def test_hashed_and_redacted_differ_from_empty_plain(self):
        plain = _env_manifest({"name": "K", "value": {"representation": "plain", "value": ""}})
        redacted = _env_manifest({"name": "K", "value": {"representation": "redacted"}})
        hashed = _env_manifest({"name": "K", "value": {"representation": "hashed",
                                "hash_value": "abc"}})
        assert "environment.K" in compare_manifests(plain, redacted)["modified"]
        assert "environment.K" in compare_manifests(plain, hashed)["modified"]
        assert "environment.K" in compare_manifests(redacted, hashed)["modified"]

    def test_identical_hashes_are_same(self):
        v = {"name": "K", "value": {"representation": "hashed", "hash_value": "abc"}}
        rep = compare_manifests(_env_manifest(v), _env_manifest(dict(v)), show_same=True)
        assert rep["modified"] == {}
        assert "environment.K" in rep["same"]

    @pytest.mark.parametrize("key", ["invocation.script.path", "invocation.script.real_path",
                                     "filesystem.run_dir.path", "data_files.inputs.0.path"])
    def test_non_env_path_fields_are_scalar(self, key):
        assert _is_path_var(key) is False

    @pytest.mark.parametrize("key", ["environment.PATH", "environment.LD_LIBRARY_PATH",
                                     "environment.PythonPath"])
    def test_env_path_vars_split(self, key):
        assert _is_path_var(key) is True

    def test_script_path_change_is_standard_diff(self):
        a = {"invocation": {"script": {"path": "/a/train.py"}}}
        b = {"invocation": {"script": {"path": "/b/train.py"}}}
        mod = compare_manifests(a, b)["modified"]["invocation.script.path"]
        assert mod == {"type": "standard", "old": "/a/train.py", "new": "/b/train.py"}

    def test_reordered_path_records_order_changed(self):
        old = os.pathsep.join(["/x", "/y", "/z"])
        new = os.pathsep.join(["/z", "/x", "/y"])
        a = _env_manifest({"name": "PATH", "value": old})
        b = _env_manifest({"name": "PATH", "value": new})
        mod = compare_manifests(a, b)["modified"]["environment.PATH"]
        assert mod["type"] == "path_split"
        assert mod["added"] == [] and mod["removed"] == []
        assert mod["order_changed"] is True
        assert mod["old"] == old and mod["new"] == new

    def test_path_add_without_reorder(self):
        a = _env_manifest({"name": "PATH", "value": os.pathsep.join(["/x", "/y"])})
        b = _env_manifest({"name": "PATH", "value": os.pathsep.join(["/x", "/new", "/y"])})
        mod = compare_manifests(a, b)["modified"]["environment.PATH"]
        assert mod["added"] == ["/new"]
        assert mod["order_changed"] is False

    def test_ignore_respects_dot_boundary(self):
        a = _env_manifest({"name": "FOO", "value": "1"}, {"name": "FOO_BAR", "value": "1"},
                          {"name": "FOO.sub", "value": "1"})
        b = _env_manifest({"name": "FOO", "value": "2"}, {"name": "FOO_BAR", "value": "2"},
                          {"name": "FOO.sub", "value": "2"})
        mod = compare_manifests(a, b, ignores=["environment.FOO"])["modified"]
        assert "environment.FOO" not in mod
        assert "environment.FOO.sub" not in mod
        assert "environment.FOO_BAR" in mod

    def test_ignore_with_trailing_dot_and_wildcard(self):
        a = {"git": {"commit": "a", "dirty": False}, "gitx": {"v": 1}}
        b = {"git": {"commit": "b", "dirty": True}, "gitx": {"v": 2}}
        mod = compare_manifests(a, b, ignores=["git."])["modified"]
        assert "git.commit" not in mod and "gitx.v" in mod
        mod = compare_manifests(a, b, ignores=["git*"])["modified"]
        assert mod == {}


# ---------------------------------------------------------------- BUG-50 / BUG-64: render

class TestRender:

    def _reordered_path_report(self):
        a = _env_manifest({"name": "PATH", "value": os.pathsep.join(["/x", "/y"])})
        b = _env_manifest({"name": "PATH", "value": os.pathsep.join(["/y", "/x"])})
        return compare_manifests(a, b)

    def test_inline_shows_order_change(self, capsys):
        print_diff(self._reordered_path_report(), no_color=True)
        out = capsys.readouterr().out
        assert "[ORDER CHANGED]" in out
        assert os.pathsep.join(["/x", "/y"]) in out
        assert os.pathsep.join(["/y", "/x"]) in out

    def test_table_shows_reordered(self, capsys):
        print_diff(self._reordered_path_report(), no_color=True, table=True)
        out = capsys.readouterr().out
        assert "environment.PATH" in out
        assert "reordered" in out

    def test_table_renders_same_rows_when_no_differences(self, capsys):
        rep = compare_manifests({"a": 1, "b": "x"}, {"a": 1, "b": "x"}, show_same=True)
        print_diff(rep, no_color=True, table=True)
        lines = capsys.readouterr().out.splitlines()
        assert "(no differences)" in lines
        assert any(line.startswith("=") and "a" in line for line in lines)
        assert any(line.startswith("=") and "b" in line for line in lines)

    def test_table_truncates_added_removed_same(self, capsys):
        long_val = "v" * 50
        rep = {"added": {"k_add": long_val}, "removed": {"k_rem": long_val},
               "modified": {}, "same": {"k_same": long_val}}
        print_diff(rep, no_color=True, table=True, max_length=10)
        out = capsys.readouterr().out
        assert long_val not in out
        assert out.count("v" * 10 + " ...") == 3

    def test_inline_list_diff_bool_int_common_not_marked_moved(self, capsys):
        rep = compare_manifests({"vals": [1, 2]}, {"vals": [2, True]})
        print_diff(rep, no_color=True, depth="standard")
        out = capsys.readouterr().out
        assert "[2, +True]" in out
        assert "[-1, 2]" in out

    def test_inline_list_diff_bool_int_reorder_marked(self, capsys):
        rep = compare_manifests({"vals": [True, 1, 3]}, {"vals": [1, True, 4]})
        print_diff(rep, no_color=True, depth="deep")
        out = capsys.readouterr().out
        assert "[~True, ~1, -3]" in out
        assert "[~1, ~True, +4]" in out

    def test_inline_list_diff_false_zero_distinct(self, capsys):
        rep = compare_manifests({"vals": [0, 5]}, {"vals": [5, False]})
        print_diff(rep, no_color=True, depth="standard")
        out = capsys.readouterr().out
        assert "[-0, 5]" in out
        assert "[5, +False]" in out


# ------------------------------------------- BUG-U3/U5/U7/U9/U11/U12 (IPD kk83rk)

class TestCliSelectorsAndFixesKk83rk:
    """Regression tests for CLI directory selectors, --dir expansion, diff guard, show, and bench."""

    def test_status_accepts_direct_run_dir_inside_and_outside_output_dir(self, tmp_path, monkeypatch, capsys):
        runs_dir = tmp_path / "runs"
        now = time.time()
        _make_run(runs_dir, "newer111", now - 10, script="new.py")
        older = _make_run(runs_dir, "older222", now - 20, script="old.py")
        ext_root = tmp_path / "external"
        ext_run = _make_run(ext_root, "ext33333", now - 30, script="ext.py")

        # Text inspection via direct run directory path and manifest.json path.
        m.main(["pubrun", "--no-color", "status", str(older), "--dir", str(runs_dir)])
        assert "older222" in capsys.readouterr().out

        m.main(["pubrun", "--no-color", "status", str(ext_run / "manifest.json"), "--dir", str(runs_dir)])
        assert "ext33333" in capsys.readouterr().out

        # --json inside output_dir preserves recency index (2 for older222).
        m.main(["pubrun", "--no-color", "status", str(older), "--dir", str(runs_dir), "--json"])
        in_payload = json.loads(capsys.readouterr().out)
        assert in_payload["run"]["run_id"] == "older222"
        assert in_payload["run"]["index"] == 2

        # --json outside output_dir succeeds with index: null.
        m.main(["pubrun", "--no-color", "status", str(ext_run), "--dir", str(runs_dir), "--json"])
        ext_payload = json.loads(capsys.readouterr().out)
        assert ext_payload["run"]["run_id"] == "ext33333"
        assert ext_payload["run"]["index"] is None

        # An unrelated directory without manifest/lock/logs is still rejected.
        not_a_run = tmp_path / "not_a_run"
        not_a_run.mkdir()
        with pytest.raises(SystemExit) as ei:
            m.main(["pubrun", "--no-color", "status", str(not_a_run), "--dir", str(runs_dir)])
        assert ei.value.code == 1

    def test_combined_accepts_direct_run_dir_and_log_only_dir(self, tmp_path, capsys):
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        ext_a = _make_run(
            tmp_path / "ext",
            "extA1111",
            1000.0,
            stdout="[2026-06-19T22:00:00.000Z] from-ext-a\n",
        )
        log_only = tmp_path / "custom-log-dir"
        log_only.mkdir()
        (log_only / "stdout.log").write_text("[2026-06-19T22:00:01.000Z] from-log-only\n", encoding="utf-8")

        m.main(["pubrun", "--no-color", "combined", "--dir", str(runs_dir), str(ext_a), str(log_only)])
        lines = capsys.readouterr().out.strip().splitlines()
        assert lines == [
            "[extA1111][stdout] [2026-06-19T22:00:00.000Z] from-ext-a",
            "[custom-log-dir][stdout] [2026-06-19T22:00:01.000Z] from-log-only",
        ]

        # Single manifest.json direct path works too.
        m.main(["pubrun", "--no-color", "combined", "--dir", str(runs_dir), str(ext_a / "manifest.json")])
        assert capsys.readouterr().out.strip() == "[stdout] [2026-06-19T22:00:00.000Z] from-ext-a"

    def test_status_dir_expands_env_var_and_tilde(self, tmp_path, monkeypatch, capsys):
        custom_runs = tmp_path / "custom_runs"
        _make_run(custom_runs, "envdir01", time.time() - 5, script="env_test.py")
        monkeypatch.setenv("TEST_RUNS_DIR", str(custom_runs))

        m.main(["pubrun", "--no-color", "status", "--dir", "$TEST_RUNS_DIR", "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert payload["total_runs"] == 1
        assert payload["runs"][0]["run_id"] == "envdir01"

        # Tilde expansion via HOME/USERPROFILE.
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        m.main(["pubrun", "--no-color", "status", "--dir", "~/custom_runs", "--json"])
        tilde_payload = json.loads(capsys.readouterr().out)
        assert tilde_payload["total_runs"] == 1
        assert tilde_payload["runs"][0]["run_id"] == "envdir01"

    def test_diff_recency_selectors_not_hijacked_by_cwd_numeric_dirs(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        # Ordinary folders named ./1 and ./2 in CWD must NOT hijack `diff --dir <other> 1 2`.
        (tmp_path / "1").mkdir()
        (tmp_path / "2").mkdir()

        other_runs = tmp_path / "other_runs"
        now = time.time()
        _make_run(other_runs, "new11111", now - 10, script="newest.py")
        _make_run(other_runs, "old22222", now - 20, script="older.py")

        m.main(["pubrun", "--no-color", "diff", "--dir", str(other_runs), "1", "2"])
        out = capsys.readouterr().out
        assert "newest.py" in out
        assert "older.py" in out

    def test_show_section_before_run_selector_swaps_and_double_section_exits_2(self, tmp_path, capsys):
        runs_dir = tmp_path / "runs"
        now = time.time()
        _make_run(
            runs_dir,
            "first111",
            now - 10,
            env_vars=[{"name": "TARGET_ENV", "value": {"representation": "plain", "value": "from_first"}}],
        )
        _make_run(
            runs_dir,
            "second22",
            now - 20,
            env_vars=[{"name": "TARGET_ENV", "value": {"representation": "plain", "value": "from_second"}}],
        )

        m.main(["pubrun", "--no-color", "show", "--dir", str(runs_dir), "env", "2"])
        out = capsys.readouterr().out
        assert "TARGET_ENV=from_second" in out
        assert "from_first" not in out

        with pytest.raises(SystemExit) as ei:
            m.main(["pubrun", "--no-color", "show", "--dir", str(runs_dir), "env", "logs"])
        assert ei.value.code == 2
        err = capsys.readouterr().err
        assert "env" in err and "logs" in err

    def test_bench_local_prepare_submission_failure_exits_1(self, tmp_path, monkeypatch):
        bench_dir = tmp_path / "benchmarks"
        bench_dir.mkdir()
        harness = bench_dir / "harness.py"
        harness.write_text("", encoding="utf-8")

        monkeypatch.setattr(m, "_find_bench_harness", lambda: harness)
        monkeypatch.setattr(m, "_detect_schedulers", lambda: [])
        monkeypatch.setattr(m, "_print_safe_file_block", lambda *a, **k: None)
        monkeypatch.setattr(m, "_prepare_submission", lambda *a, **k: None)
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
        monkeypatch.setenv("PUBRUN_RESULTS_DIR", str(tmp_path / "results"))
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda cmd, *a, **k: subprocess.CompletedProcess(cmd, 0, "", ""),
        )

        with pytest.raises(SystemExit) as ei:
            m._run_bench(
                None, None, True, True, False, False, False, False,
                prepare_submission=True,
            )
        assert ei.value.code == 1

    def test_show_utc_on_locked_crashed_run_and_single_scan_on_filtered_show(self, tmp_path, monkeypatch, capsys):
        runs_dir = tmp_path / "runs"
        locked = runs_dir / "pubrun-locked01"
        locked.mkdir(parents=True)
        # 1700000000.0 == 2023-11-14 22:13:20 UTC
        lock_payload = {
            "run_id": "locked01",
            "pid": 999999,
            "started_at_utc": 1700000000.0,
            "script": "train.py",
            "argv": ["train.py"],
            "hostname": "remote-other-host",
        }
        (locked / ".pubrun.lock").write_text(json.dumps(lock_payload), encoding="utf-8")

        with pytest.raises(SystemExit) as ei:
            m.main(["pubrun", "--no-color", "show", str(locked), "--dir", str(runs_dir), "--utc"])
        assert ei.value.code == 1
        err = capsys.readouterr().err
        assert "2023-11-14 22:13:20Z" in err

        # Filtered `show` across multiple matching runs calls scan_runs exactly once.
        multi_runs = tmp_path / "multi_runs"
        now = time.time()
        _make_run(multi_runs, "mrun0001", now - 10, script="train.py")
        _make_run(multi_runs, "mrun0002", now - 20, script="train.py")
        _make_run(multi_runs, "mrun0003", now - 30, script="train.py")

        import pubrun.status as status_mod

        real_scan = status_mod.scan_runs
        scan_count = 0

        def _spy_scan(*args, **kwargs):
            nonlocal scan_count
            scan_count += 1
            return real_scan(*args, **kwargs)

        monkeypatch.setattr(status_mod, "scan_runs", _spy_scan)
        m.main(["pubrun", "--no-color", "show", "--dir", str(multi_runs), "-f", "train"])
        out = capsys.readouterr().out
        assert scan_count == 1
        for rid in ("mrun0001", "mrun0002", "mrun0003"):
            assert rid in out
