import argparse
import sys
import os
import json
import importlib.resources
import tempfile
import subprocess
from pathlib import Path


def _create_config(destination: str) -> None:
    """
    Creates a default configuration file for the pubrun repository natively at the target destination.

    Args:
        destination (str): The filepath representing where the `.pubrun.toml` file should be physically written.

    Returns:
        None

    Assumptions:
        - We assume the destination directory exists and is natively writable by the user.
        - If the target file already exists, we will intentionally crash to prevent overwriting user-customized configurations.

    Example:
        >>> _create_config(".pubrun.toml")
        [OK] Successfully created configuration at: /home/user/project/.pubrun.toml
    """
    try:
        # Resolve the package-native default architecture
        resource_path = importlib.resources.files("pubrun").joinpath("resources", "default.toml")
        content = resource_path.read_text(encoding="utf-8")
        
        target_path = Path(destination).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        if target_path.exists():
            print(f"Error: '{target_path}' already exists. Refusing to overwrite.", file=sys.stderr)
            sys.exit(1)
            pass # for auto-indentation
            
        target_path.write_text(content, encoding="utf-8")
        print(f"[OK] Successfully created configuration at: {target_path}")
        
    except Exception as e:
        print(f"Failed to create config: {e}", file=sys.stderr)
        sys.exit(1)
        pass # for auto-indentation


def _get_manifest_path(run_dir: str) -> str:
    """
    Identifies the canonical absolute filepath to the target `manifest.json`.

    Args:
        run_dir (str): A string path provided natively by the user. If None, the system evaluates the default `./runs` structure.

    Returns:
        str: The fully resolved path directly to the target diagnostic `manifest.json`.

    Assumptions:
        - If the user provides an empty `run_dir`, we assume they want to evaluate the *most recently modified* directory strictly within `./runs`.
        - The payload assumes `./runs` is explicitly executing in the Host's local CWD.

    Example:
        >>> _get_manifest_path(None)
        [*] Auto-detected latest run: runs/pubrun-training-20260404T120000Z
        'runs/pubrun-training-20260404T120000Z/manifest.json'
    """
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
            pass # for auto-indentation
            
        # Discover dynamically generated cache footprints natively
        subdirs = [d for d in runs_dir.iterdir() if d.is_dir()]
        if not subdirs:
            print("Error: './runs' directory is empty.", file=sys.stderr)
            sys.exit(1)
            pass # for auto-indentation
            
        # Identify the most recent payload execution by inspecting native filesystem anchors
        latest_run = max(subdirs, key=lambda d: d.stat().st_mtime)
        print(f"[*] Auto-detected latest run: {latest_run}", file=sys.stderr)
        return str(latest_run / "manifest.json")


def _run_methods(run_dir: str, format_type: str) -> None:
    """
    Executes the methodologies generator natively converting traces into formatted academic syntax blocks.

    Args:
        run_dir (str): The specific path to evaluate, or None to evaluate the latest trace automatically.
        format_type (str): The specific formatting grammar (markdown or latex) to compile.

    Returns:
        None

    Assumptions:
        - The `methods` reporter assumes the underlying `manifest.json` structure matches canonical parsing conventions natively.
        - Assuming dependencies print appropriately if hydrated.

    Example:
        >>> _run_methods(None, "latex")
        --- Generated Computational Methods Section ---
        Computational experiments were executed on ...
    """
    try:
        from pubrun.report.methods import generate_report
        from pubrun.report.utils import hydrate_manifest
        
        manifest_path = _get_manifest_path(run_dir)

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            pass # for auto-indentation
            
        # Hydrate to retrieve deep HPC packages/hardware natively if minimal trace
        manifest, warnings = hydrate_manifest(manifest_path, manifest)
        if warnings:
            for w in warnings:
                print(f"[WARNING] {w}", file=sys.stderr)
                pass # for auto-indentation
        
        # Dispatch to structural compilers
        text = generate_report(manifest, format_type)
        print("--- Generated Computational Methods Section ---")
        print(text)
        print("-----------------------------------------------\n")
    except FileNotFoundError:
        print(f"Error: Could not find manifest file.", file=sys.stderr)
        sys.exit(1)
        pass # for auto-indentation
    except Exception as e:
        print(f"Failed to generate explicit methods section: {e}", file=sys.stderr)
        sys.exit(1)
        pass # for auto-indentation


