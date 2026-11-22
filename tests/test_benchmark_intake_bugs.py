"""Regression tests for the benchmark redaction, intake-validation, and aggregation bugs
fixed by IPD 8k73qj (Set bugs-audit): BUG-18..24 and BUG-54..56.

The modules under test live outside the package (benchmarks/ and .github/scripts/), so each
is loaded from its file path, the same way their own test suites load them.
"""
import copy
import importlib.util
import json
import sys
import urllib.error
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_BENCH = _REPO / "benchmarks"
_SCRIPTS = _REPO / ".github" / "scripts"
_FX = _SCRIPTS / "test_fixtures"

for _p in (str(_BENCH), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ss = _load("share_safety", _BENCH / "share_safety.py")
h = _load("_bugs_harness", _BENCH / "harness.py")
agg = _load("aggregate", _BENCH / "aggregate.py")
x = _load("extract_attachment_url", _SCRIPTS / "extract_attachment_url.py")
v = _load("validate_benchmark_submission", _SCRIPTS / "validate_benchmark_submission.py")


def _safe_result():
    return {
        "schema": "pubrun-benchmark/5",
        "machine": {
            "host": {"os_name": "Linux", "hostname": "<redacted>"},
            "python": {"executable": "<redacted>", "prefix": "<redacted>",
                       "base_prefix": "<redacted>", "virtual_env": "<redacted>"},
            "python_executable": "<redacted>",
        },
    }


# ------------------------------------------------------------------ BUG-18: None is safe

class TestShareSafetyNone:

    def test_virtual_env_none_is_safe(self):
        r = _safe_result()
        r["machine"]["python"]["virtual_env"] = None
        ok, reasons = ss.check_share_safe(r)
        assert ok, reasons

    def test_every_must_be_redacted_field_may_be_none(self):
        r = _safe_result()
        for key in ("executable", "prefix", "base_prefix", "virtual_env"):
            r["machine"]["python"][key] = None
        r["machine"]["host"]["hostname"] = None
        r["machine"]["python_executable"] = None
        r["machine"]["slurm"] = {"node": None, "job_id": None, "partition": "gpu"}
        ok, reasons = ss.check_share_safe(r)
        assert ok, reasons

    def test_non_none_unredacted_value_still_rejected(self):
        r = _safe_result()
        r["machine"]["python"]["virtual_env"] = "venv-name"
        ok, reasons = ss.check_share_safe(r)
        assert not ok
        assert any("machine.python.virtual_env" in m for m in reasons)
        assert all("venv-name" not in m for m in reasons)


# ------------------------------------------------- BUG-19: Slurm node / job id redaction

class TestSlurmRedaction:

    def _with_slurm(self, job_id):
        return {
            "schema": "pubrun-benchmark/5",
            "machine": {"host": {"hostname": "login-1"},
                        "slurm": {"node": "cn-0423", "job_id": job_id, "partition": "compute",
                                  "cpus_per_task": "8", "mem_per_node": "16000",
                                  "num_nodes": "1"}},
        }

    @pytest.mark.parametrize("job_id", ["4815162342", 4815162342])
    def test_redact_result_masks_node_and_job_id(self, job_id):
        red = h.redact_result(self._with_slurm(job_id))
        slurm = red["machine"]["slurm"]
        assert slurm["node"] == "<redacted>"
        assert slurm["job_id"] == "<redacted>"
        assert slurm["partition"] == "compute"
        assert slurm["cpus_per_task"] == "8"
        assert slurm["mem_per_node"] == "16000"
        assert slurm["num_nodes"] == "1"
        assert "cn-0423" not in json.dumps(red)
        ok, reasons = ss.check_share_safe(red)
        assert ok, reasons

    def test_redact_result_leaves_absent_slurm_fields_absent(self):
        red = h.redact_result({"machine": {"slurm": {"partition": "debug"}}})
        assert red["machine"]["slurm"] == {"partition": "debug"}

    @pytest.mark.parametrize("field,value", [("node", "cn-0423"), ("job_id", "12345"),
                                             ("job_id", 12345)])
    def test_check_share_safe_rejects_unredacted_slurm(self, field, value):
        r = _safe_result()
        r["machine"]["slurm"] = {field: value, "partition": "compute"}
        ok, reasons = ss.check_share_safe(r)
        assert not ok
        assert any(f"machine.slurm.{field}" in m for m in reasons)
        assert all(str(value) not in m for m in reasons)


# ------------------------------------------- BUG-20: boundary-safe username substring scrub

class TestScrubBoundaries:

    @pytest.mark.parametrize("user", ["ed", "mark", "pub", "run", "benchmark"])
    def test_short_username_does_not_corrupt_markers_or_schema(self, user, monkeypatch):
        import getpass
        monkeypatch.setattr(getpass, "getuser", lambda: user)
        monkeypatch.setenv("HOME", "/nonexistent-home-for-test")
        result = {
            "schema": "pubrun-benchmark/5",
            "mode": "default",
            "machine": {"host": {"hostname": "box", "os_name": "Linux"},
                        "pubrun_version": "1.4.0"},
            "scenario_defs": {"s": {"group": "startup", "mode": "auto",
                                    "workload": "noop.py", "config": {}}},
            "note": f"started by {user} in /data/{user}/work; marked as edited",
        }
        red = h.redact_result(result)
        assert red["schema"] == "pubrun-benchmark/5"
        assert red["machine"]["host"]["hostname"] == "<redacted>"
        assert red["scenario_defs"]["s"]["group"] == "startup"
        assert red["mode"] == "default"
        # Standalone and path-embedded usernames are scrubbed; containing words survive.
        assert red["note"] == "started by <redacted> in /data/<redacted>/work; marked as edited"

    def test_pre_redacted_value_is_not_rescanned(self):
        out = h._scrub_pii_substrings({"a": "<redacted>", "b": "x <redacted> ed"}, ["ed"])
        assert out == {"a": "<redacted>", "b": "x <redacted> <redacted>"}

    def test_path_needle_replaced_literally_longest_first(self):
        out = h._scrub_pii_substrings(
            ["/srv/users/ed/project/src", "user ed", "/data/edward/x"], ["ed", "/srv/users/ed"])
        # The longer path needle wins, so the result is one marker, not a nested one.
        assert out[0] == "<redacted>/project/src"
        assert out[1] == "user <redacted>"
        # `ed` only matches at identifier boundaries, so `edward` is kept.
        assert out[2] == "/data/edward/x"

    def test_non_string_values_untouched(self):
        out = h._scrub_pii_substrings({"n": 3, "f": 0.5, "b": True, "z": None}, ["ed"])
        assert out == {"n": 3, "f": 0.5, "b": True, "z": None}


# --------------------------------------------- BUG-54: failed self-check refuses to write

class TestHarnessSelfCheckGate:

    def _run_main(self, monkeypatch, tmp_path, redacted):
        out = tmp_path / "out" / "r.redacted.json"
        monkeypatch.setattr(h, "run", lambda *a, **k: {"schema": "pubrun-benchmark/5"})
        monkeypatch.setattr(h, "redact_result", lambda r: redacted)
        monkeypatch.setattr(sys, "argv", ["harness.py", "--quick", "--redacted-out", str(out)])
        return out

    def test_failed_self_check_exits_nonzero_and_writes_nothing(self, monkeypatch, tmp_path,
                                                                capsys):
        bad = _safe_result()
        bad["machine"]["host"]["hostname"] = "build-box-07"
        out = self._run_main(monkeypatch, tmp_path, bad)
        with pytest.raises(SystemExit) as ei:
            h.main()
        assert ei.value.code == 1
        assert not out.exists()
        err = capsys.readouterr().err
        assert "self-check FAILED" in err
        assert "build-box-07" not in err

    def test_self_check_exception_exits_nonzero(self, monkeypatch, tmp_path):
        out = self._run_main(monkeypatch, tmp_path, _safe_result())

        def _boom(_r):
            raise RuntimeError("boom")
        monkeypatch.setattr(ss, "check_share_safe", _boom)
        with pytest.raises(SystemExit) as ei:
            h.main()
        assert ei.value.code == 1
        assert not out.exists()

    def test_passing_self_check_writes_file(self, monkeypatch, tmp_path):
        out = self._run_main(monkeypatch, tmp_path, _safe_result())
        h.main()
        assert json.loads(out.read_text(encoding="utf-8")) == _safe_result()


# --------------------------------------------- BUG-22/23: extractor URL safety and https

class TestExtractorUrlSafety:

    @pytest.mark.parametrize("body", [
        "https://[invalid/a.json",
        "https://github.com:99999/a.json",
        "https://github.com:abc/a.json",
    ])
    def test_malformed_url_does_not_raise(self, body):
        url, error = x.find_attachment_url(body)
        assert url == ""
        assert error

    def test_malformed_url_skipped_then_valid_wins(self):
        good = "https://github.com/user-attachments/files/1/r.json"
        url, error = x.find_attachment_url(f"https://[bad/a.json then {good}")
        assert url == good and error == ""

    def test_http_allowlisted_json_rejected_with_https_error(self):
        url, error = x.find_attachment_url("http://github.com/user-attachments/files/1/r.json")
        assert url == ""
        assert "HTTPS" in error

    def test_resolve_source_rejects_http(self):
        kind, url, _file, error = x.resolve_source(
            "http://objects.githubusercontent.com/a/r.json")
        assert kind == "none" and url == "" and "HTTPS" in error

    def test_existing_errors_preserved(self):
        assert "empty" in x.find_attachment_url("")[1]
        assert "no URL" in x.find_attachment_url("nothing here")[1]
        assert "allowlist" in x.find_attachment_url("https://evil.example.com/a.json")[1]
        assert "not a .json" in x.find_attachment_url("https://github.com/a/b.png")[1]


# ---------------------------------------------- BUG-22/23: validator download hardening

class TestValidatorDownload:

    @pytest.mark.parametrize("url", [
        "http://github.com/a.json",
        "ftp://github.com/a.json",
        "file://github.com/etc/a.json",
        "https://[invalid/a.json",
        "https://github.com:99999/a.json",
    ])
    def test_bad_initial_url_rejected_before_fetch(self, url, tmp_path, monkeypatch):
        import urllib.request

        def _no_open(*a, **k):
            raise AssertionError("network must not be touched")
        monkeypatch.setattr(urllib.request.OpenerDirector, "open", _no_open)
        with pytest.raises(v.Reject) as ei:
            v._download(url, tmp_path / "s.json")
        assert ei.value.stage == "shape"

    def _redirect_handler(self, monkeypatch):
        """Capture the redirect handler class that _download installs."""
        import urllib.request
        captured = {}
        real_build = urllib.request.build_opener

        def _build(*handlers):
            captured["cls"] = handlers[0]
            raise urllib.error.URLError("stop after capture")
        monkeypatch.setattr(urllib.request, "build_opener", _build)
        with pytest.raises((v.Reject, urllib.error.URLError)):
            v._download("https://github.com/a.json", Path("/nonexistent/s.json"))
        monkeypatch.setattr(urllib.request, "build_opener", real_build)
        return captured["cls"]

    def test_redirect_limits_bounded(self, monkeypatch):
        cls = self._redirect_handler(monkeypatch)
        assert cls.max_redirections == 3
        assert cls.max_repeats == 3

    @pytest.mark.parametrize("newurl", [
        "http://github.com/a.json",
        "https://evil.example.com/a.json",
        "https://[invalid/a.json",
    ])
    def test_redirect_downgrade_or_offlist_rejected(self, newurl, monkeypatch):
        import urllib.request
        cls = self._redirect_handler(monkeypatch)
        req = urllib.request.Request("https://github.com/a.json")
        with pytest.raises(v.Reject) as ei:
            cls().redirect_request(req, None, 302, "Found", {}, newurl)
        assert ei.value.stage == "shape"

    def test_redirect_allowed_target_proceeds(self, monkeypatch):
        import urllib.request
        cls = self._redirect_handler(monkeypatch)
        req = urllib.request.Request("https://github.com/a.json")
        new = cls().redirect_request(req, None, 302, "Found", {},
                                     "https://objects.githubusercontent.com/a.json")
        assert new is not None
        assert new.full_url == "https://objects.githubusercontent.com/a.json"

    def test_excess_redirects_rejected(self, monkeypatch, tmp_path):
        """More than 3 redirects (all on allowlisted https hosts) is a clean shape rejection."""
        import io
        import urllib.request

        class _Redirector(urllib.request.BaseHandler):
            handler_order = 100
            count = 0

            def https_open(self, req):
                _Redirector.count += 1
                fp = io.BytesIO(b"")
                hdrs = {"Location": f"https://github.com/hop{_Redirector.count}.json"}
                import email.message
                msg = email.message.Message()
                for k, val in hdrs.items():
                    msg[k] = val
                resp = urllib.response.addinfourl(fp, msg, req.full_url, 302)
                resp.msg = "Found"
                return resp

        import urllib.response
        real_build = urllib.request.build_opener

        def _build(*handlers):
            return real_build(_Redirector, *handlers)
        monkeypatch.setattr(urllib.request, "build_opener", _build)
        with pytest.raises(v.Reject) as ei:
            v._download("https://github.com/start.json", tmp_path / "s.json")
        assert ei.value.stage == "shape"
        assert _Redirector.count <= 4
        assert not (tmp_path / "s.json").exists()

    @pytest.mark.parametrize("exc", [
        TimeoutError("t"), OSError("o"), ValueError("v"),
        urllib.error.URLError("u"),
    ])
    def test_transport_errors_become_rejects(self, exc, monkeypatch, tmp_path):
        import urllib.request

        def _raise(*a, **k):
            raise exc
        monkeypatch.setattr(urllib.request.OpenerDirector, "open", _raise)
        with pytest.raises(v.Reject) as ei:
            v._download("https://github.com/a.json", tmp_path / "s.json")
        assert ei.value.stage == "shape"

    def test_http_exception_becomes_reject(self, monkeypatch, tmp_path):
        import http.client
        import urllib.request

        def _raise(*a, **k):
            raise http.client.InvalidURL("bad")
        monkeypatch.setattr(urllib.request.OpenerDirector, "open", _raise)
        with pytest.raises(v.Reject) as ei:
            v._download("https://github.com/a.json", tmp_path / "s.json")
        assert ei.value.stage == "shape"


# --------------------------------------------- BUG-22/55: parse UTF-8 and NaN/Infinity

class TestValidatorParse:

    def test_invalid_utf8_rejected_at_parse(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_bytes(b'{"schema": "\xff\xfe"}')
        verdict = v.validate_file(f)
        assert verdict["accepted"] is False
        assert verdict["stage"] == "parse"

    @pytest.mark.parametrize("const", ["NaN", "Infinity", "-Infinity"])
    def test_non_standard_constants_rejected_at_parse(self, const, tmp_path):
        f = tmp_path / "c.json"
        f.write_text('{"schema": "pubrun-benchmark/5", "x": %s}' % const, encoding="utf-8")
        verdict = v.validate_file(f)
        assert verdict["accepted"] is False
        assert verdict["stage"] == "parse"

    def test_nan_in_timings_rejected_at_parse(self, tmp_path):
        data = json.loads((_FX / "valid.json").read_text(encoding="utf-8"))
        text = json.dumps(data)
        first_scn = next(iter(data["pass_results"][0]["timings"]))
        data["pass_results"][0]["timings"][first_scn] = [float("nan")]
        text = json.dumps(data)  # emits a bare NaN token
        assert "NaN" in text
        f = tmp_path / "nan.json"
        f.write_text(text, encoding="utf-8")
        verdict = v.validate_file(f)
        assert verdict["accepted"] is False and verdict["stage"] == "parse"


# -------------------------------------------- BUG-21: schema reasons never echo payload

class TestSchemaReasonPayloadFree:

    @pytest.fixture(autouse=True)
    def _need_jsonschema(self):
        pytest.importorskip("jsonschema")

    def _valid(self):
        return json.loads((_FX / "valid.json").read_text(encoding="utf-8"))

    def test_bad_value_not_echoed(self):
        d = self._valid()
        d["mode"] = {"secret": "SECRET-VALUE-123"}
        with pytest.raises(v.Reject) as ei:
            v.check_schema(d)
        assert ei.value.stage == "schema"
        assert "SECRET-VALUE-123" not in ei.value.reason
        assert "secret" not in ei.value.reason
        assert "validator `" in ei.value.reason and "schema path `" in ei.value.reason

    def test_user_supplied_key_not_echoed(self):
        d = self._valid()
        d["ATTACKER-KEY-xyz"] = 1
        with pytest.raises(v.Reject) as ei:
            v.check_schema(d)
        assert "ATTACKER-KEY-xyz" not in ei.value.reason
        assert "additionalProperties" in ei.value.reason

    def test_mixed_int_and_str_paths_sort_without_typeerror(self):
        d = self._valid()
        d["pass_results"][0] = "not-an-object"   # error under an int path component
        d["iterations"] = "LEAK-ITER"            # error under a str path component
        d["extra-LEAK-KEY"] = True
        with pytest.raises(v.Reject) as ei:
            v.check_schema(d)
        assert ei.value.stage == "schema"
        for leak in ("not-an-object", "LEAK-ITER", "extra-LEAK-KEY"):
            assert leak not in ei.value.reason


# ------------------------------------------------------------- BUG-24: aggregate hardening

def _run5(group="startup", machine=None):
    return {
        "schema": "pubrun-benchmark/5",
        "machine": machine if machine is not None else
        {"host": {"os_name": "Linux"},
         "hardware": {"cpu": {"model": "CPU", "logical_cores": 4}}},
        "scenario_defs": {"baseline-noop": {"group": "startup", "mode": "auto",
                                            "workload": "noop.py"},
                          "s": {"group": group, "mode": "auto", "workload": "noop.py"}},
        "pass_results": [{"pass": 1, "timings": {"baseline-noop": [0.1, 0.1],
                                                 "s": [0.2, 0.3]}}],
    }


class TestAggregateHardening:

    def test_group_null_does_not_crash(self, tmp_path):
        rows = agg.build_rows([_run5(group=None), _run5()])
        groups = {r["scenario"]: r["group"] for r in rows if r["scenario"] == "s"}
        assert groups["s"] in ("?", "startup")
        assert any(r["group"] == "?" for r in rows)
        agg.write_markdown(rows, tmp_path / "s.md")
        agg.write_csv(rows, tmp_path / "s.csv")
        assert "| ? |" in (tmp_path / "s.md").read_text(encoding="utf-8")

    @pytest.mark.parametrize("machine", [
        "not-a-dict",
        {"hardware": "x", "host": ["y"]},
        {"hardware": {"cpu": "z"}, "host": {"os_name": "Linux"}},
        {"hardware": {"cpu": {"model": None}}, "host": None},
    ])
    def test_non_dict_machine_blocks_do_not_crash(self, machine):
        rows = agg.build_rows([_run5(machine=machine)])
        assert rows
        assert rows[0]["machine"].startswith("?/") or rows[0]["machine"].startswith("Linux/")
        assert "/?/" in rows[0]["machine"] or rows[0]["machine"].split("/")[1] == "?"

    def test_non_dict_json_skipped_with_warning(self, tmp_path, capsys):
        a = tmp_path / "a.json"
        a.write_text("[1, 2, 3]", encoding="utf-8")
        b = tmp_path / "b.json"
        b.write_text('"just a string"', encoding="utf-8")
        c = tmp_path / "c.json"
        c.write_text(json.dumps(_run5()), encoding="utf-8")
        runs = agg._load([str(a), str(b), str(c)])
        assert len(runs) == 1
        err = capsys.readouterr().err
        assert "a.json" in err and "b.json" in err

    def test_non_dict_scenario_entries_ignored(self):
        run = _run5()
        run["scenario_defs"]["junk"] = "not-a-dict"
        run["pass_results"][0]["timings"]["s"] = "nope"
        rows = agg.build_rows([run, {"schema": "pubrun-benchmark/4", "scenarios": {"a": 1}}])
        assert {r["scenario"] for r in rows} == {"baseline-noop", "s"}

    def test_writers_create_missing_parent_dirs(self, tmp_path):
        rows = agg.build_rows([_run5()])
        csv_path = tmp_path / "new" / "deeper" / "summary.csv"
        md_path = tmp_path / "other" / "summary.md"
        agg.write_csv(rows, csv_path)
        agg.write_markdown(rows, md_path)
        assert csv_path.is_file() and md_path.is_file()


# ------------------------------------------------------------ BUG-22/56: pull_submissions

@pytest.fixture
def ps():
    pytest.importorskip("jsonschema")
    return _load("pull_submissions", _BENCH / "pull_submissions.py")


class TestPullIsolation:

    def _issues(self):
        return [{"number": n, "url": f"u{n}", "author": "a", "body": f"b{n}", "labels": []}
                for n in (1, 2, 3)]

    def test_unexpected_error_isolated_and_batch_continues(self, ps, monkeypatch, tmp_path):
        monkeypatch.setattr(ps, "_require_gh_ready", lambda: None)
        monkeypatch.setattr(ps, "list_issues", lambda *a, **k: self._issues())
        retagged = []
        monkeypatch.setattr(ps, "_retag", lambda repo, num, acc, reason, apply: retagged.append(
            (num, acc)))

        def _mat(body, workdir):
            if body == "b1":
                raise ConnectionResetError("SECRET-PAYLOAD peer reset")
            if body == "b2":
                raise ps._v.Reject("shape", "no submission source found in the issue")
            raise KeyError("SECRET-KEY")
        monkeypatch.setattr(ps, "_materialize_source", _mat)
        report = ps.process("o/r", "l", "open", 10, tmp_path, apply=False)
        assert report["processed"] == 3
        assert report["errors"] == [{"issue": 1, "reason": "ConnectionResetError"},
                                    {"issue": 3, "reason": "KeyError"}]
        assert [r["issue"] for r in report["rejected"]] == [2]
        # Only the real rejection was relabeled; errored issues were not mislabeled.
        assert retagged == [(2, False)]
        assert "SECRET" not in json.dumps(report)

    def test_print_report_shows_errors(self, ps, capsys):
        report = {"repo": "o/r", "apply": False, "processed": 1, "accepted": [],
                  "rejected": [], "deduped": [], "errors": [{"issue": 7, "reason": "OSError"}],
                  "aggregate_rows": 0}
        ps._print_report(report, as_json=False)
        err = capsys.readouterr().err
        assert "errors:    1" in err and "issue #7: OSError" in err


class TestPullRetag:

    def _gh(self, comments=None, fail_edits=0, view_raises=False):
        calls = []
        state = {"edit_failures": fail_edits}

        def _run(args, **k):
            calls.append(list(args))
            if args[:2] == ["issue", "edit"] and state["edit_failures"] > 0:
                state["edit_failures"] -= 1
                raise PullErrorHolder.cls("label not found")
            if args[:2] == ["issue", "view"]:
                if view_raises:
                    raise PullErrorHolder.cls("boom")
                if comments is None:
                    return ""
                return json.dumps({"comments": [{"body": b} for b in comments]})
            return ""
        return calls, _run

    def _comments_posted(self, calls):
        return [c for c in calls if c[:2] == ["issue", "comment"]]

    def test_repeat_rejection_same_reason_not_reposted(self, ps, monkeypatch):
        PullErrorHolder.cls = ps.PullError
        calls, run = self._gh()
        monkeypatch.setattr(ps, "_run_gh", run)
        ps._retag("o/r", 5, False, "schema: bad", apply=True)
        posted = self._comments_posted(calls)
        assert len(posted) == 1
        body = posted[0][posted[0].index("--body") + 1]
        assert ps._REJECT_MARKER in body and "- reason: schema: bad" in body

        calls2, run2 = self._gh(comments=["unrelated human comment", body])
        monkeypatch.setattr(ps, "_run_gh", run2)
        ps._retag("o/r", 5, False, "schema: bad", apply=True)
        assert self._comments_posted(calls2) == []

        calls3, run3 = self._gh(comments=[body])
        monkeypatch.setattr(ps, "_run_gh", run3)
        ps._retag("o/r", 5, False, "share-safety: field leaked", apply=True)
        assert len(self._comments_posted(calls3)) == 1

    def test_same_reason_without_marker_still_posts(self, ps, monkeypatch):
        PullErrorHolder.cls = ps.PullError
        calls, run = self._gh(comments=["- reason: schema: bad"])
        monkeypatch.setattr(ps, "_run_gh", run)
        ps._retag("o/r", 5, False, "schema: bad", apply=True)
        assert len(self._comments_posted(calls)) == 1

    @pytest.mark.parametrize("out", ["", "not json", "[1,2]", '{"comments": "x"}'])
    def test_unreadable_comments_degrade_to_posting(self, ps, monkeypatch, out):
        PullErrorHolder.cls = ps.PullError
        calls = []

        def _run(args, **k):
            calls.append(list(args))
            return out if args[:2] == ["issue", "view"] else ""
        monkeypatch.setattr(ps, "_run_gh", _run)
        ps._retag("o/r", 5, False, "parse: bad", apply=True)
        assert len(self._comments_posted(calls)) == 1

    def test_view_failure_degrades_to_posting(self, ps, monkeypatch):
        PullErrorHolder.cls = ps.PullError
        calls, run = self._gh(view_raises=True)
        monkeypatch.setattr(ps, "_run_gh", run)
        ps._retag("o/r", 5, False, "parse: bad", apply=True)
        assert len(self._comments_posted(calls)) == 1

    @pytest.mark.parametrize("accepted,label", [(True, "status:accepted"),
                                                (False, "status:needs-fix")])
    def test_fallback_still_drops_pending(self, ps, monkeypatch, accepted, label):
        PullErrorHolder.cls = ps.PullError
        calls, run = self._gh(fail_edits=1)
        monkeypatch.setattr(ps, "_run_gh", run)
        ps._retag("o/r", 8, accepted, "" if accepted else "schema: bad", apply=True)
        edits = [c for c in calls if c[:2] == ["issue", "edit"]]
        assert len(edits) == 2
        second = edits[1]
        assert second[second.index("--add-label") + 1] == label
        assert second[second.index("--remove-label") + 1] == "status:pending"

    def test_final_fallback_adds_label_only(self, ps, monkeypatch):
        PullErrorHolder.cls = ps.PullError
        calls, run = self._gh(fail_edits=2)
        monkeypatch.setattr(ps, "_run_gh", run)
        ps._retag("o/r", 8, True, "", apply=True)
        edits = [c for c in calls if c[:2] == ["issue", "edit"]]
        assert len(edits) == 3
        assert edits[2][-2:] == ["--add-label", "status:accepted"]
        assert "--remove-label" not in edits[2]

    def test_primary_edit_first_and_no_fallback_on_success(self, ps, monkeypatch):
        PullErrorHolder.cls = ps.PullError
        calls, run = self._gh()
        monkeypatch.setattr(ps, "_run_gh", run)
        ps._retag("o/r", 8, True, "", apply=True)
        edits = [c for c in calls if c[:2] == ["issue", "edit"]]
        assert len(edits) == 1
        assert edits[0][-6:] == ["--add-label", "status:accepted",
                                 "--remove-label", "status:needs-fix",
                                 "--remove-label", "status:pending"]


class PullErrorHolder:
    cls = Exception
