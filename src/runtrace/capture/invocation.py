import sys
import shlex
import hashlib
from pathlib import Path
from typing import Dict, Any

def get_invocation() -> Dict[str, Any]:
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
        
        return {
            "argv": argv,
            "command_line": escaped_args,
            "rerun_command": rerun_command,
            "entrypoint_type": entrypoint_type,
            "script": script_data,
            "working_directory": wd_data,
            "capture_state": {"status": "complete"}
        }
    except Exception as e:
        return {
            "argv": sys.argv,
            "capture_state": {"status": "failed", "detail": str(e)}
        }
