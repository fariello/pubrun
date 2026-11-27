import argparse
from collections import deque
import contextlib
import heapq
import sys
import os
import re
import json
import math
import shutil
import time
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, NoReturn, Optional, Set, Tuple

from pubrun import __version__

from pubrun.report import output as _out


def _print_error(message: str) -> None:
    _out.error(message)


def _print_warn(message: str) -> None:
    _out.warn(message)


def _resolve_output_base_dir(output_dir: Optional[str] = None) -> Path:
    """Resolve the active runs directory from explicit ``output_dir`` or config."""
    if output_dir:
        return Path(os.path.expanduser(os.path.expandvars(output_dir)))
    try:
        from pubrun.config import resolve_config
        base_str = resolve_config().get("core", {}).get("output_dir", "")
        return Path(base_str) if base_str else Path.cwd() / "runs"
    except Exception:
        return Path("runs")


def _format_no_runs_error(all_runs_count: int, output_dir: Optional[str] = None) -> str:
    """Distinguish an empty runs directory from a filter that matched zero runs."""
    if all_runs_count == 0:
        runs_dir = _resolve_output_base_dir(output_dir)
        return f"No runs found in '{runs_dir}'."
    return f"0 of {all_runs_count} runs matched the filter criteria."


def _dump_strict_json(payload: Any, *, indent: Optional[int] = 2) -> str:
    """Serialize payload as strict RFC 8259 JSON (sanitizing non-finite floats)."""
    from pubrun.writer import _sanitize_json_value
    return json.dumps(
        _sanitize_json_value(payload),
        indent=indent,
        allow_nan=False,
        default=str,
    )


def _serialize_run_info(run_info: Any, *, index: Optional[int]) -> Dict[str, Any]:
    """Serialize a RunInfo object into the stable ``status --json`` schema."""
    return {
        "index": index,
        "run_id": getattr(run_info, "run_id", None),
        "run_dir": str(getattr(run_info, "run_dir", "")),
        "script": getattr(run_info, "script", None),
        "args": getattr(run_info, "args", None),
        "status": getattr(run_info, "status", None),
        "exit_code": getattr(run_info, "exit_code", None),
        "started_at_utc": getattr(run_info, "started_at_utc", None),
        "ended_at_utc": getattr(run_info, "ended_at_utc", None),
        "elapsed": getattr(run_info, "elapsed", None),
        "workload_seconds": getattr(run_info, "workload_seconds", None),
        "pid": getattr(run_info, "pid", None),
        "hostname": getattr(run_info, "hostname", None),
        "git_commit": getattr(run_info, "git_commit", None),
        "cwd": getattr(run_info, "cwd", None),
        "event_count": getattr(run_info, "event_count", None),
        "console_log_size": getattr(run_info, "console_log_size", None),
    }


def _emit_ambiguous_selector(e: Any) -> None:
    """Print a clear, non-guessing message when a selector matched multiple runs."""
    by_recency = getattr(e, "by_recency", None)
    by_id = getattr(e, "by_id", None)
    candidates = getattr(e, "candidates", None)
    if candidates and (by_recency is None or by_id is None):
        items = []
        for c in candidates:
            cid = getattr(c, "run_id", None) or "?"
            cdir = getattr(getattr(c, "run_dir", None), "name", "?")
            items.append(f"{cid} ({cdir})")
        _out.warn(
            f"'{e.selector}' is ambiguous; matched {len(candidates)} runs: "
            f"{', '.join(items)}. Refusing to guess. Re-run with a longer run ID "
            f"or the full run directory path to disambiguate."
        )
        return
    rec = getattr(by_recency, "run_id", "?")
    other = getattr(by_id, "run_id", "?")
    _out.warn(
        f"'{e.selector}' is ambiguous: it means both the {e.selector}th-most-recent run "
        f"(id {rec}) AND run id '{other}'. Refusing to guess. Re-run with the full run id "
        f"or the run directory path to disambiguate.")


def _create_config(destination: str) -> None:
    """Create a default ``.pubrun.toml`` at the given path. Refuses to overwrite."""
    try:
        # Resolve the package-native default architecture
        from pubrun.config import _read_package_resource
        content = _read_package_resource("pubrun.resources", "default.toml")

        target_path = Path(destination).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if target_path.exists():
            _print_error(f"'{target_path}' already exists. Refusing to overwrite.")
            sys.exit(1)

        target_path.write_text(content, encoding="utf-8")
        _out.ok(f"Successfully created configuration at: {target_path}")

    except Exception as e:
        _print_error(f"Failed to create config: {e}")
        sys.exit(1)


class RunInProgressOrCrashedError(Exception):
    """Raised when a run has a lock file but no manifest.json yet."""
    def __init__(self, run_dir: Path) -> None:
        super().__init__()
        self.run_dir = run_dir
        try:
            from pubrun.status import RunInfo
            self.run_info: Optional[RunInfo] = RunInfo(run_dir)
        except Exception:
            self.run_info = None


def _get_manifest_path(
    run_dir: str,
    filter_str: Optional[str] = None,
    status_filter: Optional[str] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
    not_filter_str: Optional[str] = None,
    not_status_filter: Optional[str] = None,
    output_dir: Optional[str] = None,
    runs: Optional[List[Any]] = None,
) -> str:
    """Resolve the path to a manifest.json, auto-detecting the latest run if needed."""
    if run_dir:
        # Resolve via find_run first (supports recency index / id-prefix / dir-substring).
        from pubrun.status import find_run, AmbiguousRunSelectorError
        try:
            run_info = find_run(run_dir, output_dir, runs=runs)
            if run_info:
                run_path = run_info.run_dir
            else:
                run_path = Path(run_dir)
        except AmbiguousRunSelectorError as e:
            _emit_ambiguous_selector(e)
            sys.exit(1)
        except Exception:
            run_path = Path(run_dir)

        manifest_path = run_path if (run_path.is_file() and run_path.name == "manifest.json") else (run_path / "manifest.json")

        if manifest_path.exists():
            return str(manifest_path)

        # If manifest doesn't exist, check if there is a lock file in that folder
        lock_path = run_path / ".pubrun.lock" if run_path.is_dir() else (run_path.parent / ".pubrun.lock")
        if lock_path.exists():
            raise RunInProgressOrCrashedError(run_path if run_path.is_dir() else run_path.parent)

        raise FileNotFoundError(f"Run directory '{run_dir}' does not exist or does not contain a manifest.json.")
    else:
        # Auto-detect latest run matching the filters
        runs_dir = _resolve_output_base_dir(output_dir)

        if not runs_dir.exists() or not runs_dir.is_dir():
            _print_error(
                f"No run specified and '{runs_dir}' directory not found. "
                "Run a tracked script first or pass a run path/ID (use 'pubrun status' to list runs)."
            )
            sys.exit(1)

        from pubrun.status import scan_runs, filter_runs
        all_runs = runs if runs is not None else scan_runs(str(runs_dir), keep_manifest=False)
        try:
            matched = filter_runs(
                all_runs,
                filter_str=filter_str,
                status_filter=status_filter,
                limit=1,  # We only need the latest matching run
                older_than=older_than,
                exit_code=exit_code,
                not_filter_str=not_filter_str,
                not_status_filter=not_status_filter,
            )
        except ValueError as e:
            _print_error(str(e))
            sys.exit(1)
        if not matched:
            _print_error(_format_no_runs_error(len(all_runs), str(runs_dir)))
            sys.exit(1)

        latest_run = matched[0].run_dir
        manifest_path = latest_run / "manifest.json"
        if manifest_path.exists():
            _out.info(f"Auto-detected matching run: {latest_run}")
            return str(manifest_path)

        # Check if lock file exists in the latest run
        if (latest_run / ".pubrun.lock").exists():
            raise RunInProgressOrCrashedError(latest_run)

        # If neither exist, fall back to raising file not found
        raise FileNotFoundError(f"Could not find manifest file at '{manifest_path}'.")


def _resolve_methods_format(format_type: Optional[str]) -> str:
    """Resolve methods output format from explicit CLI flag or ``[methods].format`` config."""
    if format_type in ("markdown", "latex"):
        return format_type
    try:
        from pubrun.config import resolve_config
        cfg_fmt = resolve_config().get("methods", {}).get("format", "markdown")
        if isinstance(cfg_fmt, str) and cfg_fmt.lower() in ("markdown", "latex"):
            return cfg_fmt.lower()
    except Exception:
        pass
    return "markdown"


def _run_methods(
    run_dir: str,
    format_type: Optional[str] = None,
    filter_str: Optional[str] = None,
    status_filter: Optional[str] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
    not_filter_str: Optional[str] = None,
    not_status_filter: Optional[str] = None,
    aggregate: bool = False,
    limit: Optional[int] = None,
    output_dir: Optional[str] = None,
) -> None:
    """Generate and print an academic 'Computational Methods' paragraph.

    Default: the single most-recent matching run (unchanged behavior). With
    ``aggregate=True`` (the ``--all`` flag): aggregate ALL matching runs into one
    representative paragraph plus a variance note (IPD 20260706-methods-multi-run).
    """
    resolved_format = _resolve_methods_format(format_type)
    if aggregate:
        _run_methods_aggregate(
            run_dir, resolved_format,
            filter_str=filter_str, status_filter=status_filter,
            older_than=older_than, exit_code=exit_code,
            not_filter_str=not_filter_str, not_status_filter=not_status_filter,
            limit=limit, output_dir=output_dir,
        )
        return
    try:
        from pubrun.report.methods import generate_report
        from pubrun.report.utils import hydrate_manifest

        manifest_path = _get_manifest_path(
            run_dir,
            filter_str=filter_str,
            status_filter=status_filter,
            older_than=older_than,
            exit_code=exit_code,
            not_filter_str=not_filter_str,
            not_status_filter=not_status_filter,
            output_dir=output_dir,
        )

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # Hydrate to merge parent HPC context if available
        manifest, warnings = hydrate_manifest(manifest_path, manifest)
        if warnings:
            for w in warnings:
                _out.warn(w)

        # Dispatch to structural compilers; decorative banners go to stderr so stdout is pipe-clean.
        text = generate_report(manifest, resolved_format)
        print("--- Generated Computational Methods Section ---", file=sys.stderr)
        print(text)
        print("-----------------------------------------------\n", file=sys.stderr)
    except RunInProgressOrCrashedError as e:
        status = e.run_info.status if e.run_info else "crashed/running"
        _print_error(f"Run '{e.run_dir.name}' is currently {status} and does not have a manifest.json.")
        sys.exit(1)
    except FileNotFoundError as e:
        _print_error(str(e))
        sys.exit(1)
    except Exception as e:
        _print_error(f"Failed to generate methods section: {e}")
        sys.exit(1)


# Threshold above which the aggregate note nudges the user to narrow the set.
_METHODS_LARGE_SET = 25


def _run_methods_aggregate(
    run_dir: str,
    format_type: Optional[str] = None,
    filter_str: Optional[str] = None,
    status_filter: Optional[str] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
    not_filter_str: Optional[str] = None,
    not_status_filter: Optional[str] = None,
    limit: Optional[int] = None,
    output_dir: Optional[str] = None,
) -> None:
    """`pubrun methods --all`: aggregate the matching run set into one paragraph.

    Reuses the existing run-filter machinery (scan_runs + filter_runs). Loads each
    manifest defensively (skips malformed, counts them). Emits the methods
    paragraph, then a "narrow it" suggestion CLEARLY MARKED as not part of the
    methods text (authoritative textual marker; optional non-DIM color; safe
    under NO_COLOR).
    """
    from pubrun.report.methods import generate_report_multi
    from pubrun.report.utils import hydrate_manifest
    from pubrun.status import scan_runs, filter_runs

    resolved_format = _resolve_methods_format(format_type)

    if run_dir:
        _print_error("`pubrun methods --all` aggregates a filtered set; do not also "
                     "pass a specific run directory. Use -f/--filter, -F/--not-filter, "
                     "-s/--status, -S/--not-status, or -n/--limit to select.")
        sys.exit(1)

    all_runs = scan_runs(output_dir, keep_manifest=False)
    try:
        matched = filter_runs(
            all_runs,
            filter_str=filter_str,
            status_filter=status_filter,
            limit=limit,
            older_than=older_than,
            exit_code=exit_code,
            not_filter_str=not_filter_str,
            not_status_filter=not_status_filter,
        )
    except ValueError as e:
        _print_error(str(e))
        sys.exit(1)
    if not matched:
        _print_error(_format_no_runs_error(len(all_runs), output_dir))
        sys.exit(1)

    manifests: list = []
    skipped = 0
    for r in matched:
        mp = r.run_dir / "manifest.json"
        m = r.load_manifest()
        if m is None:
            skipped += 1
            continue
        try:
            m, _warnings = hydrate_manifest(str(mp), m)
            manifests.append(m)
        except Exception:
            skipped += 1  # malformed/unreadable manifest - skip, don't abort

    if not manifests:
        _print_error("No readable manifests among the matching runs.")
        sys.exit(1)

    text = generate_report_multi(manifests, resolved_format)
    print("--- Generated Computational Methods Section ---", file=sys.stderr)
    print(text)
    print("-----------------------------------------------\n", file=sys.stderr)

    # Non-methods suggestion: authoritative textual marker (works under NO_COLOR,
    # pipes, screen readers), optional full-strength color reinforcement (never
    # DIM — DIM's contrast against an arbitrary terminal theme is unknowable and
    # not reliably WCAG 2.1 AA). Emitted to stderr so it can never be pasted into
    # a paper as methods text.
    n = len(manifests)
    notes = []
    if skipped:
        notes.append(f"{skipped} matching run(s) had no readable manifest and were skipped.")
    if n > _METHODS_LARGE_SET:
        notes.append(
            f"aggregated {n} runs; consider narrowing with -f/--filter, -F/--not-filter, "
            f"-s/--status, or -n/--limit if that is broader than the study you mean to report."
        )
    if notes:
        from pubrun.report.diagnostics import Colors
        use_color = _out.use_color(sys.stderr)
        prefix = "# pubrun note (not part of the methods section):"
        if use_color:
            prefix = f"{Colors.CYAN}{prefix}{Colors.RESET}"
        print(prefix, file=sys.stderr)
        for note in notes:
            line = f"#   {note}"
            print(f"{Colors.CYAN}{line}{Colors.RESET}" if use_color else line, file=sys.stderr)


def _assess_cli_run(
    hydrated_manifest: dict,
    *,
    manifest_path: str,
    hydration_report,
    current_hostname: Optional[str],
    preflight: bool,
) -> dict:
    """Run the shared reproducibility engine for CLI commands."""
    from pubrun.report.checks import assess_run

    return assess_run(
        hydrated_manifest,
        manifest_path=manifest_path,
        hydration_report=hydration_report,
        current_hostname=current_hostname,
        preflight=preflight,
    )


def _format_rerun_cmd_for_platform(rerun_cmd: str) -> str:
    """Apply platform-specific formatting for printed rerun commands."""
    if sys.platform == "win32" and " && python " in rerun_cmd:
        import subprocess

        def _split_preserving_backslashes(part: str) -> list:
            # Parse whitespace-separated tokens honoring POSIX single quotes
            # (including '\'' escaped apostrophes) and double quotes without
            # consuming Windows path backslashes.
            tokens: list = []
            buf: list = []
            in_tok = False
            i = 0
            n = len(part)
            while i < n:
                ch = part[i]
                if ch.isspace():
                    if in_tok:
                        tokens.append("".join(buf))
                        buf.clear()
                        in_tok = False
                    i += 1
                elif ch == "'":
                    in_tok = True
                    end = part.find("'", i + 1)
                    if end == -1:
                        buf.append(part[i + 1 :])
                        break
                    buf.append(part[i + 1 : end])
                    i = end + 1
                elif ch == "\\" and i + 1 < n and part[i + 1] == "'":
                    in_tok = True
                    buf.append("'")
                    i += 2
                elif ch == '"':
                    in_tok = True
                    end = part.find('"', i + 1)
                    if end == -1:
                        buf.append(part[i + 1 :])
                        break
                    buf.append(part[i + 1 : end])
                    i = end + 1
                else:
                    in_tok = True
                    buf.append(ch)
                    i += 1
            if in_tok:
                tokens.append("".join(buf))
            return tokens

        def _to_win_line(part: str) -> str:
            if "'" not in part:
                return part
            return subprocess.list2cmdline(_split_preserving_backslashes(part))

        cd_part, py_part = rerun_cmd.split(" && ", 1)
        return f"{_to_win_line(cd_part)}\n{_to_win_line(py_part)}"
    return rerun_cmd


