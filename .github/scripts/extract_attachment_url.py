#!/usr/bin/env python3
"""Extract a benchmark-result attachment URL from an UNTRUSTED GitHub issue body.

Part of benchmark-intake Phase 1 (IPD 20260721-2255-01). The issue body is attacker-
controlled; this script treats it as DATA ONLY (regex over text, no eval, no shell). It
finds the FIRST `.json` attachment URL that lives on an allowlisted GitHub host and writes
it to the workflow's `$GITHUB_OUTPUT` as `url=...` (and any diagnostic as `error=...`). The
downstream validator re-checks the host allowlist, byte cap, and redirects and fails closed,
so this extractor is a convenience, not the security boundary.

The issue body is read from the `ISSUE_BODY` environment variable (never a shell argument),
so nothing in it is shell-evaluated. Output is written via the `GITHUB_OUTPUT` file protocol.
"""
from __future__ import annotations

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
)

# A conservative URL matcher: http(s) URLs, stopping at whitespace or common markdown
# delimiters. We do NOT trust it for security (the validator re-validates); it only needs
# to surface a candidate.
_URL_RE = re.compile(r"https?://[^\s)\]<>\"']+")


def _emit(url: str = "", error: str = "") -> None:
    out_path = os.environ.get("GITHUB_OUTPUT")
    line = f"url={url}\nerror={error}\n"
    if out_path:
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(line)
    # Also echo to stderr for the workflow log (never the payload, just the chosen URL).
    if url:
        print(f"selected attachment URL on host: {urlparse(url).hostname}", file=sys.stderr)
    elif error:
        print(f"no attachment URL: {error}", file=sys.stderr)


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
        # Strip a trailing markdown/paren artifact defensively.
        url = raw.rstrip(".,")
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path = parsed.path or ""
        is_json = path.lower().endswith(".json")
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


def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    url, error = find_attachment_url(body)
    _emit(url=url, error=error)
    # Always exit 0: a missing attachment is a "needs-fix" the workflow reports, not a
    # workflow failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
