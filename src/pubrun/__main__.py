import argparse
import sys
import os
import re
import json
import time
import tempfile
import subprocess
from pathlib import Path
from typing import List, Optional

from pubrun import __version__

from pubrun.report import output as _out


def _print_error(message: str) -> None:
    _out.error(message)


def _print_warn(message: str) -> None:
    _out.warn(message)


def _emit_ambiguous_selector(e) -> None:
    """Print a clear, non-guessing message when a bare integer matched both a recency index
    and a run id. The unambiguous escape hatch is the full id or the directory path."""
    rec = getattr(e.by_recency, "run_id", "?")
    other = getattr(e.by_id, "run_id", "?")
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
            self.run_info = RunInfo(run_dir)
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
) -> str:
    """Resolve the path to a manifest.json, auto-detecting the latest run if needed."""
    if run_dir:
        # Resolve via find_run first (supports recency index / id-prefix / dir-substring).
        from pubrun.status import find_run, AmbiguousRunSelectorError
        try:
            run_info = find_run(run_dir)
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
        try:
            from pubrun.config import resolve_config
            config = resolve_config()
            base_str = config.get("core", {}).get("output_dir", "")
            runs_dir = Path(base_str) if base_str else Path.cwd() / "runs"
        except Exception:
            runs_dir = Path("runs")

        if not runs_dir.exists() or not runs_dir.is_dir():
            _print_error(f"No --run directory provided and '{runs_dir}' directory not found.")
            sys.exit(1)

        from pubrun.status import scan_runs, filter_runs
        all_runs = scan_runs(str(runs_dir))
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
        if not matched:
            _print_error("No runs match the filter criteria.")
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


def _run_methods(
    run_dir: str,
    format_type: str,
    filter_str: Optional[str] = None,
    status_filter: Optional[str] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
    not_filter_str: Optional[str] = None,
    not_status_filter: Optional[str] = None,
    aggregate: bool = False,
    limit: Optional[int] = None,
) -> None:
    """Generate and print an academic 'Computational Methods' paragraph.

    Default: the single most-recent matching run (unchanged behavior). With
    ``aggregate=True`` (the ``--all`` flag): aggregate ALL matching runs into one
    representative paragraph plus a variance note (IPD 20260706-methods-multi-run).
    """
    if aggregate:
        _run_methods_aggregate(
            run_dir, format_type,
            filter_str=filter_str, status_filter=status_filter,
            older_than=older_than, exit_code=exit_code,
            not_filter_str=not_filter_str, not_status_filter=not_status_filter,
            limit=limit,
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
        )

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # Hydrate to merge parent HPC context if available
        manifest, warnings = hydrate_manifest(manifest_path, manifest)
        if warnings:
            for w in warnings:
                _out.warn(w)

        # Dispatch to structural compilers
        text = generate_report(manifest, format_type)
        print("--- Generated Computational Methods Section ---")
        print(text)
        print("-----------------------------------------------\n")
    except RunInProgressOrCrashedError as e:
        status = e.run_info.status if e.run_info else "crashed/running"
        _print_error(f"Run '{e.run_dir.name}' is currently {status} and does not have a manifest.json.")
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
    format_type: str,
    filter_str: Optional[str] = None,
    status_filter: Optional[str] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
    not_filter_str: Optional[str] = None,
    not_status_filter: Optional[str] = None,
    limit: Optional[int] = None,
) -> None:
    """`pubrun methods --all`: aggregate the matching run set into one paragraph.

    Reuses the existing run-filter machinery (scan_runs + filter_runs). Loads each
    manifest defensively (skips malformed, counts them). Emits the methods
    paragraph, then a "narrow it" suggestion CLEARLY MARKED as not part of the
    methods text (authoritative textual marker; optional non-DIM color; safe
    under NO_COLOR).
    """
    import json as _json
    from pubrun.report.methods import generate_report_multi
    from pubrun.report.utils import hydrate_manifest
    from pubrun.status import scan_runs, filter_runs

    if run_dir:
        _print_error("`pubrun methods --all` aggregates a filtered set; do not also "
                     "pass a specific run directory. Use -f/-F/-s/-S/-n to select.")
        sys.exit(1)

    all_runs = scan_runs()
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
    if not matched:
        _print_error("No runs match the filter criteria.")
        sys.exit(1)

    manifests: list = []
    skipped = 0
    for r in matched:
        mp = r.run_dir / "manifest.json"
        if not mp.exists():
            skipped += 1
            continue
        try:
            with open(mp, "r", encoding="utf-8") as f:
                m = _json.load(f)
            m, _warnings = hydrate_manifest(str(mp), m)
            manifests.append(m)
        except Exception:
            skipped += 1  # malformed/unreadable manifest — skip, don't abort

    if not manifests:
        _print_error("No readable manifests among the matching runs.")
        sys.exit(1)

    text = generate_report_multi(manifests, format_type)
    print("--- Generated Computational Methods Section ---")
    print(text)
    print("-----------------------------------------------\n")

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
        notes.append(f"aggregated {n} runs — consider narrowing with -f / -F / -s / -n "
                     f"if that is broader than the study you mean to report.")
    if notes:
        from pubrun.report.diagnostics import Colors, _has_color
        use_color = _has_color()
        prefix = "# pubrun note (not part of the methods section):"
        if use_color:
            prefix = f"{Colors.CYAN}{prefix}{Colors.RESET}"
        print(prefix, file=sys.stderr)
        for note in notes:
            line = f"#   {note}"
            print(f"{Colors.CYAN}{line}{Colors.RESET}" if use_color else line, file=sys.stderr)


def _run_rerun(
    run_dir: str,
    filter_str: Optional[str] = None,
    status_filter: Optional[str] = None,
    older_than: Optional[str] = None,
    exit_code: Optional[int] = None,
    not_filter_str: Optional[str] = None,
    not_status_filter: Optional[str] = None,
) -> None:
    """Print the shell command needed to reproduce a recorded run."""
    try:
        manifest_path = _get_manifest_path(
            run_dir,
            filter_str=filter_str,
            status_filter=status_filter,
            older_than=older_than,
            exit_code=exit_code,
            not_filter_str=not_filter_str,
            not_status_filter=not_status_filter,
        )
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        inv = manifest.get("invocation", {})
        rerun_cmd = inv.get("rerun_command")

        if rerun_cmd:
            if sys.platform == "win32" and "&& python " in rerun_cmd:
                rerun_cmd = rerun_cmd.replace(" && python ", "\npython ").replace("'", '"')
            print(rerun_cmd)
        else:
            _print_error("Target manifest does not contain a valid 'rerun_command' payload.")
            sys.exit(1)
    except RunInProgressOrCrashedError as e:
        status = e.run_info.status if e.run_info else "crashed/running"
        lock_data = e.run_info.lock_data if (e.run_info and hasattr(e.run_info, "lock_data")) else None
        if lock_data:
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

            _print_warn(f"Run '{e.run_dir.name}' is currently {status} and does not have a manifest.json. Reconstructed rerun command from lock file:")
            if sys.platform == "win32" and "&& python " in rerun_cmd:
                rerun_cmd = rerun_cmd.replace(" && python ", "\npython ").replace("'", '"')
            print(rerun_cmd)
        else:
            _print_error(f"Run '{e.run_dir.name}' is currently {status} and does not have a manifest.json.")
            sys.exit(1)
    except Exception as e:
        _print_error(f"Failed to fetch rerun command: {e}")
        sys.exit(1)


