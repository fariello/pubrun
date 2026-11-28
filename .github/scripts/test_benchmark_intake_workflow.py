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

# Matches YAML block-scalar indicators: |, |-, |+, >, >-, >+, optional single-digit
# indentation indicator (e.g. |2, |2-, |-2, >2+), and an optional trailing YAML comment.
_BLOCK_SCALAR_RE = re.compile(r"^[|>](?:[+-][1-9]?|[1-9][+-]?)?(?:\s+#.*)?$")
# Matches any GitHub Actions expression referencing untrusted `github.event.*` data.
_UNTRUSTED_EVENT_EXPR_RE = re.compile(
    r"\$\{\{(?:(?!\}\}).)*\bgithub\.event\.(?:(?!\}\}).)*\}\}",
    re.DOTALL,
)
_KEY_LINE_RE = re.compile(r"^(\s*(?:-\s+)?)([A-Za-z0-9_.-]+)\s*:\s*(.*)$")


def _text():
    assert _WF.is_file(), f"missing workflow: {_WF}"
    return _WF.read_text(encoding="utf-8")


def _extract_shell_and_script_blocks(text):
    """Extract every `run:` and `script:` value from workflow YAML using stdlib only.

    Handles single-line values, multi-line YAML block scalars (`|`, `|-`, `|+`, `>`,
    `>-`, `>+`, optional indentation digits such as `|2`), and indented multi-line
    continuations. Non-shell keys (such as `if:`) and their block scalars are skipped
    so legitimate job-level conditions are not falsely inspected as shell code.
    """
    lines = text.splitlines()
    blocks = []
    i = 0
    total = len(lines)
    while i < total:
        line = lines[i]
        stripped = line.lstrip(" ")
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        m = _KEY_LINE_RE.match(line)
        if not m:
            i += 1
            continue
        prefix, key, rest = m.group(1), m.group(2), m.group(3)
        parent_indent = len(prefix)
        rest_stripped = rest.strip()
        is_block_scalar = bool(_BLOCK_SCALAR_RE.match(rest_stripped))

        if key in ("run", "script"):
            collected = []
            if not is_block_scalar and rest_stripped:
                collected.append(rest_stripped)
            i += 1
            pending_blanks = []
            while i < total:
                cur = lines[i]
                if not cur.strip():
                    pending_blanks.append("")
                    i += 1
                    continue
                cur_indent = len(cur) - len(cur.lstrip(" "))
                if cur_indent > parent_indent:
                    if pending_blanks:
                        collected.extend(pending_blanks)
                        pending_blanks.clear()
                    collected.append(cur)
                    i += 1
                else:
                    break
            blocks.append((key, "\n".join(collected)))
            continue

        if is_block_scalar:
            # Skip non-shell block scalars (such as `if: >-`) completely so indented
            # lines inside them are never mistaken for `run:`/`script:` keys.
            i += 1
            while i < total:
                cur = lines[i]
                if not cur.strip():
                    i += 1
                    continue
                cur_indent = len(cur) - len(cur.lstrip(" "))
                if cur_indent > parent_indent:
                    i += 1
                else:
                    break
            continue

        i += 1
    return blocks


def _find_untrusted_interpolations(text):
    """Return `(key, expression)` pairs for untrusted `${{ ... github.event. ... }}`
    interpolations inside any `run:` or `script:` block."""
    findings = []
    for key, block in _extract_shell_and_script_blocks(text):
        for match in _UNTRUSTED_EVENT_EXPR_RE.finditer(block):
            findings.append((key, match.group(0)))
    return findings


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


def test_untrusted_body_never_interpolated_into_shell():
    text = _text()
    blocks = _extract_shell_and_script_blocks(text)
    keys = {key for key, _ in blocks}
    assert "run" in keys and "script" in keys, f"expected run and script blocks, got {keys}"
    # The extractor reads the untrusted body from the checked event JSON ($GITHUB_EVENT_PATH),
    # not a shell arg. No `run:` or `script:` block may interpolate `${{ ... github.event. ... }}`.
    findings = _find_untrusted_interpolations(text)
    assert not findings, f"untrusted github.event interpolation in shell/script block: {findings}"
    # Only an enumerated source kind (url|inline) selects the validate command; the URL is
    # passed via env, never spliced into the command by issue text.
    assert "steps.extract.outputs.kind == 'url'" in text
    assert "steps.extract.outputs.kind == 'inline'" in text
    assert "ATTACHMENT_URL: ${{ steps.extract.outputs.url }}" in text


