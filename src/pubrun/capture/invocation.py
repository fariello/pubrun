import sys
import shlex
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

def get_invocation(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Capture invocation context: argv, working directory, script metadata, and input files.

    Builds the ``rerun_command`` needed to reproduce the run and heuristically
    discovers input file paths from ``sys.argv``.

    Args:
        config: Resolved pubrun configuration. Controls input-file scanning
            and MD5 hashing behavior.
    """
    if config is None:
        config = {}
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
                    pass
                
                # Try to hash the script file for exact reproducibility validation
                try:
                    sha = hashlib.sha256()
                    with open(real_path, "rb") as f:
                        for chunk in iter(lambda: f.read(8192), b""):
                            sha.update(chunk)
                    script_data["sha256"] = sha.hexdigest()
                except Exception:
                    pass
            elif main_file == "-m":
                entrypoint_type = "module"
            elif main_file == "-c":
                entrypoint_type = "interactive"
        else:
            entrypoint_type = "interactive"
        
        # ---------------------------------------------------------
        # 3. Re-run Replication Engine
        # ---------------------------------------------------------
        # Windows cmd chokes on POSIX single quotes (via shlex),
        # and PowerShell pre-v7 crashes on `&&`.
        if sys.platform == "win32":
            import subprocess
            escaped_args = subprocess.list2cmdline(argv)
            cwd_str = subprocess.list2cmdline([str(cwd)])
            # Multiline string perfectly bypasses all operator (&, &&, ;) ecosystem inconsistencies on Windows
            rerun_command = f"cd {cwd_str}\npython {escaped_args}"
        else:
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
                            pass
                            
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
                                arg_data["md5"] = md5.hexdigest()
                            except Exception:
                                pass
                                
                        inputs_data.append(arg_data)
                except Exception:
                    pass

        # Apply argv redaction before storing in the manifest
        from pubrun.capture.redaction import redact_argv
        redacted_argv = redact_argv(argv, config)

        # Rebuild command_line and rerun_command from redacted argv
        if sys.platform == "win32":
            import subprocess as _sp
            redacted_cmdline = _sp.list2cmdline(redacted_argv)
            redacted_rerun = f"cd {_sp.list2cmdline([str(cwd)]) }\npython {redacted_cmdline}"
        else:
            redacted_cmdline = shlex.join(redacted_argv)
            redacted_rerun = f"cd {shlex.quote(str(cwd))} && python {redacted_cmdline}"

        return {
            "argv": redacted_argv,
            "command_line": redacted_cmdline,
            "rerun_command": redacted_rerun,
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
