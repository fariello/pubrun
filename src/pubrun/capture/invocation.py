import hashlib
import os
import shlex
import stat
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_DEFAULT_MAX_INPUT_MD5_BYTES = 100 * 1024 * 1024  # 100 MiB

_JUPYTER_CONN_FLAGS = ("-f", "--f", "--ConnectionFile", "--IPKernelApp.connection_file")
_JUPYTER_CONN_PREFIXES = tuple(flag + "=" for flag in _JUPYTER_CONN_FLAGS)


def _is_jupyter_kernel() -> bool:
    """Detect an active Jupyter ZMQInteractiveShell without importing IPython."""
    ipython_mod = sys.modules.get("IPython")
    if ipython_mod is None:
        return False
    get_ipython_fn = getattr(ipython_mod, "get_ipython", None)
    if not callable(get_ipython_fn):
        return False
    try:
        shell = get_ipython_fn()
    except Exception:
        return False
    return shell is not None and type(shell).__name__ == "ZMQInteractiveShell"


def _paths_match(a: str, b: str) -> bool:
    """Return True when two path strings refer to the same file or normalized path."""
    if a == b:
        return True
    if os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b)):
        return True
    try:
        pa, pb = Path(a), Path(b)
        if pa.exists() and pb.exists():
            return pa.resolve() == pb.resolve()
    except OSError:
        pass
    return False


