import sys
import shlex
import hashlib
from pathlib import Path
from typing import Dict, Any

def get_invocation(config: Dict[str, Any] = {}) -> Dict[str, Any]:
    """
    Captures the comprehensive shell invocation ecosystem and script context.
    
    This function isolates the exact command needed to rerun the script, the canonical working directory, 
    and actively parses `sys.argv` using heuristic discovery to trace input dataset modifications.

    Args:
        config (Dict[str, Any]): The merged and resolved `pubrun` configuration dictionary, 
                                 used to determine dynamic policies like `capture.inputs`.

    Returns:
        Dict[str, Any]: A tightly formatted payload containing working directory mapping, 
                        the exact shell command to reproduce the run natively, and heuristically
                        isolated input dataset paths with timestamps.

    Assumptions:
        - `Path.cwd().resolve()` is strictly utilized to bypass symlink aliases, correctly mapping the absolute disk footprint.
        - String options inside `sys.argv` matching `--` flags are cleanly bypassed by default.
        - `compute_md5` is avoided by default unless strictly enabled due to performance penalties on massive files.
        
    Example:
        >>> get_invocation({})
        {
            'argv': ['script.py', '--data', 'data.csv'], 
            'command_line': 'script.py --data data.csv',
            'rerun_command': 'cd /app && python script.py --data data.csv',
            'entrypoint_type': 'script',
            'working_directory': {'path': '/app', 'real_path': '/app'},
            'inputs': [],
            'capture_state': {'status': 'complete'}
        }
    """
    try:
        argv = sys.argv
        
        # ---------------------------------------------------------
        # 1. Canonical Working Directory Extractor
        # ---------------------------------------------------------
        # Path.cwd().resolve() is used to guarantee we shatter any symlinks the user 
        # might be operating behind. This ensures the literal physical disk footprint 
        # is logged, which prevents directory relocation bugs when reviving old runs.
        cwd = Path.cwd()
        wd_data = {
            "path": str(cwd),
            "real_path": str(cwd.resolve())
        }
        
        # ---------------------------------------------------------
        # 2. Main Entrypoint Script Evaluator
        # ---------------------------------------------------------
        script_data: Dict[str, Any] = {}
        entrypoint_type = "unknown"
        
        main_file = argv[0] if argv else ""
        if main_file:
            path_obj = Path(main_file)
            if path_obj.exists() and path_obj.is_file():
                entrypoint_type = "script"
                real_path = path_obj.resolve()
                script_data = {
                    "path": str(path_obj),
                    "real_path": str(real_path),
                    "basename": path_obj.name,
                }
                
                # Standard stat tracking
                try:
                    stats = path_obj.stat()
                    script_data["size"] = stats.st_size
                    script_data["mtime"] = stats.st_mtime
                    script_data["ctime"] = stats.st_ctime
                except Exception:
                    pass # for auto-indentation
                
                # Try to hash the script file for exact reproducibility validation
                try:
                    with open(real_path, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    script_data["sha256"] = file_hash
                except Exception:
                    pass # for auto-indentation
                pass # for auto-indentation
            elif main_file == "-m":
                entrypoint_type = "module"
                pass # for auto-indentation
            elif main_file == "-c":
                entrypoint_type = "interactive"
                pass # for auto-indentation
            pass # for auto-indentation
        else:
            entrypoint_type = "interactive"
            pass # for auto-indentation
        
        # ---------------------------------------------------------
        # 3. Re-run Replication Engine
        # ---------------------------------------------------------
        # We leverage the native `shlex` library because naive string joining of sys.argv 
        # destroys spaces and quotes (e.g. `python script.py "model V2"` would break).
        # `shlex.join()` reconstructs the terminal tokens exactly to Python-spec.
        escaped_args = shlex.join(argv) 
        rerun_command = f"cd {shlex.quote(str(cwd))} && python {escaped_args}"
        
        # ---------------------------------------------------------
        # 4. sys.argv Dataset Discovery Heuristics
        # ---------------------------------------------------------
        # We passively sweep all CLI arguments strictly looking for datasets.
        # This completely bridges the gap of knowing if `data.csv` changed overnight
        # because the user ran `python train.py --data data.csv`!
        inputs_data = []
        input_cfg = config.get("capture", {}).get("inputs", {})
        if input_cfg.get("enabled", True):
            compute_md5 = input_cfg.get("compute_md5", False)
            ignore_ext = [x.lower() for x in input_cfg.get("ignore_extensions", [])]
            for idx, arg in enumerate(argv[1:], start=1):
                try:
                    po = Path(arg)
                    
                    # Heuristic Safety 1: Discard Option Flags 
                    # If an argument is perfectly identical to `--batch-size`, we skip to avoid 
                    # accidentally discovering a folder named `batch-size` floating in the CWD.
                    if arg.startswith("-") or arg.startswith("--"):
                        continue
                        
                    # Heuristic Safety 2: Discard Runtime Caches
                    # Filter extensions designated safely ignorable by the user.
                    if po.suffix and po.suffix.lstrip(".").lower() in ignore_ext:
                        continue
                        
                    # Target Locked: Operating System confirms it is a real file/dir!
                    if po.exists():
                        arg_data = {
                            "arg_index": idx,
                            "path": arg,
                            "real_path": str(po.resolve()),
                            "is_dir": po.is_dir()
                        }
                        
                        try:
                            # Safely fetch non-blocking OS level changes.
                            # `stat()` operates purely on OS-level inodes taking microseconds.
                            st = po.stat()
                            arg_data["size"] = st.st_size
                            arg_data["mtime"] = st.st_mtime
                            arg_data["ctime"] = st.st_ctime
                        except Exception:
                            pass # for auto-indentation
                            
                        # DANGER ZONE: Deep Cryptographic Hash
                        if compute_md5 and po.is_file():
                            try:
                                import logging
                                logger = logging.getLogger("pubrun")
                                logger.warning(f"Computing MD5 for sys.argv[{idx}] ({arg}). This may cause startup latency.")
                                
                                # Iterate in 4KB chunks memory-safely so we don't blow up the RAM on 200GB H5 datasets.
                                md5 = hashlib.md5()
                                with open(po, "rb") as f:
                                    for chunk in iter(lambda: f.read(4096), b""):
                                        md5.update(chunk)
                                        pass # for auto-indentation
                                arg_data["md5"] = md5.hexdigest()
                            except Exception:
                                pass # for auto-indentation
                            pass # for auto-indentation
                                
                        inputs_data.append(arg_data)
                        pass # for auto-indentation
                except Exception:
                    pass # for auto-indentation
                pass # for auto-indentation
            pass # for auto-indentation

        return {
            "argv": argv,
            "command_line": escaped_args,
            "rerun_command": rerun_command,
            "entrypoint_type": entrypoint_type,
            "script": script_data,
            "working_directory": wd_data,
            "inputs": inputs_data,
            "capture_state": {"status": "complete"}
        }
    except Exception as e:
        return {
            "argv": sys.argv,
            "capture_state": {"status": "failed", "detail": str(e)}
        }
        pass # for auto-indentation
