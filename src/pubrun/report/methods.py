import math
from typing import Dict, Any, List, Optional
from pubrun.report.templates import MARKDOWN_TEMPLATE, LATEX_TEMPLATE, HIGHLIGHT_PACKAGES

def bytes_to_gb(bytes_val: int) -> float:
    if not bytes_val: return 0.0
    return round(bytes_val / (1024 ** 3), 1)

def extract_highlighted_packages(manifest: Dict[str, Any]) -> List[str]:
    """Return formatted strings for notable packages found in the manifest."""
    found = []
    records = manifest.get("packages", {}).get("records", [])
    for record in records:
        name = record.get("name", "").lower()
        if name in HIGHLIGHT_PACKAGES:
            version = record.get("version", "unknown")
            found.append(f"{name} (v{version})")
    return found

def generate_report(manifest: Dict[str, Any], format_type: str = "markdown") -> str:
    """Generate a publication-ready 'Computational Methods' paragraph.

    Args:
        manifest: Hydrated manifest dictionary.
        format_type: Output format (``"markdown"`` or ``"latex"``).
    """
    # Hardware
    # OS name — use the host capture data, not the Windows-only OS env var
    host = manifest.get("host", {})
    os_name = host.get("os_name", "an unknown OS")
    if format_type == "latex":
        os_name = os_name.replace("_", "\\_")
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
        packages_text = f"Key dependencies tracked include {', '.join(packages)}."
    else:
        packages_text = "Standard library dependencies were utilized."

    # pubrun version/commit — the tool that produced this record. Recorded in the
    # manifest as run.library_version / run.library_commit. Naming the exact
    # version (and commit) is important for reproducibility of the provenance.
    run_meta = manifest.get("run", {})
    pubrun_version = run_meta.get("library_version")
    pubrun_commit = run_meta.get("library_commit") or ""
    if pubrun_version and pubrun_commit:
        pubrun_version_text = f"pubrun v{pubrun_version} (commit {pubrun_commit[:8]})"
    elif pubrun_version:
        pubrun_version_text = f"pubrun v{pubrun_version}"
    else:
        pubrun_version_text = "pubrun (version unknown)"

    template = LATEX_TEMPLATE if format_type == "latex" else MARKDOWN_TEMPLATE

    return template.format(
        os_name=os_name,
        cpu_model=cpu_model,
        ram_gb=ram_gb,
        python_version=python_version,
        python_impl=python_impl.capitalize(),
        packages_text=packages_text,
        git_commit=git_commit[:8] if len(git_commit) >= 8 else git_commit,
        git_repo_text=git_repo_text,
        pubrun_version_text=pubrun_version_text
    ).strip()


# Methods-relevant fields compared across a run set (label -> extractor). Order
# is the display order for the variance note; extractors return a display string.
def _os_of(m: Dict[str, Any]) -> str:
    return m.get("host", {}).get("os_name") or "unknown OS"


def _cpu_of(m: Dict[str, Any]) -> str:
    return m.get("hardware", {}).get("cpu", {}).get("model") or "unknown CPU"


def _ram_of(m: Dict[str, Any]) -> str:
    return f"{bytes_to_gb(m.get('hardware', {}).get('memory_total_bytes', 0))} GB"


def _py_of(m: Dict[str, Any]) -> str:
    return (m.get("python", {}).get("version") or "unknown").split(" ")[0]


def _commit_of(m: Dict[str, Any]) -> str:
    c = m.get("git", {}).get("commit") or ""
    return c[:8] if len(c) >= 8 else (c or "unavailable")


def _pubrun_of(m: Dict[str, Any]) -> str:
    v = m.get("run", {}).get("library_version")
    return f"v{v}" if v else "version unknown"


def _packages_of(m: Dict[str, Any]) -> str:
    pkgs = extract_highlighted_packages(m)
    return ", ".join(sorted(pkgs)) if pkgs else "(standard library only)"


_VARIANCE_FIELDS = [
    ("Operating system", _os_of),
    ("CPU", _cpu_of),
    ("RAM", _ram_of),
    ("Python", _py_of),
    ("Git commit", _commit_of),
    ("pubrun", _pubrun_of),
    ("Key packages", _packages_of),
]


def generate_report_multi(manifests: List[Dict[str, Any]], format_type: str = "markdown") -> str:
    """Generate a methods paragraph aggregated over a SET of runs (option C).

    - Empty list: raises ValueError (the caller must have runs).
    - Exactly one run: byte-identical to ``generate_report`` (single-run parity).
    - Many runs: a representative paragraph (from the FIRST manifest — callers pass
      most-recent-first) that states "across N runs", plus a variance note listing
      only the methods-relevant fields that DIFFER across the set (sorted distinct
      values). Environment-homogeneous sets read like the single-run output with
      just the run count added. Output is deterministic for a fixed set.

    Divergence (including differing git commits) is disclosed, never a hard error.
    """
    if not manifests:
        raise ValueError("generate_report_multi requires at least one manifest")
    if len(manifests) == 1:
        return generate_report(manifests[0], format_type)

    n = len(manifests)
    base = generate_report(manifests[0], format_type)

    # Insert the run count into the representative paragraph's opening sentence.
    # (Kept simple and deterministic; the base text is the most-recent run.)
    count_note = (
        f"These figures describe a representative run; provenance was aggregated "
        f"across {n} runs."
    )

    # Compute per-field distinct values across the set (sorted for determinism).
    varying = []
    for label, fn in _VARIANCE_FIELDS:
        try:
            values = sorted({fn(m) for m in manifests})
        except Exception:
            continue
        if len(values) > 1:
            varying.append((label, values))

    if format_type == "latex":
        parts = [base, "", f"% {count_note}"]
        if varying:
            parts.append("% Environment varied across the aggregated runs:")
            for label, values in varying:
                joined = "; ".join(v.replace("_", "\\_") for v in values)
                parts.append(f"%   {label}: {joined}")
        return "\n".join(parts).strip()

    # markdown
    parts = [base, "", f"*{count_note}*"]
    if varying:
        parts.append("")
        parts.append("**Environment variation across the aggregated runs:**")
        for label, values in varying:
            parts.append(f"- {label}: {', '.join(values)}")
    return "\n".join(parts).strip()