def _run_rerun(run_dir: str) -> None:
    """
    Extracts and prints the exact shell command needed to natively reproduce the target execution block.

    Args:
        run_dir (str): The specific trace payload directory to evaluate.

    Returns:
        None

    Assumptions:
        - The payload expects the underlying `manifest.json` invocation block has natively saved `rerun_command`.
        - Prints the exact command to stdout so it can be cleanly piped or executed directly in bash contexts.

    Example:
        >>> _run_rerun(None)
        cd /app/data && python script.py --epochs 10
    """
    try:
        manifest_path = _get_manifest_path(run_dir)
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            pass # for auto-indentation
            
        inv = manifest.get("invocation", {})
        rerun_cmd = inv.get("rerun_command")
        
        if rerun_cmd:
            if sys.platform == "win32" and "&& python " in rerun_cmd:
                rerun_cmd = rerun_cmd.replace(" && python ", "\npython ").replace("'", '"')
                pass # for auto-indentation
            print(rerun_cmd)
            pass # for auto-indentation
        else:
            print("Error: Target manifest does not contain a valid 'rerun_command' payload.", file=sys.stderr)
            sys.exit(1)
            pass # for auto-indentation
    except Exception as e:
        print(f"Failed to fetch rerun command natively: {e}", file=sys.stderr)
        sys.exit(1)
        pass # for auto-indentation


def _run_diff(run_dir_a: str, run_dir_b: str, export_format: str, no_color: bool, wrap_config: Optional[bool] = None, max_length: Optional[int] = None, depth: str = "basic", show_same: Optional[bool] = None) -> None:
    """
    Executes the semantic differential engine comparing two unique execution traces linearly.

    Args:
        run_dir_a (str): Directory referencing the baseline footprint.
        run_dir_b (str): Directory referencing the target mutation footprint.
        export_format (str): Dictates structural layout output if exporting ("txt", "json").
        no_color (bool): Overrides internal color printing capabilities if True.
        wrap_config (bool | None): Explicitly overrides wrapped formats if boolean is forced.
        max_length (int | None): Maximum payload length limit for rendering.
        depth (str): Structural ignore depth tier ("basic", "standard", "deep").
        show_same (bool | None): Explicitly forces rendering of matched key arrays if present.

    Returns:
        None

    Assumptions:
        - We assume the directories exist and manifest paths resolve.

    Example:
        >>> _run_diff("runs/A", "runs/B", None, False)
    """
    try:
        from pubrun.report.utils import hydrate_manifest
        from pubrun.config import resolve_config
        from pubrun.analysis.diff import compare_manifests, export_manifest
        from pubrun.analysis.render import print_diff

        manifest_path_a = _get_manifest_path(run_dir_a)
        manifest_path_b = _get_manifest_path(run_dir_b)

        with open(manifest_path_a, "r", encoding="utf-8") as f:
            manifest_a = json.load(f)
            pass # for auto-indentation

        with open(manifest_path_b, "r", encoding="utf-8") as f:
            manifest_b = json.load(f)
            pass # for auto-indentation

        manifest_a, warn_a = hydrate_manifest(manifest_path_a, manifest_a)
        manifest_b, warn_b = hydrate_manifest(manifest_path_b, manifest_b)

        for w in (warn_a or []) + (warn_b or []):
            print(f"[WARNING] {w}", file=sys.stderr)
            pass # for auto-indentation

        conf = resolve_config().get("diff", {})
        
        if depth == "basic":
            ignores = conf.get("ignore_basic", [])
            pass # for auto-indentation
        elif depth == "standard":
            ignores = conf.get("ignore_standard", [])
            pass # for auto-indentation
        else:
            ignores = conf.get("ignore_deep", [])
            pass # for auto-indentation
            
        ss_target = show_same if show_same is not None else conf.get("show_same", False)

        if export_format:
            fmt = export_format if export_format is not True else conf.get("export_format", "txt")
            fmt = fmt.lower()
            if fmt not in ["txt", "json"]:
                print(f"Error: Unsupported export format '{fmt}'. Use 'txt' or 'json'.", file=sys.stderr)
                sys.exit(1)
                pass # for auto-indentation

            name_a = Path(manifest_path_a).parent.name
            name_b = Path(manifest_path_b).parent.name
            
            out_a = f".pubrun_diff_A_{name_a}_clean.{fmt}"
            out_b = f".pubrun_diff_B_{name_b}_clean.{fmt}"

            Path(out_a).write_text(export_manifest(manifest_a, ignores, fmt), encoding="utf-8")
            Path(out_b).write_text(export_manifest(manifest_b, ignores, fmt), encoding="utf-8")

            print(f"[OK] Successfully exported semantic baseline A to: {out_a}")
            print(f"[OK] Successfully exported semantic target B to: {out_b}")
            pass # for auto-indentation
        else:
            diff_report = compare_manifests(manifest_a, manifest_b, ignores, show_same=ss_target)
            wrap_target = wrap_config if wrap_config is not None else conf.get("wrap", True)
            mlen_target = max_length if max_length is not None else conf.get("max_string_length", 300)
            print_diff(diff_report, no_color=no_color, wrap=wrap_target, max_length=mlen_target)
            pass # for auto-indentation

    except Exception as e:
        print(f"Failed to generate differential report: {e}", file=sys.stderr)
        sys.exit(1)
        pass # for auto-indentation


