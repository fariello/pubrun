"""Normalize Python distribution names per Python Enhancement Proposal 503 (PEP 503).

Uses only the ``re`` standard-library module so lightweight callers such as
``pubrun.report.methods`` can normalize package names without importing
``pubrun.capture.packages`` or ``importlib.metadata``.
"""

import re

# PEP 503 normalization pattern collapsing runs of '-', '_', and '.' to '-'.
_PEP503_RE = re.compile(r"[-_.]+")


def normalize_package_name(name: str) -> str:
    """Return the PEP 503 normalized form of a Python distribution name."""
    return _PEP503_RE.sub("-", name).lower()
