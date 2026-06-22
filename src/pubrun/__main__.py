import argparse
import sys
import os
import json
import time
import tempfile
import subprocess
from pathlib import Path
from typing import List, Optional

from pubrun import __version__

def _print_error(message: str) -> None:
    if os.environ.get("NO_COLOR", ""):
        print(f"[ERRO] {message}", file=sys.stderr)
    else:
        print(f"\033[31m[ERRO]\033[0m {message}", file=sys.stderr)


def _print_warn(message: str) -> None:
    if os.environ.get("NO_COLOR", ""):
        print(f"[WARN] {message}", file=sys.stderr)
    else:
        print(f"\033[33m[WARN]\033[0m {message}", file=sys.stderr)


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
        print(f"[OK] Successfully created configuration at: {target_path}")
        
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
        # Resolve via find_run first
        try:
            from pubrun.status import find_run
            run_info = find_run(run_dir)
            if run_info:
                run_path = run_info.run_dir
            else:
                run_path = Path(run_dir)
        except Exception:
            run_path = Path(run_dir)

        manifest_path = run_path if (run_path.is_file() and run_path.name == "manifest.json") else (run_path / "manifest.json")

        if manifest_path.exists():
            return str(manifest_path)

        # If manifest doesn't exist, check if there is a lock file in that folder
        lock_path = run_path / ".pubrun.lock" if run_path.is_dir() else (run_path.parent / ".pubrun.lock")
        if lock_path.exists():
            raise RunInProgressOrCrashedError(run_path if run_path.is_dir() else run_path.parent)

        raise FileNotFoundError(f"Could not find manifest file at '{manifest_path}'.")
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
            print(f"[*] Auto-detected matching run: {latest_run}", file=sys.stderr)
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
) -> None:
    """Generate and print an academic 'Computational Methods' paragraph."""
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
                print(f"[WARNING] {w}", file=sys.stderr)
        
        # Dispatch to structural compilers
        text = generate_report(manifest, format_type)
        print("--- Generated Computational Methods Section ---")
        print(text)
        print("-----------------------------------------------\n")
    except RunInProgressOrCrashedError as e:
        status = e.run_info.status if e.run_info else "crashed/running"
        _print_error(f"Run '{e.run_dir.name}' is currently {status} and does not have a manifest.json.")
        sys.exit(1)
    except FileNotFoundError:
        _print_error("Could not find manifest file.")
        sys.exit(1)
    except Exception as e:
        _print_error(f"Failed to generate methods section: {e}")
        sys.exit(1)


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


def _run_diff(run_dirs: List[str], export_format: str, no_color: bool, wrap_config: Optional[bool] = None, max_length: Optional[int] = None, depth: str = "basic", show_same: Optional[bool] = None) -> None:
    """Run the semantic diff engine comparing two execution traces."""
    try:
        from pubrun.report.utils import hydrate_manifest
        from pubrun.config import resolve_config
        from pubrun.analysis.diff import compare_manifests, export_manifest
        from pubrun.analysis.render import print_diff
        from pubrun.status import scan_runs, find_run

        all_runs = scan_runs()
        valid_runs = [r for r in all_runs if (r.run_dir / "manifest.json").exists()]

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
                _print_error("Only one run was provided, and no other runs with a manifest.json were found to compare against.")
                sys.exit(1)
            
            run_dir_b = str(run_dir_b_path)
            print(f"[*] Comparing {run_dir_a_path.name} against most recent other run: {run_dir_b_path.name}", file=sys.stderr)
        else:
            # 0 runs provided: diff the last two runs (second most recent as baseline A, most recent as target B)
            if len(valid_runs) < 2:
                _print_error(f"Need at least 2 runs with manifest.json to perform default diff (found {len(valid_runs)}).")
                sys.exit(1)
            run_dir_a = str(valid_runs[1].run_dir)
            run_dir_b = str(valid_runs[0].run_dir)
            print(f"[*] Auto-detected last two runs for comparison: {valid_runs[1].run_dir.name} vs {valid_runs[0].run_dir.name}", file=sys.stderr)

        manifest_path_a = _get_manifest_path(run_dir_a)
        manifest_path_b = _get_manifest_path(run_dir_b)

        with open(manifest_path_a, "r", encoding="utf-8") as f:
            manifest_a = json.load(f)

        with open(manifest_path_b, "r", encoding="utf-8") as f:
            manifest_b = json.load(f)

        manifest_a, warn_a = hydrate_manifest(manifest_path_a, manifest_a)
        manifest_b, warn_b = hydrate_manifest(manifest_path_b, manifest_b)

        for w in (warn_a or []) + (warn_b or []):
            print(f"[WARNING] {w}", file=sys.stderr)

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

            print(f"[OK] Successfully exported semantic baseline A to: {out_a}")
            print(f"[OK] Successfully exported semantic target B to: {out_b}")
        else:
            diff_report = compare_manifests(manifest_a, manifest_b, ignores, show_same=ss_target, depth=depth)
            wrap_target = wrap_config if wrap_config is not None else conf.get("wrap", True)
            mlen_target = max_length if max_length is not None else conf.get("max_string_length", 300)
            print_diff(diff_report, no_color=no_color, wrap=wrap_target, max_length=mlen_target, depth=depth)

    except RunInProgressOrCrashedError as e:
        status = e.run_info.status if e.run_info else "crashed/running"
        _print_error(f"Run '{e.run_dir.name}' is currently {status} and does not have a manifest.json.")
        sys.exit(1)
    except Exception as e:
        _print_error(f"Failed to generate diff report: {e}")
        sys.exit(1)