def _run_rerun(
    run_dir: str,
    filter_str: Optional[str] = None,
    status_filter: Optional[str] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
    not_filter_str: Optional[str] = None,
    not_status_filter: Optional[str] = None,
    preflight: bool = False,
    strict: bool = False,
    fail_on: Optional[str] = None,
    as_json: bool = False,
    output_dir: Optional[str] = None,
) -> None:
    """Print the shell command needed to reproduce a recorded run.

    When ``preflight`` is False, preserves exact backwards-compatible stdout-only
    piping behavior. When ``preflight`` is True, runs read-only offline preflight
    comparison against the current environment and emits diagnostics to stderr
    (or structured JSON to stdout under ``--json``) without executing the command.
    """
    if (strict or fail_on is not None or as_json) and not preflight:
        _print_error("--strict, --fail-on, and --json require --preflight with `pubrun rerun`.")
        sys.exit(2)

    try:
        manifest_path = _get_manifest_path(
            run_dir,
            filter_str=filter_str,
            status_filter=status_filter,
            older_than=older_than,
            exit_code=exit_code,
            not_filter_str=not_filter_str,
            not_status_filter=not_status_filter,
            output_dir=output_dir,
        )
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        inv = manifest.get("invocation", {}) if isinstance(manifest, dict) else {}
        rerun_cmd = inv.get("rerun_command") if isinstance(inv, dict) else None

        if not preflight:
            if rerun_cmd:
                print(_format_rerun_cmd_for_platform(rerun_cmd))
            else:
                _print_error("Target manifest does not contain a valid 'rerun_command' payload.")
                sys.exit(1)
            return

        if not isinstance(rerun_cmd, str) or not rerun_cmd:
            _print_error("Target manifest does not contain a valid 'rerun_command' payload.")
            sys.exit(1)

        rerun_cmd = _format_rerun_cmd_for_platform(rerun_cmd)

        from pubrun.report.utils import hydrate_manifest_with_report
        from pubrun.report.checks import should_fail_strict
        from pubrun.report.reproducibility import format_reproducibility_summary
        from pubrun.report.diagnostics import format_redacted_rerun_advisory

        hydrated, _hydration_warnings, hydration_report = hydrate_manifest_with_report(
            manifest_path, manifest
        )
        import socket
        try:
            current_hostname = socket.gethostname()
        except Exception:
            current_hostname = None

        assessment = _assess_cli_run(
            hydrated,
            manifest_path=manifest_path,
            hydration_report=hydration_report,
            current_hostname=current_hostname,
            preflight=True,
        )
        strict_enabled = bool(strict or fail_on is not None)
        strict_failed = strict_enabled and should_fail_strict(
            assessment, fail_on=fail_on or "warn"
        )
        executable_as_printed = "[REDACTED]" not in rerun_cmd

        if as_json:
            payload = {
                "rerun_command": rerun_cmd,
                "executable_as_printed": executable_as_printed,
                "assessment": assessment,
            }
            print(json.dumps(payload, indent=2))
            if strict_failed:
                sys.exit(1)
            return

        # Human / pipe mode: all preflight diagnostics go to stderr; stdout stays clean.
        print(format_reproducibility_summary(assessment), file=sys.stderr)
        advisory = format_redacted_rerun_advisory(rerun_cmd)
        if advisory:
            _print_warn(advisory)
        if strict_failed:
            sys.exit(1)
        print(rerun_cmd)
    except RunInProgressOrCrashedError as e:
        status = e.run_info.status if e.run_info else "crashed/running"
        lock_data = e.run_info.lock_data if (e.run_info and hasattr(e.run_info, "lock_data")) else None
        if not lock_data:
            _print_error(f"Run '{e.run_dir.name}' is currently {status} and does not have a manifest.json.")
            sys.exit(1)

        cwd = lock_data.get("cwd")
        sys_argv = lock_data.get("sys_argv")
        if not sys_argv:
            # Reconstruct from script and argv if sys_argv is not present (for compatibility)
            script = lock_data.get("script") or "script.py"
            script_filename = script if script.endswith(".py") else f"{script}.py"
            argv = lock_data.get("argv", [])
            sys_argv = [script_filename] + argv

        import shlex
        if sys.platform == "win32":
            import subprocess as _sp
            redacted_cmdline = _sp.list2cmdline(sys_argv)
            cwd_str = _sp.list2cmdline([str(cwd)]) if cwd else "."
            rerun_cmd = f"cd {cwd_str}\npython {redacted_cmdline}"
        else:
            redacted_cmdline = shlex.join(sys_argv)
            cwd_str = shlex.quote(str(cwd)) if cwd else "."
            rerun_cmd = f"cd {cwd_str} && python {redacted_cmdline}"

        rerun_cmd = _format_rerun_cmd_for_platform(rerun_cmd)

        if not preflight:
            _print_warn(
                f"Run '{e.run_dir.name}' is currently {status} and does not have a manifest.json. "
                "Reconstructed rerun command from lock file:"
            )
            print(rerun_cmd)
            return

        executable_as_printed = "[REDACTED]" not in rerun_cmd
        strict_enabled = bool(strict or fail_on is not None)

        if as_json:
            from pubrun.report.reproducibility import NON_GUARANTEE_DISCLAIMER

            lock_findings = [
                {
                    "severity": "warn",
                    "code": "run_not_finalized",
                    "message": (
                        f"Run '{e.run_dir.name}' is currently {status} and does not have a finalized "
                        "manifest.json; reconstructed rerun command from .pubrun.lock is inferred "
                        "and offline preflight checks require a finalized manifest.json."
                    ),
                    "suggestion": (
                        "Wait for the run to finalize or inspect crashed-run logs before running preflight."
                    ),
                    "category": "capture_completeness",
                    "evidence_status": "inferred",
                    "impact": "material",
                    "comparison": "unknown",
                    "details": {"status": status, "run_dir": e.run_dir.name},
                }
            ]
            if not executable_as_printed:
                lock_findings.append(
                    {
                        "severity": "warn",
                        "code": "rerun_command_redacted",
                        "message": (
                            "Reconstructed rerun_command contains [REDACTED] placeholders and is "
                            "not directly executable verbatim without supplying redacted arguments."
                        ),
                        "suggestion": (
                            "Supply the redacted argument values manually before executing the recorded command."
                        ),
                        "category": "invocation",
                        "evidence_status": "inferred",
                        "impact": "material",
                        "comparison": "mismatch",
                        "details": {"rerun_command_redacted": True},
                    }
                )
            lock_assessment = {
                "schema_version": "1.0",
                "mode": "preflight",
                "summary": (
                    f"Run '{e.run_dir.name}' is currently {status} without a finalized manifest.json; "
                    "preflight comparison is unknown and the lock-file command is inferred."
                ),
                "next_action": lock_findings[0]["suggestion"],
                "next_actions": [f["suggestion"] for f in lock_findings if f.get("suggestion")],
                "disclaimer": NON_GUARANTEE_DISCLAIMER,
                "categories": [],
                "findings": lock_findings,
                "parent_metadata": None,
                "preflight": {
                    "requested": True,
                    "status": "unknown",
                    "counts": {"unknown": 1},
                    "checks": [
                        {
                            "name": "manifest_finalized",
                            "category": "capture_completeness",
                            "comparison": "unknown",
                            "evidence_status": "inferred",
                            "impact": "material",
                            "severity": "warn",
                            "message": (
                                f"Run '{e.run_dir.name}' is currently {status} without a finalized "
                                "manifest.json; preflight requires a finalized manifest.json."
                            ),
                            "details": {"status": status},
                        }
                    ],
                },
            }
            payload = {
                "rerun_command": rerun_cmd,
                "executable_as_printed": executable_as_printed,
                "assessment": lock_assessment,
            }
            print(json.dumps(payload, indent=2))
            if strict_enabled:
                sys.exit(1)
            return

        from pubrun.report.diagnostics import format_redacted_rerun_advisory

        _print_warn(
            f"Run '{e.run_dir.name}' is currently {status} and does not have a finalized manifest.json. "
            "Preflight requires a finalized manifest.json; reconstructed rerun command from lock file is inferred."
        )
        advisory = format_redacted_rerun_advisory(rerun_cmd)
        if advisory:
            _print_warn(advisory)
        if strict_enabled:
            sys.exit(1)
        print(rerun_cmd)
    except Exception as e:
        _print_error(f"Failed to fetch rerun command: {e}")
        sys.exit(1)


def _resolve_direct_manifest_path(raw_path: str) -> str:
    """Resolve an explicit existing filesystem run path without scanning output_dir."""
    run_path = Path(raw_path)
    manifest_path = (
        run_path
        if (run_path.is_file() and run_path.name == "manifest.json")
        else (run_path / "manifest.json")
    )
    if manifest_path.exists():
        return str(manifest_path)
    lock_path = run_path / ".pubrun.lock" if run_path.is_dir() else (run_path.parent / ".pubrun.lock")
    if lock_path.exists():
        raise RunInProgressOrCrashedError(run_path if run_path.is_dir() else run_path.parent)
    raise FileNotFoundError(
        f"Run directory '{raw_path}' does not exist or does not contain a manifest.json."
    )


def _run_diff(
    run_dirs: List[str],
    export_format: Any,
    no_color: bool,
    wrap_config: Optional[bool] = None,
    max_length: Optional[int] = None,
    depth: str = "basic",
    show_same: Optional[bool] = None,
    filter_str: Optional[str] = None,
    not_filter_str: Optional[str] = None,
    status_filter: Optional[str] = None,
    not_status_filter: Optional[str] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
    table: bool = False,
    output_dir: Optional[str] = None,
    as_json: bool = False,
) -> None:
    """Run the semantic diff engine comparing two execution traces.

    When no positional run directories are given, the pair to compare is drawn from
    the runs matching the shared filter options (``-f/-F/-s/-S/--older-than/--exit-code``);
    with no filters this is every run with a manifest (the historical behavior).
    """
    if len(run_dirs) > 2:
        _print_error(f"diff accepts at most 2 runs, got {len(run_dirs)}.")
        sys.exit(2)
    if as_json and export_format:
        _print_error("--json cannot be combined with --export.")
        sys.exit(2)

    try:
        from pubrun.report.utils import hydrate_manifest
        from pubrun.config import resolve_config
        from pubrun.analysis.diff import compare_manifests, export_manifest
        from pubrun.analysis.render import print_diff
        from pubrun.status import AmbiguousRunSelectorError, scan_runs, find_run, filter_runs

        has_filter = any(v is not None for v in (
            filter_str, not_filter_str, status_filter, not_status_filter, older_than, exit_code
        ))

        if len(run_dirs) == 2 and Path(run_dirs[0]).exists() and Path(run_dirs[1]).exists():
            # Explicit existing filesystem paths: skip scan_runs() entirely.
            manifest_path_a = _resolve_direct_manifest_path(run_dirs[0])
            manifest_path_b = _resolve_direct_manifest_path(run_dirs[1])
        else:
            all_runs = scan_runs(output_dir, keep_manifest=False)
            if len(run_dirs) == 2:
                manifest_path_a = _get_manifest_path(run_dirs[0], output_dir=output_dir, runs=all_runs)
                manifest_path_b = _get_manifest_path(run_dirs[1], output_dir=output_dir, runs=all_runs)
            else:
                valid_runs = [r for r in all_runs if (r.run_dir / "manifest.json").exists()]
                if has_filter:
                    valid_runs = filter_runs(
                        valid_runs,
                        filter_str=filter_str,
                        status_filter=status_filter,
                        older_than=older_than,
                        exit_code=exit_code,
                        not_filter_str=not_filter_str,
                        not_status_filter=not_status_filter,
                    )

                if len(run_dirs) == 1:
                    run_dir_a = run_dirs[0]
                    r_a = find_run(run_dir_a, output_dir, runs=all_runs)
                    run_dir_a_path = r_a.run_dir if r_a else Path(run_dir_a)
                    if run_dir_a_path.is_file() and run_dir_a_path.name == "manifest.json":
                        run_dir_a_path = run_dir_a_path.parent

                    run_dir_b_path = None
                    for r in valid_runs:
                        if r.run_dir.resolve() != run_dir_a_path.resolve():
                            run_dir_b_path = r.run_dir
                            break
                    if not run_dir_b_path:
                        if has_filter:
                            _print_error("Only one run was provided, and no other runs matching the filter were found to compare against. Widen the filter or pass a second run directory.")
                        else:
                            _print_error("Only one run was provided, and no other runs with a manifest.json were found to compare against.")
                        sys.exit(1)

                    _out.info(f"Comparing {run_dir_a_path.name} against most recent other run: {run_dir_b_path.name}")
                    manifest_path_a = _get_manifest_path(run_dir_a, output_dir=output_dir, runs=all_runs)
                    manifest_path_b = _resolve_direct_manifest_path(str(run_dir_b_path))
                else:
                    if len(valid_runs) < 2:
                        if has_filter:
                            _print_error(f"diff needs two runs, but only {len(valid_runs)} matched the filter. Widen the filter or pass two run directories explicitly.")
                        else:
                            _print_error(f"Need at least 2 runs with manifest.json to perform default diff (found {len(valid_runs)}).")
                        sys.exit(1)
                    _out.info(f"Auto-detected last two runs for comparison: {valid_runs[1].run_dir.name} vs {valid_runs[0].run_dir.name}")
                    manifest_path_a = str(valid_runs[1].run_dir / "manifest.json")
                    manifest_path_b = str(valid_runs[0].run_dir / "manifest.json")

        with open(manifest_path_a, "r", encoding="utf-8") as f:
            manifest_a = json.load(f)

        with open(manifest_path_b, "r", encoding="utf-8") as f:
            manifest_b = json.load(f)

        manifest_a, warn_a = hydrate_manifest(manifest_path_a, manifest_a)
        manifest_b, warn_b = hydrate_manifest(manifest_path_b, manifest_b)

        for w in (warn_a or []) + (warn_b or []):
            _out.warn(w)

        conf = resolve_config().get("diff", {})

        if depth == "basic":
            ignores = conf.get("ignore_basic", [])
        elif depth == "standard":
            ignores = conf.get("ignore_standard", [])
        else:
            ignores = conf.get("ignore_deep", [])

        ss_target = show_same if show_same is not None else conf.get("show_same", False)

        if export_format:
            fmt = export_format if export_format is not True else conf.get("export_format", "txt")
            fmt = fmt.lower()
            if fmt not in ["txt", "json"]:
                _print_error(f"Unsupported export format '{fmt}'. Use 'txt' or 'json'.")
                sys.exit(1)

            name_a = Path(manifest_path_a).parent.name
            name_b = Path(manifest_path_b).parent.name

            out_a = f".pubrun_diff_A_{name_a}_clean.{fmt}"
            out_b = f".pubrun_diff_B_{name_b}_clean.{fmt}"

            Path(out_a).write_text(export_manifest(manifest_a, ignores, fmt, depth=depth), encoding="utf-8")
            Path(out_b).write_text(export_manifest(manifest_b, ignores, fmt, depth=depth), encoding="utf-8")

            _out.ok(f"Successfully exported semantic baseline A to: {out_a}")
            _out.ok(f"Successfully exported semantic target B to: {out_b}")
        elif as_json:
            diff_report = compare_manifests(manifest_a, manifest_b, ignores, show_same=ss_target, depth=depth)
            name_a = Path(manifest_path_a).parent.name
            name_b = Path(manifest_path_b).parent.name
            payload = {
                "run_a": name_a,
                "run_b": name_b,
                "depth": depth,
                "diff": diff_report,
            }
            print(_dump_strict_json(payload, indent=2))
        else:
            diff_report = compare_manifests(manifest_a, manifest_b, ignores, show_same=ss_target, depth=depth)
            wrap_target = wrap_config if wrap_config is not None else conf.get("wrap", True)
            mlen_target = max_length if max_length is not None else conf.get("max_string_length", 300)
            print_diff(diff_report, no_color=no_color, wrap=wrap_target, max_length=mlen_target, depth=depth, table=table)

    except AmbiguousRunSelectorError as e:
        _emit_ambiguous_selector(e)
        sys.exit(1)
    except RunInProgressOrCrashedError as e:
        status = e.run_info.status if e.run_info else "crashed/running"
        _print_error(f"Run '{e.run_dir.name}' is currently {status} and does not have a manifest.json.")
        sys.exit(1)
    except Exception as e:
        _print_error(f"Failed to generate diff report: {e}")
        sys.exit(1)


def _run_resources(
    run_dir: str,
    filter_str: Optional[str] = None,
    status_filter: Optional[str] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
    not_filter_str: Optional[str] = None,
    not_status_filter: Optional[str] = None,
    average: bool = False,
    last: Optional[str] = None,
    metric: str = "all",
    width: Optional[int] = None,
    output_dir: Optional[str] = None,
    utc: bool = False,
) -> None:
    """Print resource monitoring graphs for a recorded run."""
    from pubrun.report.diagnostics import DiagnosticsError, print_resources_report
    try:
        manifest_path = _get_manifest_path(
            run_dir,
            filter_str=filter_str,
            status_filter=status_filter,
            older_than=older_than,
            exit_code=exit_code,
            not_filter_str=not_filter_str,
            not_status_filter=not_status_filter,
            output_dir=output_dir,
        )
        print_resources_report(
            manifest_path,
            average=average,
            last=last,
            metric=metric,
            width=width,
            utc=utc,
        )
    except RunInProgressOrCrashedError as e:
        status = e.run_info.status if e.run_info else "crashed/running"
        _print_error(f"Run '{e.run_dir.name}' is currently {status} and does not have a manifest.json.")
        sys.exit(1)
    except FileNotFoundError as e:
        _print_error(str(e))
        sys.exit(1)
    except DiagnosticsError as e:
        _print_error(e.message)
        sys.exit(e.exit_code)
    except Exception as e:
        _print_error(f"Failed to generate resources report: {e}")
        sys.exit(1)



def _render_config_toml(config: dict, title: str, note: Optional[str] = None,
                        provenance: Optional[dict] = None, show_all: bool = False) -> None:
    """Print a resolved config dict as readable, deterministic key=value lines.

    When ``provenance`` is supplied (leaf-key -> {"layer","overrides":[...]}), keys are
    annotated with their source layer; by default only OVERRIDDEN keys are annotated (a
    clean, no-conflict config prints without annotations), unless ``show_all`` is set.
    """
    print(f"# {title}")
    if note:
        print(f"# {note}")

    def walk(d: dict, prefix: str = "") -> None:
        for key in sorted(d.keys()):
            val = d[key]
            dotted = f"{prefix}{key}"
            if isinstance(val, dict):
                walk(val, dotted + ".")
                continue
            line = f"{dotted} = {val!r}"
            if provenance is not None:
                info = provenance.get(dotted)
                if info:
                    overrides = info.get("overrides") or []
                    if overrides:
                        shadowed = ", ".join(f"{o['layer']} {o['value']!r}" for o in overrides)
                        line += f"    [{info['layer']}, overrides {shadowed}]"
                    elif show_all:
                        line += f"    [{info['layer']}]"
            print(line)

    walk(config)


def _run_show_config(
    mode: str,
    run_selector: Optional[str] = None,
    show_all: bool = False,
    output_dir: Optional[str] = None,
) -> None:
    """Show resolved configuration for one of three contexts.

    mode: "current"  -> live resolve_config() in the CWD (what `import pubrun` would use now)
          "run"      -> the resolved config a past run actually used (config.resolved.json)
          "default"  -> the shipped built-in defaults (raw default.toml)
    """
    from pubrun.config import resolve_config_with_provenance, _read_package_resource

    if mode == "default":
        # Raw packaged defaults, verbatim (same source as the legacy --show-config).
        print(_read_package_resource("pubrun.resources", "default.toml"), end="")
        return

    if mode == "current":
        resolved, provenance = resolve_config_with_provenance()
        _render_config_toml(
            resolved,
            title="pubrun resolved configuration (current, as of now, in this directory)",
            note="Reflects built-in defaults + user/local config + environment variables present "
                 "now. A specific run may differ; use `pubrun show run config` for a past run.",
            provenance=provenance,
            show_all=show_all,
        )
        return

    if mode == "run":
        from pubrun.status import find_run, AmbiguousRunSelectorError
        if show_all:
            _out.info(
                "Past runs persist only resolved configuration values (not per-layer provenance). "
                "Use 'pubrun show config --all' to inspect live layer provenance."
            )
        run_path = None
        if run_selector:
            try:
                info = find_run(run_selector, output_dir)
                run_path = info.run_dir if info else Path(run_selector)
            except AmbiguousRunSelectorError as e:
                _emit_ambiguous_selector(e)
                sys.exit(1)
            except Exception:
                run_path = Path(run_selector)
        else:
            # Most recent run.
            try:
                from pubrun.status import scan_runs
                runs = scan_runs(output_dir, keep_manifest=False)
                if not runs:
                    _print_error(_format_no_runs_error(0, output_dir))
                    sys.exit(1)
                run_path = sorted(runs, key=lambda r: r.started_at_utc or 0, reverse=True)[0].run_dir
            except SystemExit:
                raise
            except Exception as e:
                _print_error(f"Could not locate the most recent run: {e}")
                sys.exit(1)

        run_path_obj = Path(run_path)
        if not run_path_obj.exists():
            _print_error(
                f"Run '{run_path}' does not exist (no recorded config). "
                "Use 'pubrun status' to list available runs."
            )
            sys.exit(1)

        cfg_path = run_path_obj / "config.resolved.json"
        if not cfg_path.exists():
            # Ghost run (never wrote a run dir/config) or otherwise absent.
            _print_error(
                f"Run '{run_path_obj.name}' has no recorded config "
                f"(config.resolved.json not found; likely a ghost run that could not write to disk)."
            )
            sys.exit(1)

        try:
            resolved = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception as e:
            _print_error(f"Failed to read {cfg_path}: {e}")
            sys.exit(1)

        # Distinguish a finalized run from a crashed/unfinalized one (startup snapshot).
        note = None
        manifest_path = Path(run_path) / "manifest.json"
        finalized = False
        if manifest_path.exists():
            try:
                mdata = json.loads(manifest_path.read_text(encoding="utf-8"))
                outcome = mdata.get("status", {}).get("outcome") or mdata.get("run", {}).get("outcome")
                finalized = outcome not in (None, "running")
            except Exception:
                finalized = False
        if not finalized:
            note = "from startup snapshot (run did not finalize; this is the config it started with)."

        _render_config_toml(
            resolved,
            title=f"pubrun resolved configuration for run {Path(run_path).name}",
            note=note,
        )
        return

    _print_error(f"Unknown show-config mode: {mode!r}")
    sys.exit(1)


