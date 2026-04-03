import sys
import shlex
import hashlib
from pathlib import Path
from typing import Dict, Any

def get_invocation(config: Dict[str, Any] = {}) -> Dict[str, Any]:
    """
    Captures the shell invocation, sys.argv, working directory context, 
    and reconstructs the command used to rerun the script cleanly without syntax errors
    using shlex.join().
    """
    try:
        argv = sys.argv
        
        # Working directory canonicalization
        cwd = Path.cwd()
        wd_data = {
            "path": str(cwd),
            "real_path": str(cwd.resolve())
        }
        
        # Script info
        script_data = {}
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
                    pass
                
                # Try to hash the script file for exact reproducibility validation
                try:
                    with open(real_path, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    script_data["sha256"] = file_hash
                except Exception:
                    pass
            elif main_file == "-m":
                entrypoint_type = "module"
            elif main_file == "-c":
                entrypoint_type = "interactive"
        else:
            entrypoint_type = "interactive"
        
        # Re-run command exact replica
        # shlex.join natively escapes quotes and spaces elegantly
        escaped_args = shlex.join(argv) 
        rerun_command = f"cd {shlex.quote(str(cwd))} && python {escaped_args}"
        
        # Process dataset inputs if configured
        inputs_data = []
        input_cfg = config.get("capture", {}).get("inputs", {})
        if input_cfg.get("enabled", True):
            compute_md5 = input_cfg.get("compute_md5", False)
            ignore_ext = [x.lower() for x in input_cfg.get("ignore_extensions", [])]
            for idx, arg in enumerate(argv[1:], start=1):
                try:
                    po = Path(arg)
                    # Heuristic false-positive guard: If it strongly resembles an option flag, skip
                    if arg.startswith("-") or arg.startswith("--"):
                        continue
                        
                    # Ignore common extensions
                    if po.suffix and po.suffix.lstrip(".").lower() in ignore_ext:
                        continue
                        
                    if po.exists():
                        arg_data = {
                            "arg_index": idx,
                            "path": arg,
                            "real_path": str(po.resolve()),
                            "is_dir": po.is_dir()
                        }
                        
                        try:
                            # Safely fetch OS level changes
                            st = po.stat()
                            arg_data["size"] = st.st_size
                            arg_data["mtime"] = st.st_mtime
                            arg_data["ctime"] = st.st_ctime
                        except Exception:
                            pass
                            
                        if compute_md5 and po.is_file():
                            try:
                                import logging
                                logger = logging.getLogger("runtrace")
                                logger.warning(f"Computing MD5 for sys.argv[{idx}] ({arg}). This may cause startup latency.")
                                md5 = hashlib.md5()
                                with open(po, "rb") as f:
                                    for chunk in iter(lambda: f.read(4096), b""):
                                        md5.update(chunk)
                                arg_data["md5"] = md5.hexdigest()
                            except Exception:
                                pass
                                
                        inputs_data.append(arg_data)
                except Exception:
                    pass

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
