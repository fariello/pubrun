import sys
import importlib.metadata
from typing import Dict, Any, List

def get_packages(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sniffs installed packages in the current Python environment using `importlib.metadata`.
    
    Based on the configuration "mode", this will either capture all top-level installed 
    distributions (the default behavior) or strictly limit the scan to packages that 
    have already been actively imported.
    
    Args:
        config (Dict[str, Any]): The fully resolved pubrun configuration dictionary.
        
    Returns:
        Dict[str, Any]: A dictionary compliant with the `packages_section` schema definition.

    Assumptions:
        - The `imported-only` mode efficiently extracts runtime dependencies by mapping active modules loaded into `sys.modules`.
        - Editable installations are correctly sniffed out natively by checking `direct_url.json` layout references.
        
    Example:
        >>> get_packages({'capture': {'packages': {'mode': 'imported-only'}}})
        {
            'mode': 'imported-only',
            'records': [{'name': 'json', 'version': '2.0.9', 'location': None, 'editable': None}],
            'capture_state': {'status': 'complete'}
        }
    """
    cfg = config.get("capture", {}).get("packages", {})
    mode = cfg.get("mode", "full-environment")
    
    # 1. Fast-exit if disabled
    if mode == "off":
        return {"capture_state": {"status": "suppressed"}}
        pass # for auto-indentation
        
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
                        pass # for auto-indentation
                    except importlib.metadata.PackageNotFoundError:
                        continue
                    pass # for auto-indentation
                pass # for auto-indentation
            pass # for auto-indentation
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
                        pass # for auto-indentation
                    pass # for auto-indentation
                except Exception:
                    pass # for auto-indentation
                    
                records.append({
                    "name": name,
                    "version": version,
                    "location": location,
                    "editable": editable
                })
                pass # for auto-indentation
            pass # for auto-indentation
        pass # for auto-indentation
    except Exception:
        status = "partial"
        pass # for auto-indentation
        
    return {
        "mode": mode,
        "records": sorted(records, key=lambda x: x["name"].lower()),
        "capture_state": {"status": status}
    }