def _run_diff(run_dirs: List[str], export_format: str, no_color: bool, wrap_config: Optional[bool] = None, max_length: Optional[int] = None, depth: str = "basic", show_same: Optional[bool] = None,
              filter_str: Optional[str] = None, not_filter_str: Optional[str] = None,
              status_filter: Optional[str] = None, not_status_filter: Optional[str] = None,
              older_than: Optional[str] = None, exit_code: Optional[int] = None, table: bool = False) -> None:
    """Run the semantic diff engine comparing two execution traces.

    When no positional run directories are given, the pair to compare is drawn from
    the runs matching the shared filter options (``-f/-F/-s/-S/--older-than/--exit-code``);
    with no filters this is every run with a manifest (the historical behavior).
    """
    try:
        from pubrun.report.utils import hydrate_manifest
        from pubrun.config import resolve_config
        from pubrun.analysis.diff import compare_manifests, export_manifest
        from pubrun.analysis.render import print_diff
        from pubrun.status import scan_runs, find_run, filter_runs

        all_runs = scan_runs()
        valid_runs = [r for r in all_runs if (r.run_dir / "manifest.json").exists()]

        # Apply the shared run filters to narrow the candidate set used for
        # auto-selection. Explicit positional run_dirs always win over filters.
        has_filter = any(v is not None for v in (
            filter_str, not_filter_str, status_filter, not_status_filter, older_than, exit_code
        ))
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

        if len(run_dirs) >= 2:
            run_dir_a = run_dirs[0]
            run_dir_b = run_dirs[1]
        elif len(run_dirs) == 1:
            run_dir_a = run_dirs[0]

            # Resolve run_dir_a to its canonical path first
            r_a = find_run(run_dir_a)
            run_dir_a_path = r_a.run_dir if r_a else Path(run_dir_a)

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

            run_dir_b = str(run_dir_b_path)
            _out.info(f"Comparing {run_dir_a_path.name} against most recent other run: {run_dir_b_path.name}")
        else:
            # 0 runs provided: diff the last two runs from the (optionally filtered)
            # candidate set: second most recent as baseline A, most recent as target B.
            if len(valid_runs) < 2:
                if has_filter:
                    _print_error(f"diff needs two runs, but only {len(valid_runs)} matched the filter. Widen the filter or pass two run directories explicitly.")
                else:
                    _print_error(f"Need at least 2 runs with manifest.json to perform default diff (found {len(valid_runs)}).")
                sys.exit(1)
            run_dir_a = str(valid_runs[1].run_dir)
            run_dir_b = str(valid_runs[0].run_dir)
            _out.info(f"Auto-detected last two runs for comparison: {valid_runs[1].run_dir.name} vs {valid_runs[0].run_dir.name}")

        manifest_path_a = _get_manifest_path(run_dir_a)
        manifest_path_b = _get_manifest_path(run_dir_b)

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
        else:
            diff_report = compare_manifests(manifest_a, manifest_b, ignores, show_same=ss_target, depth=depth)
            wrap_target = wrap_config if wrap_config is not None else conf.get("wrap", True)
            mlen_target = max_length if max_length is not None else conf.get("max_string_length", 300)
            print_diff(diff_report, no_color=no_color, wrap=wrap_target, max_length=mlen_target, depth=depth, table=table)

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
) -> None:
    """Print resource monitoring graphs for a recorded run."""
    try:
        from pubrun.report.diagnostics import print_resources_report
        manifest_path = _get_manifest_path(
            run_dir,
            filter_str=filter_str,
            status_filter=status_filter,
            older_than=older_than,
            exit_code=exit_code,
            not_filter_str=not_filter_str,
            not_status_filter=not_status_filter,
        )
        print_resources_report(manifest_path, average=average, last=last, metric=metric, width=width)
    except RunInProgressOrCrashedError as e:
        status = e.run_info.status if e.run_info else "crashed/running"
        _print_error(f"Run '{e.run_dir.name}' is currently {status} and does not have a manifest.json.")
    except FileNotFoundError as e:
        _print_error(str(e))
        sys.exit(1)
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