def _run_report(
    run_dir: str,
    depth: str,
    section: Optional[str] = None,
    utc: bool = False,
    output_dir: Optional[str] = None,
) -> None:
    """Print a human-readable diagnostic report for a recorded run."""
    from pubrun.report.diagnostics import DiagnosticsError, print_report
    try:
        try:
            manifest_path = _get_manifest_path(run_dir, output_dir=output_dir)
            print_report(manifest_path, depth, section, utc=utc)
        except RunInProgressOrCrashedError as e:
            if section == "logs":
                run_dir_path = e.run_dir
                stdout_path = run_dir_path / "stdout.log"
                stderr_path = run_dir_path / "stderr.log"
                if stdout_path.exists():
                    try:
                        with open(stdout_path, "r", encoding="utf-8", errors="replace") as sf:
                            shutil.copyfileobj(sf, sys.stdout, length=65536)
                    except Exception as le:
                        _print_error(f"Failed to read stdout log: {le}")
                if stderr_path.exists():
                    try:
                        with open(stderr_path, "r", encoding="utf-8", errors="replace") as se:
                            shutil.copyfileobj(se, sys.stdout, length=65536)
                    except Exception as le:
                        _print_error(f"Failed to read stderr log: {le}")
                return
            else:
                raise

    except RunInProgressOrCrashedError as e:
        run_dir_path = e.run_dir
        run_info = e.run_info

        status = run_info.status if run_info else "crashed/running"
        print(file=sys.stderr)
        _print_error(f"Run directory '{run_dir_path.name}' is currently {status} and does not contain a manifest.json.")
        print(file=sys.stderr)

        if run_info:
            print("Run Details (from lock file):", file=sys.stderr)
            print(f"  - Run ID:    {run_info.run_id or '-'}", file=sys.stderr)
            print(f"  - Script:    {run_info.script or '-'}", file=sys.stderr)
            if run_info.args:
                print(f"  - Arguments: {run_info.args}", file=sys.stderr)

            started_str = "-"
            if run_info.started_at_utc:
                try:
                    dt = datetime.fromtimestamp(run_info.started_at_utc)
                    started_date_str = dt.strftime("%Y-%m-%d %H:%M:%S")

                    elapsed = time.time() - run_info.started_at_utc
                    days = int(elapsed // 86400)
                    rem = elapsed % 86400
                    hours = int(rem // 3600)
                    rem = rem % 3600
                    minutes = int(rem // 60)
                    seconds = int(rem % 60)

                    duration_str = f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
                    started_str = f"{started_date_str} ({duration_str} {status})"
                except Exception:
                    started_str = str(run_info.started_at_utc)
            print(f"  - Started:   {started_str}", file=sys.stderr)
            if run_info.pid:
                print(f"  - PID:       {run_info.pid}", file=sys.stderr)
            if run_info.hostname:
                print(f"  - Host:      {run_info.hostname}", file=sys.stderr)
            cwd_str = run_info.cwd if run_info.cwd else "-"
            print(f"  - CWD:       {cwd_str}", file=sys.stderr)
            print("", file=sys.stderr)

            use_color = _out.use_color(sys.stderr)
            bold = "\033[1m" if use_color else ""
            red = "\033[91m" if use_color else ""
            yellow = "\033[93m" if use_color else ""
            rst = "\033[0m" if use_color else ""

            if status == "running":
                print(f"Status: {bold}{yellow}STILL RUNNING{rst}\n", file=sys.stderr)
            else:
                print(f"Status: {bold}{red}CRASHED{rst}\n", file=sys.stderr)
                from pubrun.status import (
                    can_safely_auto_close_crashed_run,
                    close_out_crashed_run,
                )
                if can_safely_auto_close_crashed_run(run_dir_path, run_info.lock_data):
                    close_out_crashed_run(run_dir_path, run_info.lock_data)

        # Tail error logs (last 10 lines in O(1) memory)
        log_file = None
        stderr_path = run_dir_path / "stderr.log"
        stdout_path = run_dir_path / "stdout.log"
        try:
            if stderr_path.exists() and stderr_path.stat().st_size > 0:
                log_file = stderr_path
            elif stdout_path.exists() and stdout_path.stat().st_size > 0:
                log_file = stdout_path
        except OSError:
            log_file = None

        if log_file:
            print(f"Last 10 lines of {log_file.name}:", file=sys.stderr)
            try:
                with open(log_file, "r", encoding="utf-8", errors="replace") as lf:
                    tail_lines = list(deque(lf, maxlen=10))
                for line in tail_lines:
                    sys.stderr.write(line)
                if tail_lines and not tail_lines[-1].endswith("\n"):
                    sys.stderr.write("\n")
            except Exception as le:
                print(f"  (Failed to read log file: {le})", file=sys.stderr)
            print("", file=sys.stderr)

        # Suggest the most recent non-crashed (completed/failed) run without parsing every manifest
        runs_dir = _resolve_output_base_dir(output_dir)

        candidate_dirs: List[Tuple[Path, float]] = []
        if runs_dir.exists() and runs_dir.is_dir():
            try:
                with os.scandir(runs_dir) as it:
                    for entry in it:
                        try:
                            if not entry.name.startswith("pubrun-"):
                                continue
                            if not entry.is_dir(follow_symlinks=False):
                                continue
                            d = Path(entry.path)
                            if (d / "manifest.json").exists():
                                candidate_dirs.append((d, entry.stat(follow_symlinks=False).st_mtime))
                        except OSError:
                            continue
            except OSError:
                pass

        candidate_dirs.sort(key=lambda x: x[1], reverse=True)
        latest_completed: Optional[Path] = None
        for d, _mtime in candidate_dirs:
            try:
                with open(d / "manifest.json", "r", encoding="utf-8") as f:
                    m = json.load(f)
                if isinstance(m, dict) and m.get("status", {}).get("outcome") != "crashed":
                    latest_completed = d
                    break
            except Exception:
                continue

        if latest_completed is not None:
            print("Suggestion: To view the report for the most recent completed run, run:", file=sys.stderr)
            print(f"  pubrun show {latest_completed}", file=sys.stderr)
        else:
            print("No completed runs with a manifest.json were found in the output directory.", file=sys.stderr)
            print("See 'pubrun status' to view all active or crashed runs.", file=sys.stderr)

        sys.exit(1)

    except DiagnosticsError as e:
        _print_error(e.message)
        sys.exit(e.exit_code)

    except Exception as e:
        _print_error(f"Failed to generate diagnostic report: {e}")
        sys.exit(1)


def _run_meta(out_path: str, depth: str) -> None:
    """Generate a standalone environment snapshot for HPC parent-child hydration."""
    try:
        from pubrun.report.meta_snapshot import generate_meta_snapshot
        generate_meta_snapshot(out_path, depth)
    except Exception as e:
        _print_error(f"Failed to generate meta snapshot: {e}")
        sys.exit(1)


def _run_cite(style: str) -> None:
    """Print a formatted academic citation for pubrun.

    This cites the software itself (repository), which is the honest, stable form
    while no peer-reviewed publication exists yet. Once a journal article is
    accepted, update these strings and CITATION.cff to the published
    citation with its DOI.
    """
    style = style.lower()
    try:
        from pubrun import __version__ as _ver_imported
        _ver: Optional[str] = _ver_imported
    except Exception:
        _ver = None
    ver_apa = f" (Version {_ver})" if _ver else ""
    ver_bib = f",\n  version   = {{{_ver}}}" if _ver else ""
    url = "https://github.com/fariello/pubrun"
    title = "pubrun: Low-friction execution provenance for Python research"
    # Zenodo concept DOI (all versions; always resolves to the latest archived release).
    # Keep this in sync with CITATION.cff / README / docs (a consistency test guards drift).
    doi = "10.5281/zenodo.20801582"
    doi_url = f"https://doi.org/{doi}"
    if style == "apa":
        print(f"Fariello, G. (2026). {title}{ver_apa} [Computer software]. {url}. {doi_url}")
    elif style == "mla":
        print(f"Fariello, Gabriele. \"{title}.\" 2026. Computer software. {url}. doi:{doi}.")
    elif style == "chicago":
        print(f"Fariello, Gabriele. 2026. \"{title}.\" Computer software. {url}. https://doi.org/{doi}.")
    elif style == "bibtex":
        print(
            "@software{fariello_pubrun_2026,\n"
            "  author    = {Gabriele Fariello},\n"
            f"  title     = {{{title}}},\n"
            "  year      = {2026},\n"
            f"  doi       = {{{doi}}},\n"
            f"  url       = {{{url}}}{ver_bib}\n"
            "}"
        )
    else:
        _print_error(f"Unknown citation style '{style}'. Supported styles: apa, mla, chicago, bibtex.")
        sys.exit(1)


# --- self-check / inspect: environment & capture-completeness diagnostics -----------
# The findings logic lives in pubrun.report.checks, which is imported ONLY here (the CLI),
# never by `import pubrun` / the run path, so it cannot affect a user's host script.

def _fmt_finding(f: dict, use_color: bool) -> str:
    # Map a finding severity to a canonical prefix ([WARN ]/[INFO ]). Color follows the
    # central level->color table; suppressed when use_color is False (NO_COLOR/non-TTY).
    sev = f.get("severity", "info")
    level = "warn" if sev == "warn" else "info"
    label, color = _out._LEVELS[level]
    marker = f"\033[{color}m[{label}]\033[0m" if use_color else f"[{label}]"
    return f"{marker} {f.get('message', '')}"


def _emit_findings(findings: list, *, show_suggestions: bool, as_json: bool, header: str) -> None:
    """Print findings honoring NO_COLOR, terse-by-default, and --json. Never raises."""
    if as_json:
        print(json.dumps({"findings": findings}, indent=2))
        return
    use_color = _out.use_color(sys.stdout)
    warns = [f for f in findings if f.get("severity") == "warn"]
    if not findings:
        print(f"{header}: no concerns found.")
        return
    if not show_suggestions:
        # Terse default: one summary line + a single nudge to expand.
        from pubrun.report.checks import summarize
        print(f"{header}: {summarize(findings)}")
        print("Run with --show-suggestions for per-item detail and how to capture more "
              "(with performance trade-offs).")
        return
    print(f"{header}:")
    for f in findings:
        print("  " + _fmt_finding(f, use_color))
        sugg = f.get("suggestion")
        if sugg:
            print(f"      -> {sugg}")


def _run_self_check(show_suggestions: bool, as_json: bool, strict: bool, quiet: bool = False) -> None:
    """Check the CURRENT machine for performance/config pitfalls + install health.

    Default: itemized — one line per check (with its OK/WARN/INFO outcome) plus a total-time
    footer, so it is transparent WHAT was checked and how each did. ``--quiet`` restores the
    old one-line verdict; ``--show-suggestions`` adds remediation detail; ``--json`` emits the
    full structured result (checks + findings). ``--strict`` still exits non-zero on any WARN.
    """
    try:
        from pubrun.report.checks import live_checks
        t0 = time.perf_counter()
        checks, findings = live_checks()
        elapsed = time.perf_counter() - t0
    except Exception as e:
        _print_error(f"self-check failed: {e}")
        sys.exit(1)

    if as_json:
        print(json.dumps({"checks": checks, "findings": findings,
                          "elapsed_seconds": round(elapsed, 3)}, indent=2))
    elif quiet:
        # Terse one-liner (the pre-1.4.0 default; kept for scripts/CI).
        _emit_findings(findings, show_suggestions=show_suggestions, as_json=False,
                       header="pubrun self-check")
    else:
        # Itemized: one line per check + total-time footer.
        use_color = _out.use_color(sys.stdout)
        _level_for = {"ok": "ok", "warn": "warn", "info": "info"}
        for c in checks:
            lvl = _level_for.get(c.get("status", "ok"), "info")
            label_txt, color = _out._LEVELS[lvl]
            marker = f"\033[{color}m[{label_txt}]\033[0m" if use_color else f"[{label_txt}]"
            detail = c.get("detail") or ""
            line = f"  {marker} {c.get('label', c.get('name', ''))}"
            if detail and c.get("status") != "ok":
                line += f" — {detail}"
            print(line)
            if show_suggestions and c.get("status") != "ok":
                # Pull the suggestion from the matching finding, if any.
                for f in findings:
                    if f.get("message") == detail and f.get("suggestion"):
                        print(f"      -> {f['suggestion']}")
                        break
        warns = sum(1 for c in checks if c.get("status") == "warn")
        summary = "all clear" if warns == 0 else f"{warns} concern(s)"
        print(f"\npubrun self-check: {len(checks)} checks in {elapsed:.2f}s — {summary}.")
        if warns and not show_suggestions:
            print("Run with --show-suggestions for how to address each concern.")

    if strict and any(f.get("severity") == "warn" for f in findings):
        sys.exit(1)


def _run_inspect(
    run_dir: Optional[str],
    show_suggestions: bool,
    as_json: bool,
    strict: bool,
    filter_str: Optional[str] = None,
    not_filter_str: Optional[str] = None,
    status_filter: Optional[str] = None,
    not_status_filter: Optional[str] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
    preflight: bool = False,
    fail_on: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> None:
    """Assess a completed run's reproducibility evidence and optional offline preflight.

    Hydrates parent ``meta_ref`` context via ``hydrate_manifest_with_report``, delegates
    to the shared reproducibility assessment engine, and renders terse summary, detailed
    category/finding output, or structured JSON preserving top-level ``findings``.
    """
    try:
        manifest_path = _get_manifest_path(
            run_dir or "", filter_str=filter_str, status_filter=status_filter,
            older_than=older_than, exit_code=exit_code, not_filter_str=not_filter_str,
            not_status_filter=not_status_filter, output_dir=output_dir,
        )
    except RunInProgressOrCrashedError as e:
        _print_error(f"Run '{e.run_dir.name}' is still running or crashed (no manifest.json yet).")
        sys.exit(1)
    except FileNotFoundError as e:
        _print_error(str(e))
        sys.exit(1)

    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except Exception as e:
        _print_error(f"Failed to read manifest: {e}")
        sys.exit(1)

    import socket
    try:
        current_hostname = socket.gethostname()
    except Exception:
        current_hostname = None

    from pubrun.report.utils import hydrate_manifest_with_report
    from pubrun.report.checks import should_fail_strict
    from pubrun.report.reproducibility import (
        format_reproducibility_detail,
        format_reproducibility_summary,
    )

    hydrated, _hydration_warnings, hydration_report = hydrate_manifest_with_report(
        manifest_path, manifest
    )
    assessment = _assess_cli_run(
        hydrated,
        manifest_path=manifest_path,
        hydration_report=hydration_report,
        current_hostname=current_hostname,
        preflight=preflight,
    )

    if as_json:
        print(json.dumps(assessment, indent=2))
    else:
        use_color = _out.use_color(sys.stdout)
        findings = assessment.get("findings") or []
        banner = [
            f for f in findings if isinstance(f, dict) and f.get("code") == "different_host"
        ]
        # The different-host banner is always shown once at the top (never duplicated in detail).
        if banner:
            line = _fmt_finding(banner[0], use_color)
            bar = "=" * 60
            print(bar)
            print(line)
            print(bar)

        header = "pubrun inspect --preflight" if preflight else "pubrun inspect"
        print(f"{header}:")
        if show_suggestions:
            detail_assessment = (
                {
                    **assessment,
                    "findings": [
                        f
                        for f in findings
                        if not (isinstance(f, dict) and f.get("code") == "different_host")
                    ],
                }
                if banner
                else assessment
            )
            print(format_reproducibility_detail(detail_assessment, use_color=use_color))
        else:
            print(format_reproducibility_summary(assessment))
            if preflight:
                print("Run with --show-suggestions (-v) for per-check and per-finding detail.")
            else:
                print(
                    "Run with --show-suggestions (-v) for category and finding detail, "
                    "or --preflight to compare against this machine."
                )

    if (strict or fail_on is not None) and should_fail_strict(
        assessment, fail_on=fail_on or "warn"
    ):
        sys.exit(1)


# --- bench: friendly benchmark runner + HPC (Slurm) submit + share guidance ---------

# Community benchmark results are contributed by ATTACHING the redacted JSON file to a
# GitHub Issue Form on the MAIN repo (Phase 1 of benchmark-intake, IPD 20260721-2255-01).
# The old paste-the-JSON-into-the-issue-body path (and its gh/HTTP auto-post) is retired:
# it hit GitHub's ~65 KB issue-body cap and it embedded the file into a request the client
# transmitted. Attaching a file is a deliberate human action in the browser, so the LOCAL
# mitigations (unmistakable naming + `--prepare-submission`) are the real privacy defense.
_BENCH_SUBMIT_URL = (
    "https://github.com/fariello/pubrun/issues/new?template=benchmark-result.yml")


def _find_bench_harness() -> Optional[Path]:
    """Locate the benchmark harness module file.

    Resolves the packaged ``pubrun._bench.harness`` module first so ``pubrun bench``
    works from a wheel installation without a source checkout. Falls back to
    ``benchmarks/harness.py`` inside a verified source checkout or the current
    working directory if the packaged module file is unavailable. Returns the
    resolved ``Path`` or ``None``.
    """
    try:
        import importlib.util as _ilu
        spec = _ilu.find_spec("pubrun._bench.harness")
        if spec is not None and spec.origin is not None and spec.origin != "built-in":
            packaged = Path(spec.origin).resolve()
            if packaged.is_file():
                return packaged
    except Exception:
        pass

    candidates: List[Path] = []
    try:
        from pubrun._bench import find_checkout_root
        checkout_root = find_checkout_root()
        if checkout_root is not None:
            candidates.append(checkout_root / "benchmarks" / "harness.py")
    except Exception:
        pass
    candidates.append(Path.cwd() / "benchmarks" / "harness.py")
    for c in candidates:
        try:
            if c.is_file():
                return c.resolve()
        except Exception:
            continue
    return None


def _is_packaged_bench_harness(harness: Path) -> bool:
    """Return True when *harness* is the packaged ``pubrun._bench.harness`` module."""
    if harness.parent.name == "_bench" and harness.parent.parent.name == "pubrun":
        return True
    try:
        import importlib.util as _ilu
        spec = _ilu.find_spec("pubrun._bench.harness")
        if spec is not None and spec.origin is not None and spec.origin != "built-in":
            return harness.resolve() == Path(spec.origin).resolve()
    except Exception:
        pass
    return False


def _find_bench_submit_script(script_name: str) -> Optional[Path]:
    """Locate a high-performance computing (HPC) benchmark submission script.

    Checks the packaged ``pubrun._bench.scripts`` directory first, falling back
    to ``<checkout_root>/benchmarks/<script_name>`` when running inside a
    verified source checkout. Returns the script ``Path`` or ``None``.
    """
    try:
        from pubrun._bench import get_submit_script_path
        packaged = get_submit_script_path(script_name)
        if packaged.is_file():
            return packaged
    except Exception:
        pass

    try:
        from pubrun._bench import find_checkout_root
        checkout_root = find_checkout_root()
        if checkout_root is not None:
            checkout_script = checkout_root / "benchmarks" / script_name
            if checkout_script.is_file():
                return checkout_script
    except Exception:
        pass
    return None


def _slurm_available() -> bool:
    import shutil as _sh
    return bool(os.environ.get("SLURM_JOB_ID") or _sh.which("sbatch"))


def _on_compute_node() -> bool:
    """Best-effort: are we already inside a Slurm allocation (a compute node)?"""
    return bool(os.environ.get("SLURM_JOB_ID"))


# --- HPC scheduler abstraction (Slurm/PBS/LSF/SGE) -----------------------------------
#
# Detection is best-effort, cheap, and side-effect-free: env vars + `shutil.which` only.
# No scheduler is QUERIED at detection time (querying, e.g. `sinfo`, happens only inside a
# submit script AFTER the user confirms), and no network call is made. Submission always
# uses an argv list, never shell=True; forwarded values are charset-validated. Nothing here
# runs on the `import pubrun` path — it is reached only via `pubrun bench`.

def _pbs_markers() -> bool:
    """PBS/Torque/OpenPBS markers (distinct from SGE, which also uses `qsub`)."""
    import shutil as _sh
    return bool(os.environ.get("PBS_JOBID") or os.environ.get("PBS_ENVIRONMENT")
                or os.environ.get("PBS_O_HOST") or _sh.which("pbsnodes"))


def _sge_markers() -> bool:
    """SGE / Grid Engine markers (distinct from PBS, which also uses `qsub`)."""
    import shutil as _sh
    return bool(os.environ.get("SGE_ROOT") or os.environ.get("SGE_O_HOST")
                or os.environ.get("PE_HOSTFILE") or _sh.which("qhost"))


def _detect_schedulers():
    """Return a list of detected scheduler descriptors, in precedence order
    (Slurm > PBS > LSF > SGE). Each descriptor is a dict:
        {name, submit_bin, submit_script, on_compute_node: bool}
    Cheap + side-effect-free (env + which); never queries a scheduler or the network.
    """
    import shutil as _sh
    found = []
    # Slurm (first, for back-compat). Reuses the existing helpers verbatim.
    if _slurm_available():
        found.append({"name": "slurm", "submit_bin": "sbatch",
                      "submit_script": "submit_bench.sh",
                      "on_compute_node": _on_compute_node()})
    # PBS/Torque and SGE both use `qsub`; disambiguate by markers.
    has_qsub = bool(_sh.which("qsub"))
    pbs = _pbs_markers()
    sge = _sge_markers()
    if (has_qsub and pbs) or os.environ.get("PBS_JOBID"):
        found.append({"name": "pbs", "submit_bin": "qsub",
                      "submit_script": "submit_bench_pbs.sh",
                      "on_compute_node": bool(os.environ.get("PBS_JOBID"))})
    # LSF.
    if _sh.which("bsub") or os.environ.get("LSB_JOBID"):
        found.append({"name": "lsf", "submit_bin": "bsub",
                      "submit_script": "submit_bench_lsf.sh",
                      "on_compute_node": bool(os.environ.get("LSB_JOBID"))})
    if (has_qsub and sge) or os.environ.get("JOB_ID"):
        found.append({"name": "sge", "submit_bin": "qsub",
                      "submit_script": "submit_bench_sge.sh",
                      "on_compute_node": bool(os.environ.get("PE_HOSTFILE") or os.environ.get("JOB_ID"))})
    return found


def _qsub_ambiguous() -> bool:
    """True when `qsub` is present but neither PBS nor SGE markers disambiguate it."""
    import shutil as _sh
    return bool(_sh.which("qsub")) and not _pbs_markers() and not _sge_markers()


_DEFAULT_BENCH_REPO = "fariello/pubrun"

# A safe charset for an OWNER/NAME GitHub repo slug (blocks shell metacharacters / injection).
_GH_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _share_check(redacted_path) -> Tuple[bool, List[str]]:
    """Run the packaged structural share-safety validator on a redacted result file.

    Returns ``(passed, reasons)`` by delegating directly to
    ``pubrun._bench.share_safety.check_share_safe_text`` so the local command-line
    interface (CLI) and server-side intake workflow enforce the same rules. Never
    echoes a potential leak: reasons name fields rather than values.
    """
    from pubrun._bench.share_safety import check_share_safe_text

    try:
        text = Path(redacted_path).read_text(encoding="utf-8")
    except OSError as e:
        return (False, [f"could not read {redacted_path}: {e}"])
    return check_share_safe_text(text)


def _print_safe_file_block(unredacted_path, redacted_path) -> None:
    """Print the unmistakable end-of-run block: which file is PRIVATE, which is SAFE to
    submit, the share-check verdict, and where to submit (attach the SAFE file). This is the
    primary user-facing privacy signal for the attach flow (IPD 20260721-2255-01)."""
    passed, reasons = _share_check(redacted_path)
    verdict = "PASSED" if passed else "FAILED"
    print("", file=sys.stderr)
    print("=" * 68, file=sys.stderr)
    print("  Benchmark result written. To contribute it:", file=sys.stderr)
    print("", file=sys.stderr)
    if unredacted_path is not None:
        print(f"  PRIVATE, DO NOT SHARE:  {unredacted_path}", file=sys.stderr)
    print(f"  SAFE TO SUBMIT:         {redacted_path}", file=sys.stderr)
    print(f"  Share check:            {verdict}", file=sys.stderr)
    print("", file=sys.stderr)
    if passed:
        print("  Submit (attach the SAFE file, do NOT paste it):", file=sys.stderr)
        print(f"    {_BENCH_SUBMIT_URL}", file=sys.stderr)
        print("", file=sys.stderr)
        print(f'  Tip: `pubrun bench --submit-file "{redacted_path}" --prepare-submission`', file=sys.stderr)
        print("  copies ONLY the safe file into a clean pubrun-share/ folder, so the", file=sys.stderr)
        print("  folder you browse to attach contains only the file that is safe to share.", file=sys.stderr)
    else:
        print("  The share check FAILED, so this file is NOT safe to submit as-is:", file=sys.stderr)
        for r in reasons:
            print(f"    - {r}", file=sys.stderr)
        print("  Do not attach it; please open an issue for help.", file=sys.stderr)
    print("=" * 68, file=sys.stderr)


def _prepare_submission(redacted_path, dest_dir=None) -> Optional[Path]:
    """Copy ONLY the checked redacted file into a clean `pubrun-share/` directory, so the
    folder the contributor browses to attach contains only the file that is safe to share.

    This is the PRIMARY file-pick mitigation for the attach flow: the unredacted sibling is
    never copied here, so a drag-and-drop from this folder cannot pick the wrong file. stdlib
    only. Returns the destination path on success, or None (after printing an error) on
    failure or a failed share check."""
    src = Path(redacted_path)
    if not src.is_file():
        _print_error(f"--prepare-submission: no such file: {redacted_path}")
        return None
    passed, reasons = _share_check(src)
    if not passed:
        _print_error(
            "Refusing to prepare a submission folder: the share check FAILED.\n"
            + "\n".join(f"  - {r}" for r in reasons)
            + "\nThis file does not look safe to publish; do not share it.")
        return None
    import shutil as _sh
    dest = Path(dest_dir) if dest_dir else (src.parent / "pubrun-share")
    try:
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / src.name
        _sh.copy2(str(src), str(target))
    except OSError as e:
        _print_error(f"--prepare-submission: could not copy into {dest}: {e}")
        return None
    print("", file=sys.stderr)
    print(f"Prepared a clean submission folder containing ONLY the safe file:", file=sys.stderr)
    print(f"  {target}", file=sys.stderr)
    print("Attach that file (from that folder) at:", file=sys.stderr)
    print(f"  {_BENCH_SUBMIT_URL}", file=sys.stderr)
    return target


# --- GitHub contribution (gist-and-link, inline fallback) via `gh` (IPD 20260722-1930-01) ---
#
# A script cannot reproduce the browser drag-drop "attachment" (GitHub's create-issue API has no
# file parameter), so the automated transport is: publish the redacted file as an UNLISTED gist
# and open an issue linking its raw .json URL; if that fails, fall back to embedding the JSON
# inline in the issue body when the COMPLETE body is under the cap; else fall back to the browser
# Issue Form. Every path re-runs the share-safety check first, passes untrusted content only via
# argv lists / stdin (never a shell), and never prints the token or the payload.

# Routing marker placed at the very start of an automated submission's issue body. Not a security
# boundary (a public issue body is attacker-controlled); it only lets the intake workflow route.
_BENCH_SUBMISSION_MARKER = "<!-- pubrun-benchmark-submission:v1 -->"

# The complete issue body must stay under GitHub's ~65,536-byte cap; use a margin so wrappers fit.
_GH_INLINE_BODY_LIMIT = 65_000

# The only host a validated gist raw-file URL may live on (exact match; never suffix-matched).
_GIST_RAW_HOST = "gist.githubusercontent.com"


class _GhError(Exception):
    """A `gh`/submission failure carrying a payload-free, human-readable reason."""


def _bench_issue_title() -> str:
    """A NON-identifying issue title from OS family, arch, Python version, and mode only.
    Never embeds hostname/username/home path/job id. Whitespace-normalized and capped."""
    import platform as _pf
    osname = (_pf.system() or "?").strip()
    arch = (_pf.machine() or "?").strip()
    py = (_pf.python_version() or "?").strip()
    raw = f"[BENCH]: {osname} {arch}, Python {py}"
    raw = " ".join(raw.split())  # normalize whitespace / strip newlines
    return raw[:120]


def _redacted_json_bytes(path) -> str:
    """Read the redacted file's exact bytes as text (do NOT reparse/reserialize: the file was
    validated as-is, and preserving bytes avoids changing the artifact after the share check)."""
    return Path(path).read_text(encoding="utf-8")


def _json_fence(content: str) -> str:
    """Wrap JSON in a fenced code block, using a backtick run longer than any run inside the
    content so a payload containing ``` cannot break out of the fence."""
    longest = 0
    run = 0
    for ch in content:
        if ch == "`":
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    fence = "`" * max(3, longest + 1)
    return f"{fence}json\n{content}\n{fence}"


def _build_gist_issue_body(path, raw_url: str) -> str:
    """Issue body for the gist route: the marker + a link to the raw gist .json URL."""
    name = Path(path).name
    return (
        f"{_BENCH_SUBMISSION_MARKER}\n\n"
        "## Benchmark result\n\n"
        "Automated submission from `pubrun bench`.\n\n"
        f"- Result: [{name}]({raw_url})\n"
        "- Submission method: `gh-gist-v1`\n"
        "- Share-safety check: passed\n\n"
        "The submitter confirmed this is the redacted result.\n"
    )


def _build_inline_issue_body(path) -> str:
    """Issue body for the inline route: the marker + the redacted JSON in a fenced block."""
    content = _redacted_json_bytes(path).rstrip("\n")
    return (
        f"{_BENCH_SUBMISSION_MARKER}\n\n"
        "## Benchmark result\n\n"
        "Automated submission from `pubrun bench`.\n\n"
        "- Submission method: `gh-inline-v1`\n"
        "- Share-safety check: passed\n\n"
        "The submitter confirmed this is the redacted result.\n\n"
        "<details>\n<summary>Redacted benchmark JSON</summary>\n\n"
        f"{_json_fence(content)}\n\n</details>\n"
    )


def _inline_body_fits(body: str) -> bool:
    """True iff the COMPLETE body is under the cap, measured in UTF-8 bytes (not characters)."""
    return len(body.encode("utf-8")) < _GH_INLINE_BODY_LIMIT


class GhReadiness:
    """Result of the non-blocking `gh` preflight probe."""

    __slots__ = ("installed", "authenticated", "detail")

    def __init__(self, installed: bool, authenticated: bool, detail: str = ""):
        self.installed = installed
        self.authenticated = authenticated
        self.detail = detail

    @property
    def ready(self) -> bool:
        return self.installed and self.authenticated


class SubmissionResult:
    """Outcome of a contribution attempt."""

    __slots__ = ("submitted", "method", "issue_url", "detail")

    def __init__(self, submitted: bool, method: str, issue_url=None, detail: str = ""):
        self.submitted = submitted
        self.method = method  # gist | inline | web-fallback | none
        self.issue_url = issue_url
        self.detail = detail


def _run_gh(args, *, input_text=None, timeout=30) -> str:
    """Run `gh` with an argv list (never shell), prompts disabled. Return stdout (stripped).
    Raise _GhError with a sanitized reason on failure. Never echoes the token or the payload."""
    import subprocess as _sp
    env = dict(os.environ)
    env["GH_PROMPT_DISABLED"] = "1"
    try:
        proc = _sp.run(["gh", *args], input=input_text, text=True,
                       encoding="utf-8", errors="replace",
                       capture_output=True, timeout=timeout, env=env)
    except FileNotFoundError:
        raise _GhError("GitHub CLI (gh) is not installed")
    except Exception as e:
        raise _GhError(f"gh invocation failed: {type(e).__name__}")
    if proc.returncode != 0:
        # Report only a short, generic stderr tail; never the full contributor/tool output.
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        msg = detail[-1][:200] if detail else "gh returned a non-zero exit"
        raise _GhError(msg)
    return (proc.stdout or "").strip()


def _probe_gh() -> GhReadiness:
    """Non-blocking readiness probe: is `gh` installed and authenticated? Never runs
    `gh auth login`/`refresh`, never prints/requests a token, never blocks the benchmark."""
    import shutil as _sh
    if _sh.which("gh") is None:
        return GhReadiness(False, False, "GitHub CLI (gh) is not installed")
    try:
        _run_gh(["auth", "status"], timeout=10)
    except _GhError:
        return GhReadiness(True, False, "GitHub CLI (gh) is not authenticated")
    return GhReadiness(True, True)


def _validate_gist_raw_url(url: str) -> bool:
    """A gist raw URL is acceptable only if scheme https, host EXACTLY gist.githubusercontent.com
    (no suffix match), and path ends with .json."""
    from urllib.parse import urlparse
    try:
        u = urlparse(url)
    except Exception:
        return False
    return (u.scheme == "https" and (u.hostname or "").lower() == _GIST_RAW_HOST
            and (u.path or "").lower().endswith(".json"))


def _create_result_gist(path):
    """Create an UNLISTED gist of the redacted file (omit --public). Return (gist_id, raw_url).
    Validates the raw URL host/shape; raises _GhError on any problem."""
    from urllib.parse import urlparse
    page_url = _run_gh(["gist", "create", str(path),
                        "--desc", "pubrun redacted benchmark result"])
    # `gh gist create` prints the gist page URL (https://gist.github.com/<user>/<hexid>).
    lines = (page_url or "").strip().splitlines()
    try:
        gist_id = urlparse(lines[-1].strip()).path.rstrip("/").split("/")[-1] if lines else ""
    except Exception:
        gist_id = ""
    if not gist_id or not all(c in "0123456789abcdefABCDEF" for c in gist_id):
        raise _GhError("could not parse a gist id from gh output")
    # From here on a gist exists: any failure must roll it back so no orphan leaks.
    try:
        try:
            metadata = json.loads(_run_gh(["api", f"/gists/{gist_id}"]))
        except ValueError:
            raise _GhError("gist metadata was not valid JSON")
        files = metadata.get("files", {}) if isinstance(metadata, dict) else {}
        if not isinstance(files, dict) or len(files) != 1:
            raise _GhError("unexpected gist file count")
        entry = next(iter(files.values()))
        raw_url = entry.get("raw_url", "") if isinstance(entry, dict) else ""
        if not isinstance(raw_url, str) or not _validate_gist_raw_url(raw_url):
            raise _GhError("gist raw URL failed host/shape validation")
    except _GhError:
        _delete_gist_best_effort(gist_id)
        raise
    except Exception as e:
        _delete_gist_best_effort(gist_id)
        raise _GhError(f"gist metadata inspection failed: {type(e).__name__}")
    return (gist_id, raw_url)


def _delete_gist_best_effort(gist_id: str) -> bool:
    """Delete a gist, swallowing errors. Return True iff deletion appears to have succeeded."""
    try:
        _run_gh(["gist", "delete", gist_id, "--yes"], timeout=20)
        return True
    except _GhError:
        return False


def _create_benchmark_issue(title: str, body: str, repo: str) -> str:
    """Create the issue via `gh issue create`, body through stdin (never argv). NO label args
    (external callers cannot set labels; the intake workflow applies them). Return the issue URL."""
    out = _run_gh(["issue", "create", "--repo", repo, "--title", title, "--body-file", "-"],
                  input_text=body, timeout=60)
    url = out.strip().splitlines()[-1] if out.strip() else ""
    return url or "created"


def _submit_benchmark_result(path, repo: str) -> SubmissionResult:
    """Consent already obtained by the caller. Re-share-check, then gist->inline->web-fallback.
    Never raises out; returns a SubmissionResult describing the outcome honestly."""
    if not _GH_REPO_RE.match(repo or ""):
        return SubmissionResult(False, "none", detail=f"invalid repo {repo!r}")
    passed, reasons = _share_check(path)
    if not passed:
        return SubmissionResult(False, "none",
                                detail="share-safety check failed: " + "; ".join(reasons))
    readiness = _probe_gh()
    if not readiness.ready:
        return SubmissionResult(False, "web-fallback", detail=readiness.detail)

    title = _bench_issue_title()
    # (a) gist route, with immediate orphan rollback if issue creation fails.
    gist_id = None
    try:
        gist_id, raw_url = _create_result_gist(path)
        body = _build_gist_issue_body(path, raw_url)
        issue_url = _create_benchmark_issue(title, body, repo)
        return SubmissionResult(True, "gist", issue_url)
    except _GhError as e:
        if gist_id:
            # The issue was not confirmed created; roll back the gist we just made.
            _delete_gist_best_effort(gist_id)
        gist_detail = str(e)

    # (b) inline route, only if the complete body fits.
    body = _build_inline_issue_body(path)
    if not _inline_body_fits(body):
        return SubmissionResult(False, "web-fallback",
                                detail=f"gist failed ({gist_detail}); inline body too large")
    try:
        issue_url = _create_benchmark_issue(title, body, repo)
        return SubmissionResult(True, "inline", issue_url)
    except _GhError as e:
        return SubmissionResult(False, "web-fallback",
                                detail=f"gist failed ({gist_detail}); inline failed ({e})")


def _print_contribute_fallback(readiness, path) -> None:
    """Print browser/install/auth guidance appropriate to the detected `gh` state. Never claims
    something was published."""
    print("", file=sys.stderr)
    if readiness is not None and not readiness.installed:
        print("Automatic GitHub submission is unavailable: GitHub CLI (gh) is not installed.",
              file=sys.stderr)
        print("  Install it (https://cli.github.com/), then: gh auth login", file=sys.stderr)
    elif readiness is not None and not readiness.authenticated:
        print("Automatic GitHub submission is unavailable: gh is not authenticated.",
              file=sys.stderr)
        print("  Authenticate with: gh auth login", file=sys.stderr)
    print("You can finish the submission later with:", file=sys.stderr)
    print(f'  pubrun bench --submit-file "{path}"', file=sys.stderr)
    print("Or attach the SAFE file in your browser at:", file=sys.stderr)
    print(f"  {_BENCH_SUBMIT_URL}", file=sys.stderr)


def _contribute(path, repo, interactive, *, consented=False, no_submit=False) -> None:
    """Offer (or, with consent, perform) a GitHub contribution of the redacted file. Prompt is
    shown ONLY on an interactive TTY; Enter defaults to YES (maintainer decision 2026-07-22).
    Never transmits without a yes; never prompts on a non-TTY (no accidental publish)."""
    if no_submit:
        return
    do_submit = consented
    if not do_submit:
        if not interactive:
            # No TTY: do not hang and do not publish. Point at how to submit later.
            print(f'\nTo contribute later: pubrun bench --submit-file "{path}"', file=sys.stderr)
            return
        try:
            resp = input(
                "Publish the share-checked redacted benchmark result to GitHub? [Y/n] "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            resp = "n"
        do_submit = resp in ("", "y", "yes")  # Enter = YES
    if not do_submit:
        print(f'\nNot submitting. To contribute later: pubrun bench --submit-file "{path}"',
              file=sys.stderr)
        return
    result = _submit_benchmark_result(path, repo)
    if result.submitted and result.method == "gist":
        print(f"\nSubmitted via GitHub CLI and an unlisted gist:\n  {result.issue_url}",
              file=sys.stderr)
    elif result.submitted and result.method == "inline":
        print(f"\nGist upload was unavailable; submitted the result inline:\n  {result.issue_url}",
              file=sys.stderr)
    else:
        # web-fallback / none: explain honestly and show how to finish.
        if result.detail:
            print(f"\nAutomatic submission did not complete ({result.detail}).", file=sys.stderr)
        _print_contribute_fallback(_probe_gh(), path)


# --- Slurm submit-and-wait (IPD 20260722-1930-01, Slurm-only this slice) ------------------
#
# Submit the benchmark JOB to Slurm from a login node, then keep THIS (login-node) process
# alive polling for completion, so the interactive share-check + GitHub contribution can run
# from the login node (which has the TTY and network the compute node lacks). Best-effort:
# any interruption/timeout/tool-absence falls back to "finish later with --submit-file"; the
# result always lands on the shared filesystem, so no data is lost.

_SLURM_DEFAULT_WAIT_S = 30 * 60  # 30 minutes; override with --wait-timeout (0 = wait forever)


def _slurm_job_state(job_id: str):
    """Best-effort terminal-state probe for a Slurm job. Returns one of:
      "RUNNING"   - still queued/running (per squeue), or state undeterminable but job seen
      "COMPLETED" - finished successfully (per sacct)
      "FAILED"    - finished unsuccessfully (per sacct: FAILED/CANCELLED/TIMEOUT/...)
      None        - state could not be determined (neither tool usable)
    Tolerates squeue/sacct being absent or sacct accounting being disabled/lagging."""
    import shutil as _sh
    import subprocess as _sp
    # squeue: if the job still appears, it is not finished yet.
    if _sh.which("squeue"):
        try:
            q = _sp.run(["squeue", "-h", "-j", job_id, "-o", "%T"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
            if q.returncode == 0 and q.stdout.strip():
                return "RUNNING"
        except Exception:
            pass
    # sacct: terminal state once the job has left the queue.
    if _sh.which("sacct"):
        try:
            a = _sp.run(["sacct", "-n", "-P", "-j", job_id, "-o", "State"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
            if a.returncode == 0 and a.stdout.strip():
                states = {ln.strip().split()[0] for ln in a.stdout.splitlines() if ln.strip()}
                if any(s.startswith("COMPLETED") for s in states) and not (
                        states - {"COMPLETED"}):
                    return "COMPLETED"
                if any(s.startswith(("FAILED", "CANCELLED", "TIMEOUT", "OUT_OF", "NODE_FAIL",
                                     "BOOT_FAIL", "DEADLINE", "PREEMPTED")) for s in states):
                    return "FAILED"
                # Mixed/pending accounting -> treat as still running.
                return "RUNNING"
        except Exception:
            pass
    return None


def _slurm_wait_and_contribute(job_id, redacted_target, repo, interactive, *,
                               wait_timeout=None, contribute=None, no_submit=False) -> None:
    """Poll the login-node parent for job completion, then run the share-check + contribution.
    Graceful on Ctrl-C / timeout / FAILED / undeterminable state: point at --submit-file."""
    import time as _time
    budget = _SLURM_DEFAULT_WAIT_S if wait_timeout is None else int(wait_timeout)
    started = _time.monotonic()
    poll_s = 10
    print(f"Submitted Slurm job {job_id}. Waiting for it to finish "
          f"({'no timeout' if budget == 0 else f'up to ~{budget // 60} min'}); "
          "press Ctrl-C to stop waiting (the result is still written to the shared "
          "filesystem and you can finish later with --submit-file).", file=sys.stderr)
    redacted_target = Path(redacted_target)
    try:
        while True:
            state = _slurm_job_state(str(job_id))
            if state == "COMPLETED" or (state is None and redacted_target.is_file()):
                break
            if state == "FAILED":
                _print_error(f"Slurm job {job_id} did not complete successfully.")
                _print_slurm_finish_later(redacted_target)
                return
            if budget and (_time.monotonic() - started) > budget:
                print(f"\nStopped waiting after ~{budget // 60} min; the job may still be "
                      "queued or running.", file=sys.stderr)
                _print_slurm_finish_later(redacted_target)
                return
            _time.sleep(poll_s)
    except KeyboardInterrupt:
        print("\nStopped waiting.", file=sys.stderr)
        _print_slurm_finish_later(redacted_target)
        return

    if not redacted_target.is_file():
        _print_error("The job finished but the expected redacted result was not found on the "
                     "shared filesystem.")
        _print_slurm_finish_later(redacted_target)
        return
    _print_safe_file_block(None, str(redacted_target))
    _contribute(str(redacted_target), repo, interactive,
                consented=bool(contribute), no_submit=(no_submit or contribute is False))


def _print_slurm_finish_later(redacted_target) -> None:
    print("When the job has finished, submit the redacted result from this login node with:",
          file=sys.stderr)
    print(f'  pubrun bench --submit-file "{redacted_target}"', file=sys.stderr)


def _run_bench(iterations, passes, quick, local, submit, yes, as_json, unredacted,
               submit_file=None, gh_repo=None, prepare_submission=False,
               no_submit=False, scheduler="auto", rigorous=False,
               no_baseline=False, contribute=None, wait_timeout=None) -> None:
    """Friendly front-end over ``pubrun._bench.harness`` with optional HPC scheduler
    submission (Slurm/PBS/LSF/SGE) and one-command GitHub contribution.

    Works from a wheel installation without a source checkout, writing results by default
    to ``./pubrun-bench-results/`` outside a verified checkout, ``benchmarks/results/``
    inside one, or ``PUBRUN_RESULTS_DIR`` when set. By default only the redacted,
    share-safe file is written; ``--unredacted`` also writes the identifying copy for
    local debugging. After a run pubrun prints the safe-file block and, on an interactive
    terminal, offers to contribute the redacted result to GitHub (gist-and-link, inline
    fallback, browser fallback); ``--contribute``/``--no-contribute`` pre-decide, and
    ``--prepare-submission`` stages a clean folder for a manual browser attach.
    ``--submit``/``--yes`` govern HPC scheduler job submission only (not GitHub
    publication)."""
    repo = gh_repo or _DEFAULT_BENCH_REPO
    if not _GH_REPO_RE.match(repo):
        _print_error(f"Invalid --gh-repo {repo!r}; expected OWNER/NAME.")
        sys.exit(1)
    if iterations is not None and iterations < 1:
        _print_error("--iterations must be >= 1.")
        sys.exit(2)
    if passes is not None and passes < 1:
        _print_error("--passes must be >= 1.")
        sys.exit(2)
    if wait_timeout is not None and wait_timeout < 0:
        _print_error("--wait-timeout must be >= 0.")
        sys.exit(2)
    interactive = sys.stdin.isatty()

    # --- Recovery / HPC / batch path: contribute an EXISTING redacted file, no benchmark run. ---
    if submit_file is not None:
        p = Path(submit_file)
        if not p.is_file():
            _print_error(f"--submit-file: no such file: {submit_file}")
            sys.exit(1)
        if prepare_submission:
            target = _prepare_submission(p)
            sys.exit(0 if target is not None else 1)
        # Share-check + show the safe-file block, then offer/perform the GitHub contribution
        # (unless --no-contribute). Same consent rules as after a fresh run.
        _print_safe_file_block(None, str(p))
        passed, _ = _share_check(p)
        if not passed:
            sys.exit(1)
        _contribute(str(p), repo, interactive,
                    consented=bool(contribute), no_submit=(no_submit or contribute is False))
        sys.exit(0)

    harness = _find_bench_harness()
    if harness is None:
        _print_error(
            "Could not find the benchmark runtime (`pubrun._bench.harness`). "
            "Reinstall pubrun (`pip install --force-reinstall pubrun`) or run from "
            "a verified pubrun source checkout.")
        sys.exit(1)

    from pubrun._bench import default_results_dir, find_checkout_root

    # --- HPC scheduler submission path (Slurm/PBS/LSF/SGE) ---
    # Pick the scheduler: an explicit --scheduler wins; else auto-detect (Slurm first).
    chosen: Optional[dict] = None
    if scheduler and scheduler not in ("auto", "local"):
        _scripts = {"slurm": "submit_bench.sh", "pbs": "submit_bench_pbs.sh",
                    "lsf": "submit_bench_lsf.sh", "sge": "submit_bench_sge.sh"}
        chosen = {"name": scheduler, "submit_script": _scripts.get(scheduler, "submit_bench.sh")}
        # An explicitly named scheduler is treated as "not on a compute node" unless its env
        # says otherwise (the user asked to submit).
        detected = {d["name"]: d for d in _detect_schedulers()}
        chosen["on_compute_node"] = bool(
            detected.get(scheduler, {}).get("on_compute_node", False))
    elif scheduler == "local":
        chosen = None
    else:  # auto
        detected = _detect_schedulers()
        if detected:
            if len(detected) > 1:
                names = ", ".join(d["name"] for d in detected)
                print(f"Multiple schedulers detected ({names}); using '{detected[0]['name']}'. "
                      f"Override with --scheduler.", file=sys.stderr)
            elif _qsub_ambiguous() and detected[0]["name"] in ("pbs", "sge"):
                print("`qsub` is present but PBS-vs-SGE could not be determined from the "
                      "environment. Re-run with --scheduler pbs|sge to choose.", file=sys.stderr)
            chosen = detected[0]
        elif not local and _qsub_ambiguous():
            print("`qsub` is present but PBS-vs-SGE could not be determined from the "
                  "environment; running locally. Re-run with --scheduler pbs|sge to submit.",
                  file=sys.stderr)

    want_submit = (submit or (not local and chosen is not None and not chosen.get("on_compute_node"))) \
        and scheduler != "local"
    if want_submit and chosen is not None:
        submit_script = _find_bench_submit_script(chosen["submit_script"])
        if submit_script is None:
            _print_error(f"{chosen['name']} detected but {chosen['submit_script']} is missing; "
                         f"re-run with --local.")
            sys.exit(1)
        # Build the exact command; pass args as discrete argv (never shell=True) so
        # partition/args cannot inject. The submit script reads PUBRUN_* env vars.
        extra = []
        if quick:
            extra.append("--quick")
        elif rigorous:
            extra.append("--rigorous")
        if no_baseline:
            extra.append("--no-baseline")
        if iterations is not None:
            extra += ["--iterations", str(int(iterations))]
        if passes is not None:
            extra += ["--passes", str(int(passes))]
        cmd = ["bash", str(submit_script)] + extra
        label = chosen["name"].upper() if chosen["name"] != "slurm" else "Slurm"
        is_slurm = chosen["name"] == "slurm"
        print(f"{label} detected. Submission command:\n  {' '.join(cmd)}", file=sys.stderr)
        if not (submit or yes):
            prompt = (f"Run by submitting to the {label} queue? [y/N] " if is_slurm
                      else f"Submit this benchmark job to {label}? [y/N] ")
            try:
                resp = input(prompt).strip().lower()
            except (EOFError, KeyboardInterrupt):
                resp = ""
            if resp not in ("y", "yes"):
                print("Not submitting. Re-run with --submit/--yes to submit, or --local to run here.", file=sys.stderr)
                return
        import subprocess as _sp
        import hashlib as _hashlib
        import platform as _pf
        from datetime import datetime, timezone
        results_dir = default_results_dir()
        results_dir.mkdir(parents=True, exist_ok=True)
        resolved_results_dir = results_dir.resolve()
        checkout_root = find_checkout_root()
        env = dict(os.environ)
        if checkout_root is not None:
            env.setdefault("PUBRUN_REPO", str(checkout_root))
        env["PUBRUN_RESULTS_DIR"] = str(resolved_results_dir)
        if not env.get("PUBRUN_PY"):
            env["PUBRUN_PY"] = sys.executable
        if unredacted:
            env["PUBRUN_UNREDACTED"] = "1"

        # For Slurm submit-and-wait, pass a DETERMINISTIC redacted-out path (on the shared FS)
        # so this login-node process can find and contribute the result after the job finishes.
        redacted_target = None
        if is_slurm:
            _tok = _hashlib.sha256((_pf.node() or "unknown").encode("utf-8", "replace")).hexdigest()[:8]
            _ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            redacted_target = resolved_results_dir / f"pubrun-bench-{_tok}-{_ts}.redacted.json"
            env["PUBRUN_REDACTED_OUT"] = str(redacted_target)
        try:
            proc = _sp.run(cmd, env=env, check=False,
                           capture_output=is_slurm, text=True,
                           encoding="utf-8", errors="replace")  # argv list; no shell
        except Exception as e:
            _print_error(f"Failed to submit: {e}")
            sys.exit(1)
        if not is_slurm:
            if proc.returncode != 0:
                _print_error(f"{label} submission failed (exit {proc.returncode}).")
                sys.exit(proc.returncode if isinstance(proc.returncode, int) and proc.returncode > 0 else 1)
            print(f"Submitted. Results will be written under {results_dir} on the compute node.", file=sys.stderr)
            return
        if proc.returncode != 0:
            _print_error(f"Slurm submission failed: {(proc.stderr or proc.stdout or '').strip()[:200]}")
            sys.exit(1)
        # submit_bench.sh (with --parsable) prints the bare job id as its last stdout line.
        job_id = ""
        for line in reversed((proc.stdout or "").splitlines()):
            tok = line.strip().split(";")[0]  # `--parsable` may emit jobid;cluster
            if tok.isdigit():
                job_id = tok
                break
        if proc.stdout:
            print(proc.stdout.strip(), file=sys.stderr)
        if not job_id:
            print("Could not determine the Slurm job id; not waiting.", file=sys.stderr)
            if redacted_target is not None:
                _print_slurm_finish_later(redacted_target)
            return
        _slurm_wait_and_contribute(job_id, redacted_target, repo, interactive,
                                   wait_timeout=wait_timeout, contribute=contribute,
                                   no_submit=no_submit)
        return

    # --- Local path ---
    import subprocess as _sp
    results_dir = default_results_dir()
    results_dir.mkdir(parents=True, exist_ok=True)
    import platform as _pf
    import hashlib as _hashlib
    from datetime import datetime, timezone
    host = (_pf.node() or "unknown").replace("/", "_")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Redacted-only by default: the shareable *.redacted.json uses a stable NON-identifying
    # hostname-hash token (never the hostname). The identifying *.unredacted.json is written
    # ONLY with --unredacted (local debugging). Never a bare *.json.
    _host_token = _hashlib.sha256((_pf.node() or "unknown").encode("utf-8", "replace")).hexdigest()[:8]
    redacted_target = results_dir / f"pubrun-bench-{_host_token}-{ts}.redacted.json"
    out_path = results_dir / f"{host}-{ts}.unredacted.json" if unredacted else None
    if _is_packaged_bench_harness(harness):
        argv = [sys.executable, "-m", "pubrun._bench.harness", "--redacted-out", str(redacted_target)]
    else:
        argv = [sys.executable, str(harness), "--redacted-out", str(redacted_target)]
    if unredacted:
        argv += ["--out", str(out_path)]
    if quick:
        argv.append("--quick")
    elif rigorous:
        argv.append("--rigorous")
    if no_baseline:
        argv.append("--no-baseline")
    if iterations is not None:
        argv += ["--iterations", str(int(iterations))]
    if passes is not None:
        argv += ["--passes", str(int(passes))]
    print(f"Running benchmarks locally (this may take a few minutes)...", file=sys.stderr)
    rc = _sp.run(argv, check=False).returncode
    if rc != 0:
        _print_error(f"Benchmark harness exited with code {rc}.")
        sys.exit(rc)
    redacted_path = redacted_target
    if as_json:
        print(json.dumps({"redacted": str(redacted_path),
                          "unredacted": str(out_path) if unredacted else None}))
        return

    if no_submit:
        # Suppress the contribution guidance; just point at the file(s).
        print(f"\nRedacted (shareable) result: {redacted_path}", file=sys.stderr)
        if unredacted:
            print(f"Unredacted (PRIVATE, do not share): {out_path}", file=sys.stderr)
        return

    # Print the safe-file block (PRIVATE line only when an unredacted copy exists).
    _print_safe_file_block(str(out_path) if unredacted else None, str(redacted_path))

    # --prepare-submission stages a clean folder holding ONLY the safe file (browser attach).
    if prepare_submission:
        _prepare_submission(redacted_path)
        return

    # Offer / perform the GitHub contribution (interactive TTY prompt defaults to YES; a
    # non-TTY never prompts; --contribute/--no-contribute pre-decide). Never transmits an
    # unredacted file; _submit_benchmark_result re-share-checks first.
    _contribute(str(redacted_path), repo, interactive,
                consented=bool(contribute), no_submit=(contribute is False))


def _run_status(
    run_id: Optional[str],
    output_dir: Optional[str],
    verbose: bool,
    filter_str: Optional[str] = None,
    limit: Optional[int] = None,
    status_filter: Optional[str] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
    not_filter_str: Optional[str] = None,
    not_status_filter: Optional[str] = None,
    as_json: bool = False,
) -> None:
    """List runs or inspect a specific run."""
    from pubrun.status import (
        find_run,
        render_inspect,
        render_short_list,
        render_verbose_list,
        scan_runs,
        filter_runs,
        can_safely_auto_close_crashed_run,
        close_out_crashed_run,
    )

    if run_id:
        # Inspect a specific run (recency index / id-prefix / dir-substring).
        from pubrun.status import AmbiguousRunSelectorError
        idx: Optional[int] = None
        try:
            if as_json:
                all_runs = scan_runs(output_dir, keep_manifest=False)
                run_info = find_run(run_id, output_dir, runs=all_runs)
                if run_info is not None:
                    idx = next((i for i, r in enumerate(all_runs, 1) if r is run_info), None)
            else:
                run_info = find_run(run_id, output_dir)
        except AmbiguousRunSelectorError as e:
            _emit_ambiguous_selector(e)
            sys.exit(1)
        if run_info is None:
            _print_error(f"No run found matching '{run_id}'. Use 'pubrun status' to list available runs.")
            sys.exit(1)
        if run_info.status == "crashed" and can_safely_auto_close_crashed_run(
            run_info.run_dir, run_info.lock_data
        ):
            close_out_crashed_run(run_info.run_dir, run_info.lock_data)
        if as_json:
            print(_dump_strict_json({"run": _serialize_run_info(run_info, index=idx)}, indent=2))
        else:
            print(render_inspect(run_info))
    else:
        # List all runs
        all_runs = scan_runs(output_dir, keep_manifest=False)
        try:
            runs = filter_runs(
                all_runs,
                filter_str=filter_str,
                status_filter=status_filter,
                limit=limit,
                older_than=older_than,
                exit_code=exit_code,
                not_filter_str=not_filter_str,
                not_status_filter=not_status_filter,
            )
        except ValueError as e:
            _print_error(str(e))
            sys.exit(1)

        for r in runs:
            if r.status == "crashed" and can_safely_auto_close_crashed_run(
                r.run_dir, r.lock_data
            ):
                close_out_crashed_run(r.run_dir, r.lock_data)

        if as_json:
            index_map = {id(r): i for i, r in enumerate(all_runs, 1)}
            payload = {
                "total_runs": len(all_runs),
                "matched_runs": len(runs),
                "runs": [_serialize_run_info(r, index=index_map.get(id(r))) for r in runs],
            }
            print(_dump_strict_json(payload, indent=2))
        elif verbose:
            print(render_verbose_list(runs, all_runs=all_runs))
        else:
            print(render_short_list(runs, all_runs=all_runs))


def _run_clean(
    output_dir: Optional[str],
    older_than: Optional[str],
    status: Optional[str],
    yes: bool,
    dry_run: bool,
    filter_str: Optional[str] = None,
    limit: Optional[int] = None,
    exit_code: Optional[int] = None,
    not_filter_str: Optional[str] = None,
    not_status_filter: Optional[str] = None,
    force_remote_locks: bool = False,
) -> None:
    """Interactive or automatic cleanup of old run directories."""
    from pubrun.status import clean_runs

    try:
        clean_runs(
            output_dir=output_dir,
            older_than=older_than,
            status_filter=status,
            yes=yes,
            dry_run=dry_run,
            filter_str=filter_str,
            limit=limit,
            exit_code=exit_code,
            not_filter_str=not_filter_str,
            not_status_filter=not_status_filter,
            force_remote_locks=force_remote_locks,
        )
    except ValueError as e:
        _print_error(str(e))
        sys.exit(1)


def _fallback_iso_ts(run_info: Any) -> str:
    """Return an ISO-8601 UTC fallback timestamp derived from ``run_info.started_at_utc``."""
    started = getattr(run_info, "started_at_utc", None)
    if isinstance(started, (int, float)) and not isinstance(started, bool) and math.isfinite(started):
        try:
            dt = datetime.fromtimestamp(float(started), tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        except (OSError, OverflowError, ValueError):
            pass
    return ""


def _run_combined(
    run_ids: list,
    dir_path: Optional[str],
    output: Optional[str],
    yes: bool,
    force: bool,
    filter_str: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: Optional[int] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
    not_filter_str: Optional[str] = None,
    not_status_filter: Optional[str] = None,
) -> None:
    """Interleave stdout/stderr logs from one or more runs in O(K) memory."""
    from pubrun.status import AmbiguousRunSelectorError, filter_runs, find_run, scan_runs

    TIMESTAMP_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\] (.*)$")

    all_runs = scan_runs(dir_path, keep_manifest=False)
    if not run_ids:
        has_filters = any(v is not None for v in (
            filter_str, status_filter, older_than, exit_code, not_filter_str, not_status_filter
        ))
        run_limit = limit if limit is not None else (None if has_filters else 1)
        try:
            target_runs = filter_runs(
                all_runs,
                filter_str=filter_str,
                status_filter=status_filter,
                limit=run_limit,
                older_than=older_than,
                exit_code=exit_code,
                not_filter_str=not_filter_str,
                not_status_filter=not_status_filter,
            )
        except ValueError as e:
            _print_error(str(e))
            sys.exit(1)
        if not target_runs:
            _print_error(_format_no_runs_error(len(all_runs), dir_path))
            sys.exit(1)
    else:
        target_runs = []
        for rid in run_ids:
            try:
                run_info = find_run(rid, dir_path, runs=all_runs)
            except AmbiguousRunSelectorError as e:
                _emit_ambiguous_selector(e)
                sys.exit(1)
            if not run_info:
                _print_error(f"Run ID '{rid}' not found.")
                sys.exit(1)
            target_runs.append(run_info)

    # Collect existing log files and compute total size safely.
    log_entries: List[Tuple[Any, str, Path]] = []
    total_size = 0
    for r in target_runs:
        for stream in ("stdout", "stderr"):
            p = r.run_dir / f"{stream}.log"
            if p.exists():
                log_entries.append((r, stream, p))
                try:
                    total_size += p.stat().st_size
                except OSError:
                    pass

    if not log_entries:
        _out.info(
            'No stdout.log or stderr.log files found for the selected run(s). '
            'Enable [console].capture_mode = "standard" in .pubrun.toml or use `import pubrun.full` to capture console logs.'
        )
        return

    if total_size > 500 * 1024 * 1024:
        if not force:
            _print_error(f"Combined log size ({total_size / (1024*1024):.1f} MB) exceeds 500 MB limit. Use --force to proceed.")
            sys.exit(1)

    if total_size > 250 * 1024 * 1024:
        if not yes:
            _print_warn(f"Combined log size ({total_size / (1024*1024):.1f} MB) exceeds 250 MB.")
            try:
                response = input("Proceed? [y/N] ").strip().lower()
                if response not in ("y", "yes"):
                    print("Operation cancelled.", file=sys.stderr)
                    sys.exit(0)
            except (KeyboardInterrupt, EOFError):
                print("\nOperation cancelled.", file=sys.stderr)
                sys.exit(0)

    # Check if any log file contains timestamps (first 50 lines per file).
    has_any_timestamps = False
    for _r, _stream, p in log_entries:
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                for _ in range(50):
                    line = f.readline()
                    if not line:
                        break
                    if TIMESTAMP_RE.match(line):
                        has_any_timestamps = True
                        break
        except Exception:
            pass
        if has_any_timestamps:
            break

    def _stream_log_entries(
        fh: Any,
        file_idx: int,
        prefix: str,
        fallback_ts: str,
    ) -> Iterator[Tuple[str, int, int, int, str]]:
        """Yield (sort_ts, phase, file_idx, line_idx, formatted_line) in O(1) steady-state RAM.

        Leading untimestamped lines are buffered only until the file's first timestamped
        line (or EOF, using ``fallback_ts`` from ``run.started_at_utc``), so they stay
        anchored to their own run instead of being hoisted above earlier runs.
        """
        leading_buffer: List[Tuple[int, str]] = []
        seen_first_ts = False
        current_ts = ""
        for line_idx, raw_line in enumerate(fh):
            line_str = raw_line.rstrip("\r\n")
            m = TIMESTAMP_RE.match(line_str)
            if m:
                ts = m.group(1)
                if not seen_first_ts:
                    seen_first_ts = True
                    for lead_idx, lead_line in leading_buffer:
                        yield (ts, 0, file_idx, lead_idx, prefix + lead_line)
                    leading_buffer.clear()
                current_ts = ts
                yield (ts, 1, file_idx, line_idx, prefix + line_str)
            else:
                if not seen_first_ts:
                    leading_buffer.append((line_idx, line_str))
                else:
                    yield (current_ts, 1, file_idx, line_idx, prefix + line_str)
        if leading_buffer:
            for lead_idx, lead_line in leading_buffer:
                yield (fallback_ts, 0, file_idx, lead_idx, prefix + lead_line)

    multiple_runs = len(target_runs) > 1
    try:
        with contextlib.ExitStack() as stack:
            out_file = None
            if output:
                try:
                    out_file = stack.enter_context(open(output, "w", encoding="utf-8"))
                except Exception as e:
                    _print_error(f"Failed to open output file '{output}': {e}")
                    sys.exit(1)

            if not has_any_timestamps:
                print(
                    'Warning: Logs lack timestamps. Falling back to sequential concatenation. '
                    'True interleaving requires capture_mode = "standard".',
                    file=sys.stderr,
                )
                for r, stream, p in log_entries:
                    prefix = f"[{r.run_id}][{stream}] " if multiple_runs else f"[{stream}] "
                    try:
                        with open(p, "r", encoding="utf-8", errors="replace") as f:
                            for line in f:
                                out_line = prefix + line.rstrip("\r\n")
                                if out_file:
                                    out_file.write(out_line + "\n")
                                else:
                                    print(out_line)
                    except OSError as e:
                        print(f"Warning: Failed to read log file {p}: {e}", file=sys.stderr)
            else:
                streams: List[Iterator[Tuple[str, int, int, int, str]]] = []
                for file_idx, (r, stream, p) in enumerate(log_entries):
                    prefix = f"[{r.run_id}][{stream}] " if multiple_runs else f"[{stream}] "
                    try:
                        fh = stack.enter_context(open(p, "r", encoding="utf-8", errors="replace"))
                    except OSError as e:
                        print(f"Warning: Failed to read log file {p}: {e}", file=sys.stderr)
                        continue
                    streams.append(
                        _stream_log_entries(fh, file_idx, prefix, _fallback_iso_ts(r))
                    )
                for _ts, _phase, _fidx, _lidx, formatted in heapq.merge(*streams):
                    if out_file:
                        out_file.write(formatted + "\n")
                    else:
                        print(formatted)

            if out_file:
                _out.ok(f"Combined logs written to {output}", stream=sys.stderr)
    except BrokenPipeError:
        pass


def _show_info() -> None:
    """Print hardware, invocation, and import-mode diagnostics for debugging."""
    from pubrun.capture.hardware import get_hardware
    from pubrun.capture.invocation import get_invocation

    print("==================================================")
    print("          pubrun Hardware Diagnostics           ")
    print("==================================================\n")

    # Import mode diagnostics (P5-U1)
    print("--- [ Import Mode ] ---")
    try:
        from pubrun._bootstrap import get_selected_mode, get_selected_behavior
        mode = get_selected_mode() or "auto"
        behavior = get_selected_behavior() or {
            "auto_start": True,
            "global_hooks": True,
            "patch_subprocesses": True,
            "patch_console": True,
            "signal_hooks": True,
        }
        import_mode_env = os.environ.get("PUBRUN_IMPORT_MODE", "")
        print(f"  Active mode:         {mode}")
        print(f"  auto_start:          {behavior.get('auto_start')}")
        print(f"  global_hooks:        {behavior.get('global_hooks')}")
        print(f"  patch_subprocesses:  {behavior.get('patch_subprocesses')}")
        print(f"  patch_console:       {behavior.get('patch_console')}")
        print(f"  signal_hooks:        {behavior.get('signal_hooks')}")
        if import_mode_env:
            print(f"  env override:        PUBRUN_IMPORT_MODE={import_mode_env}")
    except Exception:
        print("  (unavailable)")
    print()

    print("--- [ Invocation Details ] ---")
    data = {"invocation": get_invocation({}), "hardware": get_hardware({})}
    print(json.dumps(data, indent=2))
    print("\nIf GPU details are missing here, your active Python environment")
    print("may not have `nvidia-smi` on PATH or permission to query GPU devices.")


def _run_tests() -> None:
    """Run the test suite and an end-to-end mock script for validation."""
    print("==================================================")
    print("        pubrun Pipeline Evaluation Mode         ")
    print("==================================================\n")

    failed = False
    if Path("tests").exists() and Path("tox.ini").exists():
        _out.info("Source repository detected. Running PyTest matrix...", stream=sys.stdout)
        try:
            pytest_proc = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"])
            if pytest_proc.returncode != 0:
                _out.fail(f"PyTest exited with code {pytest_proc.returncode}.", stream=sys.stdout)
                failed = True
        except Exception:
            _out.warn("PyTest execution failed.", stream=sys.stdout)
            failed = True

    print()
    _out.info("Executing Native End-to-End Mock Script...", stream=sys.stdout)
    MOCK_SCRIPT = """
import time
import os
import pubrun

print('Starting Mock Training Environment...')

tracker = pubrun.start()
pubrun.annotate('initializing_model', layers=3, opt='adam')
time.sleep(0.6)

with pubrun.phase('epoch_1'):
    print('Epoch 1: loss = 0.95')
    os.system('echo "Evaluating internal shell capture hooks..."')
    time.sleep(0.4)

with pubrun.phase('epoch_2'):
    print('Epoch 2: loss = 0.45')
    time.sleep(0.4)

print('Mock Training Complete.')
"""
    with tempfile.TemporaryDirectory() as td:
        script_path = Path(td) / "mock_training.py"
        script_path.write_text(MOCK_SCRIPT.strip(), encoding="utf-8")

        env = os.environ.copy()
        env["PUBRUN_AUTO_START"] = "true"

        result = subprocess.run(
            [sys.executable, str(script_path)],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=td,
        )

        if result.returncode != 0:
            _out.fail(f"Mock Evaluation Failed. Exit Code: {result.returncode}")
            sys.exit(1)

        _out.ok("Mock script executed without crashing.")

        runs_dir = Path(td) / "runs"
        run_folders = [p for p in runs_dir.iterdir() if p.is_dir()] if runs_dir.is_dir() else []
        manifest_p = run_folders[0] / "manifest.json" if run_folders else None
        if manifest_p is None or not manifest_p.exists():
            _out.fail("Mock script produced no run manifest.")
            sys.exit(1)

        try:
            manifest_data = json.loads(manifest_p.read_text(encoding="utf-8"))
            if not isinstance(manifest_data, dict):
                raise ValueError("manifest is not a JSON object")
            rcs = manifest_data.get("subprocesses", [])
            _out.ok(f"Subprocess spy captured {len(rcs)} shell commands.")
        except Exception as e:
            _out.fail(f"Mock run manifest is invalid: {e}")
            sys.exit(1)

    if failed:
        sys.exit(1)
    _out.ok("Validation complete.")


def _can_open_browser(no_browser: bool) -> bool:
    """Return True only when an interactive local graphical session can safely open a browser."""
    if no_browser:
        return False
    try:
        if not sys.stdout.isatty():
            return False
    except Exception:
        return False
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    in_ssh = any(os.environ.get(k) for k in ("SSH_CLIENT", "SSH_TTY", "SSH_CONNECTION"))
    if in_ssh and not has_display:
        return False
    if sys.platform.startswith("linux") and not has_display:
        return False
    return True


def _run_bug_report(no_browser: bool = False) -> None:
    """Guide the user to report a bug or request a feature on GitHub."""
    import webbrowser
    import platform
    import time
    from pubrun import __version__

    print("==================================================")
    print("        pubrun Bug & Feature Reporting           ")
    print("==================================================\n")
    print("Please copy the following environment diagnostics for your report:")
    print("--------------------------------------------------")
    print(f"pubrun Version : {__version__}")
    print(f"Python Version : {platform.python_version()}")
    print(f"Platform       : {platform.platform()}")
    print(f"Machine        : {platform.machine()}")
    print(f"Processor      : {platform.processor() or 'unknown'}")
    print(f"System Time    : {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("--------------------------------------------------\n")

    url = "https://github.com/fariello/pubrun/issues/new"
    if not _can_open_browser(no_browser):
        print(f"Open the GitHub issue tracker at:\n  {url}\n")
        return

    print(f"Opening GitHub issue tracker at:\n  {url}\n")
    try:
        opened = webbrowser.open(url)
        if not opened:
            print("Could not launch web browser automatically.")
            print(f"Please navigate to the URL manually: {url}")
    except Exception as e:
        print(f"Failed to open web browser: {e}")
        print(f"Please navigate to the URL manually: {url}")


def _add_run_filter_args(parser: argparse.ArgumentParser, include_limit: bool = True) -> None:
    """Helper to add standard run filter arguments to a subparser."""
    from pubrun.status import VALID_STATUSES

    status_choices_text = ", ".join(VALID_STATUSES)
    has_f = any("-f" in getattr(action, "option_strings", []) for action in parser._actions)
    if has_f:
        parser.add_argument("--filter", type=str, default=None, metavar="QUERY", help="Filter runs by script name, arguments, or run ID (supports regex or plain string).")
    else:
        parser.add_argument("-f", "--filter", type=str, default=None, metavar="QUERY", help="Filter runs by script name, arguments, or run ID (supports regex or plain string).")
    parser.add_argument("-F", "--not-filter", type=str, default=None, metavar="QUERY", help="Exclude runs matching script name, arguments, or run ID.")
    parser.add_argument("-s", "--status", type=str, default=None, metavar="STATUS", help=f"Comma-separated status filter. Valid statuses: {status_choices_text}.")
    parser.add_argument("-S", "--not-status", type=str, default=None, metavar="STATUS", help=f"Comma-separated status exclusion filter. Valid statuses: {status_choices_text}.")
    parser.add_argument("--older-than", type=str, default=None, metavar="AGE", help="Only consider runs older than AGE (e.g. '7d', '24h', '30' for 30 days).")
    parser.add_argument("--exit-code", type=int, default=None, metavar="CODE", help="Only consider runs with this exit code.")
    if include_limit:
        parser.add_argument("-n", "--limit", type=int, default=None, metavar="LIMIT", help="Limit the number of runs to consider.")


def _preprocess_argv(argv: List[str], subcommands: Set[str]) -> Tuple[List[str], bool]:
    """Return (rewritten argv, no_color_present) without mutating the input."""
    argv = list(argv)

    # Handle global --no-color flag regardless of position
    # But do not strip it if it is part of the command run by 'pubrun run'
    run_idx = -1
    for idx, arg in enumerate(argv[1:], start=1):
        if arg in subcommands:
            if arg == "run":
                run_idx = idx
            break

    no_color_present = False
    if run_idx != -1:
        if "--no-color" in argv[:run_idx]:
            no_color_present = True
            argv = [arg for i, arg in enumerate(argv) if i >= run_idx or arg != "--no-color"]
    else:
        if "--no-color" in argv:
            no_color_present = True
            argv = [arg for arg in argv if arg != "--no-color"]

    # Support placing run ID / prefix / path before the subcommand
    # (e.g. `pubrun 16528343 cpu` -> `pubrun cpu 16528343`)
    if (len(argv) > 2 and argv[1] not in subcommands and argv[1] != "help"
            and not argv[1].startswith("-")):
        for idx in range(2, len(argv)):
            if argv[idx] in subcommands:
                cmd = argv.pop(idx)
                argv.insert(1, cmd)
                break

    # Translate 'help' and subcommand translations
    if len(argv) > 1:
        if argv[1] == "help":
            if len(argv) > 2 and argv[2] in subcommands:
                argv = [argv[0], argv[2], "--help"]
            else:
                argv = [argv[0], "--help"]
        elif argv[1] in subcommands and len(argv) > 2 and argv[2] == "help":
            argv = [argv[0], argv[1], "--help"]

    return argv, no_color_present


def _apply_global_flags(args: argparse.Namespace, no_color_present: bool) -> None:
    """Apply global CLI side effects (NO_COLOR env and UTC display mode) after parsing."""
    if no_color_present:
        setattr(args, "no_color", True)
    if getattr(args, "no_color", False):
        os.environ["NO_COLOR"] = "1"

    # Timestamp display timezone: local by default, UTC when --utc is given
    # (status/show). Timestamps are always stored as UTC epochs. (IPD EC-17.)
    if getattr(args, "utc", False):
        from pubrun.status import set_display_utc
        set_display_utc(True)


def main(argv: Optional[List[str]] = None) -> None:
    """CLI entrypoint for the ``pubrun`` command.

    Args:
        argv: Full argument vector including the program name (defaults to ``sys.argv``).
    """
    argv = list(sys.argv if argv is None else argv)
    raw_stem = Path(argv[0].replace("\\", "/")).stem.lower() if argv and argv[0] else "pubrun"
    prog_name = "pbr" if raw_stem == "pbr" else "pubrun"

    # Primary commands (excluding aliases) for clean error messages.
    _PRIMARY_COMMANDS: list = []
    _argv_for_errors: List[str] = []

    class _SubcommandAwareArgumentParser(argparse.ArgumentParser):
        def error(self, message: str) -> NoReturn:
            subcommand = None
            subparsers_actions = [
                act for act in self._actions
                if isinstance(act, argparse._SubParsersAction)
            ]
            if subparsers_actions:
                for arg in _argv_for_errors[1:]:
                    if arg in subparsers_actions[0].choices:
                        subcommand = arg
                        break

            if subcommand:
                subparser = subparsers_actions[0].choices[subcommand]
                subparser.print_usage(sys.stderr)
                sys.stderr.write(f"{self.prog} {subcommand}: error: {message}\n")
                sys.exit(2)

            # UX-01: Rewrite "invalid choice" errors to show only primary
            # commands (not aliases) for a cleaner novice experience.
            if "invalid choice" in message and _PRIMARY_COMMANDS:
                bad = re.search(r"'([^']+)'", message)
                bad_cmd = bad.group(1) if bad else "?"
                clean_msg = (
                    f"argument <command>: unknown command '{bad_cmd}' "
                    f"(choose from: {', '.join(_PRIMARY_COMMANDS)})"
                )
                self.print_usage(sys.stderr)
                sys.stderr.write(f"{self.prog}: error: {clean_msg}\n")
                sys.exit(2)

            super().error(message)

    parser = _SubcommandAwareArgumentParser(
        prog=prog_name,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            f"{prog_name}: Zero-dependency execution telemetry and publication engine.\n\n"
            "Command groups:\n"
            "  Setup & run:    init, run, meta, self-check\n"
            "  Inspect runs:   status, show, diff, inspect, rerun, combined\n"
            "  Resources:      res (resources), cpu, mem\n"
            "  Publish & UI:   methods, cite, ui (tui/gui), bench\n"
            "  Maintenance:    clean, report-bug"
        ),
        epilog=(
            "Quick start:\n"
            f"  {prog_name} init                         Create .pubrun.toml in this project\n"
            f"  {prog_name} status                       List recorded runs and their status\n"
            f"  {prog_name} show                         Inspect the most recent run\n\n"
            f"Use '{prog_name} <command> --help' for detailed information on a specific command."
        ),
    )
    from pubrun import __commit__ as _commit
    _commit_line = f" (commit {_commit})" if _commit else ""
    parser.add_argument(
        "--version",
        action="version",
        version=(
            f"pubrun {__version__}{_commit_line}\n"
            "Based on the original pubrun by Gabriele Fariello "
            "(https://github.com/fariello/pubrun).\n"
            "Licensed under Apache-2.0; see the NOTICE file for the required attribution."
        ),
    )
    parser.add_argument("--no-color", action="store_true", help="Suppress ANSI color output globally.")

    subparsers = parser.add_subparsers(dest="command", title="Available core commands", metavar="<command>")

    _RUN_HELP = (
        "Run selector: recency index (#1, #2 passed as 1, 2), run ID/prefix, "
        "or directory path. Defaults to the most recent matching run."
    )
    _DIR_HELP = "Override the output directory to scan (default: configured output_dir, PUBRUN_OUTPUT_DIR, or ./runs)."

    # ---------------- Init Subparser (UX-08) ----------------
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize pubrun in the current project (create .pubrun.toml).",
        description="Create a .pubrun.toml configuration file and display getting-started guidance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="After init, add 'import pubrun' to your script to begin tracking."
    )
    init_parser.add_argument("dest", nargs="?", default=".pubrun.toml",
                             help="Destination path (default: .pubrun.toml).")

    # ---------------- Bug Report Subparser ----------------
    report_bug_parser = subparsers.add_parser(
        "report-bug",
        aliases=["feedback"],
        help="File a bug report or request a feature.",
        description="Print environment diagnostics and open the GitHub issue tracker (skipped automatically on non-TTY or headless sessions).",
        epilog=f"Examples:\n  {prog_name} report-bug\n  {prog_name} report-bug --no-browser",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    report_bug_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Print diagnostics and the GitHub issue URL without opening a web browser.",
    )

    # ---------------- Cite Subparser ----------------
    cite_parser = subparsers.add_parser(
        "cite",
        help="Generate a formatted academic citation for pubrun.",
        description="Generate a formatted academic citation for pubrun.",
        epilog=f"Examples:\n  {prog_name} cite\n  {prog_name} cite --style bibtex",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    cite_parser.add_argument("--style", type=str, choices=["apa", "mla", "chicago", "bibtex"], default="apa", help="Citation format (default: apa).")

    # ---------------- Self-check Subparser ----------------
    selfcheck_parser = subparsers.add_parser(
        "self-check",
        help="Check THIS machine for pubrun performance/config pitfalls + install health.",
        description="Report-only checks of the current environment: filesystem types "
                    "(flagging network filesystems like NFS/Lustre), free RAM, load, pubrun "
                    "import origin, and install health (config validity, output-dir "
                    "writability, git availability, Python version). Never modifies anything.",
        epilog=f"Examples:\n  {prog_name} self-check\n  {prog_name} self-check --show-suggestions\n  {prog_name} self-check --strict",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    selfcheck_parser.add_argument("--show-suggestions", "-v", action="store_true", help="Show per-item detail and how to address each concern.")
    selfcheck_parser.add_argument("--json", action="store_true", dest="as_json", help="Emit findings as JSON (always full detail).")
    selfcheck_parser.add_argument("--strict", action="store_true", help="Exit non-zero if any warning fired (useful in CI / HPC job pre-checks).")
    selfcheck_parser.add_argument("--quiet", "-q", action="store_true", help="Print only a one-line verdict instead of the itemized per-check output.")

    # ---------------- Inspect Subparser ----------------
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Assess a completed run's reproducibility evidence and optional offline preflight.",
        description=(
            "Report-only, post-hoc reproducibility assessment of a completed run's manifest. "
            "If the run references a parent meta.json snapshot (created by `pubrun meta` and "
            "linked via PUBRUN_META_REF or [core].meta_ref), inspect hydrates shared hardware, "
            "host, git, and package metadata from that parent snapshot before evaluating seven "
            "structured evidence categories. Pass --preflight to run a read-only offline "
            "comparison against the current machine. Prints a prominent banner when the "
            "inspecting host differs from where the run executed (e.g. HPC head node vs compute node)."
        ),
        epilog=f"Examples:\n  {prog_name} inspect\n  {prog_name} inspect 1 --show-suggestions\n"
               f"  {prog_name} inspect runs/pubrun-XYZ --preflight\n"
               f"  {prog_name} inspect runs/pubrun-XYZ --preflight --fail-on mismatch\n"
               f"  {prog_name} inspect -f train.py --json",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    inspect_parser.add_argument("run_dir", type=str, nargs="?", metavar="RUN", help=_RUN_HELP)
    inspect_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help=_DIR_HELP)
    inspect_parser.add_argument("--show-suggestions", "-v", action="store_true", help="Show per-category status, preflight checks, and per-finding detail with next steps.")
    inspect_parser.add_argument("--preflight", action="store_true", help="Run read-only offline comparison of supported recorded requirements against the current environment.")
    inspect_parser.add_argument("--json", action="store_true", dest="as_json", help="Emit the full structured reproducibility assessment as JSON (preserving top-level 'findings').")
    inspect_parser.add_argument("--strict", action="store_true", help="Exit 1 when the strict threshold triggers (defaults to 'warn' unless --fail-on is given).")
    inspect_parser.add_argument(
        "--fail-on",
        choices=["warn", "mismatch", "unknown"],
        default=None,
        help=(
            "Strict exit threshold (implies --strict, works with or without --preflight): "
            "'warn' fails on any warning finding; "
            "'mismatch' fails on material warnings or preflight mismatches; "
            "'unknown' also fails on unknown/not-checked preflight checks or uncertain categories."
        ),
    )
    _add_run_filter_args(inspect_parser, include_limit=False)

    # ---------------- Bench Subparser ----------------
    bench_parser = subparsers.add_parser(
        "bench",
        help="Run the pubrun overhead benchmark suite (auto-detects Slurm on HPC).",
        description="Run the pubrun overhead benchmark suite directly from a wheel "
                    "installation or a source checkout. Runs locally by default; on a "
                    "high-performance computing (HPC) login node with a supported "
                    "scheduler it offers to submit the job to a compute node (never "
                    "submits without confirmation). Writes results by default to "
                    "./pubrun-bench-results/ outside a source checkout, "
                    "benchmarks/results/ inside one, or PUBRUN_RESULTS_DIR when set. "
                    "Writes only a redacted, share-safe file by default (`--unredacted` "
                    "also keeps the identifying copy), runs a share-safety check, and "
                    "offers to contribute the redacted result to GitHub (via `gh` "
                    "gist/inline, or browser Issue Form fallback).",
        epilog=f"Examples:\n  {prog_name} bench --quick\n  {prog_name} bench --local --passes 3\n"
               f"  {prog_name} bench --submit-file runs.redacted.json --prepare-submission\n"
               f"  {prog_name} bench --submit-file runs.redacted.json",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    bench_speed = bench_parser.add_mutually_exclusive_group()
    bench_speed.add_argument("--quick", action="store_true", help="Fast smoke run (baseline + 2 passes x 15 iterations).")
    bench_speed.add_argument("--full", action="store_true", help="Standard run (baseline + 3 passes x 30 iterations). This is the default; the flag is for clarity.")
    bench_speed.add_argument("--rigorous", action="store_true", help="Tight-CI run (baseline + 5 passes x 50 iterations); can take many minutes.")
    bench_parser.add_argument("--no-baseline", action="store_true", help="Skip the initial uncaptured baseline pass (the pubrun-absent reference sweep).")
    bench_parser.add_argument("--iterations", type=int, default=None, help="Override iterations per scenario (>= 1; takes precedence over --quick/--full).")
    bench_parser.add_argument("--passes", type=int, default=None, help="Override the number of measured scenario sweeps (>= 1; default depends on the tier: quick=2, full=3, rigorous=5).")
    bench_parser.add_argument("--unredacted", action="store_true",
                              help="ALSO write the identifying, un-redacted result (embeds hostname/paths; for local "
                                   "debugging only, do NOT share). By default only the redacted, share-safe file is written.")
    bench_parser.add_argument("--json", action="store_true", dest="as_json", help="Emit the redacted/unredacted paths as JSON.")

    hpc_group = bench_parser.add_argument_group("HPC scheduler options")
    bench_exec = hpc_group.add_mutually_exclusive_group()
    bench_exec.add_argument("--local", action="store_true", help="Run here even if an HPC scheduler is detected.")
    bench_exec.add_argument("--submit", action="store_true", help="Submit the benchmark JOB to the detected HPC scheduler without prompting (no effect off HPC).")
    hpc_group.add_argument("--scheduler", choices=("auto", "slurm", "pbs", "lsf", "sge", "local"),
                           default="auto", help="HPC scheduler to submit to (default: auto-detect; 'local' forces a local run).")
    hpc_group.add_argument("-y", "--yes", action="store_true", help="Assume yes to the HPC scheduler submit prompt.")
    hpc_group.add_argument("--wait-timeout", type=int, default=None, metavar="SECONDS",
                           help="For Slurm submit-and-wait: how long the login-node process waits for the "
                                "queued job before pointing you at --submit-file (>= 0; default ~1800s; 0 = wait forever).")

    gh_group = bench_parser.add_argument_group("GitHub contribution options")
    contrib = gh_group.add_mutually_exclusive_group()
    contrib.add_argument("--contribute", dest="contribute", action="store_true", default=None,
                         help="Publish the share-checked redacted result to GitHub after the run (no prompt). "
                              "Uses `gh`: an unlisted gist linked from an issue, or inline if small.")
    contrib.add_argument("--no-contribute", dest="contribute", action="store_false",
                         help="Never offer or attempt GitHub publication.")
    gh_group.add_argument("--prepare-submission", action="store_true",
                          help="Instead of publishing, copy ONLY the redacted (safe) file into a clean "
                               "pubrun-share/ folder for a manual browser attach.")
    gh_group.add_argument("--submit-file", metavar="FILE", default=None,
                          help="Contribute an existing redacted result file (share-check + publish/prepare), "
                               "without running a benchmark.")
    gh_group.add_argument("--no-submit", action="store_true", help="Skip the end-of-run contribution offer entirely.")
    gh_group.add_argument("--gh-repo", metavar="OWNER/NAME", default=None,
                          help=f"Target GitHub repo for the contribution (default {_DEFAULT_BENCH_REPO}).")

    # ---------------- Clean Subparser ----------------
    clean_parser = subparsers.add_parser(
        "clean",
        help="Interactively delete old run directories.",
        description="Interactively delete old run directories. By default, lists candidates and prompts for confirmation.",
        epilog=f"Examples:\n  {prog_name} clean\n  {prog_name} clean --older-than 7d --yes\n  {prog_name} clean --status completed,ghost",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    clean_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help=_DIR_HELP)
    clean_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt (delete all matching runs).")
    clean_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting.")
    clean_parser.add_argument(
        "--force-remote-locks",
        action="store_true",
        help="Allow deleting runs locked by a different host (never bypasses active local PID, unreadable lock, or symlink confinement checks).",
    )
    _add_run_filter_args(clean_parser)

    # ---------------- Combined Subparser ----------------
    combined_parser = subparsers.add_parser(
        "combined",
        help="Interleave stdout/stderr logs from one or more runs.",
        description="Interleave stdout/stderr logs from one or more runs.",
        epilog=f"Examples:\n  {prog_name} combined\n  {prog_name} combined 1 2 --output combined.log",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    combined_parser.add_argument("run_ids", type=str, nargs="*", metavar="RUN", help="Run selectors (recency index #1/#2 as 1/2, run ID/prefix, or directory path) to combine. Defaults to the latest matching run if omitted.")
    combined_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help=_DIR_HELP)
    combined_parser.add_argument("--output", type=str, default=None, metavar="FILE", help="Write combined logs to this file instead of stdout.")
    combined_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt for files > 250 MB.")
    # NOTE: as of 1.4.0, `-f` means `--filter` on `combined` (consistent with every other
    # command); the force flag is `--force` (long-only). This is an intentional breaking
    # change from prior releases where `combined -f` meant force. See CHANGELOG.
    combined_parser.add_argument("--force", action="store_true", help="Force execution for files > 500 MB.")
    _add_run_filter_args(combined_parser)

    # ---------------- CPU Subparser ----------------
    cpu_parser = subparsers.add_parser(
        "cpu",
        help="Display CPU utilization chart over the run lifecycle.",
        description="Display CPU utilization chart over the run lifecycle.",
        epilog=f"Examples:\n  {prog_name} cpu\n  {prog_name} cpu 1 --utc",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    cpu_parser.add_argument("run_dir", type=str, nargs="?", metavar="RUN", help=_RUN_HELP)
    cpu_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help=_DIR_HELP)
    cpu_parser.add_argument("--average", action="store_true", help="Plot average/mean values instead of the default maximum values.")
    cpu_parser.add_argument("-l", "--last", type=str, default=None, help="Only show the last X minutes, hours, or seconds of data (e.g. '10m', '2h', '30s').")
    cpu_parser.add_argument("-w", "--width", type=int, default=None, help="Override chart width in columns.")
    cpu_parser.add_argument("--utc", action="store_true", help="Display chart axis timestamps in UTC instead of local time.")
    _add_run_filter_args(cpu_parser, include_limit=False)

    # ---------------- Diff Subparser ----------------
    diff_parser = subparsers.add_parser(
        "diff",
        help="Compare two execution traces and highlight differences.",
        description="Compare two execution traces and highlight differences.",
        epilog=(
            "Examples:\n"
            f"  {prog_name} diff\n"
            f"  {prog_name} diff 2 1 --deep --same\n"
            f"  {prog_name} diff runs/pubrun-A runs/pubrun-B --json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    diff_parser.add_argument("run_dirs", type=str, nargs="*", metavar="RUN", help="Up to two run selectors (recency index #1/#2 as 1/2, run ID/prefix, or directory path). Omit to diff the last two runs; pass one to diff it against the most recent other run.")
    diff_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help=_DIR_HELP)
    diff_parser.add_argument(
        "--export",
        type=str,
        nargs="?",
        const=True,
        help="Export cleaned manifests to .pubrun_diff_A_<run>_clean.<fmt> and .pubrun_diff_B_<run>_clean.<fmt> in the current directory ('txt' or 'json'; default from [diff].export_format, which defaults to 'txt').",
    )
    diff_parser.add_argument("--json", action="store_true", dest="as_json", help="Emit the structured diff report as strict JSON to stdout (cannot be combined with --export).")
    diff_parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output.")

    wrap_group = diff_parser.add_mutually_exclusive_group()
    wrap_group.add_argument("--wrap", action="store_true", default=None, help="Wrap long strings across multiple lines instead of truncating.")
    wrap_group.add_argument("--no-wrap", action="store_false", dest="wrap", default=None, help="Force ellipsis truncation for long values.")

    diff_parser.add_argument("--max-length", type=int, default=None, help="Max characters per value before truncation.")
    diff_parser.add_argument("--table", action="store_true", help="Render a compact aligned table instead of the default git-style +/-/~ lines.")

    diff_depth = diff_parser.add_mutually_exclusive_group()
    diff_depth.add_argument("--basic", action="store_const", dest="depth", const="basic", help="Structural changes only, filtering most metrics.")
    diff_depth.add_argument("--standard", action="store_const", dest="depth", const="standard", help="Include standard telemetry, ignoring jitter metrics (default).")
    diff_depth.add_argument("--deep", action="store_const", dest="depth", const="deep", help="Unfiltered comparison of all captured data.")
    diff_parser.set_defaults(depth="standard")

    diff_same = diff_parser.add_mutually_exclusive_group()
    diff_same.add_argument("--same", action="store_true", default=None, help="Show keys that are identical between both runs.")
    diff_same.add_argument("--no-same", action="store_false", dest="same", default=None, help="Hide keys that are identical between both runs.")
    _add_run_filter_args(diff_parser, include_limit=False)

    # ---------------- Memory Subparser ----------------
    mem_parser = subparsers.add_parser(
        "mem",
        help="Display memory utilization chart over the run lifecycle.",
        description="Display memory utilization chart over the run lifecycle.",
        epilog=f"Examples:\n  {prog_name} mem\n  {prog_name} mem 1 --utc",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mem_parser.add_argument("run_dir", type=str, nargs="?", metavar="RUN", help=_RUN_HELP)
    mem_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help=_DIR_HELP)
    mem_parser.add_argument("--average", action="store_true", help="Plot average/mean values instead of the default maximum values.")
    mem_parser.add_argument("-l", "--last", type=str, default=None, help="Only show the last X minutes, hours, or seconds of data (e.g. '10m', '2h', '30s').")
    mem_parser.add_argument("-w", "--width", type=int, default=None, help="Override chart width in columns.")
    mem_parser.add_argument("--utc", action="store_true", help="Display chart axis timestamps in UTC instead of local time.")
    _add_run_filter_args(mem_parser, include_limit=False)

    # ---------------- Meta Subparser ----------------
    meta_parser = subparsers.add_parser(
        "meta",
        help="Generate a standalone meta.json environment snapshot.",
        description=(
            "Capture shared node and environment metadata (hardware, host, git, Python, "
            "and packages) once into a standalone meta.json file. In HPC array or batch "
            "jobs, point child runs at this file via PUBRUN_META_REF or [core].meta_ref "
            "so `pubrun show`, `pubrun inspect`, `pubrun methods`, and `pubrun diff` "
            "hydrate (merge) the shared parent context into each child manifest without "
            "re-capturing slow node details on every task."
        ),
        epilog=f"Examples:\n  {prog_name} meta\n  {prog_name} meta --out custom_meta.json --deep",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    meta_parser.add_argument("--out", type=str, default="", help="Output file path. Defaults to ./runs/meta.json.")

    depth_group_2 = meta_parser.add_mutually_exclusive_group()
    depth_group_2.add_argument("--basic", action="store_const", dest="depth", const="basic", help="Minimal footprint (fastest).")
    depth_group_2.add_argument("--standard", action="store_const", dest="depth", const="standard", help="Standard environment factors.")
    depth_group_2.add_argument("--deep", action="store_const", dest="depth", const="deep", help="Full hardware, git, and pip dependency snapshot (default).")
    meta_parser.set_defaults(depth="deep")

    # ---------------- Methods Subparser ----------------
    methods_parser = subparsers.add_parser(
        "methods",
        help="Generate publication-ready 'Computational Methods' paragraphs.",
        description="Generate publication-ready 'Computational Methods' paragraphs (prints pure Markdown or LaTeX to stdout; status banners go to stderr).",
        epilog=(
            "Examples:\n"
            f"  {prog_name} methods\n"
            f"  {prog_name} methods 1 --format latex\n"
            f"  {prog_name} methods --all --filter train.py --status completed --limit 10"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    methods_parser.add_argument("run_dir", type=str, nargs="?", metavar="RUN", help=_RUN_HELP)
    methods_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help=_DIR_HELP)
    methods_parser.add_argument("--format", type=str, choices=["markdown", "latex"], default=None, help="Output format: markdown or latex (default: [methods].format in config, or markdown).")
    methods_parser.add_argument("--all", action="store_true", help="Aggregate ALL matching runs into one methods paragraph (with a variance note where they differ), instead of the single most-recent run. Combine with --filter (-f), --not-filter (-F), --status (-s), --not-status (-S), or --limit (-n) to bound the set.")
    _add_run_filter_args(methods_parser, include_limit=True)

    # ---------------- Hidden Report Subparser ----------------
    report_parser = subparsers.add_parser(
        "report",
        help=argparse.SUPPRESS,
        description="Analyze and display diagnostic telemetry from a specific run.",
        epilog=f"Examples:\n  {prog_name} report\n  {prog_name} report runs/pubrun-XYZ\n  {prog_name} report env",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    report_parser.add_argument("run_dir", type=str, nargs="?", metavar="RUN", help=_RUN_HELP)
    report_parser.add_argument("section", type=str, nargs="?", help="Optional section to view (e.g. 'logs', 'env', 'packages').")
    report_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help=_DIR_HELP)

    depth_group_report = report_parser.add_mutually_exclusive_group()
    depth_group_report.add_argument("--basic", action="store_const", dest="depth", const="basic", help="Timing and outcome only.")
    depth_group_report.add_argument("--standard", action="store_const", dest="depth", const="standard", help="Hardware, Git, Python, and dependency summary (default).")
    depth_group_report.add_argument("--deep", action="store_const", dest="depth", const="deep", help="Full environment variables and complete package list.")
    report_parser.set_defaults(depth="standard")
    report_parser.add_argument("--utc", action="store_true", help="Display timestamps in UTC instead of local time.")
    _add_run_filter_args(report_parser)

    # ---------------- Rerun Subparser ----------------
    rerun_parser = subparsers.add_parser(
        "rerun",
        help="Print the shell command needed to replicate a run (with optional --preflight).",
        description="Print the shell command needed to replicate a run. By default, prints only "
                    "the command to stdout (safe for piping such as `pubrun rerun | bash`). "
                    "Pass --preflight to run a read-only offline comparison against the current "
                    "environment (diagnostics go to stderr; never executes the command).",
        epilog=f"Examples:\n  {prog_name} rerun\n  {prog_name} rerun 1\n"
               f"  {prog_name} rerun runs/pubrun-XYZ --preflight\n"
               f"  {prog_name} rerun runs/pubrun-XYZ --preflight --strict\n"
               f"  {prog_name} rerun runs/pubrun-XYZ --preflight --fail-on mismatch --json",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    rerun_parser.add_argument("run_dir", type=str, nargs="?", metavar="RUN", help=_RUN_HELP)
    rerun_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help=_DIR_HELP)
    rerun_parser.add_argument("--preflight", action="store_true", help="Run read-only offline preflight comparison before printing the rerun command (diagnostics go to stderr).")
    rerun_parser.add_argument("--strict", action="store_true", help="Requires --preflight. Exit 1 and suppress stdout when the strict threshold triggers (default: 'warn').")
    rerun_parser.add_argument(
        "--fail-on",
        choices=["warn", "mismatch", "unknown"],
        default=None,
        help=(
            "Requires --preflight; implies --strict. Strict exit threshold: "
            "'warn' fails on any warning finding; "
            "'mismatch' fails on material warnings or preflight mismatches; "
            "'unknown' also fails on unknown/not-checked preflight checks."
        ),
    )
    rerun_parser.add_argument("--json", action="store_true", dest="as_json", help="Requires --preflight. Emit JSON with rerun_command, executable_as_printed, and assessment to stdout.")
    _add_run_filter_args(rerun_parser, include_limit=False)

    # ---------------- Resources Subparser ----------------
    res_parser = subparsers.add_parser(
        "res",
        aliases=["resources"],
        help="Display memory and CPU utilization charts over the run lifecycle.",
        description="Display memory and CPU utilization charts over the run lifecycle.",
        epilog=f"Examples:\n  {prog_name} res\n  {prog_name} res 1 --utc",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    res_parser.add_argument("run_dir", type=str, nargs="?", metavar="RUN", help=_RUN_HELP)
    res_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help=_DIR_HELP)
    res_parser.add_argument("--average", action="store_true", help="Plot average/mean values instead of the default maximum values.")
    res_parser.add_argument("-l", "--last", type=str, default=None, help="Only show the last X minutes, hours, or seconds of data (e.g. '10m', '2h', '30s').")
    res_parser.add_argument("-w", "--width", type=int, default=None, help="Override chart width in columns.")
    res_parser.add_argument("--utc", action="store_true", help="Display chart axis timestamps in UTC instead of local time.")
    _add_run_filter_args(res_parser, include_limit=False)

    # ---------------- Run Subparser ----------------
    run_parser = subparsers.add_parser(
        "run",
        help="Run a command with a specific pubrun import mode.",
        description=(
            "Spawn a child process with PUBRUN_IMPORT_MODE and PUBRUN_RUN_MODE_OVERRIDE set.\n"
            "Prerequisite: the target Python script must still contain `import pubrun` (or\n"
            "`import pubrun.<mode>`). `pubrun run` overrides the import mode at launch time\n"
            "without editing source code; it does not inject pubrun into untracked scripts.\n\n"
            "Import modes:\n"
            "  auto       Start tracking on import with standard hooks (default).\n"
            "  full       Like auto, plus force stdout/stderr console capture on.\n"
            "  noauto     Load API only; start tracking when pubrun.start() is called.\n"
            "  nopatch    Start tracking without subprocess or console patching (keeps signals).\n"
            "  noconsole  Start tracking without wrapping stdout/stderr.\n"
            "  minimal    Load API only, with no auto-start and no process-global hooks."
        ),
        epilog=f"Examples:\n  {prog_name} run --mode minimal -- python train.py --epochs 10\n  {prog_name} run --mode full -- python evaluate.py",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    run_parser.add_argument("--mode", type=str, choices=["auto", "noauto", "nopatch", "noconsole", "minimal", "full"], default="auto", help="Import mode for the child process (default: auto).")
    run_parser.add_argument("command_args", nargs=argparse.REMAINDER, metavar="-- COMMAND", help="Command to execute (use -- to separate pubrun flags from the target command).")

    # ---------------- Show Subparser ----------------
    show_parser = subparsers.add_parser(
        "show",
        help="Analyze and display diagnostic telemetry from a specific run.",
        description="Analyze and display diagnostic telemetry from a specific run.",
        epilog=f"Examples:\n  {prog_name} show\n  {prog_name} show 1\n  {prog_name} show runs/pubrun-XYZ env\n  {prog_name} show env\n  {prog_name} show config\n  {prog_name} show run config 1\n  {prog_name} show default config",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    show_parser.add_argument("run_dir", type=str, nargs="?", metavar="RUN", help="Run selector (recency index #1/#2 as 1/2, run ID/prefix, or directory path; defaults to latest). Also the keyword 'config' (current resolved config), or 'run'/'default' in the `show <run|default> config` forms.")
    show_parser.add_argument("section", type=str, nargs="?", help="Optional section to view ('logs', 'env', 'packages'), or 'config' in the `show run config` / `show default config` forms.")
    show_parser.add_argument("config_extra", type=str, nargs="?", metavar="RUN", help="Optional run selector for `pubrun show run config <RUN>` (recency index #1/#2 as 1/2, run ID/prefix, or directory path). Defaults to the most recent run.")
    show_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help=_DIR_HELP)

    depth_group_show = show_parser.add_mutually_exclusive_group()
    depth_group_show.add_argument("--basic", action="store_const", dest="depth", const="basic", help="Timing and outcome only.")
    depth_group_show.add_argument("--standard", action="store_const", dest="depth", const="standard", help="Hardware, Git, Python, and dependency summary (default).")
    depth_group_show.add_argument("--deep", action="store_const", dest="depth", const="deep", help="Full environment variables and complete package list.")
    show_parser.add_argument("--utc", action="store_true", help="Display timestamps in UTC instead of local time.")
    show_parser.add_argument("--all", action="store_true", help="With `show config`: annotate every key with its source config layer (default: only overridden keys).")
    show_parser.set_defaults(depth="standard")
    _add_run_filter_args(show_parser)

    # ---------------- Status Subparser ----------------
    status_parser = subparsers.add_parser(
        "status",
        help="List runs and their status, or inspect a specific run.",
        description="List runs and their status, or inspect a specific run.",
        epilog=f"Examples:\n  {prog_name} status\n  {prog_name} status --status failed,crashed\n  {prog_name} status --limit 5\n  {prog_name} status -f train.py --json",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    status_parser.add_argument("run_id", type=str, nargs="?", metavar="RUN", help="Run selector (recency index #1/#2 as 1/2, run ID/prefix, or directory path) to inspect in detail. If omitted, lists matching runs.")
    status_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help=_DIR_HELP)
    status_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed information for each run in the listing.")
    status_parser.add_argument("--utc", action="store_true", help="Display timestamps in UTC instead of local time.")
    status_parser.add_argument("--json", action="store_true", dest="as_json", help="Emit run status output as strict JSON to stdout.")
    _add_run_filter_args(status_parser)

    # ---------------- UI Subparser ----------------
    ui_parser = subparsers.add_parser(
        "ui",
        aliases=["tui", "gui"],
        help="Launch the interactive pubrun dashboard.",
        description="Launch the interactive pubrun dashboard.",
        epilog=f"Examples:\n  {prog_name} ui\n  {prog_name} ui --dir /path/to/runs",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ui_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help=_DIR_HELP)

    # Hide the `report` alias from the help listing, then sort the remaining commands
    # alphabetically so `pubrun -h` presents them in a predictable order. This affects
    # only the DISPLAY list; dispatch is unaffected (hidden aliases still work).
    subparsers._choices_actions = sorted(
        [a for a in subparsers._choices_actions if a.dest != "report"],
        key=lambda a: a.dest,
    )

    # ---------------- Diagnostic Flags ----------------
    parser.add_argument("--create-config", type=str, nargs="?", const="PROMPT", metavar="DEST", help="Create an annotated `.pubrun.toml` configuration file.")
    # Deprecated: hidden from --help (SUPPRESS) but still functional; emits a stderr
    # deprecation notice at runtime pointing to `pubrun show default config`.
    parser.add_argument("--show-config", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--info", action="store_true", help="Display import mode, invocation, and hardware/capture diagnostics. (Use `--version` for version and `pubrun show config` for resolved configuration.)")
    parser.add_argument("--run-tests", action="store_true", help="Run the built-in test suite and a mock end-to-end script.")

    # UX-01: Build the primary commands list (excluding aliases) for clean errors.
    _known_aliases = {"tui", "gui", "report", "resources", "feedback"}
    _PRIMARY_COMMANDS.extend(
        name for name in subparsers.choices if name not in _known_aliases
    )

    # Every registered subcommand and alias, derived from the parser so a newly added
    # command can never be missing from the argv preprocessing below.
    subcommands = set(subparsers.choices.keys())

    argv, no_color_present = _preprocess_argv(argv, subcommands)

    # Easter egg
    if len(argv) >= 2 and prog_name == "pbr" and argv[1] == "me":
        print("ASAP")
        sys.exit(0)

    _argv_for_errors[:] = argv
    args = parser.parse_args(argv[1:])
    _apply_global_flags(args, no_color_present)

    # `pubrun show config` family (positional grammar), intercepted BEFORE run resolution so
    # the keyword `config` is not mistaken for a run selector. Forms:
    #   show config                -> current resolved config (run_dir == "config", no section)
    #   show config default        -> shipped defaults      (run_dir == "config", section == "default")
    #   show config <id>           -> a past run's config   (run_dir == "config", section == <id>)
    #   show default config        -> shipped defaults      (run_dir == "default", section == "config")
    #   show run config [<id>]     -> a past run's config   (run_dir == "run",     section == "config")
    # Precedence note: these keyword forms win over a run whose id literally starts with
    # config/run/default; such a run must be selected by full id or path.
    if args.command in {"show", "report"}:
        _rd = getattr(args, "run_dir", None)
        _sec = getattr(args, "section", None)
        _extra = getattr(args, "config_extra", None)  # optional run id after `show run config`
        _out_dir = getattr(args, "dir", None)
        if _rd == "config":
            if _sec is None:
                _run_show_config("current", show_all=getattr(args, "all", False))
                return
            if _sec == "default":
                _run_show_config("default")
                return
            _out.info(f"Interpreting 'show config {_sec}' as 'show run config {_sec}'.")
            _run_show_config(
                "run",
                run_selector=_sec,
                show_all=getattr(args, "all", False),
                output_dir=_out_dir,
            )
            return
        if _rd == "default" and _sec == "config":
            _run_show_config("default")
            return
        if _rd == "run" and _sec == "config":
            _run_show_config(
                "run",
                run_selector=_extra,
                show_all=getattr(args, "all", False),
                output_dir=_out_dir,
            )
            return

    # Shifting logic: if run_dir is a bare section name, shift it to section and null run_dir.
    if args.command in {"show", "report"}:
        from pubrun.report.diagnostics import SHOW_SECTIONS
        if getattr(args, "run_dir", None) in SHOW_SECTIONS:
            args.section = args.run_dir
            args.run_dir = None

    executed = False

    if args.command in {"show", "report"}:
        run_dir = getattr(args, "run_dir", None)
        out_dir = getattr(args, "dir", None)
        if not run_dir:
            from pubrun.status import scan_runs, filter_runs
            all_runs = scan_runs(out_dir, keep_manifest=False)
            show_filters = {
                "filter_str": getattr(args, "filter", None),
                "status_filter": getattr(args, "status", None),
                "older_than": getattr(args, "older_than", None),
                "exit_code": getattr(args, "exit_code", None),
                "not_filter_str": getattr(args, "not_filter", None),
                "not_status_filter": getattr(args, "not_status", None),
            }
            has_filters = any(v is not None for v in show_filters.values())
            limit = getattr(args, "limit", None)
            # Bare `pubrun show` reports the single most recent run; filters or -n widen it.
            run_limit = limit if limit is not None else (None if has_filters else 1)
            try:
                matched = filter_runs(all_runs, limit=run_limit, **show_filters)
            except ValueError as e:
                _print_error(str(e))
                sys.exit(1)
            if not matched:
                _print_error(_format_no_runs_error(len(all_runs), out_dir))
                sys.exit(1)
            for idx, r in enumerate(matched):
                if idx > 0:
                    print("\n")
                _run_report(
                    str(r.run_dir),
                    args.depth,
                    getattr(args, "section", None),
                    utc=getattr(args, "utc", False),
                    output_dir=out_dir,
                )
        else:
            _run_report(
                run_dir,
                args.depth,
                getattr(args, "section", None),
                utc=getattr(args, "utc", False),
                output_dir=out_dir,
            )
        executed = True

    elif args.command in {"res", "resources", "cpu", "mem"}:
        metric = "all"
        if args.command == "cpu":
            metric = "cpu"
        elif args.command == "mem":
            metric = "mem"

        _run_resources(
            args.run_dir,
            filter_str=getattr(args, "filter", None),
            status_filter=getattr(args, "status", None),
            older_than=getattr(args, "older_than", None),
            exit_code=getattr(args, "exit_code", None),
            not_filter_str=getattr(args, "not_filter", None),
            not_status_filter=getattr(args, "not_status", None),
            average=getattr(args, "average", False),
            last=getattr(args, "last", None),
            metric=metric,
            width=getattr(args, "width", None),
            output_dir=getattr(args, "dir", None),
            utc=getattr(args, "utc", False),
        )
        executed = True

    elif args.command == "methods":
        _run_methods(
            args.run_dir,
            args.format,
            filter_str=getattr(args, "filter", None),
            status_filter=getattr(args, "status", None),
            older_than=getattr(args, "older_than", None),
            exit_code=getattr(args, "exit_code", None),
            not_filter_str=getattr(args, "not_filter", None),
            not_status_filter=getattr(args, "not_status", None),
            aggregate=getattr(args, "all", False),
            limit=getattr(args, "limit", None),
            output_dir=getattr(args, "dir", None),
        )
        executed = True

    elif args.command == "rerun":
        _run_rerun(
            args.run_dir,
            filter_str=getattr(args, "filter", None),
            status_filter=getattr(args, "status", None),
            older_than=getattr(args, "older_than", None),
            exit_code=getattr(args, "exit_code", None),
            not_filter_str=getattr(args, "not_filter", None),
            not_status_filter=getattr(args, "not_status", None),
            preflight=getattr(args, "preflight", False),
            strict=getattr(args, "strict", False),
            fail_on=getattr(args, "fail_on", None),
            as_json=getattr(args, "as_json", False),
            output_dir=getattr(args, "dir", None),
        )
        executed = True

    elif args.command == "diff":
        _run_diff(
            getattr(args, "run_dirs", []),
            args.export,
            args.no_color,
            getattr(args, "wrap", None),
            getattr(args, "max_length", None),
            getattr(args, "depth", "basic"),
            getattr(args, "same", None),
            filter_str=getattr(args, "filter", None),
            not_filter_str=getattr(args, "not_filter", None),
            status_filter=getattr(args, "status", None),
            not_status_filter=getattr(args, "not_status", None),
            older_than=getattr(args, "older_than", None),
            exit_code=getattr(args, "exit_code", None),
            table=getattr(args, "table", False),
            output_dir=getattr(args, "dir", None),
            as_json=getattr(args, "as_json", False),
        )
        executed = True


    elif args.command == "meta":
        _run_meta(args.out, args.depth)
        executed = True

    elif args.command == "cite":
        _run_cite(args.style)
        executed = True

    elif args.command == "self-check":
        _run_self_check(
            getattr(args, "show_suggestions", False),
            getattr(args, "as_json", False),
            getattr(args, "strict", False),
            quiet=getattr(args, "quiet", False),
        )
        executed = True

    elif args.command == "inspect":
        _run_inspect(
            getattr(args, "run_dir", None),
            getattr(args, "show_suggestions", False),
            getattr(args, "as_json", False),
            getattr(args, "strict", False),
            filter_str=getattr(args, "filter", None),
            not_filter_str=getattr(args, "not_filter", None),
            status_filter=getattr(args, "status", None),
            not_status_filter=getattr(args, "not_status", None),
            older_than=getattr(args, "older_than", None),
            exit_code=getattr(args, "exit_code", None),
            preflight=getattr(args, "preflight", False),
            fail_on=getattr(args, "fail_on", None),
            output_dir=getattr(args, "dir", None),
        )
        executed = True

    elif args.command == "bench":
        _run_bench(
            getattr(args, "iterations", None),
            getattr(args, "passes", None),
            getattr(args, "quick", False),
            getattr(args, "local", False),
            getattr(args, "submit", False),
            getattr(args, "yes", False),
            getattr(args, "as_json", False),
            getattr(args, "unredacted", False),
            submit_file=getattr(args, "submit_file", None),
            gh_repo=getattr(args, "gh_repo", None),
            prepare_submission=getattr(args, "prepare_submission", False),
            no_submit=getattr(args, "no_submit", False),
            scheduler=getattr(args, "scheduler", "auto"),
            rigorous=getattr(args, "rigorous", False),
            no_baseline=getattr(args, "no_baseline", False),
            contribute=getattr(args, "contribute", None),
            wait_timeout=getattr(args, "wait_timeout", None),
        )
        executed = True

    elif args.command == "status":
        _run_status(
            getattr(args, "run_id", None),
            getattr(args, "dir", None),
            getattr(args, "verbose", False),
            filter_str=getattr(args, "filter", None),
            limit=getattr(args, "limit", None),
            status_filter=getattr(args, "status", None),
            older_than=getattr(args, "older_than", None),
            exit_code=getattr(args, "exit_code", None),
            not_filter_str=getattr(args, "not_filter", None),
            not_status_filter=getattr(args, "not_status", None),
            as_json=getattr(args, "as_json", False),
        )
        executed = True

    elif args.command == "clean":
        _run_clean(
            getattr(args, "dir", None),
            getattr(args, "older_than", None),
            getattr(args, "status", None),
            getattr(args, "yes", False),
            getattr(args, "dry_run", False),
            filter_str=getattr(args, "filter", None),
            limit=getattr(args, "limit", None),
            exit_code=getattr(args, "exit_code", None),
            not_filter_str=getattr(args, "not_filter", None),
            not_status_filter=getattr(args, "not_status", None),
            force_remote_locks=getattr(args, "force_remote_locks", False),
        )
        executed = True

    elif args.command == "combined":
        _run_combined(
            args.run_ids,
            args.dir,
            args.output,
            args.yes,
            args.force,
            filter_str=getattr(args, "filter", None),
            status_filter=getattr(args, "status", None),
            limit=getattr(args, "limit", None),
            older_than=getattr(args, "older_than", None),
            exit_code=getattr(args, "exit_code", None),
            not_filter_str=getattr(args, "not_filter", None),
            not_status_filter=getattr(args, "not_status", None),
        )
        executed = True

    elif args.command in {"report-bug", "feedback"}:
        _run_bug_report(no_browser=getattr(args, "no_browser", False))
        executed = True

    elif args.command in {"ui", "tui", "gui"}:
        try:
            from pubrun.tui.app import PubrunTUIApp
            app = PubrunTUIApp(output_dir=getattr(args, "dir", None))
            app.run()
        except ImportError:
            print(
                "pubrun is by default zero-dependency based and does not install the TUI dashboard.\n"
                "Run `pip install textual rich` (or `pip install \"pubrun[tui]\"`) to run the UI.",
                file=sys.stderr
            )
            sys.exit(1)
        executed = True

    elif args.command == "run":
        cmd_args = getattr(args, "command_args", [])
        # Strip leading '--' if present (separates pubrun flags from target command)
        if cmd_args and cmd_args[0] == "--":
            cmd_args = cmd_args[1:]
        if not cmd_args:
            _print_error("No command specified. Usage: pubrun run --mode minimal -- python script.py")
            sys.exit(1)
        # Spawn child process with PUBRUN_IMPORT_MODE and launch-time override set
        import subprocess as _sp
        import signal as _signal
        child_env = {
            **os.environ,
            "PUBRUN_IMPORT_MODE": args.mode,
            "PUBRUN_RUN_MODE_OVERRIDE": args.mode,
        }
        child_proc = None
        prev_sigterm = None
        sigterm_installed = False
        try:
            child_proc = _sp.Popen(cmd_args, env=child_env)

            # Forward SIGTERM to child so it isn't orphaned (P2-S3)
            def _forward_sigterm(signum, frame):
                if child_proc and child_proc.poll() is None:
                    child_proc.terminate()
            if hasattr(_signal, "SIGTERM"):
                try:
                    prev_sigterm = _signal.getsignal(_signal.SIGTERM)
                    _signal.signal(_signal.SIGTERM, _forward_sigterm)
                    sigterm_installed = True
                except ValueError:
                    pass  # Not on main thread

            rc = child_proc.wait()
            # Translate negative returncode (signal death) to 128+N (P2-B4)
            if rc < 0:
                sys.exit(128 + abs(rc))
            sys.exit(rc)
        except (FileNotFoundError, PermissionError) as e:
            _print_error(f"Cannot execute command: {e}")
            sys.exit(127)
        except IsADirectoryError as e:
            _print_error(f"Cannot execute command: {e}")
            sys.exit(126)
        except KeyboardInterrupt:
            if child_proc and child_proc.poll() is None:
                # Give the child a brief grace window to finish SIGINT finalization
                # before sending SIGTERM.
                try:
                    child_proc.wait(timeout=3.0)
                except _sp.TimeoutExpired:
                    child_proc.terminate()
                    try:
                        child_proc.wait(timeout=5.0)
                    except _sp.TimeoutExpired:
                        child_proc.kill()
                        child_proc.wait()
            sys.exit(130)
        finally:
            if sigterm_installed and prev_sigterm is not None:
                try:
                    _signal.signal(_signal.SIGTERM, prev_sigterm)
                except (ValueError, OSError):
                    pass

    elif args.command == "init":
        dest = getattr(args, "dest", ".pubrun.toml")
        _create_config(dest)
        print()
        print("Getting started:")
        print("  1. Add 'import pubrun' at the top of your script.")
        print("  2. Run your script normally to record environment, git, packages, and resources.")
        print("  3. View results: pubrun status")
        print()
        print(f"  Config: {dest}")
        print("  Tip: set capture_mode = \"standard\" in [console] to capture stdout/stderr.")
        executed = True

    if getattr(args, "create_config", False):
        dest = args.create_config
        if dest == "PROMPT":
            print("\nWhere would you like to install the default configuration?")
            print("  [1] Locally (./.pubrun.toml)")
            global_hint = "Global AppData" if sys.platform == "win32" else "Global (~/.config/pubrun/config.toml)"
            print(f"  [2] {global_hint}")

            try:
                choice = input("Select an option [1/2] (Default: 1): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nConfiguration abandoned.", file=sys.stderr)
                sys.exit(1)

            if choice == "2":
                from pubrun.config import get_global_config_dir
                dest = str(get_global_config_dir() / "config.toml")
            elif choice in ["1", ""]:
                dest = ".pubrun.toml"
            else:
                _print_error("Invalid selection.")
                sys.exit(1)

        _create_config(dest)
        executed = True

    if getattr(args, "show_config", False):
        # Soft-deprecated: `show default config` is the canonical form. Keep --show-config
        # working (prints the raw defaults, unchanged) but nudge to the new command. The
        # notice goes to stderr so piping stdout to a file stays clean.
        print("[WARN ] --show-config is deprecated; use `pubrun show default config`.", file=sys.stderr)
        from pubrun.config import _read_package_resource
        content = _read_package_resource("pubrun.resources", "default.toml")
        print(content)
        executed = True

    if getattr(args, "info", False):
        _show_info()
        executed = True

    if getattr(args, "run_tests", False):
        _run_tests()
        executed = True

    if not executed:
        parser.print_help()
        try:
            runs_dir = _resolve_output_base_dir()
            run_count = 0
            if runs_dir.exists() and runs_dir.is_dir():
                with os.scandir(runs_dir) as it:
                    for entry in it:
                        try:
                            if entry.name.startswith("pubrun-") and entry.is_dir(follow_symlinks=False):
                                run_count += 1
                        except OSError:
                            continue
            if run_count:
                print(f"\nFound {run_count} run(s) in the output directory. Run '{prog_name} status' to view them.")
            else:
                print("\nNo runs found in the output directory.")
                print("Quick start:")
                print("  1. Add 'import pubrun' at the top of your Python script.")
                print(f"  2. Run your script, then inspect results with '{prog_name} status' or '{prog_name} show'.")
                print(f"  3. Optional: run '{prog_name} init' to create a .pubrun.toml configuration file.")
        except Exception:
            pass


if __name__ == "__main__":
    main()