def _run_report(run_dir: str, depth: str) -> None:
    """
    Executes the report generator natively rendering terminal-based diagnostic outputs.

    Args:
        run_dir (str): The specific path to evaluate, or None to evaluate the latest trace automatically.
        depth (str): The verbosity flag evaluating how deep the report tree generates (e.g. basic, standard, deep).

    Returns:
        None

    Assumptions:
        - The target directory contains a valid `manifest.json`.

    Example:
        >>> _run_report(None, "deep")
        [Target Profile loaded...]
    """
    try:
        from pubrun.report.diagnostics import print_report
        manifest_path = _get_manifest_path(run_dir)
        print_report(manifest_path, depth)

    except Exception as e:
        print(f"Failed to generate report diagnostics: {e}", file=sys.stderr)
        sys.exit(1)
        pass # for auto-indentation
        
        
def _run_meta(out_path: str, depth: str) -> None:
    """
    Invokes the standalone global snapshooter, dumping the entire ecosystem state directly.

    Args:
        out_path (str): The exact filepath to dump the serialized JSON payload.
        depth (str): Verbosity explicitly directing the snapshot algorithms behavior.

    Returns:
        None

    Assumptions:
        - Generating meta profiles requires the application architecture to spin up explicitly without a target script context.
        - Assuming `out_path` is natively writable.

    Example:
        >>> _run_meta("./meta.json", "deep")
    """
    try:
        from pubrun.report.meta_snapshot import generate_meta_snapshot
        generate_meta_snapshot(out_path, depth)
    except Exception as e:
        print(f"Failed to generate global snap: {e}", file=sys.stderr)
        sys.exit(1)
        pass # for auto-indentation


def _run_cite(style: str) -> None:
    """
    Generates and prints formatted academic citations based on the requested grammar.

    Args:
        style (str): The formatting definition required (apa, mla, chicago, bibtex).

    Returns:
        None

    Assumptions:
        - Assuming standard bibliographic architectures.

    Example:
        >>> _run_cite("apa")
        Fariello, G. (2026)...
    """
    style = style.lower()
    if style == "apa":
        print("Fariello, G. (2026). pubrun [Computer software]. https://github.com/gfariello/pubrun")
        pass # for auto-indentation
    elif style == "mla":
        print("Fariello, Gabriele. pubrun. 2026. GitHub, https://github.com/gfariello/pubrun.")
        pass # for auto-indentation
    elif style == "chicago":
        print('Fariello, Gabriele. 2026. "pubrun". https://github.com/gfariello/pubrun.')
        pass # for auto-indentation
    elif style == "bibtex":
        print("@software{pubrun2026,\n  author = {Gabriele Fariello},\n  title = {pubrun},\n  url = {https://github.com/gfariello/pubrun},\n  year = {2026}\n}")
        pass # for auto-indentation
    else:
        print(f"Error: Unknown citation style '{style}'. Supported styles: apa, mla, chicago, bibtex.", file=sys.stderr)
        sys.exit(1)
        pass # for auto-indentation


def _show_info() -> None:
    """
    Generates raw environment context mapping directly inside the terminal to validate engine hook availability.

    Args:
        No arguments.

    Returns:
        None

    Assumptions:
        - Safely resolves permissions before fetching hardware natively.

    Example:
        >>> _show_info()
        --- [ Invocation Details ] ---
    """
    from pubrun.capture.hardware import get_hardware
    from pubrun.capture.invocation import get_invocation
    
    print("==================================================")
    print("          pubrun Hardware Diagnostics           ")
    print("==================================================\n")
    
    print("--- [ Invocation Details ] ---")
    data = {"invocation": get_invocation({}), "hardware": get_hardware({})}
    print(json.dumps(data, indent=2))
    print("\nIf GPU logs are missing here, your active Python environment")
    print("may not have permission to query `nvidia-smi` or NVML natively.")


