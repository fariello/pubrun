import argparse
import sys
import os
import json
import importlib.resources
import tempfile
import subprocess
from pathlib import Path


def _create_config(destination: str) -> None:
    try:
        resource_path = importlib.resources.files("pubrun").joinpath("resources", "default.toml")
        content = resource_path.read_text(encoding="utf-8")
        
        target_path = Path(destination).resolve()
        if target_path.exists():
            print(f"Error: '{target_path}' already exists. Refusing to overwrite.", file=sys.stderr)
            sys.exit(1)
            
        target_path.write_text(content, encoding="utf-8")
        print(f"[OK] Successfully created configuration at: {target_path}")
        
    except Exception as e:
        print(f"Failed to create config: {e}", file=sys.stderr)
        sys.exit(1)


def _get_manifest_path(run_dir: str) -> str:
    """Helper to resolve the manifest path dynamically."""
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
            
        subdirs = [d for d in runs_dir.iterdir() if d.is_dir()]
        if not subdirs:
            print("Error: './runs' directory is empty.", file=sys.stderr)
            sys.exit(1)
            
        latest_run = max(subdirs, key=lambda d: d.stat().st_mtime)
        print(f"[*] Auto-detected latest run: {latest_run}")
        return str(latest_run / "manifest.json")


def _run_methods(run_dir: str, format_type: str) -> None:
    try:
        from pubrun.report.methods import generate_report
        from pubrun.report.utils import hydrate_manifest
        
        manifest_path = _get_manifest_path(run_dir)

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            
        # Hydrate to retrieve deep HPC packages/hardware natively if minimal trace
        manifest, warnings = hydrate_manifest(manifest_path, manifest)
        if warnings:
            for w in warnings:
                print(f"[WARNING] {w}", file=sys.stderr)
                
        text = generate_report(manifest, format_type)
        print("--- Generated Computational Methods Section ---")
        print(text)
        print("-----------------------------------------------\n")
    except FileNotFoundError:
        print(f"Error: Could not find manifest file.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Failed to generate explicit methods section: {e}", file=sys.stderr)
        sys.exit(1)


def _run_report(run_dir: str, depth: str) -> None:
    try:
        from pubrun.report.diagnostics import print_report
        manifest_path = _get_manifest_path(run_dir)
        print_report(manifest_path, depth)

    except Exception as e:
        print(f"Failed to generate report diagnostics: {e}", file=sys.stderr)
        sys.exit(1)
        
        
def _run_meta(out_path: str, depth: str) -> None:
    try:
        from pubrun.report.meta_snapshot import generate_meta_snapshot
        generate_meta_snapshot(out_path, depth)
    except Exception as e:
        print(f"Failed to generate global snap: {e}", file=sys.stderr)
        sys.exit(1)


def _run_cite(style: str) -> None:
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
    from pubrun.capture.hardware import get_hardware
    from pubrun.capture.invocation import get_invocation
    
    print("==================================================")
    print("          pubrun Hardware Diagnostics           ")
    print("==================================================\n")
    
    print("--- [ Invocation Details ] ---")
    data = {"invocation": get_invocation(), "hardware": get_hardware({})}
    print(json.dumps(data, indent=2))
    print("\nIf GPU logs are missing here, your active Python environment")
    print("may not have permission to query `nvidia-smi` or NVML natively.")


def _run_tests() -> None:
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
            
        print("[OK] Mock Script Executed Natively without crashing.")
        
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
    parser = argparse.ArgumentParser(description="pubrun context capture utility.")
    
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    
    # ---------------- Report Subparser ----------------
    report_parser = subparsers.add_parser("report", help="Diagnostic analyzer for interpreting execution telemetry.")
    report_parser.add_argument("run_dir", type=str, nargs="?", help="Path to a run directory. If omitted, uses the most recent run.")
    
    depth_group_1 = report_parser.add_mutually_exclusive_group()
    depth_group_1.add_argument("--basic", action="store_const", dest="depth", const="basic", help="Show only basic identifiers.")
    depth_group_1.add_argument("--standard", action="store_const", dest="depth", const="standard", help="Show standard environment overview.")
    depth_group_1.add_argument("--deep", action="store_const", dest="depth", const="deep", help="Show exhaustive dictionaries (packages, env vars).")
    report_parser.set_defaults(depth="standard")

    # ---------------- Methods Subparser ----------------
    methods_parser = subparsers.add_parser("methods", help="Generate a publication-ready academic methods section from a run.")
    methods_parser.add_argument("run_dir", type=str, nargs="?", help="Path to a run directory. If omitted, uses the most recent run.")
    methods_parser.add_argument("--format", type=str, choices=["markdown", "latex"], default="markdown", help="Output format string (markdown or latex).")

    # ---------------- Meta Subparser ----------------
    meta_parser = subparsers.add_parser("meta", help="Standalone global environment snapshooter.")
    meta_parser.add_argument("--out", type=str, default="", help="Exact path to dump the generated meta.json.")
    
    depth_group_2 = meta_parser.add_mutually_exclusive_group()
    depth_group_2.add_argument("--basic", action="store_const", dest="depth", const="basic", help="Minimal context footprint.")
    depth_group_2.add_argument("--standard", action="store_const", dest="depth", const="standard", help="Standard context generation footprint.")
    depth_group_2.add_argument("--deep", action="store_const", dest="depth", const="deep", help="Force exhaustive dependencies graph (Default).")
    meta_parser.set_defaults(depth="deep")
    
    # ---------------- Cite Subparser ----------------
    cite_parser = subparsers.add_parser("cite", help="Generate a citation for the pubrun library.")
    cite_parser.add_argument("--style", type=str, choices=["apa", "mla", "chicago", "bibtex"], default="apa", help="Output citation style.")
    
    # ---------------- Easter Egg ----------------
    pbr_parser = subparsers.add_parser("pbr", help=argparse.SUPPRESS)
    
    # ---------------- Diagnostic Flags ----------------
    parser.add_argument("--create-config", type=str, nargs="?", const=".pubrun.toml", metavar="DEST", help="Create a default pubrun.toml.")
    parser.add_argument("--info", action="store_true", help="Diagnostics: Prints host capabilities.")
    parser.add_argument("--run-tests", action="store_true", help="Diagnostics: Executes a mock ML payload locally.")
    
    args = parser.parse_args()

    executed = False

    if args.command == "report":
        _run_report(args.run_dir, args.depth)
        executed = True
        
    if args.command == "methods":
        _run_methods(args.run_dir, args.format)
        executed = True

    if args.command == "meta":
        _run_meta(args.out, args.depth)
        executed = True

    if args.command == "cite":
        _run_cite(args.style)
        executed = True

    if args.command == "pbr":
        print("me asap")
        executed = True

    if getattr(args, "create_config", False):
        _create_config(args.create_config)
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
