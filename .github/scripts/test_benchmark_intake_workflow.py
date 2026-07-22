"""Security invariant tests for the validate-only benchmark-intake workflow.

Phase 1 (IPD 20260721-2255-01) grants the Action NO write access to repo contents. These
tests assert the workflow's permission block is exactly `contents: read` + `issues: write`
(never `contents: write`), that it is validate-only (calls the validator, no branch push),
and that the untrusted issue body is passed via env, not a shell argument. They avoid a
PyYAML dependency (pubrun ships zero runtime deps); a lightweight structural parse suffices,
with a PyYAML cross-check when it happens to be installed.
"""
import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_WF = _REPO / ".github" / "workflows" / "benchmark-intake.yml"


def _text():
    assert _WF.is_file(), f"missing workflow: {_WF}"
    return _WF.read_text(encoding="utf-8")


def _permissions_block(text):
    """Return the top-level `permissions:` mapping as {key: value} via a small structural
    parse (top-level key, indented `name: value` children)."""
    lines = text.splitlines()
    perms = {}
    in_block = False
    for line in lines:
        if re.match(r"^permissions:\s*$", line):
            in_block = True
            continue
        if in_block:
            m = re.match(r"^\s+([A-Za-z0-9_-]+):\s*([A-Za-z0-9_-]+)\s*$", line)
            if m:
                perms[m.group(1)] = m.group(2)
            elif re.match(r"^\S", line):  # dedent to a new top-level key ends the block
                break
    return perms


def test_permissions_are_read_plus_issues_write_only():
    perms = _permissions_block(_text())
    assert perms.get("contents") == "read", perms
    assert perms.get("issues") == "write", perms
    # No write to contents, packages, id-token, etc. Phase 1 is validate-only.
    assert perms.get("contents") != "write"
    forbidden = {"packages", "id-token", "deployments", "pull-requests"}
    assert not (set(perms) & forbidden), f"unexpected permission(s): {set(perms) & forbidden}"


def test_no_contents_write_anywhere():
    # Belt-and-suspenders: the literal `contents: write` must not appear at all.
    assert "contents: write" not in _text()


def test_calls_validator_and_is_validate_only():
    text = _text()
    assert "validate_benchmark_submission.py" in text
    # No branch push / commit in Phase 1.
    assert "git push" not in text
    assert "git commit" not in text


def test_untrusted_body_passed_via_env_not_shell_arg():
    text = _text()
    # The issue body reaches the extractor through an env var (ISSUE_BODY), never as an
    # inline shell argument like $(...) interpolation of github.event.issue.body.
    assert "ISSUE_BODY: ${{ github.event.issue.body }}" in text
    # The body expression must not appear inside a `run:` shell line.
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("python3") or stripped.startswith("- run") or stripped.startswith("run:"):
            assert "github.event.issue.body" not in line, line


def test_label_gated():
    text = _text()
    assert "type:benchmark-submission" in text
    assert "if:" in text


def test_pyyaml_crosscheck_when_available():
    yaml = pytest.importorskip("yaml")
    data = yaml.safe_load(_text())
    assert data["permissions"] == {"contents": "read", "issues": "write"}
    # `on.issues` trigger present.
    on = data.get(True, data.get("on"))  # PyYAML may parse bare `on` as True
    assert "issues" in on
