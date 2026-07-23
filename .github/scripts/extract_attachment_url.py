#!/usr/bin/env python3
"""Extract a benchmark-result submission SOURCE from an UNTRUSTED GitHub issue body.

Benchmark-intake (IPD 20260721-2255-01 + 20260722-1930-01). The issue body is attacker-
controlled; this script treats it as DATA ONLY (regex/text, no eval, no shell). It resolves the
submission to exactly one of:

    kind=url     url=<https allowlisted-host .json URL>   # attach flow or gist-and-link
    kind=inline  file=submission.json                     # inline gh-submission (JSON in body)
    kind=none    error=<reason>

and writes that to the workflow's `$GITHUB_OUTPUT`. For an inline submission it also WRITES the
embedded JSON to a FIXED path (`submission.json`), enforcing a byte cap before writing and never
logging the payload. The downstream validator re-checks host/redirects/byte-cap/schema/share-
safety and fails closed, so this extractor is routing convenience, not the security boundary.

The issue body is read from `$GITHUB_EVENT_PATH` (the checked event JSON) rather than a possibly
large env var; if that is unavailable it falls back to the `ISSUE_BODY` env var. Either way the
body is only ever treated as data.
"""
from __future__ import annotations

import json
import os
import re
import sys
from urllib.parse import urlparse

# Keep in lockstep with validate_benchmark_submission.ALLOWED_ATTACHMENT_HOSTS.
ALLOWED_ATTACHMENT_HOSTS = (
    "github.com",
    "objects.githubusercontent.com",
    "user-images.githubusercontent.com",
    "private-user-images.githubusercontent.com",
    "raw.githubusercontent.com",
    "gist.githubusercontent.com",
)

# The automated-submission routing marker (must match __main__._BENCH_SUBMISSION_MARKER).
SUBMISSION_MARKER = "<!-- pubrun-benchmark-submission:v1 -->"

# Byte cap for an inline JSON payload, matches the validator's MAX_BYTES (~1 MiB).
MAX_INLINE_BYTES = 1 * 1024 * 1024

# Fixed output path for an extracted inline payload (never derived from issue content).
INLINE_OUT = "submission.json"

_URL_RE = re.compile(r"https?://[^\s)\]<>\"']+")
# A ```json ... ``` fenced block (fence of 3+ backticks). Non-greedy; DOTALL for multiline JSON.
_JSON_FENCE_RE = re.compile(r"`{3,}[ \t]*json[ \t]*\r?\n(.*?)\r?\n`{3,}", re.DOTALL | re.IGNORECASE)


def _emit(kind: str, *, url: str = "", file: str = "", error: str = "") -> None:
    out_path = os.environ.get("GITHUB_OUTPUT")
    line = f"kind={kind}\nurl={url}\nfile={file}\nerror={error}\n"
    if out_path:
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(line)
    if kind == "url":
        print(f"selected attachment URL on host: {urlparse(url).hostname}", file=sys.stderr)
    elif kind == "inline":
        print(f"extracted an inline JSON submission to {file}", file=sys.stderr)
    else:
        print(f"no submission source: {error}", file=sys.stderr)


def find_attachment_url(body: str) -> tuple:
    """Return (url, error). url is the first allowlisted-host `.json` URL, else ('', reason)."""
    if not body:
        return ("", "the issue body is empty")
    candidates = _URL_RE.findall(body)
    if not candidates:
        return ("", "no URL found in the issue body")
    saw_json_off_allowlist = False
    saw_allowlisted_non_json = False
    for raw in candidates:
        url = raw.rstrip(".,")
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        is_json = (parsed.path or "").lower().endswith(".json")
        on_allowlist = host in ALLOWED_ATTACHMENT_HOSTS
        if on_allowlist and is_json:
            return (url, "")
        if is_json and not on_allowlist:
            saw_json_off_allowlist = True
        if on_allowlist and not is_json:
            saw_allowlisted_non_json = True
    if saw_json_off_allowlist:
        return ("", "a .json link was found but not on an allowlisted GitHub attachment host")
    if saw_allowlisted_non_json:
        return ("", "an attachment was found but it is not a .json file")
    return ("", "no .json attachment on an allowlisted GitHub host was found")


def find_inline_json(body: str) -> tuple:
    """For an automated (marker-bearing) submission, extract EXACTLY ONE ```json block.
    Return (payload, error). Rejects zero/multiple blocks and an oversize payload (before any
    parse). payload is the raw fenced bytes as text; caller writes it."""
    if SUBMISSION_MARKER not in body:
        return ("", "no automated-submission marker present")
    blocks = _JSON_FENCE_RE.findall(body)
    if not blocks:
        return ("", "no ```json block found for an inline submission")
    if len(blocks) > 1:
        return ("", "multiple ```json blocks found; expected exactly one")
    payload = blocks[0]
    if len(payload.encode("utf-8")) > MAX_INLINE_BYTES:
        return ("", "inline JSON exceeds the size cap")
    return (payload, "")


def _read_issue_body() -> str:
    """Read the issue body from $GITHUB_EVENT_PATH (checked event JSON), else $ISSUE_BODY."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and os.path.isfile(event_path):
        try:
            with open(event_path, "r", encoding="utf-8") as fh:
                event = json.load(fh)
            body = (event.get("issue") or {}).get("body")
            if isinstance(body, str):
                return body
        except Exception:
            pass
    return os.environ.get("ISSUE_BODY", "") or ""


def resolve_source(body: str) -> tuple:
    """Resolve the submission source. Return (kind, url, file, error).

    Preference: an allowlisted `.json` URL (attach or gist-and-link) wins; else, if the
    automated marker is present, a single inline ```json block; else none. Writing the inline
    file is done by main() so this stays a pure function for testing."""
    url, url_err = find_attachment_url(body)
    if url:
        return ("url", url, "", "")
    payload, inline_err = find_inline_json(body)
    if payload:
        return ("inline", "", INLINE_OUT, "")
    # Choose the most informative error.
    if SUBMISSION_MARKER in body:
        return ("none", "", "", inline_err or url_err)
    return ("none", "", "", url_err)


def main() -> int:
    body = _read_issue_body()
    kind, url, file, error = resolve_source(body)
    if kind == "inline":
        # Re-extract and write the payload to the fixed path (never log it).
        payload, err = find_inline_json(body)
        if not payload:
            _emit("none", error=err or "inline extraction failed")
            return 0
        try:
            with open(INLINE_OUT, "w", encoding="utf-8") as fh:
                fh.write(payload)
        except OSError as e:
            _emit("none", error=f"could not write inline submission: {e}")
            return 0
        _emit("inline", file=INLINE_OUT)
        return 0
    if kind == "url":
        _emit("url", url=url)
        return 0
    _emit("none", error=error)
    # Always exit 0: a missing source is a "needs-fix" the workflow reports, not a failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
