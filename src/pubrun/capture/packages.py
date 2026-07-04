import re
import sys
import importlib.metadata
from typing import Dict, Any, List, Set


# Regex to extract the package name from a PEP 508 requirement string.
# Handles: "numpy>=1.21", "pytz", "foo[extra]>=1.0", "bar ; python_version<'3.9'"
_REQ_NAME_RE = re.compile(r'^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)')


def _parse_req_name(req_str: str) -> str:
    """Extract the package name from a PEP 508 requirement string."""
    m = _REQ_NAME_RE.match(req_str.strip())
    return m.group(1) if m else ""


def get_packages(config: Dict[str, Any]) -> Dict[str, Any]:
    """Capture installed Python packages via ``importlib.metadata``.

    Modes:
    - ``imported-only``: Only packages already loaded in ``sys.modules`` (default).
    - ``imported-transitive``: Imported packages plus their declared dependencies.
    - ``top-level-installed``: All top-level pip distributions.
    - ``full-environment``: Every distribution in the environment.

    Args:
        config: Resolved pubrun configuration.
    """
    cfg = config.get("capture", {}).get("packages", {})
    mode = cfg.get("mode", "imported-only")
    
    # 1. Fast-exit if disabled
    if mode == "off":
        return {"capture_state": {"status": "suppressed"}}
        
    records: List[Dict[str, Any]] = []
    status = "complete"
    
    try:
        if mode in ("imported-only", "imported-transitive"):
            # Grab versions of whatever is currently loaded in memory
            imported_names: Set[str] = set()
            for mod_name in sorted(sys.modules.keys()):
                # Filter out submodules and built-in edge cases
                if '.' not in mod_name and mod_name != '_ast':
                    try:
                        version = importlib.metadata.version(mod_name)
                        imported_names.add(mod_name)
                        records.append({
                            "name": mod_name, 
                            "version": version, 
                            "location": None, 
                            "editable": None,
                            "source": "imported",
                        })
                    except importlib.metadata.PackageNotFoundError:
                        continue

            # Transitive: for each imported package, record its declared deps
            if mode == "imported-transitive":
                seen: Set[str] = {r["name"].lower() for r in records}
                # Map from transitive package name -> which imported packages require it
                required_by: Dict[str, List[str]] = {}

                for pkg_name in list(imported_names):
                    try:
                        dist = importlib.metadata.distribution(pkg_name)
                        requires = dist.requires
                        if not requires:
                            continue
                        for req_str in requires:
                            dep_name = _parse_req_name(req_str)
                            if not dep_name:
                                continue
                            dep_lower = dep_name.lower()
                            # Track who requires this dep
                            required_by.setdefault(dep_lower, [])
                            if pkg_name not in required_by[dep_lower]:
                                required_by[dep_lower].append(pkg_name)
                            # Skip if already recorded
                            if dep_lower in seen:
                                continue
                            # Try to get its version (only if installed)
                            try:
                                dep_version = importlib.metadata.version(dep_name)
                                seen.add(dep_lower)
                                records.append({
                                    "name": dep_name,
                                    "version": dep_version,
                                    "location": None,
                                    "editable": None,
                                    "source": "transitive",
                                    "required_by": required_by[dep_lower],
                                })
                            except importlib.metadata.PackageNotFoundError:
                                continue  # Extra not installed; skip
                    except importlib.metadata.PackageNotFoundError:
                        continue

                # Update required_by for transitive records that were discovered
                # by multiple imported packages
                for rec in records:
                    if rec.get("source") == "transitive":
                        dep_lower = rec["name"].lower()
                        if dep_lower in required_by:
                            rec["required_by"] = required_by[dep_lower]

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
                    "editable": editable,
                })
    except Exception:
        status = "partial"
        
    return {
        "mode": mode,
        "records": sorted(records, key=lambda x: x["name"].lower()),
        "capture_state": {"status": status}
    }