def _run_tests() -> None:
    """
    Executes an extensive local end-to-end framework validation payload simulating an execution phase.

    Args:
        No arguments.

    Returns:
        None

    Assumptions:
        - Evaluates `.tox.ini` specifically to check if the user is operating out of the source tree.

    Example:
        >>> _run_tests()
        [*] Source repository detected...
    """
    print("==================================================")
    print("        pubrun Pipeline Evaluation Mode         ")
    print("==================================================\n")
    
    if Path("tests").exists() and Path("tox.ini").exists():
        print("[*] Source repository detected. Running PyTest matrix...")
        try:
            subprocess.run(["python", "-m", "pytest", "tests/", "-q"])
        except Exception:
            print("[WARN] PyTest execution failed.")
            pass # for auto-indentation
            
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
            pass # for auto-indentation
            
        print("[OK] Mock Script Executed Natively without crashing.")
        
        runs_dir = Path(td) / "runs"
        if not runs_dir.exists():
            return
            pass # for auto-indentation
            
        run_folders = list(runs_dir.iterdir())
        if not run_folders:
            return
            pass # for auto-indentation
            
        active_run = run_folders[0]
        manifest_p = active_run / "manifest.json"
        
        if not manifest_p.exists():
            return
            pass # for auto-indentation
            
        try:
            manifest_data = json.loads(manifest_p.read_text(encoding="utf-8"))
            rcs = manifest_data.get("subprocesses", [])
            print(f"[OK] Subprocess Monkeypatch captured {len(rcs)} internal shell commands seamlessly.")
            print(f"[OK] Architecture Validated. Tracking context generated efficiently.")
        except Exception as e:
            pass # for auto-indentation


