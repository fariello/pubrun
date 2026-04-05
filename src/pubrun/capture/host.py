import platform
import socket
import logging
from typing import Dict, Any

logger = logging.getLogger("pubrun")

def get_host(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs the standard host telemetry footprint capturing OS parameters.
    
    Args:
        config (Dict[str, Any]): The globally resolved configuration mapping.
        
    Returns:
        Dict[str, Any]: A dictionary structurally matching the internal schema.
        
    Example:
        >>> get_host({})
        {'os_name': 'Windows', 'os_version': '10', 'hostname': 'workstation-X', ...}
    """
    host_config = config.get("capture", {}).get("host", {})
    if host_config.get("enabled", True) is False:
        return {"capture_state": {"status": "suppressed", "detail": "Host profile explicitly disabled."}}
        
    try:
        data = {
            "os_name": platform.system(),
            "os_version": platform.release(),
            "os_release": platform.version(),
            "hostname": platform.node() or socket.gethostname(),
            "capture_state": {"status": "complete"}
        }
        return data
    except Exception as e:
        logger.debug(f"pubrun failed tracking host metrics: {e}")
        return {"capture_state": {"status": "failed", "detail": str(e)}}