def _run_show_config(mode: str, run_selector: Optional[str] = None, show_all: bool = False) -> None:
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
        run_path = None
        if run_selector:
            try:
                info = find_run(run_selector)
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
                from pubrun.config import resolve_config as _rc
                out_dir = _rc().get("core", {}).get("output_dir") or "runs"
                runs = scan_runs(out_dir)
                if not runs:
                    _print_error("No runs found to show config for.")
                    sys.exit(1)
                run_path = sorted(runs, key=lambda r: r.started_at_utc or 0, reverse=True)[0].run_dir
            except SystemExit:
                raise
            except Exception as e:
                _print_error(f"Could not locate the most recent run: {e}")
                sys.exit(1)

        cfg_path = Path(run_path) / "config.resolved.json"
        if not cfg_path.exists():
            # Ghost run (never wrote a run dir/config) or otherwise absent.
            _print_error(
                f"Run '{Path(run_path).name}' has no recorded config "
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


def _run_report(run_dir: str, depth: str, section: Optional[str] = None, utc: bool = False) -> None:
    """Print a human-readable diagnostic report for a recorded run."""
    try:
        from pubrun.report.diagnostics import print_report
        try:
            manifest_path = _get_manifest_path(run_dir)
            print_report(manifest_path, depth, section, utc=utc)
        except RunInProgressOrCrashedError as e:
            if section == "logs":
                run_dir_path = e.run_dir
                stdout_path = run_dir_path / "stdout.log"
                stderr_path = run_dir_path / "stderr.log"
                if stdout_path.exists():
                    try:
                        with open(stdout_path, "r", encoding="utf-8", errors="replace") as sf:
                            print(sf.read(), end="")
                    except Exception as le:
                        _print_error(f"Failed to read stdout log: {le}")
                if stderr_path.exists():
                    try:
                        with open(stderr_path, "r", encoding="utf-8", errors="replace") as se:
                            print(se.read(), end="")
                    except Exception as le:
                        _print_error(f"Failed to read stderr log: {le}")
                sys.exit(0)
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
                    from datetime import datetime
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

            use_color = not os.environ.get("NO_COLOR", "")
            bold = "\033[1m" if use_color else ""
            red = "\033[91m" if use_color else ""
            yellow = "\033[93m" if use_color else ""
            rst = "\033[0m" if use_color else ""

            if status == "running":
                print(f"Status: {bold}{yellow}STILL RUNNING{rst}\n", file=sys.stderr)
            else:
                print(f"Status: {bold}{red}CRASHED{rst}\n", file=sys.stderr)
                from pubrun.status import close_out_crashed_run
                close_out_crashed_run(run_dir_path, run_info.lock_data)

        # Tail error logs (last 10 lines)
        log_file = None
        stderr_path = run_dir_path / "stderr.log"
        stdout_path = run_dir_path / "stdout.log"
        if stderr_path.exists() and stderr_path.stat().st_size > 0:
            log_file = stderr_path
        elif stdout_path.exists() and stdout_path.stat().st_size > 0:
            log_file = stdout_path

        if log_file:
            print(f"Last 10 lines of {log_file.name}:", file=sys.stderr)
            try:
                with open(log_file, "r", encoding="utf-8", errors="replace") as lf:
                    lines = lf.readlines()
                    tail_lines = lines[-10:]
                    for line in tail_lines:
                        sys.stderr.write(line)
                    if tail_lines and not tail_lines[-1].endswith("\n"):
                        sys.stderr.write("\n")
            except Exception as le:
                print(f"  (Failed to read log file: {le})", file=sys.stderr)
            print("", file=sys.stderr)

        # Suggest the most recent non-crashed (completed/failed) run
        try:
            from pubrun.config import resolve_config
            config = resolve_config()
            base_str = config.get("core", {}).get("output_dir", "")
            runs_dir = Path(base_str) if base_str else Path.cwd() / "runs"
        except Exception:
            runs_dir = Path("runs")

        completed_runs = []
        if runs_dir.exists() and runs_dir.is_dir():
            for d in runs_dir.iterdir():
                if d.is_dir() and d.name.startswith("pubrun-") and (d / "manifest.json").exists():
                    try:
                        with open(d / "manifest.json", "r", encoding="utf-8") as f:
                            m = json.load(f)
                            if m.get("status", {}).get("outcome") != "crashed":
                                completed_runs.append((d, d.stat().st_mtime))
                    except Exception:
                        pass

        if completed_runs:
            completed_runs.sort(key=lambda x: x[1], reverse=True)
            latest_completed = completed_runs[0][0]
            print("Suggestion: To view the report for the most recent completed run, run:", file=sys.stderr)
            print(f"  pubrun report {latest_completed}", file=sys.stderr)
        else:
            print("No completed runs with a manifest.json were found in the output directory.", file=sys.stderr)
            print("See 'pubrun status' to view all active or crashed runs.", file=sys.stderr)

        sys.exit(1)

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
    while no peer-reviewed publication exists yet. Once a journal article (e.g.
    JOSS) is accepted, update these strings and CITATION.cff to the published
    citation with its DOI.
    """
    style = style.lower()
    try:
        from pubrun import __version__ as _ver
    except Exception:
        _ver = None
    ver_apa = f" (Version {_ver})" if _ver else ""
    ver_bib = f",\n  version   = {{{_ver}}}" if _ver else ""
    url = "https://github.com/fariello/pubrun"
    title = "pubrun: Low-friction execution provenance for Python research"
    # Zenodo concept DOI (all versions). PLACEHOLDER until the repo is enabled in
    # Zenodo and the first GitHub release mints a real DOI. Keep this in sync with
    # CITATION.cff / README (a consistency test guards drift). Replace
    # "10.5281/zenodo.PENDING" with the real concept DOI in Phase 2; see
    # .agents/plans/pending/20260706-citation-doi-and-enforceable-attribution.md.
    doi = "10.5281/zenodo.PENDING"
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
    use_color = not os.environ.get("NO_COLOR", "") and sys.stdout.isatty()
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
        use_color = not os.environ.get("NO_COLOR", "") and sys.stdout.isatty()
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


def _run_inspect(run_dir: Optional[str], show_suggestions: bool, as_json: bool, strict: bool,
                 filter_str: Optional[str] = None, not_filter_str: Optional[str] = None,
                 status_filter: Optional[str] = None, not_status_filter: Optional[str] = None,
                 older_than: Optional[str] = None, exit_code: Optional[int] = None) -> None:
    """Diagnose a COMPLETED run's manifest: capture-completeness + recorded I/O signals,
    with a glaring banner when the inspecting host differs from the run's host."""
    try:
        manifest_path = _get_manifest_path(
            run_dir or "", filter_str=filter_str, status_filter=status_filter,
            older_than=older_than, exit_code=exit_code, not_filter_str=not_filter_str,
            not_status_filter=not_status_filter,
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

    from pubrun.report.checks import manifest_findings
    findings = manifest_findings(manifest, current_hostname=current_hostname)

    # The different-host banner is always shown (never hidden behind --show-suggestions),
    # because a live-vs-run host mismatch changes how everything else should be read.
    banner = [f for f in findings if f.get("code") == "different_host"]
    rest = [f for f in findings if f.get("code") != "different_host"]
    if banner and not as_json:
        use_color = not os.environ.get("NO_COLOR", "") and sys.stdout.isatty()
        line = _fmt_finding(banner[0], use_color)
        bar = "=" * 60
        print(bar)
        print(line)
        print(bar)

    _emit_findings(rest if not as_json else findings,
                   show_suggestions=show_suggestions, as_json=as_json,
                   header="pubrun inspect")
    if strict and any(f.get("severity") == "warn" for f in findings):
        sys.exit(1)


# --- bench: friendly benchmark runner + HPC (Slurm) submit + share guidance ---------

# Public repo for community-contributed benchmark results. Submissions arrive as issues
# (attach the redacted JSON); opening from your own GitHub account is the contact channel.
_BENCH_SUBMIT_URL = "https://github.com/fariello/pubrun-benchmarks/issues/new"


def _find_bench_harness():
    """Locate benchmarks/harness.py in a source checkout.

    The benchmark tooling is NOT packaged into the wheel (it is dev/reproducibility
    tooling, kept out of every user install for zero-footprint). So `pubrun bench` requires
    a source checkout. Returns the Path or None.
    """
    candidates = []
    # 1) alongside the installed package's repo (…/src/pubrun/__main__.py -> repo root)
    try:
        here = Path(__file__).resolve()
        # src/pubrun/__main__.py -> parents[2] == repo root
        candidates.append(here.parents[2] / "benchmarks" / "harness.py")
    except Exception:
        pass
    # 2) cwd (running from a checkout)
    candidates.append(Path.cwd() / "benchmarks" / "harness.py")
    for c in candidates:
        try:
            if c.is_file():
                return c
        except Exception:
            continue
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


_DEFAULT_BENCH_REPO = "fariello/pubrun-benchmarks"

# Sensitive keys that a properly-redacted benchmark result must NOT expose as raw strings.
# Kept in sync with benchmarks/harness.py `_REDACT_KEYS`/`_REDACT_LIST_KEYS`. Duplicated here
# (not imported) because the benchmark tooling is NOT packaged in the wheel, so the CLI cannot
# import from benchmarks/.
_BENCH_SENSITIVE_KEYS = {
    "hostname", "username", "executable", "prefix", "base_prefix", "virtual_env",
    "python_executable", "path", "mount_point", "run_dir", "output_base_dir",
    "results_dir", "pubrun_install", "tmpdir",
}
_BENCH_SENSITIVE_LIST_KEYS = {"sys_path", "source_files"}
# A safe charset for an OWNER/NAME GitHub repo slug (blocks shell metacharacters / injection).
_GH_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _pii_needles() -> list:
    """Home-dir prefix + OS username: the substrings a redacted file must never contain."""
    needles = []
    try:
        home = os.path.expanduser("~")
        if home and home != "~":
            needles.append(home)
    except Exception:
        pass
    try:
        import getpass
        needles.append(getpass.getuser())
    except Exception:
        pass
    return sorted({n for n in needles if n}, key=len, reverse=True)


def _scan_for_pii(obj, needles) -> Optional[str]:
    """Return the first offending substring found anywhere in the structure, else None."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _BENCH_SENSITIVE_LIST_KEYS and isinstance(v, list):
                for item in v:
                    if isinstance(item, str) and item and item != "<redacted>":
                        return f"{k}[]={item!r}"
            elif k in _BENCH_SENSITIVE_KEYS and isinstance(v, str) and v and v != "<redacted>":
                return f"{k}={v!r}"
            hit = _scan_for_pii(v, needles)
            if hit:
                return hit
    elif isinstance(obj, list):
        for item in obj:
            hit = _scan_for_pii(item, needles)
            if hit:
                return hit
    elif isinstance(obj, str):
        for n in needles:
            if n and n in obj:
                return f"contains {n!r}"
    return None


def _verify_redacted(path) -> tuple:
    """Return (ok, detail). ok=True iff the file parses as JSON and looks redacted:
    no enumerated sensitive key holds a raw value and no home-dir/username substring leaks.
    This gates EVERY transmit path (the never-publish-PII invariant)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        return (False, f"could not read/parse {path} as JSON: {e}")
    hit = _scan_for_pii(data, _pii_needles())
    if hit:
        return (False, f"file does not look redacted ({hit})")
    return (True, "")


def _bench_issue_title() -> str:
    import platform as _pf
    return f"benchmark result: {_pf.system()} / Python {_pf.python_version()}"


def _bench_issue_body(redacted_path) -> str:
    """A short human-readable wrapper + the redacted JSON in a fenced block."""
    try:
        content = open(redacted_path, "r", encoding="utf-8").read()
    except OSError as e:
        content = f"(could not read {redacted_path}: {e})"
    return (
        "Community-contributed pubrun overhead benchmark result (redacted).\n\n"
        "```json\n" + content.rstrip("\n") + "\n```\n"
    )


def _scrub(text, secrets) -> str:
    """Remove any secret substring (e.g. a token) from text before printing."""
    if not text:
        return text
    for s in secrets:
        if s:
            text = text.replace(s, "<redacted>")
    return text


def _submit_via_gh(repo, redacted_path):
    """Try `gh issue create`. Return the issue URL on success, or None if gh is
    unavailable/unauthenticated/failed (caller falls through)."""
    import shutil as _sh
    import subprocess as _sp
    import tempfile as _tf
    if not _sh.which("gh"):
        return (None, "gh not on PATH")
    try:
        auth = _sp.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=15)
    except Exception as e:
        return (None, f"gh auth status failed: {e}")
    if auth.returncode != 0:
        return (None, "gh is not authenticated (`gh auth login`)")
    body = _bench_issue_body(redacted_path)
    tf = None
    try:
        tf = _tf.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        tf.write(body)
        tf.close()
        # argv list, never shell=True; repo/title/paths are discrete args.
        cmd = ["gh", "issue", "create", "--repo", repo,
               "--title", _bench_issue_title(), "--body-file", tf.name]
        proc = _sp.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            return (None, f"gh issue create failed: {(proc.stderr or proc.stdout).strip()}")
        url = (proc.stdout or "").strip().splitlines()[-1] if proc.stdout.strip() else ""
        return (url or "created", None)
    except Exception as e:
        return (None, f"gh issue create error: {e}")
    finally:
        if tf is not None:
            try:
                os.unlink(tf.name)
            except OSError:
                pass


def _resolve_gh_token(explicit):
    """Token source order: --gh-token > GITHUB_TOKEN/GH_TOKEN > `gh auth token`. Returns
    (token, source) or (None, None). Never logs the value."""
    if explicit:
        return (explicit, "--gh-token")
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(var):
            return (os.environ[var], f"${var}")
    try:
        import shutil as _sh
        import subprocess as _sp
        if _sh.which("gh"):
            proc = _sp.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=15)
            if proc.returncode == 0 and proc.stdout.strip():
                return (proc.stdout.strip(), "gh auth token")
    except Exception:
        pass
    return (None, None)