def test_multiline_clean_env_block_has_zero_findings():
    workflow = """\
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Safe multi-line run using env
        env:
          ISSUE_BODY: ${{ github.event.issue.body }}
        run: |
          set -euo pipefail
          python3 .github/scripts/extract_attachment_url.py
          echo "checked via env"
"""
    blocks = _extract_shell_and_script_blocks(workflow)
    assert len(blocks) == 1 and blocks[0][0] == "run"
    assert _find_untrusted_interpolations(workflow) == []


@pytest.mark.parametrize("indicator", ["|", "|-", "|+", ">", ">-", ">+", "|2"])
@pytest.mark.parametrize(
    "expr",
    ["${{ github.event.issue.body }}", "${{ github.event.issue.title }}"],
)
def test_multiline_untrusted_run_block_interpolations_caught(indicator, expr):
    workflow = f"""\
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Unsafe multi-line run
        run: {indicator}
          echo "line 1 is harmless"
          python3 tool.py --arg "{expr}"
"""
    findings = _find_untrusted_interpolations(workflow)
    assert findings == [("run", expr)]


def test_multiline_untrusted_script_and_continuation_interpolations_caught():
    workflow = """\
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Unsafe github-script block
        uses: actions/github-script@v9
        with:
          script: |
            const safe = context.issue.number;
            const bad = "${{ github.event.issue.body }}";
      - name: Unsafe indented continuation
        run:
          echo "line 1"
          echo "${{ github.event.issue.title }}"
"""
    findings = _find_untrusted_interpolations(workflow)
    assert findings == [
        ("script", "${{ github.event.issue.body }}"),
        ("run", "${{ github.event.issue.title }}"),
    ]


def test_job_level_if_condition_not_flagged():
    workflow = """\
jobs:
  validate:
    runs-on: ubuntu-latest
    if: >-
      contains(join(github.event.issue.labels.*.name, ','), 'type:benchmark-submission')
      || contains(github.event.issue.body, '<!-- pubrun-benchmark-submission:v1 -->')
    steps:
      - name: Clean step
        run: |
          echo "no untrusted interpolation here"
"""
    assert _find_untrusted_interpolations(workflow) == []


def test_routes_on_label_or_marker():
    text = _text()
    assert "type:benchmark-submission" in text
    assert "pubrun-benchmark-submission:v1" in text  # marker route (external callers)
    assert "if:" in text


def test_receipt_is_idempotent():
    text = _text()
    # A hidden receipt marker + update-existing-comment keeps edits from piling up comments.
    assert "pubrun-benchmark-receipt:v1" in text
    assert "updateComment" in text


def test_pyyaml_crosscheck_when_available():
    yaml = pytest.importorskip("yaml")
    data = yaml.safe_load(_text())
    assert data["permissions"] == {"contents": "read", "issues": "write"}
    # `on.issues` trigger present.
    on = data.get(True, data.get("on"))  # PyYAML may parse bare `on` as True
    assert "issues" in on
    checked_run = 0
    checked_script = 0
    for job_name, job in (data.get("jobs") or {}).items():
        for idx, step in enumerate(job.get("steps") or []):
            run_val = step.get("run")
            if isinstance(run_val, str):
                checked_run += 1
                match = _UNTRUSTED_EVENT_EXPR_RE.search(run_val)
                assert match is None, (
                    f"untrusted interpolation in jobs.{job_name}.steps[{idx}].run: {match.group(0)}"
                )
            with_block = step.get("with")
            if isinstance(with_block, dict) and isinstance(with_block.get("script"), str):
                checked_script += 1
                match = _UNTRUSTED_EVENT_EXPR_RE.search(with_block["script"])
                assert match is None, (
                    f"untrusted interpolation in jobs.{job_name}.steps[{idx}].with.script: {match.group(0)}"
                )
    assert checked_run > 0 and checked_script > 0
