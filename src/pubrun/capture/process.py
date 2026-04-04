import os
import getpass
from typing import Dict, Any

def get_process_info(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Captures process-level information from the host operating system.
    
    This includes the Process ID (PID), Parent Process ID (PPID), and details 
    about the user executing the script (username, UID, GID).
    
    Args:
        config (Dict[str, Any]): The fully resolved pubrun configuration dictionary.
        
    Returns:
        Dict[str, Any]: A dictionary compliant with the `process` schema section.

    Assumptions:
        - The `getpass.getuser()` call may fail on strictly isolated container environments, defaulting securely to "unknown".
        - The UID and GID checks fall back cleanly to `None` on unsupported architectures like Windows.
        
    Example:
        >>> get_process_info({})
        {
            'pid': 1234, 
            'ppid': 1233, 
            'user': {
                'username': {'representation': 'plain', 'value': 'alice'}, 
                'uid': 1000, 
                'gid': 1000
            }, 
            'capture_state': {'status': 'complete'}
        }
    """
    
    # 1. Safely extract the username, falling back gracefully
    try:
        username = getpass.getuser()
    except Exception:
        username = "unknown"
        pass # for auto-indentation
        
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
