import math
from typing import Dict, Any, List, Optional
from pubrun.report.templates import MARKDOWN_TEMPLATE, LATEX_TEMPLATE, HIGHLIGHT_PACKAGES

def bytes_to_gb(bytes_val: int) -> float:
    if not bytes_val: return 0.0
    return round(bytes_val / (1024 ** 3), 1)

def extract_highlighted_packages(manifest: Dict[str, Any]) -> List[str]:
    """Finds highlighted packages and their versions from the manifest."""
    found = []
    records = manifest.get("packages", {}).get("records", [])
    for record in records:
        name = record.get("name", "").lower()
        if name in HIGHLIGHT_PACKAGES:
            version = record.get("version", "unknown")
            found.append(f"{name} (v{version})")
    return found

def generate_report(manifest: Dict[str, Any], format_type: str = "markdown") -> str:
    """Generates the text for the methods section."""
    # Hardware
    os_name = "an unknown OS"
    env_vars = manifest.get("environment", {}).get("variables", [])
    for v in env_vars:
        if v.get("name") == "OS":
            os_name = str(v.get("value", {}).get("value", os_name)).replace("_", "\\_" if format_type == "latex" else "_")
            break
            
    hw = manifest.get("hardware", {})
    cpu_model = hw.get("cpu", {}).get("model", "unknown CPU")
    ram_gb = bytes_to_gb(hw.get("memory_total_bytes", 0))
    
    # Python
    py = manifest.get("python", {})
    python_version = py.get("version", "unknown").split(" ")[0]
    python_impl = py.get("implementation", "unknown")
    
    # Git
    git = manifest.get("git", {})
    git_commit = git.get("commit", "unknown")
    if not git_commit: git_commit = "unavailable"
    
    remote = git.get("remote_url", {}).get("value")
    git_repo_text = f" (origin: {remote})" if remote else ""
    if format_type == "latex":
        git_repo_text = git_repo_text.replace("_", "\\_")
    
    # Packages
    packages = extract_highlighted_packages(manifest)
    if packages:
        packages_text = f"Key dependencies explicitly tracked include {', '.join(packages)}."
    else:
        packages_text = "Standard library dependencies were utilized."
        
    template = LATEX_TEMPLATE if format_type == "latex" else MARKDOWN_TEMPLATE
    
    return template.format(
        os_name=os_name,
        cpu_model=cpu_model,
        ram_gb=ram_gb,
        python_version=python_version,
        python_impl=python_impl.capitalize(),
        packages_text=packages_text,
        git_commit=git_commit[:8] if len(git_commit) >= 8 else git_commit,
        git_repo_text=git_repo_text
    ).strip()