def _submit_via_http(repo, redacted_path, token):
    """POST to the GitHub Issues API via stdlib urllib. Return (url, None) on success or
    (None, reason) to fall through. HTTPS-only; hardened headers; token never echoed."""
    import urllib.request
    import urllib.error
    if not token:
        return (None, "no GitHub token (set --gh-token, $GITHUB_TOKEN, or `gh auth login`)")
    api = f"https://api.github.com/repos/{repo}/issues"
    payload = json.dumps({"title": _bench_issue_title(),
                          "body": _bench_issue_body(redacted_path)}).encode("utf-8")
    req = urllib.request.Request(api, data=payload, method="POST")
    req.add_header("User-Agent", f"pubrun/{__version__}")  # GitHub rejects requests w/o UA
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        # HTTPS-only + explicit timeout so a stalled connection cannot hang the CLI.
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return (data.get("html_url", "created"), None)
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        extra = ""
        if e.code in (403, 429):
            ra = e.headers.get("Retry-After") or e.headers.get("X-RateLimit-Reset")
            extra = f" (rate-limited; retry-after/reset={ra})" if ra else " (rate-limited)"
        return (None, _scrub(f"GitHub API HTTP {e.code}{extra}: {detail[:200]}", [token]))
    except Exception as e:
        return (None, _scrub(f"HTTP submit error: {e}", [token]))


def _print_floor(repo, redacted_path, reasons, interactive) -> None:
    """The always-works manual fallback: explain, then offer a copy-paste submission."""
    print("", file=sys.stderr)
    if reasons:
        print("Automated submission was not possible:", file=sys.stderr)
        for r in reasons:
            print(f"  - {r}", file=sys.stderr)
    do_print = True
    if interactive:
        try:
            resp = input("Print a ready-to-paste submission (issue body + gh command)? [Y/n] ").strip().lower()
            do_print = resp in ("", "y", "yes")
        except (EOFError, KeyboardInterrupt):
            do_print = False
    if not do_print:
        print(f"To submit later: pubrun bench --submit-file \"{redacted_path}\"", file=sys.stderr)
        print(f"Or open an issue manually at: {_BENCH_SUBMIT_URL}", file=sys.stderr)
        return
    print("\n--- Copy-paste submission ------------------------------------------", file=sys.stderr)
    print(f"Open an issue at: {_BENCH_SUBMIT_URL}", file=sys.stderr)
    print(f"Title: {_bench_issue_title()}", file=sys.stderr)
    print("Or with the GitHub CLI:", file=sys.stderr)
    print(f'  gh issue create --repo {repo} --title "{_bench_issue_title()}" '
          f'--body-file "{redacted_path}"', file=sys.stderr)
    print("\nIssue body:\n", file=sys.stderr)
    print(_bench_issue_body(redacted_path), file=sys.stderr)
    print("--------------------------------------------------------------------", file=sys.stderr)


def _submit_benchmark(redacted_path, repo, method, gh_token, interactive) -> None:
    """Consent-gated submission chain: gh -> HTTP-to-Issues -> printed floor. Callers must
    have already obtained explicit consent and a REDACTED file (verified). Never raises out."""
    if not _GH_REPO_RE.match(repo or ""):
        _print_error(f"Invalid --gh-repo {repo!r}; expected OWNER/NAME.")
        return
    reasons = []

    if method == "print":
        _print_floor(repo, redacted_path, [], interactive)
        return

    # (a) gh
    if method in (None, "gh"):
        url, why = _submit_via_gh(repo, redacted_path)
        if url:
            print(f"\nSubmitted. Thank you! {url}", file=sys.stderr)
            return
        reasons.append(f"gh: {why}")
        if method == "gh":
            _print_floor(repo, redacted_path, reasons, interactive)
            return

    # (b) HTTP to GitHub Issues API
    if method in (None, "http"):
        token, source = _resolve_gh_token(gh_token)
        if source:
            print(f"Using GitHub token from {source}.", file=sys.stderr)
        url, why = _submit_via_http(repo, redacted_path, token)
        if url:
            print(f"\nSubmitted. Thank you! {url}", file=sys.stderr)
            return
        reasons.append(f"http: {why}")

    # (c) printed floor
    _print_floor(repo, redacted_path, reasons, interactive)


def _print_share_guidance(results_path, redacted_path) -> None:
    print("", file=sys.stderr)
    print("To contribute this benchmark result:", file=sys.stderr)
    print(f"  1. A redacted, shareable copy was written to:\n       {redacted_path}", file=sys.stderr)
    print("     (hostname, username, and home-directory paths are masked; CPU/GPU model,", file=sys.stderr)
    print("      timings, versions, filesystem type, and Slurm partition are preserved.)", file=sys.stderr)
    print(f"  2. Attach it to a new issue at:\n       {_BENCH_SUBMIT_URL}", file=sys.stderr)
    print("     Opening the issue from your own GitHub account lets us follow up with", file=sys.stderr)
    print("     questions without any personal data in the file (fully anonymous", file=sys.stderr)
    print("     submission is fine too). Note: CPU/GPU model + a distinctive partition", file=sys.stderr)
    print("     name can still be re-identifying in a small group.", file=sys.stderr)
    print(f"  Full (un-redacted) results for your own analysis are at:\n       {results_path}", file=sys.stderr)


