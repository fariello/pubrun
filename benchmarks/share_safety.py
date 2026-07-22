#!/usr/bin/env python3
"""Structural share-safety validator for benchmark result JSON (IPD 20260721-2255-01).

This is a VALIDATOR, not a redactor. It answers one question: "is this result already
safe to publish?" by checking that privacy-sensitive fields carry the expected redaction
marker and that no unredacted-looking value survives. It does NOT produce redacted output
(that is `src/pubrun/capture/redaction.py`'s job, and the harness's redaction pass), and it
does NOT compare against the current machine's live hostname (meaningless server-side: the
CI runner is a different machine than the submitter). The check is STRUCTURAL
(is-it-redacted), not identity-based (does-it-match-this-host).

Shared by:
  - the local `pubrun bench` submission path (a pre-share gate), and
  - the server-side GitHub Action validator,
so local and server checks stay in lockstep. Reused via import; stdlib only. This module is
NOT part of the installed pubrun runtime surface (it lives under benchmarks/, dev/CI only).

NOTE: agent-workflows will soon ship a canonical commit-hook/CI path/hostname scrubber
(cf. executed IPD 20260720-2331-01). Where it lands, prefer adopting its share-safety
patterns over this local copy, keeping only the benchmark-result-specific structural rules
(the `<redacted>` marker assertions) here.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

# Versioned so an accepted result can record which ruleset validated it, and so the local
# client and the server Action can assert they agree.
SHARE_SAFETY_VERSION = 1

REDACTED = "<redacted>"

# Absolute home / user-profile path shapes that must never appear in a shareable result.
# Detection patterns only (reused idea from scripts/sanitize_paths.py); NOT live-host based.
# The scan runs over the JSON-serialized document, where a single backslash is escaped to
# two, so the Windows pattern tolerates one-or-more backslashes (\\+) between segments.
_HOME_PATH_RE = re.compile(
    r"(?:/home|/Users)/[A-Za-z0-9._-]+"          # POSIX: /home/<x> or /Users/<x>
    r"|[A-Za-z]:\\+[Uu]sers\\+[^\\\"]+"           # Windows: C:\Users\<x> (escaped or not)
)

# Dotted paths (into the result dict) whose leaf value MUST equal the redaction marker.
# These are the fields the harness redacts; if any is not the marker, the file is not safe.
_MUST_BE_REDACTED = (
    "machine.host.hostname",
    "machine.python.executable",
    "machine.python.prefix",
    "machine.python.base_prefix",
    "machine.python.virtual_env",
    "machine.python_executable",
)


def _get(d: Dict[str, Any], dotted: str):
    cur: Any = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


_MISSING = object()


def check_share_safe(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Return (is_safe, reasons). reasons is empty when safe.

    Rules (structural):
      1. Each field in _MUST_BE_REDACTED, when PRESENT, must equal "<redacted>".
      2. No absolute home/user-profile path may appear anywhere in the serialized document.
    A missing field is not by itself unsafe (a partial/older result may omit it); an
    unredacted PRESENT value is unsafe.
    """
    reasons: List[str] = []

    for dotted in _MUST_BE_REDACTED:
        val = _get(result, dotted)
        if val is _MISSING:
            continue
        if val != REDACTED:
            # Report the field, never the raw value (do not echo a potential leak).
            reasons.append(f"field `{dotted}` is not redacted (must equal \"{REDACTED}\")")

    # Whole-document scan for home/user-profile paths. Serialize once.
    import json as _json

    blob = _json.dumps(result)
    if _HOME_PATH_RE.search(blob):
        reasons.append("an absolute home or user-profile path is present somewhere in the result")

    return (len(reasons) == 0, reasons)


def check_share_safe_text(text: str) -> Tuple[bool, List[str]]:
    """Convenience wrapper: parse JSON text then check. Returns (False, [reason]) on parse
    failure so callers get a uniform result."""
    import json as _json

    try:
        result = _json.loads(text)
    except (ValueError, TypeError) as e:
        return (False, [f"not valid JSON: {e}"])
    if not isinstance(result, dict):
        return (False, ["top-level JSON is not an object"])
    return check_share_safe(result)
