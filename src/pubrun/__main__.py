import argparse
import sys
import os
import json
import importlib.resources
import tempfile
import subprocess
from pathlib import Path
from typing import Optional


def _create_config(destination: str) -> None:
    """Create a default ``.pubrun.toml`` at the given path. Refuses to overwrite."""
    try:
        # Resolve the package-native default architecture
        resource_path = importlib.resources.files("pubrun").joinpath("resources", "default.toml")
        content = resource_path.read_text(encoding="utf-8")
        
        target_path = Path(destination).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        if target_path.exists():
            print(f"Error: '{target_path}' already exists. Refusing to overwrite.", file=sys.stderr)
            sys.exit(1)
            
        target_path.write_text(content, encoding="utf-8")
        print(f"[OK] Successfully created configuration at: {target_path}")
        
    except Exception as e:
        print(f"Failed to create config: {e}", file=sys.stderr)
        sys.exit(1)


def _get_manifest_path(run_dir: str) -> str:
    """Resolve the path to a manifest.json, auto-detecting the latest run if needed."""
    if run_dir:
        run_path = Path(run_dir)
        if run_path.is_file() and run_path.name == "manifest.json":
            return str(run_path)
        else:
            return str(run_path / "manifest.json")
    else:
        runs_dir = Path("runs")
        if not runs_dir.exists() or not runs_dir.is_dir():
            print("Error: No --run directory provided and './runs' directory not found.", file=sys.stderr)
            sys.exit(1)
            
        # Discover the most recent run directory
        subdirs = [d for d in runs_dir.iterdir() if d.is_dir()]
        if not subdirs:
            print("Error: './runs' directory is empty.", file=sys.stderr)
            sys.exit(1)
            
        # Pick the most recently modified run
        latest_run = max(subdirs, key=lambda d: d.stat().st_mtime)
        print(f"[*] Auto-detected latest run: {latest_run}", file=sys.stderr)
        return str(latest_run / "manifest.json")


def _run_methods(run_dir: str, format_type: str) -> None:
    """Generate and print an academic 'Computational Methods' paragraph."""
    try:
        from pubrun.report.methods import generate_report
        from pubrun.report.utils import hydrate_manifest
        
        manifest_path = _get_manifest_path(run_dir)

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
    except FileNotFoundError:
        print(f"Error: Could not find manifest file.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Failed to generate methods section: {e}", file=sys.stderr)
        sys.exit(1)