def _run_bench(iterations, passes, quick, local, submit, yes, as_json, no_redact,
               submit_file=None, submit_method=None, gh_repo=None, gh_token=None,
               print_submission=False, no_submit=False, scheduler="auto", rigorous=False,
               no_baseline=False) -> None:
    """Friendly front-end over benchmarks/harness.py with optional HPC scheduler submission
    (Slurm/PBS/LSF/SGE) and consent-gated result submission to the public pubrun-benchmarks
    repo."""
    repo = gh_repo or _DEFAULT_BENCH_REPO
    if not _GH_REPO_RE.match(repo):
        _print_error(f"Invalid --gh-repo {repo!r}; expected OWNER/NAME.")
        sys.exit(1)
    interactive = sys.stdin.isatty()

    # --- Recovery / HPC / batch path: submit an EXISTING file, no benchmark run. ---
    if submit_file is not None:
        p = Path(submit_file)
        if not p.is_file():
            _print_error(f"--submit-file: no such file: {submit_file}")
            sys.exit(1)
        # NEVER auto-transmit an un-redacted result to the PUBLIC repo (verifier gates it).
        if not no_redact:
            ok, detail = _verify_redacted(p)
            if not ok:
                _print_error(
                    f"Refusing to submit: {detail}.\n"
                    "This looks like a full (un-redacted) result, which may contain personal "
                    "data. Point --submit-file at the '.redacted.json' copy, or, only if you "
                    "have manually verified it is safe, pass --no-redact to override.")
                sys.exit(1)
        else:
            print("WARNING: --no-redact given; skipping the redaction safety check. Ensure "
                  "this file contains no personal data before it is published publicly.",
                  file=sys.stderr)
        if print_submission:
            _print_floor(repo, str(p), [], interactive)
            return
        _submit_benchmark(str(p), repo, submit_method, gh_token, interactive)
        return

    harness = _find_bench_harness()
    if harness is None:
        _print_error(
            "Could not find benchmarks/harness.py. `pubrun bench` needs a source checkout "
            "(the benchmark tooling is not shipped in the pip package). Clone the repo:\n"
            "  git clone https://github.com/fariello/pubrun && cd pubrun\n"
            "  python -m pubrun bench")
        sys.exit(1)
    repo_root = harness.parents[1]

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

    want_submit = (submit or (not local and chosen is not None and not chosen.get("on_compute_node"))) \
        and scheduler != "local"
    if want_submit and chosen is not None:
        submit_script = repo_root / "benchmarks" / chosen["submit_script"]
        if not submit_script.is_file():
            _print_error(f"{chosen['name']} detected but {submit_script} is missing; "
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
        if iterations:
            extra += ["--iterations", str(int(iterations))]
        if passes:
            extra += ["--passes", str(int(passes))]
        cmd = ["bash", str(submit_script)] + extra
        label = chosen["name"].upper() if chosen["name"] != "slurm" else "Slurm"
        print(f"{label} detected. Submission command:\n  {' '.join(cmd)}", file=sys.stderr)
        if not (submit or yes):
            try:
                resp = input(f"Submit this benchmark job to {label}? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                resp = ""
            if resp not in ("y", "yes"):
                print("Not submitting. Re-run with --submit/--yes to submit, or --local to run here.", file=sys.stderr)
                return
        import subprocess as _sp
        env = dict(os.environ)
        env.setdefault("PUBRUN_REPO", str(repo_root))
        env.setdefault("PUBRUN_PY", sys.executable)
        try:
            _sp.run(cmd, env=env, check=False)  # argv list; no shell
        except Exception as e:
            _print_error(f"Failed to submit: {e}")
            sys.exit(1)
        print("Submitted. Results will be written under benchmarks/results/ on the compute node.", file=sys.stderr)
        return

    # --- Local path ---
    import subprocess as _sp
    import tempfile as _tf
    results_dir = repo_root / "benchmarks" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    import platform as _pf
    from datetime import datetime, timezone
    host = (_pf.node() or "unknown").replace("/", "_")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = results_dir / f"{host}-{ts}.json"
    argv = [sys.executable, str(harness), "--out", str(out_path)]
    if quick:
        argv.append("--quick")
    elif rigorous:
        argv.append("--rigorous")
    if no_baseline:
        argv.append("--no-baseline")
    if iterations:
        argv += ["--iterations", str(int(iterations))]
    if passes:
        argv += ["--passes", str(int(passes))]
    if not no_redact:
        argv += ["--redacted-out", str(out_path.with_suffix(".redacted.json"))]
    print(f"Running benchmarks locally (this may take a few minutes)...", file=sys.stderr)
    rc = _sp.run(argv, check=False).returncode
    if rc != 0:
        _print_error(f"Benchmark harness exited with code {rc}.")
        sys.exit(rc)
    redacted_path = None if no_redact else out_path.with_suffix(".redacted.json")
    if as_json:
        print(json.dumps({"results": str(out_path),
                          "redacted": None if no_redact else str(redacted_path)}))
        return

    _print_share_guidance(out_path, redacted_path) if not no_redact else \
        print(f"\nResults: {out_path}", file=sys.stderr)

    # --- Consent-gated submission offer (never transmits without an explicit yes) ---
    if no_redact:
        # No redacted artifact exists; never auto-transmit a full result to the public repo.
        if submit or yes:
            print("\nNot submitting: --no-redact produced no shareable (redacted) copy. Re-run "
                  "without --no-redact to contribute, or submit a redacted file manually.",
                  file=sys.stderr)
        return

    # Explicit consent via flag, else an interactive [y/N] offer (Enter == No).
    consented = submit or yes
    if not consented and interactive and not no_submit:
        try:
            resp = input("\nContribute this redacted result to help verify pubrun's "
                         "overhead claims? [y/N] ").strip().lower()
            consented = resp in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            consented = False

    if consented:
        # Redacted copy was just written by the harness, but verify before any network call.
        ok, detail = _verify_redacted(redacted_path)
        if not ok:
            _print_error(f"Not submitting: {detail}. Submit manually if you have verified it.")
            return
        if print_submission:
            _print_floor(repo, str(redacted_path), [], interactive)
        else:
            _submit_benchmark(str(redacted_path), repo, submit_method, gh_token, interactive)
    else:
        print(f'\nTo submit later: pubrun bench --submit-file "{redacted_path}"', file=sys.stderr)


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
) -> None:
    """List runs or inspect a specific run."""
    from pubrun.status import (
        find_run,
        render_inspect,
        render_short_list,
        render_verbose_list,
        scan_runs,
        filter_runs,
        close_out_crashed_run,
    )

    if run_id:
        # Inspect a specific run (recency index / id-prefix / dir-substring).
        from pubrun.status import AmbiguousRunSelectorError
        try:
            run_info = find_run(run_id, output_dir)
        except AmbiguousRunSelectorError as e:
            _emit_ambiguous_selector(e)
            sys.exit(1)
        if run_info is None:
            _print_error(f"No run found matching '{run_id}'.")
            sys.exit(1)
        if run_info.status == "crashed" and (run_info.run_dir / ".pubrun.lock").exists():
            close_out_crashed_run(run_info.run_dir, run_info.lock_data)
        print(render_inspect(run_info))
    else:
        # List all runs
        all_runs = scan_runs(output_dir)
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

        for r in runs:
            if r.status == "crashed" and (r.run_dir / ".pubrun.lock").exists():
                close_out_crashed_run(r.run_dir, r.lock_data)

        if verbose:
            print(render_verbose_list(runs))
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
) -> None:
    """Interactive or automatic cleanup of old run directories."""
    from pubrun.status import clean_runs

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
    )


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
    """Interleave stdout/stderr logs from one or more runs."""
    import re
    from pubrun.status import scan_runs, find_run

    TIMESTAMP_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\] (.*)$")

    if not run_ids:
        from pubrun.status import filter_runs
        all_runs = scan_runs(dir_path)
        has_filters = any(v is not None for v in (filter_str, status_filter, older_than, exit_code))
        run_limit = limit if limit is not None else (None if has_filters else 1)
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
        if not target_runs:
            _print_error("No runs match the filter criteria.")
            sys.exit(1)
    else:
        target_runs = []
        for rid in run_ids:
            run_info = find_run(rid, dir_path)
            if not run_info:
                _print_error(f"Run ID '{rid}' not found or ambiguous.")
                sys.exit(1)
            target_runs.append(run_info)

    # Calculate total size of stdout.log and stderr.log files
    total_size = 0
    for r in target_runs:
        for suffix in ("stdout.log", "stderr.log"):
            p = r.run_dir / suffix
            if p.exists():
                total_size += p.stat().st_size

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

    # Check if any log files exist and if they contain any timestamps
    has_any_timestamps = False
    for r in target_runs:
        for suffix in ("stdout.log", "stderr.log"):
            p = r.run_dir / suffix
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        for _ in range(50):  # Check first 50 lines to detect standard mode
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
        if has_any_timestamps:
            break

    out_file = None
    if output:
        try:
            out_file = open(output, "w", encoding="utf-8")
        except Exception as e:
            _print_error(f"Failed to open output file '{output}': {e}")
            sys.exit(1)

    def _parse_log_file(file_path: Path, run_id: Optional[str], stream: str, multiple_runs: bool) -> list:
        entries = []
        current_ts = ""
        prefix = f"[{run_id}][{stream}] " if multiple_runs else f"[{stream}] "
        if not file_path.exists():
            return entries
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line_str = line.rstrip("\r\n")
                    m = TIMESTAMP_RE.match(line_str)
                    if m:
                        ts, msg = m.groups()
                        current_ts = ts
                        # Keep the prefix and the entire original line (including its timestamp)
                        entries.append((ts, prefix + line_str))
                    else:
                        entries.append((current_ts, prefix + line_str))
        except Exception as e:
            print(f"Warning: Failed to read log file {file_path}: {e}", file=sys.stderr)
        return entries

    try:
        if not has_any_timestamps:
            print("Warning: Logs lack timestamps. Falling back to sequential concatenation. True interleaving requires capture_mode = \"standard\".", file=sys.stderr)
            for r in target_runs:
                for stream in ("stdout", "stderr"):
                    p = r.run_dir / f"{stream}.log"
                    if p.exists():
                        prefix = f"[{r.run_id}][{stream}] " if len(target_runs) > 1 else f"[{stream}] "
                        with open(p, "r", encoding="utf-8", errors="replace") as f:
                            for line in f:
                                out_line = prefix + line.rstrip("\r\n")
                                if out_file:
                                    out_file.write(out_line + "\n")
                                else:
                                    print(out_line)
        else:
            all_entries = []
            multiple_runs = len(target_runs) > 1
            for r in target_runs:
                for stream in ("stdout", "stderr"):
                    p = r.run_dir / f"{stream}.log"
                    if p.exists():
                        all_entries.extend(_parse_log_file(p, r.run_id, stream, multiple_runs))

            # Sort chronologically by timestamp, keeping the original read order
            # as a stable secondary key. Lines with an empty timestamp (content
            # before the first timestamped line, or partial final lines from a
            # killed process) thus stay in their original relative position
            # instead of being hoisted to the top. (IPD 20260705 EC-22.)
            indexed = list(enumerate(all_entries))
            indexed.sort(key=lambda pair: (pair[1][0], pair[0]))
            all_entries = [entry for _, entry in indexed]
            for _, line in all_entries:
                if out_file:
                    out_file.write(line + "\n")
                else:
                    print(line)
        if out_file:
            _out.ok(f"Combined logs written to {output}", stream=sys.stderr)
    except BrokenPipeError:
        pass
    finally:
        if out_file:
            out_file.close()


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
    print("\nIf GPU logs are missing here, your active Python environment")
    print("may not have permission to query `nvidia-smi` or NVML.")


