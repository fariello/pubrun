from __future__ import annotations
import collections
import json
import math
import re
import shutil
from typing import Deque, Optional, Dict, Any, List, TextIO, Tuple
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from pubrun.report.file_evidence import _classify_file_record
from pubrun.report.utils import hydrate_manifest, hydrate_manifest_with_report

# The section names `pubrun show <run> <section>` accepts as a bare trailing token.
# Single source of truth: the CLI shift heuristic, the argparse help, and the render
# branches below all reference this so the set cannot drift (it did before: it was
# duplicated as a literal in three places).
SHOW_SECTIONS = ("logs", "env", "packages")

_MAX_DIAGNOSTIC_DETAIL_LEN = 160
_MAX_DISPLAYED_CAPTURE_ERRORS = 10


def _is_finite_number(val: Any) -> bool:
    return (
        isinstance(val, (int, float))
        and not isinstance(val, bool)
        and math.isfinite(val)
    )


def _as_finite_float(val: Any) -> Optional[float]:
    if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val):
        return float(val)
    return None


def _as_dict(val: Any) -> Dict[str, Any]:
    return val if isinstance(val, dict) else {}


def _as_dict_list(val: Any) -> List[Dict[str, Any]]:
    if not isinstance(val, list):
        return []
    return [item for item in val if isinstance(item, dict)]


def _section_status(manifest: Any, name: str) -> Optional[str]:
    if not isinstance(manifest, dict):
        return None
    sec = manifest.get(name)
    if not isinstance(sec, dict):
        return None
    cs = sec.get("capture_state")
    if not isinstance(cs, dict):
        return None
    status = cs.get("status")
    return status if isinstance(status, str) else None


def _section_detail(manifest: Any, name: str) -> Optional[str]:
    if not isinstance(manifest, dict):
        return None
    sec = manifest.get(name)
    if not isinstance(sec, dict):
        return None
    cs = sec.get("capture_state")
    if not isinstance(cs, dict):
        return None
    detail = cs.get("detail")
    return detail if isinstance(detail, str) else None


def _bound_text(text: Any, max_len: int = _MAX_DIAGNOSTIC_DETAIL_LEN) -> str:
    if not isinstance(text, str):
        return ""
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max(0, max_len - 3)].rstrip() + "..."


_ANSI_ESCAPE_RE = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-Z\\-_])"
)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_inline(val: Any, max_len: int = 200) -> str:
    """Return a single-line, control-character-free, length-bounded display string."""
    if val is None:
        return ""
    text = val if isinstance(val, str) else str(val)
    text = _ANSI_ESCAPE_RE.sub("", text)
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = _CONTROL_CHAR_RE.sub("", text)
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    if max_len > 0 and len(cleaned) > max_len:
        if max_len <= 3:
            return cleaned[:max_len]
        return cleaned[: max_len - 3].rstrip() + "..."
    return cleaned


_DATA_FILE_BUCKETS: Tuple[Tuple[str, str], ...] = (
    ("inputs", "input"),
    ("outputs", "output"),
    ("mixed", "mixed"),
)


def _iter_data_file_entries(data_files: Any) -> List[Tuple[str, Dict[str, Any]]]:
    if not isinstance(data_files, dict):
        return []
    out: List[Tuple[str, Dict[str, Any]]] = []
    for bucket_name, default_role in _DATA_FILE_BUCKETS:
        bucket = data_files.get(bucket_name)
        if not isinstance(bucket, list):
            continue
        for rec in bucket:
            if isinstance(rec, dict):
                out.append((default_role, rec))
    return out


def _classify_file_record_display(rec: Dict[str, Any]) -> str:
    """Classify a ``data_files`` record into its authoritative textual badge name."""
    category = _classify_file_record(rec)
    if category == "over_budget":
        return "over-budget"
    if category == "identified_only":
        return "path-only" if rec.get("evidence_strength") == "path_only" else "metadata-only"
    return category


def _extract_display_digest(rec: Dict[str, Any], badge: str) -> Optional[str]:
    """Return ``<alg>:<prefix12>`` for verified/asserted records only; ``None`` otherwise."""
    if badge == "verified":
        digest = rec.get("digest")
        if isinstance(digest, dict):
            raw_val = digest.get("value")
            if isinstance(raw_val, str) and raw_val.strip():
                raw_alg = digest.get("algorithm") or rec.get("hash_algorithm") or "sha256"
                alg = _sanitize_inline(raw_alg, max_len=32) or "sha256"
                val = _sanitize_inline(raw_val, max_len=128)
                if val:
                    return f"{alg}:{val[:12]}"
        raw_sha = rec.get("sha256")
        if isinstance(raw_sha, str) and raw_sha.strip():
            val = _sanitize_inline(raw_sha, max_len=128)
            if val:
                return f"sha256:{val[:12]}"
        raw_md5 = rec.get("md5")
        if isinstance(raw_md5, str) and raw_md5.strip():
            val = _sanitize_inline(raw_md5, max_len=128)
            if val:
                return f"md5:{val[:12]}"
        return None

    if badge == "asserted":
        for key in ("caller_digest", "digest"):
            obj = rec.get(key)
            if isinstance(obj, dict):
                raw_val = obj.get("value")
                if isinstance(raw_val, str) and raw_val.strip():
                    raw_alg = obj.get("algorithm") or rec.get("hash_algorithm") or "sha256"
                    alg = _sanitize_inline(raw_alg, max_len=32) or "sha256"
                    val = _sanitize_inline(raw_val, max_len=128)
                    if val:
                        return f"{alg}:{val[:12]}"
        return None

    return None


def _summarize_data_files(data_files: Any) -> Dict[str, int]:
    """Summarize ``data_files`` counts across evidence categories (sum equals ``total``)."""
    counts: Dict[str, int] = {
        "total": 0,
        "verified": 0,
        "asserted": 0,
        "identified_only": 0,
        "over_budget": 0,
        "changed": 0,
        "failed_or_unavailable": 0,
        "pending": 0,
    }
    for _, rec in _iter_data_file_entries(data_files):
        badge = _classify_file_record_display(rec)
        counts["total"] += 1
        if badge == "verified":
            counts["verified"] += 1
        elif badge == "asserted":
            counts["asserted"] += 1
        elif badge in ("metadata-only", "path-only"):
            counts["identified_only"] += 1
        elif badge == "over-budget":
            counts["over_budget"] += 1
        elif badge == "changed":
            counts["changed"] += 1
        elif badge in ("failed", "unavailable"):
            counts["failed_or_unavailable"] += 1
        elif badge == "pending":
            counts["pending"] += 1
        else:
            counts["identified_only"] += 1
    return counts


def _format_data_files_summary_line(counts: Dict[str, int]) -> str:
    """Format the concise Standard-depth ``Data Files`` summary text."""
    parts: List[str] = []
    if counts["verified"] > 0:
        parts.append(f"{counts['verified']} verified")
    if counts["asserted"] > 0:
        parts.append(f"{counts['asserted']} asserted")
    if counts["identified_only"] > 0:
        parts.append(f"{counts['identified_only']} identified-only")
    if counts["over_budget"] > 0:
        parts.append(f"{counts['over_budget']} over-budget")
    if counts["pending"] > 0:
        parts.append(f"{counts['pending']} pending")
    if counts["changed"] > 0:
        parts.append(f"{counts['changed']} changed")
    if counts["failed_or_unavailable"] > 0:
        parts.append(f"{counts['failed_or_unavailable']} failed/unavailable")
    return f"{counts['total']} tracked ({', '.join(parts)})"