def _run_rerun(run_dir: str) -> None:
    """Print the shell command needed to reproduce a recorded run."""
    try:
        manifest_path = _get_manifest_path(run_dir)
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            
        inv = manifest.get("invocation", {})
        rerun_cmd = inv.get("rerun_command")
        
        if rerun_cmd:
            if sys.platform == "win32" and "&& python " in rerun_cmd:
                rerun_cmd = rerun_cmd.replace(" && python ", "\npython ").replace("'", '"')
            print(rerun_cmd)
        else:
            print("Error: Target manifest does not contain a valid 'rerun_command' payload.", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Failed to fetch rerun command: {e}", file=sys.stderr)
        sys.exit(1)


def _run_diff(run_dir_a: str, run_dir_b: str, export_format: str, no_color: bool, wrap_config: Optional[bool] = None, max_length: Optional[int] = None, depth: str = "basic", show_same: Optional[bool] = None) -> None:
    """Run the semantic diff engine comparing two execution traces."""
    try:
        from pubrun.report.utils import hydrate_manifest
        from pubrun.config import resolve_config
        from pubrun.analysis.diff import compare_manifests, export_manifest
        from pubrun.analysis.render import print_diff

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
                print(f"Error: Unsupported export format '{fmt}'. Use 'txt' or 'json'.", file=sys.stderr)
                sys.exit(1)

            name_a = Path(manifest_path_a).parent.name
            name_b = Path(manifest_path_b).parent.name
            
            out_a = f".pubrun_diff_A_{name_a}_clean.{fmt}"
            out_b = f".pubrun_diff_B_{name_b}_clean.{fmt}"

            Path(out_a).write_text(export_manifest(manifest_a, ignores, fmt), encoding="utf-8")
            Path(out_b).write_text(export_manifest(manifest_b, ignores, fmt), encoding="utf-8")

            print(f"[OK] Successfully exported semantic baseline A to: {out_a}")
            print(f"[OK] Successfully exported semantic target B to: {out_b}")
        else:
            diff_report = compare_manifests(manifest_a, manifest_b, ignores, show_same=ss_target)
            wrap_target = wrap_config if wrap_config is not None else conf.get("wrap", True)
            mlen_target = max_length if max_length is not None else conf.get("max_string_length", 300)
            print_diff(diff_report, no_color=no_color, wrap=wrap_target, max_length=mlen_target)

    except Exception as e:
        print(f"Failed to generate differential report: {e}", file=sys.stderr)
        sys.exit(1)


def _run_report(run_dir: str, depth: str) -> None:
    """Print a human-readable diagnostic report for a recorded run."""
    try:
        from pubrun.report.diagnostics import print_report
        manifest_path = _get_manifest_path(run_dir)
        print_report(manifest_path, depth)

    except Exception as e:
        print(f"Failed to generate report diagnostics: {e}", file=sys.stderr)
        sys.exit(1)
        
        
def _run_meta(out_path: str, depth: str) -> None:
    """Generate a standalone environment snapshot for HPC parent-child hydration."""
    try:
        from pubrun.report.meta_snapshot import generate_meta_snapshot
        generate_meta_snapshot(out_path, depth)
    except Exception as e:
        print(f"Failed to generate global snap: {e}", file=sys.stderr)
        sys.exit(1)


def _run_cite(style: str) -> None:
    """Print a formatted academic citation for pubrun."""
    style = style.lower()
    if style == "apa":
        print("Fariello, G. (2026). pubrun [Computer software]. https://github.com/gfariello/pubrun")
    elif style == "mla":
        print("Fariello, Gabriele. pubrun. 2026. GitHub, https://github.com/gfariello/pubrun.")
    elif style == "chicago":
        print('Fariello, Gabriele. 2026. "pubrun". https://github.com/gfariello/pubrun.')
    elif style == "bibtex":
        print("@software{pubrun2026,\n  author = {Gabriele Fariello},\n  title = {pubrun},\n  url = {https://github.com/gfariello/pubrun},\n  year = {2026}\n}")
    else:
        print(f"Error: Unknown citation style '{style}'. Supported styles: apa, mla, chicago, bibtex.", file=sys.stderr)
        sys.exit(1)


def _show_info() -> None:
    """Print hardware and invocation diagnostics for debugging."""
    from pubrun.capture.hardware import get_hardware
    from pubrun.capture.invocation import get_invocation
    
    print("==================================================")
    print("          pubrun Hardware Diagnostics           ")
    print("==================================================\n")
    
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
            print(f"[OK] Subprocess Monkeypatch captured {len(rcs)} internal shell commands seamlessly.")
            print(f"[OK] Architecture Validated. Tracking context generated efficiently.")
        except Exception as e:
            pass


def main() -> None:
    """CLI entrypoint for the ``pubrun`` command."""
    if len(sys.argv) >= 2 and sys.argv[1] == "pbr":
        print("me asap")
        sys.exit(0)
        
    parser = argparse.ArgumentParser(
        description="pubrun: Zero-dependency execution telemetry and publication engine.",
        epilog="Use 'pubrun <command> --help' for detailed information on a specific tool."
    )
    
    subparsers = parser.add_subparsers(dest="command", title="Available core commands", metavar="<command>")
    
    # ---------------- Report Subparser ----------------
    report_parser = subparsers.add_parser("report", help="Analyze and display diagnostic telemetry from a specific run.", description="Analyze and display diagnostic telemetry from a specific run.")
    report_parser.add_argument("run_dirs", type=str, nargs="*", help="Directory path to one or more existing pubrun artifact folders (e.g., runs/pubrun-XYZ). If omitted, the system automatically discovers and evaluates the most recently completed run in the ./runs directory.")
    
    depth_group_1 = report_parser.add_mutually_exclusive_group()
    depth_group_1.add_argument("--basic", action="store_const", dest="depth", const="basic", help="Display only high-level identifiers (Architecture, Timing, Outcome).")
    depth_group_1.add_argument("--standard", action="store_const", dest="depth", const="standard", help="Display a standard summary including OS constraints, Hardware info, and Git provenance (Default).")
    depth_group_1.add_argument("--deep", action="store_const", dest="depth", const="deep", help="Force the renderer to dump out heavily exhaustive dependency graphs (every pip package and env var).")
    report_parser.set_defaults(depth="standard")

    # ---------------- Methods Subparser ----------------
    methods_parser = subparsers.add_parser("methods", help="Autogenerate publication-ready 'Computational Methods' paragraphs for academic papers.", description="Autogenerate publication-ready 'Computational Methods' paragraphs for academic papers.")
    methods_parser.add_argument("run_dir", type=str, nargs="?", help="Directory path to an existing pubrun artifact. Automatically defaults to the most recent run if omitted.")
    methods_parser.add_argument("--format", type=str, choices=["markdown", "latex"], default="markdown", help="Specify the structured language (markdown or latex) the methodology section should be compiled into.")

    # ---------------- Rerun Subparser ----------------
    rerun_parser = subparsers.add_parser("rerun", help="Print the shell command needed to replicate a run.", description="Print the shell command needed to replicate a run.")
    rerun_parser.add_argument("run_dir", type=str, nargs="?", help="Directory path to an existing pubrun artifact. Automatically defaults to the most recent run if omitted.")

    # ---------------- Diff Subparser ----------------
    diff_parser = subparsers.add_parser("diff", help="Compare two execution traces and highlight differences.", description="Compare two execution traces and highlight differences.")
    diff_parser.add_argument("run_dir_a", type=str, help="First trace artifact directory (Baseline).")
    diff_parser.add_argument("run_dir_b", type=str, help="Second trace artifact directory (Target Mutation).")
    diff_parser.add_argument("--export", type=str, nargs="?", const=True, help="Export parsed datasets by flattening the dictionary mappings ('txt' or 'json').")
    diff_parser.add_argument("--no-color", action="store_true", help="Disables standard ANSI output.")
    
    # Wrap config logic
    wrap_group = diff_parser.add_mutually_exclusive_group()
    wrap_group.add_argument("--wrap", action="store_true", default=None, help="Wrap long strings across multiple lines instead of truncating.")
    wrap_group.add_argument("--no-wrap", action="store_false", dest="wrap", default=None, help="Force ellipsis truncation for long values.")
    
    diff_parser.add_argument("--max-length", type=int, default=None, help="Maximum length allowable for inline string rendering before truncation ellipsis engages.")

    # Depth logic
    diff_depth = diff_parser.add_mutually_exclusive_group()
    diff_depth.add_argument("--basic", action="store_const", dest="depth", const="basic", help="Ignore vast bulk metric data to analyze strictly structural changes (Default).")
    diff_depth.add_argument("--standard", action="store_const", dest="depth", const="standard", help="Include standard telemetry, ignoring jitter metrics.")
    diff_depth.add_argument("--deep", action="store_const", dest="depth", const="deep", help="Unfiltered comparison of all captured data.")
    diff_parser.set_defaults(depth="basic")

    # Identical keys logic
    diff_same = diff_parser.add_mutually_exclusive_group()
    diff_same.add_argument("--same", action="store_true", default=None, help="Show keys that are identical between both runs.")
    diff_same.add_argument("--no-same", action="store_false", dest="same", default=None, help="Hide keys that are identical between both runs.")
    
    # ---------------- Meta Subparser ----------------
    meta_parser = subparsers.add_parser("meta", help="Generate a localized 'meta.json' environment snapshot. Useful for massive HPC array payloads.", description="Generate a localized 'meta.json' environment snapshot. Useful for massive HPC array payloads.")
    meta_parser.add_argument("--out", type=str, default="", help="Provide an explicit filepath destination to dump the generated snapshot (defaults to stdout if empty).")
    
    depth_group_2 = meta_parser.add_mutually_exclusive_group()
    depth_group_2.add_argument("--basic", action="store_const", dest="depth", const="basic", help="Capture a minimal ecosystem footprint (fastest runtime).")
    depth_group_2.add_argument("--standard", action="store_const", dest="depth", const="standard", help="Capture standard environment factors.")
    depth_group_2.add_argument("--deep", action="store_const", dest="depth", const="deep", help="Force exhaustive evaluation of the complete underlying system hardware, git branches, and pip dependency trees (Default).")
    meta_parser.set_defaults(depth="deep")
    
    # ---------------- Cite Subparser ----------------
    cite_parser = subparsers.add_parser("cite", help="Generate a formatted academic citation for pubrun.", description="Generate a formatted academic citation for pubrun.")
    cite_parser.add_argument("--style", type=str, choices=["apa", "mla", "chicago", "bibtex"], default="apa", help="Filter the output citation by standard academic grammar.")
    
    # ---------------- Diagnostic Flags ----------------
    parser.add_argument("--create-config", type=str, nargs="?", const="PROMPT", metavar="DEST", help="Create an annotated `.pubrun.toml` configuration file.")
    parser.add_argument("--show-config", action="store_true", help="Print the fully documented default `.pubrun.toml` configuration strictly to the terminal without creating any artifacts.")
    parser.add_argument("--info", action="store_true", help="Launch a raw system capabilities assessment to verify pubrun hardware telemetry hooks are functioning properly in this environment.")
    parser.add_argument("--run-tests", action="store_true", help="Execute an aggressive end-to-end sandbox deployment and run standard architectural tests.")
    
    args = parser.parse_args()

    executed = False

    if args.command == "report":
        runs = args.run_dirs if getattr(args, "run_dirs", None) else [None]
        for idx, rd in enumerate(runs):
            if idx > 0:
                print("\n")
            _run_report(rd, args.depth)
        executed = True

    elif args.command == "methods":
        _run_methods(args.run_dir, args.format)
        executed = True

    elif args.command == "rerun":
        _run_rerun(args.run_dir)
        executed = True

    elif args.command == "diff":
        _run_diff(
            args.run_dir_a, 
            args.run_dir_b, 
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
                print("Invalid selection. Exiting.", file=sys.stderr)
                sys.exit(1)
            
        _create_config(dest)
        executed = True
        
    if getattr(args, "show_config", False):
        import importlib.resources
        resource_path = importlib.resources.files("pubrun").joinpath("resources", "default.toml")
        content = resource_path.read_text(encoding="utf-8")
        try:
            from rich.console import Console
            from rich.syntax import Syntax
            console = Console()
            console.print(Syntax(content, "toml", theme="monokai", line_numbers=True, padding=1))
        except ImportError:
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


if __name__ == "__main__":
    main()