def _run_tests() -> None:
    """Run the test suite and an end-to-end mock script for validation."""
    print("==================================================")
    print("        pubrun Pipeline Evaluation Mode         ")
    print("==================================================\n")

    if Path("tests").exists() and Path("tox.ini").exists():
        _out.info("Source repository detected. Running PyTest matrix...", stream=sys.stdout)
        try:
            subprocess.run(["python", "-m", "pytest", "tests/", "-q"])
        except Exception:
            _out.warn("PyTest execution failed.", stream=sys.stdout)

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

        result = subprocess.run([sys.executable, str(script_path)], env=env, capture_output=True, text=True, cwd=td)

        if result.returncode != 0:
            _out.fail(f"Mock Evaluation Failed. Exit Code: {result.returncode}")
            return

        _out.ok("Mock script executed without crashing.")

        runs_dir = Path(td) / "runs"
        if not runs_dir.exists():
            return

        run_folders = list(runs_dir.iterdir())
        if not run_folders:
            return

        active_run = run_folders[0]
        manifest_p = active_run / "manifest.json"

        if not manifest_p.exists():
            return

        try:
            manifest_data = json.loads(manifest_p.read_text(encoding="utf-8"))
            rcs = manifest_data.get("subprocesses", [])
            _out.ok(f"Subprocess spy captured {len(rcs)} shell commands.")
            _out.ok("Validation complete.")
        except Exception as e:
            pass


def _run_bug_report() -> None:
    """Guide the user to report a bug or request a feature on GitHub."""
    import webbrowser
    import platform
    import sys
    import time
    from pubrun.__init__ import __version__

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
    has_f = any("-f" in getattr(action, "option_strings", []) for action in parser._actions)
    if has_f:
        parser.add_argument("--filter", type=str, default=None, metavar="QUERY", help="Filter runs by script name, arguments, or run ID (supports regex or plain string).")
    else:
        parser.add_argument("-f", "--filter", type=str, default=None, metavar="QUERY", help="Filter runs by script name, arguments, or run ID (supports regex or plain string).")
    parser.add_argument("-F", "--not-filter", type=str, default=None, metavar="QUERY", help="Exclude runs matching script name, arguments, or run ID.")
    parser.add_argument("-s", "--status", type=str, default=None, metavar="STATUS", help="Comma-separated status filter (e.g. 'completed,failed,crashed').")
    parser.add_argument("-S", "--not-status", type=str, default=None, metavar="STATUS", help="Comma-separated status exclusion filter (e.g. 'completed').")
    parser.add_argument("--older-than", type=str, default=None, metavar="AGE", help="Only consider runs older than AGE (e.g. '7d', '24h', '30' for 30 days).")
    parser.add_argument("--exit-code", type=int, default=None, metavar="CODE", help="Only consider runs with this exit code.")
    if include_limit:
        parser.add_argument("-n", "--limit", type=int, default=None, metavar="LIMIT", help="Limit the number of runs to consider.")


