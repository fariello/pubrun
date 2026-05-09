import os
import getpass
from typing import Dict, Any

def get_process_info(config: Dict[str, Any]) -> Dict[str, Any]:
    """Capture process-level info: PID, PPID, username, UID, GID.

    Falls back gracefully on platforms where getuser() or getuid() are
    unavailable (e.g. restricted containers, Windows).

    Args:
        config: Resolved pubrun configuration.
    """
    
    # 1. Safely extract the username, falling back gracefully
    try:
        username = getpass.getuser()
    except Exception:
        username = "unknown"
        
    # 2. Extract UID/GID if supported by the OS (Unix/Linux/macOS)
    uid = getattr(os, 'getuid', lambda: None)()
    gid = getattr(os, 'getgid', lambda: None)()
    
    # 3. Construct and return the schema-compliant payload
    return {
        "pid": os.getpid(),
        "ppid": os.getppid() if hasattr(os, 'getppid') else None,
        "user": {
            "username": {"representation": "plain", "value": username},
            "uid": uid,
            "gid": gid
        },
        "capture_state": {"status": "complete"}
    }
