import sys
import importlib.metadata
from typing import Dict, Any, List

def get_packages(config: Dict[str, Any]) -> Dict[str, Any]:
    """Capture installed Python packages via ``importlib.metadata``.

    Modes:
    - ``imported-only``: Only packages already loaded in ``sys.modules``.
    - ``top-level-installed``: All top-level pip distributions.
    - ``full-environment``: Every distribution in the environment.

    Args:
        config: Resolved pubrun configuration.
    """
    cfg = config.get("capture", {}).get("packages", {})
    mode = cfg.get("mode", "full-environment")
    
    # 1. Fast-exit if disabled
    if mode == "off":
        return {"capture_state": {"status": "suppressed"}}
        
    records: List[Dict[str, Any]] = []
    status = "complete"
    
    try:
        if mode == "imported-only":
            # Just grab versions of whatever is currently loaded in memory
            for mod_name in sorted(sys.modules.keys()):
                # Filter out submodules and built-in edge cases
                if '.' not in mod_name and mod_name != '_ast':
                    try:
                        version = importlib.metadata.version(mod_name)
                        records.append({
                            "name": mod_name, 
                            "version": version, 
                            "location": None, 
                            "editable": None
                        })
                    except importlib.metadata.PackageNotFoundError:
                        continue
        else: 
            # Extract across the full isolated environment or top-level list
            for dist in importlib.metadata.distributions():
                name = dist.metadata["Name"]
                version = dist.version
                location = str(dist.locate_file(""))
                
                # Check for "editable" install status by reading direct_url.json metadata
                editable = False
                try:
                    direct_url = dist.read_text("direct_url.json")
                    if direct_url and "dir_info" in direct_url:
                        editable = True
                except Exception:
                    pass
                    
                records.append({
                    "name": name,
                    "version": version,
                    "location": location,
                    "editable": editable
                })
    except Exception:
        status = "partial"
        
    return {
        "mode": mode,
        "records": sorted(records, key=lambda x: x["name"].lower()),
        "capture_state": {"status": status}
    }