def _run_report(run_dir: str, depth: str) -> None:
    """Print a human-readable diagnostic report for a recorded run."""
    try:
        from pubrun.report.diagnostics import print_report
        manifest_path = _get_manifest_path(run_dir)
        print_report(manifest_path, depth)

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
                    completed_runs.append((d, d.stat().st_mtime))
                    
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
    """Print a formatted academic citation for pubrun."""
    style = style.lower()
    if style == "apa":
        print("Fariello, G. (2026). pubrun: Low-friction execution provenance for Python research. Journal of Open Source Software, (In Submission).")
    elif style == "mla":
        print("Fariello, Gabriele. \"pubrun: Low-friction execution provenance for Python research.\" Journal of Open Source Software, (In Submission).")
    elif style == "chicago":
        print("Fariello, Gabriele. 2026. \"pubrun: Low-friction execution provenance for Python research.\" Journal of Open Source Software, (In Submission).")
    elif style == "bibtex":
        print("@article{fariello_pubrun_2026,\n  author    = {Gabriele Fariello},\n  title     = {pubrun: Low-friction execution provenance for Python research},\n  journal   = {Journal of Open Source Software},\n  note      = {In Submission},\n  year      = {2026}\n}")
    else:
        _print_error(f"Unknown citation style '{style}'. Supported styles: apa, mla, chicago, bibtex.")
        sys.exit(1)


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
        # Inspect a specific run
        run_info = find_run(run_id, output_dir)
        if run_info is None:
            _print_error(f"No run found matching '{run_id}'.")
            sys.exit(1)
        if run_info.status == "crashed" and (run_info.run_dir / ".pubrun.lock").exists():
            close_out_crashed_run(run_info.run_dir, run_info.lock_data)
        print(render_inspect(run_info))
    else:
        # List all runs
        runs = scan_runs(output_dir)
        runs = filter_runs(
            runs,
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
            print(render_short_list(runs))


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
            
            # Sort chronologically by timestamp
            all_entries.sort(key=lambda x: x[0])
            for _, line in all_entries:
                if out_file:
                    out_file.write(line + "\n")
                else:
                    print(line)
        if out_file:
            print(f"[OK] Combined logs written to {output}", file=sys.stderr)
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
        print("[*] Source repository detected. Running PyTest matrix...")
        try:
            subprocess.run(["python", "-m", "pytest", "tests/", "-q"])
        except Exception:
            print("[WARN] PyTest execution failed.")
            
    print("\n[*] Executing Native End-to-End Mock Script...")
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
            print(f"[FAIL] Mock Evaluation Failed. Exit Code: {result.returncode}")
            return
            
        print("[OK] Mock script executed without crashing.")
        
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
            print(f"[OK] Subprocess spy captured {len(rcs)} shell commands.")
            print(f"[OK] Validation complete.")
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
    subcommands = {"report", "methods", "rerun", "diff", "meta", "status", "clean", "combined", "cite", "run", "ui", "tui", "gui"}
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
                
            super().error(message)

    parser = _SubcommandAwareArgumentParser(
        prog=prog_name,
        description=f"{prog_name}: Zero-dependency execution telemetry and publication engine.",
        epilog=f"Use '{prog_name} <command> --help' for detailed information on a specific command."
    )
    parser.add_argument("--version", action="version", version=f"pubrun {__version__}")
    parser.add_argument("--no-color", action="store_true", help="Suppress ANSI color output globally.")
    
    subparsers = parser.add_subparsers(dest="command", title="Available core commands", metavar="<command>")
    
    # ---------------- Report Subparser ----------------
    report_parser = subparsers.add_parser(
        "report",
        help="Analyze and display diagnostic telemetry from a specific run.",
        description="Analyze and display diagnostic telemetry from a specific run.",
        epilog=f"Examples:\n  {prog_name} report\n  {prog_name} report runs/pubrun-XYZ\n  {prog_name} report --deep runs/pubrun-XYZ",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    report_parser.add_argument("run_dirs", type=str, nargs="*", help="One or more run directories (e.g., runs/pubrun-XYZ). Defaults to the most recent run in ./runs/.")
    
    depth_group_1 = report_parser.add_mutually_exclusive_group()
    depth_group_1.add_argument("--basic", action="store_const", dest="depth", const="basic", help="Timing and outcome only.")
    depth_group_1.add_argument("--standard", action="store_const", dest="depth", const="standard", help="Hardware, Git, Python, and dependency summary (default).")
    depth_group_1.add_argument("--deep", action="store_const", dest="depth", const="deep", help="Full environment variables and complete package list.")
    report_parser.set_defaults(depth="standard")
    _add_run_filter_args(report_parser)

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
    _add_run_filter_args(methods_parser, include_limit=False)

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

    
    # Wrap config logic
    wrap_group = diff_parser.add_mutually_exclusive_group()
    wrap_group.add_argument("--wrap", action="store_true", default=None, help="Wrap long strings across multiple lines instead of truncating.")
    wrap_group.add_argument("--no-wrap", action="store_false", dest="wrap", default=None, help="Force ellipsis truncation for long values.")
    
    diff_parser.add_argument("--max-length", type=int, default=None, help="Max characters per value before truncation.")

    # Depth logic
    diff_depth = diff_parser.add_mutually_exclusive_group()
    diff_depth.add_argument("--basic", action="store_const", dest="depth", const="basic", help="Structural changes only, filtering most metrics.")
    diff_depth.add_argument("--standard", action="store_const", dest="depth", const="standard", help="Include standard telemetry, ignoring jitter metrics (default).")
    diff_depth.add_argument("--deep", action="store_const", dest="depth", const="deep", help="Unfiltered comparison of all captured data.")
    diff_parser.set_defaults(depth="standard")

    # Identical keys logic
    diff_same = diff_parser.add_mutually_exclusive_group()
    diff_same.add_argument("--same", action="store_true", default=None, help="Show keys that are identical between both runs.")
    diff_same.add_argument("--no-same", action="store_false", dest="same", default=None, help="Hide keys that are identical between both runs.")
    
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
    _add_run_filter_args(status_parser)

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
    combined_parser.add_argument("-f", "--force", action="store_true", help="Force execution for files > 500 MB.")
    _add_run_filter_args(combined_parser)

    # ---------------- Cite Subparser ----------------
    cite_parser = subparsers.add_parser(
        "cite",
        help="Generate a formatted academic citation for pubrun.",
        description="Generate a formatted academic citation for pubrun.",
        epilog=f"Examples:\n  {prog_name} cite\n  {prog_name} cite --style bibtex",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    cite_parser.add_argument("--style", type=str, choices=["apa", "mla", "chicago", "bibtex"], default="apa", help="Citation format (default: apa).")

    # ---------------- Run Subparser ----------------
    run_parser = subparsers.add_parser(
        "run",
        help="Run a command with a specific pubrun import mode.",
        description="Spawn a child process with PUBRUN_IMPORT_MODE set. Useful for CI, shell scripts, and HPC workflows where source code should remain unchanged.",
        epilog=f"Examples:\n  {prog_name} run --mode minimal -- python train.py --epochs 10\n  {prog_name} run --mode noconsole -- python evaluate.py",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    run_parser.add_argument("--mode", type=str, choices=["auto", "noauto", "nopatch", "noconsole", "minimal"], default="auto", help="Import mode for the child process (default: auto).")
    run_parser.add_argument("command_args", nargs=argparse.REMAINDER, metavar="-- COMMAND", help="Command to execute (use -- to separate pubrun flags from the target command).")
    
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
    
    # ---------------- Bug Report Subparser ----------------
    bug_parser = subparsers.add_parser(
        "bug-report",
        aliases=["feedback", "issue"],
        help="File a bug report or request a feature.",
        description="Opens the GitHub issue tracker and prints environment diagnostics for copy-pasting.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # ---------------- Diagnostic Flags ----------------
    parser.add_argument("--create-config", type=str, nargs="?", const="PROMPT", metavar="DEST", help="Create an annotated `.pubrun.toml` configuration file.")
    parser.add_argument("--show-config", action="store_true", help="Print the default configuration to the terminal.")
    parser.add_argument("--info", action="store_true", help="Display system capabilities and pubrun version info.")
    parser.add_argument("--run-tests", action="store_true", help="Run the built-in test suite and a mock end-to-end script.")
    
    args = parser.parse_args()
    if no_color_present:
        setattr(args, "no_color", True)
    if getattr(args, "no_color", False):
        os.environ["NO_COLOR"] = "1"

    executed = False

    if args.command == "report":
        run_dirs = getattr(args, "run_dirs", [])
        if not run_dirs:
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
                _run_report(str(r.run_dir), args.depth)
        else:
            for idx, rd in enumerate(run_dirs):
                if idx > 0:
                    print("\n")
                _run_report(rd, args.depth)
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
            getattr(args, "same", None)
        )
        executed = True


    elif args.command == "meta":
        _run_meta(args.out, args.depth)
        executed = True

    elif args.command == "cite":
        _run_cite(args.style)
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

    elif args.command in {"bug-report", "feedback", "issue"}:
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