def _print_data_files_block(
    manifest: Dict[str, Any],
    use_color: bool,
    *,
    out: Optional[TextIO] = None,
) -> None:
    """Render the Deep-depth ``[ Data Files ]`` subsection without ``Colors.DIM``."""
    stream = out if out is not None else sys.stdout
    blue = Colors.BLUE if use_color else ""
    green = Colors.GREEN if use_color else ""
    yellow = Colors.YELLOW if use_color else ""
    red = Colors.RED if use_color else ""
    cyan = Colors.CYAN if use_color else ""
    rst = Colors.RESET if use_color else ""

    entries = _iter_data_file_entries(manifest.get("data_files"))
    print(f"\n{blue}[ Data Files ]{rst}", file=stream)
    if not entries:
        print("  (None captured)", file=stream)
        return

    badge_colors = {
        "verified": green,
        "asserted": yellow,
        "metadata-only": cyan,
        "path-only": cyan,
        "over-budget": yellow,
        "pending": yellow,
        "changed": red,
        "unavailable": red,
        "failed": red,
    }
    anomaly_badges = frozenset(("failed", "changed", "unavailable", "over-budget"))

    for default_role, rec in entries:
        badge = _classify_file_record_display(rec)
        b_color = badge_colors.get(badge, "") if use_color else ""
        badge_txt = f"{b_color}[{badge}]{rst}" if b_color else f"[{badge}]"

        path_txt = _sanitize_inline(rec.get("path"), max_len=200) or "<unknown>"
        role_txt = _sanitize_inline(rec.get("role") or default_role, max_len=32) or default_role
        mode_txt = _sanitize_inline(rec.get("mode"), max_len=16)
        role_meta = f"({role_txt}, mode={mode_txt})" if mode_txt else f"({role_txt})"

        pieces: List[str] = [f"  {badge_txt}", path_txt, role_meta]

        label_txt = _sanitize_inline(rec.get("label"), max_len=80)
        if label_txt:
            pieces.append(f"[label={label_txt}]")

        digest_txt = _extract_display_digest(rec, badge)
        if digest_txt:
            pieces.append(digest_txt)

        if badge in anomaly_badges:
            detail_txt = _sanitize_inline(rec.get("hash_status_detail"), max_len=120)
            if detail_txt:
                pieces.append(f"({detail_txt})")

        print(" ".join(pieces), file=stream)


def _unwrap_value(val: Any, default: str = "unknown") -> str:
    if isinstance(val, str):
        return val if val else default
    if isinstance(val, dict):
        rep = val.get("representation")
        if rep == "plain" or (rep is None and "value" in val):
            inner = val.get("value")
            if isinstance(inner, str):
                return inner if inner else default
            return str(inner) if inner is not None else default
        if isinstance(rep, str) and rep:
            return f"<{rep.upper()}>"
        return default
    if val is None:
        return default
    return str(val)


def _format_report_timestamp(ts: Any, utc: bool = False) -> str:
    from pubrun.status import _as_float

    val = _as_float(ts)
    if val is None:
        return "unknown"
    try:
        sdt = datetime.fromtimestamp(val, tz=timezone.utc)
        if not utc:
            sdt = sdt.astimezone()
        return sdt.strftime("%Y-%m-%d %H:%M:%S")
    except (OverflowError, OSError, ValueError, TypeError):
        return "unknown"


def bytes_to_gb(bytes_val: Any) -> float:
    if not _is_finite_number(bytes_val) or not bytes_val:
        return 0.0
    return round(float(bytes_val) / (1024 ** 3), 1)

class Colors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

def _has_color(stream: Optional[TextIO] = None) -> bool:
    from pubrun.report.output import use_color as _output_use_color
    return _output_use_color(stream)

