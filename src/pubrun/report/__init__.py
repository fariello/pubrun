"""Reporting subpackage and callable ``pubrun.report(name, data)`` entry point.

Calling ``pubrun.report(name, data)`` saves a structured custom report
(``{name}.json`` for a ``dict`` or ``list``, or ``{name}.txt`` otherwise)
inside the active run directory and emits an annotation event visible in
``pubrun show``.

Submodules (``pubrun.report.checks``, ``pubrun.report.diagnostics``,
``pubrun.report.methods``, ``pubrun.report.output``,
``pubrun.report.reproducibility``, ``pubrun.report.utils``) remain lazily
importable without eagerly loading ``pubrun.core``.
"""

import sys
import types
from typing import Any


class CallableModule(types.ModuleType):
    """Module subclass exposing ``pubrun.report`` as both a subpackage and a callable."""

    def __call__(self, name: str, data: Any) -> None:
        """Save a custom structured report to the active run directory.

        If ``data`` is a ``dict`` or ``list``, serializes it as strict RFC 8259
        JSON to ``{name}.json``. Otherwise, writes UTF-8 text to ``{name}.txt``.
        Emits an annotation event so the report appears in ``pubrun show``.

        Args:
            name: Base filename (without extension) relative to the active run
                directory.
            data: Report payload (``dict``/``list`` for JSON, or text-convertible
                value).

        Returns:
            None.

        Example:
            >>> pubrun.report("eval_metrics", {"accuracy": 0.942, "loss": 0.108})
        """
        from pubrun.core import report as real_report

        return real_report(name, data)


sys.modules[__name__].__class__ = CallableModule