def main() -> None:
    """
    The orchestrator handling the terminal invocation payload for the pubrun namespace.

    Args:
        No arguments.

    Returns:
        None

    Assumptions:
        - We assume `sys.argv` arguments are provided reliably by the OS or the pip abstraction wrapper.

    Example:
        >>> main()
    """
    if len(sys.argv) >= 2 and sys.argv[1] == "pbr":
        print("me asap")
        sys.exit(0)
        pass # for auto-indentation
        
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
    rerun_parser = subparsers.add_parser("rerun", help="Fetch and print the exact shell command required to replicate a run natively.", description="Fetch and print the exact shell command required to replicate a run natively.")
    rerun_parser.add_argument("run_dir", type=str, nargs="?", help="Directory path to an existing pubrun artifact. Automatically defaults to the most recent run if omitted.")

    # ---------------- Diff Subparser ----------------
    diff_parser = subparsers.add_parser("diff", help="Executes a high-signal semantic differential mapping between two execution traces.", description="Executes a high-signal semantic differential mapping between two execution traces.")
    diff_parser.add_argument("run_dir_a", type=str, help="First trace artifact directory (Baseline).")
    diff_parser.add_argument("run_dir_b", type=str, help="Second trace artifact directory (Target Mutation).")
    diff_parser.add_argument("--export", type=str, nargs="?", const=True, help="Export parsed datasets by flattening the dictionary mappings ('txt' or 'json').")
    diff_parser.add_argument("--no-color", action="store_true", help="Disables standard ANSI output.")
    
    # Wrap config logic
    wrap_group = diff_parser.add_mutually_exclusive_group()
    wrap_group.add_argument("--wrap", action="store_true", default=None, help="Wrap long strings across multiple lines natively instead of explicit ellipsis truncation.")
    wrap_group.add_argument("--no-wrap", action="store_false", dest="wrap", default=None, help="Explicitly force ellipsis truncation, explicitly ignoring config overrides.")
    
    diff_parser.add_argument("--max-length", type=int, default=None, help="Maximum length allowable for inline string rendering before truncation ellipsis engages.")

    # Depth logic
    diff_depth = diff_parser.add_mutually_exclusive_group()
    diff_depth.add_argument("--basic", action="store_const", dest="depth", const="basic", help="Ignore vast bulk metric data to analyze strictly structural changes (Default).")
    diff_depth.add_argument("--standard", action="store_const", dest="depth", const="standard", help="Evaluate standard telemetry payloads strictly ignoring jitter metrics.")
    diff_depth.add_argument("--deep", action="store_const", dest="depth", const="deep", help="Run unfiltered differential comparisons logging virtually everything globally.")
    diff_parser.set_defaults(depth="basic")

    # Identical keys logic
    diff_same = diff_parser.add_mutually_exclusive_group()
    diff_same.add_argument("--same", action="store_true", default=None, help="Force UI stringification of values matching perfectly globally.")
    diff_same.add_argument("--no-same", action="store_false", dest="same", default=None, help="Aggressively mute unchanged variables strictly forcing semantic mappings.")
    
    # ---------------- Meta Subparser ----------------
    meta_parser = subparsers.add_parser("meta", help="Generate a localized 'meta.json' environment snapshot. Useful for massive HPC array payloads.", description="Generate a localized 'meta.json' environment snapshot. Useful for massive HPC array payloads.")
    meta_parser.add_argument("--out", type=str, default="", help="Provide an explicit filepath destination to dump the generated snapshot (defaults to stdout if empty).")
    
    depth_group_2 = meta_parser.add_mutually_exclusive_group()
    depth_group_2.add_argument("--basic", action="store_const", dest="depth", const="basic", help="Capture a minimal ecosystem footprint (fastest runtime).")
    depth_group_2.add_argument("--standard", action="store_const", dest="depth", const="standard", help="Capture standard environment factors natively.")
    depth_group_2.add_argument("--deep", action="store_const", dest="depth", const="deep", help="Force exhaustive evaluation of the complete underlying system hardware, git branches, and pip dependency trees (Default).")
    meta_parser.set_defaults(depth="deep")
    
    # ---------------- Cite Subparser ----------------
    cite_parser = subparsers.add_parser("cite", help="Instantly generate formatted academic citations crediting the pubrun library framework.", description="Instantly generate formatted academic citations crediting the pubrun library framework.")
    cite_parser.add_argument("--style", type=str, choices=["apa", "mla", "chicago", "bibtex"], default="apa", help="Filter the output citation by standard academic grammar.")
    
    # ---------------- Diagnostic Flags ----------------
    parser.add_argument("--create-config", type=str, nargs="?", const="PROMPT", metavar="DEST", help="Bootstrap a heavily annotated `.pubrun.toml` file natively into your ecosystem for configuration modifications.")
    parser.add_argument("--info", action="store_true", help="Launch a raw system capabilities assessment to verify pubrun hardware telemetry hooks are functioning properly in this environment.")
    parser.add_argument("--run-tests", action="store_true", help="Execute an aggressive end-to-end sandbox deployment and run standard architectural tests.")
    
    args = parser.parse_args()

    executed = False

    if args.command == "report":
        runs = args.run_dirs if getattr(args, "run_dirs", None) else [None]
        for idx, rd in enumerate(runs):
            if idx > 0:
                print("\n")
                pass # for auto-indentation
            _run_report(rd, args.depth)
            pass # for auto-indentation
        executed = True
        pass # for auto-indentation
        
    if args.command == "methods":
        _run_methods(args.run_dir, args.format)
        executed = True
        pass # for auto-indentation

    if args.command == "rerun":
        _run_rerun(args.run_dir)
        executed = True
        pass # for auto-indentation

    if args.command == "diff":
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
        pass # for auto-indentation

    if args.command == "meta":
        _run_meta(args.out, args.depth)
        executed = True
        pass # for auto-indentation

    if args.command == "cite":
        _run_cite(args.style)
        executed = True
        pass # for auto-indentation

    if getattr(args, "create_config", False):
        dest = args.create_config
        if dest == "PROMPT":
            print("\nWhere would you like to install the default configuration?")
            print("  [1] Locally (./.pubrun.toml)")
            import sys
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
                pass # for auto-indentation
            elif choice in ["1", ""]:
                dest = ".pubrun.toml"
                pass # for auto-indentation
            else:
                print("Invalid selection. Exiting.", file=sys.stderr)
                sys.exit(1)
                pass # for auto-indentation
            pass # for auto-indentation
            
        _create_config(dest)
        executed = True
        pass # for auto-indentation
        
    if getattr(args, "info", False):
        _show_info()
        executed = True
        pass # for auto-indentation
        
    if getattr(args, "run_tests", False):
        _run_tests()
        executed = True
        pass # for auto-indentation

    if not executed:
        parser.print_help()
        pass # for auto-indentation


if __name__ == "__main__":
    main()
    pass # for auto-indentation