class DiagnosticsError(Exception):
    """A diagnostics report could not be produced; the CLI prints ``message`` and exits."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


def _print_error(message: str) -> None:
    from pubrun.report import output as _out
    _out.error(message)


def read_resource_series(events_path) -> Dict[str, Any]:
    """Read per-sample resource series from an events.jsonl.

    Returns a dict with time-ordered lists: ``timestamps``, ``rss`` (main), ``cpu`` (main),
    ``tree_rss``, ``tree_cpu`` (present only when captured). Shared by the ``res``/``report``
    summary, the ASCII charts, and the TUI. Never raises; returns empty lists on any error.
    """
    out: Dict[str, List[Any]] = {"timestamps": [], "rss": [], "cpu": [], "tree_rss": [], "tree_cpu": []}
    try:
        with open(events_path, "r", encoding="utf-8", errors="replace") as ef:
            for line in ef:
                if '"resource_sample"' not in line:
                    continue
                try:
                    e = json.loads(line)
                    if not isinstance(e, dict) or e.get("type") != "resource_sample":
                        continue
                    p = e.get("payload")
                    if not isinstance(p, dict):
                        continue
                    ts = _as_finite_float(e.get("timestamp_utc"))
                    rss = _as_finite_float(p.get("rss_bytes"))
                    cpu = _as_finite_float(p.get("cpu_percent"))
                    if ts is None or rss is None or cpu is None:
                        continue
                    out["timestamps"].append(ts)
                    out["rss"].append(rss)
                    out["cpu"].append(cpu)
                    tree_rss = _as_finite_float(p.get("tree_rss_bytes"))
                    if tree_rss is not None:
                        out["tree_rss"].append(tree_rss)
                    tree_cpu = _as_finite_float(p.get("tree_cpu_percent"))
                    if tree_cpu is not None:
                        out["tree_cpu"].append(tree_cpu)
                except Exception:
                    continue
    except Exception:
        pass
    return out


def _series_stats(values):
    """(peak, avg, min) for a numeric series, or None if empty."""
    clean = [float(v) for v in (values or []) if _is_finite_number(v)]
    if not clean:
        return None
    return (max(clean), sum(clean) / len(clean), min(clean))


def _sparkline(
    values,
    width: int = 40,
    *,
    ascii_only: bool = False,
    stream: Optional[TextIO] = None,
) -> str:
    """A tiny sparkline for a numeric series (no color, no deps). Empty or width < 1 -> ''."""
    if width < 1:
        return ""
    clean = [float(v) for v in (values or []) if _is_finite_number(v)]
    if not clean:
        return ""
    unicode_bars = "▁▂▃▄▅▆▇█"
    ascii_bars = " .:-=+*#%@"
    use_ascii = ascii_only
    if not use_ascii and stream is not None:
        try:
            unicode_bars.encode(getattr(stream, "encoding", "utf-8") or "utf-8")
        except (UnicodeEncodeError, LookupError):
            use_ascii = True
    bars = ascii_bars if use_ascii else unicode_bars
    lo = min(clean)
    hi = max(clean)
    span = (hi - lo) or 1.0
    # Downsample to width by simple bucketed max (keeps spikes visible).
    n = len(clean)
    if n > width:
        step = n / width
        sampled = [max(clean[int(i * step):int((i + 1) * step)] or [clean[min(int(i * step), n - 1)]])
                   for i in range(width)]
    else:
        sampled = clean
    return "".join(
        bars[max(0, min(len(bars) - 1, int((v - lo) / span * (len(bars) - 1))))]
        for v in sampled
    )


def format_resource_digest(series, width: int = 40) -> str:
    """Plain-text resource digest (summary lines + sparklines) for a run's per-sample series.

    ``series`` is the dict returned by :func:`read_resource_series`. Returns a multi-line
    string with peak/avg/min + a sparkline for each captured metric (main RSS/CPU and, when
    present, tree RSS/CPU). Used by the TUI resource view; pure, no textual/ANSI dependency,
    so it is unit-testable. Returns a clear message when there are no samples.
    """
    if not series or not series.get("timestamps"):
        return "No resource samples recorded for this run."

    def _mb(n):
        return f"{n / (1024**2):.1f} MB" if n < 1024**3 else f"{n / (1024**3):.2f} GB"

    lines = []

    def _row(title, values, fmt, unit=""):
        st = _series_stats(values)
        if not st:
            return
        pk, avg, mn = st
        lines.append(f"{title:<12} peak {fmt(pk)}{unit} / avg {fmt(avg)}{unit} / min {fmt(mn)}{unit}")
        spark = _sparkline(values, width)
        if spark:
            lines.append(f"             {spark}")

    _row("RSS (main)", series.get("rss", []), _mb)
    _row("CPU (main)", series.get("cpu", []), lambda v: f"{v:.1f}", "%")
    _row("RSS (tree)", series.get("tree_rss", []), _mb)
    _row("CPU (tree)", series.get("tree_cpu", []), lambda v: f"{v:.1f}", "%")
    return "\n".join(lines) if lines else "No resource samples recorded for this run."

def format_redacted_rerun_advisory(rerun_cmd: Optional[str]) -> Optional[str]:
    """Return a plain-text advisory when a rerun command contains ``[REDACTED]`` placeholders.

    Pure Python with zero TUI or ANSI dependencies so CLI and TUI surfaces share
    the same advisory wording without duplicating detection logic.
    """
    if isinstance(rerun_cmd, str) and "[REDACTED]" in rerun_cmd:
        return (
            "Rerun command contains [REDACTED] placeholders and is not directly "
            "executable verbatim; supply the redacted arguments manually before running."
        )
    return None


def _supports_unicode(stream) -> bool:
    try:
        "┌".encode(getattr(stream, "encoding", "utf-8") or "utf-8")
        return True
    except UnicodeEncodeError:
        return False


def _print_packages_block(
    manifest: Dict[str, Any],
    use_color: bool,
    *,
    leading_newline: bool = False,
    out: Optional[TextIO] = None,
) -> None:
    """Render the ``[ Packages ]`` block and any ``unresolved`` summary cleanly."""
    stream = out if out is not None else sys.stdout
    pkg_sec = _as_dict(manifest.get("packages"))
    pkgs = _as_dict_list(pkg_sec.get("records"))
    unresolved = _as_dict_list(pkg_sec.get("unresolved"))
    pkg_status = _section_status(manifest, "packages")

    blue = Colors.BLUE if use_color else ""
    green = Colors.GREEN if use_color else ""
    yellow = Colors.YELLOW if use_color else ""
    rst = Colors.RESET if use_color else ""

    prefix = "\n" if leading_newline else ""
    print(f"{prefix}{blue}[ Packages ]{rst}", file=stream)
    if pkg_status == "failed":
        detail = _bound_text(_section_detail(manifest, "packages"))
        if detail:
            print(f"  {yellow}(capture failed: {detail}){rst}", file=stream)
        else:
            print(f"  {yellow}(capture failed){rst}", file=stream)
    elif not pkgs:
        print("  (None captured)", file=stream)

    term_cols = shutil.get_terminal_size((80, 24)).columns
    if term_cols >= 96:
        num_cols = 3
    elif term_cols >= 60:
        num_cols = 2
    else:
        num_cols = 1

    for i, p in enumerate(pkgs):
        raw_name = p.get("name")
        name = raw_name if isinstance(raw_name, str) and raw_name else "<unknown>"
        raw_ver = p.get("version")
        ver = str(raw_ver) if raw_ver not in (None, "") else "unknown"
        pkg_str = f"{name}=={ver}"
        display_len = len(pkg_str)
        if use_color:
            pkg_str = f"{green}{name}{rst}=={ver}"
        if num_cols == 1:
            print(pkg_str, file=stream)
        else:
            is_row_end = (i + 1) % num_cols == 0
            if is_row_end:
                print(pkg_str, file=stream)
            else:
                pad_width = max(30, display_len + 1)
                print(pkg_str.ljust(pad_width + (len(pkg_str) - display_len)), end="", file=stream)
    if num_cols > 1 and len(pkgs) % num_cols != 0:
        print(file=stream)

    if unresolved:
        print(f"  {yellow}Unresolved ({len(unresolved)}):{rst}", file=stream)
        for entry in unresolved:
            raw_mod = entry.get("module")
            mod = raw_mod if isinstance(raw_mod, str) and raw_mod else "<unknown>"
            raw_reason = entry.get("reason")
            reason = raw_reason if isinstance(raw_reason, str) and raw_reason else "unresolved"
            raw_cands = entry.get("candidates")
            cands = (
                [str(c) for c in raw_cands if isinstance(c, str) and c]
                if isinstance(raw_cands, list)
                else []
            )
            if cands:
                preview = ", ".join(cands[:5])
                more = f" (+{len(cands) - 5} more)" if len(cands) > 5 else ""
                print(f"    - {mod}: {reason} ({len(cands)} candidates: {preview}{more})", file=stream)
            else:
                detail = _bound_text(entry.get("detail"))
                if detail:
                    print(f"    - {mod}: {reason} ({detail})", file=stream)
                else:
                    print(f"    - {mod}: {reason}", file=stream)

def print_report(
    manifest_path: str,
    depth: str = "standard",
    section: Optional[str] = None,
    utc: bool = False,
    *,
    out: Optional[TextIO] = None,
) -> None:
    """Print a human-readable diagnostic summary of a recorded run.

    Args:
        manifest_path: Path to the manifest.json file.
        depth: Verbosity level (``"basic"``, ``"standard"``, or ``"deep"``).
        section: Optional section to extract (``"logs"``, ``"env"``, or ``"packages"``).
        utc: Show timestamps in UTC instead of local time.
        out: Optional output stream (defaults to ``sys.stdout`` at call time).
    """
    stream = out if out is not None else sys.stdout
    if section is not None and section not in SHOW_SECTIONS:
        valid_list = ", ".join(SHOW_SECTIONS)
        raise DiagnosticsError(
            f"Unknown section '{section}'. Valid sections: {valid_list}.",
            exit_code=2,
        )

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except FileNotFoundError as e:
        raise DiagnosticsError(f"Could not find manifest file at '{manifest_path}'.") from e
    except json.JSONDecodeError as e:
        raise DiagnosticsError(
            f"The manifest file at '{manifest_path}' is corrupt or contains invalid JSON."
        ) from e

    # Hydrate!
    if not isinstance(manifest, dict):
        manifest = {}
    manifest, warnings, hydration_report = hydrate_manifest_with_report(manifest_path, manifest)
    if not isinstance(manifest, dict):
        manifest = {}

    if section == "logs":
        run_dir = Path(manifest_path).parent
        stdout_path = run_dir / "stdout.log"
        stderr_path = run_dir / "stderr.log"
        if not stdout_path.exists() and not stderr_path.exists():
            from pubrun.report import output as _out
            _out.info(
                "No captured stdout.log or stderr.log found for this run. "
                'Enable console capture with [console].capture_mode = "standard" '
                "(or `import pubrun.full`).",
                stream=sys.stderr,
            )
            return
        if stdout_path.exists():
            try:
                with open(stdout_path, "r", encoding="utf-8", errors="replace") as sf:
                    shutil.copyfileobj(sf, stream, length=65536)
            except Exception as e:
                raise DiagnosticsError(f"Failed to read stdout log: {e}") from e
        if stderr_path.exists():
            try:
                with open(stderr_path, "r", encoding="utf-8", errors="replace") as se:
                    shutil.copyfileobj(se, stream, length=65536)
            except Exception as e:
                raise DiagnosticsError(f"Failed to read stderr log: {e}") from e
        return

    if section == "env":
        env_sec = _as_dict(manifest.get("environment"))
        envs = _as_dict_list(env_sec.get("variables"))
        env_status = _section_status(manifest, "environment")
        use_color = _has_color(stream)
        blue = Colors.BLUE if use_color else ""
        green = Colors.GREEN if use_color else ""
        yellow = Colors.YELLOW if use_color else ""
        rst = Colors.RESET if use_color else ""

        print(f"{blue}[ Environment Variables ]{rst}", file=stream)
        if env_status == "failed":
            detail = _bound_text(_section_detail(manifest, "environment"))
            if detail:
                print(f"  {yellow}(capture failed: {detail}){rst}", file=stream)
            else:
                print(f"  {yellow}(capture failed){rst}", file=stream)
        elif not envs:
            print("  (None captured)", file=stream)
        for var in envs:
            name = var.get("name")
            val_obj = var.get("value", {})
            if isinstance(val_obj, dict) and "representation" in val_obj:
                rep = val_obj.get("representation")
                if rep == "plain":
                    print(f"  {green}{name}{rst}={val_obj.get('value', '')}", file=stream)
                else:
                    rep_label = str(rep).upper() if rep not in (None, "") else "REDACTED"
                    print(f"  {green}{name}{rst}={yellow}<{rep_label}>{rst}", file=stream)
            else:
                print(f"  {green}{name}{rst}={val_obj}", file=stream)
        return

    if section == "packages":
        _print_packages_block(manifest, _has_color(stream), leading_newline=False, out=stream)
        return

    use_color = _has_color(stream)
    bold = Colors.BOLD if use_color else ""
    rst = Colors.RESET if use_color else ""
    cyan = Colors.CYAN if use_color else ""
    blue = Colors.BLUE if use_color else ""
    green = Colors.GREEN if use_color else ""
    red = Colors.RED if use_color else ""
    yellow = Colors.YELLOW if use_color else ""

    if use_color:
        if _supports_unicode(stream):
            print(f"\n{cyan}{bold}┌─────────────────────────────────────────────────┐{rst}", file=stream)
            print(f"{cyan}{bold}│               PUBRUN DIAGNOSTICS                │{rst}", file=stream)
            print(f"{cyan}{bold}└─────────────────────────────────────────────────┘{rst}", file=stream)
        else:
            print(f"\n{cyan}{bold}+-------------------------------------------------+{rst}", file=stream)
            print(f"{cyan}{bold}|               PUBRUN DIAGNOSTICS                |{rst}", file=stream)
            print(f"{cyan}{bold}+-------------------------------------------------+{rst}", file=stream)
    else:
        print(f"\n=================================================", file=stream)
        print(f"               PUBRUN DIAGNOSTICS                ", file=stream)
        print(f"=================================================", file=stream)

    print(f"{cyan}Source{rst}      : {manifest_path}", file=stream)

    meta_ref = manifest.get("meta_ref")
    if meta_ref:
        print(f"{cyan}Parent{rst}      : {meta_ref}", file=stream)

    for w in warnings:
        # Report-body warning (stays on stdout as part of the rendered report); label
        # normalized to the canonical [WARN ] prefix for consistency.
        print(f"\n{yellow}[WARN ]{rst} {w}", file=stream)

    # Non-disruptive config notices recorded at run time (e.g. deprecated core.profile).
    cfg_notices = _as_dict(manifest.get("config")).get("notices")
    if isinstance(cfg_notices, list):
        for notice in cfg_notices:
            if isinstance(notice, dict):
                msg = notice.get("message", notice.get("code", "config notice"))
            elif notice:
                msg = str(notice)
            else:
                continue
            print(f"\n{yellow}[WARN ]{rst} {msg}", file=stream)

    # Surface failed capture sections and recorded capture errors at every depth.
    failed_sections = sorted(
        (sec_name, _bound_text(_section_detail(manifest, sec_name)))
        for sec_name, sec_val in manifest.items()
        if isinstance(sec_val, dict) and _section_status(manifest, sec_name) == "failed"
    )
    errors_sec = _as_dict(manifest.get("errors"))
    error_records = _as_dict_list(errors_sec.get("records"))
    cap_errors = [rec for rec in error_records if rec.get("kind") == "capture-error"]
    errors_partial = _section_status(manifest, "errors") == "partial"

    if failed_sections or cap_errors or errors_partial:
        if failed_sections:
            sec_parts = [
                f"{sec} ({detail})" if detail else sec
                for sec, detail in failed_sections
            ]
            print(f"\n{yellow}[WARN ]{rst} Capture failed for section(s): {', '.join(sec_parts)}", file=stream)
        if cap_errors:
            lead = "\n" if not failed_sections else ""
            print(f"{lead}{yellow}[WARN ]{rst} Capture errors recorded ({len(cap_errors)}):", file=stream)
            for rec in cap_errors[:_MAX_DISPLAYED_CAPTURE_ERRORS]:
                raw_sec = rec.get("section")
                sec_label = raw_sec.strip() if isinstance(raw_sec, str) and raw_sec.strip() else "general"
                raw_stage = rec.get("stage")
                stage_label = f"/{raw_stage.strip()}" if isinstance(raw_stage, str) and raw_stage.strip() else ""
                raw_msg = rec.get("message")
                if not isinstance(raw_msg, str) or not raw_msg.strip():
                    raw_msg = rec.get("type")
                msg = _bound_text(raw_msg) or "capture error"
                print(f"  - {sec_label}{stage_label}: {msg}", file=stream)
            if len(cap_errors) > _MAX_DISPLAYED_CAPTURE_ERRORS:
                overflow = len(cap_errors) - _MAX_DISPLAYED_CAPTURE_ERRORS
                print(f"  ... (+{overflow} more capture error(s))", file=stream)
        if errors_partial:
            lead = "\n" if not failed_sections and not cap_errors else ""
            err_detail = _bound_text(_section_detail(manifest, "errors"))
            if err_detail:
                print(f"{lead}{yellow}[WARN ]{rst} Capture errors truncated: {err_detail}", file=stream)
            else:
                print(f"{lead}{yellow}[WARN ]{rst} Capture errors truncated.", file=stream)

    print(f"\n{blue}{bold}--- Basic Information ---{rst}", file=stream)
    run = _as_dict(manifest.get("run"))
    timing = _as_dict(manifest.get("timing"))
    status = _as_dict(manifest.get("status"))
    python = _as_dict(manifest.get("python"))
    inv = _as_dict(manifest.get("invocation"))

    script_info = _as_dict(inv.get("script"))
    raw_basename = script_info.get("basename")
    script_name = raw_basename if isinstance(raw_basename, str) and raw_basename else "<interactive or module>"

    signals_data = _as_dict(manifest.get("signals"))
    exit_code = signals_data.get("exit_code")
    exit_exception = signals_data.get("exit_exception")
    signals_received = _as_dict_list(signals_data.get("signals_received"))

    # Colorize outcome
    raw_outcome = status.get("outcome")
    outcome = str(raw_outcome) if raw_outcome not in (None, "") else "unknown"
    out_color = ""
    if use_color:
        if outcome == "completed":
            out_color = Colors.GREEN
        elif outcome in ("failed", "crashed"):
            out_color = Colors.RED
        elif outcome == "interrupted":
            out_color = Colors.YELLOW

    from pubrun.status import _as_float, _format_duration_detail, classify_timing_semantics

    exit_str = ""
    if exit_code is not None:
        if exit_code == 0:
            code_color = Colors.BOLD + Colors.GREEN if use_color else ""
        else:
            code_color = Colors.BOLD + Colors.RED if use_color else ""
        exit_str = f" ({code_color}{exit_code}{rst})"

    print(f"{cyan}Run ID{rst}      : {run.get('run_id')}", file=stream)
    print(f"{cyan}Script{rst}      : {script_name}", file=stream)
    print(f"{cyan}Status{rst}      : {out_color}{outcome}{rst}{exit_str}", file=stream)
    if exit_exception:
        print(f"{cyan}Exception{rst}   : {red}{exit_exception}{rst}", file=stream)
    if signals_received:
        sig_names = [
            str(s.get("signal_name") or f"SIG{s.get('signal')}")
            for s in signals_received
        ]
        print(f"{cyan}Signals{rst}     : {yellow}{', '.join(sig_names)}{rst}", file=stream)

    start_str = _format_report_timestamp(timing.get("started_at_utc"), utc=utc)
    print(f"{cyan}Started{rst}     : {start_str}", file=stream)

    timing_sem = classify_timing_semantics(timing)
    workload_val = _as_float(timing.get("workload_seconds"))
    elapsed_raw = _as_float(timing.get("elapsed_seconds"))
    elapsed_val: Optional[float]
    if timing_sem.get("elapsed_basis") == "session" and elapsed_raw is not None:
        elapsed_val = elapsed_raw
    else:
        elapsed_val = workload_val if workload_val is not None else elapsed_raw
    startup_overhead = _as_float(timing.get("startup_overhead_seconds"))
    finalization_overhead = _as_float(timing.get("finalization_overhead_seconds"))
    hardware_wait = _as_float(timing.get("hardware_wait_seconds"))
    session_val = _as_float(timing.get("session_seconds"))
    bg_hardware = _as_float(timing.get("background_hardware_seconds"))

    elapsed_label = timing_sem.get("label", "Elapsed")
    elapsed_str = (
        "unknown"
        if elapsed_val is None
        else _format_duration_detail(elapsed_val)
    )
    print(f"{cyan}{elapsed_label}{rst} : {elapsed_str}", file=stream)
    print(
        f"{cyan}Timing Scope{rst} : tracked interval "
        "(start() to stop(), not full application lifetime when imported late)",
        file=stream,
    )
    if startup_overhead is not None:
        print(f"{cyan}Startup overhead{rst} : {_format_duration_detail(startup_overhead)}", file=stream)
    if finalization_overhead is not None:
        fin_str = _format_duration_detail(finalization_overhead)
        if hardware_wait is not None:
            fin_str += f" (includes Hardware wait: {_format_duration_detail(hardware_wait)})"
        print(f"{cyan}Finalization overhead{rst} : {fin_str}", file=stream)
    elif hardware_wait is not None:
        print(f"{cyan}Hardware wait{rst} : {_format_duration_detail(hardware_wait)}", file=stream)
    if session_val is not None:
        print(f"{cyan}Tracked session{rst} : {_format_duration_detail(session_val)}", file=stream)
    if bg_hardware is not None:
        print(
            f"{cyan}Background hardware{rst} : "
            f"{_format_duration_detail(bg_hardware)} (overlaps workload)",
            file=stream,
        )

    # Read Events if available (O(1) memory: keep oldest 10 + newest 10)
    events_path = Path(manifest_path).parent / "events.jsonl"
    if events_path.exists():
        print(f"\n{blue}{bold}--- Event Timeline ---{rst}", file=stream)
        try:
            head_events: List[Dict[str, Any]] = []
            tail_events: Deque[Dict[str, Any]] = collections.deque(maxlen=10)
            total_events = 0
            skipped_lines = 0
            with open(events_path, "r", encoding="utf-8", errors="replace") as ef:
                for raw_line in ef:
                    if not raw_line.strip():
                        continue
                    try:
                        parsed = json.loads(raw_line)
                    except json.JSONDecodeError:
                        skipped_lines += 1
                        continue
                    if not isinstance(parsed, dict):
                        skipped_lines += 1
                        continue
                    total_events += 1
                    if len(head_events) < 10:
                        head_events.append(parsed)
                    else:
                        tail_events.append(parsed)

            def _print_ev(e: Dict[str, Any]) -> None:
                ts_str = _format_report_timestamp(e.get("timestamp_utc"), utc=utc)
                print(
                    f"  [{cyan}{ts_str}{rst}] {green}{e.get('type')}{rst}: "
                    f"{e.get('name', '')} {e.get('payload', '')}",
                    file=stream,
                )

            for ev in head_events:
                _print_ev(ev)

            if total_events > 20:
                print(f"  ... [ {total_events - 20} events truncated ] ...", file=stream)

            for ev in tail_events:
                _print_ev(ev)

            if skipped_lines > 0:
                print(
                    f"  {yellow}[WARN ] Skipped {skipped_lines} corrupt or non-object event line(s).{rst}",
                    file=stream,
                )
        except Exception:
            print("  (Events file corrupt or unreadable)", file=stream)

    if depth == "basic":
        print(file=stream)
        return

    # --- STANDARD ---
    host = _as_dict(manifest.get("host"))
    hw = _as_dict(manifest.get("hardware"))
    git = _as_dict(manifest.get("git"))
    pkgs = _as_dict_list(_as_dict(manifest.get("packages")).get("records"))
    envs = _as_dict_list(_as_dict(manifest.get("environment")).get("variables"))

    python_status = _section_status(manifest, "python")
    host_status = _section_status(manifest, "host")
    hw_status = _section_status(manifest, "hardware")
    git_status = _section_status(manifest, "git")
    pkg_status = _section_status(manifest, "packages")
    env_status = _section_status(manifest, "environment")

    cpu_model = _as_dict(hw.get("cpu")).get("model") or "unknown"
    ram_gb = bytes_to_gb(hw.get("memory_total_bytes", 0))

    raw_argv = inv.get("argv")
    if isinstance(raw_argv, list):
        argv_str = " ".join(str(a) for a in raw_argv)
    elif isinstance(raw_argv, str):
        argv_str = raw_argv
    else:
        argv_str = ""

    print(f"\n{blue}{bold}--- Standard Information ---{rst}", file=stream)
    print(f"{cyan}Arguments{rst}   : {argv_str}", file=stream)

    # Safely extract python version
    if python_status == "failed":
        print(f"{cyan}Python{rst}      : {yellow}capture failed{rst}", file=stream)
    else:
        py_ver = python.get("version")
        py_parts = py_ver.split() if isinstance(py_ver, str) else []
        v_tag = py_parts[0] if py_parts else "unknown"
        print(f"{cyan}Python{rst}      : {python.get('executable')} (v{v_tag})", file=stream)

    hw_summary = (
        "hardware: capture failed"
        if hw_status == "failed"
        else f"{cpu_model}, {ram_gb} GB RAM"
    )
    if host_status == "failed":
        print(f"{cyan}Host{rst}        : {yellow}capture failed{rst} ({hw_summary})", file=stream)
    else:
        hostname = _unwrap_value(host.get("hostname"), default="unknown")
        os_name = _unwrap_value(host.get("os_name"), default="")
        os_version = _unwrap_value(host.get("os_version"), default="")
        os_text = " ".join(part for part in (os_name, os_version) if part) or "unknown OS"
        print(f"{cyan}Host{rst}        : {hostname} - {os_text} ({hw_summary})", file=stream)

    if git_status == "failed":
        print(f"{cyan}Git Commit{rst}  : {yellow}capture failed{rst}", file=stream)
    else:
        commit = git.get("commit")
        if isinstance(commit, str) and commit:
            remote = _unwrap_value(git.get("remote_url"), default="unknown origin")
            print(f"{cyan}Git Commit{rst}  : {commit[:8]} ({remote})", file=stream)
        else:
            print(f"{cyan}Git Commit{rst}  : Not found or un-tracked", file=stream)

    pkg_unresolved = _as_dict_list(_as_dict(manifest.get("packages")).get("unresolved"))
    if pkg_status == "failed":
        print(f"{cyan}Packages{rst}    : {yellow}capture failed{rst}", file=stream)
    else:
        unresolved_suffix = f" ({len(pkg_unresolved)} unresolved)" if pkg_unresolved else ""
        print(f"{cyan}Packages{rst}    : {len(pkgs)} recorded{unresolved_suffix}", file=stream)

    if env_status == "failed":
        print(f"{cyan}Env Vars{rst}    : {yellow}capture failed{rst}", file=stream)
    else:
        print(f"{cyan}Env Vars{rst}    : {len(envs)} captured", file=stream)

    df_counts = _summarize_data_files(manifest.get("data_files"))
    if df_counts["total"] > 0:
        print(f"{cyan}Data Files{rst}  : {_format_data_files_summary_line(df_counts)}", file=stream)

    # Concise reproducibility summary (standard and deep depths only; never in basic or section extracts).
    try:
        import socket as _socket
        try:
            current_hostname = _socket.gethostname()
        except Exception:
            current_hostname = None
        from pubrun.report.reproducibility import (
            assess_run as _assess_run,
            format_reproducibility_summary as _format_repro_summary,
        )
        repro = _assess_run(
            manifest,
            manifest_path=manifest_path,
            hydration_report=hydration_report,
            current_hostname=current_hostname,
            preflight=False,
        )
        repro_lines = _format_repro_summary(repro).splitlines()
        print(f"\n{blue}{bold}--- Reproducibility ---{rst}", file=stream)
        for rline in repro_lines:
            print(f"  {rline}", file=stream)
        if hydration_report.inherited_sections and not any(
            "Inherited from parent snapshot:" in rl for rl in repro_lines
        ):
            inherited_str = ", ".join(hydration_report.inherited_sections)
            print(
                f"  Inherited from parent snapshot: {inherited_str} "
                "(script mtime alone does not prove dependencies matched).",
                file=stream,
            )
        if not any("pubrun inspect --preflight" in rl for rl in repro_lines):
            print(
                f"  {cyan}Preflight{rst}   : Run `pubrun inspect --preflight` to compare "
                "recorded requirements against this environment.",
                file=stream,
            )
    except Exception:
        pass

    if depth == "standard":
        print(file=stream)
        return

    # --- DEEP ---
    print(f"\n{blue}{bold}--- Deep Information ---{rst}", file=stream)

    # Read Config
    cfg_path = Path(manifest_path).parent / "config.resolved.json"
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as cf:
                cfg = _as_dict(json.load(cf))
            print(f"\n{blue}[ Resolved Configuration Highlights ]{rst}", file=stream)
            cfg_core = _as_dict(cfg.get("core"))
            cfg_cap = _as_dict(cfg.get("capture"))
            print(f"  {cyan}Output Dir{rst}: {cfg_core.get('output_dir') or './runs'}", file=stream)
            print(f"  {cyan}Inputs Mode{rst}: {_as_dict(cfg_cap.get('inputs')).get('enabled')}", file=stream)
            print(f"  {cyan}Packages Mode{rst}: {_as_dict(cfg_cap.get('packages')).get('mode')}", file=stream)
            prof = cfg_core.get("profile")
            if prof and prof != "default":
                print(f"  {cyan}Profile (deprecated){rst}: {prof}", file=stream)
        except Exception:
            pass

    print(f"\n{blue}[ Environment Variables ]{rst}", file=stream)
    if env_status == "failed":
        detail = _bound_text(_section_detail(manifest, "environment"))
        if detail:
            print(f"  {yellow}(capture failed: {detail}){rst}", file=stream)
        else:
            print(f"  {yellow}(capture failed){rst}", file=stream)
    elif not envs:
        print("  (None captured)", file=stream)
    for var in envs:
        name = var.get("name")
        val_obj = var.get("value", {})
        if isinstance(val_obj, dict) and "representation" in val_obj:
            rep = val_obj.get("representation")
            if rep == "plain":
                print(f"  {green}{name}{rst}={val_obj.get('value', '')}", file=stream)
            else:
                rep_label = str(rep).upper() if rep not in (None, "") else "REDACTED"
                print(f"  {green}{name}{rst}={yellow}<{rep_label}>{rst}", file=stream)
        else:
            print(f"  {green}{name}{rst}={val_obj}", file=stream)

    _print_packages_block(manifest, use_color, leading_newline=True, out=stream)
    _print_data_files_block(manifest, use_color, out=stream)

    subprocs = _as_dict_list(manifest.get("subprocesses"))
    print(f"\n{blue}[ Subprocesses ]{rst} ({len(subprocs)} executed)", file=stream)
    for sp in subprocs:
        cmd = sp.get("argv", [])
        if isinstance(cmd, list):
            cmd_str = " ".join(str(c) for c in cmd)
        else:
            cmd_str = str(cmd)
        rc = sp.get("exit_code")
        sp_elapsed = _as_float(sp.get("elapsed_seconds"))
        if sp_elapsed is not None:
            elapsed = round(max(0.0, sp_elapsed), 3)
            sp_clock = sp.get("duration_clock")
            if sp_clock == "monotonic":
                dur_str = f" ({elapsed}s, monotonic)"
            elif sp_clock == "wall_clock":
                dur_str = f" ({elapsed}s, wall-clock)"
            else:
                dur_str = f" ({elapsed}s)"
        else:
            started = _as_float(sp.get("started_at_utc"))
            ended = _as_float(sp.get("ended_at_utc"))
            if started is not None and ended is not None:
                elapsed = round(max(0.0, ended - started), 3)
                dur_str = f" ({elapsed}s, wall-clock)"
            else:
                dur_str = ""
        print(f"  [{green if rc == 0 else red}{rc}{rst}] {cmd_str}{dur_str}", file=stream)

    print(file=stream)


def format_elapsed_range(total_seconds: float) -> tuple[str, str]:
    sec_int = int(round(total_seconds))
    days = sec_int // 86400
    hours = (sec_int % 86400) // 3600
    minutes = (sec_int % 3600) // 60
    secs = sec_int % 60

    if days > 0:
        return "0d 00:00:00", f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}"
    elif hours > 0:
        return "00:00:00", f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return "00:00", f"{minutes:02d}:{secs:02d}"


_DURATION_EXAMPLES = "valid examples: '30s', '10m', '2h', '1d'"


def parse_duration(val: str) -> float:
    if not isinstance(val, str):
        raise ValueError(f"duration must be a string ({_DURATION_EXAMPLES})")
    raw = val.strip().lower()
    if not raw:
        raise ValueError(f"duration string is empty ({_DURATION_EXAMPLES})")
    multipliers = {"d": 86400.0, "h": 3600.0, "m": 60.0, "s": 1.0}
    unit = raw[-1]
    if unit in multipliers:
        num_str = raw[:-1]
        mult = multipliers[unit]
    else:
        num_str = raw
        mult = 1.0
    try:
        amount = float(num_str)
    except ValueError as exc:
        raise ValueError(f"invalid duration {val!r} ({_DURATION_EXAMPLES})") from exc
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError(
            f"duration {val!r} must be a positive finite value ({_DURATION_EXAMPLES})"
        )
    result = amount * mult
    if not math.isfinite(result) or result <= 0:
        raise ValueError(
            f"duration {val!r} must be a positive finite value ({_DURATION_EXAMPLES})"
        )
    return result


def draw_ascii_chart(
    data: list[float],
    timestamps: list[float],
    title: str,
    unit: str,
    height: int = 8,
    width: int = 50,
    color: str = "",
    use_color: bool = True,
    average: bool = False,
    use_utc: bool = False,
    *,
    out: Optional[TextIO] = None,
) -> None:
    """Helper to render a standardized ASCII utilization area graph."""
    stream = out if out is not None else sys.stdout

    valid_pairs = [
        (float(ts), float(val))
        for ts, val in zip(timestamps or [], data or [])
        if _is_finite_number(ts) and _is_finite_number(val)
    ]
    if not valid_pairs:
        print(f"\n{title}: No valid resource samples to plot.", file=stream)
        return

    timestamps = [p[0] for p in valid_pairs]
    data = [p[1] for p in valid_pairs]
    height = max(2, int(height))
    width = max(1, int(width))

    min_val = 0.0
    max_val = max(0.1, max(data))
    if unit == "%":
        max_val = max(100.0, max_val)

    n = len(data)
    y_vals = []
    if n <= width:
        # No downsampling needed, just interpolate/map to closest indices
        for x in range(width):
            idx = int(round(x * (n - 1) / (width - 1))) if width > 1 else 0
            idx = max(0, min(n - 1, idx))
            y_vals.append(data[idx])
    else:
        # Downsampling needed: group by bin
        t_start = timestamps[0]
        t_end = timestamps[-1]
        total_time = t_end - t_start

        # Initialize bins
        bins: List[List[Any]] = [[] for _ in range(width)]
        for i in range(n):
            t = timestamps[i]
            if total_time > 0:
                pct = (t - t_start) / total_time
                bin_idx = int(pct * width)
                bin_idx = max(0, min(width - 1, bin_idx))
            else:
                bin_idx = 0
            bins[bin_idx].append(data[i])

        for x in range(width):
            bin_data = bins[x]
            if not bin_data:
                # Fallback to nearest neighbor index
                idx = int(round(x * (n - 1) / (width - 1))) if width > 1 else 0
                idx = max(0, min(n - 1, idx))
                val = data[idx]
            else:
                if average:
                    val = sum(bin_data) / len(bin_data)
                else:
                    val = max(bin_data)
            y_vals.append(val)

    grid = [[" " for _ in range(width)] for _ in range(height)]

    char = "█" if _supports_unicode(stream) else "#"

    for x in range(width):
        y = y_vals[x]
        pct = (y - min_val) / (max_val - min_val)
        fill_height = int(round(pct * (height - 1)))
        fill_height = max(0, min(height - 1, fill_height))
        for r in range(height - 1, height - 1 - fill_height - 1, -1):
            if 0 <= r < height:
                grid[r][x] = char

    bold = Colors.BOLD if use_color else ""
    rst = Colors.RESET if use_color else ""

    corner = "└" if _supports_unicode(stream) else "+"
    pipe = "│" if _supports_unicode(stream) else "|"
    hline = "─" if _supports_unicode(stream) else "-"

    # Format max value string
    if data:
        max_data_val = max(data)
        if unit == "%":
            max_str = f"Max: {max_data_val:.1f}%"
        else:
            if unit in ("GB", "MB"):
                max_str = f"Max: {max_data_val:.2f} {unit}"
            else:
                max_str = f"Max: {max_data_val:.1f} {unit}"
    else:
        max_str = ""

    title_suffix = f" ({max_str})" if max_str else ""
    print(f"\n{bold}{title}{title_suffix}{rst}", file=stream)

    for r in range(height):
        val = max_val - r * (max_val - min_val) / (height - 1)
        label_str = f"{val:6.1f} {unit}".rjust(10)
        row_str = "".join(grid[r])
        if use_color and color:
            row_str = f"{color}{row_str}{rst}"
        print(f"  {label_str} {pipe} {row_str}", file=stream)

    # Put ticks at the start, 25%, middle, 75%, and end marks
    ticks_str = list(hline * width)
    if width > 1:
        tick_char = "┼" if _supports_unicode(stream) else "+"
        ticks_str[0] = tick_char
        ticks_str[-1] = tick_char
        ticks_str[(width - 1) // 2] = tick_char
        if width >= 8:
            ticks_str[(width - 1) // 4] = tick_char
            ticks_str[(3 * (width - 1)) // 4] = tick_char
    axis_line = "".join(ticks_str)
    print(f"  {' ' * 10} {corner}{axis_line}", file=stream)

    from pubrun.status import _format_elapsed

    # Format dates (local time by default; UTC with trailing 'Z' when use_utc=True)
    def _fmt_chart_ts(ts: float) -> str:
        try:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            if use_utc:
                return dt.strftime("%Y-%m-%d %H:%M:%SZ")
            return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except (OverflowError, OSError, ValueError, TypeError):
            return "unknown"

    t_start = timestamps[0]
    t_end = timestamps[-1]
    start_time_str = _fmt_chart_ts(t_start)
    end_time_str = _fmt_chart_ts(t_end)

    # Format elapsed durations
    duration = max(0.0, t_end - t_start)
    elapsed_total_str = _format_elapsed(duration)
    start_elapsed_str = "0d 00:00:00" if "d " in elapsed_total_str else "00:00:00"

    # Build tick indices
    tick_indices = []
    if width > 0:
        tick_indices.append(0)
    if width > 1:
        if width >= 8:
            tick_indices.append((width - 1) // 4)
        tick_indices.append((width - 1) // 2)
        if width >= 8:
            tick_indices.append((3 * (width - 1)) // 4)
        tick_indices.append(width - 1)

    # Greedy placement of elapsed labels
    placed: Dict[int, Tuple[int, int, str]] = {}  # maps idx -> (start_col, end_col, lbl_str)

    # Priority order: End tick, Start tick, Middle tick, then the rest
    priority_order = []
    if tick_indices:
        priority_order.append(tick_indices[-1])
        if tick_indices[0] not in priority_order:
            priority_order.append(tick_indices[0])
        mid_idx = tick_indices[len(tick_indices) // 2]
        if mid_idx not in priority_order:
            priority_order.append(mid_idx)
        for idx in tick_indices:
            if idx not in priority_order:
                priority_order.append(idx)

    for idx in priority_order:
        if idx == 0:
            lbl_str = start_elapsed_str
        else:
            lbl_str = _format_elapsed((idx / (width - 1)) * duration if width > 1 else 0.0)

        L = len(lbl_str)
        if L > width:
            continue
        if idx == 0:
            start_col = 0
        elif idx == width - 1:
            start_col = width - L
        else:
            start_col = idx - 1 - (L // 2)

        start_col = max(0, min(width - L, start_col))

        # Check overlap with gap = 1
        overlap = False
        for p_start, p_end, _ in placed.values():
            if not (start_col + L + 1 <= p_start or p_end + 1 <= start_col):
                overlap = True
                break

        if not overlap:
            placed[idx] = (start_col, start_col + L, lbl_str)

    # Build elapsed row
    elapsed_row_list = [" "] * width
    for idx in placed:
        s_col, e_col, lbl_str = placed[idx]
        elapsed_row_list[s_col:e_col] = list(lbl_str)
    row2_vals = "".join(elapsed_row_list)

    # Row 1 (Timeline):
    spaces1 = width - len(start_time_str) - len(end_time_str)
    if spaces1 > 0:
        row1_vals = f"{start_time_str}{' ' * spaces1}{end_time_str}"
    else:
        row1_vals = f"{start_time_str} ... {end_time_str}"

    prefix1 = "  Timeline".ljust(13) + ": "
    prefix2 = "  Elapsed".ljust(13) + ": "
    print(f"{prefix1}{row1_vals}", file=stream)
    print(f"{prefix2}{row2_vals}", file=stream)


def print_resources_report(
    manifest_path: str,
    average: bool = False,
    last: Optional[str] = None,
    metric: str = "all",
    width: Optional[int] = None,
    utc: bool = False,
    *,
    out: Optional[TextIO] = None,
) -> None:
    """Print a diagnostic resources report with ASCII utilization graphs over time."""
    stream = out if out is not None else sys.stdout
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except FileNotFoundError as e:
        raise DiagnosticsError(f"Could not find manifest file at '{manifest_path}'.") from e
    except json.JSONDecodeError as e:
        raise DiagnosticsError(
            f"The manifest file at '{manifest_path}' is corrupt or contains invalid JSON."
        ) from e

    # Hydrate!
    manifest = _as_dict(manifest)
    manifest, warnings = hydrate_manifest(manifest_path, manifest)
    manifest = _as_dict(manifest)

    use_color = _has_color(stream)
    bold = Colors.BOLD if use_color else ""
    rst = Colors.RESET if use_color else ""
    cyan = Colors.CYAN if use_color else ""
    blue = Colors.BLUE if use_color else ""
    yellow = Colors.YELLOW if use_color else ""
    red = Colors.RED if use_color else ""

    run = _as_dict(manifest.get("run"))
    timing = _as_dict(manifest.get("timing"))
    status = _as_dict(manifest.get("status"))
    inv = _as_dict(manifest.get("invocation"))
    resources = _as_dict(manifest.get("resources"))

    script_info = _as_dict(inv.get("script"))
    raw_basename = script_info.get("basename")
    script_name = raw_basename if isinstance(raw_basename, str) and raw_basename else "<interactive or module>"
    raw_outcome = status.get("outcome")
    outcome = str(raw_outcome) if raw_outcome not in (None, "") else "unknown"

    out_color = ""
    if use_color:
        if outcome == "completed":
            out_color = Colors.GREEN
        elif outcome in ("failed", "crashed"):
            out_color = Colors.RED
        elif outcome == "interrupted":
            out_color = Colors.YELLOW

    if use_color:
        if _supports_unicode(stream):
            print(f"\n{cyan}{bold}┌─────────────────────────────────────────────────┐{rst}", file=stream)
            print(f"{cyan}{bold}│               RESOURCE MONITORING               │{rst}", file=stream)
            print(f"{cyan}{bold}└─────────────────────────────────────────────────┘{rst}", file=stream)
        else:
            print(f"\n{cyan}{bold}+-------------------------------------------------+{rst}", file=stream)
            print(f"{cyan}{bold}|               RESOURCE MONITORING               |{rst}", file=stream)
            print(f"{cyan}{bold}+-------------------------------------------------+{rst}", file=stream)
    else:
        print(f"\n=================================================", file=stream)
        print(f"               RESOURCE MONITORING               ", file=stream)
        print(f"=================================================", file=stream)

    print(f"{cyan}Run ID{rst}      : {run.get('run_id')}", file=stream)
    print(f"{cyan}Script{rst}      : {script_name}", file=stream)
    print(f"{cyan}Status{rst}      : {out_color}{outcome}{rst}", file=stream)

    peak_rss = resources.get("peak_rss_bytes")
    peak_cpu = resources.get("peak_cpu_percent")
    end_rss = resources.get("end_rss_bytes")

    def _fmt_bytes(n: Any) -> Optional[str]:
        if not _is_finite_number(n):
            return None
        val = float(n)
        if val >= 1024**3:
            return f"{val / (1024**3):.2f} GB"
        if val >= 1024**2:
            return f"{val / (1024**2):.2f} MB"
        return f"{val / 1024:.2f} KB"

    # Per-sample series (for avg/min/max). Read once here; reused for the charts below.
    _events_path = Path(manifest_path).parent / "events.jsonl"
    series = read_resource_series(_events_path) if _events_path.exists() else \
        {"timestamps": [], "rss": [], "cpu": [], "tree_rss": [], "tree_cpu": []}

    def _bytes_stat_line(values, peak_fallback):
        st = _series_stats(values)
        if st:
            pk, avg, mn = st
            return f"peak {_fmt_bytes(pk)} / avg {_fmt_bytes(avg)} / min {_fmt_bytes(mn)}"
        if _is_finite_number(peak_fallback) and peak_fallback:
            return f"peak {_fmt_bytes(peak_fallback)}"  # no per-sample data (short/old run)
        return None

    def _cpu_stat_line(values, peak_fallback):
        st = _series_stats(values)
        if st:
            pk, avg, mn = st
            return f"peak {pk:.1f}% / avg {avg:.1f}% / min {mn:.1f}%"
        if _is_finite_number(peak_fallback):
            return f"peak {float(peak_fallback):.1f}%"
        return None

    # --- Main process: RSS + CPU (peak/avg/min from samples, peak fallback otherwise) ---
    if metric in ("mem", "all"):
        line = _bytes_stat_line(series["rss"], peak_rss)
        if line:
            print(f"{cyan}RSS (main){rst}   : {line}", file=stream)
        if _is_finite_number(end_rss) and end_rss:
            print(f"{cyan}End RSS{rst}      : {_fmt_bytes(end_rss)}", file=stream)

    if metric in ("cpu", "all"):
        line = _cpu_stat_line(series["cpu"], peak_cpu)
        if line:
            print(f"{cyan}CPU (main){rst}   : {line}", file=stream)

    # Comprehensive resource view (only for `pubrun res`; cpu/mem stay single-metric).
    # Each field is rendered only when present, so older manifests just show less.
    if metric == "all":
        # Process-tree RSS + CPU (when scope=tree). Explicit "(tree)" labels so the reader
        # is never misled into thinking the main-process numbers are the whole tree.
        tree_line = _bytes_stat_line(series["tree_rss"], resources.get("peak_tree_rss_bytes"))
        if tree_line:
            print(f"{cyan}RSS (tree){rst}   : {tree_line}", file=stream)
        tree_cpu_line = _cpu_stat_line(series["tree_cpu"], resources.get("peak_tree_cpu_percent"))
        if tree_cpu_line:
            print(f"{cyan}CPU (tree){rst}   : {tree_cpu_line} {yellow}(% of one core; may exceed 100%){rst}", file=stream)

        # System memory (free/available) at start and worst point.
        sysmem = _as_dict(resources.get("system_memory"))
        if sysmem:
            start = _as_dict(sysmem.get("start"))
            worst = _as_dict(sysmem.get("min_available"))
            avail = start.get("available_bytes")
            total = start.get("total_bytes")
            if _is_finite_number(avail) and _is_finite_number(total) and total:
                print(f"{cyan}System RAM{rst}   : {_fmt_bytes(avail)} available of "
                      f"{_fmt_bytes(total)} at start", file=stream)
            worst_avail = worst.get("available_bytes")
            if _is_finite_number(worst_avail):
                print(f"{cyan}Min Avail RAM{rst}: {_fmt_bytes(worst_avail)} (lowest during run)", file=stream)

        # Load average (start / max 1-min).
        load = _as_dict(resources.get("load_average"))
        if load:
            start_l = _as_finite_float(_as_dict(load.get("start")).get("1min"))
            max_l = _as_finite_float(load.get("max_1min"))
            parts = []
            if start_l is not None:
                parts.append(f"{start_l:.2f} at start")
            if max_l is not None:
                parts.append(f"{max_l:.2f} peak (1-min)")
            if parts:
                print(f"{cyan}Load Average{rst} : {', '.join(parts)}", file=stream)

        # Node iowait (labeled node-wide / indicative only).
        iowait = _as_dict(resources.get("system_iowait_pct"))
        if iowait:
            mx = iowait.get("max")
            if _is_finite_number(mx):
                print(f"{cyan}Node iowait{rst}  : {mx}% peak {yellow}(node-wide, indicative only){rst}", file=stream)

        # Per-process I/O byte volume (this run), from /proc/self/io.
        io = _as_dict(resources.get("io_counters"))
        if io:
            delta = _as_dict(io.get("delta"))
            rb = delta.get("read_bytes")
            wb = delta.get("write_bytes")
            rc = delta.get("rchar")
            wc = delta.get("wchar")
            if _is_finite_number(rb) or _is_finite_number(wb):
                rb_val = rb if _is_finite_number(rb) else 0
                wb_val = wb if _is_finite_number(wb) else 0
                print(f"{cyan}Disk I/O{rst}     : read {_fmt_bytes(rb_val)}, "
                      f"wrote {_fmt_bytes(wb_val)} (storage layer)", file=stream)
            if _is_finite_number(rc) or _is_finite_number(wc):
                rc_val = rc if _is_finite_number(rc) else 0
                wc_val = wc if _is_finite_number(wc) else 0
                print(f"{cyan}Logical I/O{rst}  : read {_fmt_bytes(rc_val)}, "
                      f"wrote {_fmt_bytes(wc_val)} (incl. cache)", file=stream)

    if not _events_path.exists():
        print(f"\n{yellow}No events.jsonl file found. Cannot generate utilization graphs.{rst}\n", file=stream)
        return

    # Reuse the series already read for the summary above (single read of events.jsonl).
    timestamps = list(series["timestamps"])
    # Plot the process-tree RSS only when the run was recorded in tree scope AND every
    # sample carries a tree value (so it lines up with the timestamps); otherwise plot the
    # main-process RSS. The chart title below follows whichever series is plotted.
    _scope = resources.get("scope", "process")
    _tree_rss = list(series.get("tree_rss") or [])
    plot_tree = _scope == "tree" and bool(_tree_rss) and len(_tree_rss) == len(timestamps)
    rss_values = _tree_rss if plot_tree else list(series["rss"])
    cpu_values = list(series["cpu"])
    if not timestamps:
        print(f"\n{yellow}No resource samples found in events.jsonl.{rst}\n", file=stream)
        return

    last_seconds = None
    if last is not None:
        try:
            last_seconds = parse_duration(last)
        except ValueError as e:
            raise DiagnosticsError(f"Invalid duration for --last: {e}") from e

    if last_seconds is not None and timestamps:
        cutoff_time = timestamps[-1] - last_seconds
        filtered_timestamps = []
        filtered_rss = []
        filtered_cpu = []
        for ts, rss, cpu in zip(timestamps, rss_values, cpu_values):
            if ts >= cutoff_time:
                filtered_timestamps.append(ts)
                filtered_rss.append(rss)
                filtered_cpu.append(cpu)
        timestamps = filtered_timestamps
        rss_values = filtered_rss
        cpu_values = filtered_cpu

    # Guard against any non-finite entries in case series was supplied or modified externally.
    finite_triples = [
        (float(ts), float(rss), float(cpu))
        for ts, rss, cpu in zip(timestamps, rss_values, cpu_values)
        if _is_finite_number(ts) and _is_finite_number(rss) and _is_finite_number(cpu)
    ]
    timestamps = [t[0] for t in finite_triples]
    rss_values = [t[1] for t in finite_triples]
    cpu_values = [t[2] for t in finite_triples]

    if not rss_values:
        print(f"\n{yellow}No resource samples found in events.jsonl.{rst}\n", file=stream)
        return

    if len(rss_values) < 2:
        print(f"\nOnly one resource sample recorded:", file=stream)
        if metric in ("mem", "all"):
            if rss_values[0] >= 1024**3:
                single_rss = f"{rss_values[0] / (1024**3):.2f} GB"
            else:
                single_rss = f"{rss_values[0] / (1024**2):.2f} MB"
            print(f"  Memory: {single_rss}", file=stream)
        if metric in ("cpu", "all"):
            print(f"  CPU   : {cpu_values[0]}%", file=stream)
        print(file=stream)
        return

    # Get terminal width for dynamic sizing
    if width is not None:
        chart_width = max(20, width)
    else:
        try:
            columns = os.get_terminal_size().columns
        except OSError:
            columns = 80
        chart_width = max(20, columns - 20)

    # Scope label names the series actually plotted, so a reader isn't misled into
    # thinking a thin orchestrator's RSS is the whole tree (or vice versa).
    _scope_label = "process tree" if plot_tree else "main process"

    # Plot CPU (Yellow theme). CPU% is always measured for the main process
    # (child CPU is excluded from the metric), regardless of RSS scope.
    if metric in ("cpu", "all"):
        draw_ascii_chart(
            cpu_values,
            timestamps,
            "CPU Utilization History (main process)",
            "%",
            height=8,
            width=chart_width,
            color=Colors.YELLOW if use_color else "",
            use_color=use_color,
            average=average,
            use_utc=utc,
            out=stream,
        )

    # Plot Memory (Green theme)
    if metric in ("mem", "all"):
        # Determine memory scale
        max_mem_val = max(rss_values)
        if max_mem_val >= 1024**3:
            mem_scale = 1024**3
            mem_unit = "GB"
        elif max_mem_val >= 1024**2:
            mem_scale = 1024**2
            mem_unit = "MB"
        else:
            mem_scale = 1024
            mem_unit = "KB"

        scaled_rss = [r / mem_scale for r in rss_values]

        draw_ascii_chart(
            scaled_rss,
            timestamps,
            f"Memory (RSS) History ({_scope_label})",
            mem_unit,
            height=8,
            width=chart_width,
            color=Colors.GREEN if use_color else "",
            use_color=use_color,
            average=average,
            use_utc=utc,
            out=stream,
        )
    print(file=stream)
