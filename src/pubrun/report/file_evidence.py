"""Classify recorded ``data_files`` records by evidence strength and hashing outcome.

This module is the single definition shared by the reproducibility assessment and the
methods report. It imports only the standard library, so the runtime capture path
(which writes ``methods.md`` when a run stops) can use it.
"""

from typing import Any, Dict


def _is_caller_digest_mismatch(rec: Dict[str, Any]) -> bool:
    """Return True when a record indicates a verified caller digest mismatched content."""
    if rec.get("hash_status_detail") == "caller_digest_mismatch":
        return True
    caller_digest = rec.get("caller_digest")
    if isinstance(caller_digest, dict) and caller_digest.get("verified") is False:
        return True
    return False


def _has_nonempty_digest_value(rec: Dict[str, Any]) -> bool:
    """Return True when a record carries a non-empty digest, sha256, or md5 value."""
    digest = rec.get("digest")
    if isinstance(digest, dict):
        val = digest.get("value")
        if isinstance(val, str) and val.strip():
            return True
    sha256 = rec.get("sha256")
    if isinstance(sha256, str) and sha256.strip():
        return True
    md5 = rec.get("md5")
    if isinstance(md5, str) and md5.strip():
        return True
    return False


def _classify_file_record(rec: Dict[str, Any]) -> str:
    """Classify a single ``data_files`` record by evidence strength and hashing outcome."""
    hash_status = rec.get("hash_status")
    evidence_strength = rec.get("evidence_strength")
    evidence_source = rec.get("evidence_source")

    if hash_status == "file_changed" or rec.get("change_detected") is True:
        return "changed"
    if hash_status == "failed" or _is_caller_digest_mismatch(rec):
        return "failed"
    if hash_status == "unavailable":
        return "unavailable"
    if hash_status == "over_budget":
        return "over_budget"
    if hash_status == "completed" or evidence_strength == "verified_content":
        return "verified" if _has_nonempty_digest_value(rec) else "identified_only"
    if (
        hash_status == "asserted"
        or evidence_strength == "asserted_content"
        or evidence_source == "asserted"
    ):
        return "asserted"
    if hash_status == "pending":
        return "pending"
    if hash_status == "disabled" or evidence_strength in ("metadata_only", "path_only"):
        return "identified_only"
    if hash_status is None and evidence_strength is None and evidence_source is None:
        return "verified" if _has_nonempty_digest_value(rec) else "identified_only"
    if evidence_strength == "unavailable":
        return "unavailable"
    if evidence_strength == "changed_unverified":
        return "changed"
    return "identified_only"
