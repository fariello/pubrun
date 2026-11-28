"""Tests for benchmarks/pull_submissions.py (IPD 20260722-2209-01, Phase 2 local pull model).

Focus: reuse of the SAME fail-closed validation as the server, content-addressed store with
multi-issue attribution and path confinement, the uniform 256 KB store cap, and gh interaction
that is dry-run by default, argv-only, drops status:pending, and comments only on rejection.
All gh calls are mocked; no live GitHub. Requires the dev-only jsonschema dependency.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("jsonschema")

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_FX = _REPO / ".github" / "scripts" / "test_fixtures"


@pytest.fixture(scope="module")
def ps():
    before_path = list(sys.path)
    before_modules = dict(sys.modules)
    spec = importlib.util.spec_from_file_location(
        "pull_submissions", _HERE / "pull_submissions.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pull_submissions"] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.path[:] = before_path
        for name in list(sys.modules):
            if name not in before_modules:
                sys.modules.pop(name, None)
        for name, prev in before_modules.items():
            if sys.modules.get(name) is not prev:
                sys.modules[name] = prev
        raise
    added = [name for name in sys.modules if name not in before_modules]
    overwritten = {
        name: prev
        for name, prev in before_modules.items()
        if sys.modules.get(name) is not prev
    }
    try:
        yield mod
    finally:
        sys.path[:] = before_path
        for name in added:
            sys.modules.pop(name, None)
        for name, prev in overwritten.items():
            sys.modules[name] = prev


def _valid_body_inline(ps):
    """An automated-submission body with a single valid inline JSON block (marker present)."""
    payload = (_FX / "valid.json").read_text(encoding="utf-8").strip()
    return f"{ps._x.SUBMISSION_MARKER}\n\n```json\n{payload}\n```\n"


# --------------------------------------------------------------- import smoke (PR-001)

def test_cross_dir_imports_resolve(ps):
    # The validator + extractor (.github/scripts) and share_safety + aggregate (benchmarks/)
    # must import via the documented sys.path injection; a move/rename fails this loudly.
    assert hasattr(ps._v, "validate_file")
    assert hasattr(ps._v, "_download")
    assert hasattr(ps._x, "resolve_source")
    assert hasattr(ps._x, "find_inline_json")
    assert hasattr(ps._agg, "build_rows")


def test_store_cap_matches_stated_256k(ps):
    assert ps.MAX_STORE_BYTES == 256 * 1024


# ------------------------------------------------------ validation reuse (accept/reject)

def test_inline_valid_result_accepted(ps, tmp_path):
    body = _valid_body_inline(ps)
    src, kind, host = ps._materialize_source(body, tmp_path)
    verdict = ps._v.validate_file(src)
    assert verdict["accepted"] is True
    assert kind == "inline"


@pytest.mark.parametrize("fixture,stage", [
    ("unredacted_hostname.json", "share-safety"),
    ("home_path.json", "share-safety"),
    ("wrong_schema.json", "schema"),
    ("missing_required.json", "schema"),
])
def test_inline_adversarial_rejected(ps, tmp_path, fixture, stage):
    payload = (_FX / fixture).read_text(encoding="utf-8").strip()
    body = f"{ps._x.SUBMISSION_MARKER}\n\n```json\n{payload}\n```\n"
    src, kind, host = ps._materialize_source(body, tmp_path)
    verdict = ps._v.validate_file(src)
    assert verdict["accepted"] is False
    assert verdict["stage"] == stage


def test_no_source_is_rejected(ps, tmp_path):
    with pytest.raises(ps._v.Reject) as ei:
        ps._materialize_source("no submission here", tmp_path)
    assert ei.value.stage == "shape"


# ----------------------------------------------------- uniform 256 KB store cap (PR-004)

def test_inline_oversize_rejected_before_parse(ps, tmp_path):
    big = "x" * (ps.MAX_STORE_BYTES + 10)
    body = f"{ps._x.SUBMISSION_MARKER}\n\n```json\n{big}\n```\n"
    with pytest.raises(ps._v.Reject) as ei:
        ps._materialize_source(body, tmp_path)
    assert ei.value.stage == "shape"
    assert "store cap" in ei.value.reason


# ------------------------------------------------------- content-addressed store + dedupe

def _store(ps_mod, tmp_path, src, issue_number, apply=True):
    return ps_mod.store_accepted(
        src, tmp_path, issue_number=issue_number, issue_url=f"https://x/i/{issue_number}",
        submitter="octocat", kind="inline", host="", apply=apply)


def test_store_content_addressed_and_sidecar(ps, tmp_path):
    body = _valid_body_inline(ps)
    src, _, _ = ps._materialize_source(body, tmp_path)
    sha, stored, deduped = _store(ps, tmp_path, src, 101)
    assert stored and not deduped
    acc = tmp_path / "accepted"
    assert (acc / f"{sha}.redacted.json").is_file()
    meta = json.loads((acc / f"{sha}.meta.json").read_text())
    assert meta["sha256"] == sha
    assert meta["sources"] == [{"issue_number": 101, "issue_url": "https://x/i/101",
                                "submitter_login": "octocat"}]


def test_dedupe_same_bytes_two_issues_keeps_both_sources(ps, tmp_path):
    body = _valid_body_inline(ps)
    wa = tmp_path / "a"
    wa.mkdir()
    src1, _, _ = ps._materialize_source(body, wa)
    sha1, stored1, ded1 = _store(ps, tmp_path, src1, 101)
    # Same bytes, different issue.
    wb = tmp_path / "b"
    wb.mkdir()
    src2, _, _ = ps._materialize_source(body, wb)
    sha2, stored2, ded2 = _store(ps, tmp_path, src2, 202)
    assert sha1 == sha2
    assert stored1 and not ded1
    assert (not stored2) and ded2  # second is a dedupe hit; file not rewritten
    meta = json.loads((tmp_path / "accepted" / f"{sha1}.meta.json").read_text())
    nums = sorted(s["issue_number"] for s in meta["sources"])
    assert nums == [101, 202]  # both issues recorded (PR-002)


def test_dry_run_writes_nothing(ps, tmp_path):
    body = _valid_body_inline(ps)
    src, _, _ = ps._materialize_source(body, tmp_path)
    sha, stored, deduped = _store(ps, tmp_path, src, 101, apply=False)
    assert not stored
    assert not (tmp_path / "accepted").exists() or not list((tmp_path / "accepted").glob("*"))


def test_path_confinement_rejects_escape(ps, tmp_path):
    base = tmp_path / "accepted"
    base.mkdir()
    with pytest.raises(ps.PullError):
        ps._confined(base, "../evil.json")


# ------------------------------------------------------------ aggregation over the corpus

def test_aggregate_over_stored_corpus(ps, tmp_path):
    body = _valid_body_inline(ps)
    src, _, _ = ps._materialize_source(body, tmp_path)
    _store(ps, tmp_path, src, 101)
    rows = ps.aggregate_corpus(tmp_path, apply=True)
    assert isinstance(rows, int)
    assert (tmp_path / "summary.csv").is_file()
    assert (tmp_path / "summary.md").is_file()


# ---------------------------------------------------- gh interaction (mocked; argv/no-shell)

def test_retag_dry_run_makes_no_gh_call(ps, monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(ps, "_run_gh",
                        lambda *a, **k: called.__setitem__("n", called["n"] + 1) or "")
    ps._retag("fariello/pubrun", 5, True, "", apply=False)
    assert called["n"] == 0


def test_retag_apply_accepts_drops_pending_argv(ps, monkeypatch):
    seen = []
    monkeypatch.setattr(ps, "_run_gh", lambda args, **k: seen.append(args) or "")
    ps._retag("fariello/pubrun", 7, True, "", apply=True)
    assert seen, "gh was not called"
    argv = seen[0]
    assert argv[0] == "issue" and argv[1] == "edit" and "7" in argv
    assert "--add-label" in argv and ps._LABEL_ACCEPTED in argv
    assert "--remove-label" in argv and ps._LABEL_PENDING in argv  # PR-003
    # Accepted submissions get NO comment (quiet accept).
    assert not any(a and a[0] == "comment" for a in seen)


def test_retag_apply_rejection_comments(ps, monkeypatch):
    seen = []
    monkeypatch.setattr(ps, "_run_gh", lambda args, **k: seen.append(args) or "")
    ps._retag("fariello/pubrun", 9, False, "schema: bad", apply=True)
    assert any(a and a[0] == "issue" and a[1] == "comment" for a in seen)
    # Comment body is our own text; it names the reason, not the payload.
    comment = next(a for a in seen if a[1] == "comment")
    body = comment[comment.index("--body") + 1]
    assert "needs fix" in body and "schema: bad" in body


def _strict_label_gh(ps, labels: set):
    """Simulate `gh issue edit` failing whenever `--remove-label` names an absent label."""
    calls = []

    def _fake_gh(args, **kwargs):
        calls.append(list(args))
        if args[:2] == ["issue", "edit"]:
            adds = []
            removes = []
            i = 0
            while i < len(args):
                if args[i] == "--add-label":
                    adds.append(args[i + 1])
                    i += 2
                elif args[i] == "--remove-label":
                    removes.append(args[i + 1])
                    i += 2
                else:
                    i += 1
            for lb in removes:
                if lb not in labels:
                    raise ps.PullError(f"label {lb!r} is not present on issue")
            for lb in removes:
                labels.discard(lb)
            for lb in adds:
                labels.add(lb)
        return ""

    return _fake_gh, calls


def test_process_issue_reaccepted_drops_needs_fix_without_pending(ps, monkeypatch, tmp_path):
    """BUG-E8: re-accepting a needs-fix issue passes current_labels and removes status:needs-fix."""
    labels = {"type:benchmark-submission", "status:needs-fix"}
    fake_gh, calls = _strict_label_gh(ps, labels)
    monkeypatch.setattr(ps, "_run_gh", fake_gh)

    issue = {
        "number": 42,
        "url": "https://x/i/42",
        "author": "octocat",
        "body": _valid_body_inline(ps),
        "labels": sorted(labels),
    }
    report = {"accepted": [], "rejected": [], "deduped": []}
    ps._process_issue("fariello/pubrun", issue, tmp_path, apply=True, report=report)

    assert len(report["accepted"]) == 1
    assert ps._LABEL_ACCEPTED in labels
    assert ps._LABEL_NEEDS_FIX not in labels
    assert len(calls) == 1
    assert "--remove-label" in calls[0] and ps._LABEL_NEEDS_FIX in calls[0]
    assert ps._LABEL_PENDING not in calls[0]


def test_retag_direct_fallback_drops_needs_fix_when_pending_absent(ps, monkeypatch):
    """BUG-E8: direct _retag(..., current_labels=None) tries removing only opposite label."""
    labels = {"type:benchmark-submission", "status:needs-fix"}
    fake_gh, calls = _strict_label_gh(ps, labels)
    monkeypatch.setattr(ps, "_run_gh", fake_gh)

    ps._retag("fariello/pubrun", 42, True, "", apply=True)

    assert ps._LABEL_ACCEPTED in labels
    assert ps._LABEL_NEEDS_FIX not in labels
    assert len(calls) == 3
    assert calls[2][-4:] == [
        "--add-label",
        ps._LABEL_ACCEPTED,
        "--remove-label",
        ps._LABEL_NEEDS_FIX,
    ]


def test_retag_concurrent_label_drift_falls_back_to_add_only(ps, monkeypatch):
    """BUG-E8: if labels changed on GitHub since listing, final add-only fallback still succeeds."""
    labels = {"type:benchmark-submission"}
    fake_gh, calls = _strict_label_gh(ps, labels)
    monkeypatch.setattr(ps, "_run_gh", fake_gh)

    ps._retag(
        "fariello/pubrun",
        43,
        True,
        "",
        apply=True,
        current_labels=["type:benchmark-submission", "status:needs-fix"],
    )

    assert ps._LABEL_ACCEPTED in labels
    assert len(calls) == 2
    assert calls[1][-2:] == ["--add-label", ps._LABEL_ACCEPTED]


def test_run_gh_uses_argv_no_shell(ps, monkeypatch):
    seen = {}

    class _Proc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def _fake(argv, **kw):
        seen["argv"] = argv
        assert "shell" not in kw or kw["shell"] is False
        return _Proc()
    import subprocess
    monkeypatch.setattr(subprocess, "run", _fake)
    ps._run_gh(["issue", "list"])
    assert seen["argv"][0] == "gh"


def test_repo_slug_injection_rejected(ps):
    # A shell-metachar repo slug is refused by the CLI guard (never reaches gh).
    rc = ps.main(["--repo", "$(touch /tmp/pwn)", "--limit", "1"])
    assert rc == 2
