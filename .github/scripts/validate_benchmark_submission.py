#!/usr/bin/env python3
"""First-party validator for a benchmark-result submission (IPD 20260721-2255-01, Phase 1).

Treated as an INTERNET-FACING PARSER: the input is an attacker-controlled attachment from a
public GitHub issue. This script parses it ONLY as data. It never evaluates strings, never
interpolates content into a shell, and never prints the payload. It performs the ordered
checks and returns a structured pass/fail result the workflow turns into an issue comment.

Phase 1 is VALIDATE-ONLY: this script does not write to any branch and the workflow that
calls it holds no `contents: write`. Archival/aggregation is Phase 2 (separate child IPD),
gated behind a hard security review.

Checks, in order (fail closed at the first failing stage):
  1. shape       - the local file exists, is `.json`, and is within the byte cap
  2. parse       - valid JSON object (data only)
  3. schema      - schema marker == "pubrun-benchmark/5" and validates against the committed
                   schema (jsonschema; the required-field set comes from the schema itself)
  4. share-safe  - structural is-it-redacted check (benchmarks/share_safety.py)
  5. semantic    - finite nonnegative timings; a plausible pubrun_version

Safe download (fetching the attachment from the GitHub host allowlist with redirect/host/
byte-cap enforcement) is done by the WORKFLOW before calling this, or via `--url` here with
the same limits; either way this script fails closed. Usage:

    validate_benchmark_submission.py --file <path>     # validate an already-downloaded file
    validate_benchmark_submission.py --url <url>       # download (allowlisted host) then validate

Exit code 0 = accepted; nonzero = rejected. A machine-readable JSON verdict is printed to
stdout; human reasons go to stderr. Neither ever contains the raw payload.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent.parent
_SCHEMA_PATH = _REPO / "schemas" / "benchmark.schema.json"

# Byte cap for the attachment (fail closed above this). ~1 MiB initial per the design.
MAX_BYTES = 1 * 1024 * 1024

# Allowlist of hosts a GitHub issue attachment may live on. A download must end on one of
# these after following a bounded number of redirects.
ALLOWED_ATTACHMENT_HOSTS = (
    "github.com",
    "objects.githubusercontent.com",
    "user-images.githubusercontent.com",
    "private-user-images.githubusercontent.com",
    "raw.githubusercontent.com",
)

SCHEMA_MARKER = "pubrun-benchmark/5"

# Make benchmarks/share_safety.py importable without installing pubrun.
sys.path.insert(0, str(_REPO / "benchmarks"))
import share_safety  # noqa: E402  (path set above)


class Reject(Exception):
    """A rejection with a human-readable, payload-free reason and a stage tag."""

    def __init__(self, stage: str, reason: str):
        super().__init__(reason)
        self.stage = stage
        self.reason = reason


def _load_schema():
    with _SCHEMA_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def check_shape(path: Path) -> None:
    if not path.is_file():
        raise Reject("shape", "attachment file not found")
    if path.suffix != ".json":
        raise Reject("shape", "attachment is not a .json file")
    size = path.stat().st_size
    if size == 0:
        raise Reject("shape", "attachment is empty")
    if size > MAX_BYTES:
        raise Reject("shape", f"attachment is {size} bytes, over the {MAX_BYTES}-byte cap")


def parse_json(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise Reject("parse", f"could not read attachment: {e}")
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as e:
        raise Reject("parse", f"not valid JSON: {e}")
    if not isinstance(data, dict):
        raise Reject("parse", "top-level JSON is not an object")
    return data


def check_schema(data: dict) -> None:
    marker = data.get("schema")
    if marker != SCHEMA_MARKER:
        raise Reject("schema", f'schema marker is not "{SCHEMA_MARKER}"')
    try:
        import jsonschema  # dev/CI dependency; installed in the workflow
    except ImportError:
        raise Reject("schema", "validator environment missing jsonschema")
    schema = _load_schema()
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    errors = sorted(validator_cls(schema).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        loc = "/".join(str(p) for p in first.path) or "(root)"
        # message is schema-derived, not raw payload
        raise Reject("schema", f"schema validation failed at `{loc}`: {first.message}")


def check_share_safe(data: dict) -> None:
    ok, reasons = share_safety.check_share_safe(data)
    if not ok:
        raise Reject("share-safety", "; ".join(reasons))


def check_semantic(data: dict) -> None:
    # pubrun version present and plausible.
    machine = data.get("machine", {})
    version = machine.get("pubrun_version") if isinstance(machine, dict) else None
    if not version or not isinstance(version, str):
        raise Reject("semantic", "missing or non-string machine.pubrun_version")
    # Timings finite and nonnegative, wherever they appear in pass_results/baseline.

    def _walk_timings(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "timings" and isinstance(v, dict):
                    for _scn, arr in v.items():
                        if not isinstance(arr, list):
                            raise Reject("semantic", "a timings entry is not a list")
                        for t in arr:
                            if not isinstance(t, (int, float)) or isinstance(t, bool):
                                raise Reject("semantic", "a timing value is not a number")
                            if not math.isfinite(t) or t < 0:
                                raise Reject("semantic", "a timing value is negative or non-finite")
                else:
                    _walk_timings(v)
        elif isinstance(node, list):
            for item in node:
                _walk_timings(item)

    _walk_timings(data)


def validate_file(path: Path) -> dict:
    """Run all stages. Return a verdict dict; raise nothing (rejections are captured)."""
    try:
        check_shape(path)
        data = parse_json(path)
        check_schema(data)
        check_share_safe(data)
        check_semantic(data)
    except Reject as r:
        return {"accepted": False, "stage": r.stage, "reason": r.reason,
                "share_safety_version": share_safety.SHARE_SAFETY_VERSION}
    return {"accepted": True, "stage": "ok", "reason": "all checks passed",
            "share_safety_version": share_safety.SHARE_SAFETY_VERSION}


def _download(url: str, dest: Path) -> None:
    """Fetch an attachment with strict host + redirect + byte-cap limits. Fail closed."""
    import urllib.request
    import urllib.error
    from urllib.parse import urlparse

    host = urlparse(url).hostname or ""
    if host not in ALLOWED_ATTACHMENT_HOSTS:
        raise Reject("shape", f"attachment host `{host}` is not on the allowlist")

    class _NoFollow(urllib.request.HTTPRedirectHandler):
        max_repeats = 3

        def redirect_request(self, req, fp, code, msg, headers, newurl):
            new_host = urlparse(newurl).hostname or ""
            if new_host not in ALLOWED_ATTACHMENT_HOSTS:
                raise Reject("shape", f"redirect host `{new_host}` is not on the allowlist")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(_NoFollow)
    try:
        with opener.open(url, timeout=20) as resp:
            data = resp.read(MAX_BYTES + 1)
    except urllib.error.URLError as e:
        raise Reject("shape", f"download failed: {e}")
    if len(data) > MAX_BYTES:
        raise Reject("shape", f"download exceeds the {MAX_BYTES}-byte cap")
    dest.write_bytes(data)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate a benchmark-result submission.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="path to an already-downloaded attachment")
    src.add_argument("--url", help="attachment URL (allowlisted host) to download then validate")
    ap.add_argument("--out", help="write the JSON verdict to this path (in addition to stdout)")
    args = ap.parse_args(argv)

    try:
        if args.url:
            import tempfile
            tmp = Path(tempfile.mkdtemp()) / "submission.json"
            _download(args.url, tmp)
            path = tmp
        else:
            path = Path(args.file)
    except Reject as r:
        verdict = {"accepted": False, "stage": r.stage, "reason": r.reason,
                   "share_safety_version": share_safety.SHARE_SAFETY_VERSION}
    else:
        verdict = validate_file(path)

    line = json.dumps(verdict)
    print(line)
    if args.out:
        Path(args.out).write_text(line + "\n", encoding="utf-8")
    if not verdict["accepted"]:
        print(f"REJECTED [{verdict['stage']}]: {verdict['reason']}", file=sys.stderr)
    return 0 if verdict["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