def main() -> None:
    """CLI entrypoint for the ``pubrun`` command."""
    # Handle global --no-color flag regardless of position
    # But do not strip it if it is part of the command run by 'pubrun run'
    subcommands = {"report", "methods", "rerun", "diff", "meta", "status", "clean", "combined", "cite", "run", "ui", "tui", "gui", "show", "res", "resources", "cpu", "mem"}
    run_idx = -1
    for idx, arg in enumerate(sys.argv):
        if arg in subcommands:
            if arg == "run":
                run_idx = idx
            break

    no_color_present = False
    if run_idx != -1:
        if "--no-color" in sys.argv[:run_idx]:
            no_color_present = True
            sys.argv = [arg for i, arg in enumerate(sys.argv) if i >= run_idx or arg != "--no-color"]
    else:
        if "--no-color" in sys.argv:
            no_color_present = True
            sys.argv = [arg for arg in sys.argv if arg != "--no-color"]

    # Support placing run ID / prefix / path before the subcommand
    # (e.g. `pubrun 16528343 cpu` -> `pubrun cpu 16528343`)
    if len(sys.argv) > 2 and sys.argv[1] not in subcommands and not sys.argv[1].startswith("-"):
        for idx in range(2, len(sys.argv)):
            if sys.argv[idx] in subcommands:
                cmd = sys.argv.pop(idx)
                sys.argv.insert(1, cmd)
                break

    # Translate 'help' and subcommand translations
    if len(sys.argv) > 1:
        if sys.argv[1] == "help":
            if len(sys.argv) > 2 and sys.argv[2] in subcommands:
                sys.argv = [sys.argv[0], sys.argv[2], "--help"]
            else:
                sys.argv = [sys.argv[0], "--help"]
        elif sys.argv[1] in subcommands and len(sys.argv) > 2 and sys.argv[2] == "help":
            sys.argv = [sys.argv[0], sys.argv[1], "--help"]

    prog_name = Path(sys.argv[0]).name if sys.argv[0] else "pubrun"
    if prog_name not in ("pubrun", "pbr"):
        prog_name = "pubrun"

    # Easter egg
    if len(sys.argv) >= 2 and prog_name == "pbr" and sys.argv[1] == "me":
        print("ASAP")
        sys.exit(0)

    # Primary commands (excluding aliases) for clean error messages.
    _PRIMARY_COMMANDS: list = []

    class _SubcommandAwareArgumentParser(argparse.ArgumentParser):
        def error(self, message: str) -> None:
            subcommand = None
            subparsers_actions = [
                act for act in self._actions
                if isinstance(act, argparse._SubParsersAction)
            ]
            if subparsers_actions:
                for arg in sys.argv[1:]:
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
                import re
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
        description=f"{prog_name}: Zero-dependency execution telemetry and publication engine.",
        epilog=f"Use '{prog_name} <command> --help' for detailed information on a specific command."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=(
            f"pubrun {__version__}\n"
            "Based on the original pubrun by Gabriele G. R. Fariello "
            "(https://github.com/fariello/pubrun).\n"
            "Licensed under Apache-2.0; see the NOTICE file for the required attribution."
        ),
    )
    parser.add_argument("--no-color", action="store_true", help="Suppress ANSI color output globally.")

    subparsers = parser.add_subparsers(dest="command", title="Available core commands", metavar="<command>")

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
        help="File a bug report or request a feature.",
        description="Opens the GitHub issue tracker and prints environment diagnostics for copy-pasting.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    feedback_parser = subparsers.add_parser(
        "feedback",
        help="Send feedback about pubrun.",
        description="Opens the GitHub issue tracker and prints environment diagnostics for copy-pasting.",
        formatter_class=argparse.RawDescriptionHelpFormatter
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
        help="Diagnose a completed run: what was captured, what wasn't, and how to capture more.",
        description="Report-only, post-hoc diagnosis of a completed run's manifest: recorded "
                    "I/O/RAM/load/filesystem signals, a capture-completeness assessment (what "
                    "provenance was NOT captured and why), and how to enable more next time "
                    "with honest performance trade-offs. Prints a glaring banner when the "
                    "inspecting host differs from where the run executed (e.g. HPC head node "
                    "vs compute node).",
        epilog=f"Examples:\n  {prog_name} inspect\n  {prog_name} inspect runs/pubrun-XYZ --show-suggestions\n  {prog_name} inspect -f train.py",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    inspect_parser.add_argument("run_dir", type=str, nargs="?", help="Run directory to inspect. Defaults to the most recent matching run.")
    inspect_parser.add_argument("--show-suggestions", "-v", action="store_true", help="Show per-item detail and how to capture more (with perf trade-offs).")
    inspect_parser.add_argument("--json", action="store_true", dest="as_json", help="Emit findings as JSON (always full detail).")
    inspect_parser.add_argument("--strict", action="store_true", help="Exit non-zero if any warning fired.")
    _add_run_filter_args(inspect_parser, include_limit=False)

    # ---------------- Bench Subparser ----------------
    bench_parser = subparsers.add_parser(
        "bench",
        help="Run the pubrun overhead benchmark suite (auto-detects Slurm on HPC).",
        description="Friendly front-end over the benchmark harness. Runs locally by "
                    "default; on an HPC login node with Slurm it OFFERS to submit to a "
                    "compute node (never submits without confirmation). Writes a "
                    "redacted, shareable copy by default and prints how to contribute it. "
                    "Requires a source checkout (the benchmark tooling is not shipped in "
                    "the pip package).",
        epilog=f"Examples:\n  {prog_name} bench --quick\n  {prog_name} bench --local --passes 3\n"
               f"  {prog_name} bench --submit\n  {prog_name} bench --submit-file runs.redacted.json",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    bench_speed = bench_parser.add_mutually_exclusive_group()
    bench_speed.add_argument("--quick", action="store_true", help="Fast smoke run (baseline + 2 passes x 15 iterations).")
    bench_speed.add_argument("--full", action="store_true", help="Standard run (baseline + 3 passes x 30 iterations). This is the default; the flag is for clarity.")
    bench_speed.add_argument("--rigorous", action="store_true", help="Tight-CI run (baseline + 5 passes x 50 iterations); can take many minutes.")
    bench_parser.add_argument("--no-baseline", action="store_true", help="Skip the initial uncaptured baseline pass (the pubrun-absent reference sweep).")
    bench_parser.add_argument("--iterations", type=int, default=None, help="Override iterations per scenario (takes precedence over --quick/--full).")
    bench_parser.add_argument("--passes", type=int, default=None, help="Override the number of measured scenario sweeps (default depends on the tier: quick=2, full=3, rigorous=5).")
    bench_group = bench_parser.add_mutually_exclusive_group()
    bench_group.add_argument("--local", action="store_true", help="Run here even if an HPC scheduler is detected.")
    bench_group.add_argument("--submit", action="store_true", help="Submit to the detected scheduler (no prompt); off HPC, contribute the result without prompting.")
    bench_parser.add_argument("--scheduler", choices=("auto", "slurm", "pbs", "lsf", "sge", "local"),
                              default="auto", help="HPC scheduler to submit to (default: auto-detect; 'local' forces a local run).")
    bench_parser.add_argument("-y", "--yes", action="store_true", help="Assume yes to the submit/contribute prompt.")
    bench_parser.add_argument("--no-redact", action="store_true", help="Do NOT write a redacted share copy (full detail only).")
    bench_parser.add_argument("--json", action="store_true", dest="as_json", help="Emit the result/redacted paths as JSON.")
    # --- result submission (consent-gated; never transmits without an explicit yes) ---
    bench_parser.add_argument("--submit-file", metavar="FILE", default=None,
                              help="Submit an existing (redacted) result file to the pubrun-benchmarks "
                                   "repo, without running a benchmark. For 'oh, I meant yes' recovery and HPC.")
    bench_parser.add_argument("--no-submit", action="store_true", help="Do not offer to contribute the result.")
    bench_parser.add_argument("--submit-method", choices=("gh", "http", "print"), default=None,
                              help="Force a single submission method instead of probing (gh -> http -> print).")
    bench_parser.add_argument("--gh-repo", metavar="OWNER/NAME", default=None,
                              help=f"Target GitHub repo for submission (default {_DEFAULT_BENCH_REPO}).")
    bench_parser.add_argument("--gh-token", metavar="TOKEN", default=None,
                              help="GitHub token for the HTTP submission path (else $GITHUB_TOKEN/$GH_TOKEN or `gh auth token`).")
    bench_parser.add_argument("--print-submission", action="store_true",
                              help="Print a ready-to-paste submission instead of transmitting (offline/power-user).")

    # ---------------- Clean Subparser ----------------
    clean_parser = subparsers.add_parser(
        "clean",
        help="Interactively delete old run directories.",
        description="Interactively delete old run directories. By default, lists candidates and prompts for confirmation.",
        epilog=f"Examples:\n  {prog_name} clean\n  {prog_name} clean --older-than 7d --yes\n  {prog_name} clean --status completed,ghost",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    clean_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help="Override the output directory to scan.")
    clean_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt (delete all matching runs).")
    clean_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting.")
    _add_run_filter_args(clean_parser)

    # ---------------- Combined Subparser ----------------
    combined_parser = subparsers.add_parser(
        "combined",
        help="Interleave stdout/stderr logs from one or more runs.",
        description="Interleave stdout/stderr logs from one or more runs.",
        epilog=f"Examples:\n  {prog_name} combined\n  {prog_name} combined run-A run-B --output combined.log",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    combined_parser.add_argument("run_ids", type=str, nargs="*", help="Run IDs (or prefixes) to combine. Defaults to the latest run if omitted.")
    combined_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help="Override the output directory to scan (default: configured output_dir or ./runs).")
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
        epilog=f"Examples:\n  {prog_name} cpu\n  {prog_name} cpu runs/pubrun-XYZ",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    cpu_parser.add_argument("run_dir", type=str, nargs="?", help="Directory path to an existing pubrun artifact. Automatically defaults to the most recent run if omitted.")
    cpu_parser.add_argument("--average", action="store_true", help="Plot average/mean values instead of the default maximum values.")
    cpu_parser.add_argument("-l", "--last", type=str, default=None, help="Only show the last X minutes, hours, or seconds of data (e.g. '10m', '2h', '30s').")
    cpu_parser.add_argument("-w", "--width", type=int, default=None, help="Override chart width in columns.")
    _add_run_filter_args(cpu_parser, include_limit=False)

    # ---------------- Diff Subparser ----------------
    diff_parser = subparsers.add_parser(
        "diff",
        help="Compare two execution traces and highlight differences.",
        description="Compare two execution traces and highlight differences.",
        epilog=f"Examples:\n  {prog_name} diff runs/pubrun-A runs/pubrun-B\n  {prog_name} diff runs/pubrun-A runs/pubrun-B --deep --same",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    diff_parser.add_argument("run_dirs", type=str, nargs="*", help="Run directories to compare. If omitted, diffs the last two runs. If one is provided, diffs it against the most recent different run.")
    diff_parser.add_argument("--export", type=str, nargs="?", const=True, help="Export flattened manifests to files ('txt' or 'json').")
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
        epilog=f"Examples:\n  {prog_name} mem\n  {prog_name} mem runs/pubrun-XYZ",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mem_parser.add_argument("run_dir", type=str, nargs="?", help="Directory path to an existing pubrun artifact. Automatically defaults to the most recent run if omitted.")
    mem_parser.add_argument("--average", action="store_true", help="Plot average/mean values instead of the default maximum values.")
    mem_parser.add_argument("-l", "--last", type=str, default=None, help="Only show the last X minutes, hours, or seconds of data (e.g. '10m', '2h', '30s').")
    mem_parser.add_argument("-w", "--width", type=int, default=None, help="Override chart width in columns.")
    _add_run_filter_args(mem_parser, include_limit=False)

    # ---------------- Meta Subparser ----------------
    meta_parser = subparsers.add_parser(
        "meta",
        help="Generate a standalone meta.json environment snapshot.",
        description="Generate a standalone meta.json environment snapshot for HPC parent-child hydration.",
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
        description="Generate publication-ready 'Computational Methods' paragraphs.",
        epilog=f"Examples:\n  {prog_name} methods\n  {prog_name} methods runs/pubrun-XYZ --format latex",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    methods_parser.add_argument("run_dir", type=str, nargs="?", help="Directory path to an existing pubrun artifact. Automatically defaults to the most recent run if omitted.")
    methods_parser.add_argument("--format", type=str, choices=["markdown", "latex"], default="markdown", help="Output format: markdown or latex.")
    methods_parser.add_argument("--all", action="store_true", help="Aggregate ALL matching runs into one methods paragraph (with a variance note where they differ), instead of the single most-recent run. Combine with -f/-F/-s/-S/-n to bound the set.")
    _add_run_filter_args(methods_parser, include_limit=True)

    # ---------------- Hidden Report Subparser ----------------
    report_parser = subparsers.add_parser(
        "report",
        help=argparse.SUPPRESS,
        description="Analyze and display diagnostic telemetry from a specific run.",
        epilog=f"Examples:\n  {prog_name} report\n  {prog_name} report runs/pubrun-XYZ\n  {prog_name} report env",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    report_parser.add_argument("run_dir", type=str, nargs="?", help="Run directory (e.g., runs/pubrun-XYZ). Defaults to the most recent run.")
    report_parser.add_argument("section", type=str, nargs="?", help="Optional section to view (e.g. 'logs', 'env', 'packages').")

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
        help="Print the shell command needed to replicate a run.",
        description="Print the shell command needed to replicate a run.",
        epilog=f"Examples:\n  {prog_name} rerun\n  {prog_name} rerun runs/pubrun-XYZ",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    rerun_parser.add_argument("run_dir", type=str, nargs="?", help="Directory path to an existing pubrun artifact. Automatically defaults to the most recent run if omitted.")
    _add_run_filter_args(rerun_parser, include_limit=False)

    # ---------------- Resources Subparser ----------------
    res_parser = subparsers.add_parser(
        "res",
        aliases=["resources"],
        help="Display memory and CPU utilization charts over the run lifecycle.",
        description="Display memory and CPU utilization charts over the run lifecycle.",
        epilog=f"Examples:\n  {prog_name} res\n  {prog_name} res runs/pubrun-XYZ",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    res_parser.add_argument("run_dir", type=str, nargs="?", help="Directory path to an existing pubrun artifact. Automatically defaults to the most recent run if omitted.")
    res_parser.add_argument("--average", action="store_true", help="Plot average/mean values instead of the default maximum values.")
    res_parser.add_argument("-l", "--last", type=str, default=None, help="Only show the last X minutes, hours, or seconds of data (e.g. '10m', '2h', '30s').")
    res_parser.add_argument("-w", "--width", type=int, default=None, help="Override chart width in columns.")
    _add_run_filter_args(res_parser, include_limit=False)

    # ---------------- Run Subparser ----------------
    run_parser = subparsers.add_parser(
        "run",
        help="Run a command with a specific pubrun import mode.",
        description="Spawn a child process with PUBRUN_IMPORT_MODE set. Useful for CI, shell scripts, and HPC workflows where source code should remain unchanged.",
        epilog=f"Examples:\n  {prog_name} run --mode minimal -- python train.py --epochs 10\n  {prog_name} run --mode noconsole -- python evaluate.py",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    run_parser.add_argument("--mode", type=str, choices=["auto", "noauto", "nopatch", "noconsole", "minimal", "full"], default="auto", help="Import mode for the child process (default: auto).")
    run_parser.add_argument("command_args", nargs=argparse.REMAINDER, metavar="-- COMMAND", help="Command to execute (use -- to separate pubrun flags from the target command).")

    # ---------------- Show Subparser ----------------
    show_parser = subparsers.add_parser(
        "show",
        help="Analyze and display diagnostic telemetry from a specific run.",
        description="Analyze and display diagnostic telemetry from a specific run.",
        epilog=f"Examples:\n  {prog_name} show\n  {prog_name} show runs/pubrun-XYZ\n  {prog_name} show runs/pubrun-XYZ env\n  {prog_name} show env\n  {prog_name} show config\n  {prog_name} show run config 1\n  {prog_name} show default config",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    show_parser.add_argument("run_dir", type=str, nargs="?", help="Run directory (e.g., runs/pubrun-XYZ). Defaults to the most recent run. Also the keyword 'config' (current resolved config), or 'run'/'default' in the `show <run|default> config` forms.")
    show_parser.add_argument("section", type=str, nargs="?", help="Optional section to view ('logs', 'env', 'packages'), or 'config' in the `show run config` / `show default config` forms.")
    show_parser.add_argument("config_extra", type=str, nargs="?", help="Optional run selector for `pubrun show run config <id>` (recency index, id prefix, or path). Defaults to the most recent run.")

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
        epilog=f"Examples:\n  {prog_name} status\n  {prog_name} status --status failed,crashed\n  {prog_name} status --limit 5\n  {prog_name} status -f train.py",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    status_parser.add_argument("run_id", type=str, nargs="?", help="Run ID (or prefix) to inspect in detail. If omitted, lists all runs.")
    status_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help="Override the output directory to scan (default: configured output_dir or ./runs).")
    status_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed information for each run in the listing.")
    status_parser.add_argument("--utc", action="store_true", help="Display timestamps in UTC instead of local time.")
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
    ui_parser.add_argument("--dir", type=str, default=None, metavar="PATH", help="Override the output directory to scan (default: configured output_dir or ./runs).")

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
    parser.add_argument("--info", action="store_true", help="Display runtime diagnostics: Python version, pubrun version, import mode, invocation, and hardware/capture capabilities. (To see resolved configuration, use `pubrun show config`.)")
    parser.add_argument("--run-tests", action="store_true", help="Run the built-in test suite and a mock end-to-end script.")

    # UX-01: Build the primary commands list (excluding aliases) for clean errors.
    _known_aliases = {"tui", "gui"}
    _PRIMARY_COMMANDS.extend(
        name for name in subparsers.choices if name not in _known_aliases
    )

    args = parser.parse_args()
    if no_color_present:
        setattr(args, "no_color", True)
    if getattr(args, "no_color", False):
        os.environ["NO_COLOR"] = "1"

    # Timestamp display timezone: local by default, UTC when --utc is given
    # (status/show). Timestamps are always stored as UTC epochs. (IPD EC-17.)
    if getattr(args, "utc", False):
        from pubrun.status import set_display_utc
        set_display_utc(True)

    # `pubrun show config` family (positional grammar), intercepted BEFORE run resolution so
    # the keyword `config` is not mistaken for a run selector. Three forms:
    #   show config                -> current resolved config (run_dir == "config", no section)
    #   show default config        -> shipped defaults      (run_dir == "default", section == "config")
    #   show run config [<id>]     -> a past run's config    (run_dir == "run",     section == "config")
    # Precedence note: these keyword forms win over a run whose id literally starts with
    # config/run/default; such a run must be selected by full id or path.
    if args.command in {"show", "report"}:
        _rd = getattr(args, "run_dir", None)
        _sec = getattr(args, "section", None)
        _extra = getattr(args, "config_extra", None)  # optional run id after `show run config`
        if _rd == "config" and _sec is None:
            _run_show_config("current", show_all=getattr(args, "all", False))
            return
        if _rd == "default" and _sec == "config":
            _run_show_config("default")
            return
        if _rd == "run" and _sec == "config":
            _run_show_config("run", run_selector=_extra, show_all=getattr(args, "all", False))
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
        if not run_dir:
            from pubrun.status import scan_runs, filter_runs
            all_runs = scan_runs()
            matched = filter_runs(
                all_runs,
                filter_str=getattr(args, "filter", None),
                status_filter=getattr(args, "status", None),
                limit=getattr(args, "limit", None),
                older_than=getattr(args, "older_than", None),
                exit_code=getattr(args, "exit_code", None),
                not_filter_str=getattr(args, "not_filter", None),
                not_status_filter=getattr(args, "not_status", None),
            )
            if not matched:
                _print_error("No runs match the filter criteria.")
                sys.exit(1)
            for idx, r in enumerate(matched):
                if idx > 0:
                    print("\n")
                _run_report(str(r.run_dir), args.depth, getattr(args, "section", None), utc=getattr(args, "utc", False))
        else:
            _run_report(run_dir, args.depth, getattr(args, "section", None), utc=getattr(args, "utc", False))
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
            getattr(args, "no_redact", False),
            submit_file=getattr(args, "submit_file", None),
            submit_method=getattr(args, "submit_method", None),
            gh_repo=getattr(args, "gh_repo", None),
            gh_token=getattr(args, "gh_token", None),
            print_submission=getattr(args, "print_submission", False),
            no_submit=getattr(args, "no_submit", False),
            scheduler=getattr(args, "scheduler", "auto"),
            rigorous=getattr(args, "rigorous", False),
            no_baseline=getattr(args, "no_baseline", False),
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
        _run_bug_report()
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
        # Spawn child process with PUBRUN_IMPORT_MODE set
        import subprocess as _sp
        import signal as _signal
        child_env = {**os.environ, "PUBRUN_IMPORT_MODE": args.mode}
        child_proc = None
        try:
            child_proc = _sp.Popen(cmd_args, env=child_env)

            # Forward SIGTERM to child so it isn't orphaned (P2-S3)
            def _forward_sigterm(signum, frame):
                if child_proc and child_proc.poll() is None:
                    child_proc.terminate()
            if hasattr(_signal, "SIGTERM"):
                _signal.signal(_signal.SIGTERM, _forward_sigterm)

            rc = child_proc.wait()
            # Translate negative returncode (signal death) to 128+N (P2-B4)
            if rc < 0:
                sys.exit(128 + abs(rc))
            sys.exit(rc)
        except (FileNotFoundError, PermissionError) as e:
            _print_error(f"Cannot execute command: {e}")
            sys.exit(127)
        except KeyboardInterrupt:
            if child_proc and child_proc.poll() is None:
                child_proc.terminate()
                child_proc.wait()
            sys.exit(130)

    elif args.command == "init":
        dest = getattr(args, "dest", ".pubrun.toml")
        _create_config(dest)
        print()
        print("Getting started:")
        print("  1. Add 'import pubrun' at the top of your script.")
        print("  2. Run your script normally — pubrun captures everything.")
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
            except KeyboardInterrupt:
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
            from pubrun.status import scan_runs
            runs = scan_runs()
            if runs:
                print(f"\nFound {len(runs)} run(s) in the output directory. Run '{prog_name} status' to view them.")
            else:
                print("\nNo runs found in the output directory.")
        except Exception:
            pass


if __name__ == "__main__":
    main()