def _parse_max_md5_bytes(raw: Any) -> int:
    """Parse [capture.inputs].max_md5_bytes (non-negative int; 0 = uncapped)."""
    if raw is None or isinstance(raw, bool):
        return _DEFAULT_MAX_INPUT_MD5_BYTES
    if isinstance(raw, int) and raw >= 0:
        return raw
    return _DEFAULT_MAX_INPUT_MD5_BYTES


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
        # 2. Main Entrypoint Script / Module / Notebook Evaluator
        # ---------------------------------------------------------
        script_data: Dict[str, Any] = {}
        entrypoint_type = "unknown"
        module_name: Optional[str] = None
        is_jupyter = _is_jupyter_kernel()

        main_file = str(argv[0]) if argv else ""
        if is_jupyter:
            entrypoint_type = "notebook"
        elif main_file:
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
                stats: Optional[os.stat_result] = None
                try:
                    stats = path_obj.stat()
                    script_data["size"] = stats.st_size
                    script_data["mtime"] = stats.st_mtime
                    script_data["ctime"] = stats.st_ctime
                except Exception:
                    stats = None

                # Try to hash the script file for exact reproducibility validation.
                # PERF-04: skip hashing for files > 1MB to avoid startup latency
                # on large notebooks/generated scripts.
                _max_hash_size = 1_048_576  # 1 MB
                try:
                    if (
                        stats is not None
                        and stat.S_ISREG(stats.st_mode)
                        and "size" in script_data
                    ):
                        if script_data["size"] <= _max_hash_size:
                            sha = hashlib.sha256()
                            with open(real_path, "rb") as f:
                                for chunk in iter(lambda: f.read(8192), b""):
                                    sha.update(chunk)
                            script_data["sha256"] = sha.hexdigest()
                        else:
                            script_data["sha256_skipped"] = "file exceeds 1MB"
                except Exception:
                    pass
            elif main_file == "-m":
                entrypoint_type = "module"
            elif main_file == "-c":
                entrypoint_type = "interactive"

            # Detect `python -m <pkg.mod>` via __main__.__spec__ when the spec
            # matches this invocation (avoiding hijack under `python -m pytest`).
            main_mod = sys.modules.get("__main__")
            main_spec = getattr(main_mod, "__spec__", None)
            spec_name = getattr(main_spec, "name", None) if main_spec is not None else None
            spec_origin = getattr(main_spec, "origin", None) if main_spec is not None else None
            if (
                isinstance(spec_name, str)
                and spec_name
                and spec_name != "__main__"
                and (
                    main_file == "-m"
                    or (
                        isinstance(spec_origin, str)
                        and bool(spec_origin)
                        and _paths_match(main_file, spec_origin)
                    )
                )
            ):
                stripped_name = (
                    spec_name[: -len(".__main__")]
                    if spec_name.endswith(".__main__")
                    else spec_name
                )
                if stripped_name:
                    entrypoint_type = "module"
                    module_name = stripped_name
        else:
            entrypoint_type = "interactive"

        # Apply argv redaction before input discovery and manifest storage
        from pubrun.capture.redaction import redact_argv
        redacted_argv = redact_argv(argv, config)

        # ---------------------------------------------------------
        # 4. sys.argv Dataset Discovery Heuristics
        # ---------------------------------------------------------
        # Scan CLI arguments for file paths that look like input datasets.
        # Bridges the gap of knowing if `data.csv` changed between runs
        # when the user ran `python train.py --data data.csv`.
        inputs_data: List[Dict[str, Any]] = []
        input_cfg = config.get("capture", {}).get("inputs", {})
        if input_cfg.get("enabled", True):
            compute_md5 = input_cfg.get("compute_md5", False)
            max_md5_bytes = _parse_max_md5_bytes(input_cfg.get("max_md5_bytes"))
            ignore_ext = [x.lower() for x in input_cfg.get("ignore_extensions", [])]
            skip_next_jupyter_arg = False
            for idx, arg in enumerate((str(a) for a in argv[1:]), start=1):
                try:
                    if is_jupyter:
                        if skip_next_jupyter_arg:
                            skip_next_jupyter_arg = False
                            continue
                        if arg in _JUPYTER_CONN_FLAGS:
                            skip_next_jupyter_arg = True
                            continue
                        if arg.startswith(_JUPYTER_CONN_PREFIXES):
                            continue

                    # A value redaction removed from argv must not reappear here.
                    # Check BEFORE splitting --flag=value so sensitive flag values
                    # (such as --api-key=creds.json) are never inspected.
                    if idx < len(redacted_argv) and redacted_argv[idx] != arg:
                        continue

                    # Heuristic Safety 1: Discard Option Flags (unless --flag=value)
                    candidate = arg
                    if arg.startswith("-"):
                        if "=" not in arg:
                            continue
                        _, candidate = arg.split("=", 1)
                        if not candidate:
                            continue

                    po = Path(candidate)
                    if is_jupyter and po.name == "ipykernel_launcher.py":
                        continue

                    # Heuristic Safety 2: Discard Runtime Caches
                    # Filter extensions designated safely ignorable by the user.
                    if po.suffix and po.suffix.lstrip(".").lower() in ignore_ext:
                        continue

                    # Single os.stat() call replaces exists/is_dir/stat/is_file.
                    try:
                        st = os.stat(candidate)
                    except OSError:
                        continue

                    is_dir = stat.S_ISDIR(st.st_mode)
                    is_reg = stat.S_ISREG(st.st_mode)
                    arg_data: Dict[str, Any] = {
                        "arg_index": idx,
                        "path": candidate,
                        "real_path": str(po.resolve()),
                        "is_dir": is_dir,
                        "size": st.st_size,
                        "mtime": st.st_mtime,
                        "ctime": st.st_ctime,
                    }

                    # DANGER ZONE: Deep Cryptographic Hash (bounded by max_md5_bytes)
                    if compute_md5 and is_reg:
                        if max_md5_bytes > 0 and st.st_size > max_md5_bytes:
                            arg_data["md5_skipped"] = f"file exceeds {max_md5_bytes} bytes"
                        else:
                            try:
                                import logging
                                logger = logging.getLogger("pubrun")
                                logger.warning(
                                    f"Computing MD5 for sys.argv[{idx}] ({candidate}). "
                                    f"This may cause startup latency."
                                )

                                # Iterate in 4KB chunks memory-safely so we don't blow up RAM.
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

        # Rebuild command_line and rerun_command from redacted argv
        exe = sys.executable or "python"
        if sys.platform == "win32":
            import subprocess as _sp
            redacted_cmdline = _sp.list2cmdline(redacted_argv)
            quoted_cwd = _sp.list2cmdline([str(cwd)])
            quoted_exe = _sp.list2cmdline([exe])
            if is_jupyter or main_file == "-c" or not main_file:
                redacted_rerun: Optional[str] = None
            elif entrypoint_type == "module" and module_name:
                extra_args = (
                    redacted_argv[2:]
                    if main_file == "-m" and len(redacted_argv) > 1 and redacted_argv[1] == module_name
                    else redacted_argv[1:]
                )
                mod_tokens = ["-m", module_name] + extra_args
                redacted_rerun = f"cd {quoted_cwd}\n{quoted_exe} {_sp.list2cmdline(mod_tokens)}"
            else:
                redacted_rerun = f"cd {quoted_cwd}\n{quoted_exe} {redacted_cmdline}"
        else:
            redacted_cmdline = shlex.join(redacted_argv)
            quoted_cwd = shlex.quote(str(cwd))
            quoted_exe = shlex.quote(exe)
            if is_jupyter or main_file == "-c" or not main_file:
                redacted_rerun = None
            elif entrypoint_type == "module" and module_name:
                extra_args = (
                    redacted_argv[2:]
                    if main_file == "-m" and len(redacted_argv) > 1 and redacted_argv[1] == module_name
                    else redacted_argv[1:]
                )
                mod_tokens = ["-m", module_name] + extra_args
                redacted_rerun = f"cd {quoted_cwd} && {quoted_exe} {shlex.join(mod_tokens)}"
            else:
                redacted_rerun = f"cd {quoted_cwd} && {quoted_exe} {redacted_cmdline}"

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
        from pubrun.capture.redaction import format_safe_error_detail, redact_argv
        try:
            safe_argv = redact_argv(list(sys.argv), config)
        except Exception:
            safe_argv = []
        return {
            "argv": safe_argv,
            "capture_state": {
                "status": "failed",
                "detail": format_safe_error_detail(e, config),
            },
        }
